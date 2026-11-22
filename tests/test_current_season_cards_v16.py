"""Current card boundaries and full-scheduler wiring, not real-game acceptance."""
from copy import deepcopy
import json
import shutil
import subprocess
import unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v15 as old, full_battle_v16 as current
from yixian.simulator import SimulatorError


class CurrentSeasonCardsTests(unittest.TestCase):
    def compile(self,raw=0,turns=1):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=raw
        return current.compile_start(row,first_player=0,seed='software-only',game_mode=3,
            season_mec=10,combat_context=ctx,max_turns=turns)

    def test_effect_boundaries_on_native_primitives(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(current.ROOT/'tests/current_season_cards_v16_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=30)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertTrue(json.loads(p.stdout)['passed'])

    def test_all_three_grades_are_mapped_without_changing_old_mapping(self):
        a=old.catalogue()[1];b=current.catalogue()[1]
        self.assertEqual(len(b)-len(a),24);self.assertTrue(all(b[k]==v for k,v in a.items()))
        self.assertEqual(sum(len(f['cards']) for f in current.extension_contract()['families']),24)

    def test_qi_cost_is_paid_by_scheduler_before_conditional_rain_attack(self):
        battle=self.compile(7000115)['battle'];battle['players'][0].update(qi=3,activate_wood_spirit_stacks=1)
        result=current.simulate_batch([battle])['results'][0]
        self.assertEqual(result['players'][0]['qi'],2)
        self.assertEqual(result['players'][0]['hp'],50)
        self.assertTrue(any('reduced player 1 hp by 3 to 37' in line for line in result['log']))
        # The newly gained water force deals 1 more damage at this turn's end.
        self.assertEqual(result['players'][1]['hp'],36)

    def test_unaffordable_card_waits_and_has_no_effect(self):
        for raw in (4000105,4000107,7000115):
            result=current.simulate_batch([self.compile(raw)['battle']])['results'][0]
            self.assertEqual(result['players'][0]['qi'],1)
            self.assertEqual(result['players'][1]['hp'],40)
            self.assertEqual(result['players'][0]['next_card_index'],0)
            self.assertTrue(result['truncated']);self.assertIsNone(result['winner'])

    def test_zero_outcome_leak_and_input_mutation(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=7000116
        args=dict(first_player=0,seed='software-only',game_mode=3,season_mec=10,combat_context=ctx)
        prior=deepcopy(row);a=current.compile_start(row,**args);self.assertEqual(row,prior)
        row['outcome']={'recorded_hp_delta':9999,'winner_snapshot_slot':'p2'}
        self.assertEqual(a,current.compile_start(row,**args))
        row['players'][0]['candidate_start']['permanentBuffTempDatas']['999999']=1
        with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**args)

    def test_old_engine_does_not_silently_load_new_alias(self):
        battle=self.compile(7000116)['battle']
        with self.assertRaisesRegex(SimulatorError,'Unimplemented card'):old.simulate_batch([battle])

    def test_old_battle_full_output_unchanged(self):
        battle=self.compile(0,64)['battle']
        self.assertEqual(old.simulate_batch([battle])['results'],current.simulate_batch([battle])['results'])

    def test_new_battle_can_reach_terminal_without_a_training_label(self):
        result=current.simulate_batch([self.compile(7000113,64)['battle']])['results'][0]
        self.assertTrue(result['terminated']);self.assertFalse(result['truncated'])
        self.assertFalse(result['training_label_allowed']);self.assertFalse(result['legacy_destiny_settlement_applied'])

if __name__=='__main__':unittest.main()
