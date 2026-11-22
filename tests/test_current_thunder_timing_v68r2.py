from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v67r2 as old, full_battle_v68 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class ThunderTimingTests(unittest.TestCase):
 def args(self,ctx):return dict(first_player=0,seed='thunder-timing-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_rolls_before_hits_and_interactions(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_thunder_timing_v68r2_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertEqual(r['scenarios'],107)
 def test_three_grades_complete_battle_and_settlement(self):
  compiled=[]
  for raw in [4000046,4010046,4020046]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=raw;compiled.append(current.compile_start(row,**self.args(ctx)))
  saved=deepcopy(compiled);out=current.simulate_batch([c['battle'] for c in compiled])['results'];self.assertEqual(compiled,saved)
  for c,r in zip(compiled,out):
   self.assertTrue(r['terminated']);self.assertTrue(calculate_terminal_damage(c,r)['resolved']);self.assertFalse(r['training_label_allowed'])
   self.assertTrue(r['thunder_timing_v68']['events']);self.assertFalse(r['thunder_timing_v68']['recorded_action_log'])
 def test_unchanged_mapping_start_and_unrelated_full_battle(self):
  self.assertEqual(old.catalogue(),current.catalogue());row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_terminal_and_poststate_are_not_inputs(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=4020046;a=current.compile_start(row,**self.args(ctx))
  row['outcome']={'recorded_hp_delta':-9999,'winner_snapshot_slot':'p2'};ctx['players'][0]['after_talent_counters']={'195':999}
  self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_unknown_cards_and_missing_start_still_block(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=9999999
  with self.assertRaisesRegex(current.UnresolvedBattle,'unmapped_cards'):current.compile_start(row,**self.args(ctx))
  row,ctx=start_fixture();del row['players'][0]['candidate_start']['permanentBuffTempDatas']
  with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
if __name__=='__main__':unittest.main()
