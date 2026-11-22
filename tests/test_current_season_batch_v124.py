from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v124 as new,full_battle_v123 as old

class SeasonBatchTests(unittest.TestCase):
 def test_complete_batch_software_boundaries(self):
  run=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(new.ROOT/'tests/current_season_batch_v124_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=90)
  self.assertEqual(run.returncode,0,run.stdout+run.stderr)
  result=json.loads(run.stdout);self.assertFalse(result['failures']);self.assertFalse(result['missing_ids'])

 def test_private_compiler_preserves_unowned_original_and_terminal_separation(self):
  row,ctx=start_fixture();kw=dict(first_player=0,seed='batch-software',game_mode=3,season_mec=10,combat_context=ctx)
  self.assertEqual(new.compile_start(row,**kw),old.compile_start(row,**kw))
  row['players'][0]['candidate_start']['xian_mo_strategies']=[3003,7002,7097]
  saved=deepcopy(row);out=new.compile_start(row,**kw);self.assertEqual(row,saved)
  self.assertEqual(out['battle']['season_batch']['players'][0]['ids'],[3003,7002,7097])
  self.assertEqual(out['battle']['season_batch']['players'][0]['raw_cards'],[0,0,0])
  row['outcome']={'winner':'p2','recorded_hp_delta':999,'recorded_turn_count':999}
  self.assertEqual(out,new.compile_start(row,**kw))
  with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**kw)
  row['players'][0]['candidate_start']['xian_mo_strategies'].append(999999)
  with self.assertRaises(old.UnresolvedBattle):new.compile_start(row,**kw)

 def test_unknown_toggle_and_active_use_remain_blocked(self):
  row,ctx=start_fixture();kw=dict(first_player=0,seed='batch-software',game_mode=3,season_mec=10,combat_context=ctx)
  for ids in [[1004],[1010],[3013],[13005]]:
   row['players'][0]['candidate_start']['xian_mo_strategies']=ids
   with self.subTest(ids=ids),self.assertRaises(old.UnresolvedBattle):new.compile_start(row,**kw)

 def test_uncapped_stored_counter_not_reacquired(self):
  row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s.update(talents=[92],talentTempDatas={'92':27},board=[19,0,0],xian_mo_strategies=[7012])
  kw=dict(first_player=0,seed='batch-software',game_mode=3,season_mec=10,combat_context=ctx)
  result=new.compile_start(row,**kw);self.assertEqual(result['battle']['players'][0]['swordsmith_stacks'],27)
  self.assertEqual(result['effect_players'][0]['fates'],[92]);self.assertEqual(result['effect_players'][0]['talent_counters'],{'92':27})
  with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**kw)

if __name__=='__main__':unittest.main()
