from copy import deepcopy
from pathlib import Path
import json, shutil, subprocess, unittest
from unittest.mock import patch

# Keep standard-library/base initialization outside the retained version chain.
from yixian import full_battle
from yixian import full_battle_v125r3 as new

STAGE = new.ROOT / 'runs/stages/20261116T074100Z-s2-season-random-inputs'
FIXTURES = json.loads((STAGE / 'binding-fixtures-v125.json').read_text('utf8'))

class SeasonRandomBindingTests(unittest.TestCase):
    def test_runtime_binding_guards(self):
        run = subprocess.run([shutil.which('node'), '--experimental-default-type=module',
            str(new.ROOT / 'tests/current_season_random_inputs_v125r3_probe.mjs')],
            capture_output=True, text=True, encoding='utf8', timeout=60)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)['scenarios'], 48)

    def test_start_and_stream_binding_exclude_terminal_labels(self):
        facts = new.extension_contract()
        self.assertEqual(set(facts['admitted_records']), set(FIXTURES))
        self.assertIs(new.catalogue, new.previous.catalogue)
        for rid, fixture in FIXTURES.items():
            with self.subTest(record_id=rid):
                row, ctx = deepcopy(fixture['row']), deepcopy(fixture['context'])
                original = deepcopy(fixture['compiled'])
                kwargs = dict(combat_context=ctx, first_player=original['battle']['first_player'])
                with patch.object(new.previous, 'compile_start', side_effect=lambda *a, **k: deepcopy(original)):
                    got = new.compile_start(row, **kwargs)
                    stream = got['battle'].pop('replay_parameters')
                    metadata = got.pop('replay_parameter_context_v125')
                    self.assertEqual(got, original)
                    self.assertEqual(stream['stream'], ctx['battle_params'])
                    self.assertFalse(metadata['training_label_allowed'])
                    row['outcome'] = {'recorded_hp_delta': 9999, 'winner_snapshot_slot': 'p1', 'recorded_turn_count': 1}
                    for player in ctx['players']:
                        player['after_talent_counters'] = {'invalid_terminal_label': 9999}
                    self.assertEqual(new.compile_start(row, **kwargs)['battle']['replay_parameters'], stream)
                    ctx['battle_params'][0] += 1
                    with self.assertRaisesRegex(new.UnresolvedBattle, 'recorded_stream_mismatch'):
                        new.compile_start(row, **kwargs)
                    ctx['battle_params'] = list(stream['stream'])
                    row['battle_params_evidence']['entries'] += 1
                    with self.assertRaisesRegex(new.UnresolvedBattle, 'source_parameter_mismatch'):
                        new.compile_start(row, **kwargs)
                    row['battle_params_evidence']['entries'] -= 1
                    row['players'][0]['candidate_start']['board'].reverse()
                    with self.assertRaisesRegex(new.UnresolvedBattle, 'original_snapshot_mismatch'):
                        new.compile_start(row, **kwargs)

    def test_counterfactual_start_and_duplicate_readers_rejected(self):
        fixture = next(iter(FIXTURES.values()))
        row, ctx = fixture['row'], fixture['context']
        for mutate, message in [
            (lambda b: b.update(seed='changed'), 'unaudited_compiled_start'),
            (lambda b: b.update(replay_parameters={}), 'mixed_parameter_handlers')]:
            altered = deepcopy(fixture['compiled'])
            mutate(altered['battle'])
            with patch.object(new.previous, 'compile_start', return_value=altered):
                with self.assertRaisesRegex(new.UnresolvedBattle, message):
                    new.compile_start(row, combat_context=ctx)
        sentinel = object()
        with patch.object(new.previous, 'compile_start', return_value=sentinel) as old:
            self.assertIs(new.compile_start({'id': 'unbound-record'}), sentinel)
            old.assert_called_once_with({'id': 'unbound-record'})

if __name__ == '__main__':
    unittest.main()
