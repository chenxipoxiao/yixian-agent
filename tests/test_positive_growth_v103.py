from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v102 as old,full_battle_v103 as new
class PositiveGrowthTests(unittest.TestCase):
 def test_native_callbacks_and_order(self):
  r=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(new.ROOT/'tests/positive_growth_v103_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=90)
  self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertEqual(json.loads(r.stdout)['scenarios'],12)
 def test_ownership_no_opening_reward_or_outcome(self):
  row,ctx=start_fixture();kw=dict(first_player=0,seed='growth-software',game_mode=3,season_mec=10,combat_context=ctx)
  baseline=old.compile_start(row,**kw);self.assertEqual(baseline,new.compile_start(row,**kw))
  row['players'][0]['candidate_start']['xian_mo_strategies'].append(7076);saved=deepcopy(row)
  with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**kw)
  got=new.compile_start(row,**kw);self.assertEqual(row,saved);self.assertEqual(got['battle']['players'],baseline['battle']['players'])
  self.assertEqual(got['battle']['positive_growth'],{'players':[True,False]})
  self.assertIn(7076,got['effect_players'][0]['season_choices'])
  row['outcome']={'recorded_hp_delta':99999,'winner_snapshot_slot':'p2'};self.assertEqual(got,new.compile_start(row,**kw))
  row['players'][0]['candidate_start']['xian_mo_strategies'].append(7053)
  with self.assertRaisesRegex(new.UnresolvedBattle,'yan_qi_combination_pending'):new.compile_start(row,**kw)
 def test_unknown_permanent_and_duplicate_not_erased(self):
  row,ctx=start_fixture();kw=dict(first_player=0,seed='growth-software',game_mode=3,season_mec=10,combat_context=ctx)
  p=row['players'][0]['candidate_start'];p['xian_mo_strategies']=[7076,7076]
  with self.assertRaisesRegex(new.UnresolvedBattle,'unique_ownership'):new.compile_start(row,**kw)
  p['xian_mo_strategies']=[7076];p['permanentBuffTempDatas']['10025']=1
  with self.assertRaisesRegex(new.UnresolvedBattle,'10025'):new.compile_start(row,**kw)
if __name__=='__main__':unittest.main()
