from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v63r2 as old,full_battle_v64 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class CharacterPassiveTests(unittest.TestCase):
 def args(self,ctx):return dict(first_player=0,seed='character-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_callback_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_character_passives_v64_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],50)
 def test_exact_mapping_extension(self):
  a=old.catalogue()[1];b=current.catalogue()[1];self.assertEqual(set(b)-set(a),{family+10000*i for family in [415,416,418] for i in range(3)})
  self.assertEqual(a,{k:v for k,v in b.items() if k in a})
 def test_all_grades_full_battles_and_settlement(self):
  cases=[]
  for base in [415,416,418]:
   for rank in range(3):
    row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[base+rank*10000,0,0];cases.append(current.compile_start(row,**self.args(ctx)))
  before=deepcopy(cases);results=current.simulate_batch([c['battle'] for c in cases])['results'];self.assertEqual(cases,before)
  for c,r in zip(cases,results):
   self.assertTrue(r.get('terminated'),r);self.assertTrue(calculate_terminal_damage(c,r)['resolved']);self.assertTrue(r['character_passives_v64']['events']);self.assertFalse(r['training_label_allowed'])
 def test_seat_identity(self):
  for first in [0,1]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[415,0,0]
   c=current.compile_start(row,**{**self.args(ctx),'first_player':first});r=current.simulate_batch([c['battle']])['results'][0]
   self.assertTrue(r.get('terminated'),r);self.assertEqual({e['player_index'] for e in r['character_passives_v64']['events']},{0})
 def test_no_terminal_input(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[416,0,0];a=current.compile_start(row,**self.args(ctx))
  row['outcome']={'recorded_hp_delta':999};ctx['players'][0]['after_talent_counters']={'27':1}
  self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_unknowns_stay_blocked(self):
  for raw in [999999,350]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[415,raw,0]
   with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_old_complete_output_unchanged(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])

if __name__=='__main__':unittest.main()
