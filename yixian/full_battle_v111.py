"""Preserve the audited preparation-only10025 stock at original combat entry."""
from copy import deepcopy
from pathlib import Path
import hashlib,json
from . import full_battle_v110 as previous
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-daoyun-permanent-v111.json'
PROOF_SHA='8d782b804637e60b773bbee6c4716aff5904cdbf33d5288ee1a27adfc3694019'
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('daoyun_v111:evidence_changed')
    facts=json.loads(raw)
    for name,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('daoyun_v111:source_changed:'+name)
    return facts

def owns_content(row):
    return any(isinstance(p['candidate_start'].get('permanentBuffTempDatas'),dict) and
               '10025' in p['candidate_start']['permanentBuffTempDatas'] for p in row['players'])

def compile_start(row,**kwargs):
    extension_contract()
    if not owns_content(row):return previous.compile_start(row,**kwargs)
    return compile_content_start(row,**kwargs)

def compile_content_start(row,**kwargs):
    values=[]
    for p in row['players']:
        buffs=p['candidate_start'].get('permanentBuffTempDatas')
        if not isinstance(buffs,dict):raise UnresolvedBattle('daoyun_v111:explicit_permanent_map_required')
        present='10025' in buffs;value=buffs.get('10025')
        if present and (type(value) is not int or not -(2**31)<=value<2**31):
            raise UnresolvedBattle('daoyun_v111:invalid_signed_value')
        values.append({'present':present,'value':value})
    if isinstance(kwargs.get('combat_context'),dict) and 'cloud_sword_record' in kwargs['combat_context']:
        raise UnresolvedBattle('daoyun_v111:cloud_leaf_combination_pending')
    view=isolated_compiler(previous)
    leaf=compiler_modules(view)['yixian.full_battle']
    leaf.PERMANENT_FIELDS=leaf.PERMANENT_FIELDS|{'10025'}
    result=view.compile_start(row,**kwargs)
    result['daoyun_permanent_context_v111']={'evidence_sha256':PROOF_SHA,'permanent10025':deepcopy(values),
        'original_state_preserved':True,'source_row_rewritten':False,'acquisition_reapplied':False,
        'combat_buff_created':False,'cross_round_rules_implemented':False,'training_label_allowed':False}
    return result

def simulate_batch(battles,*,timeout=90):
    extension_contract()
    result=previous.simulate_batch(battles,timeout=timeout)
    result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v111',
                                'evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result
