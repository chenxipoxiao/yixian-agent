from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_current_falling_paper_v45 import fixture as paper_fixture
from tests.test_full_battle import start_fixture
from yixian import full_battle_v45 as old,full_battle_v46 as current

def certify(row,ctx,first=0):
 row['battle_params_evidence']={'entries':len(ctx['battle_params']),'sha256':current.digest_json(ctx['battle_params'])}
 ctx['typed_parameter_record']={'snapshot_sha256':current.snapshot_binding(row,ctx),'scope':'unchanged_recorded_battle_only','first_player':first}

def fixture():
 row,ctx=paper_fixture(3);row['players'][0]['candidate_start']['board'][0]=4000017
 ctx['battle_params']=[3,16];certify(row,ctx);return row,ctx

class TypedParametersTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='typed-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_consumers_order_and_failure_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_typed_parameters_v46_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertEqual(r['scenarios'],33)
 def test_old_inputs_and_full_outputs_unchanged(self):
  cases=[]
  for maker in [start_fixture,paper_fixture]:
   row,ctx=maker();a=self.args(ctx);x=old.compile_start(row,**a);y=current.compile_start(row,**a);self.assertEqual(x,y);cases.append(x['battle'])
  self.assertEqual(old.simulate_batch(cases)['results'],current.simulate_batch(cases)['results'])
 def test_new_source_and_context_not_mutated(self):
  row,ctx=fixture();saved=deepcopy((row,ctx));c=current.compile_start(row,**self.args(ctx));self.assertEqual(saved,(row,ctx))
  self.assertNotIn('falling_paper',c['battle']);self.assertEqual(c['battle']['typed_parameters']['stream'],[3,16]);self.assertFalse(c['typed_parameter_context']['training_label_allowed'])
 def test_outcomes_and_poststate_do_not_change_compilation(self):
  row,ctx=fixture();a=current.compile_start(row,**self.args(ctx));row['outcome']={'recorded_hp_delta':9999,'winner_snapshot_slot':'p2'};ctx['players'][0]['after_talent_counters']={'x':999}
  self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_original_start_and_initiative_bound(self):
  row,ctx=fixture()
  with self.assertRaisesRegex(current.UnresolvedBattle,'initiative_binding_mismatch'):current.compile_start(row,**self.args(ctx,1))
  row['players'][0]['candidate_start']['exp']+=1
  with self.assertRaisesRegex(current.UnresolvedBattle,'snapshot_binding_mismatch'):current.compile_start(row,**self.args(ctx))
 def test_source_parameter_provenance_required(self):
  for value in [[3,15],[],[3],[-1,16],[3,True],None]:
   row,ctx=fixture();ctx['battle_params']=value
   with self.subTest(value=value),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_explicit_optin_and_supported_content_required(self):
  row,ctx=fixture();del ctx['typed_parameter_record']
  with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
  for field,value in [('xian_mo_strategies',[16024,7059]),('talents',[999999]),('board',[0,9999999,0])]:
   row,ctx=fixture();row['players'][0]['candidate_start'][field]=value;certify(row,ctx)
   with self.subTest(field=field),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_compiled_changes_block_before_execution(self):
  battles=[]
  for field,value in [('first_player',1),('seed','changed'),('max_turns',1)]:
   row,ctx=fixture();b=current.compile_start(row,**self.args(ctx))['battle'];b[field]=value;battles.append(b)
  for r in current.simulate_batch(battles)['results']:
   self.assertIn('compiled_battle_binding_mismatch',r['unresolved_reason']);self.assertNotIn('winner',r)
 def test_queue_overrun_is_unresolved_without_winner(self):
  row,ctx=fixture();c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0]
  self.assertIn('parameter_underflow',r['unresolved_reason']);self.assertNotIn('winner',r);self.assertFalse(r['training_label_allowed'])

if __name__=='__main__':unittest.main()
