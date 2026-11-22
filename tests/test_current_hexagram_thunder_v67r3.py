from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v66r2 as old, full_battle_v67r2 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class HexagramThunderTests(unittest.TestCase):
 def args(self,ctx):return dict(first_player=0,seed='hexagram-thunder-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_boundaries_and_shared_schedulers(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_hexagram_thunder_v67r2_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],35)
 def test_all_grades_complete_battle_and_settlement(self):
  compiled=[]
  for raw in [4000100,4010100,4020100,4000108,4010108,4020108,4000102,4010102,4020102]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=raw;compiled.append(current.compile_start(row,**self.args(ctx)))
  before=deepcopy(compiled);out=current.simulate_batch([c['battle'] for c in compiled])['results'];self.assertEqual(compiled,before)
  for c,r in zip(compiled,out):
   self.assertTrue(r.get('terminated'),r);self.assertTrue(calculate_terminal_damage(c,r)['resolved']);self.assertFalse(r['training_label_allowed'])
   self.assertTrue(r['hexagram_thunder_v67']['events']);self.assertFalse(r['hexagram_thunder_v67']['random_outcomes_reconstructed'])
 def test_old_source_unchanged_and_new_mapping_exclusive(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
  row['players'][0]['candidate_start']['board'][0]=4000108
  with self.assertRaisesRegex(old.UnresolvedBattle,'unmapped_cards'):old.compile_start(row,**self.args(ctx))
 def test_no_terminal_inputs_and_unknown_cards_still_blocked(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=4000100;a=current.compile_start(row,**self.args(ctx))
  row['outcome']={'recorded_hp_delta':-999,'winner':1};self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
  row['players'][0]['candidate_start']['board'][1]=999999
  with self.assertRaisesRegex(current.UnresolvedBattle,'unmapped_cards'):current.compile_start(row,**self.args(ctx))
 def test_new_aliases_are_fully_bound_to_fixed_card_table(self):
  facts=current.extension_contract();_,mapping,_,_=current.catalogue()
  for c in facts['cards']:
   self.assertEqual(mapping[c['raw_id']],c['runtime_id'])
   meta=facts['extra_transform_cards'][str(c['raw_id'])];self.assertEqual(meta['rarity'],c['config']['rarity'])
   self.assertEqual(facts['neighbor_is_thunder'][c['runtime_id']], '雷' in c['config']['name'])
 def test_upgrade_sound_uses_current_identities_and_preserves_hidden_cards(self):
  from tests.test_current_upgrade_sound_v41 import fixture
  for enabled in [False,True]:
   row,ctx=fixture(enabled);row['players'][0]['candidate_start']['board']=[4000108,4000102,4000100]
   saved=deepcopy(row);c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0]
   self.assertTrue(r.get('terminated'),r);self.assertEqual(row,saved)
   e=next(e for e in r['upgrade_sound_v41']['events'] if e['player_index']==0)
   self.assertEqual(e['after_raw'],[4020108,4020102,4000100] if enabled else [4000108,4000102,4000100])
   self.assertEqual(len(e['upgrades']),4 if enabled else 0)
if __name__=='__main__':unittest.main()
