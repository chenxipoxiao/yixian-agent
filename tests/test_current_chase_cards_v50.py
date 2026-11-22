from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v49 as old,full_battle_v50 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

IDS=[438,10438,20438,448,10448,20448,7000108,7010108,7020108]

class ChaseCardsBatchTests(unittest.TestCase):
 def args(self,context):return dict(first_player=0,seed='chase-cards-software',game_mode=3,season_mec=10,combat_context=context)
 def test_native_interaction_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_chase_cards_v50_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertEqual(r['scenarios'],32)
 def test_old_catalogue_unchanged_and_nine_new_variants(self):
  before=old.catalogue();after=current.catalogue();self.assertEqual(before[0],after[0]);self.assertEqual(before[2:],after[2:])
  self.assertEqual({k:v for k,v in after[1].items() if k in before[1]},before[1])
  self.assertEqual(set(after[1])-set(before[1]),set(IDS))
  for i,raw in enumerate(IDS):self.assertEqual(after[1][raw],f'7450{i//3+1}{i%3+1}')
 def test_old_compiler_still_rejects_new_families(self):
  for raw in [438,448,7000108]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[raw,0,0]
   with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
   current.compile_start(row,**self.args(ctx))
 def test_complete_battles_all_grades_and_input_immutability(self):
  compiled=[]
  for raw in IDS:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[raw,0,0]
   compiled.append(current.compile_start(row,**self.args(ctx)))
  before=deepcopy(compiled);results=current.simulate_batch([c['battle'] for c in compiled])['results'];self.assertEqual(before,compiled)
  for c,b in zip(compiled,results):
   self.assertTrue(b['terminated']);self.assertFalse(b['used_randomness']);self.assertFalse(b['training_label_allowed'])
   self.assertTrue(b['chase_cards_v50']['events']);self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
 def test_unrelated_complete_battle_exactly_unchanged(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_no_terminal_or_postbattle_leakage(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[448,0,0]
  before=current.compile_start(row,**self.args(ctx));row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999}
  ctx['players'][0]['after_talent_counters']={'281':999};self.assertEqual(before,current.compile_start(row,**self.args(ctx)))
  row['players'][0]['candidate_start']['permanentBuffTempDatas']['999999']=1
  with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_truncation_not_a_winner(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[7000108,0,0]
  c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1;b=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
