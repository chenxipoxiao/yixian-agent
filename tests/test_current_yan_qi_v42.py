from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from tests.test_current_clouds_rain_v35 import fixture as cloud_fixture
from yixian import full_battle_v41 as old,full_battle_v42 as current
from yixian.terminal_damage_v38 import calculate_terminal_damage

class YanQiTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='yan-qi-software',game_mode=3,season_mec=10,combat_context=ctx)
 def fixture(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7053];return row,ctx
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_yan_qi_v42_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);result=json.loads(p.stdout);self.assertTrue(result['passed']);self.assertGreaterEqual(result['scenarios'],20)
 def test_unowned_complete_inputs_and_outputs_unchanged(self):
  for maker in [start_fixture,cloud_fixture]:
   row,ctx=maker();a=self.args(ctx);x=old.compile_start(row,**a);y=current.compile_start(row,**a)
   self.assertEqual(x,y);self.assertEqual(old.simulate_batch([x['battle']])['results'],current.simulate_batch([y['battle']])['results'])
 def test_owned_opening_does_not_invent_healing(self):
  for first in [0,1]:
   row,ctx=self.fixture();saved=deepcopy(row);c=current.compile_start(row,**self.args(ctx,first))
   self.assertEqual(saved,row);self.assertEqual(c['effect_players'][0]['season_choices'],[7053])
   r=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(r['terminated']);self.assertFalse(r['training_label_allowed'])
   state=next(s for s in r['yan_qi_v42']['remaining'] if s['player_index']==0);self.assertEqual(state['pending_uses'],1)
 def test_poststate_and_outcomes_not_inputs(self):
  row,ctx=self.fixture();c=current.compile_start(row,**self.args(ctx));row['outcome']={'recorded_hp_delta':999,'winner_snapshot_slot':'p2'}
  ctx['battle_params']=[744,999];ctx['players'][0]['after_talent_counters']={'744':999}
  self.assertEqual(c,current.compile_start(row,**self.args(ctx)))
 def test_unknown_choices_states_or_cards_still_block(self):
  for key,value in [('xian_mo_strategies',[7053,7053]),('xian_mo_strategies',[7053,16024]),('xian_mo_strategies',None),
                    ('permanentBuffTempDatas',{'744':1}),('board',[0,99999999,0])]:
   row,ctx=self.fixture();row['players'][0]['candidate_start'][key]=value
   with self.subTest(key=key,value=value),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_legacy_fate326_not_enabled_by_parameter_dependency(self):
  row,ctx=self.fixture();ctx['players'][0]['fate_strategies']=[326]
  # Legacy choices are a candidate-start field; the metadata binder alone must
  # never allow a historical-season selection.
  row['players'][0]['candidate_start']['fate_strategies']=[326]
  with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_truncated_no_settlement(self):
  row,ctx=self.fixture();c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
  r=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(r['truncated']);self.assertIsNone(r['winner']);self.assertFalse(calculate_terminal_damage(c,r)['resolved'])

if __name__=='__main__':unittest.main()
