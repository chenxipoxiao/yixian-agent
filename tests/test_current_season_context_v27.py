from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v26 as old,full_battle_v27 as current

class SeasonContextTests(unittest.TestCase):
    def args(self,ctx,first=0):
        return dict(first_player=first,seed='season-context-software',game_mode=3,season_mec=10,combat_context=ctx)

    def test_native_boundaries(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(current.ROOT/'tests/current_season_context_v27_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout),{'passed':True,'scenarios':48})

    def test_no_ownership_exact_regression(self):
        row,ctx=start_fixture();a=self.args(ctx)
        x=old.compile_start(row,**a);self.assertEqual(x,current.compile_start(row,**a))
        self.assertEqual(old.simulate_batch([x['battle']])['results'],current.simulate_batch([x['battle']])['results'])

    def test_start_input_and_outcomes_never_mutated(self):
        row,ctx=start_fixture();row['players'][1]['candidate_start']['xian_mo_strategies']=[23080,3001]
        original=deepcopy(row);r=current.compile_start(row,**self.args(ctx,1))
        self.assertEqual(row,original);self.assertEqual(r['battle']['season_current_context'],{'players':[[],[23080,3001]]})
        self.assertEqual(r['effect_players'][1]['season_choices'],[23080,3001])
        self.assertEqual(r['battle']['players'][1]['cultivation'],4)
        row['outcome']={'winner':0,'hp_delta':999};self.assertEqual(r,current.compile_start(row,**self.args(ctx,1)))
        self.assertFalse(r['training_label_allowed'])

    def test_missing_duplicate_and_unknowns_rejected(self):
        for choices in ([3001,3001],[23080,23080],[3001,16024],[23080,999999],None):
            row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=choices
            with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))

    def test_both_actors_open_once_and_full_battle_terminates(self):
        row,ctx=start_fixture()
        for p in row['players']:p['candidate_start']['xian_mo_strategies']=[3001]
        for first in (0,1):
            c=current.compile_start(row,**self.args(ctx,first));r=current.simulate_batch([c['battle']])['results'][0]
            self.assertTrue(r['terminated']);events=r['season_context_v27']['events']
            self.assertEqual([e['player_index'] for e in events],[first,1-first])
            self.assertEqual(len(events),2);self.assertFalse(r['used_randomness'])

    def test_bridge_bad_ownership_rejected(self):
        row,ctx=start_fixture();b=current.compile_start(row,**self.args(ctx))['battle']
        for bad in ({'players':[[3001,3001],[]]},{'players':[[16024],[]]}):
            b['season_current_context']=bad
            with self.assertRaisesRegex(current.SimulatorError,'ownership'):current.simulate_batch([b])

    def test_source_rules_and_no_preparation_rewards(self):
        f=current.extension_contract();self.assertEqual(f['version'],'001.0008.0005')
        self.assertEqual(f['dragon_awe']['amount'],1)
        self.assertEqual(f['generating_formation']['order'],['earth','water','fire','wood','wood_forceage','metal'])
        self.assertFalse(f['training_label_allowed'])

if __name__=='__main__':unittest.main()
