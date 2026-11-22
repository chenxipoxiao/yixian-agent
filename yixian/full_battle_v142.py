"""Three website-blocked card families, all three upgrade forms, over frozen v136."""
import hashlib
import json
from pathlib import Path
from . import full_battle_v136 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler, compiler_modules

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT/'data/inspection/current-website-cards-v142.json'
PROOF_SHA = '6dcacc45713bc9a24290f0972eb0490833b16094bb297275f7a48c91adf08294'
BRIDGE = ROOT/'tools/full_battle_bridge_web_v142.mjs'
UnresolvedBattle = previous.UnresolvedBattle
derive_start_initiative = previous.derive_start_initiative


def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('website_cards_v142:evidence_changed')
    facts = json.loads(raw)
    for name, expected in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise UnresolvedBattle('website_cards_v142:source_changed:' + name)
    return facts


def catalogue():
    facts = extension_contract()
    cards, mapping, talents, season = previous.catalogue()
    for c in facts['cards']:
        if c['raw_id'] in mapping or c['runtime_id'] in mapping.values():
            raise UnresolvedBattle('website_cards_v142:alias_collision')
        if cards.get(c['raw_id']) != c['config']:
            raise UnresolvedBattle('website_cards_v142:configuration_mismatch')
        mapping[c['raw_id']] = c['runtime_id']
    return cards, mapping, talents, season


def compile_start(row, **kwargs):
    extension_contract()
    if 'tables' not in kwargs:
        kwargs['tables'] = catalogue()
    return previous.compile_start(row, **kwargs)


def simulate_batch(battles, *, timeout=90):
    extension_contract()
    for module in compiler_modules(previous).values():
        contract = vars(module).get('extension_contract')
        if contract is not None:
            contract()
    result = isolated_compiler(core, runtime_bridge=BRIDGE).simulate_batch(battles, timeout=timeout)
    result['adapter_contract'] = {**result['adapter_contract'],
        'schema':'complete-single-battle-diagnostic-v142',
        'website_cards_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result
