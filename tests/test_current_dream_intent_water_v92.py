from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v91 as old,full_battle_v92 as new

class DreamIntentWaterTests(unittest.TestCase):
    def compile(self,engine,row,ctx):
        return engine.compile_start(row,first_player=0,seed='v92-software',game_mode=3,season_mec=10,combat_context=ctx)
    def test_source_boundaries_and_interactions(self):
        r=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(new.ROOT/'tests/current_dream_intent_water_v92_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertEqual(json.loads(r.stdout)['scenarios'],8)
    def test_additive_catalogue_and_start_contract(self):
        a=old.catalogue()[1];b=new.catalogue()[1]
        self.assertEqual(len(b)-len(a),6);self.assertTrue(all(b[k]==v for k,v in a.items()))
        self.assertTrue(all(c['raw_id'] not in b for c in new.extension_contract()['unadmitted_high_grade_cards']))
        row,ctx=start_fixture();saved=deepcopy(row);baseline=self.compile(old,row,ctx)
        self.assertEqual(baseline,self.compile(new,row,ctx));self.assertEqual(saved,row)
        row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':9999}
        self.assertEqual(baseline,self.compile(new,row,ctx))
    def test_unaffected_whole_battle(self):
        row,ctx=start_fixture();c=self.compile(new,row,ctx)
        self.assertEqual(old.simulate_batch([c['battle']])['results'],new.simulate_batch([c['battle']])['results'])
if __name__=='__main__':unittest.main()
