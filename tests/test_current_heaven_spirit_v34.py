from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v33 as old,full_battle_v34 as current

def fixture(temp=None):
 row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[1001]
 ctx['players'][0]['heaven_spirit_switch']={'origin':'privateData.xianMoData:preparation_switch',
  'source_raw_sha256':row['source']['raw_sha256'],'environment_only':True,
  'selected_strategy_ids':[1001],'temp_data':{} if temp is None else temp}
 return row,ctx

class HeavenSpiritTests(unittest.TestCase):
 def args(self,ctx,first=0):
  return dict(first_player=first,seed='heaven-spirit-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_heaven_spirit_v34_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout),{'passed':True,'scenarios':28})
 def test_no_owner_complete_regression(self):
  row,ctx=start_fixture();a=self.args(ctx);before=old.compile_start(row,**a);after=current.compile_start(row,**a)
  self.assertEqual(before,after);self.assertEqual(old.simulate_batch([before['battle']])['results'],current.simulate_batch([after['battle']])['results'])
 def test_map_missing_key_zero_and_nonzero(self):
  for temp,enabled in [({},True),({'1001':0},True),({'1001':1},False),({'1001':-1},False)]:
   row,ctx=fixture(temp);c=current.compile_start(row,**self.args(ctx))
   self.assertEqual(c['battle']['heaven_spirit']['players'],[{'strategy_id':1001,'enabled':enabled},None])
   self.assertEqual(c['effect_players'][0]['season_choices'],[1001])
 def test_missing_or_wrong_source_stays_unresolved(self):
  for change in ('missing','null_map','bad_value','wrong_selection','wrong_source','missing_origin','not_environment'):
   row,ctx=fixture();data=ctx['players'][0]['heaven_spirit_switch']
   if change=='missing':del ctx['players'][0]['heaven_spirit_switch']
   elif change=='null_map':data['temp_data']=None
   elif change=='bad_value':data['temp_data']={'1001':False}
   elif change=='wrong_selection':data['selected_strategy_ids']=[]
   elif change=='wrong_source':data['source_raw_sha256']='other'
   elif change=='missing_origin':del data['origin']
   else:data['environment_only']=False
   with self.subTest(change=change),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_unknowns_not_filtered(self):
  for extra in (1001,1009,7053,9999999):
   row,ctx=fixture();row['players'][0]['candidate_start']['xian_mo_strategies'].append(extra)
   with self.subTest(extra=extra),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_outcomes_not_input_and_both_initiatives(self):
  for first in (0,1):
   row,ctx=fixture();saved=deepcopy(row);a=self.args(ctx,first);c=current.compile_start(row,**a)
   self.assertEqual(row,saved);row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999}
   ctx['battle_params']=[999,4,5];self.assertEqual(c,current.compile_start(row,**a))
   r=current.simulate_batch([c['battle']])['results'][0]
   self.assertTrue(r['terminated']);self.assertEqual(len(r['heaven_spirit_v34']['events']),1)
   self.assertEqual(r['heaven_spirit_v34']['events'][0]['player_index'],0);self.assertFalse(r['training_label_allowed'])
 def test_truncation_does_not_label_winner(self):
  row,ctx=fixture();b=current.compile_start(row,**self.args(ctx))['battle'];b['max_turns']=1
  r=current.simulate_batch([b])['results'][0];self.assertTrue(r['truncated']);self.assertIsNone(r['winner'])
 def test_invalid_bridge_context(self):
  row,ctx=start_fixture();b=current.compile_start(row,**self.args(ctx))['battle']
  b['heaven_spirit']={'players':[{'strategy_id':1001,'enabled':'yes'},None]}
  with self.assertRaisesRegex(current.SimulatorError,'ownership'):current.simulate_batch([b])

if __name__=='__main__':unittest.main()
