from copy import deepcopy
import json,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v100 as old,full_battle_v101 as new

class PaperMixedParameterTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.facts=new.extension_contract();cls.rows={};cls.contexts={}
  plan=json.loads((new.ROOT/'runs/stages/20261115T081700Z-s2-cloud-parameter-binding/batch-plan.json').read_text('utf8'))
  for c in plan['cohorts']:
   cls.rows.update({r['id']:r for r in map(json.loads,(new.ROOT/c['rows']).read_text('utf8').splitlines())});cls.contexts.update(json.loads((new.ROOT/c['contexts']).read_text('utf8')))
  cls.rid=next(rid for rid,e in cls.facts['admitted_records'].items() if e['compiled_battle_sha256'])
  row=cls.rows[cls.rid];ctx=cls.contexts[cls.rid]
  first=cls.facts['admitted_records'][cls.rid]['binding']['first_player'] if old.derive_start_initiative(row,game_mode=3)['candidate_first_index'] is None else None
  cls.kw=dict(first_player=first,seed='diagnostic-'+cls.rid,game_mode=3,season_mec=10,combat_context=ctx)
  cls.compiled=new.compile_start(row,**cls.kw)

 def test_source_binding_and_unknown_hand_boundary(self):
  self.assertIs(new.catalogue,old.catalogue);row=self.rows[self.rid]
  with self.assertRaisesRegex(old.UnresolvedBattle,'falling_paper_other_parameter_consumers_unresolved'):old.compile_start(row,**self.kw)
  changed=deepcopy(row);changed['outcome']={'recorded_hp_delta':9999,'winner_snapshot_slot':'p2'};ctx=deepcopy(self.kw['combat_context'])
  for p in ctx['players']:p['after_talent_counters']={'27':999}
  self.assertEqual(self.compiled,new.compile_start(changed,**{**self.kw,'combat_context':ctx}))
  changed=deepcopy(row);changed['players'][0]['candidate_start']['board'].reverse()
  with self.assertRaisesRegex(new.UnresolvedBattle,'original_snapshot_mismatch'):new.compile_start(changed,**self.kw)
  ctx=deepcopy(self.kw['combat_context']);ctx['battle_params']=ctx['battle_params'][:-1]
  with self.assertRaisesRegex(new.UnresolvedBattle,'recorded_stream_mismatch'):new.compile_start(row,**{**self.kw,'combat_context':ctx})
  with self.assertRaisesRegex(new.UnresolvedBattle,'unaudited_compiled_start'):new.compile_start(row,**{**self.kw,'seed':'changed-seed'})
  for rid,e in self.facts['admitted_records'].items():
   if e['compiled_battle_sha256'] is not None:continue
   with self.assertRaisesRegex(new.UnresolvedBattle,'element_flag_hand_source_binding_required:0'):
    new.compile_start(self.rows[rid],first_player=None,seed='diagnostic-'+rid,game_mode=3,season_mec=10,combat_context=self.contexts[rid])
  fixture,context=start_fixture();kw=dict(first_player=0,seed='unbound-control',game_mode=3,season_mec=10,combat_context=context)
  self.assertEqual(old.compile_start(fixture,**kw),new.compile_start(fixture,**kw))

 def test_runtime_tampering_rejected(self):
  a=deepcopy(self.compiled['battle']);a['players'][0]['hp']-=1
  b=deepcopy(self.compiled['battle']);b['paper_mixed_parameters']['stream'][0]+=1
  c=deepcopy(self.compiled['battle']);c['paper_mixed_parameters']['record_binding']['record_id']='forged'
  d=deepcopy(self.compiled['battle']);d['paper_mixed_parameters']['owners'].reverse()
  results=new.simulate_batch([a,b,c,d])['results']
  for result,reason in zip(results,['compiled_battle_binding_mismatch','recorded_stream_mismatch','unaudited_record_binding','opening_owners_mismatch']):
   self.assertIn(reason,result['unresolved_reason']);self.assertFalse(result['training_label_allowed'])

 def test_single_queue_opening_card_boundaries(self):
  result=subprocess.run(['node','--experimental-default-type=module','tests/paper_mixed_queue_v101_checks.mjs'],cwd=new.ROOT,capture_output=True,text=True,encoding='utf8',timeout=30)
  self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
