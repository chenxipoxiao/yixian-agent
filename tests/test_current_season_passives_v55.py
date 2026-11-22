"""Batch boundaries and complete single battles; software fixtures are explicit."""
from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v54 as old,full_battle_v55 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class SeasonPassiveTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='season-passive-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_season_passives_v55_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertEqual(len(r['names']),r['scenarios']);self.assertGreater(r['scenarios'],25);print('V55_NATIVE_PROBE='+p.stdout.strip(),flush=True)
 def test_full_battles_both_orders_and_settlement(self):
  starts=[]
  for ids in [[7035],[7050],[7132],[7035,7050,7132],[5007,7050],[5008,7035]]:
   for first in [0,1]:
    row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['xian_mo_strategies']=ids;s['board']=[1000041,1000001,0]
    starts.append(current.compile_start(row,**self.args(ctx,first)));self.assertEqual(starts[-1]['effect_players'][0]['season_choices'],ids)
  saved=deepcopy(starts);results=current.simulate_batch([c['battle'] for c in starts])['results'];self.assertEqual(starts,saved)
  for c,b in zip(starts,results):
   self.assertTrue(b['terminated']);self.assertFalse(b['used_randomness']);self.assertFalse(b['training_label_allowed']);self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
 def test_no_ownership_preserves_complete_case(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_old_contract_stays_closed(self):
  for id in [7035,7050,7132]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[id]
   with self.subTest(id=id),self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
 def test_unsupported_context_not_silently_admitted(self):
  for ids in [None,[True],[7035,7035],[7132,7010],[7035,999999]]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=ids
   with self.subTest(ids=ids),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
  for fate in [148,320,380,97]:
   row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['xian_mo_strategies']=[7035,7050,7132];s['fate_strategies']=[fate]
   with self.subTest(fate=fate),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_outcome_independent_and_inputs_immutable(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7035,7050,7132];saved=deepcopy((row,ctx))
  a=current.compile_start(row,**self.args(ctx));self.assertEqual(saved,(row,ctx))
  row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999};ctx['players'][0]['after_talent_counters']={'202':999,'645':999}
  self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_truncation_never_labels(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7035,7050,7132]
  c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1;b=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
