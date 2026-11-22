from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v75 as old,full_battle_v76 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class SeasonWaterTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='season-water-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_order_and_damage_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_season_water_v76_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],25);print('V76_NATIVE_PROBE='+p.stdout.strip(),flush=True)
 def test_complete_battles_for_both_seats_rounds_and_effects(self):
  starts=[]
  for ids in [[3012],[7032],[3012,7032]]:
   for round_number in [12,13]:
    for first in [0,1]:
     row,ctx=start_fixture();row['round']=round_number;row['players'][0]['candidate_start']['xian_mo_strategies']=ids
     if 7032 in ids:row['players'][0]['candidate_start']['board'][0]=20
     starts.append(current.compile_start(row,**self.args(ctx,first)))
  saved=deepcopy(starts);bs=current.simulate_batch([c['battle'] for c in starts])['results'];self.assertEqual(saved,starts)
  for c,b in zip(starts,bs):
   self.assertTrue(b.get('terminated'),b);self.assertFalse(b['training_label_allowed']);self.assertFalse(b['used_randomness']);self.assertTrue(calculate_terminal_damage(c,b)['resolved']);self.assertIn('season_water_v76',b)
 def test_restores_season_ownership_and_input_is_immutable(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[3012,7032];saved=deepcopy((row,ctx));c=current.compile_start(row,**self.args(ctx));self.assertEqual(saved,(row,ctx));self.assertEqual(c['effect_players'][0]['season_choices'],[3012,7032]);self.assertEqual(c['battle']['season_water']['players'],[[3012,7032],[]])
  row['outcome']={'recorded_hp_delta':999,'winner_snapshot_slot':'p2'};self.assertEqual(c,current.compile_start(row,**self.args(ctx)))
 def test_old_adapter_keeps_rejecting_new_ownership(self):
  for id in [3012,7032]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[id]
   with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
 def test_nonowners_identical_full_output(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b);self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_missing_duplicate_and_unknown_choices_stay_blocked(self):
  for choices in [None,[7032,7032],[7032,999999]]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=choices
   with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_truncated_battle_has_no_settlement(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7032];c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1;b=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
