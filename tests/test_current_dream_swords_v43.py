from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from tests.test_current_clouds_rain_v35 import fixture as cloud_fixture
from yixian import full_battle_v42 as old,full_battle_v43 as current
from yixian.terminal_damage_v38 import calculate_terminal_damage

class DreamSwordTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='dream-swords-software',game_mode=3,season_mec=10,combat_context=ctx)
 def fixture(self,raw=1040075):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[raw,0,0];return row,ctx
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_dream_swords_v43_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);result=json.loads(p.stdout);self.assertTrue(result['passed']);self.assertGreaterEqual(result['scenarios'],30)
 def test_ten_exact_bindings(self):
  mapping=current.catalogue()[1];prior=old.catalogue()[1]
  expected={base+10000*i:prefix+str(i+1) for base,prefix in [(1000070,'D1103'),(1000075,'D1108')] for i in range(5)}
  self.assertEqual({k:v for k,v in mapping.items() if k not in prior},expected)
 def test_old_complete_inputs_and_outputs_unchanged(self):
  for maker in [start_fixture,cloud_fixture]:
   row,ctx=maker();a=self.args(ctx);x=old.compile_start(row,**a);y=current.compile_start(row,**a)
   self.assertEqual(x,y);self.assertEqual(old.simulate_batch([x['battle']])['results'],current.simulate_batch([y['battle']])['results'])
 def test_all_grades_execute_full_battles_and_preserve_input(self):
  rows=[self.fixture(base+10000*i) for base in [1000070,1000075] for i in range(5)]
  saved=deepcopy(rows);compiled=[current.compile_start(row,**self.args(ctx)) for row,ctx in rows]
  results=current.simulate_batch([c['battle'] for c in compiled])['results'];self.assertEqual(saved,rows)
  for (row,_),r in zip(rows,results):
   self.assertTrue(r['terminated']);self.assertFalse(r['training_label_allowed']);self.assertFalse(r['used_randomness'])
   ids={e['raw_id'] for e in r['dream_swords_v43']['events'] if e['kind']=='card_body'}
   self.assertIn(row['players'][0]['candidate_start']['board'][0],ids)
 def test_poststate_and_outcomes_not_inputs(self):
  row,ctx=self.fixture();c=current.compile_start(row,**self.args(ctx));row['outcome']={'recorded_hp_delta':999,'winner_snapshot_slot':'p2'}
  ctx['battle_params']=[625,999];ctx['players'][0]['after_talent_counters']={'625':999}
  self.assertEqual(c,current.compile_start(row,**self.args(ctx)))
 def test_unknown_context_or_initial_state_still_blocks(self):
  for key,value in [('permanentBuffTempDatas',{'625':1}),('board',[1040075,99999999,0]),('used_keyin_cards',[9999999]),('xian_mo_strategies',[9999999])]:
   row,ctx=self.fixture();row['players'][0]['candidate_start'][key]=value
   with self.subTest(key=key),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_recorded_initiative_is_not_inferred_from_new_cards(self):
  row,ctx=self.fixture();a=self.args(ctx);a.pop('first_player')
  with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**a)
 def test_truncated_no_settlement(self):
  row,ctx=self.fixture();c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
  r=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(r['truncated']);self.assertIsNone(r['winner']);self.assertFalse(calculate_terminal_damage(c,r)['resolved'])

if __name__=='__main__':unittest.main()
