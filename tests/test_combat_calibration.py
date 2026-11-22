from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from yixian.combat_calibration import select_sources, iter_selected_records, project_rounds, summarize_rounds
from yixian.order_data import game_split
from yixian.replays import game_key
from test_replays import sample


def fixture():
    record = sample()
    for i in range(100):
        record['data']['gameId'] = f'train-{i}'
        if game_split(game_key(record['data']['gameId'])) == 'train':
            break
    turn = record['data']['roundStats'][0]
    turn['p1']['publicData']['characterId'] = 1000003
    turn['log'] = []
    turn['battleParams'] = []
    raw = json.dumps(record).encode()
    source = {'game_id': game_key(record['data']['gameId']), 'split': 'train',
              'archive': '1000.tar.zst', 'member': '1000/1001_p0.json',
              'raw_sha256': hashlib.sha256(raw).hexdigest()}
    return record, source, raw


class CombatCalibrationTests(unittest.TestCase):
    def test_selection_is_grouped_and_outcome_independent(self):
        _, source, _ = fixture()
        row = {k: source[k] for k in ('game_id', 'split')} | {'source': source}
        later = deepcopy(row)
        later['source']['member'] = '1000/1001_p7.json'
        selected = select_sources([later, row, row], games=1)
        self.assertEqual(selected, [source])
        self.assertEqual(select_sources([row, later], games=1), selected)

    def test_test_role_and_conflicting_provenance_rejected(self):
        _, source, _ = fixture()
        row = {k: source[k] for k in ('game_id', 'split')} | {'source': source}
        with self.assertRaisesRegex(ValueError, 'training'):
            select_sources([dict(row, split='test')], games=1)
        conflict = deepcopy(row)
        conflict['source']['raw_sha256'] = 'f'*64
        with self.assertRaisesRegex(ValueError, 'provenance'):
            select_sources([row, conflict], games=1)

    def archive(self, directory, source, raw, *, duplicate=False):
        path = Path(directory)/source['archive']
        with tarfile.open(path, 'w:zst') as archive:
            # An unselected malformed JSON would crash a broad archive reader.
            for name, data in [('1000/1000_p0.json', b'not-json-heldout-payload'), (source['member'], raw)]:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            if duplicate:
                archive.addfile(info, io.BytesIO(data))
        return path

    def test_only_selected_payload_is_parsed(self):
        record, source, raw = fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = self.archive(directory, source, raw)
            self.assertEqual(list(iter_selected_records(path, [source])), [(source, record)])

    def test_raw_hash_and_missing_member_rejected(self):
        _, source, raw = fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = self.archive(directory, source, raw)
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                list(iter_selected_records(path, [dict(source, raw_sha256='0'*64)]))
            with self.assertRaisesRegex(ValueError, 'missing'):
                list(iter_selected_records(path, [dict(source, member='1000/1002_p0.json')]))

    def test_group_version_and_duplicate_member_rejected(self):
        record, source, raw = fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = self.archive(directory, source, raw, duplicate=True)
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                list(iter_selected_records(path, [source]))
            with self.assertRaisesRegex(ValueError, 'whole-game'):
                list(iter_selected_records(path, [dict(source, game_id='wrong')]))
            record['data']['version'] = 'old'
            raw = json.dumps(record).encode()
            source['raw_sha256'] = hashlib.sha256(raw).hexdigest()
            path = self.archive(directory, source, raw)
            with self.assertRaisesRegex(ValueError, 'version'):
                list(iter_selected_records(path, [source]))

    def test_no_private_hands_post_state_or_invented_hp(self):
        record, source, _ = fixture()
        record['data']['roundStats'][0]['p1']['publicData']['hp'] = 999
        rows, _ = project_rounds(record, source)
        text = json.dumps(rows)
        for private in ['alice', 'bob', 'private name', 'private_snapshot', 'after_snapshot']:
            self.assertNotIn(private, text)
        player = rows[0]['players'][0]
        self.assertNotIn('hand', player['candidate_start'])
        self.assertNotIn('handCards', player['candidate_start'])
        self.assertFalse(player['direct_hp_field_present'])
        self.assertEqual(player['candidate_start']['destiny'], 100)
        self.assertNotIn('hp', player['candidate_start'])
        self.assertFalse(rows[0]['training_label_allowed'])

    def test_empty_logs_are_not_traces_and_mapping_not_admission(self):
        record, source, _ = fixture()
        rows, _ = project_rounds(record, source)
        report = summarize_rounds(rows, card_mapping={123: 'a', 0: 'b', 456: 'c'},
            reference_subset={'a', 'b', 'c'}, regular_components=set(), season_components=set())
        self.assertEqual(report['log_status_counts'], {'empty': 1})
        self.assertEqual(report['both_sides_direct_hp_and_max_hp'], 0)
        self.assertEqual(report['all_cards_have_candidate_mapping'], 1)
        self.assertEqual(report['training_labels_emitted'], 0)
        self.assertEqual(report['admitted_training_content'], [])
        self.assertEqual(report['source_games'], 1)
        self.assertFalse(report['current_version_combat_verified'])


if __name__ == '__main__':
    unittest.main()
