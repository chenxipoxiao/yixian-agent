from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v36 as old,full_battle_v37 as current

def fixture():
 row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['xian_mo_strategies']=[7056]
 s['board']=[4000011,0,0];return row,ctx

class SevenStarsTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='seven-stars-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_seven_stars_v37_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout),{'passed':True,'scenarios':87})
 def test_no_owner_exact_regression(self):
  row,ctx=start_fixture();a=self.args(ctx);before=old.compile_start(row,**a);after=current.compile_start(row,**a)
  self.assertEqual(before,after);self.assertEqual(old.simulate_batch([before['battle']])['results'],current.simulate_batch([after['battle']])['results'])
 def test_ownership_and_unlocked_grids(self):
  row,ctx=fixture();c=current.compile_start(row,**self.args(ctx))
  self.assertEqual(c['battle']['seven_stars'],{'players':[{'strategy_id':7056,'unlocked_slots':3},None]})
  self.assertEqual(c['effect_players'][0]['season_choices'],[7056])
 def test_missing_or_invalid_grids(self):
  for n in (None,True,0,1,2,9,4):
   row,ctx=fixture();row['players'][0]['candidate_start']['unlocked_slots']=n
   with self.subTest(n=n),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_unknown_effects_and_duplicate_not_filtered(self):
  for extra in (7056,1009,7053,999999):
   row,ctx=fixture();row['players'][0]['candidate_start']['xian_mo_strategies'].append(extra)
   with self.subTest(extra=extra),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_no_mutation_or_outcome_input_both_initiatives(self):
  for first in (0,1):
   row,ctx=fixture();saved=deepcopy(row);a=self.args(ctx,first);c=current.compile_start(row,**a)
   self.assertEqual(row,saved);row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999}
   ctx['battle_params']=[99,1,7];self.assertEqual(c,current.compile_start(row,**a))
   r=current.simulate_batch([c['battle']])['results'][0]
   self.assertTrue(r['terminated']);self.assertTrue(r['seven_stars_v37']['events'])
   self.assertTrue(all(e['player_index']==0 for e in r['seven_stars_v37']['events']));self.assertFalse(r['training_label_allowed'])
 def test_truncation_not_label(self):
  row,ctx=fixture();b=current.compile_start(row,**self.args(ctx))['battle'];b['max_turns']=1
  r=current.simulate_batch([b])['results'][0];self.assertTrue(r['truncated']);self.assertIsNone(r['winner'])
 def test_invalid_bridge_context_remains_unresolved(self):
  row,ctx=fixture();b=current.compile_start(row,**self.args(ctx))['battle']
  b['seven_stars']['players'][0]['unlocked_slots']=4
  r=current.simulate_batch([b])['results'][0]
  self.assertIn('grid_deck_mismatch',r['unresolved_reason']);self.assertNotIn('winner',r)

if __name__=='__main__':unittest.main()
