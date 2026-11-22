"""Admission checks on real opening inputs; full combats are evaluated separately."""
from copy import deepcopy
from pathlib import Path
import json
import unittest
from yixian import full_battle_v109 as engine, full_battle as base

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'replay-07782d8c64bd4a0e0123de97ae8aab61ab1b46b09e6b8ad52df46f93333ea8a4-round-'


class ConsumptionCapacityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        plan = json.loads((ROOT / 'runs/stages/20261115T122500Z-s2-permanent-card-readers/batch-plan-v108r3.json').read_text('utf8'))
        cls.rows = {}; cls.contexts = {}; cls.tables = engine.catalogue()
        for co in plan['cohorts']:
            cls.rows.update({r['id']: r for r in map(json.loads, (ROOT / co['rows']).read_text('utf8').splitlines())})
            cls.contexts.update(json.loads((ROOT / co['contexts']).read_text('utf8')))

    def compile(self, row, context=None):
        c = deepcopy(self.contexts[row['id']]) if context is None else context
        return engine.compile_start(row, tables=self.tables, combat_context=c,
            game_mode=c['game_mode'], season_mec=c['season_mec'], seed='diagnostic-' + row['id'])

    def test_original_bound_receipt_and_global_leaf_unchanged(self):
        row = deepcopy(self.rows[PREFIX + '13']); before = deepcopy(row)
        context = deepcopy(self.contexts[row['id']]); saved_context = deepcopy(context)
        fields = set(base.PERMANENT_FIELDS)
        compiled = self.compile(row, context)
        self.assertEqual(row, before); self.assertEqual(context, saved_context)
        self.assertEqual(base.PERMANENT_FIELDS, fields); self.assertNotIn('10049', fields)
        self.assertEqual(compiled['consumption_capacity_context_v109']['permanent10049'],
            [{'present': True, 'value': 1}, {'present': False, 'value': None}])

    def test_bound_receipt_rejects_mutated_original_stock(self):
        row = deepcopy(self.rows[PREFIX + '13'])
        row['players'][0]['candidate_start']['permanentBuffTempDatas']['10049'] = 2
        with self.assertRaises(engine.UnresolvedBattle):self.compile(row)

    def test_signed_stock_does_not_become_a_battle_buff(self):
        row = deepcopy(self.rows[PREFIX + '6']); expected = self.compile(row)['battle']
        for value in [0, -3, -(2**31), 2**31 - 1]:
            row['players'][1]['candidate_start']['permanentBuffTempDatas']['10049'] = value
            actual = self.compile(row)
            self.assertEqual(actual['battle'], expected)
            self.assertEqual(actual['consumption_capacity_context_v109']['permanent10049'][1]['value'], value)

    def test_missing_map_and_invalid_stock_rejected(self):
        for value in [True, None, '1', 2**31, -(2**31)-1]:
            row = deepcopy(self.rows[PREFIX + '6'])
            row['players'][1]['candidate_start']['permanentBuffTempDatas']['10049'] = value
            with self.assertRaisesRegex(engine.UnresolvedBattle, 'invalid_signed_value'):self.compile(row)
        row = deepcopy(self.rows[PREFIX + '6'])
        del row['players'][0]['candidate_start']['permanentBuffTempDatas']
        with self.assertRaisesRegex(engine.UnresolvedBattle, 'explicit_permanent_map_required'):self.compile(row)

    def test_old_entry_and_unknown_keys_remain_blocked(self):
        row = deepcopy(self.rows[PREFIX + '6']); context = self.contexts[row['id']]
        with self.assertRaisesRegex(engine.UnresolvedBattle, 'permanent_hooks_pending:10049'):
            engine.previous.compile_start(row, tables=self.tables, combat_context=context,
                game_mode=3, season_mec=10, seed='diagnostic-' + row['id'])
        row['players'][1]['candidate_start']['permanentBuffTempDatas']['10016'] = 1
        with self.assertRaisesRegex(engine.UnresolvedBattle, 'permanent_hooks_pending:10016'):self.compile(row)

    def test_cloud_combination_requires_separate_migration(self):
        row = deepcopy(self.rows[PREFIX + '6']); context = deepcopy(self.contexts[row['id']])
        context['cloud_sword_record'] = {}
        with self.assertRaisesRegex(engine.UnresolvedBattle, 'cloud_leaf_combination_pending'):self.compile(row, context)


if __name__ == '__main__':unittest.main()
