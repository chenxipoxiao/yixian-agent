from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v40 as old,full_battle_v41 as current
from yixian.terminal_damage_v38 import calculate_terminal_damage

def fixture(enabled=True):
 row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[1009]
 row['players'][0]['candidate_start']['board']=[1000001,1010002,0]
 ctx['players'][0]['upgrade_sound_switch']={'origin':'privateData.xianMoData:preparation_switch',
  'source_raw_sha256':row['source']['raw_sha256'],'selected_strategy_ids':[1009],
  'temp_data':{} if enabled else {'1009':1},'environment_only':True}
 return row,ctx

class UpgradeSoundTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='upgrade-sound-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_upgrade_sound_v41_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout),{'passed':True,'scenarios':26})
 def test_unowned_full_input_and_output_unchanged(self):
  row,ctx=start_fixture();args=self.args(ctx);a=old.compile_start(row,**args);b=current.compile_start(row,**args)
  self.assertEqual(a,b);self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_full_fight_after_upgrades_and_original_inputs_preserved(self):
  for first in [0,1]:
   row,ctx=fixture();saved=deepcopy(row);c=current.compile_start(row,**self.args(ctx,first))
   self.assertEqual(c['effect_players'][0]['season_choices'],[1009]);r=current.simulate_batch([c['battle']])['results'][0]
   self.assertTrue(r['terminated']);self.assertEqual(saved,row)
   e=next(e for e in r['upgrade_sound_v41']['events'] if e['player_index']==0)
   self.assertEqual(e['after_raw'],[1020001,1020002,0]);self.assertEqual(r['initial'][0]['cards'],['111011','111022','601011'])
   self.assertFalse(r['training_label_allowed'])
 def test_disabled_matches_same_battle_without_strategy(self):
  row,ctx=fixture(False);c=current.compile_start(row,**self.args(ctx));r=current.simulate_batch([c['battle']])['results'][0]
  row['players'][0]['candidate_start']['xian_mo_strategies']=[];baseline=old.compile_start(row,**self.args(ctx));b=old.simulate_batch([baseline['battle']])['results'][0]
  del r['upgrade_sound_v41'];self.assertEqual(r,b)
 def test_missing_switch_source_or_map_rejected(self):
  for key,value in [('origin','afterBattle'),('source_raw_sha256','bad'),('temp_data',None),
    ('temp_data',{'1009':True}),('selected_strategy_ids',[]),('environment_only',False)]:
   row,ctx=fixture();ctx['players'][0]['upgrade_sound_switch'][key]=value
   with self.subTest(key=key),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_targets_cannot_change_start_input(self):
  row,ctx=fixture();c=current.compile_start(row,**self.args(ctx));row['outcome']={'recorded_hp_delta':999}
  ctx['battle_params']=[1,2];ctx['players'][0]['after_talent_counters']={'1009':999}
  self.assertEqual(c,current.compile_start(row,**self.args(ctx)))
 def test_other_unknown_effects_remain_blocked(self):
  for key,value in [('xian_mo_strategies',[1009,7053]),('xian_mo_strategies',[1009,1009]),
    ('permanentBuffTempDatas',{'509':1}),('board',[0,99999999,0])]:
   row,ctx=fixture();row['players'][0]['candidate_start'][key]=value
   with self.subTest(key=key),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_legacy_runtime_not_applied_twice(self):
  row,ctx=fixture();b=current.compile_start(row,**self.args(ctx))['battle']
  b['season_runtime']=[{'ids':[1009],'disabled_ids':[]},{'ids':[],'disabled_ids':[]}]
  r=current.simulate_batch([b])['results'][0];self.assertIn('legacy_runtime1009_not_admitted',r['unresolved_reason']);self.assertNotIn('winner',r)
 def test_budget_truncation_cannot_produce_reward(self):
  row,ctx=fixture();c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
  r=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(r['truncated']);self.assertFalse(calculate_terminal_damage(c,r)['resolved'])

if __name__=='__main__':unittest.main()
