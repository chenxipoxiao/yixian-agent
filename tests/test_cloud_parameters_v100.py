from copy import deepcopy
import json,unittest
from pathlib import Path
from tests.test_full_battle import start_fixture
from yixian import full_battle_v99 as old,full_battle_v100 as new
class CloudParameterTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.facts=new.extension_contract();cls.rows={};cls.contexts={}
  plan=json.loads((new.ROOT/'runs/stages/20261115T074700Z-s2-cloud-shadow-batch/batch-plan.json').read_text('utf8'))
  for c in plan['cohorts']:
   cls.rows.update({r['id']:r for r in map(json.loads,(new.ROOT/c['rows']).read_text('utf8').splitlines())});cls.contexts.update(json.loads((new.ROOT/c['contexts']).read_text('utf8')))
  cls.rid=next(iter(cls.facts['admitted_records']));row=cls.rows[cls.rid];ctx=cls.contexts[cls.rid]
  first=cls.facts['admitted_records'][cls.rid]['binding']['first_player'] if old.derive_start_initiative(row,game_mode=3)['candidate_first_index'] is None else None
  cls.kw=dict(first_player=first,seed='diagnostic-'+cls.rid,game_mode=3,season_mec=10,combat_context=ctx)
  cls.compiled=new.compile_start(row,**cls.kw)
 def test_original_snapshot_and_full_stream_guards(self):
  self.assertIs(new.catalogue,old.catalogue)
  row=self.rows[self.rid];base=old.compile_start(row,**self.kw);plain=deepcopy(self.compiled);plain.pop('mixed_parameter_context_v100');plain['battle'].pop('mixed_parameters');self.assertEqual(base,plain)
  changed=deepcopy(row);changed['outcome']={'recorded_hp_delta':9999,'winner_snapshot_slot':'p2'};ctx=deepcopy(self.kw['combat_context'])
  for p in ctx['players']:p['after_talent_counters']={'27':999}
  self.assertEqual(self.compiled,new.compile_start(changed,**{**self.kw,'combat_context':ctx}))
  changed=deepcopy(row);changed['players'][0]['candidate_start']['board'].reverse()
  with self.assertRaisesRegex(new.UnresolvedBattle,'original_snapshot_mismatch'):new.compile_start(changed,**self.kw)
  ctx=deepcopy(self.kw['combat_context']);ctx['battle_params']=ctx['battle_params'][:-1]
  with self.assertRaisesRegex(new.UnresolvedBattle,'recorded_stream_mismatch'):new.compile_start(row,**{**self.kw,'combat_context':ctx})
  with self.assertRaisesRegex(new.UnresolvedBattle,'unaudited_compiled_start'):new.compile_start(row,**{**self.kw,'seed':'changed-seed'})
  fixture,context=start_fixture();kw=dict(first_player=0,seed='unbound-control',game_mode=3,season_mec=10,combat_context=context)
  self.assertEqual(old.compile_start(fixture,**kw),new.compile_start(fixture,**kw))
 def test_runtime_tampering_rejected(self):
  a=deepcopy(self.compiled['battle']);a['players'][0]['hp']-=1
  b=deepcopy(self.compiled['battle']);b['mixed_parameters']['stream'][0]+=1
  c=deepcopy(self.compiled['battle']);c['mixed_parameters']['record_binding']['record_id']='forged'
  results=new.simulate_batch([a,b,c])['results']
  for result,reason in zip(results,['compiled_battle_binding_mismatch','recorded_stream_mismatch','unaudited_record_binding']):
   self.assertIn(reason,result['unresolved_reason']);self.assertFalse(result['training_label_allowed'])
if __name__=='__main__':unittest.main()
