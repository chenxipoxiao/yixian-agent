from copy import deepcopy
import json,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v96 as old,full_battle_v97 as new

class ReplayBindingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.facts=new.extension_contract()
  root=new.ROOT/'runs/stages/20261115T011300Z-s2-second-training-pilot/source-intake'
  cls.rows={r['id']:r for r in map(json.loads,(root/'evidence-rounds.jsonl').read_text('utf8').splitlines())}
  cls.contexts=json.loads((root/'combat-context.json').read_text('utf8'))
  cls.rid=next(iter(cls.facts['admitted_records']))
  row=cls.rows[cls.rid];ctx=cls.contexts[cls.rid];first=cls.facts['admitted_records'][cls.rid]['binding']['first_player']
  cls.kw={'first_player':first,'seed':'diagnostic-'+cls.rid,'game_mode':3,'season_mec':10,'combat_context':ctx}
  cls.compiled=new.compile_start(row,**cls.kw)

 def test_source_binding_and_nonleak(self):
  self.assertIs(new.catalogue,old.catalogue)
  row=self.rows[self.rid];saved=deepcopy(row);base=old.compile_start(row,**self.kw)
  plain=deepcopy(self.compiled);plain.pop('replay_parameter_context_v97');plain['battle'].pop('replay_parameters')
  self.assertEqual(base,plain);self.assertEqual(saved,row)
  changed=deepcopy(row);changed['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':9999}
  ctx=deepcopy(self.kw['combat_context'])
  for p in ctx['players']:p['after_talent_counters']={'27':999}
  self.assertEqual(self.compiled,new.compile_start(changed,**{**self.kw,'combat_context':ctx}))
  changed=deepcopy(row);changed['players'][0]['candidate_start']['board'].reverse()
  with self.assertRaisesRegex(new.UnresolvedBattle,'original_snapshot_mismatch'):new.compile_start(changed,**self.kw)
  ctx=deepcopy(self.kw['combat_context']);ctx['battle_params'][0]+=1
  with self.assertRaisesRegex(new.UnresolvedBattle,'recorded_stream_mismatch'):new.compile_start(row,**{**self.kw,'combat_context':ctx})
  with self.assertRaisesRegex(new.UnresolvedBattle,'unaudited_compiled_start'):new.compile_start(row,**{**self.kw,'seed':'other-seed'})
  fixture,context=start_fixture();kw=dict(first_player=0,seed='unbound-control',game_mode=3,season_mec=10,combat_context=context)
  self.assertEqual(old.compile_start(fixture,**kw),new.compile_start(fixture,**kw))

 def test_runtime_binding_guards(self):
  cases=[]
  altered=deepcopy(self.compiled['battle']);altered['players'][0]['hp']-=1;cases.append(altered)
  altered=deepcopy(self.compiled['battle']);altered['replay_parameters']['stream'][0]+=1;cases.append(altered)
  altered=deepcopy(self.compiled['battle']);altered['replay_parameters']['record_binding']['record_id']='forged';cases.append(altered)
  result=new.simulate_batch(cases)['results']
  self.assertEqual(len(result),3)
  for r,reason in zip(result,['compiled_battle_binding_mismatch','recorded_stream_mismatch','unaudited_record_binding']):
   self.assertIn(reason,r['unresolved_reason']);self.assertFalse(r['training_label_allowed'])
if __name__=='__main__':unittest.main()
