from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from tests.test_current_element_flag_v62r3 import fixture as flag_fixture
from yixian import full_battle_v62r2 as old,full_battle_v63r2 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class DreamFireTests(unittest.TestCase):
 def args(self,ctx):return dict(first_player=0,seed='dream-fire-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundaries_and_all_schedulers(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_dream_fire_v63r2_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],50)
 def test_mapping_only_eight_new_grades(self):
  a=old.catalogue()[1];b=current.catalogue()[1]
  self.assertEqual(set(b)-set(a),{7000090,7010090,7020090,7030090,7040090,374,10374,20374});self.assertEqual(a,{k:v for k,v in b.items() if k in a})
 def test_new_content_complete_battles_and_settlement(self):
  compiled=[]
  for raw in [7000090,7010090,7020090,7030090,7040090,374,10374,20374]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[raw,0,0];compiled.append(current.compile_start(row,**self.args(ctx)))
  before=deepcopy(compiled);rs=current.simulate_batch([c['battle'] for c in compiled])['results'];self.assertEqual(compiled,before)
  for c,r in zip(compiled,rs):
   self.assertTrue(r.get('terminated'),r);self.assertTrue(calculate_terminal_damage(c,r)['resolved']);self.assertTrue(r['dream_fire_v63']['events']);self.assertFalse(r['training_label_allowed'])
 def test_flag_uses_dream_before_later_ordinary(self):
  row,ctx=flag_fixture([7040090,7000031]);c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(r.get('terminated'),r);e=r['element_flag_v62']['events'][0];self.assertEqual(e['formation']['raw'],7040090);self.assertTrue(e['flag_remains_playable'])
 def test_stars_divination_ownership_and_no_acquisition_replay(self):
  for first in [0,1]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[11002];c=current.compile_start(row,**{**self.args(ctx),'first_player':first})
   self.assertEqual(c['effect_players'][0]['season_choices'],[11002]);r=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(r.get('terminated'),r)
   e=r['star_opening_v63']['events'][0];self.assertEqual(e['player_index'],0);self.assertEqual(e['after']['hexagram'],e['before']['hexagram']+1);self.assertEqual(e['after']['star_power'],e['before']['star_power']);self.assertEqual(e['after']['qi'],e['before']['qi'])
 def test_unknowns_and_duplicate_ownership_stay_blocked(self):
  for ids in [[11002,11002],[11002,99999]]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=ids
   with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
  row,ctx=flag_fixture([7040074,7040090]);c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0]
  self.assertIn('unmapped_first_formation',r.get('unresolved_reason',''))
 def test_terminal_results_cannot_change_inputs(self):
  row,ctx=flag_fixture([7040090]);row['players'][0]['candidate_start']['xian_mo_strategies']=[11002];a=current.compile_start(row,**self.args(ctx))
  row['outcome']={'recorded_hp_delta':999};ctx['players'][0]['after_talent_counters']={'27':1};self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_old_inputs_and_complete_outputs_unchanged(self):
  for row,ctx in [start_fixture(),flag_fixture([7000031])]:
   a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
   self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])

 def test_cloud_identity_binding_counts_dream_cloud_without_changing_classification(self):
  row,ctx=flag_fixture([7040090,1000001]);row['players'][0]['candidate_start']['board'][1]=1040070
  row['players'][0]['candidate_start']['xian_mo_strategies']=[7069,11002]
  ctx['players'][0]['element_flag_hand']['board']=deepcopy(row['players'][0]['candidate_start']['board'])
  ctx['players'][0]['clouds_rain_hand']={'origin':'publicData.lastRoundData.handCards','raw_cards':[7040090,1000001],'source_raw_sha256':row['source']['raw_sha256'],'environment_only':True}
  c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(r.get('terminated'),r);e=r['clouds_rain_v35']['events'][0]
  self.assertEqual(e['hand_cloud_count'],1);self.assertEqual(e['board_cloud_count'],1);self.assertEqual(e['requested_qi'],1)
  self.assertTrue(r['dream_fire_v63']['events']);self.assertTrue(r['star_opening_v63']['events'])

if __name__=='__main__':unittest.main()
