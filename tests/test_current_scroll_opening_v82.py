"""Source-derived boundaries plus complete software fights, never real strength."""
from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v81 as previous,full_battle_v82 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class ScrollOpeningTests(unittest.TestCase):
    def fixture(self):
        row,ctx=start_fixture()
        row['players'][0]['candidate_start']['talents']=[198]
        row['players'][0]['candidate_start']['board']=[0,215,0]
        return row,ctx
    def args(self,ctx,first=0):
        return dict(first_player=first,seed='scroll-software',game_mode=3,season_mec=10,combat_context=ctx)
    def test_source_boundaries(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_scroll_opening_v82_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr);d=json.loads(p.stdout);self.assertTrue(d['passed']);self.assertEqual(d['scenarios'],12)
        print('V82_SOURCE_SCENARIOS='+p.stdout.strip(),flush=True)
    def test_compile_original_state_and_separate_acquisition(self):
        row,ctx=self.fixture();before=deepcopy(row);c=current.compile_start(row,**self.args(ctx))
        self.assertEqual(row,before);self.assertEqual(c['battle']['players'][0]['cards'],['601011','625031','601011'])
        self.assertNotIn(198,c['declared_components'][0]['preparation_fates_not_reapplied'])
        self.assertEqual(c['effect_players'][0]['fates'],[198])
        self.assertIn(198,previous.compile_start(row,**self.args(ctx))['declared_components'][0]['preparation_fates_not_reapplied'])
    def test_unknown_missing_duplicate_inputs_stay_rejected(self):
        for key,value in [('talents',None),('talents',[198,198]),('talents',[198,999999]),('unlocked_slots',None)]:
            row,ctx=self.fixture();row['players'][0]['candidate_start'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises((current.UnresolvedBattle,ValueError)):
                current.compile_start(row,**self.args(ctx))
    def test_terminal_and_future_fields_do_not_affect_start(self):
        row,ctx=self.fixture();a=current.compile_start(row,**self.args(ctx));row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':999}
        ctx['players'][0]['after_talent_counters']={'198':100};self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
    def test_full_software_battle_both_seats_and_settlement(self):
        compiled=[]
        for first in [0,1]:
            row,ctx=self.fixture();compiled.append(current.compile_start(row,**self.args(ctx,first)))
        for c,b in zip(compiled,current.simulate_batch([x['battle'] for x in compiled])['results']):
            self.assertTrue(b.get('terminated'),b);self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
            self.assertEqual(b['scroll_opening_v82']['events'][0]['after'],['625041','625031','625051'])
            self.assertFalse(b['training_label_allowed'])
    def test_nonowner_unchanged(self):
        row,ctx=start_fixture();a=previous.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
        self.assertEqual(previous.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
    def test_truncated_result_cannot_settle(self):
        row,ctx=self.fixture();c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
        b=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(b['truncated']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
