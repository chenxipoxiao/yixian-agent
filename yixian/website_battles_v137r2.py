"""Distinguish recorded Suan Ni skip choices from combat strategy ownership.

Raw24/25 in the seasonal-choice namespace are skip selectors, independent of
ordinary fate24/25. No obtained fate, preparation reward or combat input is
created here. Every other ownership disagreement still blocks execution.
"""
from copy import deepcopy
from . import website_battles_v137 as previous

ORIGIN=previous.ORIGIN
UnresolvedBattle=previous.UnresolvedBattle
compiler=previous.compiler
validate_owner_parameters=previous.validate_owner_parameters

def normalize_choice_ownership(case):
    receipt=case['combat_context']['players'][0].get('website_skip_ownership_v137r2')
    if receipt is None:return case
    row=case['row'];ctx=case['combat_context']['players'][0]
    if case.get('preparation_owner_verified') is not True or ctx.get('website_hand_unknown') is not False:
        raise UnresolvedBattle('website_skip_v137r2:private_owner_required')
    expected={'origin':ORIGIN,'source_raw_sha256':row['source']['raw_sha256'],'source_step':row['source']['step'],
        'case_id':row['id'],'player_index':0,'environment_only':True,
        'battle_strategy_ids':row['players'][0]['candidate_start']['xian_mo_strategies']}
    if not isinstance(receipt,dict) or any(receipt.get(k)!=v for k,v in expected.items()):
        raise UnresolvedBattle('website_skip_v137r2:source_binding_mismatch')
    private=receipt.get('private_selected_ids');skips=receipt.get('observed_suanni_skip_ids')
    if (not isinstance(private,list) or not isinstance(skips,list)
            or any(type(x)is not int for x in private+skips) or len(set(private))!=len(private)
            or not skips or skips!=sorted(set(private)&{24,25})
            or receipt.get('metadata_verified_skip_ids')!=skips
            or set(private)-set(skips)!=set(expected['battle_strategy_ids'])):
        raise UnresolvedBattle('website_skip_v137r2:ownership_mismatch')
    conflict='private_vs_battle_strategy_ownership'
    result=deepcopy(case)
    result['input_conflicts']=[v for v in case['input_conflicts'] if v!=conflict]
    return result

def compile_case(case,view,tables):
    return previous.compile_case(normalize_choice_ownership(case),view,tables)
