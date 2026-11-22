from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v50r2 as old,full_battle_v51 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

def fixture(ids=(1002,3002,7105),switch=0):
 row,ctx=start_fixture()
 row['players'][0]['character_id']=4000003
 row['players'][0]['candidate_start']['xian_mo_strategies']=list(ids)
 if 1002 in ids:
  ctx['players'][0]['wild_dance_switch']={'origin':'privateData.xianMoData:preparation_switch',
   'source_raw_sha256':row['source']['raw_sha256'],'selected_strategy_ids':[1002],
   'temp_data':{} if switch is None else {'1002':switch},'environment_only':True}
 return row,ctx

class SeasonOpeningBatchTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='season-opening-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_interaction_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_season_opening_v51_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],20)
 def test_entire_batch_and_each_effect_complete_both_orders(self):
  compiled=[]
  for ids in [(1002,),(3002,),(7105,),(1002,3002,7105)]:
   for first in [0,1]:
    row,ctx=fixture(ids);saved=deepcopy((row,ctx));c=current.compile_start(row,**self.args(ctx,first))
    self.assertEqual(saved,(row,ctx));self.assertEqual(c['effect_players'][0]['season_choices'],list(ids));compiled.append(c)
  before=deepcopy(compiled);results=current.simulate_batch([c['battle'] for c in compiled])['results'];self.assertEqual(before,compiled)
  for c,b in zip(compiled,results):
   self.assertTrue(b['terminated']);self.assertFalse(b['used_randomness']);self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
   self.assertFalse(b['training_label_allowed']);self.assertTrue(b['season_opening_v51']['events'])
 def test_switch_zero_absent_and_signed_disabled(self):
  for value in [None,0,-1,1,2147483647,-2147483648]:
   row,ctx=fixture((1002,),value);c=current.compile_start(row,**self.args(ctx))
   self.assertEqual(c['battle']['season_opening_batch']['players'][0],[{'strategy_id':1002,'enabled':value in [None,0]}])
 def test_missing_switch_whole_map_source_and_choice_rejected(self):
  for change in ['missing','map','source','choices','origin','boolean']:
   row,ctx=fixture();entry=ctx['players'][0]['wild_dance_switch']
   if change=='missing':del ctx['players'][0]['wild_dance_switch']
   elif change=='map':del entry['temp_data']
   elif change=='source':entry['source_raw_sha256']='other'
   elif change=='choices':entry['selected_strategy_ids']=[]
   elif change=='origin':entry['origin']='after_battle'
   else:entry['temp_data']={'1002':True}
   with self.subTest(change=change),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_acquired_maximum_hp_not_reapplied(self):
  row,ctx=fixture((3002,));row['players'][0]['candidate_start']['extra_max_hp_modifier']=4
  c=current.compile_start(row,**self.args(ctx));self.assertEqual((c['battle']['players'][0]['hp'],c['battle']['players'][0]['max_hp']),(44,44))
  b=current.simulate_batch([c['battle']])['results'][0];event=b['season_opening_v51']['events'][0]
  self.assertEqual(event['after'][0]['max_hp'],44);self.assertEqual(event['after'][0]['guard_up'],1)
 def test_old_compiler_stays_closed_and_old_battle_exact(self):
  for id in [1002,3002,7105]:
   row,ctx=fixture((id,))
   with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_extreme_metal_battle_with_guard(self):
  row,ctx=fixture((3002,));row['players'][0]['candidate_start']['board']=[7010108,0,0]
  c=current.compile_start(row,**self.args(ctx));b=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(b['terminated']);self.assertTrue(b['chase_cards_v50r2']['events']);self.assertEqual(b['season_opening_v51']['events'][0]['after'][0]['guard_up'],1)
 def test_outcomes_and_after_state_cannot_change_input(self):
  row,ctx=fixture();before=current.compile_start(row,**self.args(ctx));row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999}
  ctx['battle_params']=[367,999];ctx['players'][0]['after_talent_counters']={'367':999,'5':999}
  self.assertEqual(before,current.compile_start(row,**self.args(ctx)))
 def test_unknown_content_and_duplicates_still_reject(self):
  for ids in [[3002,3002],[7105,999999],[1002,5009]]:
   row,ctx=fixture(ids)
   with self.subTest(ids=ids),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_truncation_not_a_winner(self):
  row,ctx=fixture();c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
  b=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
