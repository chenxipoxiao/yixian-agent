from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v77 as old,full_battle_v78 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class ParrotTests(unittest.TestCase):
    def args(self,ctx,first=0):return dict(first_player=first,seed='parrot-software',game_mode=3,season_mec=10,combat_context=ctx)
    def test_native_copy_boundaries(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_parrot_v78_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr);d=json.loads(p.stdout);self.assertTrue(d['passed']);self.assertGreaterEqual(d['scenarios'],14);print('V78_NATIVE_PROBE='+p.stdout.strip(),flush=True)
    def test_three_grades_have_distinct_aliases_and_old_stays_blocked(self):
        for grade in range(3):
            row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=99000216+10000*grade
            before=deepcopy(row);c=current.compile_start(row,**self.args(ctx))
            self.assertEqual(c['battle']['players'][0]['cards'][0],'77801'+str(grade+1));self.assertEqual(row,before)
            with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
    def test_full_normal_copy_both_initiatives(self):
        starts=[]
        for first in [0,1]:
            for grade in range(3):
                row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=99000216+10000*grade
                starts.append(current.compile_start(row,**self.args(ctx,first)))
        for c,b in zip(starts,current.simulate_batch([x['battle'] for x in starts])['results']):
            self.assertTrue(b.get('terminated'),b);self.assertIn('parrot_v78',b);self.assertFalse(b['used_randomness']);self.assertTrue(calculate_terminal_damage(c,b)['resolved']);self.assertFalse(b['training_label_allowed'])
    def test_unsupported_copy_is_not_a_terminal_label(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=99000216;row['players'][1]['candidate_start']['board'][0]=1000039
        c=current.compile_start(row,**self.args(ctx));b=current.simulate_batch([c['battle']])['results'][0]
        self.assertIn('copy_target_not_admitted',b['unresolved_reason']);self.assertFalse(calculate_terminal_damage(c,b)['resolved']);self.assertFalse(b['training_label_allowed'])
    def test_terminal_fields_do_not_change_compilation(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=99000216;a=current.compile_start(row,**self.args(ctx))
        row['outcome']={'recorded_hp_delta':999,'winner_snapshot_slot':'p2','recorded_turn_count':99}
        self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
    def test_nonowner_full_output_unchanged(self):
        row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
        self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
    def test_truncation_never_settles(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['board'][0]=99000216;c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
        b=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(b['truncated']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
