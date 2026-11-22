import copy
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from tests.test_full_battle import start_fixture, compile_fixture
from yixian import full_battle_v5 as old, full_battle_v6 as current
from yixian.simulator import SimulatorError

ROOT=Path(__file__).resolve().parents[1]

class CurrentSectCardsTests(unittest.TestCase):
    def test_static_boundaries_through_native_helpers(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(ROOT/'tests/current_sect_cards_v6_probe.mjs')],capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertTrue(json.loads(p.stdout)['passed'])

    def test_mapping_only_extends_and_compiler_does_not_mutate(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board']=[1000106,1000103,1000107]
        before=copy.deepcopy(row)
        c=current.compile_start(row,first_player=0,seed=1,game_mode=3,season_mec=10,combat_context=ctx)
        self.assertEqual(before,row);self.assertFalse(c['training_label_allowed'])
        a=old.catalogue()[1];b=current.catalogue()[1]
        self.assertEqual(len(b)-len(a),30);self.assertTrue(all(b[k]==v for k,v in a.items()))

    def test_old_entry_cannot_silently_use_new_cards(self):
        b=compile_fixture()['battle'];b['players'][0]['cards'][0]='115921'
        with self.assertRaisesRegex(SimulatorError,'Unimplemented card'):old.simulate_batch([b])

    def test_old_whole_battle_output_is_unchanged(self):
        b=compile_fixture()['battle'];a=old.simulate_batch([b])['results'][0]
        r=current.simulate_batch([b])['results'][0];r.pop('current_sect_cards')
        self.assertEqual(a,r)

    def test_qi_cost_blocks_attack_and_flash_chase(self):
        for card in ['114921','115931']:
            b=compile_fixture()['battle'];b['players'][0]['cards'][0]=card;b['max_turns']=1
            r=current.simulate_batch([b])['results'][0]
            self.assertEqual(r['players'][0]['qi'],1);self.assertEqual(r['players'][1]['hp'],40)
            self.assertEqual(r['players'][0]['next_card_index'],0)
            self.assertIsNone(r['winner']);self.assertFalse(r['training_label_allowed'])

    def test_targets_never_enter_start_input_and_unknowns_reject(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=1000106
        args=dict(first_player=0,seed=1,game_mode=3,season_mec=10,combat_context=ctx)
        before=current.compile_start(row,**args);row['outcome']={'recorded_hp_delta':9999}
        self.assertEqual(before,current.compile_start(row,**args))
        row['players'][0]['candidate_start']['permanentBuffTempDatas']['99999']=1
        with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**args)
