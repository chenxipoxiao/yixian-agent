"""Preserve audited legacy skip receipts before later catalogue readers.

Only 70 exact frozen original cases are projected through the unchanged v137r2
normalizer. No receipt is synthesized and no unmatched private state is filled.
The v171 stance entry and all historical source files remain unchanged.
"""
from pathlib import Path
from functools import lru_cache
import hashlib,json
from . import website_battles_v171 as previous
from .website_battles_v137r2 import normalize_choice_ownership
from .website_battles_v139 import digest

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/website-legacy-skip-v171r2.json'
PROOF_SHA='98fdc5c3ad55b7dc38807980af62f92fa9bceba56606b836290e3dc15f8bbd10'
FIELD='website_skip_ownership_v137r2'
UnresolvedBattle=previous.UnresolvedBattle

def require(ok,reason):
    if not ok:raise UnresolvedBattle('website_legacy_skip_v171r2:'+reason)

@lru_cache(maxsize=1)
def _facts(raw):
    require(hashlib.sha256(raw).hexdigest()==PROOF_SHA,'proof_changed')
    facts=json.loads(raw)
    require(facts['schema']=='frozen-legacy-skip-receipts-v171r2' and len(facts['bindings'])==70,'manifest_changed')
    for p,h in facts['source_sha256'].items():
        require(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,'source_changed:'+p)
    return facts

def extension_contract():return _facts(PROOF.read_bytes())

def compiler():
    extension_contract()
    return previous.compiler()

def compile_case(case,view,tables):
    binding=extension_contract()['bindings'].get(case['row']['id'])
    if binding is None:return previous.compile_case(case,view,tables)
    require(digest(case)==binding['case_sha256'],'original_case_changed')
    src=case['row']['source']
    require(src==binding['source'],'source_binding_changed')
    require(hashlib.sha256(Path(src['path']).read_bytes()).hexdigest()==src['raw_sha256'],'source_file_changed')
    receipt=case['combat_context']['players'][0].get(FIELD)
    require(isinstance(receipt,dict) and digest(receipt)==binding['receipt_sha256'],'original_receipt_changed')
    # Keep the historical compiled object byte-for-byte: this preflight restores
    # the original validator ordering, not a new combat effect or audit field.
    return previous.compile_case(normalize_choice_ownership(case),view,tables)
