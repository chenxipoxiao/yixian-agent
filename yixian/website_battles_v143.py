"""Bind Five Elements Flag to the recorder's exact prebattle private hand.

The frozen card bodies and battle runtime are unchanged. No opponent hand,
postbattle field, missing switch or absent counter is inferred by this adapter.
"""
from pathlib import Path
import hashlib
from . import website_battles_v139 as previous
from .website_battles_v132 import replace_function
from .combat_compiler_view_v81 import compiler_modules

ORIGIN=previous.ORIGIN
UnresolvedBattle=previous.UnresolvedBattle
FLAGS={7000111,7010111,7020111}

def require(ok,reason):
    if not ok:raise UnresolvedBattle('website_flag_v143:'+reason)

def validate_owner_hand(row,context,seat,hand):
    require(seat==0,'opponent_private_hand_not_observed')
    require(isinstance(hand,dict) and hand.get('origin')==ORIGIN,'website_origin_required')
    cp=context['players'][seat];src=row['source'];start=row['players'][seat]['candidate_start']
    require(cp.get('website_hand_unknown') is False,'private_owner_required')
    expected={'source_raw_sha256':src['raw_sha256'],'source_step':src['step'],'case_id':row['id'],
        'record_id':row['id'],'round':row['round'],'player_index':seat,'environment_only':True}
    require(all(hand.get(k)==v for k,v in expected.items()),'source_binding_mismatch')
    require(context.get('source_raw_sha256')==src['raw_sha256'],'context_source_mismatch')
    path=Path(src['path'])
    require(hashlib.sha256(path.read_bytes()).hexdigest()==src['raw_sha256'],'source_file_changed')
    rid,uid,before,battle=previous._before(str(path),src['raw_sha256'],src['step'])
    require(row['id']==rid+'/round'+str(row['round']) and before['round']==battle['round']==row['round'],'source_round_mismatch')
    authoritative=[m for m in battle['matchups'] if m.get('authoritative') is True and uid in m.get('players',{})]
    require(len(authoritative)==1,'unique_owner_authority_required')
    private=before.get('privatePlayer')
    require(isinstance(private,dict) and private.get('uid')==uid,'source_private_owner_required')
    require(private.get('deck')==start['board']==hand.get('board')==authoritative[0]['players'][uid]['deck'],'private_board_mismatch')
    require(bool(FLAGS.intersection(start['board'])),'flag_not_in_owner_board')
    raw=private.get('hand')
    require(type(raw)is list and raw==hand.get('raw_cards'),'private_hand_order_mismatch')
    require(cp.get('hand_count')==len(raw),'private_hand_count_mismatch')
    require(hand.get('private_state_sha256')==previous.digest(private),'private_state_hash_mismatch')
    return True

def supported_origin(row,context,seat,hand):
    if hand.get('origin')=='publicData.lastRoundData.handCards':return True
    if hand.get('origin')!=ORIGIN:return False
    return validate_owner_hand(row,context,seat,hand)

def source_label(context):
    return ORIGIN if any(p.get('element_flag_hand',{}).get('origin')==ORIGIN for p in context['players']) else 'publicData.lastRoundData.handCards'

def compiler():
    view=previous.compiler();target=compiler_modules(view)['yixian.full_battle_v62r2']
    target._website_flag_origin_v143=supported_origin
    target._website_flag_source_v143=source_label
    replace_function(target,'compile_start',[
        ("h.get('origin')!='publicData.lastRoundData.handCards'","not _website_flag_origin_v143(row,ctx,i,h)"),
        ("'source':'publicData.lastRoundData.handCards'","'source':_website_flag_source_v143(ctx)")])
    return view

def compile_case(case,view,tables):
    # This entry only accepts the website's owner source. The original native
    # archive origin remains supported by the separate, frozen compiler API.
    for seat,cp in enumerate(case['combat_context']['players']):
        if cp.get('element_flag_hand') is not None:
            require(case.get('preparation_owner_verified') is True,'private_owner_unverified')
            validate_owner_hand(case['row'],case['combat_context'],seat,cp['element_flag_hand'])
    return previous.compile_case(case,view,tables)
