from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v113 as old,full_battle_v114 as new
from yixian.combat_engraving_start_v114 import compile_exorcism_start


class ExorcismParametersTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.facts=new.extension_contract();cls.rows={};cls.contexts={}
  plan=json.loads((new.ROOT/'runs/stages/20261115T145600Z-s2-engraving-source/batch-plan-v113.json').read_text('utf8'))
  for c in plan['cohorts']:
   cls.rows.update({r['id']:r for r in map(json.loads,(new.ROOT/c['rows']).read_text('utf8').splitlines())})
   cls.contexts.update(json.loads((new.ROOT/c['contexts']).read_text('utf8')))
  cls.tables=new.catalogue();cls.compiled={};cls.kw={}
  for rid,expected in cls.facts['admitted_records'].items():
   ctx=cls.contexts[rid]
   cls.kw[rid]=dict(first_player=expected['binding']['first_player'],seed='diagnostic-'+rid,game_mode=3,season_mec=10,combat_context=ctx,tables=cls.tables)
   cls.compiled[rid]=new.compile_start(cls.rows[rid],**cls.kw[rid])

 def test_shared_queue_callbacks_and_rejections(self):
  r=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(new.ROOT/'tests/current_exorcism_parameters_v114_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(json.loads(r.stdout)['passed'])

 def test_all_six_add_only_bound_stream(self):
  self.assertEqual(len(self.compiled),6)
  for rid,compiled in self.compiled.items():
   b=deepcopy(compiled);del b['battle']['replay_parameters'];del b['replay_parameter_context_v114']
   self.assertEqual(b,compile_exorcism_start(self.rows[rid],**self.kw[rid]))
   with self.assertRaisesRegex(old.UnresolvedBattle,'unsupported_season_combat:13002'):
    old.compile_start(self.rows[rid],**self.kw[rid])

 def test_terminal_fields_do_not_change_inputs(self):
  rid=next(iter(self.compiled));row=deepcopy(self.rows[rid]);ctx=deepcopy(self.contexts[rid])
  row['outcome']={'recorded_hp_delta':9999,'winner_snapshot_slot':'p2'}
  for p in ctx['players']:p['after_talent_counters']={'27':999}
  self.assertEqual(self.compiled[rid],new.compile_start(row,**{**self.kw[rid],'combat_context':ctx}))

 def test_start_receipt_stream_and_seed_mutations_rejected(self):
  rid=next(iter(self.compiled))
  for kind in ['stream','bool','evidence','grid','source','seed']:
   row=deepcopy(self.rows[rid]);ctx=deepcopy(self.contexts[rid]);kw={**self.kw[rid],'combat_context':ctx}
   if kind=='stream':ctx['battle_params'][0]=100
   elif kind=='bool':ctx['battle_params'][0]=True
   elif kind=='evidence':row['battle_params_evidence']['entries']+=1
   elif kind=='grid':ctx['original_engraving_slots_v8']['players'][0]['present_values']={'13002':7}
   elif kind=='source':ctx['source_raw_sha256']='0'*64
   else:kw['seed']='changed'
   with self.subTest(kind=kind),self.assertRaises(new.UnresolvedBattle):new.compile_start(row,**kw)

 def test_runtime_cannot_rebind_changed_start(self):
  battle=next(iter(self.compiled.values()))['battle'];items=[]
  for kind in ['seed','stream','record']:
   b=deepcopy(battle)
   if kind=='seed':b['seed']='changed'
   elif kind=='stream':b['replay_parameters']['stream'][0]=100
   else:b['replay_parameters']['record_binding']['record_id']='invented'
   b['replay_parameters']['battle_sha256']=new.digest_json({k:v for k,v in b.items() if k!='replay_parameters'})
   items.append(b)
  for result in new.simulate_batch(items)['results']:
   self.assertIn('unresolved',result['unresolved_reason']);self.assertNotIn('winner',result)

 def test_unselected_delegation(self):
  row,ctx=start_fixture();kw=dict(first_player=0,seed='unbound-control',game_mode=3,season_mec=10,combat_context=ctx)
  self.assertEqual(old.compile_start(row,**kw),new.compile_start(row,**kw))

if __name__=='__main__':unittest.main()
