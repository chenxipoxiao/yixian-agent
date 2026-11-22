"""Source-anchored fan arithmetic, linked callbacks and complete software battles."""
from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v59 as old,full_battle_v60 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class FanQiTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='fan-qi-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_fan_qi_v60_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],25)
  print('V60_NATIVE_PROBE='+p.stdout.strip(),flush=True)
 def test_complete_fan_battles_both_orders_and_settlement(self):
  starts=[]
  for raw in [131,10131,20131]:
   for first in [0,1]:
    row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['board']=[raw,15,0];s['xian_mo_strategies']=[7059,7109]
    s['extra_max_hp_modifier']=100;row['players'][1]['candidate_start']['extra_max_hp_modifier']=100
    saved=deepcopy((row,ctx));c=current.compile_start(row,**self.args(ctx,first));self.assertEqual(c,old.compile_start(row,**self.args(ctx,first)));self.assertEqual((row,ctx),saved);starts.append(c)
  for c,b in zip(starts,current.simulate_batch([c['battle'] for c in starts])['results']):
   self.assertTrue(b['terminated']);self.assertTrue(b.get('fan_qi_v60',{}).get('events'));self.assertFalse(b['training_label_allowed'])
   self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
 def test_nonfan_results_remain_identical_including_season_callbacks(self):
  starts=[]
  for choices in [[],[7059,7109],[7064,7079]]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=choices
   a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b);starts.append(b['battle'])
  self.assertEqual(old.simulate_batch(starts)['results'],current.simulate_batch(starts)['results'])
 def test_unknowns_stay_blocked_and_outcomes_cannot_change_input(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[131,15,0]
  a=current.compile_start(row,**self.args(ctx));row['outcome']={'recorded_hp_delta':999};ctx['players'][0]['after_talent_counters']={'412':999}
  self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
  for value in [7062,7135]:
   row['players'][0]['candidate_start']['xian_mo_strategies']=[value]
   with self.subTest(id=value),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_truncation_never_settles(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[131,15,0]
  c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1;b=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
