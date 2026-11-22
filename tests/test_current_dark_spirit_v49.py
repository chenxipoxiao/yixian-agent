from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v48 as old,full_battle_v49 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class DarkSpiritTests(unittest.TestCase):
 def args(self,context):return dict(first_player=0,seed='dark-spirit-software',game_mode=3,season_mec=10,combat_context=context)
 def test_native_state_and_chase_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_dark_spirit_v49_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertEqual(r['scenarios'],30)
 def test_new_mapping_and_frozen_old_catalogue(self):
  before=old.catalogue();after=current.catalogue()
  self.assertEqual(after[0],before[0]);self.assertEqual(after[2:],before[2:])
  self.assertEqual({k:v for k,v in after[1].items() if k in before[1]},before[1])
  self.assertEqual({k:v for k,v in after[1].items() if k not in before[1]},{336:'744061',10336:'744062',20336:'744063'})
 def test_old_compiler_still_rejects_new_card(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[336,0,0]
  with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
  self.assertEqual(current.compile_start(row,**self.args(ctx))['battle']['players'][0]['cards'][0],'744061')
 def test_unrelated_complete_battle_unchanged(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx))
  self.assertEqual(a,b);self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_complete_all_grades_preserve_input(self):
  inputs=[]
  for raw in [336,10336,20336]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[raw,0,0]
   inputs.append(current.compile_start(row,**self.args(ctx)))
  saved=deepcopy(inputs);r=current.simulate_batch([c['battle'] for c in inputs]);self.assertEqual(inputs,saved)
  for c,b in zip(inputs,r['results']):
   self.assertTrue(b['terminated']);self.assertFalse(b['used_randomness']);self.assertFalse(b['training_label_allowed'])
   self.assertTrue(b['dark_spirit_v49']['events']);self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
 def test_outcomes_and_unknowns_still_guarded(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[336,0,0]
  before=current.compile_start(row,**self.args(ctx));row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999}
  ctx['players'][0]['after_talent_counters']={'336':999}
  self.assertEqual(current.compile_start(row,**self.args(ctx)),before)
  row['players'][0]['candidate_start']['permanentBuffTempDatas']['999999']=1
  with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_truncated_battle_has_no_settlement(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[336,0,0]
  c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
  b=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
