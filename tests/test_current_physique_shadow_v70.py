from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v69 as old, full_battle_v70 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

IDS=[10000110+i*10000 for i in range(3)]+[base+i*10000 for base in [10000070,10000077] for i in range(5)]
class PhysiqueShadowTests(unittest.TestCase):
 def args(self,ctx):return dict(first_player=0,seed='physique-shadow-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_boundaries_and_schedulers(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_physique_shadow_v70_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],40)
 def test_all_grades_complete_battle(self):
  compiled=[]
  for raw in IDS:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=raw;compiled.append(current.compile_start(row,**self.args(ctx)))
  before=deepcopy(compiled);out=current.simulate_batch([c['battle'] for c in compiled])['results'];self.assertEqual(compiled,before)
  for c,r in zip(compiled,out):
   self.assertTrue(r.get('terminated'),r);self.assertTrue(calculate_terminal_damage(c,r)['resolved']);self.assertFalse(r['training_label_allowed']);self.assertTrue(r['physique_shadow_v70']['events'])
 def test_legacy_equivalence_and_no_result_leak(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
  row['players'][0]['candidate_start']['board'][0]=10000070
  with self.assertRaisesRegex(old.UnresolvedBattle,'unmapped_cards'):old.compile_start(row,**self.args(ctx))
  a=current.compile_start(row,**self.args(ctx));row['outcome']={'recorded_hp_delta':999,'winner':0};self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_strict_identity_dependencies(self):
  from tests.test_current_upgrade_sound_v41 import fixture
  from tests.test_current_engraving_effects_v21 import TransformEngravingTests
  mapping=current.catalogue()[1]
  for board in [[10000110,10010110,10020110],[10000070,10010070,10020070,10030070,10040070],[10000077,10010077,10020077,10030077,10040077]]:
   row,ctx=fixture(True);row['players'][0]['candidate_start']['board']=board;c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(r.get('terminated'),r)
   e=next(e for e in r['upgrade_sound_v41']['events'] if e['player_index']==0);self.assertEqual(e['after_raw'],board);self.assertEqual(e['upgrades'],[])
   row,ctx=TransformEngravingTests().fixture(13003,board);c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(r.get('terminated'),r);self.assertEqual(r['players'][0]['cards'],[mapping[x] for x in board])
 def test_cloud_and_wind_identity_maps(self):
  from tests.test_current_clouds_rain_v35 import fixture
  row,ctx=fixture([10000070,10000077,401]);row['players'][0]['candidate_start']['board']=[10000110,10040070,10040077]
  c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(r.get('terminated'),r)
  e=r['clouds_rain_v35']['events'][0];self.assertEqual((e['hand_cloud_count'],e['board_cloud_count'],e['requested_qi']),(1,0,1))
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[4000108,10000070,10000077];c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(r.get('terminated'),r)
  self.assertTrue(all(e['as_attack'] is False for e in r['hexagram_thunder_v67']['events'] if e.get('raw_card_id')==4000108))
if __name__=='__main__':unittest.main()
