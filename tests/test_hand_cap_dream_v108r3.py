import unittest
import subprocess,shutil
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
from yixian import full_battle_v108r3 as engine,full_battle as base

def row(value=4):
 return {'players':[{'candidate_start':{'board':[0],'permanentBuffTempDatas':{'10044':value}}},
                    {'candidate_start':{'board':[0],'permanentBuffTempDatas':{}}}]}

class HandCapDreamTests(unittest.TestCase):
 def test_runtime_config_and_owner_ordered_multiple_copies(self):
  code="""
import assert from 'node:assert/strict';
const root=process.cwd();process.chdir('external/yisim');
const {GameState,ready}=await import('./external/yisim/gamestate_full.js');
const {swogi}=await import('./external/yisim/card_info.js');
import {registerDreamPredicament,installDreamPredicament} from './tools/current_dream_predicament_v108r3.mjs';
await ready;registerDreamPredicament(root,swogi);
const game=new GameState(undefined,undefined,'software-boundary');
const a=game.players[0],b=game.players[1];a.cards=['D23035','D23035'];b.cards=['D23035'];
a.hp=a.max_hp=100;b.hp=b.max_hp=100;let next=0;
game.do_dream_unrestrained_sword_zero_setup=()=>next++;
const hook=installDreamPredicament(root,game,swogi,[0,1]);
game.do_dream_predicament_for_immortals_setup();assert.equal(a.dream_predicament_for_immortals_stacks,0);
game.do_dream_unrestrained_sword_zero_setup();assert.equal(a.dream_predicament_for_immortals_stacks,9);assert.equal(b.dream_predicament_for_immortals_stacks,0);
game.swap_players();game.do_dream_unrestrained_sword_zero_setup();assert.equal(b.dream_predicament_for_immortals_stacks,9);assert.equal(next,2);
swogi.D23035.card_actions(game);assert.equal(b.hp,95);assert.equal(a.hp,100);assert.equal(hook.metadata().events.length,2);
assert.throws(()=>game.do_dream_unrestrained_sword_zero_setup(),/opening_twice/);
"""
  result=subprocess.run([shutil.which('node'),'--experimental-default-type=module','--input-type=module','-e',code],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(result.returncode,0,result.stderr)
 def test_unique_mapping_and_old_catalogue_preserved(self):
  old=engine.previous.catalogue();new=engine.catalogue()
  self.assertNotIn(348,old[1]);self.assertEqual(new[1][348],'D23035')
  new[1].pop(348);self.assertEqual(old,new)
 def test_invalid_signed_values_rejected_without_compilation(self):
  for value in [True,None,'4',2**31,-2**31-1]:
   with self.subTest(value=value),self.assertRaisesRegex(engine.UnresolvedBattle,'invalid_signed_value'):
    engine.compile_content_start(row(value),tables=engine.catalogue())
 def test_original_row_and_shared_leaf_unchanged(self):
  source=row(-4);saved=deepcopy(source);fields=set(base.PERMANENT_FIELDS)
  class View:
   def compile_start(self,r,**kwargs):
    self_seen.append(deepcopy(r));return {}
  self_seen=[];view=View()
  class Leaf:PERMANENT_FIELDS=set(fields)
  leaf=Leaf()
  with patch.object(engine,'isolated_compiler',return_value=view),patch.object(engine,'compiler_modules',return_value={'yixian.full_battle':leaf}):
   result=engine.compile_content_start(source,tables=())
  self.assertEqual(source,saved);self.assertEqual(self_seen,[saved]);self.assertEqual(base.PERMANENT_FIELDS,fields)
  self.assertIn('10044',leaf.PERMANENT_FIELDS)
  self.assertEqual(result['hand_cap_dream_context_v108r3']['permanent10044'],[{'present':True,'value':-4},{'present':False,'value':None}])
 def test_unaffected_path_delegates_exact_input(self):
  r=row();r['players'][0]['candidate_start']['permanentBuffTempDatas']={}
  with patch.object(engine.previous,'compile_start',return_value={'sentinel':1}) as call:
   self.assertEqual(engine.compile_start(r,test_marker=7),{'sentinel':1});call.assert_called_once_with(r,test_marker=7)
 def test_cloud_combination_remains_explicitly_blocked(self):
  with self.assertRaisesRegex(engine.UnresolvedBattle,'cloud_leaf_combination_pending'):
   engine.compile_content_start(row(),tables=(),combat_context={'cloud_sword_record':{}})
 def test_missing_map_is_not_empty(self):
  r=row();del r['players'][0]['candidate_start']['permanentBuffTempDatas']
  with self.assertRaisesRegex(engine.UnresolvedBattle,'explicit_permanent_map_required'):
   engine.compile_content_start(r,tables=())

if __name__=='__main__':unittest.main()
