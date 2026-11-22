"""Compare declared reward outcome sets; never choose using the observed board."""
from collections import Counter

from .dragon_scale_reward import initialize_reward, apply_post_battle_upgrade, REMAINING, CHARACTER


def audit_reward_snapshot(player, card_catalog):
    start = player['start_snapshot']
    after = player['after_snapshot']
    if player.get('audit_context', {}).get('is_mirror') is not False:
        return {'status': 'mirror_or_unknown_context', 'training_label_allowed': False}
    if type(start.get('destiny')) is not int or start['destiny'] <= 0:
        return {'status': 'already_eliminated_or_unknown_start_destiny', 'training_label_allowed': False}
    # This is a conditional post-battle reward check. Recorded final destiny
    # supplies the phase condition, never an initial combat/policy observation.
    initial = initialize_reward({'character_id': CHARACTER, 'fates': [27],
        'life': after.get('destiny'), 'board': start.get('board'), 'is_mirror': False},
        talent_counters=start.get('talentTempDatas'))
    first = apply_post_battle_upgrade(initial, card_catalog)
    possible = ([apply_post_battle_upgrade(initial, card_catalog, selected_slot=slot)
                 for slot in first['pending_actions'][0]['candidate_slots']]
                if first['pending_actions'] else [first])
    # Only after every possible output has been constructed read expectations.
    board = player.get('private_snapshot', {}).get('board')
    counters = after.get('talentTempDatas')
    if not isinstance(board, list) or not isinstance(counters, dict) or type(counters.get('27')) is not int:
        return {'status': 'expected_output_missing', 'training_label_allowed': False}
    predictions = [{'board': r['player']['board'], 'remaining': r['player']['effect_state'][REMAINING]}
                   for r in possible]
    expected = {'board': board, 'remaining': counters['27']}
    return {'status': 'compared', 'allowed_output_match': expected in predictions,
            'deterministic': len(possible) == 1, 'allowed_choice_count': len(possible),
            'predicted_outputs': predictions, 'expected_output': expected,
            'input_board': initial['board'], 'input_remaining': initial['effect_state'][REMAINING],
            'recorded_post_battle_destiny_condition': initial['life'],
            'observed_counter_consumed': initial['effect_state'][REMAINING] == 1 and counters['27'] == 0,
            'no_candidate_charge_preserved': bool(first['events']) and first['events'][0].get('status') == 'no_eligible_board_card',
            'training_label_allowed': False, 'complete_battle_prediction': False}


def summarize_reward_audit(rows):
    compared = [r for r in rows if r['status'] == 'compared']
    deterministic = [r for r in compared if r['deterministic']]
    return {'scope': 'conditional_post_battle_upgrade_allowed_output_set',
            'snapshots': len(rows), 'status_counts': dict(Counter(r['status'] for r in rows)),
            'compared_snapshots': len(compared), 'allowed_output_matches': sum(r['allowed_output_match'] for r in compared),
            'allowed_output_mismatches': sum(not r['allowed_output_match'] for r in compared),
            'deterministic_snapshots': len(deterministic), 'deterministic_matches': sum(r['allowed_output_match'] for r in deterministic),
            'multiple_choice_snapshots': sum(not r['deterministic'] for r in compared),
            'observed_charge_consumptions': sum(r['observed_counter_consumed'] for r in compared),
            'no_candidate_charge_preserved_snapshots': sum(r['no_candidate_charge_preserved'] for r in compared),
            'recorded_post_battle_destiny_used_as_condition': True, 'outcome_used_to_choose_random_slot': False,
            'random_distribution_verified': False, 'counter_semantics_server_certified': False,
            'current_server_calibration_passed': False, 'complete_combat_replayed': False,
            'full_match_integration_complete': False, 'training_labels_emitted': 0,
            'limitations': ['This compares a set of legal reward outputs, not model accuracy or random probability.',
                           'Recorded post-battle destiny is supplied as the reward phase condition.',
                           'Private usedCards are expected output only; never a policy or initial combat input.',
                           'Other reward effects and exact snapshot timing are not fully excluded.',
                           'No complete battle, full-match training eligibility, or real-game strength claim.']}
