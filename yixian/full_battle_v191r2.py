"""Observed preparation7114 boundary for three source-bound native battles.

No active use, cost, grant, count transition or future state is synthesized.
The canonical client table and all earlier compilers remain unchanged.
"""
from copy import deepcopy
from pathlib import Path
import hashlib,json
from . import full_battle_v191 as previous
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-quicksand-preparation-v191r2.json'
PROOF_SHA='c8b07382d336e602047b5fdbab50d285a7eb45a08d061dbe973ac572b921a91e'
UnresolvedBattle=previous.UnresolvedBattle
derive_start_initiative=previous.derive_start_initiative
catalogue=previous.catalogue

def binding(row,context):
    start={k:v for k,v in row.items() if k!='outcome'}
    return hashlib.sha256(json.dumps({'start':start,'context':context},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:
        raise UnresolvedBattle('preparation_v191r2:evidence_changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:
            raise UnresolvedBattle('preparation_v191r2:source_changed:'+p)
    return facts

def compile_start(row,**kwargs):
    facts=extension_contract()
    owners=[i for i,p in enumerate(row['players']) if 7114 in p['candidate_start']['xian_mo_strategies']]
    if not owners:
        return previous.compile_start(row,**kwargs)
    receipt=facts['admissions'].get(row.get('id'))
    if receipt is None or binding(row,kwargs.get('combat_context'))!=receipt['start_context_sha256']:
        raise UnresolvedBattle('preparation_v191r2:original_start_binding_required')
    tables=kwargs.get('tables') or catalogue()
    if tables[3].get(7114)!=facts['config']:
        raise UnresolvedBattle('preparation_v191r2:canonical_config_changed')
    # The client catalogue's broad isBattleEffect flag does not identify timing.
    # Only this private legacy phase projection classifies7114 as preparation.
    season=deepcopy(tables[3]);season[7114]['isBattleEffect']=False
    projected={**kwargs,'tables':(*tables[:3],season)}
    result=previous.compile_start(row,**projected)
    for i in owners:
        assert result['battle']['players'][i]['cultivation']==row['players'][i]['candidate_start']['exp']
        assert 7114 in result['effect_players'][i]['season_choices']
        assert 7114 in result['declared_components'][i]['preparation_season_not_reapplied']
    result['preparation7114_v191r2']={'evidence_sha256':PROOF_SHA,'players':owners,
        'original_start_binding':receipt['start_context_sha256'],
        'used_or_unused_not_inferred':True,'costs_or_grants_replayed':False,
        'preparation_actions_implemented':False,'counterfactual_reuse_allowed':False,
        'match_continuation_allowed':False,'training_label_allowed':False}
    return result
