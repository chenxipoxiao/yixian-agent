from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v60r2 as old,full_battle_v61 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class TemporaryChaseBatchTests(unittest.TestCase):
 def args(self,ctx):return dict(first_player=0,seed='temporary-chase-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_all_scheduler_capacity_payment_cleanup_and_seats(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_temporary_chase_v61_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertEqual(r['scenarios'],39)
 def test_old_mapping_preserved_and_three_new_grades(self):
  before=old.catalogue();after=current.catalogue();self.assertEqual(before[0],after[0]);self.assertEqual(before[2:],after[2:])
  self.assertEqual({k:v for k,v in after[1].items() if k in before[1]},before[1]);self.assertEqual(set(after[1])-set(before[1]),{435,10435,20435})
 def test_complete_battles_grades_with_immutable_inputs(self):
  compiled=[]
  for raw in [435,10435,20435]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[raw,raw,0]
   with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
   compiled.append(current.compile_start(row,**self.args(ctx)))
  before=deepcopy(compiled);results=current.simulate_batch([c['battle'] for c in compiled])['results'];self.assertEqual(before,compiled)
  for c,b in zip(compiled,results):
   self.assertTrue(b['terminated']);self.assertFalse(b['used_randomness']);self.assertFalse(b['training_label_allowed'])
   self.assertTrue(b['temporary_chase_v61']['events']);self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
 def test_unaffected_full_output_unchanged(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_legacy_fate_and_engraving_contexts_remain_blocked(self):
  for key,value in [('talents',[221]),('talents',[222]),('talents',[221,222]),('used_keyin_cards',[40067]),('permanentBuffTempDatas',{'572':1,'10024':6})]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[435,0,0];row['players'][0]['candidate_start'][key]=value
   with self.subTest(key=key,value=value),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_current_engraving_downgrade_all_grades(self):
  for raw in [435,10435,20435]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[raw,0,0]
   row['players'][1]['candidate_start']['xian_mo_strategies']=[13007]
   ctx['players'][1]['season_engraving_input']={'origin':'privateData.xianMoData.tempDatas:preparation_grid_selection','selected_strategy_ids':[13007],'slots':{'13007':0}}
   c=current.compile_start(row,**{**self.args(ctx),'first_player':1});b=current.simulate_batch([c['battle']])['results'][0]
   self.assertTrue(b['terminated']);event=next(e for e in b['temporary_chase_v61']['events'] if e['kind']=='card_body')
   self.assertEqual(event['raw_id'],raw if raw==435 else raw-10000)
 def test_terminal_fields_do_not_change_start(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[435,0,0];before=current.compile_start(row,**self.args(ctx))
  row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':99999};ctx['players'][0]['after_talent_counters']={'572':999}
  self.assertEqual(before,current.compile_start(row,**self.args(ctx)))
 def test_budget_truncation_has_no_winner_or_settlement(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[435,0,0];c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
  b=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
