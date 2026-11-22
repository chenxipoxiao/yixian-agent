import unittest
from copy import deepcopy
from unittest.mock import patch
from yixian import full_battle_v108 as engine,full_battle as base

def row(value=4):
 return {'players':[{'candidate_start':{'board':[0],'permanentBuffTempDatas':{'10044':value}}},
                    {'candidate_start':{'board':[0],'permanentBuffTempDatas':{}}}]}

class HandCapDreamTests(unittest.TestCase):
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
  self.assertEqual(result['hand_cap_dream_context_v108']['permanent10044'],[{'present':True,'value':-4},{'present':False,'value':None}])
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
