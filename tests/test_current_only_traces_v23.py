from copy import deepcopy
import json
import shutil
import subprocess
import unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v22 as old, full_battle_v23 as current


class OnlyTracesTests(unittest.TestCase):
    def test_native_boundary_scenarios(self):
        result=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(current.ROOT/'tests/current_only_traces_v23_probe.mjs')],
            capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),{'passed':True,'scenarios':11})

    def test_compiler_input_unchanged_and_result_fields_not_used(self):
        row,ctx=start_fixture()
        row['players'][0]['candidate_start']['board']=[12,10012,20012]
        args=dict(first_player=0,seed='software-only-traces',game_mode=3,season_mec=10,combat_context=ctx)
        expected=old.compile_start(row,**args)
        self.assertEqual(current.compile_start(row,**args),expected)
        polluted=deepcopy(row);polluted['outcome']={'recorded_hp_delta':10000,'winner_snapshot_slot':'p2'}
        self.assertEqual(current.compile_start(polluted,**args),expected)

    def test_unaffected_complete_battle_preserves_full_result(self):
        row,ctx=start_fixture()
        b=current.compile_start(row,first_player=0,seed='software-only-traces',
            game_mode=3,season_mec=10,combat_context=ctx)['battle']
        self.assertEqual(current.simulate_batch([b])['results'],old.simulate_batch([b])['results'])

    def test_current_version_contract_explicit(self):
        facts=current.extension_contract()
        self.assertEqual(facts['version'],'001.0008.0005')
        self.assertEqual([c['otherParams'] for c in facts['cards']],[[0,0],[1,2],[1,2]])
        self.assertFalse(facts['training_label_allowed'])


if __name__=='__main__':unittest.main()
