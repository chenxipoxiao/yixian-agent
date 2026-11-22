from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v109r3 as old,full_battle_v110 as new

class PreparationParameterTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.facts=new.extension_contract();cls.rows={};cls.contexts={};cls.kw={};cls.compiled={}
  plan=json.loads((new.ROOT/'runs/stages/20261115T132600Z-s2-capacity-parameters/batch-plan-v110.json').read_text('utf8'))
  for c in plan['cohorts']:
   cls.rows.update({r['id']:r for r in map(json.loads,(new.ROOT/c['rows']).read_text('utf8').splitlines())})
   cls.contexts.update(json.loads((new.ROOT/c['contexts']).read_text('utf8')))
  for rid,binding in cls.facts['admitted_records'].items():
   row=cls.rows[rid];ctx=cls.contexts[rid]
   first=binding['binding']['first_player'] if old.derive_start_initiative(row,game_mode=3)['candidate_first_index'] is None else None
   cls.kw[rid]=dict(first_player=first,seed='diagnostic-'+rid,game_mode=3,season_mec=10,combat_context=ctx)
   cls.compiled[rid]=new.compile_start(row,**cls.kw[rid])

 def test_physical_start_and_comparison_fields(self):
  for rid in self.compiled:
   with self.subTest(record=rid):
    plain=deepcopy(self.compiled[rid]);plain.pop('replay_parameter_context_v110');plain['battle'].pop('replay_parameters')
    self.assertEqual(old.compile_start(self.rows[rid],**self.kw[rid]),plain)
    row=deepcopy(self.rows[rid]);row['outcome']={'recorded_hp_delta':9999,'winner_snapshot_slot':'p2'}
    ctx=deepcopy(self.contexts[rid])
    for p in ctx['players']:p['after_talent_counters']={'27':999}
    self.assertEqual(self.compiled[rid],new.compile_start(row,**{**self.kw[rid],'combat_context':ctx}))

 def test_source_and_stream_guards(self):
  for rid in self.compiled:
   for mutation in ['board','truncated','bool','evidence','seed']:
    with self.subTest(record=rid,mutation=mutation):
     row=deepcopy(self.rows[rid]);kw=deepcopy(self.kw[rid]);ctx=kw['combat_context']
     if mutation=='board':row['players'][0]['candidate_start']['board'].reverse()
     elif mutation=='truncated':ctx['battle_params']=ctx['battle_params'][:-1]
     elif mutation=='bool':ctx['battle_params'][0]=True
     elif mutation=='evidence':row['battle_params_evidence']['entries']+=1
     else:kw['seed']='changed'
     with self.assertRaises(new.UnresolvedBattle):new.compile_start(row,**kw)

 def test_runtime_binding_guards(self):
  cases=[];reasons=[]
  for compiled in self.compiled.values():
   for mutation,reason in [('hp','compiled_battle_binding_mismatch'),('stream','recorded_stream_mismatch'),('first','exclusive_bound_initiative_required')]:
    b=deepcopy(compiled['battle'])
    if mutation=='hp':b['players'][0]['hp']-=1
    elif mutation=='stream':b['replay_parameters']['stream'][0]+=1
    else:b['mixed_parameters']={}
    cases.append(b);reasons.append(reason)
  for result,reason in zip(new.simulate_batch(cases)['results'],reasons):
   self.assertIn(reason,result['unresolved_reason']);self.assertFalse(result['training_label_allowed']);self.assertNotIn('winner',result)

 def test_unselected_exact_delegation(self):
  row,ctx=start_fixture();kw=dict(first_player=0,seed='unbound-control',game_mode=3,season_mec=10,combat_context=ctx)
  self.assertIs(new.catalogue,old.catalogue);self.assertEqual(old.compile_start(row,**kw),new.compile_start(row,**kw))

 def test_existing_reader_boundaries(self):
  for name in ['current_probability_parameters_v88r2_probe.mjs']:
   with self.subTest(reader=name):
    r=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(new.ROOT/'tests'/name)],capture_output=True,text=True,encoding='utf8',timeout=60)
    self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(json.loads(r.stdout)['passed'])

if __name__=='__main__':unittest.main()
