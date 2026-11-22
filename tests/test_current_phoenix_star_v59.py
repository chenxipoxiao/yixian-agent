"""Timing interactions and complete software battles; no independent holdout."""
from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v58 as old,full_battle_v59 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class PhoenixStarTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='phoenix-star-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_phoenix_star_v59_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],23)
  print('V59_NATIVE_PROBE='+p.stdout.strip(),flush=True)
 def test_complete_battles_both_orders_round_boundary_and_settlement(self):
  starts=[]
  for round in [12,13]:
   for first in [0,1]:
    row,ctx=start_fixture();row['round']=round;row['players'][0]['candidate_start']['xian_mo_strategies']=[7064,7079]
    saved=deepcopy((row,ctx));starts.append(current.compile_start(row,**self.args(ctx,first)));self.assertEqual((row,ctx),saved)
  for c,b in zip(starts,current.simulate_batch([x['battle'] for x in starts])['results']):
   self.assertTrue(b['terminated']);self.assertFalse(b['training_label_allowed']);self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
   ev=b['phoenix_star_v59']['events'];self.assertTrue(any(e['strategy_id']==7079 for e in ev))
   if c['battle']['players'][0]['round_number']==12:self.assertFalse(any(e['strategy_id']==7064 for e in ev))
 def test_unowned_compiled_and_full_outputs_exact(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7028,7084];row['players'][0]['candidate_start']['talents']=[10109]
  a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_unknown_context_and_legacy_paths_stay_closed(self):
  for choices in [None,[True],[7064,7064],[7079,7135]]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=choices
   with self.subTest(choices=choices),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
  for id in [7064,7079]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[id]
   with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
  for fate in [344,402]:
   row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['xian_mo_strategies']=[7064,7079];s['fate_strategies']=[fate]
   with self.subTest(fate=fate),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_unknown_longma_buff_and_card_are_not_silently_ignored(self):
  for key,value in [('board',[370,0,0]),('permanentBuffTempDatas',{'708':1,'10024':6})]:
   row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['xian_mo_strategies']=[7079];s[key]=value
   with self.subTest(key=key),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_no_terminal_backflow(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7064,7079]
  a=current.compile_start(row,**self.args(ctx));row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999};ctx['players'][0]['after_talent_counters']={'7064':0}
  self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_truncation_has_no_reward(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7064,7079]
  c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1;b=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
