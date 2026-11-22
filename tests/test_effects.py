from copy import deepcopy
import unittest

from yixian.effects import EffectEngine, UnknownEffectState


def player(*, fates=(), season=(), qi=0, rerolls=0):
    return {'fates':list(fates), 'season_choices':list(season), 'qi':qi, 'rerolls':rerolls, 'life':100}


class EffectTests(unittest.TestCase):
    def setUp(self):
        self.engine = EffectEngine()

    def test_start_both_owners_stack_without_mutating_inputs_or_accumulating_between_battles(self):
        left, right = player(season=[1001], qi=1), player(season=[1001], qi=3)
        frozen = deepcopy((left, right))
        result = self.engine.battle_start(left, right)
        self.assertEqual([p['qi'] for p in result['players']], [5, 7])
        self.assertEqual(len(result['events']), 2)
        self.assertEqual((left, right), frozen)
        self.assertEqual(self.engine.battle_start(left, right), result)

    def test_switch_defaults_on_imports_nonzero_off_and_preserves_local_changes(self):
        actor = self.engine.initialize_player(player(season=[1001]), season_temp_datas={'1001': 1})
        self.assertEqual([p['qi'] for p in self.engine.battle_start(actor, player())['players']], [0, 0])
        actor = self.engine.set_season_enabled(actor, 1001, True)
        actor = self.engine.initialize_player(actor, season_temp_datas={'1001': 1})
        self.assertEqual([p['qi'] for p in self.engine.battle_start(actor, player())['players']], [2, 2])
        actor = self.engine.set_season_enabled(actor, 1001, False)
        self.assertEqual([p['qi'] for p in self.engine.battle_start(actor, player())['players']], [0, 0])
        with self.assertRaises(ValueError):
            self.engine.set_season_enabled(player(), 1001, False)

    def test_skip_receipt_does_not_activate_season_effect(self):
        left = player(season=[{'kind':'skip', 'selected':1001}])
        result = self.engine.battle_start(left, player())
        self.assertEqual(result['events'], [])
        self.assertEqual(result['players'][0]['qi'], 0)

    def test_guard_import_missing_key_means_unavailable_missing_snapshot_is_error(self):
        actor = player(fates=[105])
        with self.assertRaises(UnknownEffectState):
            self.engine.initialize_player(actor)
        unavailable = self.engine.initialize_player(actor, talent_counters={})
        self.assertEqual(unavailable['effect_state']['talent_105_remaining'], 0)
        available = self.engine.initialize_player(actor, talent_counters={'105':1})
        self.assertEqual(available['effect_state']['talent_105_remaining'], 1)
        self.assertNotIn('effect_state', actor)

    def test_guard_consumes_only_when_threshold_met_and_cannot_refill_from_replay(self):
        actor = self.engine.initialize_player(player(fates=[105]), newly_acquired_fates=(105,))
        lower = self.engine.settle(player(), actor, 14)
        self.assertEqual(lower['life_damage'], 14)
        self.assertEqual(lower['loser']['effect_state']['talent_105_remaining'], 1)
        triggered = self.engine.settle(player(), lower['loser'], 15)
        self.assertEqual(triggered['life_damage'], 0)
        used = self.engine.initialize_player(triggered['loser'], talent_counters={'105':1}, newly_acquired_fates=(105,))
        self.assertEqual(used['effect_state']['talent_105_remaining'], 0)
        self.assertEqual(self.engine.settle(player(), used, 20)['life_damage'], 20)

    def test_supported_order_kindness_then_cat_then_guard(self):
        winner = player(season=[2011], rerolls=25)
        loser = self.engine.initialize_player(player(fates=[45, 105]), talent_counters={'105':1})
        frozen = deepcopy((winner, loser))
        result = self.engine.settle(winner, loser, 31)
        # 31 -> 30 -> 15 -> 0; cat first would instead reach 14 and not trigger.
        self.assertEqual(result['life_damage'], 0)
        self.assertEqual([e['effect_id'] for e in result['events']], [2011, 45, 105, 2011])
        self.assertEqual(result['winner']['rerolls'], 26)
        self.assertEqual(result['loser']['effect_state']['talent_105_remaining'], 0)
        self.assertEqual(result['loser']['life'], 100)  # Caller owns life deduction.
        self.assertEqual((winner, loser), frozen)

    def test_kindness_changes_parity_before_cat(self):
        result = self.engine.settle(player(season=[2011]), player(fates=[45]), 20)
        self.assertEqual(result['life_damage'], 19)
        self.assertEqual(self.engine.settle(player(), player(fates=[45]), 20)['life_damage'], 10)

    def test_kindness_minimum_and_positive_even_only_cat(self):
        self.assertEqual(self.engine.settle(player(season=[2011]), player(), 1)['life_damage'], 1)
        result = self.engine.settle(player(), player(fates=[45]), 0)
        self.assertEqual(result['life_damage'], 0)
        self.assertEqual(result['events'], [])
        self.assertEqual(self.engine.settle(player(), player(fates=[45]), 3)['life_damage'], 3)

    def test_unknown_effects_are_reported_without_claiming_complete_execution(self):
        actor = player(fates=[45, 999], season=[1001, 8003])
        report = self.engine.battle_start(actor, player())
        self.assertEqual(report['unsupported_effects'][0]['unsupported_fates'], [999])
        self.assertEqual(report['unsupported_effects'][0]['unsupported_season'], [8003])
        self.assertFalse(report['complete_rule_execution'])

    def test_duplicate_ownership_does_not_duplicate_trigger(self):
        result = self.engine.battle_start(player(season=[1001, 1001]), player())
        self.assertEqual([p['qi'] for p in result['players']], [2, 2])

    def test_failed_application_never_mutates_inputs(self):
        winner = player(season=[2011]); del winner['rerolls']
        loser = self.engine.initialize_player(player(fates=[105]), talent_counters={'105':1})
        frozen = deepcopy((winner, loser))
        with self.assertRaises(UnknownEffectState):
            self.engine.settle(winner, loser, 20)
        self.assertEqual((winner, loser), frozen)
        with self.assertRaises(ValueError):
            self.engine.initialize_player(player(fates=[105]), talent_counters={'105':True})
        with self.assertRaises(ValueError):
            self.engine.settle(player(), player(), -1)

    def test_configuration_parameters_drive_effects(self):
        engine = EffectEngine(start_qi=3, kindness_reduction=2, guard_threshold=17)
        self.assertEqual(engine.battle_start(player(season=[1001]), player())['players'][0]['qi'],3)
        self.assertEqual(engine.settle(player(season=[2011]), player(),10)['life_damage'],8)
        guard=engine.initialize_player(player(fates=[105]),newly_acquired_fates=(105,))
        self.assertEqual(engine.settle(player(),guard,16)['life_damage'],16)
        self.assertEqual(engine.settle(player(),guard,17)['life_damage'],0)


if __name__ == '__main__':
    unittest.main()
