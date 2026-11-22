from copy import deepcopy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from yixian import combat_validation_batch as batch


def row(rid, card=1000006):
    return {'id': rid, 'game_id': 'game-' + rid, 'split': 'train', 'round': 2,
        'outcome': {'winner_snapshot_slot': 'p1', 'first_player_snapshot_slot': 'p1',
                    'recorded_hp_delta': 5, 'recorded_turn_count': 2, 'recorded_destiny_damage': 3},
        'players': [{'character_id': 1000003, 'candidate_start': {'board': [card], 'talents': [],
            'fate_strategies': [], 'xian_mo_strategies': [], 'permanentBuffTempDatas': {}}},
            {'character_id': 1000004, 'candidate_start': {'board': [1000007], 'talents': [],
            'fate_strategies': [], 'xian_mo_strategies': [], 'permanentBuffTempDatas': {}}}]}


def change(**kwargs):
    return {'name': 'card336', 'scope': 'card', 'card_ids': [336, 10336, 20336],
        'dependency_complete': True, 'dependency_review': 'All grades plus known copy consumers reviewed.', **kwargs}


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.rows = [row('a', 336), row('b'), row('c'), row('d')]
        self.contexts = {r['id']: {'game_mode': 3, 'season_mec': 10, 'players': []} for r in self.rows}

    def select(self, changes=None, controls=0):
        return batch.select_records(self.rows, self.contexts, changes or [change()], control_count=controls)

    def test_batch_union_both_players_and_grade_variants(self):
        self.rows[1]['players'][1]['candidate_start']['board'] = [10336]
        self.rows[2]['players'][0]['candidate_start']['talents'] = [27]
        selected = self.select([change(), change(name='dragon-scale', scope='fate', card_ids=[], fate_ids=[27])])
        self.assertEqual(selected['selected_record_ids'], ['a', 'b', 'c'])
        self.assertFalse(selected['selection_is_dependency_proof'])
        self.assertTrue(selected['release_requires_full_pass'])

    def test_hand_copy_candidate_and_permanent_key_even_zero(self):
        self.contexts['b']['players'] = [{'dream_echo_hand': {'raw_cards': [20336]}}]
        self.rows[2]['players'][1]['candidate_start']['permanentBuffTempDatas'] = {'393': 0}
        selected = self.select([change(), change(name='indigestion', scope='permanent', card_ids=[], permanent_ids=[393])])
        self.assertEqual(selected['selected_record_ids'], ['a', 'b', 'c'])

    def test_season_switch_and_explicit_related_cards_are_unioned(self):
        self.contexts['b']['players'] = [{'heaven_spirit_switch': {'selected_strategy_ids': [1001]}}]
        self.rows[2]['players'][0]['candidate_start']['board'] = [349]
        selected = self.select([change(card_ids=[336, 10336, 20336, 349]),
                                change(name='spirit', scope='season', card_ids=[], season_ids=[1001])])
        self.assertEqual(selected['selected_record_ids'], ['a', 'b', 'c'])

    def test_outcomes_and_post_battle_context_cannot_select_or_change_controls(self):
        before = self.select(controls=1)
        self.rows[1]['outcome']['recorded_hp_delta'] = 336
        self.contexts['b']['players'] = [{'after_talent_counters': {'raw_cards': [336]}}]
        self.contexts['b']['battle_params'] = [{'raw_cards': [336]}]
        after = self.select(controls=1)
        self.assertEqual(before, after)
        self.assertEqual(len(after['control_record_ids']), 1)
        self.assertEqual(len(set(after['selected_record_ids'])), 2)

    def test_shared_logic_and_unknown_dependencies_force_full(self):
        for item in [change(scope='damage'), change(scope='unknown'), change(dependency_complete=False)]:
            selected = self.select([item])
            self.assertTrue(selected['full_required_by_scope'])
            self.assertEqual(len(selected['selected_record_ids']), 4)
            self.assertEqual(selected['control_record_ids'], [])

    def test_missing_train_context_and_duplicate_ids_fail_closed(self):
        for mutate in [lambda: self.rows[0].update(split='test'),
                       lambda: self.contexts.pop('a'),
                       lambda: self.rows.append(deepcopy(self.rows[0]))]:
            saved_rows, saved_contexts = deepcopy(self.rows), deepcopy(self.contexts)
            mutate()
            with self.assertRaises(ValueError): self.select()
            self.rows, self.contexts = saved_rows, saved_contexts

    def test_invalid_manifest_and_empty_local_declaration_rejected(self):
        for item in [change(dependency_review=''), change(card_ids=[]), change(card_ids=['336']), change(scope='typo')]:
            with self.assertRaises(ValueError): self.select([item])

    def test_source_mutation_and_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path = root / 'source.py'; path.write_text('before')
            manifest = {'source.py': batch.digest(path)}
            batch.verify_sources(root, manifest)
            path.write_text('after')
            with self.assertRaises(ValueError): batch.verify_sources(root, manifest)
            with self.assertRaises(ValueError): batch.verify_sources(root, {'../escape': '0' * 64})


class ExecutionTests(unittest.TestCase):
    def fake_engine(self, blocked=False):
        class Unresolved(ValueError): pass
        def compile_start(row, **kwargs):
            if blocked: raise Unresolved('unmapped_cards:336')
            return {'battle': {'first_player': 0, 'seed': kwargs['seed'], 'id': row['id']}}
        return SimpleNamespace(UnresolvedBattle=Unresolved, catalogue=lambda: None,
            derive_start_initiative=lambda *a, **k: {'candidate_first_index': 0}, compile_start=compile_start,
            simulate_batch=lambda rows: {'results': [{'winner': 0, 'hp_delta': 5, 'turns': 2,
                'used_randomness': False, 'truncated': False} for r in rows]})

    def test_all_blocked_batch_keeps_reasons_and_never_simulates_empty_input(self):
        engine = self.fake_engine(blocked=True)
        engine.simulate_batch = lambda _: self.fail('An empty executable batch must not be simulated')
        cases, excluded, _ = batch.execute_rows([row('a')], {'a': {'game_mode': 3, 'season_mec': 10}}, engine, None)
        self.assertEqual(cases, [])
        self.assertEqual(excluded[0]['reason'], 'unmapped_cards:336')

    def test_failed_settlement_not_counted_as_match_or_training_label(self):
        def reject(*_): raise ValueError('unresolved settlement')
        cases, _, _ = batch.execute_rows([row('a')], {'a': {'game_mode': 3, 'season_mec': 10}},
            self.fake_engine(), SimpleNamespace(calculate_terminal_damage=reject))
        self.assertFalse(cases[0]['all_four_match'])
        self.assertFalse(cases[0]['settlement']['resolved'])

    def test_regression_flags_previously_matching_or_executable_records(self):
        previous = {'cases': [{'record_id': 'a', 'all_four_match': True}, {'record_id': 'b', 'all_four_match': True}]}
        result = batch.compare_previous([{'record_id': 'a', 'all_four_match': False}],
                                        [{'record_id': 'b', 'reason': 'blocked'}], previous)
        self.assertEqual(result['previous_matches_lost'], ['a'])
        self.assertEqual(result['previous_executable_now_blocked'], ['b'])

    def test_partial_execution_counts_only_fresh_rows_and_full_is_explicit(self):
        rows = [row('a', 336), row('b')]
        contexts = {r['id']: {'game_mode': 3, 'season_mec': 10} for r in rows}
        changes = [change()]
        plan = {'schema': batch.SCHEMA, 'batch_id': 'test', 'pilot': 'p', 'context': 'c', 'baseline': 'b',
            'source_sha256': 'sha', 'context_sha256': 'sha', 'baseline_sha256': 'sha',
            'candidate_sources': {'placeholder': 'sha'}, 'changes': changes, 'control_count': 0,
            'selection': batch.select_records(rows, contexts, changes, control_count=0),
            'engine_module': 'engine', 'settlement_module': 'settlement'}
        engine = self.fake_engine()
        settlement = SimpleNamespace(calculate_terminal_damage=lambda *_: {'resolved': True, 'life_damage': 3})
        with patch.object(batch, 'verify_sources'), patch.object(batch, 'digest', return_value='sha'), \
             patch.object(batch, 'load_sources', return_value=(rows, contexts, {'context_sha256': 'sha', 'cases': []})), \
             patch.object(batch.importlib, 'import_module', side_effect=lambda name: engine if name == 'engine' else settlement):
            partial = batch.run_plan('.', plan)
            full = batch.run_plan('.', plan, full=True)
        self.assertEqual(partial['summary']['fresh_simulated_records'], 1)
        self.assertEqual(partial['summary']['untested_records'], 1)
        self.assertEqual(partial['summary']['cached_records_counted_as_tested'], 0)
        self.assertFalse(partial['summary']['batch_release_candidate'])
        self.assertEqual(full['summary']['fresh_simulated_records'], 2)
        self.assertTrue(full['summary']['full_development_pass'])
        self.assertFalse(full['summary']['S2_accepted'])


if __name__ == '__main__':
    unittest.main()
