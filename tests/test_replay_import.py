from compression import zstd
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from tools.import_replays import download_archive, import_sample, iter_records


def record(dao_xin=True):
    def player(uid):
        return {'publicData': {'uid': uid, 'characterId': 1, 'life': 100,
                               'lastRoundData': {'life': 100, 'usedCards': [11, 0, 12]}},
                'privateData': {'usedCards': [11, 0, 12]}}
    return {'data': {'gameId': 'whole-game', 'version': 'test-version', 'seasonMec': 10,
                    'gameMode': 3, 'isDaoXinRank': dao_xin, 'uid': 'a',
                    'roundStats': [{'round': 1, 'p1': player('a'), 'p2': player('b'),
                                   'firstPlayerId': 'a', 'winerId': 'b'}]}}


def archive(path, records):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as tar:
        for name, value in records:
            payload = json.dumps(value).encode()
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            tar.addfile(member, io.BytesIO(payload))
    path.write_bytes(zstd.compress(stream.getvalue()))
    return {'path': path.name, 'size': path.stat().st_size,
            'lfs': {'oid': hashlib.sha256(path.read_bytes()).hexdigest()}}


class ReplayImportTests(unittest.TestCase):
    def test_collects_non_ranked_perspectives_of_selected_game_and_keeps_group(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            info = archive(cache/'100.tar.zst', [(f'100/100_p{i}.json', record(i == 3)) for i in range(8)])
            metadata = {'sha': 'a'*40, 'siblings': [{'rfilename': info['path']}]}
            with patch('tools.import_replays.request_json', side_effect=[metadata, [info]]):
                out, manifest = import_sample(games=1, cache=cache, out=cache/'out')
            self.assertEqual(manifest['whole_games'], 1)
            self.assertEqual(manifest['perspective_records'], 8)
            group = next(iter(manifest['games'].values()))
            self.assertTrue(group['all_eight_json_perspectives_present'])
            rows = [json.loads(line) for line in (out/'rounds.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(len({row['dataset_split'] for row in rows}), 1)
            self.assertEqual(len({row['game_id'] for row in rows}), 1)

    def test_duplicate_members_cannot_create_fake_eight_views(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'100.tar.zst'
            archive(path, [('100/100_p0.json', record())]*8)
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                list(iter_records(path, 1024*1024))

    def test_conflicting_season_in_same_game_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            wrong = deepcopy(record(False)); wrong['data']['seasonMec'] = 9
            info = archive(cache/'100.tar.zst', [('100/100_p0.json', record()), ('100/100_p1.json', wrong)])
            metadata = {'sha': 'a'*40, 'siblings': [{'rfilename': info['path']}]}
            with patch('tools.import_replays.request_json', side_effect=[metadata, [info]]):
                with self.assertRaisesRegex(ValueError, 'disagree on season'):
                    import_sample(games=1, cache=cache, out=cache/'out')
            self.assertFalse((cache/'out/manifest.json').exists())

    def test_read_budget_and_unsafe_names_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'100.tar.zst'
            archive(path, [('100/100_p0.json', record())])
            with self.assertRaisesRegex(ValueError, 'Decoded archive'):
                list(iter_records(path, 10))
            archive(path, [('../100_p0.json', record())])
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                list(iter_records(path, 1024*1024))

    def test_bad_cache_hash_and_invalid_budgets_do_not_download(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'100.tar.zst'
            info = archive(path, [('100/100_p0.json', record())])
            info['lfs']['oid'] = '0'*64
            with patch('tools.import_replays.urllib.request.urlopen') as network:
                with self.assertRaisesRegex(ValueError, 'Cached archive'):
                    download_archive('a'*40, info, path, 1024*1024)
                network.assert_not_called()
        with patch('tools.import_replays.request_json') as network:
            for value in (0, -1, float('inf'), True):
                with self.assertRaises(ValueError):
                    import_sample(max_download_mb=value)
            network.assert_not_called()


if __name__ == '__main__':
    unittest.main()
