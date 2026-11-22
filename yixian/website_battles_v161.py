"""Exact audited private-owner prefixes for seasonal skip24/25 choices.

The source state target is retained separately from the recording's private
owner. All unregistered source prefixes continue through the frozen adapter.
"""
from copy import deepcopy
from pathlib import Path
import hashlib,json

from . import website_battles_v160r2 as previous
from .website_battles_v151 import strategy_ids
from .website_battles_v137r2 import normalize_choice_ownership
from .website_battles_v139 import _before,digest

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/website-private-owner-v161.json'
PROOF_SHA='c3f50a7e2994dbd0c45bc090643d78aa3d74066eb5448439d29be77493bfd096'
ORIGIN=previous.ORIGIN
UnresolvedBattle=previous.UnresolvedBattle
CONFLICT='private_vs_battle_strategy_ownership'


def require(ok,reason):
    if not ok:raise UnresolvedBattle('website_private_owner_v161:'+reason)


def _facts():
    data=PROOF.read_bytes()
    require(hashlib.sha256(data).hexdigest()==PROOF_SHA,'binding_evidence_changed')
    return json.loads(data)


def extension_contract():
    facts=_facts()
    require(facts.get('schema')=='website-exact-private-owner-prefixes-v161'
            and len(facts.get('bindings',{}))==30,'binding_contract_changed')
    for path,expected in facts['source_sha256'].items():
        require(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,'evidence_source_changed:'+path)
    return facts


def compiler():
    extension_contract()
    return previous.compiler()


def bind_private_owner(case):
    facts=_facts()
    binding=facts['bindings'].get(case['row']['id'])
    if binding is None:return case,None
    require(case['input_conflicts']==[CONFLICT],'only_audited_skip_ownership_conflict_supported')
    extension_contract()
    row,context=case['row'],case['combat_context'];src=row['source'];path=Path(src['path'])
    require(hashlib.sha256(path.read_bytes()).hexdigest()==src['raw_sha256'],'source_file_changed')
    rid,owner,before,battle=_before(str(path),src['raw_sha256'],src['step'])
    private=before.get('privatePlayer')
    require(isinstance(private,dict) and private.get('uid')==owner,'source_private_owner_required')
    require(len(row['players'])==len(context['players'])==2,'two_players_required')
    cp=context['players'][0]
    require(case.get('preparation_owner_verified') is True and cp.get('website_hand_unknown') is False,
            'verified_private_owner_required')
    require(context.get('game_mode')==3 and context.get('season_mec')==10
            and before.get('gameMode')==3 and before.get('seasonMechanic')==10,'mode_outside_scope')
    require(all(p.get('is_mirror') is False for p in context['players']),'mirror_not_admitted')
    require(context.get('source_raw_sha256')==src['raw_sha256'],'context_source_mismatch')
    require(row['id']==rid+'/round'+str(row['round']) and row['game_id']==rid
            and before['round']==battle['round']==row['round'],'source_round_mismatch')
    sid=binding['skip_id']
    require(type(sid) is int and sid in (24,25),'unknown_skip_id')
    raw=json.loads(path.read_text(encoding='utf8'))
    metadata=raw.get('catalog',{}).get('xianMoStrategies',{}).get(str(sid))
    require(isinstance(metadata,dict) and metadata.get('assetKind')=='xianMoStrategy'
            and metadata.get('id')==sid and metadata.get('isSkip') is True
            and metadata.get('isSuanniSkip') is True,'explicit_skip_catalogue_required')
    actual={'source_raw_sha256':src['raw_sha256'],'source_step':src['step'],'round':before['round'],
        'source_record_owner_sha256':digest(owner),'source_state_target_sha256':digest(before.get('targetUid')),
        'private_state_sha256':digest(private),'prebattle_state_sha256':digest(before),
        'skip_id':sid,'catalogue_sha256':digest(metadata)}
    require(actual==binding,'audited_prefix_binding_mismatch')
    require(isinstance(before.get('targetUid'),str) and before['targetUid']!=owner,
            'expected_distinct_state_target')
    require(digest(metadata) in facts['catalogue_metadata'].get(str(sid),{}),'unregistered_catalogue')
    matches=[m for m in battle['matchups'] if m.get('authoritative') is True and owner in m.get('players',{})]
    require(len(matches)==1 and len(matches[0]['players'])==2,'authoritative_pair_required')
    pair=matches[0]['players'];other=pair[owner].get('opponentUid')
    require(other!=owner and other in pair and pair[other].get('opponentUid')==owner,'reciprocal_pair_required')
    require(all(p.get('innerDemon') is not True and type(p.get('lifeBefore')) is int and p['lifeBefore']>0
                for p in pair.values()),'source_mirror_or_zero_life_not_admitted')
    start=row['players'][0]['candidate_start']
    require(row['players'][0]['character_id']==pair[owner].get('characterId')
            and start['board']==private.get('deck')==pair[owner].get('deck'),'source_player_mismatch')
    require(start['level']==pair[owner].get('phase') and start['exp']==pair[owner].get('cultivation'),
            'source_start_mismatch')
    require(start['talents']==strategy_ids(pair[owner].get('talents')),'ordinary_fates_changed')
    require(type(private.get('hand')) is list and type(cp.get('hand_count')) is int
            and cp['hand_count']==len(private['hand']),'source_hand_mismatch')
    entries=private.get('selectedXianMoStrategies');private_ids=strategy_ids(entries)
    battle_ids=strategy_ids(pair[owner].get('xianMoStrategies'))
    require(start['xian_mo_strategies']==battle_ids,'battle_ownership_changed')
    require(sorted(set(private_ids)&{24,25})==[sid] and sid not in battle_ids
            and set(private_ids)-{sid}==set(battle_ids),'only_observed_skip_difference_supported')
    chosen=next(e for e in entries if e['id']==sid)
    require('runtime' in chosen and chosen['runtime'] is None and chosen.get('locked') is False,'skip_runtime_unknown')
    history=chosen.get('choiceHistory',{});offers=history.get('offers')
    require(history.get('complete') is True and history.get('selected')==sid
            and type(history.get('roundOrPhase')) is int and 0<history['roundOrPhase']<=row['round']
            and isinstance(offers,list) and bool(offers)
            and all(isinstance(group,list) and all(type(x) is int for x in group) for group in offers)
            and any(sid in group for group in offers),'observed_skip_selection_required')
    receipt={'origin':ORIGIN,'source_raw_sha256':src['raw_sha256'],'source_step':src['step'],
        'case_id':row['id'],'player_index':0,'environment_only':True,'battle_strategy_ids':battle_ids,
        'private_selected_ids':private_ids,'observed_suanni_skip_ids':[sid],'metadata_verified_skip_ids':[sid]}
    require(cp.get('website_skip_ownership_v137r2') is None or cp['website_skip_ownership_v137r2']==receipt,
            'prefilled_receipt_mismatch')
    projected=deepcopy(case);projected['combat_context']['players'][0]['website_skip_ownership_v137r2']=receipt
    projected=normalize_choice_ownership(projected)
    return projected,{'source_binding':binding,'state_target_rewritten':False,'opponent_private_state_inferred':False,
        'ordinary_fates_unchanged':True,'battle_strategy_ids_unchanged':True,
        'obtained_fate_or_reward_replayed':False,'training_label_allowed':False}


def compile_case(case,view,tables):
    projected,receipt=bind_private_owner(case)
    result=previous.compile_case(projected,view,tables)
    if receipt is not None:result['website_private_owner_v161']=receipt
    return result
