from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from tests.test_current_clouds_rain_v35 import fixture as cloud_fixture
from yixian import full_battle_v38 as old,full_battle_v39 as current
from yixian.terminal_damage_v38 import calculate_terminal_damage

class NameContextTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='name-context-software',game_mode=3,season_mec=10,combat_context=ctx)
 def fixture(self,raw=10433):
  row,ctx=cloud_fixture();row['players'][0]['candidate_start']['board'][0]=raw
  return row,ctx
 def test_native_identity_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_name_context_v39_probe_fixed.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout),{'passed':True,'scenarios':12})
 def test_legacy_full_outputs_preserved(self):
  for maker in [start_fixture,cloud_fixture]:
   row,ctx=maker();args=self.args(ctx);a=old.compile_start(row,**args);b=current.compile_start(row,**args)
   self.assertEqual(a,b);self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_real_identity_is_not_cloud_and_no_outcome_input(self):
  for raw in [433,10433,20433]:
   for first in [0,1]:
    row,ctx=self.fixture(raw);before=deepcopy(row);args=self.args(ctx,first);c=current.compile_start(row,**args)
    self.assertEqual(before,row);row['outcome']={'recorded_hp_delta':999};ctx['battle_params']=[999]
    self.assertEqual(c,current.compile_start(row,**args));r=current.simulate_batch([c['battle']])['results'][0]
    self.assertTrue(r['terminated']);event=r['clouds_rain_v35']['events'][0]
    self.assertEqual(event['board_cloud_count'],0);self.assertEqual(event['requested_qi'],1);self.assertEqual(event['player_index'],0)
    self.assertFalse(r['training_label_allowed'])
 def test_seven_stars_combination_does_not_consume_charge(self):
  row,ctx=self.fixture();row['players'][0]['candidate_start']['xian_mo_strategies'].append(7056)
  c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(r['terminated']);self.assertEqual(r['seven_stars_v37']['remaining'][0]['charges'],7)
  self.assertEqual(r['seven_stars_v37']['events'],[])
 def test_unknown_and_mismatched_runtime_still_block(self):
  row,ctx=self.fixture();b=current.compile_start(row,**self.args(ctx))['battle']
  b['clouds_rain']['players'][0]['board'][0]=20433
  r=current.simulate_batch([b])['results'][0]
  self.assertIn('raw_board_mismatch',r['unresolved_reason']);self.assertNotIn('winner',r)
  row['players'][0]['candidate_start']['board'][1]=99999999
  with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_missing_hand_or_mirror_still_blocks(self):
  for key in ['clouds_rain_hand','is_mirror']:
   row,ctx=self.fixture();ctx['players'][0].pop(key)
   with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_resource_boundary_unchanged(self):
  row,ctx=self.fixture();c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0]
  d=calculate_terminal_damage(c,r);self.assertTrue(d['resolved']);self.assertIsNone(d['authoritative_post_battle_destiny'])
  c['battle']['max_turns']=1;r=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(r['truncated']);self.assertIsNone(r['winner']);self.assertFalse(calculate_terminal_damage(c,r)['resolved'])

if __name__=='__main__':unittest.main()
