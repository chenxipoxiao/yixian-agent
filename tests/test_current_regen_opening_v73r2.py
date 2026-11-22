from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v72 as old,full_battle_v73 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

def bind(row,ctx,i=0,temp=None):
 ctx['players'][i]['regen_opening_switch']={'origin':'privateData.xianMoData:preparation_switch',
  'selected_strategy_ids':[7135],'temp_data':{'7135':0} if temp is None else temp,
  'source_raw_sha256':row['source']['raw_sha256'],'environment_only':True,
  'record_id':row['id'],'round':row['round'],'snapshot_slot':row['players'][i]['snapshot_slot']}

class RegenOpeningTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='regen-opening-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_regen_opening_v73r2_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertEqual(len(r['names']),r['scenarios']);self.assertGreaterEqual(r['scenarios'],25);print('V73_NATIVE_PROBE='+p.stdout.strip(),flush=True)
 def test_complete_battles_orders_and_settlement(self):
  starts=[]
  for ids in [[7103],[7135],[7103,7135],[7103,15018],[1006,7103]]:
   for first in [0,1]:
    row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=ids;ctx['players'][0]['hand_count']=1
    if 7135 in ids:bind(row,ctx)
    if 1006 in ids:ctx['players'][0]['killing_sound_switch']={'origin':'privateData.xianMoData:preparation_switch','source_raw_sha256':row['source']['raw_sha256'],'environment_only':True,'selected_strategy_ids':[1006],'temp_data':{'1006':0}}
    c=current.compile_start(row,**self.args(ctx,first));self.assertEqual(c['effect_players'][0]['season_choices'],ids);starts.append(c)
  saved=deepcopy(starts);results=current.simulate_batch([c['battle'] for c in starts])['results'];self.assertEqual(starts,saved)
  for c,b in zip(starts,results):
   self.assertTrue(b['terminated'],b);self.assertFalse(b['used_randomness']);self.assertTrue(calculate_terminal_damage(c,b)['resolved']);self.assertFalse(b['training_label_allowed'])
   events=b['regen_opening_v73']['events'];ids=c['effect_players'][0]['season_choices']
   if 7103 in ids:
    e=next(e for e in events if e['strategy_id']==7103);self.assertEqual(e['requested'],e['before']['hp']//10)
   if 7135 in ids:self.assertTrue(next(e for e in events if e['strategy_id']==7135)['enabled'])
 def test_switch_values_and_old_gate(self):
  for temp,enabled in [({},True),({'7135':0},True),({'7135':1},False),({'7135':-1},False)]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7135];bind(row,ctx,temp=temp)
   with self.subTest(temp=temp):
    self.assertEqual(current.compile_start(row,**self.args(ctx))['battle']['regen_opening']['players'][0][0]['enabled'],enabled)
    with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
 def test_unknown_switch_does_not_default_to_enabled(self):
  for change in ['missing','map','hash','record','round','slot','environment','choices','bool','extra']:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7135];bind(row,ctx);x=ctx['players'][0]['regen_opening_switch']
   if change=='missing':del ctx['players'][0]['regen_opening_switch']
   elif change=='map':x.pop('temp_data')
   elif change=='hash':x['source_raw_sha256']='wrong'
   elif change=='record':x['record_id']='wrong'
   elif change=='round':x['round']=99
   elif change=='slot':x['snapshot_slot']='p2'
   elif change=='environment':x['environment_only']=False
   elif change=='choices':x['selected_strategy_ids']=[7135,7135]
   elif change=='bool':x['temp_data']={'7135':False}
   else:x['temp_data']={'7135':0,'1006':0}
   with self.subTest(change=change),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_unrelated_rules_remain_blocked(self):
  for ids in [[7103,7103],[7135,7135],[7103,7062],[7135,1010]]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=ids;bind(row,ctx)
   with self.subTest(ids=ids),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_nonowner_and_inputs_unchanged(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
  row['players'][0]['candidate_start']['xian_mo_strategies']=[7103,7135];bind(row,ctx);saved=deepcopy((row,ctx));c=current.compile_start(row,**self.args(ctx));self.assertEqual(saved,(row,ctx))
  row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999};ctx['players'][0]['after_talent_counters']={'7135':-9}
  self.assertEqual(c,current.compile_start(row,**self.args(ctx)))
 def test_truncation_not_a_label(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7103,7135];bind(row,ctx)
  c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1;b=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
