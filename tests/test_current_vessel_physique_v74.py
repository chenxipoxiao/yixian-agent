from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v73 as old,full_battle_v74 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class VesselPhysiqueTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='vessel-physique-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_effect_order_and_identity(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_vessel_physique_v74_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],20);print('V74_NATIVE_PROBE='+p.stdout.strip(),flush=True)
 def test_all_levels_complete_battles_and_settlement(self):
  starts=[]
  for c in current.extension_contract()['cards']:
   for first in [0,1]:
    row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=c['raw_id'];starts.append(current.compile_start(row,**self.args(ctx,first)))
  saved=deepcopy(starts);results=current.simulate_batch([c['battle'] for c in starts])['results'];self.assertEqual(saved,starts)
  for c,b in zip(starts,results):
   self.assertTrue(b['terminated'],b);self.assertFalse(b['used_randomness']);self.assertFalse(b['training_label_allowed']);self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
 def test_vessel_complete_battle_uses_two_opening_charges(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=181
  c=current.compile_start(row,**self.args(ctx));b=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(b['terminated'],b);events=b['vessel_physique_v74']['events'];e=next(x for x in events if x['kind']=='vessel_opening');self.assertEqual(e['after']-e['before'],2)
  self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
 def test_unrelated_full_case_unchanged(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_input_and_terminal_fields_do_not_change_start(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=339;saved=deepcopy((row,ctx));a=current.compile_start(row,**self.args(ctx));self.assertEqual(saved,(row,ctx))
  row['outcome']={'recorded_hp_delta':999,'winner_snapshot_slot':'p2'};self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_missing_and_unsupported_stay_blocked(self):
  for raw in [99000216,7010081]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=raw
   with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_old_adapter_still_rejects_new_cards(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=339
  with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
 def test_truncation_does_not_create_a_label(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=10020073;c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
  b=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
