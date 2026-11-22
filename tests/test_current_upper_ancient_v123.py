from copy import deepcopy
import ast,json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v122r2 as old,full_battle_v123 as new

class UpperAncientTests(unittest.TestCase):
 def test_current_force_boundaries(self):
  r=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(new.ROOT/'tests/current_upper_ancient_v123_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  self.assertEqual(json.loads(r.stdout)['scenarios'],16)

 def test_leaf_delta_and_original_start_preserved(self):
  before=(new.ROOT/'yixian/full_battle.py').read_text('utf8')
  after=(new.ROOT/'yixian/full_battle_base_v123.py').read_text('utf8')
  self.assertEqual(after.replace('            if f==7120:continue  # Executed by the explicit v123 runtime owner context.\n',''),before)
  self.assertEqual(old.catalogue(),new.catalogue())
  row,ctx=start_fixture();kw=dict(first_player=0,seed='upper-ancient-software',game_mode=3,season_mec=10,combat_context=ctx)
  self.assertEqual(old.compile_start(row,**kw),new.compile_start(row,**kw))
  row['players'][0]['candidate_start']['xian_mo_strategies']=[7120];saved=deepcopy(row)
  with self.assertRaisesRegex(old.UnresolvedBattle,'unsupported_season_combat:7120'):old.compile_start(row,**kw)
  result=new.compile_start(row,**kw);self.assertEqual(row,saved)
  self.assertEqual(result['effect_players'][0]['season_choices'],[7120]);self.assertEqual(result['battle']['upper_ancient'],{'players':[True,False]})
  self.assertNotIn('max_force',result['battle']['players'][0])
  row['outcome']={'winner':'p2','hp_delta':999,'turns':999};self.assertEqual(result,new.compile_start(row,**kw))
  with self.assertRaisesRegex(old.UnresolvedBattle,'unsupported_season_combat:7120'):old.compile_start(row,**kw)
  row['players'][0]['candidate_start']['xian_mo_strategies']=[7120,999999]
  with self.assertRaises(old.UnresolvedBattle):new.compile_start(row,**kw)
  row['players'][0]['candidate_start']['xian_mo_strategies']=[7120,7120]
  with self.assertRaisesRegex(old.UnresolvedBattle,'explicit_unique_ownership'):new.compile_start(row,**kw)

if __name__=='__main__':unittest.main()
