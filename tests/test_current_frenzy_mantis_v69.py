from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v68 as old, full_battle_v69 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class FrenzyMantisTests(unittest.TestCase):
 def args(self,ctx):return dict(first_player=0,seed='frenzy-mantis-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_boundaries_and_shared_schedulers(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_frenzy_mantis_v69_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],30)
 def test_all_grades_complete_battle_and_settlement(self):
  compiled=[]
  for raw in [401,10401,20401,4000101,4010101,4020101]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=raw;compiled.append(current.compile_start(row,**self.args(ctx)))
  before=deepcopy(compiled);out=current.simulate_batch([c['battle'] for c in compiled])['results'];self.assertEqual(compiled,before)
  for c,r in zip(compiled,out):
   self.assertTrue(r.get('terminated'),r);self.assertTrue(calculate_terminal_damage(c,r)['resolved']);self.assertFalse(r['training_label_allowed'])
   self.assertTrue(r['frenzy_mantis_v69']['events'])
 def test_old_sources_unchanged_and_new_mapping_exclusive(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
  row['players'][0]['candidate_start']['board'][0]=401
  with self.assertRaisesRegex(old.UnresolvedBattle,'unmapped_cards'):old.compile_start(row,**self.args(ctx))
 def test_no_terminal_inputs_and_unknown_cards_still_blocked(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=4000101;a=current.compile_start(row,**self.args(ctx))
  row['outcome']={'recorded_hp_delta':-999,'winner':1};self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
  row['players'][0]['candidate_start']['board'][1]=999999
  with self.assertRaisesRegex(current.UnresolvedBattle,'unmapped_cards'):current.compile_start(row,**self.args(ctx))
 def test_identities_and_hidden_upgrade_exclusion(self):
  from tests.test_current_upgrade_sound_v41 import fixture
  facts=current.extension_contract();_,mapping,_,_=current.catalogue()
  for c in facts['cards']:self.assertEqual(mapping[c['raw_id']],c['runtime_id'])
  boards=[[401,10401,20401],[4000101,4010101,4020101]]
  for board in boards:
   row,ctx=fixture(True);row['players'][0]['candidate_start']['board']=board;c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0]
   self.assertTrue(r.get('terminated'),r);e=next(e for e in r['upgrade_sound_v41']['events'] if e['player_index']==0)
   self.assertEqual(e['after_raw'],board);self.assertEqual(e['upgrades'],[])
if __name__=='__main__':unittest.main()
