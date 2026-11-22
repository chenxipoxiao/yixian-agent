"""Client's ordinary destiny-damage branch, isolated from seasonal modifiers."""
from __future__ import annotations

import math


def ordinary_destiny_damage(round_number: int, hp_difference: int | float) -> int:
    """Base branch recovered from CalLifeDamage; not the complete server rule.

    Mode-specific multipliers, Fate21 and XianMo2011 reductions, immunity and
    server-authoritative results must be handled separately before live use.
    """
    if type(round_number) is not int or round_number < 1:
        raise ValueError('round_number must be a positive integer')
    if type(hp_difference) not in (int, float) or not math.isfinite(hp_difference) or hp_difference < 0:
        raise ValueError('hp_difference must be finite and nonnegative')
    if hp_difference <= 20:
        damage = round_number + 1 + math.ceil(hp_difference / 5)
    else:
        damage = round_number + 5 + min(math.ceil((hp_difference - 20) / 10), 2 + round_number // 2)
    return damage - int(round_number <= 9)


def audit_recorded_damage(rounds):
    comparisons = []
    for row in rounds:
        result = row.get('outcome', {})
        delta, actual = result.get('recorded_hp_delta'), result.get('recorded_destiny_damage')
        if result.get('status') != 'recorded_winner' or delta is None or actual is None:
            continue
        predicted = ordinary_destiny_damage(row['round'], abs(delta))
        comparisons.append({'record_id': row['id'], 'round': row['round'],
                            'predicted_base_damage': predicted, 'recorded_damage_magnitude': abs(actual),
                            'match': predicted == abs(actual)})
    return {'scope': 'ordinary_client_branch_vs_recorded_magnitude',
            'records_checked': len(comparisons), 'matching': sum(x['match'] for x in comparisons),
            'mismatching': sum(not x['match'] for x in comparisons),
            'current_season_rules_verified': False, 'comparisons': comparisons,
            'limitation': 'Includes repeated perspectives; matches validate this branch on these records only. Special reductions and all other rules remain separate.'}
