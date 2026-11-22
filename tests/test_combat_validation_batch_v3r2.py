from copy import deepcopy
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
from tests.test_current_element_flag_v62r3 import fixture
from yixian import combat_validation_batch_v3 as batch

class AdditivePlanExecutionTests(unittest.TestCase):
 def test_targeted_execution_validates_addition_without_forcing_full_dataset(self):
  row,context=fixture();rows=[];contexts={}
  for i in range(9):
   r=deepcopy(row);r['id']=f'row-{i}';r['split']='train';r['source']['split']='train'
   c=deepcopy(context)
   if i==0:c['players'][0]['element_flag_hand']['record_id']=r['id']
   else:r['players'][0]['candidate_start']['board']=[0,0,0];del c['players'][0]['element_flag_hand']
   rows.append(r);contexts[r['id']]=c
  old=deepcopy(contexts);del old['row-0']['players'][0]['element_flag_hand']
  changes=[{'name':'flag','dependency_review':'software fixture limits change to flag owner','scope':'card','card_ids':[7000111,7010111,7020111],'dependency_complete':True}]
  selection=batch.select_records(rows,contexts,changes)
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'old.json';p.write_text(json.dumps(old),'utf8');h=batch.digest(p)
   for key in ['pilot','context','baseline']:(root/key).write_text('{}')
   plan={'schema':batch.SCHEMA,'batch_id':'software-only','changes':changes,'control_count':4,'selection':selection,'candidate_sources':{},
    'pilot':'pilot','context':'context','baseline':'baseline','source_sha256':batch.digest(root/'pilot'),'context_sha256':batch.digest(root/'context'),
    'baseline_sha256':batch.digest(root/'baseline'),'engine_module':'yixian.full_battle_v62r2','settlement_module':'yixian.terminal_damage_v47',
    'additive_context':{'previous_context':'old.json','previous_sha256':h,'additions':[{'record_id':'row-0','player_index':0}]}}
   baseline={'context_sha256':h,'cases':[]}
   # This isolates admission/selection; no fabricated battle is a strength label.
   with patch.object(batch,'verify_sources'),patch.object(batch,'load_sources',return_value=(rows,contexts,baseline)),patch.object(batch,'execute_rows',return_value=([],[],{})) as execute:
    report=batch.run_plan(root,plan,full=False)
    self.assertEqual(report['summary']['attempted_records'],5);self.assertFalse(report['summary']['full_development_pass']);self.assertFalse(report['summary']['batch_release_candidate'])
    self.assertEqual(len(execute.call_args.args[0]),5)
    bad=deepcopy(contexts);bad['row-8']['players'][1]['public_level']=9
    with patch.object(batch,'load_sources',return_value=(rows,bad,baseline)),self.assertRaises(ValueError):batch.run_plan(root,plan,full=False)
    self.assertEqual(execute.call_count,1)

if __name__=='__main__':unittest.main()
