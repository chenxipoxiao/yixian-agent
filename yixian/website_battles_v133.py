"""Owner-observed sound switches for the separate website diagnostic contract.

The battle rules and the v132 adapter remain frozen. A complete private switch
receipt is required; the legacy absent-key default is never used for this source.
"""
from . import website_battles_v132 as previous
from .combat_compiler_view_v81 import compiler_modules

ORIGIN = previous.ORIGIN
UnresolvedBattle = previous.UnresolvedBattle
SOUND_IDS = frozenset({1003, 1005, 1007})


def compiler():
    view = previous.compiler()
    modules = compiler_modules(view)
    previous.replace_function(modules['yixian.full_battle_v52r2'], 'compile_start', [
        ('privateData.xianMoData:preparation_switch', ORIGIN)])
    return view


def compile_case(case, view, tables):
    row = case['row']
    for seat, (player, context) in enumerate(zip(row['players'], case['combat_context']['players'])):
        receipt = context.get('sound_control_switch')
        if receipt is None:
            continue  # The existing compiler blocks an owned effect without evidence.
        owned = sorted(SOUND_IDS.intersection(player['candidate_start']['xian_mo_strategies']))
        if (seat != 0 or context.get('website_hand_unknown') is not False
                or case.get('preparation_owner_verified') is not True):
            raise UnresolvedBattle('website_sound_switch_not_verified_private_owner')
        if (receipt.get('origin') != ORIGIN or receipt.get('environment_only') is not True
                or receipt.get('source_raw_sha256') != row['source']['raw_sha256']
                or receipt.get('source_step') != row['source']['step']
                or receipt.get('case_id') != row['id']
                or receipt.get('player_index') != seat
                or receipt.get('selected_strategy_ids') != owned):
            raise UnresolvedBattle('website_sound_switch_source_binding_mismatch')
        values = receipt.get('temp_data')
        if (not isinstance(values, dict) or set(values) != {str(x) for x in owned}
                or any(type(v) is not int or v not in (0, 1) for v in values.values())):
            raise UnresolvedBattle('website_sound_switch_explicit_boolean_required')
    return previous.compile_case(case, view, tables)
