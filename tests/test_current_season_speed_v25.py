from copy import deepcopy
import unittest
from tests.test_full_battle import start_fixture
from yixian import full_battle_v24 as old, full_battle_v25 as current


def fixture():
    row,ctx=start_fixture()
    left=row['players'][0]['candidate_start'];right=row['players'][1]['candidate_start']
    left['xian_mo_strategies']=[3005];left['permanentBuffTempDatas']['10056']=3
    left['exp']=10;right['exp']=12
    return row,ctx


class SeasonSpeedTests(unittest.TestCase):
    def args(self,ctx,**kw):
        return dict(seed='software-season-speed',game_mode=3,season_mec=10,combat_context=ctx,**kw)

    def test_speed_added_once_without_changing_cultivation(self):
        row,ctx=fixture()
        for enemy,first in [(12,0),(15,1)]:
            row['players'][1]['candidate_start']['exp']=enemy
            initiative=current.derive_start_initiative(row)
            self.assertEqual(initiative['players'][0]['candidate_initiative_score'],13)
            self.assertEqual(initiative['candidate_first_index'],first)
            c=current.compile_start(row,**self.args(ctx))
            self.assertEqual(c['battle']['first_player'],first)
            self.assertEqual(c['battle']['players'][0]['cultivation'],10)
            self.assertEqual(c['effect_players'][0]['season_choices'],[3005])
            self.assertFalse(c['training_label_allowed'])

    def test_counter_missing_or_outside_admitted_scope_is_not_invented(self):
        for value in (None,0,-3,6,True,'3'):
            row,ctx=fixture()
            p=row['players'][0]['candidate_start']['permanentBuffTempDatas']
            if value is None:p.pop('10056')
            else:p['10056']=value
            with self.assertRaisesRegex(current.UnresolvedBattle,'recorded_speed_required'):
                current.derive_start_initiative(row)
            with self.assertRaisesRegex(current.UnresolvedBattle,'recorded_speed_required'):
                current.compile_start(row,**self.args(ctx,first_player=0))

    def test_ties_remain_external_and_other_speed_components_add_once(self):
        row,ctx=fixture();row['players'][1]['candidate_start']['exp']=13
        self.assertIsNone(current.derive_start_initiative(row)['candidate_first_index'])
        with self.assertRaisesRegex(current.UnresolvedBattle,'Unknown initiative'):
            current.compile_start(row,**self.args(ctx))
        self.assertEqual(current.compile_start(row,**self.args(ctx,first_player=1))['battle']['first_player'],1)
        row['players'][0]['candidate_start']['permanentBuffTempDatas']['10012']=2
        self.assertEqual(current.derive_start_initiative(row)['players'][0]['candidate_initiative_score'],15)

    def test_no_ownership_keeps_old_compilation_and_complete_output(self):
        row,ctx=start_fixture();args=self.args(ctx,first_player=0)
        expected=old.compile_start(row,**args)
        self.assertEqual(current.compile_start(row,**args),expected)
        self.assertEqual(current.simulate_batch([expected['battle']])['results'],
                         old.simulate_batch([expected['battle']])['results'])

    def test_ownership_is_not_a_second_battle_buff_or_reward(self):
        row,ctx=fixture();original=deepcopy(row)
        c=current.compile_start(row,**self.args(ctx))
        projected=deepcopy(row);projected['players'][0]['candidate_start']['xian_mo_strategies']=[]
        expected=old.compile_start(projected,**self.args(ctx))
        self.assertEqual(c['battle'],expected['battle'])
        self.assertEqual(row,original)
        self.assertEqual(current.simulate_batch([c['battle']])['results'],old.simulate_batch([expected['battle']])['results'])
        row['outcome']={'recorded_hp_delta':999,'first_player_snapshot_slot':'p2'}
        self.assertEqual(current.compile_start(row,**self.args(ctx)),c)

    def test_other_unknown_effect_and_duplicate_choice_still_rejected(self):
        for ids in ([3005,3005],[3005,999999]):
            row,ctx=fixture();row['players'][0]['candidate_start']['xian_mo_strategies']=ids
            with self.assertRaises(current.UnresolvedBattle):current.compile_start(row,**self.args(ctx))

    def test_other_versioned_season_extension_survives(self):
        row,ctx=fixture();row['players'][1]['candidate_start']['xian_mo_strategies']=[7065]
        c=current.compile_start(row,**self.args(ctx))
        self.assertEqual(c['battle']['season_full_moon'],{'players':[[],[7065]]})
        self.assertEqual([x['season_choices'] for x in c['effect_players']],[[3005],[7065]])
        self.assertEqual(current.extension_contract()['permanent_id'],'10056')


if __name__=='__main__':unittest.main()
