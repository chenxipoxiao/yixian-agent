from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from tests.test_current_clouds_rain_v35 import fixture as cloud_fixture
from yixian import full_battle_v39 as old,full_battle_v40 as current
from yixian.terminal_damage_v38 import calculate_terminal_damage

class DragonQiTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='dragon-qi-software',game_mode=3,season_mec=10,combat_context=ctx)
 def fixture(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[3011];return row,ctx
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_dragon_qi_v40_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout),{'passed':True,'scenarios':17})
 def test_unowned_inputs_and_full_outputs_identical(self):
  for maker in [start_fixture,cloud_fixture]:
   row,ctx=maker();a=self.args(ctx);x=old.compile_start(row,**a);y=current.compile_start(row,**a)
   self.assertEqual(x,y);self.assertEqual(old.simulate_batch([x['battle']])['results'],current.simulate_batch([y['battle']])['results'])
 def test_owned_no_gain_preserves_pending_bonus(self):
  for first in [0,1]:
   row,ctx=self.fixture();saved=deepcopy(row);c=current.compile_start(row,**self.args(ctx,first))
   self.assertEqual(saved,row);self.assertEqual(c['battle']['players'][0]['qi'],0)
   self.assertEqual(c['effect_players'][0]['season_choices'],[3011]);self.assertEqual(c['battle']['dragon_qi']['players'],[{'strategy_id':3011},None])
   r=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(r['terminated'])
   s=next(s for s in r['dragon_qi_v40']['remaining'] if s['player_index']==0)
   self.assertEqual(s['bonus'],2);self.assertFalse(r['training_label_allowed'])
 def test_later_cloud_opening_executes_bonus_both_initiatives(self):
  for first in [0,1]:
   row,ctx=cloud_fixture();row['players'][0]['candidate_start']['xian_mo_strategies'].append(3011)
   c=current.compile_start(row,**self.args(ctx,first));r=current.simulate_batch([c['battle']])['results'][0]
   self.assertTrue(r['terminated']);self.assertEqual(r['clouds_rain_v35']['events'][0]['qi_after'],3)
   self.assertEqual([e['delegated_amount'] for e in r['dragon_qi_v40']['events'] if e['kind']=='first_positive_qi'],[3])
 def test_outcomes_and_poststate_are_not_inputs(self):
  row,ctx=self.fixture();c=current.compile_start(row,**self.args(ctx));row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999}
  ctx['battle_params']=[543,999];ctx['players'][0]['after_talent_counters']={'543':999}
  self.assertEqual(c,current.compile_start(row,**self.args(ctx)))
 def test_unknown_choices_states_or_cards_still_block(self):
  for key,val in [('xian_mo_strategies',[3011,3011]),('xian_mo_strategies',[3011,16024]),('xian_mo_strategies',None),
                  ('permanentBuffTempDatas',{'543':2}),('board',[0,99999999,0])]:
   row,ctx=self.fixture();row['players'][0]['candidate_start'][key]=val
   with self.subTest(key=key,val=val),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_legacy_runtime_cannot_double_apply(self):
  row,ctx=self.fixture();b=current.compile_start(row,**self.args(ctx))['battle'];b['season_runtime']=[{'ids':[3011],'disabled_ids':[]},{'ids':[],'disabled_ids':[]}]
  r=current.simulate_batch([b])['results'][0];self.assertIn('legacy_runtime3011_not_admitted',r['unresolved_reason']);self.assertNotIn('winner',r)
 def test_truncation_has_no_settlement(self):
  row,ctx=self.fixture();c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
  r=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(r['truncated']);self.assertIsNone(r['winner']);self.assertFalse(calculate_terminal_damage(c,r)['resolved'])

if __name__=='__main__':unittest.main()
