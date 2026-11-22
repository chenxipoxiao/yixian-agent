"""Combined dependency batch; explicit software scenarios, not observed action logs."""
from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from tests.test_current_carefree_twin_v53r2 import fixture as twin_fixture
from yixian import full_battle_v53 as old,full_battle_v54 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class TwinDependencyTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='twin-dependencies-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundary_batch(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_twin_dependencies_v54_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertEqual(len(r['names']),r['scenarios']);self.assertGreater(r['scenarios'],25)
 def test_complete_battles_settlement_and_ownership_both_orders(self):
  compiled=[]
  for ids in [(5005,),(5007,),(5005,5007,5009),(5007,5008)]:
   for first in [0,1]:
    row,ctx=twin_fixture(ids,slot=1);row['players'][0]['candidate_start']['board']=[1000012,0,1010099]
    saved=deepcopy((row,ctx));c=current.compile_start(row,**self.args(ctx,first));self.assertEqual(saved,(row,ctx))
    self.assertEqual(c['effect_players'][0]['season_choices'],list(ids));compiled.append(c)
  original=deepcopy(compiled);results=current.simulate_batch([c['battle'] for c in compiled])['results'];self.assertEqual(compiled,original)
  for c,b in zip(compiled,results):
   self.assertTrue(b['terminated']);self.assertFalse(b['used_randomness']);self.assertFalse(b['training_label_allowed']);self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
 def test_old_compiler_stays_closed_and_unrelated_case_exact(self):
  for id in [5005,5007]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[id]
   with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_extreme_grade_registration(self):
  before=old.catalogue()[1];after=current.catalogue()[1]
  for raw in [1000099,1010099,1020099]:self.assertNotIn(raw,before);self.assertIn(raw,after)
  self.assertEqual({k:v for k,v in after.items() if k in before},before)
 def test_outcomes_not_inputs(self):
  row,ctx=twin_fixture((5005,5007,5009),1);a=current.compile_start(row,**self.args(ctx))
  row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999};ctx['players'][0]['after_talent_counters']={'781':0,'786':0}
  self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_missing_ownership_and_unknowns_rejected(self):
  for value in [None,[5005,5005],[5007,5007],[5005,7035],[5007,999999],[True]]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=value
   with self.subTest(value=value),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_truncation_has_no_reward(self):
  row,ctx=twin_fixture((5005,5007),1);c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
  b=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
