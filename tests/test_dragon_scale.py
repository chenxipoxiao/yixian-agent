from copy import deepcopy
import unittest

from yixian.dragon_scale import cap_damage
from yixian.effects import EffectEngine, SUPPORTED_FATES
from yixian.fate_catalog import discover_runtime_support, _execution
from yixian.effect_battle import simulate_effect_battle


def actor(fates=(), **values):
    return dict({'life': 50, 'fates': list(fates), 'season_choices': [], 'rerolls': 0}, **values)


class DragonScaleTests(unittest.TestCase):
    def test_boundary_and_no_life_deduction(self):
        engine = EffectEngine()
        original = actor([27])
        for damage, expected in ((0, 0), (19, 19), (20, 20), (21, 20), (100, 20)):
            result = engine.settle(actor(), original, damage)
            self.assertEqual(result['life_damage'], expected)
            self.assertEqual(result['loser']['life'], 50)
            self.assertEqual(len(result['events']), int(damage > 20))
        self.assertEqual(original, actor([27]))

    def test_cap_before_even_halving_and_immunity(self):
        engine = EffectEngine()
        loser = engine.initialize_player(actor([27, 45, 105]), talent_counters={'105': 1})
        result = engine.settle(actor(), loser, 31)
        self.assertEqual(result['life_damage'], 10)
        self.assertEqual([e['effect_id'] for e in result['events']], [27, 45])
        self.assertEqual(result['loser']['effect_state']['talent_105_remaining'], 1)

    def test_cap_then_immunity_is_consumed_once(self):
        engine = EffectEngine()
        loser = engine.initialize_player(actor([27, 105]), talent_counters={'105': 1})
        result = engine.settle(actor(), loser, 31)
        self.assertEqual(result['life_damage'], 0)
        self.assertEqual([e['effect_id'] for e in result['events']], [27, 105])
        again = engine.settle(actor(), result['loser'], 31)
        self.assertEqual(again['life_damage'], 20)

    def test_cap_then_single_death_prevention(self):
        engine = EffectEngine()
        loser = engine.initialize_player(actor([27, 7], life=10), newly_acquired_fates=(7,))
        result = engine.settle(actor(), loser, 31)
        self.assertEqual(result['life_damage'], 9)
        self.assertEqual(result['loser']['rerolls'], 5)
        self.assertEqual([e['effect_id'] for e in result['events']], [27, 7])

    def test_winner_kindness_precedes_cap(self):
        result = EffectEngine().settle(actor(season_choices=[2011]), actor([27, 45]), 31)
        self.assertEqual(result['life_damage'], 10)
        self.assertEqual([e['effect_id'] for e in result['events']], [2011, 27, 45, 2011])

    def test_cap_independent_of_once_upgrade_counter_and_repeatable(self):
        engine = EffectEngine()
        for raw in ({}, {'27': 0}, {'27': 1}):
            loser = engine.initialize_player(actor([27]), talent_counters=raw)
            for _ in range(3):
                result = engine.settle(actor(), loser, 45)
                self.assertEqual(result['life_damage'], 20)
                self.assertEqual(result['loser']['effect_state'], loser['effect_state'])
                loser = result['loser']

    def test_mirror_and_already_eliminated_bypass_only_this_component(self):
        self.assertEqual(cap_damage(31, life_before_battle=50, is_mirror=True), 31)
        self.assertEqual(cap_damage(31, life_before_battle=0), 31)
        self.assertEqual(cap_damage(31, life_before_battle=-5), 31)
        self.assertEqual(EffectEngine().settle(actor(), actor([27], is_mirror=True), 31)['life_damage'], 31)

    def test_invalid_context_fails_without_mutating_input(self):
        for values in ({'life': None}, {'life': True}, {'is_mirror': 0}):
            loser = actor([27], **values)
            before = deepcopy(loser)
            with self.assertRaises(ValueError):
                EffectEngine().settle(actor(), loser, 31)
            self.assertEqual(loser, before)
        for values in ({'damage': True}, {'damage': -1}, {'limit': 0}, {'limit': True}):
            kwargs = dict(damage=30, life_before_battle=50, **{})
            kwargs.update(values)
            with self.assertRaises(ValueError):
                cap_damage(**kwargs)

    def test_configurable_cap_is_in_environment_contract(self):
        engine = EffectEngine(dragon_scale_limit=18)
        self.assertEqual(engine.settle(actor(), actor([27]), 19)['life_damage'], 18)
        self.assertEqual(engine.contract()['parameters']['dragon_scale_limit'], 18)
        self.assertEqual(EffectEngine.from_local().dragon_scale_limit, 20)

    def test_partial_component_never_becomes_whole_fate(self):
        self.assertNotIn(27, SUPPORTED_FATES)
        coverage = EffectEngine.coverage(actor([27]))
        self.assertIn(27, coverage['unsupported_fates'])
        self.assertEqual(coverage['partial_fates'], [27])
        entry = _execution('regular', 27, discover_runtime_support())
        self.assertFalse(entry['complete_effect'])
        self.assertIn('destiny_damage_cap', entry['components'])

    def test_terminal_cap_diagnostic_cannot_become_training_label(self):
        battle = {'players': [dict(character='sw3', hp=40, max_hp=40, cultivation=10,
                                  round_number=15, destiny=50, cards=['111011'] * 8) for _ in range(2)]}
        def terminal(_):
            return {'winner': 0, 'terminated': True, 'truncated': False,
                    'players': [{'hp': 40, 'destiny': 50}, {'hp': -50, 'destiny': 0}]}
        result = simulate_effect_battle(battle, [actor(), actor([27])], engine=EffectEngine(), simulator=terminal)
        self.assertEqual(result['settlement']['life_damage'], 20)
        self.assertEqual(result['match_players'][1]['life'], 30)
        self.assertFalse(result['label_usable'])
