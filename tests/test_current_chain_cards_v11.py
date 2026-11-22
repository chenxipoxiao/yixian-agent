import json
from pathlib import Path
import shutil
import subprocess
import unittest
from tests.test_full_battle import start_fixture,compile_fixture
from yixian import full_battle_v10 as old,full_battle_v11 as current

class ChainCardsTests(unittest.TestCase):
    def test_classification_lifetime_and_continue_in_native_engine(self):
        root=Path(__file__).resolve().parents[1]
        run=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(root/'tests/current_chain_cards_v11_probe.mjs')],cwd=root,text=True,encoding='utf-8',capture_output=True)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertTrue(json.loads(run.stdout)['passed'])

    def test_all_grades_pay_hp_and_execute_full_turn(self):
        inputs=[]
        for base in [331,10000105]:
            for grade in range(3):
                row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[base+10000*grade,0,0]
                c=current.compile_start(row,first_player=0,seed=1,game_mode=3,season_mec=10,combat_context=ctx)
                c['battle']['max_turns']=1;inputs.append(c['battle'])
        results=current.simulate_batch(inputs)['results']
        self.assertEqual([r['players'][1]['hp'] for r in results],[33,29,25,34,31,28])
        self.assertEqual([r['players'][0]['hp'] for r in results],[40,40,40,35,35,35])

    def test_unaffected_trace_unchanged(self):
        b=compile_fixture()['battle'];a=old.simulate_batch([b])['results'][0]
        r=current.simulate_batch([b])['results'][0];r.pop('current_chain_cards')
        self.assertEqual(a,r)
