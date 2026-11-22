"""Exact prebattle owner13003 slot receipts; all old interfaces stay frozen."""
from pathlib import Path
from copy import deepcopy
from functools import lru_cache
from types import FunctionType
import hashlib,json
from . import website_battles_v171r3 as previous
from .website_battles_v139 import _before,digest
from .combat_compiler_view_v81 import compiler_modules
from .combat_website_engraving_v173 import compile_start as engraving_leaf

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/website-owner-engraving-v173.json'
PROOF_SHA='ad5f7a92b484f57dd11d871a9dc308a793dcef0b08a1da98fb162ddf137ce347'
FIELD='_website_owner_engraving_v173'
UnresolvedBattle=previous.UnresolvedBattle

def require(ok,reason):
    if not ok:raise UnresolvedBattle('website_engraving_v173:'+reason)

@lru_cache(maxsize=1)
def _facts(raw):
    require(hashlib.sha256(raw).hexdigest()==PROOF_SHA,'proof_changed')
    facts=json.loads(raw)
    require(facts['schema']=='website-owner13003-slot-v173' and len(facts['bindings'])==3,'manifest_changed')
    for p,h in facts['source_sha256'].items():
        require(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,'source_changed:'+p)
    return facts

def extension_contract():return _facts(PROOF.read_bytes())

def validate_source(case,binding):
    row=case['row'];ctx=case['combat_context'];src=row['source']
    require(digest(case)==binding['case_sha256'],'original_case_changed')
    require(src==binding['source'] and ctx['source_raw_sha256']==src['raw_sha256'],'source_binding_changed')
    require(hashlib.sha256(Path(src['path']).read_bytes()).hexdigest()==src['raw_sha256'],'source_file_changed')
    rid,owner,before,battle=_before(src['path'],src['raw_sha256'],src['step'])
    require(row['id']==rid+'/round'+str(row['round']) and before['round']==battle['round']==row['round'],'round_mismatch')
    require(before['gameMode']==ctx['game_mode']==3 and before['seasonMechanic']==ctx['season_mec']==10,'mode_mismatch')
    require(all(p.get('is_mirror') is False for p in ctx['players']),'mirror_not_admitted')
    require(case.get('preparation_owner_verified') is True and ctx['players'][0].get('website_hand_unknown') is False,'private_owner_required')
    matches=[x['players'] for x in battle['matchups'] if x.get('authoritative') is True and owner in x.get('players',{})]
    require(len(matches)==1 and len(matches[0])==2,'unique_authoritative_pair_required')
    pair=matches[0];opponent=pair[owner].get('opponentUid')
    require(opponent!=owner and opponent in pair and pair[opponent].get('opponentUid')==owner,'reciprocal_pair_required')
    private=before.get('privatePlayer',{})
    require(private.get('uid')==owner and digest(owner)==binding['owner_uid_sha256'],'owner_mismatch')
    require(digest(private)==binding['private_prefix_sha256'],'private_prefix_changed')
    start=row['players'][0]['candidate_start'];cp=ctx['players'][0]
    require(row['players'][0]['character_id']==pair[owner]['characterId']==binding['character_id'],'character_mismatch')
    require(private.get('deck')==pair[owner]['deck']==start['board'],'board_mismatch')
    require(type(private.get('hand')) is list and cp.get('hand_count')==len(private['hand']),'hand_count_mismatch')
    selected=private.get('selectedXianMoStrategies')
    require(isinstance(selected,list) and len({x['id'] for x in selected})==len(selected),'unique_ownership_required')
    require({x['id'] for x in selected}==set(start['xian_mo_strategies']),'ownership_mismatch')
    chosen=[x for x in selected if x['id']==13003]
    require(len(chosen)==1 and type(chosen[0].get('enchantedSlot')) is int,'explicit_slot_required')
    position=chosen[0]['enchantedSlot']
    require(1<=position<=len(start['board']) and position==binding['source_one_based_slot'],'slot_outside_board')
    require(type(cp.get('website_strategy_parameters',{}).get('13003')) is int
        and cp['website_strategy_parameters']['13003']==position-1==binding['zero_based_slot'],'slot_conversion_mismatch')
    require('season_engraving_input' not in cp and FIELD not in cp,'conflicting_existing_receipt')
    return {'proof_sha256':PROOF_SHA,'case_id':row['id'],'case_sha256':binding['case_sha256'],
        'source_raw_sha256':src['raw_sha256'],'source_step':src['step'],
        'private_prefix_sha256':binding['private_prefix_sha256'],'seat':0,
        'character_id':binding['character_id'],'strategy_id':13003,'slot':position-1,
        'origin':'website:privatePlayer:prebattle:selectedXianMoStrategies:enchantedSlot',
        'environment_only':True,'counterfactual_reuse_allowed':False}

def leaf_receipt(row,context,index,owned):
    if not isinstance(context,dict):return None
    receipt=context['players'][index].get(FIELD)
    if receipt is None:return None
    binding=extension_contract()['bindings'].get(row['id'])
    require(index==0 and owned==[13003] and binding is not None,'leaf_ownership_mismatch')
    require(receipt=={
        'proof_sha256':PROOF_SHA,'case_id':row['id'],'case_sha256':binding['case_sha256'],
        'source_raw_sha256':row['source']['raw_sha256'],'source_step':row['source']['step'],
        'private_prefix_sha256':binding['private_prefix_sha256'],'seat':0,
        'character_id':row['players'][0]['character_id'],'strategy_id':13003,'slot':binding['zero_based_slot'],
        'origin':'website:privatePlayer:prebattle:selectedXianMoStrategies:enchantedSlot',
        'environment_only':True,'counterfactual_reuse_allowed':False},'leaf_binding_mismatch')
    require(context.get('source_raw_sha256')==binding['source']['raw_sha256'],'leaf_context_source_mismatch')
    return deepcopy(receipt)

def compiler():
    extension_contract();view=previous.compiler()
    leaf=compiler_modules(view)['yixian.full_battle_v21']
    leaf._website_engraving_receipt_v173=leaf_receipt
    leaf.compile_start=FunctionType(engraving_leaf.__code__,vars(leaf),engraving_leaf.__name__,engraving_leaf.__defaults__)
    return view

def compile_case(case,view,tables):
    require(all(FIELD not in p for p in case['combat_context']['players']),'external_internal_receipt')
    binding=extension_contract()['bindings'].get(case['row']['id'])
    if binding is None:return previous.compile_case(case,view,tables)
    receipt=validate_source(case,binding)
    translated=deepcopy(case)
    translated['combat_context']['players'][0][FIELD]=receipt
    return previous.compile_case(translated,view,tables)
