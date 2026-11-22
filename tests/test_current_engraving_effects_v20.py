from copy import deepcopy
import json
import shutil
import subprocess
import unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v19 as old, full_battle_v20 as current


class PostCardEngravingTests(unittest.TestCase):
    def fixture(self,slot=0):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[13006]
        ctx['players'][0]['season_engraving_input']={'origin':current.ORIGIN,
            'selected_strategy_ids':[13006],'slots':{'13006':slot}}
        return row,ctx

    def compile(self,row,ctx,**kw):
        return current.compile_start(row,first_player=0,seed='software-v20',
            game_mode=3,season_mec=10,combat_context=ctx,**kw)

    def test_native_boundaries(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(current.ROOT/'tests/current_engraving_effects_v20_probe.mjs')],
            capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr);self.assertTrue(json.loads(p.stdout)['passed'])

    def test_complete_battle_and_no_training_permission(self):
        row,ctx=self.fixture();before=deepcopy((row,ctx));compiled=self.compile(row,ctx)
        self.assertEqual((row,ctx),before)
        r=current.simulate_batch([compiled['battle']])['results'][0]
        self.assertTrue(r['terminated']);self.assertEqual(r['winner'],0)
        self.assertEqual(sum('current engraving 13006 first use' in x for x in r['log']),1)
        self.assertFalse(r['training_label_allowed'])

    def test_prior_outputs_and_old_contract_preserved(self):
        for identifier in sorted(old.SUPPORTED):
            row,ctx=self.fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[identifier]
            ctx['players'][0]['season_engraving_input']['selected_strategy_ids']=[identifier]
            ctx['players'][0]['season_engraving_input']['slots']={str(identifier):0}
            battle=self.compile(row,ctx)['battle']
            self.assertEqual(old.simulate_batch([battle])['results'],current.simulate_batch([battle])['results'])
        row,ctx=self.fixture()
        with self.assertRaisesRegex(old.UnresolvedBattle,'unsupported_season_combat:13006'):
            old.compile_start(row,first_player=0,seed='software',game_mode=3,season_mec=10,combat_context=ctx)

    def test_grid_unknown_out_of_bounds_and_ownership_reject(self):
        for value in [None,False,-1,8,'0']:
            row,ctx=self.fixture(value)
            with self.assertRaisesRegex(current.UnresolvedBattle,'engraving_preparation_slot_missing'):self.compile(row,ctx)
        row,ctx=self.fixture();ctx['players'][0]['season_engraving_input']['selected_strategy_ids']=[]
        with self.assertRaisesRegex(current.UnresolvedBattle,'engraving_preparation_ownership_mismatch'):self.compile(row,ctx)

    def test_upgrade_and_downgrade_still_unresolved(self):
        for i in [13003,13007]:
            row,ctx=self.fixture();row['players'][0]['candidate_start']['xian_mo_strategies'].append(i)
            with self.assertRaisesRegex(current.UnresolvedBattle,'unsupported_season_combat'):self.compile(row,ctx)

    def test_targets_and_replay_usage_are_not_inputs(self):
        row,ctx=self.fixture();before=self.compile(row,ctx)
        row['outcome']={'recorded_hp_delta':999,'recorded_destiny_damage':999}
        ctx['players'][0]['after_talent_counters']={'794':999,'13006':999}
        self.assertEqual(self.compile(row,ctx),before)

    def test_unresolved_nested_identity_emits_no_terminal_or_reward(self):
        row,ctx=self.fixture();valid=self.compile(row,ctx)['battle'];nested=deepcopy(valid)
        # Software-only bridge scenario: Five Elements Blossom creates
        # temporary executions. It is not a fabricated replay/actor action.
        nested['players'][0]['cards'][0]='236021';nested['players'][0]['qi']=100
        result=current.simulate_batch([nested,valid])['results']
        self.assertEqual(result[0],{'unresolved_reason':'engraving_temporary_card_identity_unresolved:13006',
                                  'training_label_allowed':False})
        self.assertEqual(result[1],current.simulate_batch([valid])['results'][0])


if __name__=='__main__':unittest.main()
