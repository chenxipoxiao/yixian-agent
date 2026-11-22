from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v51r2 as old,full_battle_v52r2 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

def fixture(ids=(1003,1005,1007),switch=0):
 row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=list(ids)
 ctx['players'][0]['sound_control_switch']={'origin':'privateData.xianMoData:preparation_switch',
  'source_raw_sha256':row['source']['raw_sha256'],'selected_strategy_ids':sorted(set(ids)&{1003,1005,1007}),
  'temp_data':{} if switch is None else {str(i):switch for i in ids if i in [1003,1005,1007]},'environment_only':True}
 return row,ctx

class SoundControlTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='sound-control-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundaries_and_interactions(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_sound_control_v52r2_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],20)
 def test_batch_complete_battles_and_settlement_both_orders(self):
  compiled=[]
  for ids in [(1003,),(1005,),(1007,),(1003,1005,1007)]:
   for first in [0,1]:
    row,ctx=fixture(ids);saved=deepcopy((row,ctx));c=current.compile_start(row,**self.args(ctx,first))
    self.assertEqual(saved,(row,ctx));self.assertEqual(c['effect_players'][0]['season_choices'],list(ids));compiled.append(c)
  before=deepcopy(compiled);results=current.simulate_batch([c['battle'] for c in compiled])['results'];self.assertEqual(before,compiled)
  for c,b in zip(compiled,results):
   self.assertTrue(b['terminated']);self.assertFalse(b['used_randomness']);self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
   self.assertFalse(b['training_label_allowed']);self.assertTrue(b['sound_control_v52']['events'])
 def test_explicit_switch_semantics(self):
  for value in [None,0,-1,1,2147483647,-2147483648]:
   row,ctx=fixture(switch=value);c=current.compile_start(row,**self.args(ctx))
   self.assertEqual([e['enabled'] for e in c['battle']['sound_control']['players'][0]],[value in [None,0]]*3)
 def test_missing_and_invalid_context_rejected(self):
  for change in ['missing','map','source','choices','origin','boolean','foreign_key']:
   row,ctx=fixture();entry=ctx['players'][0]['sound_control_switch']
   if change=='missing':del ctx['players'][0]['sound_control_switch']
   elif change=='map':del entry['temp_data']
   elif change=='source':entry['source_raw_sha256']='other'
   elif change=='choices':entry['selected_strategy_ids']=[]
   elif change=='origin':entry['origin']='after_battle'
   elif change=='boolean':entry['temp_data']={'1003':True}
   else:entry['temp_data']={'1009':0}
   with self.subTest(change=change),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_frozen_old_interface_and_case(self):
  for id in [1003,1005,1007]:
   row,ctx=fixture((id,))
   with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_no_terminal_backflow(self):
  row,ctx=fixture();a=current.compile_start(row,**self.args(ctx));row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999}
  ctx['battle_params']=[281,999];ctx['players'][0]['after_talent_counters']={'281':999,'561':999}
  self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_unknown_effects_and_duplicates_stay_blocked(self):
  for ids in [[1007,1007],[1005,999999],[1003,5009]]:
   row,ctx=fixture(ids)
   with self.subTest(ids=ids),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_truncation_not_a_result(self):
  row,ctx=fixture();c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
  b=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
