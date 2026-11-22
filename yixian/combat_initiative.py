"""Client-displayed speed and a diagnostic initiative candidate.

The display helper is not proof of complete server initiative rules. No record
of who acted first enters these functions, and no result is a training label.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib,json
from pathlib import Path

from .combat_initialization import ROOT, IncompleteCombatState, _int_field
from .combat_permanent import _permanent_map
from .combat_speed_metadata import conditional_speed_components, conditional_speed_contract

EVIDENCE='data/inspection/combat-initiative-v1.json'
EVIDENCE_HASH='9771306273d071ff811f9c93d6d9dfd53ebc740d092ac1f500f8ebcb7e64c3b9'
SPEED_IDS=('10012','10045','10056','369')


class UnsupportedSpeedComponent(IncompleteCombatState):
    pass


def load_initiative_contract(root=ROOT,*,include_conditional_metadata=False):
    root=Path(root);raw=(root/EVIDENCE).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EVIDENCE_HASH:
        raise ValueError('Initiative evidence hash mismatch')
    evidence=json.loads(raw)
    contract={'schema_version':1,'scope':evidence['scope'],'game_mode_scope':3,
            'evidence_sha256':EVIDENCE_HASH,'client_dll_sha256':evidence['client_dll_sha256'],
            'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'permanent_reader_sha256':hashlib.sha256((root/'yixian/combat_permanent.py').read_bytes()).hexdigest(),
            'permanent_speed_ids':[10012,10045,10056,369],
            'unsupported_talent_family':128,'unsupported_engraving_family':42,
            'tie_policy':'unresolved_without_complete_context_and_external_outcome',
            'full_initiative_rules_recovered':False,'counterfactual_safe':False,
            'server_parity_verified':False,'training_label_allowed':False}
    if include_conditional_metadata:
        contract.update(conditional_metadata=conditional_speed_contract(root),
                        unsupported_talent_family=None,unsupported_engraving_family=None,
                        unknown_conditional_parameters='reject')
    return contract


def _ids(start,name):
    values=start.get(name)
    if not isinstance(values,list) or any(type(v) is not int or v<=0 or v>2**31-1 for v in values):
        raise IncompleteCombatState(f'Explicit positive integer {name} list required')
    return values


def derive_displayed_speed(public_data,*,game_mode=3,speed_metadata=None):
    if type(game_mode) is not int or game_mode!=3:
        raise IncompleteCombatState('Only ordinary mode 3 is scoped')
    if not isinstance(public_data,Mapping) or not isinstance(public_data.get('lastRoundData'),Mapping):
        raise IncompleteCombatState('Explicit lastRoundData required')
    start=public_data['lastRoundData']
    cultivation=_int_field(start,'exp',minimum=0)
    talents=_ids(start,'talents');engravings=_ids(start,'usedKeYinCards')
    unsupported_talents=[v for v in talents if v%10000==128]
    unsupported_engravings=[v for v in engravings if v%10000==42]
    if unsupported_talents and speed_metadata is None:
        raise UnsupportedSpeedComponent('Conditional talent family128 needs element/card metadata')
    if unsupported_engravings and speed_metadata is None:
        raise UnsupportedSpeedComponent('Engraving family42 needs speed parameters')
    permanent=_permanent_map(public_data)
    components={k:permanent.get(k,0) for k in SPEED_IDS}
    talent_components,engraving_components=([],[]) if speed_metadata is None else conditional_speed_components(start,talents,engravings,speed_metadata)
    extra=sum(components.values())+sum(c['speed'] for c in talent_components+engraving_components)
    return {'scope':'candidate_client_displayed_speed','cultivation':cultivation,
            'permanent_speed_components':components,'extra_speed':extra,'candidate_initiative_score':cultivation+extra,
            'conditional_talent_components':talent_components,'engraving_speed_components':engraving_components,
            'conditional_metadata_sha256':None if speed_metadata is None else speed_metadata.metadata_sha256,
            'used_current_or_future_values':False,'regenerated_reward_values':False,
            'resonance_context':'not_evaluated; absence_is_not_assumed',
            'full_initiative_rules_recovered':False,'server_parity_verified':False,'counterfactual_safe':False,
            'training_label_allowed':False}


def compare_initiative_candidates(public_players,*,game_mode=3,speed_metadata=None):
    if not isinstance(public_players,(list,tuple)) or len(public_players)!=2:
        raise IncompleteCombatState('Exactly two explicit player snapshots required')
    speeds=[derive_displayed_speed(p,game_mode=game_mode,speed_metadata=speed_metadata) for p in public_players]
    left,right=[s['candidate_initiative_score'] for s in speeds]
    tie=left==right
    return {'scope':'diagnostic_strict_score_comparison','players':speeds,
            'candidate_first_index':None if tie else (0 if left>right else 1),
            'strict_score_order_available':not tie,
            'reason':'equal_score_requires_unresolved_context_or_external_outcome' if tie else 'higher_candidate_cultivation_plus_displayed_speed',
            'actual_initiative_resolved':False,'observed_first_used_as_input':False,
            'full_initiative_rules_recovered':False,'counterfactual_safe':False,'server_parity_verified':False,
            'training_label_allowed':False}
