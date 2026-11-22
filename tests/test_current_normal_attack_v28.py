from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v27 as old,full_battle_v28 as current

class NormalAttackTests(unittest.TestCase):
    def args(self,ctx,first=0):
        return dict(first_player=first,seed='normal-attack-software',game_mode=3,season_mec=10,combat_context=ctx)

    def test_native_boundaries(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(current.ROOT/'tests/current_normal_attack_v28_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout),{'passed':True,'scenarios':32})

    def test_no_ownership_complete_regression(self):
        row,ctx=start_fixture();a=self.args(ctx)
        c=old.compile_start(row,**a);self.assertEqual(c,current.compile_start(row,**a))
        self.assertEqual(old.simulate_batch([c['battle']])['results'],current.simulate_batch([c['battle']])['results'])

    def test_ownership_and_outcome_isolation(self):
        row,ctx=start_fixture();row['players'][1]['candidate_start']['xian_mo_strategies']=[5011,5004]
        before=deepcopy(row);c=current.compile_start(row,**self.args(ctx,1));self.assertEqual(before,row)
        self.assertEqual(c['battle']['season_normal_attack'],{'players':[[],[5011,5004]]})
        self.assertEqual(c['effect_players'][1]['season_choices'],[5011,5004])
        row['outcome']={'winner':1,'hp_delta':9999};self.assertEqual(c,current.compile_start(row,**self.args(ctx,1)))
        self.assertFalse(c['training_label_allowed'])

    def test_unknown_and_duplicate_context_rejected(self):
        for choices in ([5011,5011],[5004,5004],[5011,5001],None):
            row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=choices
            with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))

    def test_both_players_terminal_and_single_consumption(self):
        row,ctx=start_fixture()
        for p in row['players']:p['candidate_start']['xian_mo_strategies']=[5011,5004]
        for first in (0,1):
            c=current.compile_start(row,**self.args(ctx,first));r=current.simulate_batch([c['battle']])['results'][0]
            self.assertTrue(r['terminated']);self.assertFalse(r['training_label_allowed']);self.assertFalse(r['used_randomness'])
            events=r['normal_attack_v28']['events']
            self.assertEqual(sorted(e['player_index'] for e in events if e['effect_id']==5011),[0,1])
            self.assertGreater(len([e for e in events if e['effect_id']==5004]),2)

    def test_prior_season_extensions_preserved_when_combined(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[3001,5011]
        c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0]
        self.assertTrue(r['terminated']);self.assertEqual(r['season_context_v27']['events'][0]['effect_id'],3001)
        self.assertEqual(r['normal_attack_v28']['events'][0]['effect_id'],5011)

    def test_bridge_bad_ownership_rejected(self):
        row,ctx=start_fixture();c=current.compile_start(row,**self.args(ctx))['battle']
        for bad in ({'players':[[5011,5011],[]]},{'players':[[5001],[]]}):
            c['season_normal_attack']=bad
            with self.assertRaisesRegex(current.SimulatorError,'ownership'):current.simulate_batch([c])

    def test_fixed_rule_values(self):
        f=current.extension_contract();self.assertEqual(f['version'],'001.0008.0005')
        self.assertEqual(f['footwork']['agility'],14);self.assertTrue(f['footwork']['repeats'])
        self.assertEqual((f['acupoint']['weaken'],f['acupoint']['decrease_atk']),(3,1))
        self.assertTrue(f['acupoint']['current_attack_executes']);self.assertFalse(f['training_label_allowed'])

if __name__=='__main__':unittest.main()
