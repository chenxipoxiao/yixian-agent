from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v116 as old,full_battle_v117 as new

class LightningInterleavingTests(unittest.TestCase):
 def test_actual_scheduler_all_grade_and_order_boundaries(self):
  r=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(new.ROOT/'tests/current_lightning_interleaving_v117_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  self.assertEqual(json.loads(r.stdout)['scenarios'],22)
 def test_identical_start_contract_and_no_terminal_input(self):
  self.assertEqual(old.catalogue(),new.catalogue())
  row,ctx=start_fixture();kw=dict(first_player=0,seed='lightning-software',game_mode=3,season_mec=10,combat_context=ctx)
  for raw in [407,10407,20407]:
   row['players'][0]['candidate_start']['board'][0]=raw;saved=deepcopy(row)
   a=old.compile_start(row,**kw);b=new.compile_start(row,**kw)
   self.assertEqual(a,b);self.assertEqual(row,saved)
   row['outcome']={'recorded_hp_delta':9999,'winner_snapshot_slot':'p2','huiHeCount':9999}
   self.assertEqual(b,new.compile_start(row,**kw))
if __name__=='__main__':unittest.main()
