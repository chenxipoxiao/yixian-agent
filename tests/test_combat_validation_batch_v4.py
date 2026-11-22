from copy import deepcopy
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
from tests.test_full_battle import start_fixture
from tests.test_current_regen_opening_v73 import bind
from yixian import combat_validation_batch_v4 as batch

def contexts():
 rows=[];new={}
 for i in range(9):
  r,c=start_fixture();r['id']=f'row-{i}';r['split']='train';r['source']['split']='train'
  if i==0:r['players'][0]['candidate_start']['xian_mo_strategies']=[7135];bind(r,c)
  rows.append(r);new[r['id']]=c
 old=deepcopy(new);del old['row-0']['players'][0]['regen_opening_switch']
 return rows,old,new

class SwitchContextTests(unittest.TestCase):
 def test_only_bound_targeted_addition(self):
  rows,old,new=contexts();saved=deepcopy((old,new))
  self.assertEqual(batch.validate_switch_context(rows,old,new,['row-0']),[{'record_id':'row-0','player_index':0}]);self.assertEqual(saved,(old,new))
  for kind in ['unselected','other-field','terminal','wrong-row','wrong-seat','wrong-hash','bool','extra','missing-map','nonowner','existing']:
   a=deepcopy(old);b=deepcopy(new);rs=deepcopy(rows);selected=['row-0'];h=b['row-0']['players'][0]['regen_opening_switch']
   if kind=='unselected':selected=[]
   elif kind=='other-field':b['row-8']['players'][1]['public_level']=9
   elif kind=='terminal':h['recorded_hp_delta']=100
   elif kind=='wrong-row':h['record_id']='row-1'
   elif kind=='wrong-seat':h['snapshot_slot']='p2'
   elif kind=='wrong-hash':h['source_raw_sha256']='wrong'
   elif kind=='bool':h['temp_data']={'7135':False}
   elif kind=='extra':h['temp_data']={'7135':0,'1006':0}
   elif kind=='missing-map':del h['temp_data']
   elif kind=='nonowner':rs[0]['players'][0]['candidate_start']['xian_mo_strategies']=[]
   else:a['row-0']['players'][0]['regen_opening_switch']=deepcopy(h)
   with self.subTest(kind=kind),self.assertRaises(ValueError):batch.validate_switch_context(rs,a,b,selected)
 def test_targeted_execution_and_mutation_guard(self):
  rows,old,new=contexts();changes=[{'name':'7135','dependency_review':'Only source-bound7135 ownership adds switch','scope':'season','season_ids':[7135],'dependency_complete':True}]
  selection=batch.select_records(rows,new,changes)
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'old.json';p.write_text(json.dumps(old),'utf8');h=batch.digest(p)
   for key in ['pilot','context','baseline']:(root/key).write_text('{}')
   plan={'schema':batch.SCHEMA,'batch_id':'software-only','changes':changes,'control_count':4,'selection':selection,'candidate_sources':{},
    'pilot':'pilot','context':'context','baseline':'baseline','source_sha256':batch.digest(root/'pilot'),'context_sha256':batch.digest(root/'context'),
    'baseline_sha256':batch.digest(root/'baseline'),'engine_module':'yixian.full_battle_v73','settlement_module':'yixian.terminal_damage_v47',
    'additive_context':{'previous_context':'old.json','previous_sha256':h,'additions':[{'record_id':'row-0','player_index':0}]}}
   baseline={'context_sha256':h,'cases':[]}
   with patch.object(batch,'verify_sources'),patch.object(batch,'load_sources',return_value=(rows,new,baseline)),patch.object(batch,'execute_rows',return_value=([],[],{})) as execute:
    report=batch.run_plan(root,plan,full=False)
    self.assertEqual(report['summary']['attempted_records'],5);self.assertFalse(report['summary']['full_development_pass']);self.assertFalse(report['summary']['batch_release_candidate'])
    self.assertEqual(len(execute.call_args.args[0]),5)
    bad=deepcopy(new);bad['row-8']['players'][1]['public_level']=9
    with patch.object(batch,'load_sources',return_value=(rows,bad,baseline)),self.assertRaises(ValueError):batch.run_plan(root,plan,full=False)
    self.assertEqual(execute.call_count,1)

if __name__=='__main__':unittest.main()
