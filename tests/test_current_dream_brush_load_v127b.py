from copy import deepcopy
import json,shutil,subprocess,unittest
from unittest.mock import patch
from yixian import full_battle
from yixian import full_battle_v127 as new
S=new.ROOT/'runs/stages/20261116T085500Z-s2-dream-brush-load'
FIXTURES=json.loads((S/'opening-fixtures-v127.json').read_text('utf8'))
class DreamBrushLoadTests(unittest.TestCase):
 def test_all_configured_forms_and_prior_catalogue_preserved(self):
  old=new.previous.catalogue();now=new.catalogue()
  self.assertEqual(now[0],old[0]);self.assertEqual(now[2:],old[2:])
  self.assertEqual({k:v for k,v in now[1].items() if k in old[1]},old[1])
  self.assertEqual(set(now[1])-set(old[1]),{341,10341,10030083,10040083})
 def test_records_bind_only_original_start_and_ordered_stream(self):
  for fixture in FIXTURES.values():
   row,ctx=deepcopy(fixture['row']),deepcopy(fixture['context'])
   with patch.object(new.previous,'compile_start',side_effect=lambda *a,**k:deepcopy(fixture['compiled'])):
    before=new.compile_start(row,combat_context=ctx)
    self.assertFalse(before['replay_parameter_context_v127']['counterfactual_reuse_allowed'])
    row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':123456}
    ctx['players'][0]['after_talent_counters']={'not_a_start':123456}
    self.assertEqual(before,new.compile_start(row,combat_context=ctx))
    ctx['battle_params'].reverse()
    if len(ctx['battle_params'])>1:
     with self.assertRaises(new.UnresolvedBattle):new.compile_start(row,combat_context=ctx)
    ctx=deepcopy(fixture['context']);row['players'][0]['candidate_start']['board'].reverse()
    with self.assertRaisesRegex(new.UnresolvedBattle,'original_snapshot_mismatch'):new.compile_start(row,combat_context=ctx)
 def test_runtime_boundaries_and_nested_interleaving(self):
  r=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(new.ROOT/'tests/current_dream_brush_load_v127b_probe.mjs')],cwd=new.ROOT,capture_output=True,text=True,encoding='utf8',timeout=60)
  self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  self.assertGreaterEqual(json.loads(r.stdout)['scenarios'],20)
if __name__=='__main__':unittest.main()
