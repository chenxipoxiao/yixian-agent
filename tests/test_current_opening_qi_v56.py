"""Opening and actual-Qi boundaries, plus complete explicit software battles."""
from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v55 as old,full_battle_v56 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class OpeningQiTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='opening-qi-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_opening_qi_v56_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertEqual(len(r['names']),r['scenarios']);self.assertGreater(r['scenarios'],20);print('V56_NATIVE_PROBE='+p.stdout.strip(),flush=True)
 def test_full_battles_both_orders_and_settlement(self):
  starts=[]
  for ids in [[7005],[7059],[7109],[7005,7059,7109],[7005,7132],[7059,7069,7109]]:
   for first in [0,1]:
    row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['xian_mo_strategies']=ids
    starts.append(current.compile_start(row,**self.args(ctx,first)));self.assertEqual(starts[-1]['effect_players'][0]['season_choices'],ids)
  saved=deepcopy(starts);results=current.simulate_batch([c['battle'] for c in starts])['results'];self.assertEqual(starts,saved)
  for c,b in zip(starts,results):
   self.assertTrue(b['terminated']);self.assertFalse(b['used_randomness']);self.assertFalse(b['training_label_allowed']);self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
 def test_no_ownership_preserves_complete_case(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_old_contract_stays_closed(self):
  for id in [7005,7059,7109]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[id]
   with self.subTest(id=id),self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
 def test_unsupported_context_not_silently_admitted(self):
  for ids in [None,[True],[7005,7005],[7109,7010],[7059,999999]]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=ids
   with self.subTest(ids=ids),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
  for fate in [89,336,407,148]:
   row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['xian_mo_strategies']=[7005,7059,7109];s['fate_strategies']=[fate]
   with self.subTest(fate=fate),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_outcome_independent_and_inputs_immutable(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7005,7059,7109];saved=deepcopy((row,ctx))
  a=current.compile_start(row,**self.args(ctx));self.assertEqual(saved,(row,ctx))
  row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999};ctx['players'][0]['after_talent_counters']={'202':999,'645':999}
  self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_truncation_never_labels(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7005,7059,7109]
  c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1;b=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
