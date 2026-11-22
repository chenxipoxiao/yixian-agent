from copy import deepcopy
import json,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v112 as old,full_battle_v113 as new
from yixian.combat_start_context_bindings_v8 import FIELD,validate_receipt
from yixian import full_battle_v105

class EngravingSourceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.facts=new.extension_contract();cls.rows={};cls.contexts={}
  plan=json.loads((new.ROOT/'runs/stages/20261115T145600Z-s2-engraving-source/batch-plan-v113.json').read_text('utf8'))
  for c in plan['cohorts']:
   cls.rows.update({r['id']:r for r in map(json.loads,(new.ROOT/c['rows']).read_text('utf8').splitlines())})
   cls.contexts.update(json.loads((new.ROOT/c['contexts']).read_text('utf8')))
  cls.legacy=full_battle_v105.extension_contract()['admitted_records'];cls.compiled={};cls.kw={}
  for rid in cls.facts['active_record_ids']:
   ctx=cls.contexts[rid]
   cls.kw[rid]=dict(first_player=None,seed='diagnostic-'+rid,game_mode=3,season_mec=10,combat_context=ctx)
   cls.compiled[rid]=new.compile_start(cls.rows[rid],**cls.kw[rid])

 def test_all_eight_receipts_preserve_legacy(self):
  for rid,expected in self.facts['admitted_records'].items():
   plain,entries=validate_receipt(self.rows[rid],self.contexts[rid],expected,self.legacy[rid])
   stripped=deepcopy(self.contexts[rid]);del stripped[FIELD]
   self.assertEqual(plain,stripped)
   for e in entries:
    if e:self.assertEqual(set(e['temp_data']),set(map(str,e['selected_strategy_ids'])))
  self.assertEqual(len(self.facts['admitted_records']),8)

 def test_receipt_and_source_mutations_rejected(self):
  rid=self.facts['active_record_ids'][0];expected=self.facts['admitted_records'][rid]
  for mutation in ['grid','missing','source','ownership','board']:
   row=deepcopy(self.rows[rid]);ctx=deepcopy(self.contexts[rid]);p=ctx[FIELD]['players'][0]
   if mutation=='grid':p['present_values']['13017']=True
   elif mutation=='missing':p['present_values'].pop('13017')
   elif mutation=='source':p['complete_temp_map_sha256']='0'*64
   elif mutation=='ownership':p['start_owned_ids']=[]
   else:row['players'][0]['candidate_start']['board'].reverse()
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):validate_receipt(row,ctx,expected,self.legacy[rid])

 def test_selected_grid_and_old_gate(self):
  for rid,compiled in self.compiled.items():
   ctx=self.contexts[rid];grid=ctx[FIELD]['players'][0]['present_values']['13017']
   self.assertIn({'strategy_id':13017,'slot':grid},compiled['battle']['season_engraving']['players'][0])
   plain=deepcopy(ctx);del plain[FIELD]
   with self.assertRaisesRegex(old.UnresolvedBattle,'unsupported_season_combat:13017'):
    old.compile_start(self.rows[rid],**{**self.kw[rid],'combat_context':plain})

 def test_outcome_and_post_battle_fields_are_not_inputs(self):
  rid=self.facts['active_record_ids'][0];row=deepcopy(self.rows[rid]);ctx=deepcopy(self.contexts[rid])
  row['outcome']={'recorded_hp_delta':9999,'winner_snapshot_slot':'p2'}
  for p in ctx['players']:p['after_talent_counters']={'27':999}
  self.assertEqual(self.compiled[rid],new.compile_start(row,**{**self.kw[rid],'combat_context':ctx}))

 def test_unselected_delegation_and13002_stays_blocked(self):
  row,ctx=start_fixture();kw=dict(first_player=0,seed='unbound-control',game_mode=3,season_mec=10,combat_context=ctx)
  self.assertEqual(old.compile_start(row,**kw),new.compile_start(row,**kw))
  rid=next(r for r in self.facts['admitted_records'] if r not in self.facts['active_record_ids'])
  with self.assertRaisesRegex(new.UnresolvedBattle,'unsupported_season_combat:13002'):
   new.compile_start(self.rows[rid],first_player=None,seed='diagnostic-'+rid,game_mode=3,season_mec=10,combat_context=self.contexts[rid])

if __name__=='__main__':unittest.main()
