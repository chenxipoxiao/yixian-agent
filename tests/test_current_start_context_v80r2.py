"""Input-boundary regression and full software battles; no replay acceptance."""
from copy import deepcopy
import unittest
from tests.test_full_battle import start_fixture
from tests.test_current_falling_paper_v45 import certify
from yixian import full_battle_v79r2 as old, full_battle_v80 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage


def fixture(paper=True, vase=False, branch=0):
    row, ctx = start_fixture()
    row['game_id'] = 'software-v80'
    for p in ctx['players']:
        p['start_extensions'] = {'origin': 'publicData.lastRoundData', 'talentDatas': {}, 'privateTalentDatas': {}}
    if vase:
        row['players'][0]['candidate_start']['talents'] = [199]
        ctx['players'][0]['start_extensions']['privateTalentDatas']['199'] = {'commonParams': [7010009, 7000004, 7000109]}
    if paper:
        row['players'][0]['candidate_start']['xian_mo_strategies'] = [16024]
        row['players'][1]['candidate_start']['xian_mo_strategies'] = [7059]
        ctx['battle_params'] = [branch]
        certify(row, ctx)
    return row, ctx


class StartContextTests(unittest.TestCase):
    def args(self, ctx, first=0):
        return dict(combat_context=ctx, first_player=first, game_mode=3, season_mec=10, seed='software-v80')

    def test_projection_error_repaired_without_mutating_source(self):
        for maker in [lambda: fixture(), lambda: fixture(False, True), lambda: fixture(True, True)]:
            row, ctx = maker(); saved = deepcopy((row, ctx))
            with self.assertRaises(old.UnresolvedBattle): old.compile_start(row, **self.args(ctx))
            c = current.compile_start(row, **self.args(ctx))
            self.assertEqual(saved, (row, ctx))
            self.assertEqual(c['effect_players'][0]['fates'], row['players'][0]['candidate_start']['talents'])
            self.assertEqual(c['effect_players'][1]['season_choices'], row['players'][1]['candidate_start']['xian_mo_strategies'])
            self.assertFalse(c['start_context_v80']['training_label_allowed'])

    def test_original_binding_checked_before_projection(self):
        for kind in ['board', 'exp', 'ownership', 'context', 'source', 'round', 'id', 'raw_vase']:
            row, ctx = fixture(True, True)
            if kind == 'board': row['players'][0]['candidate_start']['board'][0] = 1000001
            if kind == 'exp': row['players'][1]['candidate_start']['exp'] += 1
            if kind == 'ownership': row['players'][1]['candidate_start']['xian_mo_strategies'] = []
            if kind == 'context': ctx['players'][0]['hand_count'] += 1
            if kind == 'source': ctx['source_raw_sha256'] = 'changed'
            if kind == 'round': row['round'] += 1
            if kind == 'id': row['id'] = 'changed'
            if kind == 'raw_vase': ctx['players'][0]['start_extensions']['privateTalentDatas']['199']['commonParams'][2] = 0
            with self.subTest(kind=kind), self.assertRaisesRegex(current.UnresolvedBattle, 'snapshot_binding_mismatch'):
                current.compile_start(row, **self.args(ctx))

    def test_projected_snapshot_hash_cannot_replace_original_hash(self):
        row, ctx = fixture(); projected = deepcopy(row)
        projected['players'][1]['candidate_start']['xian_mo_strategies'] = []
        ctx['falling_paper_record']['snapshot_sha256'] = current.paper.snapshot_binding(projected, ctx)
        with self.assertRaisesRegex(current.UnresolvedBattle, 'snapshot_binding_mismatch'):
            current.compile_start(row, **self.args(ctx))

    def test_complete_parameter_evidence_remains_required(self):
        for params in [[], [0, 1], [4], [True], [1], None]:
            row, ctx = fixture(); ctx['battle_params'] = params
            with self.subTest(params=params), self.assertRaises(current.UnresolvedBattle):
                current.compile_start(row, **self.args(ctx))

    def test_full_battles_cover_both_initiatives_and_vase_read_slot(self):
        compiled = []
        for first in [0, 1]:
            for branch in range(4):
                row, ctx = fixture(True, True, branch)
                compiled.append(current.compile_start(row, **self.args(ctx, first)))
        results = current.simulate_batch([c['battle'] for c in compiled])['results']
        for c, result in zip(compiled, results):
            self.assertTrue(result.get('terminated'), result)
            self.assertEqual(result['falling_paper_v45']['consumed'], 1)
            self.assertTrue(result['used_randomness'])
            self.assertTrue(calculate_terminal_damage(c, result)['resolved'])
            self.assertFalse(result['training_label_allowed'])
            self.assertEqual(c['battle']['players'][0]['five_elements_pure_vase_cards'], ['131032', '131021', None])
            self.assertEqual(c['start_context_v80']['vase_projections'][0]['raw_slots'], [7010009, 7000004, 7000109])

    def test_final_compiled_battle_is_bound_including_new_opening_effect(self):
        row, ctx = fixture(); c = current.compile_start(row, **self.args(ctx))
        self.assertIn('opening_qi', c['battle'])
        modified = []
        for change in ['hp', 'opening', 'first', 'board']:
            b = deepcopy(c['battle'])
            if change == 'hp': b['players'][0]['hp'] -= 1
            if change == 'opening': b['opening_qi']['players'][1] = [7005]
            if change == 'first': b['first_player'] = 1
            if change == 'board': b['players'][0]['cards'][0] = '111011'
            modified.append(b)
        for result in current.simulate_batch(modified)['results']:
            self.assertIn('compiled_battle_binding_mismatch', result['unresolved_reason'])
            self.assertNotIn('winner', result)

    def test_vase_unknown_and_first_unmapped_are_rejected(self):
        for slots in [[7000109, 7000004, 0], [7010009, 9999999, 7000109], [7010009, 7000109], [None, 0, 7000109]]:
            row, ctx = fixture(False, True)
            ctx['players'][0]['start_extensions']['privateTalentDatas']['199']['commonParams'] = slots
            with self.subTest(slots=slots), self.assertRaises(current.UnresolvedBattle):
                current.compile_start(row, **self.args(ctx))

    def test_vase_missing_context_and_unreviewed_interactions_rejected(self):
        for mode in ['missing', 'wrong-origin', '23058', '7085', 'unknown_fate', 'mirror']:
            row, ctx = fixture(False, True)
            if mode == 'missing': del ctx['players'][0]['start_extensions']
            if mode == 'wrong-origin': ctx['players'][0]['start_extensions']['origin'] = 'after_battle'
            if mode in ['23058', '7085']: row['players'][0]['candidate_start']['xian_mo_strategies'] = [int(mode)]
            if mode == 'unknown_fate': row['players'][1]['candidate_start']['talents'] = [999999]
            if mode == 'mirror': ctx['players'][1]['is_mirror'] = True
            with self.subTest(mode=mode), self.assertRaises(current.UnresolvedBattle):
                current.compile_start(row, **self.args(ctx))

    def test_explicit_empty_first_slot_is_not_shifted(self):
        row, ctx = fixture(False, True)
        ctx['players'][0]['start_extensions']['privateTalentDatas']['199']['commonParams'] = [0, 7010009, 7000109]
        c = current.compile_start(row, **self.args(ctx))
        self.assertEqual(c['battle']['players'][0]['five_elements_pure_vase_cards'], [None, '131032', None])

    def test_outcomes_and_after_state_are_not_input(self):
        row, ctx = fixture(True, True); before = current.compile_start(row, **self.args(ctx))
        row['outcome'] = {'recorded_hp_delta': 999, 'winner_snapshot_slot': 'p2'}
        ctx['players'][0]['after_talent_counters'] = {'199': {'commonParams': [0, 0, 0]}}
        self.assertEqual(before, current.compile_start(row, **self.args(ctx)))

    def test_already_executable_outputs_unchanged(self):
        for variant in ['none', 'paper', 'mapped_vase']:
            row, ctx = fixture(variant == 'paper', variant == 'mapped_vase')
            if variant == 'paper':
                row['players'][1]['candidate_start']['xian_mo_strategies'] = []; certify(row, ctx)
            if variant == 'mapped_vase': ctx['players'][0]['start_extensions']['privateTalentDatas']['199']['commonParams'][2] = 0
            self.assertEqual(old.compile_start(row, **self.args(ctx)), current.compile_start(row, **self.args(ctx)))


if __name__ == '__main__': unittest.main()
