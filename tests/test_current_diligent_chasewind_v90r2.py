from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v89 as old,full_battle_v90r2 as new
from yixian.terminal_damage_v47 import calculate_terminal_damage
class DiligentChaseWindTests(unittest.TestCase):
    def compile(self,engine,row,ctx,first=0):
        return engine.compile_start(row,first_player=first,seed='v90r2-software',game_mode=3,season_mec=10,combat_context=ctx)
    def test_actual_trigger_and_chase_boundaries(self):
        r=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(new.ROOT/'tests/current_diligent_chasewind_v90r2_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        result=json.loads(r.stdout);self.assertTrue(result['passed']);self.assertEqual(result['scenarios'],18)
    def test_compile_unchanged_and_no_outcome_leak(self):
        for raw in [323,10323,20323,1000098,1010098,1020098]:
            row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=raw
            saved=deepcopy(row);a=self.compile(old,row,ctx);b=self.compile(new,row,ctx)
            self.assertEqual(a,b);self.assertEqual(saved,row)
            row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':9999}
            ctx['players'][0]['after_talent_counters']={'204':999}
            self.assertEqual(b,self.compile(new,row,ctx))
    def test_unaffected_full_battle_identical(self):
        row,ctx=start_fixture();c=self.compile(new,row,ctx)
        self.assertEqual(old.simulate_batch([c['battle']])['results'],new.simulate_batch([c['battle']])['results'])
    def test_full_diligent_battles_finite_and_settlement(self):
        cases=[]
        for first in [0,1]:
            row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[323,1000001,1000002]
            cases.append(self.compile(new,row,ctx,first))
        for c,r in zip(cases,new.simulate_batch([c['battle'] for c in cases])['results']):
            self.assertTrue(r['terminated']);self.assertFalse(r['truncated']);self.assertFalse(r['training_label_allowed'])
            self.assertNotIn('NaN','\n'.join(r['log']));self.assertTrue(calculate_terminal_damage(c,r)['resolved'])
    def test_missing_and_unknown_still_blocked(self):
        for key,value in [('talents',None),('board',[323,999999999,0]),('permanentBuffTempDatas',{'591':1})]:
            row,ctx=start_fixture();row['players'][0]['candidate_start'][key]=value
            with self.assertRaises((new.UnresolvedBattle,ValueError)):self.compile(new,row,ctx)
if __name__=='__main__':unittest.main()
