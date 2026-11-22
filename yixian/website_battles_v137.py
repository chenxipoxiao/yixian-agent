"""Source-bound owner switches for additional website development recordings.

No combat effect changes. Preserve missing opponent parameters and all frozen
adapters. The extractor separately verifies the receipt against original steps.
"""
from . import website_battles_v135r2 as previous
from .combat_season_inputs_v124 import SWITCH_IDS, GRID_IDS

ORIGIN=previous.ORIGIN
UnresolvedBattle=previous.UnresolvedBattle
compiler=previous.compiler

def validate_owner_parameters(case):
    row=case['row']
    for seat,(p,ctx) in enumerate(zip(row['players'],case['combat_context']['players'])):
        owned=set(p['candidate_start']['xian_mo_strategies'])
        required=owned&(SWITCH_IDS|GRID_IDS)
        supplied=ctx.get('website_strategy_parameters',{})
        present={str(x):supplied[str(x)] for x in required if str(x) in supplied}
        receipt=ctx.get('website_owner_preparation_v137')
        if not present and receipt is None:
            continue  # The original compiler rejects missing data when read.
        if (seat!=0 or ctx.get('website_hand_unknown') is not False
                or case.get('preparation_owner_verified') is not True):
            raise UnresolvedBattle('website_owner_v137:private_owner_required')
        if not isinstance(receipt,dict):
            raise UnresolvedBattle('website_owner_v137:receipt_required')
        expected={'origin':ORIGIN,'source_raw_sha256':row['source']['raw_sha256'],
            'source_step':row['source']['step'],'case_id':row['id'],'player_index':seat,
            'environment_only':True,'selected_strategy_ids':sorted(required),'parameters':present}
        if any(receipt.get(k)!=v for k,v in expected.items()):
            raise UnresolvedBattle('website_owner_v137:source_binding_mismatch')
        digest=receipt.get('private_state_sha256')
        if (not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest)
                or set(present)!={str(x) for x in required}):
            raise UnresolvedBattle('website_owner_v137:complete_private_parameters_required')
        for sid in required:
            v=present[str(sid)]
            if type(v)is not int or (sid in SWITCH_IDS and v not in (0,1)) or (
                    sid in GRID_IDS and not 0<=v<len(p['candidate_start']['board'])):
                raise UnresolvedBattle('website_owner_v137:invalid_parameter')

def compile_case(case,view,tables):
    validate_owner_parameters(case)
    return previous.compile_case(case,view,tables)
