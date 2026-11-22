"""Source-bound positive Shi Li Cao stock at the plant opening boundary.

The frozen runtime already implements this plant in its correct plant order.
Only the known input projection is extended; acquisition, persistence and
unknown source metadata remain outside this single-battle diagnostic.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json

from . import website_battles_v144 as previous
from .website_battles_v139 import _before

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/website-shilicao-opening-v147.json'
PROOF_SHA = '32310f4d4022247824a11a780d399df0fa6d4e28398f02e19cd7dcf5f5cf9d60'
KEY = '10018'
FIELD = 'lose_power_grass_stacks'
UnresolvedBattle = previous.UnresolvedBattle
ORIGIN = previous.ORIGIN
compiler = previous.compiler


def require(ok, reason):
    if not ok:
        raise UnresolvedBattle('website_plant_v147:' + reason)


def extension_contract():
    require(hashlib.sha256(PROOF.read_bytes()).hexdigest() == PROOF_SHA,
            'evidence_changed')
    facts = json.loads(PROOF.read_text(encoding='utf-8'))
    for path, digest in facts['source_sha256'].items():
        require(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest,
                'evidence_source_changed:' + path)
    return facts


def validate_source(case):
    row, context = case['row'], case['combat_context']
    seats = [i for i, p in enumerate(row['players'])
             if KEY in p['candidate_start'].get('permanentBuffTempDatas', {})]
    if not seats:
        return []
    extension_contract()
    require(len(row['players']) == len(context['players']) == 2,
            'two_players_required')
    require(all(p.get('is_mirror') is False for p in context['players']),
            'mirror_not_admitted')
    src = row['source']
    require(context.get('source_raw_sha256') == src['raw_sha256'],
            'context_source_mismatch')
    path = Path(src['path'])
    require(hashlib.sha256(path.read_bytes()).hexdigest() == src['raw_sha256'],
            'source_file_changed')
    rid, owner, before, battle = _before(str(path), src['raw_sha256'], src['step'])
    require(row['id'] == rid + '/round' + str(row['round'])
            and before['round'] == battle['round'] == row['round'],
            'source_round_mismatch')
    matches = [m for m in battle['matchups']
               if m.get('authoritative') is True and owner in m.get('players', {})]
    require(len(matches) == 1 and len(matches[0]['players']) == 2,
            'unique_authoritative_pair_required')
    pair = matches[0]['players']
    opponent = pair[owner].get('opponentUid')
    require(opponent != owner and opponent in pair
            and pair[opponent].get('opponentUid') == owner,
            'reciprocal_pair_required')
    receipts = []
    for seat in seats:
        p = row['players'][seat]
        start = p['candidate_start']
        amount = start['permanentBuffTempDatas'][KEY]
        require(type(amount) is int and 1 <= amount <= 1_000_000,
                'explicit_positive_stock_required')
        actual = pair[(owner, opponent)[seat]]
        require(p['character_id'] == actual.get('characterId')
                and start['board'] == actual.get('deck'), 'source_player_mismatch')
        buffs = actual.get('battleBuffs')
        require(isinstance(buffs, list)
                and all(isinstance(b, dict) and type(b.get('id')) is int for b in buffs),
                'explicit_source_buffs_required')
        require(len({b['id'] for b in buffs}) == len(buffs), 'duplicate_source_buffs')
        entries = [b for b in buffs if b['id'] == int(KEY)]
        require(len(entries) == 1 and type(entries[0].get('value')) is int
                and entries[0]['value'] == amount, 'source_stock_mismatch')
        receipts.append({'player_index': seat, 'permanent_key': KEY, 'stock': amount,
                         'source_raw_sha256': src['raw_sha256'], 'source_step': src['step'],
                         'case_id': row['id'], 'native_field': FIELD,
                         'source': 'authoritative_battle.players.battleBuffs',
                         'effect': 'opponent decrease_atk during ordered plant startup'})
    return receipts


def compile_case(case, view, tables):
    receipts = validate_source(case)
    if not receipts:
        return previous.compile_case(case, view, tables)
    projected = deepcopy(case)
    for receipt in receipts:
        seat = receipt['player_index']
        del projected['row']['players'][seat]['candidate_start']['permanentBuffTempDatas'][KEY]
    result = previous.compile_case(projected, view, tables)
    for receipt in receipts:
        player = result['battle']['players'][receipt['player_index']]
        require(FIELD not in player, 'duplicate_native_stock')
        player[FIELD] = receipt['stock']
    result['website_plant_opening_v147'] = {
        'evidence_sha256': PROOF_SHA, 'source_checks': receipts,
        'original_source_unchanged': True, 'acquisition_reapplied': False,
        'direct_debuff_assignment': False, 'cross_round_persistence_implemented': False,
        'training_label_allowed': False}
    return result
