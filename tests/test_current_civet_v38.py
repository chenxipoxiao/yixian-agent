from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v37 as old,full_battle_v38 as current
from yixian.terminal_damage_v38 import calculate_terminal_damage

class CivetTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='civet-software',game_mode=3,season_mec=10,combat_context=ctx)
 def fixture(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[433,0,0];return row,ctx
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_civet_v38_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout),{'passed':True,'scenarios':48})
 def test_no_civet_exact_regression(self):
  row,ctx=start_fixture();a=self.args(ctx);before=old.compile_start(row,**a);after=current.compile_start(row,**a)
  self.assertEqual(before,after);self.assertEqual(old.simulate_batch([before['battle']])['results'],current.simulate_batch([after['battle']])['results'])
 def test_all_levels_and_unknown_not_dropped(self):
  for raw in [433,10433,20433]:
   row,ctx=self.fixture();row['players'][0]['candidate_start']['board'][0]=raw
   c=current.compile_start(row,**self.args(ctx));self.assertEqual(c['battle']['civet'],{'is_mirror':[False,False]})
  row['players'][0]['candidate_start']['board'][1]=999999
  with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_no_mutation_or_outcome_input(self):
  for first in [0,1]:
   row,ctx=self.fixture();before=deepcopy(row);a=self.args(ctx,first);c=current.compile_start(row,**a)
   self.assertEqual(row,before);row['outcome']={'recorded_hp_delta':999};ctx['battle_params']=[999]
   self.assertEqual(c,current.compile_start(row,**a));r=current.simulate_batch([c['battle']])['results'][0]
   self.assertTrue(r['terminated']);self.assertEqual(r['civet_v38']['requested_destiny_gains'],[3,0]);self.assertFalse(r['training_label_allowed'])
 def test_missing_context_and_mirror(self):
  row,ctx=self.fixture();ctx['players'][0].pop('is_mirror')
  with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
  row,ctx=self.fixture();b=current.compile_start(row,**self.args(ctx))['battle'];b.pop('civet')
  r=current.simulate_batch([b])['results'][0];self.assertIn('explicit_mirror_context_required',r['unresolved_reason'])
 def test_damage_is_gross_without_fabricated_total(self):
  row,ctx=self.fixture();c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0]
  d=calculate_terminal_damage(c,r);self.assertTrue(d['resolved']);self.assertNotIn('loser_destiny_after',d)
  self.assertIsNone(d['authoritative_post_battle_destiny']);self.assertFalse(d['full_match_transition_complete'])
  # Explicit software branches: gain in the loser plus each survival fate
  # remains unresolved, whether its count is exhausted or available.
  for fate in [7,65,83,154]:
   sample=deepcopy(r);sample['winner']=1;c2=deepcopy(c);c2['effect_players'][0]['fates']=[fate]
   self.assertEqual(calculate_terminal_damage(c2,sample)['reason'],'civet_survival_gain_order_unresolved')
 def test_truncation_not_label(self):
  row,ctx=self.fixture();c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
  r=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(r['truncated']);self.assertIsNone(r['winner'])
  self.assertFalse(calculate_terminal_damage(c,r)['resolved'])

if __name__=='__main__':unittest.main()
