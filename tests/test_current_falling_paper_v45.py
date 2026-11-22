from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from tests.test_current_clouds_rain_v35 import fixture as cloud_fixture
from yixian import full_battle_v44r2 as old,full_battle_v45 as current
from yixian.terminal_damage_v38 import calculate_terminal_damage

def certify(row,ctx):
 row['battle_params_evidence']={'entries':len(ctx['battle_params']),'sha256':current.digest_json(ctx['battle_params'])}
 ctx['falling_paper_record']={'snapshot_sha256':current.snapshot_binding(row,ctx),'scope':'unchanged_recorded_battle_only'}

def fixture(branch=0,both=False):
 row,ctx=start_fixture();row['game_id']='software-only';row['players'][0]['candidate_start']['xian_mo_strategies']=[16024]
 if both:row['players'][1]['candidate_start']['xian_mo_strategies']=[16024]
 ctx['battle_params']=[branch]*(2 if both else 1);certify(row,ctx);return row,ctx

class FallingPaperTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='paper-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_falling_paper_v45_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout),{'passed':True,'scenarios':31})
 def test_unowned_inputs_and_full_outputs_identical(self):
  for maker in [start_fixture,cloud_fixture]:
   row,ctx=maker();a=self.args(ctx);x=old.compile_start(row,**a);y=current.compile_start(row,**a)
   self.assertEqual(x,y);self.assertEqual(old.simulate_batch([x['battle']])['results'],current.simulate_batch([y['battle']])['results'])
 def test_all_branches_complete_without_mutating_source(self):
  compiled=[]
  for first in [0,1]:
   for branch in range(4):
    row,ctx=fixture(branch);saved=deepcopy((row,ctx));c=current.compile_start(row,**self.args(ctx,first));compiled.append(c)
    self.assertEqual(saved,(row,ctx));self.assertEqual(c['effect_players'][0]['season_choices'],[16024]);self.assertFalse(c['falling_paper_context']['counterfactual_reuse_allowed'])
  results=current.simulate_batch([c['battle'] for c in compiled])['results']
  for c,r in zip(compiled,results):
   self.assertTrue(r['terminated'],r);self.assertTrue(r['used_randomness']);self.assertFalse(r['training_label_allowed'])
   self.assertEqual(r['falling_paper_v45']['consumed'],1);self.assertEqual(r['falling_paper_v45']['events'][0]['player_index'],0)
   self.assertTrue(calculate_terminal_damage(c,r)['resolved']);self.assertFalse(r['falling_paper_v45']['distribution_verified'])
 def test_two_owners_consume_in_actual_initiative_order(self):
  for first in [0,1]:
   row,ctx=fixture(0,True);ctx['battle_params']=[1,3];certify(row,ctx)
   c=current.compile_start(row,**self.args(ctx,first));r=current.simulate_batch([c['battle']])['results'][0]
   self.assertEqual([(e['player_index'],e['branch']) for e in r['falling_paper_v45']['events']],[(first,1),(1-first,3)])
 def test_outcomes_and_poststate_cannot_change_input(self):
  row,ctx=fixture();before=current.compile_start(row,**self.args(ctx));row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':9999}
  ctx['players'][0]['after_talent_counters']={'16024':999};ctx['players'][0]['start_private_field_names']=['ignored']
  self.assertEqual(before,current.compile_start(row,**self.args(ctx)))
 def test_changed_start_or_context_is_not_counterfactual_input(self):
  for kind in ['board','exp','hand_count','round','game_id']:
   row,ctx=fixture()
   if kind=='board':row['players'][0]['candidate_start']['board'][0]=101
   if kind=='exp':row['players'][0]['candidate_start']['exp']+=1
   if kind=='hand_count':ctx['players'][0]['hand_count']+=1
   if kind=='round':row['round']+=1
   if kind=='game_id':row['game_id']='changed'
   with self.subTest(kind=kind),self.assertRaisesRegex(current.UnresolvedBattle,'snapshot_binding_mismatch'):current.compile_start(row,**self.args(ctx))
 def test_parameter_evidence_and_complete_queue_required(self):
  for params in [None,[],[0,1],[4],[-1],[True],[1.5],[1]]:
   row,ctx=fixture();ctx['battle_params']=params
   with self.subTest(params=params),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
  row,ctx=fixture();del ctx['falling_paper_record']
  with self.assertRaisesRegex(current.UnresolvedBattle,'snapshot_binding_mismatch'):current.compile_start(row,**self.args(ctx))
 def test_unknown_other_content_remains_blocked(self):
  for key,val in [('xian_mo_strategies',[16024,7059]),('talents',[999999]),('board',[0,99999999,0])]:
   row,ctx=fixture();row['players'][0]['candidate_start'][key]=val;certify(row,ctx)
   with self.subTest(key=key),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_compiled_battle_cannot_reuse_record_stream_after_mutation(self):
  row,ctx=fixture();c=current.compile_start(row,**self.args(ctx));c['battle']['players'][0]['hp']-=1
  r=current.simulate_batch([c['battle']])['results'][0];self.assertIn('compiled_battle_binding_mismatch',r['unresolved_reason']);self.assertNotIn('winner',r)
 def test_explicit_software_truncation_produces_no_settlement(self):
  row,ctx=fixture();c=current.compile_start(row,**self.args(ctx));b=c['battle'];b['max_turns']=1
  b['falling_paper']['battle_sha256']=current.digest_json({k:v for k,v in b.items() if k!='falling_paper'})
  r=current.simulate_batch([b])['results'][0];self.assertTrue(r['truncated']);self.assertIsNone(r['winner']);self.assertFalse(calculate_terminal_damage(c,r)['resolved'])

if __name__=='__main__':unittest.main()
