from copy import deepcopy
import json
import shutil
import subprocess
import unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v21 as previous, full_battle_v22 as current


class StarFateTests(unittest.TestCase):
    def fixture(self,seat=0):
        row,ctx=start_fixture()
        for p,c in zip(row['players'],ctx['players']):
            p['character_id']=2000005
            p['candidate_start'].update(level=5,unlocked_slots=8,board=[0]*8)
            c['public_level']=5
        row['players'][seat]['candidate_start']['talents']=[106]
        return row,ctx

    def compile(self,row,ctx,first=0):
        return current.compile_start(row,first_player=first,seed='software-star-fate-v22',
            game_mode=3,season_mec=10,combat_context=ctx)

    def test_both_seats_keep_ownership_without_replaying_acquisition(self):
        for seat in (0,1):
            row,ctx=self.fixture(seat);before=deepcopy((row,ctx))
            result=self.compile(row,ctx,1-seat)
            self.assertEqual((row,ctx),before)
            a,b=result['battle']['players'][seat],result['battle']['players'][1-seat]
            self.assertEqual(a['star_moon_folding_fan_stacks'],1)
            self.assertNotIn('star_moon_folding_fan_stacks',b)
            self.assertEqual(a['cards'],['601011']*8)
            self.assertEqual((a['hand_count'],a['hp'],a['max_hp'],a['qi']),(0,75,75,0))
            self.assertFalse(result['training_label_allowed'])

    def test_absent_fate_preserves_entire_compiled_input(self):
        row,ctx=start_fixture()
        expected=previous.compile_start(row,first_player=0,seed='software-star-fate-v22',
            game_mode=3,season_mec=10,combat_context=ctx)
        self.assertEqual(self.compile(row,ctx),expected)

    def test_terminal_fields_and_after_battle_fates_do_not_change_start(self):
        row,ctx=self.fixture();before=self.compile(row,ctx)
        row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999}
        ctx['players'][1]['after_talents']=[106]
        self.assertEqual(self.compile(row,ctx),before)

    def test_card_ownership_is_not_fate_ownership(self):
        row,ctx=self.fixture();row['players'][0]['candidate_start']['talents']=[]
        row['players'][0]['candidate_start']['board'][6]=23
        self.assertNotIn('star_moon_folding_fan_stacks',self.compile(row,ctx)['battle']['players'][0])

    def test_duplicate_fate_rejected(self):
        row,ctx=self.fixture();row['players'][0]['candidate_start']['talents']=[106,106]
        with self.assertRaisesRegex(current.UnresolvedBattle,'Unique explicit talents|Duplicate star'):
            self.compile(row,ctx)

    def test_incomplete_context_still_rejected(self):
        row,ctx=self.fixture();ctx['players'][0]['hand_count']=None
        with self.assertRaises(current.UnresolvedBattle):self.compile(row,ctx)

    def test_native_star_slot_and_hit_interaction(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',
            str(current.ROOT/'tests/current_star_fate_v22_probe.mjs')],
            capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertTrue(json.loads(p.stdout)['passed'])


if __name__=='__main__':unittest.main()
