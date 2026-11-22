"""Preserve source-bound signed cultivation at website battle start.

Preparation can leave cultivation below zero. The client copies that signed
value into battle UI state; ModifyTempExp's later clamp is a different boundary.
No missing value or preparation reward is reconstructed by this adapter.
"""
from pathlib import Path
import hashlib

from . import website_battles_v143 as previous
from .website_battles_v132 import nullable_hand_integer
from .website_battles_v139 import _before
from .combat_compiler_view_v81 import compiler_modules

UnresolvedBattle = previous.UnresolvedBattle
ORIGIN = previous.ORIGIN


def require(ok, reason):
    if not ok:
        raise UnresolvedBattle('website_cultivation_v144:' + reason)


def signed_start_integer(source, field, minimum=0):
    value = source.get(field)
    if field != 'exp' or type(value) is not int or value >= 0:
        return nullable_hand_integer(source, field, minimum)
    require(value >= -1_000_000,
            'explicit_signed_exp_required')
    return value


def validate_negative_starts(case):
    row, context = case['row'], case['combat_context']
    seats = [i for i, p in enumerate(row['players'])
             if type(p['candidate_start'].get('exp')) is int
             and p['candidate_start']['exp'] < 0]
    if not seats:
        return []
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
        uid = (owner, opponent)[seat]
        actual = pair[uid]
        public = before.get('players', {}).get(uid, {})
        player = row['players'][seat]
        start = player['candidate_start']
        value = signed_start_integer(start, 'exp')
        require(context['players'][seat].get('is_mirror') is False,
                'mirror_not_admitted')
        require(player['character_id'] == actual.get('characterId')
                and start['board'] == actual.get('deck'), 'source_player_mismatch')
        require(type(actual.get('cultivation')) is int
                and actual['cultivation'] == value, 'authoritative_value_mismatch')
        require(type(public.get('cultivation')) is int
                and public['cultivation'] == value, 'prebattle_value_mismatch')
        receipts.append({'player_index': seat, 'cultivation': value,
                         'source_raw_sha256': src['raw_sha256'],
                         'source_step': src['step'], 'case_id': row['id'],
                         'authoritative_and_prebattle_values_agree': True,
                         'preparation_reward_reapplied': False})
    return receipts


def compiler():
    view = previous.compiler()
    compiler_modules(view)['yixian.full_battle']._integer = signed_start_integer
    return view


def compile_case(case, view, tables):
    receipts = validate_negative_starts(case)
    result = previous.compile_case(case, view, tables)
    for receipt in receipts:
        seat = receipt['player_index']
        require(result['battle']['players'][seat]['cultivation']
                == receipt['cultivation'], 'compiled_value_changed')
    if receipts:
        result['website_signed_cultivation_v144'] = {
            'source_checks': receipts, 'start_clamped': False,
            'training_label_allowed': False}
    return result
