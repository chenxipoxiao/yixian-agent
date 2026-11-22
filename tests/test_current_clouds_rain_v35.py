from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v34 as old,full_battle_v35 as current

def fixture(hand=None):
 row,ctx=start_fixture();hand=[15,15] if hand is None else hand
 row['players'][0]['candidate_start']['xian_mo_strategies']=[7069]
 ctx['players'][0]['hand_count']=len(hand)
 ctx['players'][0]['clouds_rain_hand']={'origin':'publicData.lastRoundData.handCards',
  'source_raw_sha256':row['source']['raw_sha256'],'environment_only':True,'raw_cards':hand}
 return row,ctx

class CloudsRainTests(unittest.TestCase):
 def args(self,ctx,first=0):
  return dict(first_player=first,seed='clouds-rain-software',game_mode=3,season_mec=10,combat_context=ctx)
 def test_native_boundaries(self):
  p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_clouds_rain_v35_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout),{'passed':True,'scenarios':31})
 def test_no_owner_complete_regression(self):
  row,ctx=start_fixture();a=self.args(ctx);before=old.compile_start(row,**a);after=current.compile_start(row,**a)
  self.assertEqual(before,after);self.assertEqual(old.simulate_batch([before['battle']])['results'],current.simulate_batch([after['battle']])['results'])
 def test_explicit_hand_preserves_duplicates_and_choice(self):
  row,ctx=fixture([15,15,0]);c=current.compile_start(row,**self.args(ctx))
  self.assertEqual(c['battle']['clouds_rain']['players'],[{'hand':[15,15,0],'board':[0,0,0]},None])
  self.assertEqual(c['effect_players'][0]['season_choices'],[7069])
 def test_missing_or_wrong_source_stays_unresolved(self):
  for change in ('missing','null','bool','unknown','count','wrong_source','missing_origin','not_environment'):
   row,ctx=fixture();data=ctx['players'][0]['clouds_rain_hand']
   if change=='missing':del ctx['players'][0]['clouds_rain_hand']
   elif change=='null':data['raw_cards']=None
   elif change=='bool':data['raw_cards']=[True,15]
   elif change=='unknown':data['raw_cards']=[999999999,15]
   elif change=='count':ctx['players'][0]['hand_count']=1
   elif change=='wrong_source':data['source_raw_sha256']='other'
   elif change=='missing_origin':del data['origin']
   else:data['environment_only']=False
   with self.subTest(change=change),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_unsupported_conditional_classification_stays_blocked(self):
  for change in ('character','talent192','talent20096','engraving','season_engraving'):
   row,ctx=fixture();p=row['players'][0];s=p['candidate_start']
   if change=='character':p['character_id']=1000001
   elif change.startswith('talent'):s['talents']=[int(change[6:])]
   elif change=='engraving':s['used_keyin_cards']=[40042]
   else:s['xian_mo_strategies'].append(13006)
   with self.subTest(change=change),self.assertRaisesRegex(current.UnresolvedBattle,'classification_pending'):current.compile_start(row,**self.args(ctx))
 def test_unknowns_not_filtered(self):
  for extra in (7069,1006,7053,9999999):
   row,ctx=fixture();row['players'][0]['candidate_start']['xian_mo_strategies'].append(extra)
   with self.subTest(extra=extra),self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
 def test_outcomes_not_input_and_both_initiatives(self):
  for first in (0,1):
   row,ctx=fixture();saved=deepcopy(row);a=self.args(ctx,first);c=current.compile_start(row,**a)
   self.assertEqual(row,saved);row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999}
   ctx['battle_params']=[999,4,5];self.assertEqual(c,current.compile_start(row,**a))
   r=current.simulate_batch([c['battle']])['results'][0]
   self.assertTrue(r['terminated']);self.assertEqual(len(r['clouds_rain_v35']['events']),1)
   self.assertEqual(r['clouds_rain_v35']['events'][0]['player_index'],0);self.assertFalse(r['training_label_allowed'])
 def test_truncation_does_not_label_winner(self):
  row,ctx=fixture();b=current.compile_start(row,**self.args(ctx))['battle'];b['max_turns']=1
  r=current.simulate_batch([b])['results'][0];self.assertTrue(r['truncated']);self.assertIsNone(r['winner'])
 def test_invalid_runtime_returns_unresolved_not_winner(self):
  row,ctx=fixture();b=current.compile_start(row,**self.args(ctx))['battle'];b['clouds_rain']['players'][0]['board']=[15,0,0]
  r=current.simulate_batch([b])['results'][0];self.assertIn('raw_board_mismatch',r['unresolved_reason']);self.assertNotIn('winner',r)

if __name__=='__main__':unittest.main()
