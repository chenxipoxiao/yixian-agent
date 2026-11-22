"""Source-bound206 on a non-native27023 owner, using the unchanged runtime.

Four fixed development inputs are admitted. No identity substitution, unknown
private default, acquisition reward or additional stance initialization occurs.
"""
from pathlib import Path
from types import FunctionType
from copy import deepcopy
from functools import lru_cache
import hashlib
import json

from . import website_battles_v168 as previous
from .combat_compiler_view_v81 import compiler_modules
from .combat_website_stance_v171 import compile_start as stance_leaf
from .website_battles_v139 import _before, digest

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT/'data/inspection/website-nonnative-stance-v171.json'
PROOF_SHA = '9234ed35d3ed6da790d6b424d86f0b4c3e6f62cf0b760ece9c6c704a3a739cbe'
FIELD = '_website_stance_binding_v171'
UnresolvedBattle = previous.UnresolvedBattle


def require(ok, reason):
    if not ok:
        raise UnresolvedBattle('website_stance_v171:' + reason)


@lru_cache(maxsize=1)
def _facts(raw):
    require(hashlib.sha256(raw).hexdigest() == PROOF_SHA, 'evidence_changed')
    value = json.loads(raw)
    require(value['schema'] == 'website-owned-nonnative-stance-v171'
            and len(value['bindings']) == 4, 'manifest_changed')
    for path, expected in value['source_sha256'].items():
        require(hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == expected,
                'source_changed:' + path)
    return value


def extension_contract():
    return _facts(PROOF.read_bytes())


def leaf_receipt(row, context, index):
    """The public entry validates original bytes before any ancestor projection."""
    if not isinstance(context, dict):
        return None
    receipt = context.get(FIELD)
    if not isinstance(receipt, dict):
        return None
    require(receipt.get('proof_sha256') == PROOF_SHA
            and receipt.get('case_id') == row['id']
            and receipt.get('source_raw_sha256') == row['source']['raw_sha256']
            and receipt.get('seat') == index
            and receipt.get('character_id') == row['players'][index]['character_id'],
            'leaf_binding_mismatch')
    binding = extension_contract()['bindings'].get(row['id'])
    require(binding is not None and receipt.get('case_sha256') == binding['case_sha256'],
            'leaf_case_not_bound')
    return deepcopy(receipt)


def compiler():
    extension_contract()
    view = previous.compiler()
    leaf = compiler_modules(view)['yixian.full_battle_v15']
    leaf._website_stance_receipt_v171 = leaf_receipt
    leaf.compile_start = FunctionType(stance_leaf.__code__, vars(leaf),
                                     stance_leaf.__name__, stance_leaf.__defaults__)
    return view


def validate_source(case, binding):
    row, ctx = case['row'], case['combat_context']
    require(digest(case) == binding['case_sha256'], 'original_case_changed')
    src = row['source']
    require(src == binding['source'] and ctx['source_raw_sha256'] == src['raw_sha256'],
            'source_binding_mismatch')
    require(hashlib.sha256(Path(src['path']).read_bytes()).hexdigest() == src['raw_sha256'],
            'source_file_changed')
    rid, owner, before, battle = _before(src['path'], src['raw_sha256'], src['step'])
    require(row['id'] == rid+'/round'+str(row['round'])
            and before['round'] == battle['round'] == row['round']
            and before['gameMode'] == 3 and before['seasonMechanic'] == 10,
            'source_mode_or_round_mismatch')
    matches = [m['players'] for m in battle['matchups']
               if m.get('authoritative') is True and owner in m.get('players', {})]
    require(len(matches) == 1 and len(matches[0]) == 2, 'authoritative_pair_required')
    pair = matches[0]
    opponent = pair[owner].get('opponentUid')
    require(opponent != owner and opponent in pair and pair[opponent].get('opponentUid') == owner,
            'reciprocal_pair_required')
    require(all(p.get('is_mirror') is False for p in ctx['players']), 'mirror_not_admitted')
    private = before.get('privatePlayer', {})
    require(private.get('uid') == owner and digest(owner) == binding['owner_uid_sha256']
            and digest(private) == binding['private_prefix_sha256'], 'private_owner_mismatch')
    seat = binding['seat']
    require(seat == 0, 'owner_seat_required')
    player = row['players'][seat]
    start = player['candidate_start']
    actual = pair[owner]
    require(player['character_id'] == actual.get('characterId') == binding['character_id']
            and start['board'] == actual.get('deck') == private.get('deck')
            and start['talents'] == [x['id'] for x in actual['talents']]
            and start['xian_mo_strategies'] == [x['id'] for x in actual['xianMoStrategies']],
            'start_ownership_or_board_mismatch')
    require(206 in start['talents'] and 209 not in start['talents']
            and 27023 in start['xian_mo_strategies']
            and 7111 not in start['xian_mo_strategies']
            and 335 not in start['fate_strategies'], 'unsupported_stance_source')
    selections = [x for x in private['selectedXianMoStrategies'] if x['id'] == 27023]
    require(len(selections) == 1 and digest(selections[0]) == binding['strategy_selection_sha256'],
            'private_selection_mismatch')
    return {'proof_sha256': PROOF_SHA, 'case_id': row['id'],
            'case_sha256': binding['case_sha256'], 'source_raw_sha256': src['raw_sha256'],
            'seat': seat, 'character_id': player['character_id'], 'fate_id': 206,
            'season_id': 27023, 'environment_only': True, 'training_label_allowed': False}


def compile_case(case, view, tables):
    require(FIELD not in case['combat_context'], 'external_private_marker')
    binding = extension_contract()['bindings'].get(case['row']['id'])
    if binding is None:
        return previous.compile_case(case, view, tables)
    receipt = validate_source(case, binding)
    projected = deepcopy(case)
    projected['combat_context'][FIELD] = receipt
    result = previous.compile_case(projected, view, tables)
    seat = receipt['seat']
    require(result['battle']['players'][seat].get('indomitable_will_stacks') == 1,
            'fate_not_projected')
    batch = result['battle'].get('season_batch', {}).get('players', [])
    require(len(batch) == 2 and 27023 in batch[seat]['ids'], 'stance_initializer_missing')
    require(result['effect_players'][seat]['fates'] == case['row']['players'][seat]['candidate_start']['talents'],
            'fate_audit_changed')
    result['website_stance_v171'] = {
        **receipt, 'startup_reader': 'OnBattleStarted0x6006607:0x241..0x299',
        'runtime_initializer': 'unchanged season27023 apply_p1_fates_setup callback',
        'runtime_changed': False, 'character_substituted': False,
        'acquisition_reapplied': False, 'counterfactual_reuse_allowed': False,
        'source_version_certified': False}
    return result
