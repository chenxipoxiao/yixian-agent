from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v46 as old,full_battle_v48 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage


class HiddenDragonTests(unittest.TestCase):
 def args(self,context):return dict(first_player=0,seed='hidden-dragon-software',game_mode=3,season_mec=10,combat_context=context)
 def test_native_damage_and_classification_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_hidden_dragon_v48_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertEqual(r['scenarios'],28)
 def test_no_new_cards_or_changed_compilation(self):
  self.assertEqual(current.catalogue(),old.catalogue())
  for raw in [0,331,10331,20331]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[raw,0,0]
   self.assertEqual(current.compile_start(row,**self.args(ctx)),old.compile_start(row,**self.args(ctx)))
 def test_unrelated_complete_battle_remains_identical(self):
  row,ctx=start_fixture();c=current.compile_start(row,**self.args(ctx))
  self.assertEqual(current.simulate_batch([c['battle']])['results'],old.simulate_batch([c['battle']])['results'])
 def test_full_battles_for_all_grades_with_zero_preserve_input(self):
  inputs=[]
  for raw in [331,10331,20331]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[raw,0,0]
   c=current.compile_start(row,**self.args(ctx));c['battle']['players'][0]['unrestrained_sword_zero_stacks']=50
   inputs.append(c)
  saved=deepcopy(inputs);r=current.simulate_batch([c['battle'] for c in inputs])
  self.assertEqual(inputs,saved);self.assertEqual(r['adapter_contract']['evidence_sha256'],current.PROOF_SHA)
  for c,b in zip(inputs,r['results']):
   self.assertTrue(b['terminated']);self.assertFalse(b['training_label_allowed']);self.assertFalse(b['used_randomness'])
   self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
 def test_outcomes_and_poststate_do_not_affect_input(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[331,0,0]
  before=current.compile_start(row,**self.args(ctx));row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999}
  ctx['players'][0]['after_talent_counters']={'625':999}
  self.assertEqual(current.compile_start(row,**self.args(ctx)),before)
 def test_unknown_effects_still_stop(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[331,0,0]
  row['players'][0]['candidate_start']['permanentBuffTempDatas']['999999']=1
  with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_truncation_does_not_generate_settlement(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[331,0,0]
  c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
  b=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
