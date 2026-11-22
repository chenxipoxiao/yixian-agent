"""Plant startup semantics in whole fights, not independent server evidence."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from tests.test_full_battle import start_fixture
from yixian import full_battle_v3 as old, full_battle_v4 as current
from yixian.simulator import SimulatorError
from yixian.terminal_damage import calculate_terminal_damage


def prepare(row,context,**overrides):
    args=dict(first_player=0,seed='software-plants',game_mode=3,season_mec=10,combat_context=context)
    args.update(overrides)
    return current.compile_start(row,**args)


class PermanentPlantTests(unittest.TestCase):
    def test_preserves_input_and_base_hp_and_retains_exact_values(self):
        row,ctx=start_fixture();p=row['players'][0]['candidate_start']['permanentBuffTempDatas']
        p.update({'10008':5,'10009':3,'10006':2});before=deepcopy(row)
        c=prepare(row,ctx);raw=c['battle']['players'][0]
        self.assertEqual(row,before)
        self.assertEqual((raw['hp'],raw['max_hp']),(40,40))
        self.assertEqual((raw['origin_herb_stacks'],raw['shuttle_orchid_stacks']),(5,3))
        self.assertEqual(c['historical_permanent_counters']['10006'][0]['value'],2)
        self.assertFalse(c['training_label_allowed'])

    def test_absent_is_not_invented_zero(self):
        row,ctx=start_fixture();c=prepare(row,ctx)
        self.assertNotIn('origin_herb_stacks',c['battle']['players'][0])
        self.assertEqual(c['permanent_plant_startup']['players'][0]['effects'],{})

    def test_unknown_or_nonpositive_values_remain_unresolved(self):
        for value in [0,-1,True,1.5,None,'3',1_000_001]:
            for key in ['10008','10009']:
                with self.subTest(value=value,key=key):
                    row,ctx=start_fixture();row['players'][0]['candidate_start']['permanentBuffTempDatas'][key]=value
                    with self.assertRaisesRegex(current.UnresolvedBattle,'plant_value_pending'):prepare(row,ctx)

    def test_other_permanents_still_block_whole_fight(self):
        for key in ['10010','10011','10015','999999']:
            row,ctx=start_fixture();row['players'][0]['candidate_start']['permanentBuffTempDatas'].update({'10008':3,key:0})
            before=deepcopy(row)
            with self.subTest(key=key),self.assertRaisesRegex(current.UnresolvedBattle,'permanent_hooks_pending:'+key):prepare(row,ctx)
            self.assertEqual(row,before)

    def test_missing_dictionary_is_not_empty(self):
        row,ctx=start_fixture();del row['players'][0]['candidate_start']['permanentBuffTempDatas']
        with self.assertRaisesRegex(current.UnresolvedBattle,'Explicit permanent'):prepare(row,ctx)

    def test_pinned_version_and_mode_still_enforced(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['permanentBuffTempDatas']['10008']=3
        for args in [{'game_mode':2},{'season_mec':9}]:
            with self.subTest(args=args),self.assertRaisesRegex(current.UnresolvedBattle,'pinned ranked'):prepare(row,ctx,**args)
        row['source_rules_version']='old'
        with self.assertRaisesRegex(current.UnresolvedBattle,'pinned ranked'):prepare(row,ctx)

    def test_targets_cannot_change_projection(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['permanentBuffTempDatas']['10008']=3
        first=prepare(row,ctx);row['outcome']={'recorded_hp_delta':999,'winner_snapshot_slot':'p2'}
        ctx['players'][0]['after_talent_counters']={'10008':999}
        self.assertEqual(first,prepare(row,ctx))

    def test_old_entry_remains_strict(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['permanentBuffTempDatas']['10008']=3
        with self.assertRaisesRegex(old.UnresolvedBattle,'permanent_hooks_pending:10008'):
            old.compile_start(row,first_player=0,seed=1,game_mode=3,season_mec=10,combat_context=ctx)

    def test_proof_change_rejected(self):
        class Altered:
            def read_bytes(self):return b'{}'
        row,ctx=start_fixture()
        with patch.object(current,'PROOF',Altered()),self.assertRaisesRegex(current.UnresolvedBattle,'evidence changed'):prepare(row,ctx)

    def test_complete_trace_unchanged_without_plants(self):
        row,ctx=start_fixture();c=prepare(row,ctx)
        self.assertEqual(current.simulate_batch([c['battle']])['results'],old.simulate_batch([c['battle']])['results'])

    def test_origin_heals_once_after_initial_state(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['permanentBuffTempDatas']['10008']=5
        c=prepare(row,ctx);r=current.simulate_batch([c['battle']])['results'][0]
        self.assertEqual(r['initial'][0]['hp'],40)
        self.assertEqual((r['trace'][0]['before'][0]['hp'],r['trace'][0]['before'][0]['max_hp']),(45,45))
        self.assertEqual(r['players'][0]['max_hp'],45)
        self.assertTrue(r['terminated']);self.assertTrue(calculate_terminal_damage(c,r)['resolved'])

    def test_origin_uses_rejuvenation_and_birdie_heal_hooks(self):
        row,ctx=start_fixture();s=row['players'][0]['candidate_start'];s['talents']=[120,64]
        s['permanentBuffTempDatas']['10008']=5
        c=prepare(row,ctx);r=current.simulate_batch([c['battle']])['results'][0]
        state=r['trace'][0]['before'][0]
        self.assertEqual((state['hp'],state['max_hp'],state['def']),(45,48,1))

    def test_second_players_orchid_hits_first_players_opening_defense(self):
        # First owner heals through Birdie Wind, creating 1 defense. Second
        # owner's 3 non-attack damage must hit that defense before the fight.
        row,ctx=start_fixture();a,b=[p['candidate_start'] for p in row['players']]
        a['talents']=[64];a['permanentBuffTempDatas']['10008']=5
        b['permanentBuffTempDatas']['10009']=3
        c=prepare(row,ctx);r=current.simulate_batch([c['battle']])['results'][0]
        self.assertEqual(r['trace'][0]['before'][0]['hp'],43)
        # Losing HP also triggers Birdie Wind, restoring 1 defense.
        self.assertEqual(r['trace'][0]['before'][0]['def'],1)

    def test_each_owner_heals_then_damages_in_initiative_order(self):
        row,ctx=start_fixture()
        for p in row['players']:p['candidate_start']['permanentBuffTempDatas'].update({'10008':5,'10009':3})
        cs=[prepare(row,ctx,first_player=i) for i in [0,1]]
        rs=current.simulate_batch([c['battle'] for c in cs])['results']
        for r in rs:
            self.assertEqual([p['hp'] for p in r['trace'][0]['before']],[42,42])
            self.assertEqual([p['max_hp'] for p in r['trace'][0]['before']],[45,45])

    def test_opening_lethal_remains_unresolved_not_fake_one_turn_win(self):
        row,ctx=start_fixture();row['players'][0]['candidate_start']['permanentBuffTempDatas']['10009']=1000
        c=prepare(row,ctx)
        with self.assertRaisesRegex(SimulatorError,'opening_terminal_pending'):
            current.simulate_batch([c['battle']])


if __name__=='__main__':unittest.main()
