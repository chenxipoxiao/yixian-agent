"""Fate204 compiler ownership and full software battles; no strength claims."""
from copy import deepcopy
import json, shutil, subprocess, unittest
from unittest.mock import patch
from tests.test_full_battle import start_fixture
from yixian import full_battle_v83 as previous, full_battle_v84 as current
from yixian.terminal_damage_v47 import calculate_terminal_damage

class MortalBodyTests(unittest.TestCase):
    def fixture(self):
        row,ctx=start_fixture();row['players'][0]['character_id']=4000005
        s=row['players'][0]['candidate_start'];s['talents']=[204]
        s['talentTempDatas']={'204':18};s['board']=[432,0,0]
        s['permanentBuffTempDatas']={'10023':6,'10024':6}
        return row,ctx
    def args(self,ctx,first=0):
        return dict(first_player=first,seed='mortal-body-software',game_mode=3,season_mec=10,combat_context=ctx)
    def test_positive_conversion_boundaries(self):
        p=subprocess.run([shutil.which('node'),'--experimental-default-type=module',str(current.ROOT/'tests/current_mortal_body_v84_probe.mjs')],capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr);d=json.loads(p.stdout)
        self.assertTrue(d['passed']);self.assertEqual(d['scenarios'],14)
    def test_ownership_only_no_acquisition_or_counter_replay(self):
        row,ctx=self.fixture();saved=deepcopy(row);old=previous.compile_start(row,**self.args(ctx));new=current.compile_start(row,**self.args(ctx))
        self.assertEqual(row,saved);self.assertEqual(old['effect_players'],new['effect_players'])
        expected=deepcopy(old['battle']);expected['players'][0]['mortal_body_stacks']=1
        self.assertEqual(expected,new['battle']);self.assertNotIn('mortal_body_stacks',old['battle']['players'][0])
        self.assertIn(204,old['declared_components'][0]['preparation_fates_not_reapplied'])
        self.assertNotIn(204,new['declared_components'][0]['preparation_fates_not_reapplied'])
    def test_missing_unknown_duplicate_inputs_stay_rejected(self):
        for key,value in [('talents',None),('talents',[204,204]),('talents',[204,999999]),('xian_mo_strategies',None),('xian_mo_strategies',[8003,8003])]:
            row,ctx=self.fixture();row['players'][0]['candidate_start'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises((current.UnresolvedBattle,ValueError)):
                current.compile_start(row,**self.args(ctx))
        row,ctx=self.fixture();row['players'][0]['character_id']=1000003
        with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))
    def test_17071_veto_does_not_bypass_ancestor_admission(self):
        row,ctx=self.fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=[17071]
        with self.assertRaises((current.UnresolvedBattle,ValueError)):current.compile_start(row,**self.args(ctx))
        # Isolate the source predicate while explicitly simulating ancestor admission.
        plain,ctx=self.fixture();base=previous.compile_start(plain,**self.args(ctx))
        with patch.object(current.previous,'compile_start',return_value=deepcopy(base)):
            c=current.compile_start(row,**self.args(ctx));self.assertEqual(c['battle']['players'][0]['mortal_body_stacks'],0)
        base['context']['resonance_selected']=137
        with patch.object(current.previous,'compile_start',return_value=base),self.assertRaises(current.UnresolvedBattle):
            current.compile_start(plain,**self.args(ctx))
    def test_terminal_future_do_not_change_start(self):
        row,ctx=self.fixture();a=current.compile_start(row,**self.args(ctx))
        row['outcome']={'recorded_hp_delta':999,'winner_snapshot_slot':'p2'}
        ctx['players'][0]['after_talent_counters']={'204':999}
        self.assertEqual(a,current.compile_start(row,**self.args(ctx)))
    def test_nonowner_entire_case_unchanged(self):
        row,ctx=start_fixture();a=previous.compile_start(row,**self.args(ctx));b=current.compile_start(row,**self.args(ctx))
        self.assertEqual(a,b);self.assertEqual(previous.simulate_batch([a['battle']])['results'],current.simulate_batch([b['battle']])['results'])
    def test_complete_mouse_battles_both_initiatives(self):
        pairs=[]
        for first in [0,1]:
            row,ctx=self.fixture();pairs.append(current.compile_start(row,**self.args(ctx,first)))
        results=current.simulate_batch([c['battle'] for c in pairs])['results']
        for c,b in zip(pairs,results):
            self.assertTrue(b['terminated']);self.assertFalse(b['truncated']);self.assertFalse(b['training_label_allowed'])
            self.assertTrue(calculate_terminal_damage(c,b)['resolved'])
            self.assertEqual(b['players'][0]['qi'],0)
            self.assertGreater(b['players'][0]['max_hp'],c['battle']['players'][0]['max_hp'])
    def test_truncation_not_settled(self):
        row,ctx=self.fixture();c=current.compile_start(row,**self.args(ctx));c['battle']['max_turns']=1
        b=current.simulate_batch([c['battle']])['results'][0]
        self.assertTrue(b['truncated']);self.assertFalse(calculate_terminal_damage(c,b)['resolved'])

if __name__=='__main__':unittest.main()
