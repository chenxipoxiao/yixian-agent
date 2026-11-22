"""Four exact paired skip prefixes and one fifth-realm dream card diagnostic.

The v166 original-case binding runs before skip normalization. Existing source
validators are rebound into private function namespaces; no module is patched.
The D12155 reference reader's reset timing remains explicitly uncertified.
"""
from pathlib import Path
from types import FunctionType, SimpleNamespace
import hashlib
import json

from . import website_battles_v167 as previous
from . import website_battles_v166 as paired
from . import website_battles_v161 as owner_adapter
from .website_battles_v139 import digest

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/website-paired-skip-star-v168.json'
PROOF_SHA = '0748536b2e832cd5033d267c2afd95a4e8c29e97fe43afee60695aa3f0a6c633'
UnresolvedBattle = previous.UnresolvedBattle


def require(ok, reason):
    if not ok:
        raise UnresolvedBattle('website_paired_v168:' + reason)


def extension_contract():
    raw = PROOF.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PROOF_SHA, 'evidence_changed')
    facts = json.loads(raw)
    require(facts['schema'] == 'website-paired-skip-and-exact-dream-card-v168'
            and len(facts['bindings']) == 4 and len(facts['card_cases']) == 1,
            'binding_contract_changed')
    for path, expected in facts['source_sha256'].items():
        require(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected,
                'source_changed:' + path)
    return facts


def compiler():
    facts = extension_contract()
    view = previous.compiler()
    inherited = view.catalogue

    def catalogue():
        cards, mapping, talents, season = inherited()
        card = facts['card']
        require(cards[card['raw_id']] == card['config'], 'card_config_changed')
        require(card['raw_id'] not in mapping and card['runtime_id'] not in mapping.values(),
                'alias_collision')
        return cards, {**mapping, card['raw_id']: card['runtime_id']}, talents, season

    view.catalogue = catalogue
    return view


def _bound_skip(case, view, tables):
    # The original v166 source and whole-case validation has already run.
    # Reuse every v161 owner/history/source/mirror guard with this new manifest.
    namespace = {**vars(owner_adapter), '_facts': extension_contract,
                 'extension_contract': extension_contract}
    bind = FunctionType(owner_adapter.bind_private_owner.__code__, namespace)
    projected, receipt = bind(case)
    require(receipt is not None, 'skip_receipt_required')
    result = paired.previous.compile_case(projected, view, tables)
    result['website_paired_skip_v168'] = {
        'proof_sha256': PROOF_SHA, **receipt,
        'source_version_certified': False, 'counterfactual_reuse_allowed': False}
    return result


def compile_case(case, view, tables):
    facts = extension_contract()
    cid = case['row']['id']
    uses_card = any(facts['card']['raw_id'] in p['candidate_start']['board']
                    for p in case['row']['players'])
    if uses_card:
        require(facts['card_cases'].get(cid) == digest(case), 'exact_card_source_required')
    if cid in facts['bindings']:
        require(digest(case) == facts['original_case_sha256'][cid], 'original_case_changed')
        namespace = {**vars(paired), 'previous': SimpleNamespace(compile_case=_bound_skip)}
        bound_compile = FunctionType(paired.compile_case.__code__, namespace)
        result = bound_compile(case, view, tables)
    else:
        result = previous.compile_case(case, view, tables)
    if uses_card:
        result['dream_dotted_source_v168'] = {
            'proof_sha256': PROOF_SHA, 'raw_card_id': 4040084, 'runtime_id': 'D12155',
            'exact_realm': 5, 'reference_reset_timing_certified': False,
            'source_version_certified': False, 'training_label_allowed': False,
            'counterfactual_reuse_allowed': False}
    return result
