"""Versioned single-battle projection for the historical second-player count.

The original snapshot is retained. This does not implement match-level counter
updates or use a historical count to decide the current first player.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from . import full_battle_v2 as v2

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/permanent-counter10006-v1.json'
PROOF_SHA='d7c42e8c15f61aadc4f16b9a66b6b57d4d13f7bc926b3b9064f23b1a0e8bcdf1'
UnresolvedBattle=v2.UnresolvedBattle
derive_start_initiative=v2.derive_start_initiative
catalogue=v2.catalogue


def counter_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:
        raise UnresolvedBattle('Permanent counter evidence changed')
    return json.loads(raw)


def compile_start(row,**kwargs):
    evidence=counter_contract()
    if (row.get('source_rules_version'),kwargs.get('game_mode'),kwargs.get('season_mec'))!=(
            evidence['rules_version'],evidence['game_mode'],evidence['season_mec']):
        raise UnresolvedBattle('Counter10006 projection requires the pinned ranked version/mode/season')
    projected=deepcopy(row);retained=[]
    if not isinstance(projected.get('players'),list) or len(projected['players'])!=2:
        raise UnresolvedBattle('Two start snapshots required')
    for index,player in enumerate(projected['players']):
        permanent=player.get('candidate_start',{}).get('permanentBuffTempDatas')
        if not isinstance(permanent,dict):raise UnresolvedBattle('Explicit permanent dictionary required')
        present='10006' in permanent
        value=permanent.get('10006')
        if present:
            if type(value) is not int or not 0<=value<=1_000_000:
                raise UnresolvedBattle('Explicit nonnegative bounded counter10006 required')
            # This exact key has a reviewed current-client no-transfer rule.
            # Preserve its presence/value below. Every other key still reaches
            # the original compiler's unknown-state rejection.
            del permanent['10006']
        retained.append({'snapshot_slot':('p1','p2')[index],'present':present,'value':value})
    result=v2.compile_start(projected,**kwargs)
    result['historical_permanent_counters']={
        '10006':retained,'evidence_sha256':PROOF_SHA,
        'single_battle_projection':'not_copied_into_live_buffs_in_inspected_client',
        'original_input_mutated':False,'used_to_choose_initiative':False,
        'persistent_update_rule_implemented':False,'training_label_allowed':False}
    return result


def simulate_batch(battles,*,timeout=90):
    counter_contract()
    result=v2.simulate_batch(battles,timeout=timeout)
    result['base_adapter_contract']=result['adapter_contract']
    result['adapter_contract']={
        **result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v3',
        'permanent_counter10006_evidence_sha256':PROOF_SHA,
        'input_compiler_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'persistent_counter_updates_implemented':False}
    return result
