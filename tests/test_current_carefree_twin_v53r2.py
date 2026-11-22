"""v53 unchanged engine; correct the probe scenario-count bookkeeping."""
from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v52r2 as old,full_battle_v53 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

def fixture(ids=(5001,5008,5009),slot=0):
 row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=list(ids)
 owned=sorted(set(ids)&{5001,5009})
 ctx['players'][0]['carefree_grid_input']={'origin':'privateData.xianMoData.tempDatas:complete_preparation_grid_map',
  'source_raw_sha256':row['source']['raw_sha256'],'selected_strategy_ids':owned,
  'temp_data':{} if slot is None else {str(id):slot for id in owned},'environment_only':True}
 return row,ctx

class CarefreeTwinTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='carefree-twin-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundary_batch(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_carefree_twin_v53_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertEqual(r['scenarios'],27)
 def test_complete_battles_and_settlement_both_orders(self):
  compiled=[]
  for ids in [(5001,),(5008,),(5009,),(5001,5008,5009)]:
   for first in [0,1]:
    row,ctx=fixture(ids);saved=deepcopy((row,ctx));c=current.compile_start(row,**self.args(ctx,first))
    self.assertEqual(saved,(row,ctx));self.assertEqual(c['effect_players'][0]['season_choices'],list(ids));compiled.append(c)
  before=deepcopy(compiled);battles=current.simulate_batch([c['battle'] for c in compiled])['results'];self.assertEqual(before,compiled)
  for c,b in zip(compiled,battles):
   self.assertTrue(b['terminated']);self.assertFalse(b['used_randomness']);self.assertTrue(calculate_terminal_damage(c,b)['resolved']);self.assertFalse(b['training_label_allowed'])
 def test_absent_key_of_explicit_complete_map_defaults_to_zero(self):
  a,ca=fixture(slot=None);b,cb=fixture(slot=0)
  self.assertEqual(current.compile_start(a,**self.args(ca)),current.compile_start(b,**self.args(cb)))
 def test_missing_or_invalid_preparation_context_rejected(self):
  for change in ['missing','map','source','choices','origin','boolean','negative','outside','foreign_key']:
   row,ctx=fixture();e=ctx['players'][0]['carefree_grid_input']
   if change=='missing':del ctx['players'][0]['carefree_grid_input']
   elif change=='map':del e['temp_data']
   elif change=='source':e['source_raw_sha256']='other'
   elif change=='choices':e['selected_strategy_ids']=[]
   elif change=='origin':e['origin']='after_battle'
   else:e['temp_data']={'5001':{'boolean':True,'negative':-1,'outside':8,'foreign_key':0}[change]} if change!='foreign_key' else {'13003':0}
   with self.subTest(change=change),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_old_compiler_remains_closed_and_old_case_exact(self):
  for id in [5001,5008,5009]:
   row,ctx=fixture((id,))
   with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_outcomes_never_change_input(self):
  row,ctx=fixture();a=current.compile_start(row,**self.args(ctx));row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999}
  ctx['battle_params']=[5009,4];ctx['players'][0]['after_talent_counters']={'785':999}
  self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_duplicates_and_unknowns_remain_rejected(self):
  for ids in [[5001,5001],[5008,5008],[5009,999999],[5008,7035]]:
   row,ctx=fixture(ids)
   with self.subTest(ids=ids),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_truncation_is_not_terminal_or_reward(self):
  row,ctx=fixture();c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
  b=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
