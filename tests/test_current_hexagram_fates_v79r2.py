"""Fate lifecycle, complete software combats and diagnostic contract checks."""
from copy import deepcopy
import json,shutil,subprocess,unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v78 as old,full_battle_v79r2 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage
from yixian.combat_validation_batch_v7 import compare_previous

class HexagramFatesTests(unittest.TestCase):
    def args(self,ctx,first=0):return dict(first_player=first,seed='hexagram-fates-software',game_mode=3,season_mec=10,combat_context=ctx)
    def fixture(self):
        row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['talents']=[195,197];s['board']=[4000001,4000003,0]
        return row,ctx
    def test_native_fate_and_eight_card_boundaries(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_hexagram_fates_v79r2_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr);d=json.loads(p.stdout);self.assertTrue(d['passed']);self.assertGreaterEqual(d['scenarios'],38);print('V79_NATIVE_PROBE='+p.stdout.strip(),flush=True)
    def test_old_blocked_new_ownership_restored_and_source_immutable(self):
        row,ctx=self.fixture();before=deepcopy(row);c=current.compile_start(row,**self.args(ctx))
        self.assertEqual(row,before);self.assertEqual(c['effect_players'][0]['fates'],[195,197])
        self.assertEqual(c['battle']['hexagram_fates']['players'][0],{'fate_ids':[195,197],'starting_raw_cards':[4000001,4000003,0]})
        with self.assertRaises(old.UnresolvedBattle):old.compile_start(row,**self.args(ctx))
    def test_other_unknown_fates_and_permanent_markers_stay_blocked(self):
        row,ctx=self.fixture();row['players'][0]['candidate_start']['talents'].append(999999)
        with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
        row,ctx=self.fixture();row['players'][0]['candidate_start']['permanentBuffTempDatas']['439']=1
        with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
    def test_missing_and_duplicate_start_ownership_rejected(self):
        for value in [None,[195,195],['195']]:
            row,ctx=self.fixture();row['players'][0]['candidate_start']['talents']=value
            with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
    def test_terminal_and_future_fields_never_input(self):
        row,ctx=self.fixture();a=current.compile_start(row,**self.args(ctx));row['outcome']={'recorded_hp_delta':999,'winner_snapshot_slot':'p2'}
        ctx['players'][0]['after_talent_counters']={'195':999};self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
    def test_complete_battles_both_initiatives_have_real_effects(self):
        compiled=[]
        for first in [0,1]:
            row,ctx=self.fixture();compiled.append(current.compile_start(row,**self.args(ctx,first)))
        for c,b in zip(compiled,current.simulate_batch([c['battle'] for c in compiled])['results']):
            self.assertTrue(b.get('terminated'),b);self.assertTrue(calculate_terminal_damage(c,b)['resolved']);self.assertFalse(b['training_label_allowed'])
            ids={e['fate_id'] for e in b['hexagram_fates_v79']['events']};self.assertEqual(ids,{195,197})
    def test_nonowner_full_output_unchanged(self):
        row,ctx=start_fixture();a=old.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx));self.assertEqual(a,b)
        self.assertEqual(old.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
    def test_truncated_battle_never_settles(self):
        row,ctx=self.fixture();c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
        b=current.simulate_batch([c['battle']])['results'][0];self.assertTrue(b['truncated']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])
    def test_versioned_batch_comparator_keeps_full_content(self):
        c={'record_id':'x','all_four_match':True,'compiled':{'preparation_v77_context':{'bindings':[{'values':{13015:2}}]}},'simulation':{'hp_delta':10}}
        baseline={'cases':[json.loads(json.dumps(c))]};r=compare_previous([c],[],baseline);self.assertEqual(r['identical_full_case_outputs'],1)
        changed=deepcopy(c);changed['simulation']['hp_delta']=11;r=compare_previous([changed],[],baseline);self.assertEqual(r['identical_full_case_outputs'],0)

if __name__=='__main__':unittest.main()
