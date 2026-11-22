from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from tests.test_current_clouds_rain_v35 import fixture as cloud_fixture
from yixian import full_battle_v43 as old,full_battle_v44 as current
from yixian.terminal_damage_v38 import calculate_terminal_damage

class ExtremeFootworkTests(unittest.TestCase):
 def args(self,ctx):return dict(first_player=0,seed='footwork-software',game_mode=3,season_mec=10,combat_context=ctx)
 def fixture(self,raw=10020098):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[raw,0,0];return row,ctx
 def test_source_bound_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_extreme_footwork_v44_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],18)
 def test_exact_new_bindings(self):
  prior=old.catalogue()[1];now=current.catalogue()[1]
  self.assertEqual({k:v for k,v in now.items() if k not in prior},{10000098:'145981',10010098:'145982',10020098:'145983'})
 def test_previous_complete_battles_unchanged(self):
  for maker in [start_fixture,cloud_fixture]:
   row,ctx=maker();x=old.compile_start(row,**self.args(ctx));y=current.compile_start(row,**self.args(ctx))
   self.assertEqual(x,y);self.assertEqual(old.simulate_batch([x['battle']])['results'],current.simulate_batch([y['battle']])['results'])
 def test_all_grades_complete_battles_and_preserve_input(self):
  rows=[self.fixture(10000098+i*10000) for i in range(3)];saved=deepcopy(rows)
  compiled=[current.compile_start(row,**self.args(ctx)) for row,ctx in rows]
  results=current.simulate_batch([c['battle'] for c in compiled])['results'];self.assertEqual(saved,rows)
  for (row,_),r in zip(rows,results):
   self.assertTrue(r['terminated']);self.assertFalse(r['used_randomness']);self.assertFalse(r['training_label_allowed'])
   events=r['extreme_footwork_v44']['events'];self.assertTrue(any(e['kind']=='card_body' and e['raw_id']==row['players'][0]['candidate_start']['board'][0] for e in events))
 def test_outcomes_not_inputs(self):
  row,ctx=self.fixture();before=current.compile_start(row,**self.args(ctx));row['outcome']={'recorded_hp_delta':999,'winner_snapshot_slot':'p2'};ctx['battle_params']=[297,999]
  self.assertEqual(before,current.compile_start(row,**self.args(ctx)))
 def test_unknown_states_still_block(self):
  for key,value in [('permanentBuffTempDatas',{'297':1}),('board',[10020098,99999999,0]),('xian_mo_strategies',[9999999])]:
   row,ctx=self.fixture();row['players'][0]['candidate_start'][key]=value
   with self.subTest(key=key),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_truncation_cannot_settle(self):
  row,ctx=self.fixture();c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
  r=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(r['truncated']);self.assertIsNone(r['winner']);self.assertFalse(calculate_terminal_damage(c,r)['resolved'])

if __name__=='__main__':unittest.main()
