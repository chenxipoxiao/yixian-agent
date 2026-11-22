from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v114 as old,full_battle_v115 as new

class CloudCatTests(unittest.TestCase):
 def test_actual_scheduler_and_attack_boundaries(self):
  r=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(new.ROOT/'tests/current_cloud_cat_v115_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  self.assertEqual(json.loads(r.stdout)['scenarios'],12)

 def test_additive_mapping_and_no_terminal_input(self):
  a=old.catalogue();b=new.catalogue()
  self.assertEqual(a[0],b[0]);self.assertEqual(a[2:],b[2:])
  self.assertEqual({k:v for k,v in b[1].items() if k not in a[1]},{403:'811501',10403:'811502',20403:'811503'})
  self.assertTrue(all(b[1][k]==v for k,v in a[1].items()))
  row,ctx=start_fixture();kw=dict(first_player=0,seed='cat-software',game_mode=3,season_mec=10,combat_context=ctx)
  self.assertEqual(old.compile_start(row,**kw),new.compile_start(row,**kw))
  for raw in [403,10403,20403]:
   row['players'][0]['candidate_start']['board'][0]=raw;saved=deepcopy(row)
   with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**kw)
   start=new.compile_start(row,**kw);self.assertEqual(saved,row)
   self.assertEqual(start['battle']['players'][0]['cards'][0],b[1][raw])
   row['outcome']={'recorded_hp_delta':9999,'winner_snapshot_slot':'p2','huiHeCount':9999}
   self.assertEqual(start,new.compile_start(row,**kw))

if __name__=='__main__':unittest.main()
