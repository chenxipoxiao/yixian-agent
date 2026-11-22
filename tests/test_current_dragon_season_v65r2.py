from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v64 as old,full_battle_v65 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class DragonSeasonTests(unittest.TestCase):
 def args(self,ctx):return dict(first_player=0,seed='dragon-season-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_dragon_season_v65r2_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertGreaterEqual(r['scenarios'],60)
 def test_full_battles_and_single_battle_settlement(self):
  cases=[]
  for ids in [[3004],[7121],[3004,7121]]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=ids
   cases.append(current.compile_start(row,**self.args(ctx)))
  before=deepcopy(cases);results=current.simulate_batch([c['battle'] for c in cases])['results'];self.assertEqual(cases,before)
  for c,r in zip(cases,results):
   self.assertTrue(r.get('terminated'),r);self.assertTrue(calculate_terminal_damage(c,r)['resolved']);self.assertFalse(r['training_label_allowed'])
   if 7121 in c['effect_players'][0]['season_choices']:
    self.assertFalse(r['match_continuation_allowed']);self.assertFalse(r['pending_season_match_effects'][0]['applied'])
 def test7121_does_not_modify_current_battle(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));row['players'][0]['candidate_start']['xian_mo_strategies']=[7121];b=current.compile_start(row,**self.args(ctx))
  x=old.simulate_batch([a['battle']])['results'][0];y=current.simulate_batch([b['battle']])['results'][0]
  for k in ['players','winner','hp_delta','turns','initial','trace']:self.assertEqual(x[k],y[k])
 def test_no_terminal_state_input(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[3004,7121];a=current.compile_start(row,**self.args(ctx))
  row['outcome']={'recorded_hp_delta':999,'recorded_destiny_damage':-99};ctx['players'][0]['after_talent_counters']={'7121':99}
  self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test3013_not_activated_by_ownership_or_terminal_counters(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[3013];ctx['players'][0]['after_talent_counters']={'3013':1}
  with self.assertRaisesRegex(current.UnresolvedBattle,'active_use_conversion_pending:3013'):current.compile_start(row,**self.args(ctx))
 def test_unknown_and_duplicate_block(self):
  for ids in [[3004,3004],[7121,999999]]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=ids
   with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_no_owner_output_unchanged(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_old_runtime3004_cannot_bypass_opening_boundary(self):
  row,ctx=start_fixture();c=current.compile_start(row,**self.args(ctx));c['battle']['season_runtime']=[{'ids':[3004],'disabled_ids':[]},{'ids':[],'disabled_ids':[]}]
  r=current.simulate_batch([c['battle']])['results'][0];self.assertIn('legacy3004_not_admitted',json.dumps(r))

if __name__=='__main__':unittest.main()
