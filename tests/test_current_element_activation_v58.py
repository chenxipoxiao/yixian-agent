"""Complete software battles and source-bound activation interactions, not holdout."""
from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v57 as old,full_battle_v58 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class ElementActivationTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='element-activation-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_element_activation_v58_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],30)
  print('V58_NATIVE_PROBE='+p.stdout.strip(),flush=True)
 def test_full_battles_all_innates_both_orders_and_settlement(self):
  starts=[]
  for talent in [10109,20109,30109,40109,50109]:
   for first in [0,1]:
    row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['talents']=[talent,110];s['xian_mo_strategies']=[7028,7084]
    saved=deepcopy((row,ctx));starts.append(current.compile_start(row,**self.args(ctx,first)));self.assertEqual((row,ctx),saved)
  results=current.simulate_batch([c['battle'] for c in starts])['results']
  for c,b in zip(starts,results):
   self.assertTrue(b['terminated']);self.assertFalse(b['training_label_allowed']);self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
   self.assertEqual(len([e for e in b['element_activation_v58']['events'] if e['strategy_id']==7028]),2)
 def test_no_innate_does_not_infer_from_character(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7028]
  c=current.compile_start(row,**self.args(ctx));b=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(b['terminated']);self.assertEqual(b['element_activation_v58']['events'],[])
 def test_unowned_inputs_and_full_outputs_unchanged(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7051,7054,7112];row['players'][0]['candidate_start']['board']=[16,0,0]
  a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_old_admission_and_unsupported_combinations_stay_closed(self):
  for id in [7028,7084]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[id]
   with self.subTest(id=id),self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
  for ids in [None,[True],[7028,7028],[7084,7135]]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=ids
   with self.subTest(ids=ids),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
  row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['xian_mo_strategies']=[7084];s['fate_strategies']=[411]
  with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_missing_innate_context_not_silently_empty(self):
  row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['xian_mo_strategies']=[7028];del s['talents']
  with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_no_terminal_backflow(self):
  row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['xian_mo_strategies']=[7028,7084];s['talents']=[10109]
  a=current.compile_start(row,**self.args(ctx));row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999};ctx['players'][0]['after_talent_counters']={'7028':999}
  self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_truncation_is_not_reward(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7028,7084]
  c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1;b=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
