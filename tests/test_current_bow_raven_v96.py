from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v95 as old,full_battle_v96 as new
class BowRavenTests(unittest.TestCase):
 def test_real_card_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(new.ROOT/'tests/current_bow_raven_v96_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(json.loads(p.stdout)['scenarios'],42)
 def test_inputs_and_catalogue_preserved(self):
  self.assertEqual(old.catalogue(),new.catalogue())
  for raw in [260,10260,20260,4000097,4010097,4020097]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=raw;saved=deepcopy(row)
   kw=dict(first_player=0,seed='bow-raven-software',game_mode=3,season_mec=10,combat_context=ctx)
   a=old.compile_start(row,**kw);self.assertEqual(a,new.compile_start(row,**kw));self.assertEqual(saved,row)
   row['outcome']={'recorded_hp_delta':9999,'winner_snapshot_slot':'p2'};self.assertEqual(a,new.compile_start(row,**kw))
if __name__=='__main__':unittest.main()
