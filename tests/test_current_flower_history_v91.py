from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v90r2 as old,full_battle_v91 as new

class FlowerHistoryTests(unittest.TestCase):
    def compile(self,engine,row,ctx):
        return engine.compile_start(row,first_player=0,seed='v91-software',game_mode=3,season_mec=10,combat_context=ctx)
    def test_nonadjacent_water_and_chase_boundaries(self):
        r=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(new.ROOT/'tests/current_flower_history_v91_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertEqual(json.loads(r.stdout)['scenarios'],8)
    def test_start_contract_and_no_outcome_input(self):
        row,ctx=start_fixture();saved=deepcopy(row)
        a=self.compile(old,row,ctx);self.assertEqual(a,self.compile(new,row,ctx));self.assertEqual(row,saved)
        row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':9999};ctx['players'][0]['after_talent_counters']={'766':999}
        self.assertEqual(a,self.compile(new,row,ctx))
        row['players'][0]['candidate_start']['permanentBuffTempDatas']['766']=1
        with self.assertRaises((new.UnresolvedBattle,ValueError)):self.compile(new,row,ctx)
    def test_unaffected_full_battle_unchanged(self):
        row,ctx=start_fixture();c=self.compile(new,row,ctx)
        self.assertEqual(old.simulate_batch([c['battle']])['results'],new.simulate_batch([c['battle']])['results'])
if __name__=='__main__':unittest.main()
