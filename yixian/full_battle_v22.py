"""Restore fate106's combat star slot; reuse the frozen native battle engine."""
import hashlib
import json
from pathlib import Path
from . import full_battle_v21 as v21

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-star-fate-v22.json'
PROOF_SHA='3ec32cdcedc7c907cb309cc86c5b121d6b7ffa3a6634edc2757bd9b71618857c'
UnresolvedBattle=v21.UnresolvedBattle
catalogue=v21.catalogue
derive_start_initiative=v21.derive_start_initiative


def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:
        raise UnresolvedBattle('Star fate evidence changed')
    facts=json.loads(raw)
    for name,expected in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:
            raise UnresolvedBattle('Star fate source changed:'+name)
    return facts


def compile_start(row,**kwargs):
    extension_contract()
    result=v21.compile_start(row,**kwargs)
    for index,source in enumerate(row['players']):
        fates=source['candidate_start']['talents']
        if 106 not in fates:
            continue
        if fates.count(106)!=1:
            raise UnresolvedBattle('Duplicate star_moon_folding_fan fate106')
        player=result['battle']['players'][index]
        if 'star_moon_folding_fan_stacks' in player:
            raise UnresolvedBattle('Star fate106 already compiled by another adapter')
        # isBattleTalent=false describes neither every startup hook nor its
        # absence. OnBattleStarted explicitly dispatches106 -> AddXingWei(6,0).
        player['star_moon_folding_fan_stacks']=1
        result['declared_components'][index]['fate106_combat_start']={
            'raw_fate':106,'native_field':'star_moon_folding_fan_stacks',
            'zero_based_slot':6,'evidence_sha256':PROOF_SHA,
            'acquisition_reward_reapplied':False}
    return result


def simulate_batch(battles,*,timeout=90):
    extension_contract()
    result=v21.simulate_batch(battles,timeout=timeout)
    result['parent_adapter_contract']=result['adapter_contract']
    result['adapter_contract']={
        'schema':'complete-single-battle-diagnostic-v22',
        'evidence_sha256':PROOF_SHA,'native_star_fate_reused':True,
        'bridge_unchanged_from_v21':True,'current_content_complete':False}
    return result
