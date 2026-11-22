from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v71 as old,full_battle_v72 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class PalmVigorTests(unittest.TestCase):
 def args(self,ctx,first=0):return dict(first_player=first,seed='palm-vigor-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_palm_vigor_v72_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertTrue(r['passed']);self.assertEqual(len(r['names']),r['scenarios']);self.assertGreaterEqual(r['scenarios'],30);print('V72_NATIVE_PROBE='+p.stdout.strip(),flush=True)
 def test_full_battles_both_orders_and_settlement(self):
  starts=[]
  for ids in [[7089],[15018],[7089,15018],[1006,7089],[1006,15018],[5007,7089],[5008,7089]]:
   for first in [0,1]:
    row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['xian_mo_strategies']=ids;s['board']=[10010028,0,0];ctx['players'][0]['hand_count']=1
    if 1006 in ids:ctx['players'][0]['killing_sound_switch']={'origin':'privateData.xianMoData:preparation_switch','source_raw_sha256':row['source']['raw_sha256'],'environment_only':True,'selected_strategy_ids':[1006],'temp_data':{'1006':0}}
    c=current.compile_start(row,**self.args(ctx,first));self.assertEqual(c['effect_players'][0]['season_choices'],ids);starts.append(c)
  saved=deepcopy(starts);results=current.simulate_batch([c['battle'] for c in starts])['results'];self.assertEqual(starts,saved)
  for c,b in zip(starts,results):
   self.assertTrue(b['terminated'],b);self.assertFalse(b['used_randomness']);self.assertFalse(b['training_label_allowed']);self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
   ids=c['effect_players'][0]['season_choices'];events=b['palm_vigor_v72']['events']
   for id in [7089,15018]:
    if id in ids:self.assertTrue(any(e['strategy_id']==id for e in events))
   if 15018 in ids:
    e=next(e for e in events if e['strategy_id']==15018);self.assertEqual(e['requested'],e['before']['hp']*12//100)
 def test_unchanged_nonowner_complete_battle(self):
  row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
  self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
 def test_old_contract_closed(self):
  for id in [7089,15018]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[id]
   with self.subTest(id=id),self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
 def test_unknown_seasons_and_invalid_context_stay_closed(self):
  for ids in [None,[True],[7089,7089],[15018,15018],[7089,7135],[15018,7103],[7089,7062]]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=ids
   with self.subTest(ids=ids),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
  for count in [None,True,-1,1.5]:
   row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[15018];ctx['players'][0]['hand_count']=count
   with self.subTest(count=count),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_outcome_independent_and_inputs_immutable(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7089,15018];ctx['players'][0]['hand_count']=1;saved=deepcopy((row,ctx))
  a=current.compile_start(row,**self.args(ctx));self.assertEqual(saved,(row,ctx));row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999};ctx['players'][0]['after_talent_counters']={'15':999}
  self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
 def test_classification_matches_source_names(self):
  facts=current.extension_contract();cards={c['id']:c for c in json.loads((current.ROOT/'data/local/2026-11-06/tables/CardConfig.json').read_text('utf8'))}
  for rt,v in facts['runtime_classification'].items():
   for c in v['identities']:self.assertEqual(v['palm'],'掌' in cards[c['raw_id']]['name'],rt)
 def test_truncation_not_labelled(self):
  row,ctx=start_fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[7089,15018]
  c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1;b=current.simulate_batch([c['battle']])['results'][0]
  self.assertTrue(b['truncated']);self.assertIsNone(b['winner']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
