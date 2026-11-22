"""Mirror-aware diagnostic damage, never an authoritative mirror balance.

For a live loser the existing v47 sequence is retained. For a mirror loser,
the client reports CalLifeDamage before the live loser's mitigation and
survival checks. The displayed amount is separate from a match-state loss.
"""
from types import FunctionType
from . import terminal_damage_v47 as legacy
from . import terminal_damage_v38 as legacy38
from .terminal_damage_base_v129 import calculate_terminal_damage as mirror_base
from .full_battle_v129 import extension_contract


def _private_function(function, **bindings):
    namespace = dict(function.__globals__)
    namespace.update(bindings)
    return FunctionType(function.__code__, namespace, function.__name__, function.__defaults__)


def calculate_terminal_damage(compiled, result):
    flags = [p.get('is_mirror') for p in compiled['effect_players']]
    if len(flags) != 2 or any(type(x) is not bool for x in flags):
        raise ValueError('Explicit mirror markers required')
    if not any(flags):
        return legacy.calculate_terminal_damage(compiled, result)
    extension_contract()
    if compiled.get('battle', {}).get('mirror_context', {}).get('is_mirror') != flags:
        raise ValueError('Mirror battle and settlement context mismatch')
    prior = _private_function(legacy38.calculate_terminal_damage, previous=mirror_base)
    calculate = _private_function(legacy.calculate_terminal_damage, base_damage=mirror_base, previous=prior)
    answer = calculate(compiled, result)
    if answer.get('resolved'):
        answer['mirror_context_v129'] = {
            'is_mirror': flags, 'match_state_mutated': False,
            'authoritative_mirror_balance_inferred': False,
            'mirror_defeat_display_only': flags[answer['loser']],
        }
        # v47's optional civet preview must never invent a mirror's balance.
        civet = answer.get('civet_settlement')
        if civet is not None:
            for key in ['predicted_destiny_after_terminal_damage', 'predicted_net_change']:
                for seat, mirror in enumerate(flags):
                    if mirror:
                        civet[key][seat] = None
            civet['mirror_balance_projection_allowed'] = False
    return answer
