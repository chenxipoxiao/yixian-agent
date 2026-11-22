"""Counter projection checks; synthetic cases are not replay evidence."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from tests.test_full_battle import start_fixture
from yixian import full_battle_v2 as old, full_battle_v3 as current
from yixian.terminal_damage import calculate_terminal_damage


def prepare(row,context,**overrides):
    args={'first_player':0,'seed':'counter-software','game_mode':3,'season_mec':10,'combat_context':context}
    args.update(overrides)
    return current.compile_start(row,**args)


class PermanentCounterTests(unittest.TestCase):
    def test_counter_is_retained_without_mutating_input_or_live_state(self):
        row,context=start_fixture();plain=prepare(row,context)
        row['players'][0]['candidate_start']['permanentBuffTempDatas']['10006']=7
        original=deepcopy(row);extended=prepare(row,context)
        self.assertEqual(row,original);self.assertEqual(plain['battle'],extended['battle'])
        self.assertEqual(extended['historical_permanent_counters']['10006'][0],{'snapshot_slot':'p1','present':True,'value':7})
        self.assertEqual(extended['historical_permanent_counters']['10006'][1],{'snapshot_slot':'p2','present':False,'value':None})

    def test_zero_presence_is_not_confused_with_absence(self):
        row,context=start_fixture();row['players'][1]['candidate_start']['permanentBuffTempDatas']['10006']=0
        meta=prepare(row,context)['historical_permanent_counters']['10006']
        self.assertTrue(meta[1]['present']);self.assertEqual(meta[1]['value'],0)
        self.assertFalse(meta[0]['present']);self.assertIsNone(meta[0]['value'])

    def test_history_never_decides_current_initiative(self):
        row,context=start_fixture();row['players'][1]['candidate_start']['permanentBuffTempDatas']['10006']=99
        with self.assertRaisesRegex(current.UnresolvedBattle,'Unknown initiative'):prepare(row,context,first_player=None)
        row['players'][1]['candidate_start']['exp']=5
        self.assertEqual(prepare(row,context,first_player=None)['battle']['first_player'],1)
        row['outcome']={'first_player_snapshot_slot':'p1'}
        self.assertEqual(prepare(row,context,first_player=None)['battle']['first_player'],1)

    def test_other_permanent_fields_remain_blocked_even_when_zero(self):
        for key in ['10008','10009','10015','999999']:
            with self.subTest(key=key):
                row,context=start_fixture();p=row['players'][0]['candidate_start']['permanentBuffTempDatas'];p['10006']=2;p[key]=0
                before=deepcopy(row)
                with self.assertRaisesRegex(current.UnresolvedBattle,'permanent_hooks_pending:'+key):prepare(row,context)
                self.assertEqual(before,row)

    def test_invalid_counter_and_missing_dictionary_are_rejected(self):
        for value in [None,True,1.0,'1',-1,1000001]:
            with self.subTest(value=value):
                row,context=start_fixture();row['players'][0]['candidate_start']['permanentBuffTempDatas']['10006']=value
                with self.assertRaisesRegex(current.UnresolvedBattle,'counter10006 required'):prepare(row,context)
        row,context=start_fixture();del row['players'][0]['candidate_start']['permanentBuffTempDatas']
        with self.assertRaisesRegex(current.UnresolvedBattle,'Explicit permanent dictionary'):prepare(row,context)

    def test_only_pinned_current_ranked_context_is_allowed(self):
        row,context=start_fixture()
        for args in [{'game_mode':2},{'season_mec':9}]:
            with self.subTest(args=args),self.assertRaisesRegex(current.UnresolvedBattle,'pinned ranked'):prepare(row,context,**args)
        row['source_rules_version']='old'
        with self.assertRaisesRegex(current.UnresolvedBattle,'pinned ranked'):prepare(row,context)

    def test_frozen_v2_compiler_still_rejects_counter(self):
        row,context=start_fixture();row['players'][0]['candidate_start']['permanentBuffTempDatas']['10006']=1
        with self.assertRaisesRegex(current.UnresolvedBattle,'permanent_hooks_pending:10006'):
            old.compile_start(row,first_player=0,seed=1,game_mode=3,season_mec=10,combat_context=context)

    def test_terminal_targets_cannot_change_battle_or_counter_metadata(self):
        row,context=start_fixture();row['players'][0]['candidate_start']['permanentBuffTempDatas']['10006']=3
        initial=prepare(row,context)
        row['outcome']={'winner_snapshot_slot':'p2','recorded_hp_delta':-9999}
        context['players'][0]['after_talent_counters']={'10006':999}
        self.assertEqual(initial,prepare(row,context))

    def test_evidence_change_rejected_before_projection(self):
        class Altered:
            def read_bytes(self):return b'{}'
        row,context=start_fixture()
        with patch.object(current,'PROOF',Altered()),self.assertRaisesRegex(current.UnresolvedBattle,'evidence changed'):
            prepare(row,context)

    def test_whole_battle_trace_and_damage_independent_of_historical_count(self):
        row,context=start_fixture();compiled=[]
        for value in [None,0,1,7,1000000]:
            r=deepcopy(row)
            if value is not None:r['players'][0]['candidate_start']['permanentBuffTempDatas']['10006']=value
            compiled.append(prepare(r,context))
        results=current.simulate_batch([c['battle'] for c in compiled])
        first=results['results'][0]
        self.assertTrue(first['terminated']);self.assertFalse(first['training_label_allowed'])
        for c,r in zip(compiled,results['results']):
            self.assertEqual(r,first)
            self.assertEqual(calculate_terminal_damage(c,r),calculate_terminal_damage(compiled[0],first))
        self.assertFalse(results['adapter_contract']['persistent_counter_updates_implemented'])


if __name__=='__main__':unittest.main()
