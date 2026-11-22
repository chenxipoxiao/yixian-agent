from copy import deepcopy
import json,shutil,subprocess,unittest
from unittest.mock import patch
from yixian import full_battle_v120 as new

class ThunderParameterTests(unittest.TestCase):
 def test_all_grades_and_hit_interleaving(self):
  r=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(new.ROOT/'tests/current_thunder_parameters_v120_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  self.assertEqual(json.loads(r.stdout)['scenarios'],20)

 def test_original_start_binding_and_terminal_isolation(self):
  proof=new.extension_contract();self.assertIs(new.catalogue,new.previous.catalogue)
  stage=new.ROOT/'runs/stages/20261116T030000Z-s2-dream-card-batch'
  plan=json.loads((stage/'batch-plan-v119r2.json').read_text('utf8'));rows={};contexts={}
  for c in plan['cohorts']:
   rows.update({r['id']:r for r in map(json.loads,(new.ROOT/c['rows']).read_text('utf8').splitlines())})
   contexts.update(json.loads((new.ROOT/c['contexts']).read_text('utf8')))
  report=json.loads((new.ROOT/'runs/stages/20261116T033100Z-s2-thunder-parameters/baseline.json').read_text('utf8'))
  # Only normalized selected training starts are inspected; no archives or holdout.
  compiled={c['record_id']:c['compiled'] for c in report['cases'] if c['record_id'] in proof['admitted_records']}
  for rid,original in compiled.items():
   row=deepcopy(rows[rid]);ctx=deepcopy(contexts[rid]);kw=dict(combat_context=ctx,first_player=original['battle']['first_player'])
   with patch.object(new.previous,'compile_start',side_effect=lambda *a,**k:deepcopy(original)):
    got=new.compile_start(row,**kw);binding=got['battle'].pop('replay_parameters');got.pop('replay_parameter_context_v120')
    self.assertEqual(got,original);self.assertEqual(binding['stream'],ctx['battle_params'])
    row['outcome']={'recorded_hp_delta':9999,'winner_snapshot_slot':'p1'}
    self.assertEqual(new.compile_start(row,**kw)['battle']['replay_parameters'],binding)
    ctx['battle_params']=list(reversed(ctx['battle_params']))
    with self.assertRaisesRegex(new.UnresolvedBattle,'recorded_stream_mismatch'):new.compile_start(row,**kw)
    ctx=deepcopy(contexts[rid]);kw['combat_context']=ctx;row['players'][0]['candidate_start']['board'].reverse()
    with self.assertRaisesRegex(new.UnresolvedBattle,'original_snapshot_mismatch'):new.compile_start(row,**kw)

if __name__=='__main__':unittest.main()
