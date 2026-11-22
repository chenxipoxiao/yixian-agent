from copy import deepcopy
import unittest
from yixian.dragon_scale_validation import audit_dragon_scale
from yixian.order_data import CHARACTER, VERSION


def record():
    def player(slot, fate):
        return {'snapshot_slot': slot, 'character_id': CHARACTER, 'is_ai': False,
                'audit_context': {'is_mirror': False, 'resonance_selected': 0},
                'start_snapshot': {'talents': fate, 'board': [], 'fate_strategies': [],
                                   'xian_mo_strategies': [], 'destiny': 35,
                                   'talentTempDatas': {}},
                'after_snapshot': {'destiny': 15, 'talentTempDatas': {'27': 1}}}
    return {'id': 'synthetic', 'game_id': 'synthetic-game', 'round': 15,
            'source_rules_version': VERSION, 'game_mode': 3, 'season_mec': 10,
            'players': [player('p1', []), player('p2', [27])],
            'outcome': {'status': 'recorded_winner', 'winner_snapshot_slot': 'p1',
                        'recorded_hp_delta': 90, 'recorded_destiny_damage': 20}}


class DragonScaleValidationTests(unittest.TestCase):
    def test_expected_cap_and_unmodified_baseline(self):
        result = audit_dragon_scale([record()])
        self.assertEqual((result['compared_snapshots'], result['component_matches'], result['baseline_matches']), (1, 1, 0))
        self.assertEqual(result['cap_triggered_snapshots'], 1)
        self.assertFalse(result['current_server_calibration_passed'])
        self.assertEqual(result['training_labels_emitted'], 0)
        self.assertEqual(result['counter_observations'][0]['start_life'], 35)
        self.assertEqual(result['counter_observations'][0]['after_life'], 15)

    def test_after_counters_and_boards_never_repair_prediction(self):
        row = record(); before = deepcopy(row)
        first = audit_dragon_scale([row])
        row['players'][1]['after_snapshot'] = {'destiny': 200, 'talentTempDatas': {'27': 999}, 'board': [10015]}
        second = audit_dragon_scale([row])
        self.assertEqual(first['records'], second['records'])
        self.assertEqual(first['counter_transitions'], {'absent->1': 1})
        self.assertEqual(before['players'][1]['start_snapshot'], row['players'][1]['start_snapshot'])

    def test_mirror_unknown_resonance_and_wrong_version_excluded(self):
        for mutation in ('mirror', 'unknown', 'resonance', 'version'):
            row = record()
            if mutation == 'mirror': row['players'][1]['audit_context']['is_mirror'] = True
            if mutation == 'unknown': row['players'][1]['audit_context'] = {}
            if mutation == 'resonance': row['players'][1]['audit_context']['resonance_selected'] = 27
            if mutation == 'version': row['source_rules_version'] = 'unknown'
            result = audit_dragon_scale([row])
            self.assertEqual(result['compared_snapshots'], 0)
            self.assertEqual(result['excluded_snapshots'], 1)

    def test_known_destiny_card_or_death_prevention_excluded(self):
        for key, value in (('board', [5000006]), ('talents', [27, 7]), ('fate_strategies', [21])):
            row = record(); row['players'][1]['start_snapshot'][key] = value
            self.assertEqual(audit_dragon_scale([row])['compared_snapshots'], 0)

    def test_mismatch_kept_and_no_target_has_zero_coverage(self):
        row = record(); row['outcome']['recorded_destiny_damage'] = 19
        self.assertEqual(audit_dragon_scale([row])['component_mismatches'], 1)
        row['players'][1]['start_snapshot']['talents'] = []
        result = audit_dragon_scale([row])
        self.assertEqual(result['compared_snapshots'], 0)
        self.assertFalse(result['counter_semantics_verified'])

    def test_missing_normalized_destiny_is_not_filled_from_raw_alias_or_after_state(self):
        row = record()
        row['players'][1]['start_snapshot']['life'] = row['players'][1]['start_snapshot'].pop('destiny')
        result = audit_dragon_scale([row])
        self.assertEqual(result['compared_snapshots'], 0)
        self.assertIn('pre_battle_life_unavailable_or_eliminated', result['exclusion_reasons'])

    def test_unknown_resonance_selection_is_not_assumed_inactive(self):
        row = record(); del row['players'][1]['audit_context']['resonance_selected']
        result = audit_dragon_scale([row])
        self.assertEqual(result['compared_snapshots'], 0)
        self.assertIn('loser_resonance_selected_or_unknown', result['exclusion_reasons'])

    def test_winning_dragon_scale_does_not_reduce_opponents_damage(self):
        row = record(); row['players'][0]['start_snapshot']['talents'] = [27]
        row['players'][1]['start_snapshot']['talents'] = []
        result = audit_dragon_scale([row])
        self.assertEqual(result['targeted_losing_snapshots'], 0)
        self.assertEqual(result['counter_observation_snapshots'], 1)
