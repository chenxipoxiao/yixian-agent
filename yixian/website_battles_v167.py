"""Hand-bound phantom card extension; all older adapters remain unchanged."""
from pathlib import Path
from copy import deepcopy
import hashlib,json
from . import website_battles_v166 as previous
from .website_battles_v139 import digest

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-phantom-hand-readers-v167.json'
PROOF_SHA='85cb744f5e9d6257228bced4378314c16bdf4bfe7c74d3f6622beec3672e8d1b'
UnresolvedBattle=previous.UnresolvedBattle

def require(ok,why):
    if not ok:raise UnresolvedBattle('phantom_hand_v167:'+why)

def extension_contract():
    raw=PROOF.read_bytes();require(hashlib.sha256(raw).hexdigest()==PROOF_SHA,'evidence_changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        require(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,'source_changed:'+p)
    return facts

def compiler():
    extension_contract()
    return previous.compiler()

def compile_case(case,view,tables):
    result=previous.compile_case(case,view,tables)
    need=[i for i,p in enumerate(result['battle']['players']) if any(c.startswith('71405') for c in p['cards'])]
    if not need:return result
    b=extension_contract()['bindings'].get(case['row']['id'])
    require(b is not None and need==[b['seat']],'explicit_bound_hand_required')
    require(digest(case)==b['original_case_sha256'],'case_changed')
    binding,private=previous.validate_binding(case)
    require(binding['binding']==b['source_binding'] and private['hand']==b['hand'],'private_source_changed')
    require(digest(result['battle'])==b['old_battle_sha256'],'compiled_battle_changed')
    result['battle']['phantom_hand_v167']={'case_id':case['row']['id'],'evidence_sha256':PROOF_SHA,
                                        'hand':deepcopy(private['hand']),'seat':b['seat']}
    result['phantom_hand_context_v167']={'evidence_sha256':PROOF_SHA,'source_binding':deepcopy(b['source_binding']),
        'selection_inferred_from_unique_eligible_hand_family':True,'original_parameter_stream_observed':False,
        'policy_observation_allowed':False,'counterfactual_reuse_allowed':False,'training_label_allowed':False}
    return result
