"""Combined season batch, including real engine boundaries and full software battles."""
from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from tests.test_current_sound_control_v52 import fixture as sound_fixture
from yixian import full_battle_v56 as old,full_battle_v57 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class ChaseSeasonTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='chase-season-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_chase_season_v57_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],28)
  print('V57_NATIVE_PROBE='+p.stdout.strip(),flush=True)
 def test_full_battles_both_orders_and_settlement(self):
  starts=[]
  for ids,board in [([7051],[16,0,0]),([7054],[4010026,0,0]),([7112],[16,0,0]),([7051,7054,7112],[16,0,0]),([7112,7065],[0,0,0])]:
   for first in [0,1]:
    row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['xian_mo_strategies']=ids;s['board']=board
    saved=deepcopy((row,ctx));starts.append(current.compile_start(row,**self.args(ctx,first)));self.assertEqual((row,ctx),saved)
    self.assertEqual(starts[-1]['effect_players'][0]['season_choices'],ids)
  saved=deepcopy(starts);results=current.simulate_batch([c['battle'] for c in starts])['results'];self.assertEqual(starts,saved)
  for c,b in zip(starts,results):
   self.assertTrue(b['terminated']);self.assertFalse(b['training_label_allowed']);self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
 def test_sound_scheduler_keeps_predicament_block(self):
  for first in [0,1]:
   row,ctx=sound_fixture((1005,));s=row['players'][0]['candidate_start'];s['xian_mo_strategies']+=[7051,7112];s['board']=[16,0,0]
   c=current.compile_start(row,**self.args(ctx,first));b=current.simulate_batch([c['battle']])['results'][0]
   self.assertTrue(b['terminated']);self.assertTrue(b['sound_control_v52']['events'])
   discounts=[e for e in b['chase_season_v57']['events'] if e['strategy_id']==7051]
   self.assertTrue(discounts);self.assertEqual(discounts[0]['after_cost'],0)
 def test_earlier_1009_changes_current_upgrade_target(self):
  row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['xian_mo_strategies']=[1009,7054];s['board']=[4010026,29,0]
  ctx['players'][0]['upgrade_sound_switch']={'origin':'privateData.xianMoData:preparation_switch','source_raw_sha256':row['source']['raw_sha256'],
   'selected_strategy_ids':[1009],'temp_data':{},'environment_only':True}
  c=current.compile_start(row,**self.args(ctx));b=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(b['terminated']);e=next(e for e in b['chase_season_v57']['events'] if e['strategy_id']==7054)
  self.assertEqual((e['upgrade']['slot'],e['upgrade']['from_raw'],e['upgrade']['to_raw']),(1,29,10029))
 def test_unowned_full_input_and_output_unchanged(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_old_admission_and_unsupported_combinations_stay_closed(self):
  for strategy in [7051,7054,7112]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[strategy]
   with self.subTest(strategy=strategy),self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
  for ids in [None,[True],[7051,7051],[7054,999999],[7112,7135]]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=ids
   with self.subTest(ids=ids),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_legacy_passives_stay_closed(self):
  for fate in [321,327,340]:
   row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['xian_mo_strategies']=[7051,7054,7112];s['fate_strategies']=[fate]
   with self.subTest(fate=fate),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_no_terminal_backflow(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7051,7054,7112]
  a=current.compile_start(row,**self.args(ctx));row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999}
  ctx['players'][0]['after_talent_counters']={'7112':999};self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_truncation_not_a_reward(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7051,7054,7112]
  c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1;b=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
