from copy import deepcopy
from pathlib import Path
import json
import unittest
from unittest.mock import patch
from yixian import combat_start_context_bindings_v6 as binding

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'runs/stages/20261115T105500Z-s2-preparation-context-binding'


class PreparationSourceBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        plan = json.loads((STAGE / 'source-plan-v6.json').read_text('utf8'))
        cls.rows = {r['id']: r for r in map(json.loads, (ROOT / plan['rows']).read_text('utf8').splitlines())}
        cls.previous = json.loads((ROOT / plan['previous_contexts']).read_text('utf8'))
        cls.contexts = json.loads((STAGE / 'source-intake/combat-context.json').read_text('utf8'))
        cls.admitted = json.loads((STAGE / 'source-intake/admitted-records.json').read_text('utf8'))
        cls.rid = next(iter(cls.admitted))

    def fixture(self):
        row = deepcopy(self.rows[self.rid]); context = deepcopy(self.previous[self.rid])
        receipt = self.contexts[self.rid][binding.FIELD]
        source = {'split': 'train', 'game_id': row['game_id'], 'raw_sha256': row['source']['raw_sha256'],
                  'archive': receipt['archive'], 'member': receipt['member']}
        turn = {'round': row['round']}
        for index, slot in enumerate(('p1', 'p2')):
            owned = row['players'][index]['candidate_start']['xian_mo_strategies']
            turn[slot] = {'publicData': {'lastRoundData': {'xianMoStrategies': list(owned)}},
                'privateData': {'xianMoData': {'strategies': [{'selected': x} for x in owned],
                    'tempDatas': deepcopy(receipt['players'][index]['present_values'])}}}
        return turn, source, row, context

    def test_all_real_receipts_are_additive_and_valid(self):
        self.assertEqual(len(self.admitted), 61)
        result = binding.validate_additions(list(self.rows.values()), self.previous, self.contexts, set(self.admitted))
        self.assertEqual(result, self.admitted)

    def test_missing_map_is_unknown_but_present_empty_has_documented_defaults(self):
        turn, source, row, context = self.fixture()
        del turn['p1']['privateData']['xianMoData']['tempDatas']
        with self.assertRaisesRegex(ValueError, 'complete_map_required'):
            binding.bind_preparation(turn, source, row, context)
        turn['p1']['privateData']['xianMoData']['tempDatas'] = {}
        result = binding.bind_preparation(turn, source, row, context)
        receipt = result[binding.FIELD]; expected = {'receipt_sha256': binding.digest_json(receipt), 'snapshot_sha256': receipt['snapshot_sha256']}
        self.assertTrue(all(v == 0 for v in binding.validate_receipt(row, result, expected)[0].values()))

    def test_raw_round_game_seat_and_ownership_mismatch_rejected(self):
        for kind in ('raw', 'round', 'game', 'seat', 'ownership'):
            with self.subTest(kind=kind):
                turn, source, row, context = self.fixture()
                if kind == 'raw': source['raw_sha256'] = '0' * 64
                if kind == 'round': turn['round'] += 1
                if kind == 'game': source['game_id'] = 'another_game'
                if kind == 'seat': context['players'][0]['snapshot_slot'] = 'p2'
                if kind == 'ownership': turn['p1']['privateData']['xianMoData']['strategies'] = [{'selected': -999}]
                with self.assertRaises(ValueError): binding.bind_preparation(turn, source, row, context)

    def test_changed_start_and_receipt_fail_closed(self):
        row = deepcopy(self.rows[self.rid]); context = deepcopy(self.contexts[self.rid])
        context[binding.FIELD]['players'][0]['complete_temp_map_present'] = False
        with self.assertRaises(ValueError): binding.validate_receipt(row, context, self.admitted[self.rid])
        context = deepcopy(self.contexts[self.rid]); row['players'][0]['candidate_start']['board'].reverse()
        with self.assertRaises(ValueError): binding.validate_receipt(row, context, self.admitted[self.rid])

    def test_terminal_values_are_not_projection_inputs(self):
        turn, source, row, context = self.fixture()
        before = binding.bind_preparation(turn, source, row, context)
        turn['winner'] = 'changed'; turn['hpDelta'] = -99999; turn['turnCount'] = -1
        row['recorded_result'] = {'winner': 'changed', 'hp_delta': -99999}
        for slot in ('p1', 'p2'):
            turn[slot]['publicData']['destiny'] = -99999
        self.assertEqual(binding.bind_preparation(turn, source, row, context), before)

    def test_grids_are_bounded_and_bool_is_not_integer(self):
        turn, source, row, context = self.fixture()
        for index, slot in enumerate(('p1', 'p2')):
            ids = set(row['players'][index]['candidate_start']['xian_mo_strategies']) & binding.SUPPORTED
            if not ids: continue
            key = str(next(iter(ids))); turn[slot]['privateData']['xianMoData']['tempDatas'][key] = True
            with self.assertRaisesRegex(ValueError, 'invalid_value'):
                binding.bind_preparation(turn, source, row, context)
            break

    def test_translation_does_not_impersonate_old_raw_projection(self):
        for rid, expected in self.admitted.items():
            row = self.rows[rid]; ctx = self.contexts[rid]
            values = binding.validate_receipt(row, ctx, expected)
            try: projected, translated, ashes, disabled = binding.project_legacy_inputs(row, ctx, values)
            except ValueError as error:
                self.assertIn('active1010_not_implemented', str(error)); continue
            self.assertNotIn('engraving_source_projection_sha256', translated)
            self.assertNotIn(binding.FIELD, translated)
            self.assertEqual(row, self.rows[rid])
            self.assertEqual(ctx, self.contexts[rid])
            for player in projected['players']:
                self.assertNotIn(1010, player['candidate_start']['xian_mo_strategies'])
                self.assertNotIn(13015, player['candidate_start']['xian_mo_strategies'])

    def test_old_engine_delegate_and_unregistered_receipt_rejection(self):
        from yixian import full_battle_v105 as engine
        rid = next(r for r in self.rows if r not in self.admitted)
        with patch.object(engine.previous, 'compile_start', return_value={'unchanged': True}) as old:
            self.assertEqual(engine.compile_start(self.rows[rid], combat_context=self.contexts[rid]), {'unchanged': True})
            old.assert_called_once_with(self.rows[rid], combat_context=self.contexts[rid])
        context = deepcopy(self.contexts[rid]); context[binding.FIELD] = {}
        with self.assertRaises(engine.UnresolvedBattle): engine.compile_start(self.rows[rid], combat_context=context)


if __name__ == '__main__': unittest.main()
