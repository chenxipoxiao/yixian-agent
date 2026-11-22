from copy import deepcopy
import unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v11 as old, full_battle_v12 as current


class StartContextTests(unittest.TestCase):
    def compile(self,row,ctx,**extra):
        return current.compile_start(row,combat_context=ctx,game_mode=3,season_mec=10,
            seed='software-only',**extra)

    def test_skips_are_metadata_without_rewards_or_changed_combat(self):
        row,ctx=start_fixture();baseline=old.compile_start(row,combat_context=ctx,game_mode=3,season_mec=10,seed='software-only',first_player=0)
        row['players'][0]['candidate_start']['xian_mo_strategies']=[1,5,7,10,13,15,24,25]
        before=deepcopy(row);compiled=self.compile(row,ctx,first_player=0)
        self.assertEqual(compiled['battle'],baseline['battle'])
        self.assertEqual(compiled['current_start_context']['skip_records'][0],[1,5,7,10,13,15,24,25])
        self.assertEqual(compiled['effect_players'][0]['season_choices'],[1,5,7,10,13,15,24,25])
        self.assertEqual(row,before)
        self.assertEqual(current.simulate_batch([compiled['battle']])['results'],old.simulate_batch([baseline['battle']])['results'])

    def test_unknown_small_ids_and_real_unknown_effects_still_rejected(self):
        for value in [0,-1,999,1000,9999999,True]:
            row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[value]
            with self.subTest(value=value),self.assertRaises(ValueError):self.compile(row,ctx,first_player=0)

    def test_active_effect_cannot_hide_behind_skip(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7,13006]
        with self.assertRaisesRegex(ValueError,'unsupported_season_combat:13006'):self.compile(row,ctx,first_player=0)

    def test_conditional_initiative_is_independent_of_recorded_outcome(self):
        row,ctx=start_fixture();s=row['players'][1]['candidate_start']
        s['talents']=[30128];s['board']=[7000023,7000024,7000033]
        first=current.derive_start_initiative(row)
        self.assertEqual(first['candidate_first_index'],1)
        self.assertEqual(first['players'][1]['conditional_talent_components'][0]['speed'],6)
        row['outcome']={'first_player_snapshot_slot':'p1','winner_snapshot_slot':'p1','recorded_hp_delta':99999}
        self.assertEqual(first,current.derive_start_initiative(row))
        self.assertEqual(self.compile(row,ctx)['battle']['first_player'],1)

    def test_ties_remain_unresolved_and_other_engraving_logic_not_bypassed(self):
        row,ctx=start_fixture()
        self.assertIsNone(current.derive_start_initiative(row)['candidate_first_index'])
        with self.assertRaisesRegex(ValueError,'Unknown initiative'):self.compile(row,ctx)
        row['players'][0]['candidate_start']['used_keyin_cards']=[40042]
        with self.assertRaisesRegex(ValueError,'engraving_execution_pending'):self.compile(row,ctx)

    def test_projection_does_not_hide_duplicate_speed_fates(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['talents']=[128,128]
        with self.assertRaisesRegex(ValueError,'talent array'):self.compile(row,ctx,first_player=0)
