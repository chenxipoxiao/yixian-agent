import copy
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from tests.test_full_battle import start_fixture, compile_fixture
from yixian import full_battle_v2 as current
from yixian.full_battle import simulate_batch as legacy, catalogue as legacy_catalogue
from yixian.simulator import SimulatorError

ROOT=Path(__file__).resolve().parents[1]


class CurrentSwordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base=compile_fixture()['battle'];cls.battles=[]
        for grade in range(3):
            b=copy.deepcopy(base);b['max_turns']=1;b['players'][0]['cards']=[str(112901+grade),'601011','601011']
            cls.battles.append(b)
        cls.result=current.simulate_batch(cls.battles)['results']

    def test_all_flying_grades_use_current_two_attacks_and_pay_one_qi(self):
        for i,r in enumerate(self.result):
            with self.subTest(grade=i):
                self.assertEqual(r['trace'][0]['before'][0]['qi'],1)
                self.assertEqual(r['players'][0]['qi'],0)
                self.assertEqual(r['players'][1]['hp'],40-2*(5+2*i))

    def test_multiple_copies_do_not_stack_opening_and_existing_qi_is_preserved(self):
        copies=copy.deepcopy(self.battles[0]);copies['players'][0]['cards']=['112901','112902','112903']
        existing=copy.deepcopy(copies);existing['players'][0]['qi']=3
        a,b=current.simulate_batch([copies,existing])['results']
        self.assertEqual(a['trace'][0]['before'][0]['qi'],1)
        self.assertEqual(b['trace'][0]['before'][0]['qi'],3)
        self.assertEqual(b['players'][0]['qi'],2)

    def test_unextended_three_slot_battle_is_exactly_unchanged(self):
        b=compile_fixture()['battle'];a=legacy([b])['results'][0];c=current.simulate_batch([b])['results'][0]
        for key in ['winner','turns','players','hp_delta','trace','log','used_randomness']:
            self.assertEqual(a[key],c[key],key)

    def test_old_path_still_rejects_new_runtime_alias(self):
        with self.assertRaisesRegex(SimulatorError,'Unimplemented card'):legacy([self.battles[0]])

    def test_thousand_blades_all_grades_use_defense_at_execution(self):
        battles=[]
        for grade in range(3):
            b=copy.deepcopy(self.battles[0]);b['players'][0]['cards']=[str(115901+grade),'601011','601011']
            b['players'][0]['def']=10;battles.append(b)
        for grade,r in enumerate(current.simulate_batch(battles)['results']):
            with self.subTest(grade=grade):
                # Own turn halves 10 defense before executing. 1+5//5 attack.
                self.assertEqual(r['players'][0]['def'],5)
                self.assertEqual(r['players'][1]['hp'],40-2*(4+grade))

    def test_extension_mapping_does_not_mutate_old_catalogue(self):
        row,context=start_fixture();row['players'][0]['candidate_start']['board']=[1000101,1010108,0]
        a=current.compile_start(row,first_player=0,seed=1,game_mode=3,season_mec=10,combat_context=context)
        self.assertEqual(a['battle']['players'][0]['cards'],['112901','115902','601011'])
        self.assertNotIn(1000101,legacy_catalogue()[1]);self.assertNotIn(1010108,legacy_catalogue()[1])
        self.assertEqual(a['current_card_extension']['present_raw_ids'],[1000101,1010108])
        self.assertFalse(a['training_label_allowed'])

    def test_card_kind_opening_retrigger_and_snapshot_before_reactive_damage(self):
        proc=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(ROOT/'tests/current_sword_cards_probe.mjs')],text=True,encoding='utf-8',capture_output=True,cwd=ROOT,timeout=30)
        self.assertEqual(proc.returncode,0,proc.stderr)
        result=json.loads(proc.stdout)
        self.assertTrue(result['opening_zero_retrigger_passed'])
        self.assertEqual(len(result['defense_snapshot_trials']),6)

    def test_unknown_card_still_blocks_whole_battle(self):
        b=copy.deepcopy(self.battles[0]);b['players'][0]['cards'][1]='115999'
        with self.assertRaisesRegex(SimulatorError,'Unimplemented card'):current.simulate_batch([b])

    def test_truncation_is_not_a_training_label(self):
        for r in self.result:
            self.assertTrue(r['truncated']);self.assertIsNone(r['winner'])
            self.assertFalse(r['training_label_allowed'])


if __name__=='__main__':unittest.main()
