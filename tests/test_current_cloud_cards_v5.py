"""Card boundaries plus native whole-turn integration; not independent validation."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from tests.test_full_battle import start_fixture, compile_fixture
from yixian import full_battle_v4 as old, full_battle_v5 as current
from yixian.simulator import SimulatorError

ROOT=Path(__file__).resolve().parents[1]


class CurrentCloudCardsTests(unittest.TestCase):
    def test_native_primitives_card_parity_and_heal_split(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(ROOT/'tests/current_cloud_cards_v5_probe.mjs')],cwd=ROOT,text=True,
            encoding='utf-8',capture_output=True,timeout=30)
        self.assertEqual(p.returncode,0,p.stderr)
        report=json.loads(p.stdout)
        self.assertTrue(report['passed']);self.assertEqual(len(report['checked']),15)

    def test_new_mapping_preserves_old_mapping_and_input(self):
        row,context=start_fixture();row['players'][0]['candidate_start']['board']=[1000104,1010105,10020102]
        before=copy.deepcopy(row)
        c=current.compile_start(row,first_player=0,seed=1,game_mode=3,season_mec=10,combat_context=context)
        self.assertEqual(row,before)
        self.assertEqual(c['battle']['players'][0]['cards'],['114911','115912','142913'])
        self.assertFalse(c['training_label_allowed'])
        prior=old.catalogue()[1];new=current.catalogue()[1]
        self.assertEqual(len(new),len(prior)+9)
        self.assertTrue(all(new[k]==v for k,v in prior.items()))

    def test_previous_entry_rejects_new_aliases(self):
        b=compile_fixture()['battle'];b['players'][0]['cards'][0]='115911'
        with self.assertRaisesRegex(SimulatorError,'Unimplemented card'):old.simulate_batch([b])

    def test_unextended_full_battle_is_unchanged(self):
        b=compile_fixture()['battle']
        a=old.simulate_batch([b])['results'][0];c=current.simulate_batch([b])['results'][0]
        c.pop('current_cloud_cards')
        self.assertEqual(a,c)

    def test_even_footwork_chases_through_native_scheduler(self):
        b=compile_fixture()['battle'];b['max_turns']=3
        b['players'][0]['cards']=['601011','115911','601011']
        r=current.simulate_batch([b])['results'][0]
        self.assertEqual(r['players'][1]['hp'],34)
        self.assertEqual(r['players'][0]['qi'],1)
        self.assertEqual(r['players'][0]['next_card_index'],0)
        self.assertTrue(r['truncated']);self.assertIsNone(r['winner'])

    def test_odd_footwork_shields_without_spurious_attack(self):
        b=compile_fixture()['battle'];b['max_turns']=1;b['players'][0]['cards'][0]='115911'
        r=current.simulate_batch([b])['results'][0]
        self.assertEqual(r['players'][0]['def'],13);self.assertEqual(r['players'][1]['hp'],40)

    def test_terminal_targets_do_not_change_compiled_input(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=1000104
        args={'first_player':0,'seed':1,'game_mode':3,'season_mec':10,'combat_context':ctx}
        before=current.compile_start(row,**args)
        row['outcome']={'recorded_hp_delta':10000,'recorded_destiny_damage':999}
        self.assertEqual(before,current.compile_start(row,**args))

    def test_unknown_effects_and_cards_remain_blocked(self):
        for key,value in [('board',[1000104,999999999,0]),('permanentBuffTempDatas',{'777777':1})]:
            row,ctx=start_fixture();row['players'][0]['candidate_start'][key]=value
            with self.assertRaises(current.UnresolvedBattle):
                current.compile_start(row,first_player=0,seed=1,game_mode=3,season_mec=10,combat_context=ctx)

    def test_truncated_card_action_does_not_emit_battle_label(self):
        b=compile_fixture()['battle'];b['max_turns']=1;b['players'][0]['cards'][0]='142911'
        r=current.simulate_batch([b])['results'][0]
        self.assertIsNone(r['winner']);self.assertIsNone(r['hp_delta'])
        self.assertFalse(r['training_label_allowed'])


if __name__=='__main__':unittest.main()
