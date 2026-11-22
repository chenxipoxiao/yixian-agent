from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v65 as old,full_battle_v66r2 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class SpaceFieldTests(unittest.TestCase):
 def args(self,ctx):return dict(first_player=0,seed='space-field-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_boundary_interactions(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_space_field_v66r2_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],40)
 def test_full_battle_initial_slots_and_deferred_settlement(self):
  compiled=[]
  for slot in range(3):
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][slot]=350
   c=current.compile_start(row,**self.args(ctx));compiled.append(c)
  before=deepcopy(compiled);out=current.simulate_batch([c['battle'] for c in compiled])['results'];self.assertEqual(compiled,before)
  for slot,(c,r) in enumerate(zip(compiled,out)):
   self.assertTrue(r.get('terminated'),r);self.assertTrue(calculate_terminal_damage(c,r)['resolved'])
   skips=[e for e in r['space_field_v66']['events'] if e['kind']=='first_use_skip'];self.assertEqual(len(skips),int(slot>0))
   self.assertFalse(r['match_continuation_allowed']);self.assertFalse(r['pending_card_match_effects'][0]['applied'])
   self.assertEqual(r['initial'][0]['cultivation'],r['players'][0]['cultivation'])
 def test_no_future_or_terminal_input(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][2]=350;a=current.compile_start(row,**self.args(ctx))
  row['outcome']={'recorded_hp_delta':999,'recorded_destiny_damage':-99};ctx['players'][0]['after_talent_counters']={'350':999}
  self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_slot_and_unknown_validation(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][2]=350;row['players'][0]['candidate_start']['unlocked_slots']=8
  with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][2]=999999
  with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_old_source_rejects_and_unrelated_output_unchanged(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
  row['players'][0]['candidate_start']['board'][2]=350
  with self.assertRaisesRegex(old.UnresolvedBattle,'unmapped_cards:350'):old.compile_start(row,**self.args(ctx))
if __name__=='__main__':unittest.main()
