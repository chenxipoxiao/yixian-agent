from copy import deepcopy
import unittest

from yixian.terminal_damage_v38 import calculate_terminal_damage as old
from yixian.terminal_damage_v47 import calculate_terminal_damage, CIVET_PROOF_SHA


def fixture(life=14, gains=(3, 0), fates=(7,), counter=1):
    players = [dict(fates=list(fates), season_choices=[], life=life,
                    talent_counters={str(f): counter for f in fates}, is_mirror=False),
               dict(fates=[], season_choices=[], life=99, talent_counters={}, is_mirror=False)]
    compiled = {'battle': {'players': [{'round_number': 10}, {'round_number': 10}]},
                'effect_players': players,
                'context': {'game_mode': 3, 'season_mec': 10, 'resonance_selected': 0}}
    events = []
    for seat, gain in enumerate(gains):
        for raw, amount in [(20433, 9), (10433, 6), (433, 3)]:
            while gain >= amount:
                events.append({'player_index': seat, 'raw_card': raw, 'is_mirror': False,
                               'phase': 'card_body_after_hp_recovery', 'requested_destiny_gain': amount,
                               'authoritative_match_state_mutated': False})
                gain -= amount
        assert gain == 0
    result = {'terminated': True, 'truncated': False, 'winner': 1,
              'players': [{'hp': -1, 'direct_destiny_lost': 0, 'kindness_tune_stacks': 0},
                          {'hp': 19, 'direct_destiny_lost': 0, 'kindness_tune_stacks': 0}],
              'civet_v38': {'evidence_sha256': CIVET_PROOF_SHA,
                            'events': events, 'requested_destiny_gains': list(gains)}}
    return compiled, result


class CivetSettlementTests(unittest.TestCase):
    def test_no_civet_preserves_legacy(self):
        c, r = fixture(); r.pop('civet_v38')
        self.assertEqual(calculate_terminal_damage(c, r), old(c, r))

    def test_winner_and_loser_can_exceed100_before_damage(self):
        c, r = fixture(life=99, gains=(3, 6), fates=())
        d = calculate_terminal_damage(c, r); net = d['civet_settlement']
        self.assertEqual(net['destiny_before_terminal_damage'], [102, 105])
        self.assertEqual(net['predicted_destiny_after_terminal_damage'], [87, 105])
        self.assertEqual(d['life_damage'], 15)
        self.assertEqual(net['predicted_net_change'], [-12, 6])

    def test_gain_avoids_consuming_each_survival_fate(self):
        for fate in [7, 65, 83, 154]:
            with self.subTest(fate=fate):
                c, r = fixture(fates=(fate,)); d = calculate_terminal_damage(c, r)
                self.assertEqual(d['life_damage'], 15)
                self.assertEqual(d['loser_destiny_after'], 2)
                self.assertEqual(d['pending_match_effects'], [])

    def test_equal_damage_triggers_each_survival_fate_after_gain(self):
        for fate in [7, 65, 83, 154]:
            with self.subTest(fate=fate):
                c, r = fixture(life=12, fates=(fate,)); d = calculate_terminal_damage(c, r)
                self.assertEqual(d['loser_destiny_before'], 15)
                self.assertEqual(d['life_damage'], 14)
                self.assertEqual(d['loser_destiny_after'], 1)
                self.assertEqual(d['pending_match_effects'], [{'kind': 'survival_counter_and_reward', 'fate': fate}])

    def test_gross_damage_and_net_loss_are_distinct(self):
        c, r = fixture(life=1); d = calculate_terminal_damage(c, r)
        self.assertEqual(d['life_damage'], 3)
        self.assertEqual(d['civet_settlement']['predicted_net_change'][0], 0)
        self.assertFalse(d['match_state_mutated'])
        self.assertFalse(d['full_match_transition_complete'])
        self.assertFalse(d['training_label_allowed'])

    def test_spent_survival_does_not_revive_or_clamp_negative_life(self):
        c, r = fixture(life=1, counter=0); d = calculate_terminal_damage(c, r)
        self.assertEqual(d['life_damage'], 15)
        self.assertEqual(d['loser_destiny_after'], -11)
        self.assertEqual(d['pending_match_effects'], [])

    def test_repeated_calls_are_pure_and_dont_double_credit(self):
        c, r = fixture(gains=(12, 3)); before = deepcopy((c, r))
        a = calculate_terminal_damage(c, r); b = calculate_terminal_damage(c, r)
        self.assertEqual(a, b); self.assertEqual(before, (c, r))
        self.assertEqual(a['civet_settlement']['destiny_before_terminal_damage'], [26, 102])

    def test_zero_mirror_gain_never_becomes_live_credit(self):
        c, r = fixture(gains=(0, 0)); c['effect_players'][0]['is_mirror'] = True
        r['civet_v38']['events'] = [{'player_index': 0, 'raw_card': 433, 'is_mirror': True,
            'phase': 'card_body_after_hp_recovery', 'requested_destiny_gain': 0,
            'authoritative_match_state_mutated': False}]
        # The legacy settlement intentionally rejects a live-vs-mirror match.
        with self.assertRaisesRegex(ValueError, 'non-mirror'):
            calculate_terminal_damage(c, r)

    def test_forged_aggregate_or_event_cannot_credit(self):
        mutations = [('requested_destiny_gains', [9, 0]), ('evidence_sha256', 'wrong')]
        for key, value in mutations:
            c, r = fixture(); r['civet_v38'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                calculate_terminal_damage(c, r)
        for key, value in [('raw_card', 999), ('requested_destiny_gain', True),
                           ('is_mirror', True), ('player_index', True),
                           ('authoritative_match_state_mutated', True)]:
            c, r = fixture(); r['civet_v38']['events'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                calculate_terminal_damage(c, r)

    def test_direct_destiny_loss_remains_unresolved(self):
        for seat in [0, 1]:
            c, r = fixture(); r['players'][seat]['direct_destiny_lost'] = 1
            d = calculate_terminal_damage(c, r)
            self.assertEqual(d['reason'], 'in_combat_destiny_ledger_required')
            self.assertNotIn('civet_settlement', d)

    def test_multiple_available_survival_order_still_unresolved(self):
        c, r = fixture(life=1, fates=(7, 65)); d = calculate_terminal_damage(c, r)
        self.assertEqual(d['reason'], 'multiple_survival_effect_order_unknown')
        c['effect_players'][0]['life'] = 20
        self.assertTrue(calculate_terminal_damage(c, r)['resolved'])

    def test_truncated_battle_does_not_publish_gain_or_net_balance(self):
        c, r = fixture(); r.update(terminated=False, truncated=True, winner=None)
        d = calculate_terminal_damage(c, r)
        self.assertFalse(d['resolved']); self.assertNotIn('civet_settlement', d)

    def test_damage_reduction_and_guard_keep_existing_order(self):
        c, r = fixture(life=1, fates=(7, 105)); c['effect_players'][1]['season_choices'] = [2011]
        r['players'][0]['hp'] = -200
        d = calculate_terminal_damage(c, r)
        # Threshold and modifiers are unchanged; available105 prevents later survival.
        self.assertEqual(d['life_damage'], 0)
        self.assertEqual(d['pending_match_effects'], [{'kind': 'consume_fate_counter', 'fate': 105}])
        self.assertEqual(d['loser_destiny_after'], 4)

    def test_context_and_technical_integer_boundaries(self):
        for field, value in [('game_mode', 4), ('season_mec', 9), ('resonance_selected', 1)]:
            c, r = fixture(); c['context'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                calculate_terminal_damage(c, r)
        for life in [0, -1, True, None, 2147483647]:
            c, r = fixture(life=life)
            with self.subTest(life=life), self.assertRaises(ValueError):
                calculate_terminal_damage(c, r)


if __name__ == '__main__':
    unittest.main()
