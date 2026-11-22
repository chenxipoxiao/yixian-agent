from copy import deepcopy
import json,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v101 as old,full_battle_v102 as new
S=new.ROOT/'runs/stages/20261115T091700Z-s2-flag-hand-parameter-binding'

class FlagPaperParameterTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.facts=new.extension_contract();cls.rows={};cls.contexts={};cls.old_contexts={}
  plan=json.loads((S.parent/'20261115T084700Z-s2-falling-paper-mixed-binding/batch-plan.json').read_text('utf8'))
  for c in plan['cohorts']:
   cls.rows.update({r['id']:r for r in map(json.loads,(new.ROOT/c['rows']).read_text('utf8').splitlines())});cls.old_contexts.update(json.loads((new.ROOT/c['contexts']).read_text('utf8')))
  cls.contexts={**cls.old_contexts,**json.loads((S/'combat-context-v5-bound.json').read_text('utf8'))}
  cls.rid=next(iter(cls.facts['admitted_records']));cls.kw=dict(first_player=None,seed='diagnostic-'+cls.rid,game_mode=3,season_mec=10,combat_context=cls.contexts[cls.rid])
  cls.compiled=new.compile_start(cls.rows[cls.rid],**cls.kw)

 def test_original_hand_and_full_stream_guards(self):
  self.assertIs(new.catalogue,old.catalogue);row=self.rows[self.rid]
  with self.assertRaisesRegex(old.UnresolvedBattle,'element_flag_hand_source_binding_required'):old.compile_start(row,**{**self.kw,'combat_context':self.old_contexts[self.rid]})
  changed=deepcopy(row);changed['outcome']={'recorded_hp_delta':9999};ctx=deepcopy(self.kw['combat_context'])
  for p in ctx['players']:p['after_talent_counters']={'27':999}
  self.assertEqual(self.compiled,new.compile_start(changed,**{**self.kw,'combat_context':ctx}))
  for action in ['remove','reverse']:
   ctx=deepcopy(self.kw['combat_context'])
   if action=='remove':del ctx['players'][0]['element_flag_hand']
   else:ctx['players'][0]['element_flag_hand']['raw_cards'].reverse()
   with self.assertRaisesRegex(new.UnresolvedBattle,'original_snapshot_mismatch'):new.compile_start(row,**{**self.kw,'combat_context':ctx})
  ctx=deepcopy(self.kw['combat_context']);ctx['battle_params']=ctx['battle_params'][:-1]
  with self.assertRaisesRegex(new.UnresolvedBattle,'recorded_stream_mismatch'):new.compile_start(row,**{**self.kw,'combat_context':ctx})
  with self.assertRaisesRegex(new.UnresolvedBattle,'unaudited_compiled_start'):new.compile_start(row,**{**self.kw,'seed':'changed-seed'})
  fixture,context=start_fixture();kw=dict(first_player=0,seed='unbound-control',game_mode=3,season_mec=10,combat_context=context)
  self.assertEqual(old.compile_start(fixture,**kw),new.compile_start(fixture,**kw))

 def test_runtime_bindings_reject_tampering(self):
  a=deepcopy(self.compiled['battle']);a['element_flag']['hands'][0].reverse()
  b=deepcopy(self.compiled['battle']);b['paper_mixed_parameters']['stream'][1]+=10000
  c=deepcopy(self.compiled['battle']);c['paper_mixed_parameters']['record_binding']['record_id']='forged'
  results=new.simulate_batch([a,b,c])['results']
  for result,reason in zip(results,['compiled_battle_binding_mismatch','recorded_stream_mismatch','unaudited_record_binding']):
   self.assertIn(reason,result['unresolved_reason']);self.assertFalse(result['training_label_allowed'])

 def test_selected_card_reader_boundaries(self):
  result=subprocess.run(['node','--experimental-default-type=module','tests/flag_parameter_reader_v102_checks.mjs'],cwd=new.ROOT,capture_output=True,text=True,encoding='utf8',timeout=30)
  self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
