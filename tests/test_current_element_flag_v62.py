from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v61 as old,full_battle_v62 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage
from yixian.combat_validation_batch_v2 import validate_flag_context

def fixture(hand=None,raw=7000111,slot=0):
 row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][slot]=raw
 hand=[7000023] if hand is None else hand
 p=ctx['players'][0];p['hand_count']=len(hand)
 p['element_flag_hand']={'origin':'publicData.lastRoundData.handCards','raw_cards':hand,'source_raw_sha256':row['source']['raw_sha256'],
  'record_id':row['id'],'round':row['round'],'board':deepcopy(row['players'][0]['candidate_start']['board']),'environment_only':True}
 return row,ctx

class ElementFlagTests(unittest.TestCase):
 def args(self,ctx):return dict(first_player=0,seed='flag-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_selection_grades_parity_temporary_hooks(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_element_flag_v62_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertEqual(r['scenarios'],67)
 def test_all_flag_grades_and_even_odd_full_battles(self):
  compiled=[]
  for raw in [7000111,7010111,7020111]:
   for slot in [0,1]:
    row,ctx=fixture([7020023,7020009],raw,slot);compiled.append(current.compile_start(row,**self.args(ctx)))
  before=deepcopy(compiled);rs=current.simulate_batch([x['battle'] for x in compiled])['results'];self.assertEqual(compiled,before)
  for c,r in zip(compiled,rs):
   self.assertTrue(r['terminated']);self.assertFalse(r['used_randomness']);self.assertTrue(calculate_terminal_damage(c,r)['resolved']);self.assertFalse(r['training_label_allowed']);self.assertTrue(r['element_flag_v62']['events'])
 def test_missing_or_wrong_opening_hand_rejected(self):
  for key,value in [('record_id','wrong'),('round',2),('board',[0,0,0]),('source_raw_sha256','wrong'),('origin','postbattle'),('raw_cards',None),('raw_cards',[True]),('environment_only',False)]:
   row,ctx=fixture();ctx['players'][0]['element_flag_hand'][key]=value
   with self.subTest(key=key,value=value),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
  row,ctx=fixture();del ctx['players'][0]['element_flag_hand']
  with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_empty_known_hand_is_executable(self):
  row,ctx=fixture([]);c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(r['terminated'])
 def test_dream_target_is_rejected_without_later_substitution(self):
  row,ctx=fixture([7040090,7000031]);c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0]
  self.assertEqual(r['unresolved_reason'],'element_flag_unresolved:unmapped_first_formation:7040090');self.assertFalse(calculate_terminal_damage(c,r)['resolved'])
 def test_terminal_fields_do_not_change_input(self):
  row,ctx=fixture();a=current.compile_start(row,**self.args(ctx));row['outcome']={'recorded_hp_delta':99999};ctx['players'][0]['after_talent_counters']={'100':99}
  self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_old_full_input_output_unchanged(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_current_engraving_transforms_flag_identity(self):
  for raw in [7000111,7010111,7020111]:
   row,ctx=fixture([7020023],raw);row['players'][1]['candidate_start']['xian_mo_strategies']=[13007]
   ctx['players'][1]['season_engraving_input']={'origin':'privateData.xianMoData.tempDatas:preparation_grid_selection','selected_strategy_ids':[13007],'slots':{'13007':0}}
   c=current.compile_start(row,**{**self.args(ctx),'first_player':1});r=current.simulate_batch([c['battle']])['results'][0]
   self.assertTrue(r['terminated']);self.assertEqual(r['element_flag_v62']['events'][0]['raw_id'],max(raw-10000,7000111))
 def test_context_additions_are_strictly_bounded(self):
  row,new=fixture();oldctx=deepcopy(new);del oldctx['players'][0]['element_flag_hand'];rid=row['id']
  self.assertEqual(len(validate_flag_context([row],{rid:oldctx},{rid:new},[rid])),1)
  with self.assertRaises(ValueError):validate_flag_context([row],{rid:oldctx},{rid:new},[])
  for key,val in [('hand_count',999),('public_level',3),('after_talent_counters',{'27':1})]:
   bad=deepcopy(new);bad['players'][1][key]=val
   with self.subTest(key=key),self.assertRaises(ValueError):validate_flag_context([row],{rid:oldctx},{rid:bad},[rid])
 def test_no_new_mapping_other_than_three_flags(self):
  a=old.catalogue()[1];b=current.catalogue()[1];self.assertEqual(set(b)-set(a),{7000111,7010111,7020111});self.assertEqual(a,{k:v for k,v in b.items() if k in a})

if __name__=='__main__':unittest.main()
