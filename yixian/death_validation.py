"""Reproducible, trigger-conditioned death-fate replay diagnostics.

Recorded destiny damage is already capped by protection. Counter transitions
can establish that a protection was used, but cannot reconstruct pre-protection
damage or independently validate its trigger threshold. This audit checks only
the observable consequences; no after-state is used to infer battle destiny.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json

from .death_fates import DEATH_FATES, FIVE_ELEMENTS, apply_death_prevention


def audit_death_fate_records(records, card_catalog):
    cards = {card['id']: card for card in card_catalog}
    counts = {str(fate): {'owned_snapshots': 0, 'observed_triggers': 0,
                         'checked_triggers': 0, 'excluded_triggers': 0}
              for fate in sorted(DEATH_FATES)}
    samples, games, splits = [], set(), set()
    for record in records:
        games.add(record.get('game_id'))
        splits.add(record.get('dataset_split', 'unknown'))
        for player in record['players']:
            before, after = player['start_snapshot'], player['after_snapshot']
            owned = set(before.get('talents', [])) & DEATH_FATES
            for fate in sorted(owned):
                key = str(fate)
                counts[key]['owned_snapshots'] += 1
                old = before.get('talentTempDatas', {}).get(key, 0)
                new = after.get('talentTempDatas', {}).get(key, 0)
                if type(old) is not int or type(new) is not int or not (old > 0 and new == 0):
                    continue
                counts[key]['observed_triggers'] += 1
                sample = {'effect_id': fate, 'game_id': record.get('game_id'),
                          'record_id': record.get('id'), 'round': record.get('round'),
                          'source_member': record.get('source', {}).get('member'),
                          'dataset_split': record.get('dataset_split'),
                          'snapshot_slot': player.get('snapshot_slot'),
                          'checks': [], 'not_checked': ['pre_protection_damage', 'trigger_threshold'],
                          'scope': 'observed_counter_trigger_conditioned_consequences'}
                samples.append(sample)
                reasons = []
                # Inspect both boards because a destiny-changing card can affect
                # either side. We do not infer a delta from after life or damage.
                risky_cards, unknown_cards = [], []
                for combatant in record['players']:
                    for card_id in combatant['start_snapshot'].get('board', []):
                        if not card_id:
                            continue
                        card = cards.get(card_id)
                        if card is None:
                            unknown_cards.append(card_id)
                        elif '命元' in card.get('description_preview', card.get('desc', '')):
                            risky_cards.append({'id': card_id, 'name': card['name']})
                if risky_cards:
                    reasons.append('battle_destiny_changing_cards_prevent_start_life_settlement_validation')
                    sample['destiny_changing_cards'] = risky_cards
                if unknown_cards:
                    reasons.append('unknown_battle_cards_prevent_destiny_change_exclusion')
                    sample['unknown_card_ids'] = sorted(set(unknown_cards))
                if fate == 83 and player.get('is_ai'):
                    reasons.append('uncalibrated_ai_fate_83_reward_branch')
                if reasons:
                    sample.update(status='excluded', excluded_reasons=reasons)
                    counts[key]['excluded_triggers'] += 1
                    continue

                def check(name, expected, observed):
                    sample['checks'].append({'name': name, 'expected': expected,
                                             'observed': observed, 'match': expected == observed})

                check('retained_destiny', 1, after.get('destiny'))
                if fate == 7:
                    # Start snapshots lack a trustworthy reroll account. Do not
                    # invent one by subtracting five from the after snapshot.
                    sample['not_checked'].append('rerolls_bonus_missing_start_account')
                elif fate == 65:
                    actor = {'life': before['destiny'], 'fates': [65], 'exp': before['exp'],
                             'hand_cards': before.get('hand', [])}
                    result = apply_death_prevention(actor, actor['life'], talent_counters={key: old})
                    sample['module_check_condition'] = 'explicitly_forced_lethal_damage_not_reconstructed_server_damage'
                    check('cultivation_after', result['player']['exp'], after.get('exp'))
                    hand = player.get('private_snapshot', {}).get('hand')
                    if hand is None:
                        sample['not_checked'].append('reward_card_missing_private_hand')
                    else:
                        check('hand_after', sorted(result['player']['hand_cards']), sorted(hand))
                elif fate == 83:
                    check('cultivation_after', before['exp'] - 5, after.get('exp'))
                    hand = player.get('private_snapshot', {}).get('hand')
                    if hand is None:
                        sample['not_checked'].append('five_element_reward_missing_private_hand')
                    else:
                        prior, later = Counter(before.get('hand', [])), Counter(hand)
                        added, removed = list((later - prior).elements()), list((prior - later).elements())
                        sample['observed_cards_added'] = added
                        check('original_hand_preserved', [], removed)
                        check('reward_card_count', 5, len(added))
                        element_names = {'木': 'wood', '火': 'fire', '土': 'earth', '金': 'metal', '水': 'water'}
                        elements, realms = [], []
                        for card_id in added:
                            card = cards.get(card_id, {})
                            elements.append(element_names.get(card.get('name', '')[:1]))
                            realms.append(card.get('level'))
                        check('five_distinct_elements', sorted(FIVE_ELEMENTS), sorted(elements, key=str))
                        check('all_yuan_ying_or_above', True,
                              all(type(realm) is int and realm >= 4 for realm in realms))
                    sample['not_checked'].append('server_draw_distribution')
                elif fate == 154:
                    check('extra_max_hp_modifier', before.get('extra_max_hp_modifier', 0) + 4,
                          after.get('extra_max_hp_modifier'))
                    old_cap = before.get('permanentBuffTempDatas', {}).get('10024')
                    new_cap = after.get('permanentBuffTempDatas', {}).get('10024')
                    if type(old_cap) is int and type(new_cap) is int:
                        check('max_physique', old_cap + 4, new_cap)
                    else:
                        sample['not_checked'].append('missing_physique_cap')
                sample['status'] = ('matched_observable_consequences' if all(x['match'] for x in sample['checks'])
                                    else 'observable_consequence_mismatch')
                counts[key]['checked_triggers'] += 1
    checks = [check for sample in samples for check in sample['checks']]
    return {'schema_version': 1, 'scope': 'death_fate_trigger_conditioned_replay_diagnostic',
            'counts_are_snapshot_views_not_independent_players': True,
            'whole_games_seen': len(games), 'dataset_splits_examined': sorted(splits),
            'test_split_used_for_diagnosis': 'test' in splits,
            'counts_by_effect': counts, 'observable_checks': len(checks),
            'observable_mismatches': sum(not check['match'] for check in checks),
            'samples': samples, 'complete_battle_validation': False,
            'server_damage_reconstructed': False, 'usable_for_policy_training': False,
            'limitations': [
                'Counter transitions select observed triggers; trigger thresholds are not independently validated.',
                'Recorded destiny damage is already affected by protection and cannot be reused as raw damage.',
                'Post-combat destiny is never inferred from after life plus recorded damage.',
                'Views of one whole game are correlated; anonymous player identities remain source-local.',
                'Description-derived draw constraints do not identify the server draw distribution.',
                'Snapshot timing and full battle inputs remain uncalibrated.']}


def validate_death_fate_replays(rounds_path, *, local_root='data/local/2026-11-06'):
    rounds_path, local_root = Path(rounds_path), Path(local_root)
    card_path = local_root / 'tables/CardConfig.json'
    data, card_data = rounds_path.read_bytes(), card_path.read_bytes()
    result = audit_death_fate_records((json.loads(line) for line in data.splitlines() if line),
                                     json.loads(card_data))
    result['sources'] = {'rounds_path': str(rounds_path), 'local_snapshot': str(local_root),
                         'rounds_sha256': hashlib.sha256(data).hexdigest(),
                         'CardConfig_sha256': hashlib.sha256(card_data).hexdigest()}
    return result
