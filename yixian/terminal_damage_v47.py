"""Civet gain-before-survival preview, with no cap at100 (user confirmed).

Pure settlement only. Reuses the frozen battle and gross-damage formula;
does not commit match resources, consume fate counters or pay pending rewards.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .terminal_damage import calculate_terminal_damage as base_damage
from .terminal_damage_v38 import calculate_terminal_damage as previous

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT/'data/inspection/user-civet-settlement-2026-11-13.json'
PROOF_SHA = '390a43d7cb32ba64a8c77a3fb039dc9042000f025c780ef9a5eaccf3a08eba70'
CIVET_PROOF_SHA = '75a8f175659da11363f8d1d01ecb77fe1057c9e499a7ff1b547ded8acb34bf83'
CIVET_GAINS = {433: 3, 10433: 6, 20433: 9}


def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise ValueError('Civet settlement confirmation changed')
    return json.loads(raw)


def _gains(compiled, receipt):
    gains = receipt.get('requested_destiny_gains')
    if (not isinstance(gains, list) or len(gains) != 2
            or any(type(x) is not int or x < 0 for x in gains)):
        raise ValueError('Explicit civet gain requests required')
    events = receipt.get('events')
    if receipt.get('evidence_sha256') != CIVET_PROOF_SHA or not isinstance(events, list):
        raise ValueError('Verified civet event receipt required')
    summed = [0, 0]
    for event in events:
        seat, raw = event.get('player_index'), event.get('raw_card')
        if type(seat) is not int or seat not in (0, 1) or type(raw) is not int or raw not in CIVET_GAINS:
            raise ValueError('Invalid civet event identity')
        mirror = event.get('is_mirror')
        expected = 0 if mirror is True else CIVET_GAINS[raw]
        if (type(mirror) is not bool or compiled['effect_players'][seat].get('is_mirror') is not mirror
                or type(event.get('requested_destiny_gain')) is not int
                or event['requested_destiny_gain'] != expected
                or event.get('phase') != 'card_body_after_hp_recovery'
                or event.get('authoritative_match_state_mutated') is not False):
            raise ValueError('Civet event gain or mirror context mismatch')
        summed[seat] += expected
    if summed != gains:
        raise ValueError('Civet receipt totals do not match events')
    return gains


def calculate_terminal_damage(compiled, result):
    extension_contract()
    receipt = result.get('civet_v38')
    if receipt is None:
        return previous(compiled, result)
    if (result.get('terminated') is not True or result.get('truncated') is not False
            or type(result.get('winner')) is not int or result['winner'] not in (0, 1)):
        return base_damage(compiled, result)
    gains = _gains(compiled, receipt)
    if not any(gains):
        return previous(compiled, result)
    # Aggregating gains is safe only without other in-battle destiny mutations.
    if any(p.get('direct_destiny_lost') != 0 for p in result['players']):
        return {'resolved': False, 'reason': 'in_combat_destiny_ledger_required',
                'life_damage': None, 'training_label_allowed': False}
    ctx = compiled['context']
    if ctx.get('game_mode') != 3 or ctx.get('season_mec') != 10 or ctx.get('resonance_selected') != 0:
        raise ValueError('Civet settlement confirmation requires current ranked context')
    before = [p.get('life') for p in compiled['effect_players']]
    if len(before) != 2 or any(type(x) is not int or x <= 0 for x in before):
        raise ValueError('Explicit positive prebattle destiny required')
    credited = [life + gain for life, gain in zip(before, gains)]
    # Technical range guard, not a game cap. In particular, never clamp to100.
    if any(x > 2147483647 for x in credited):
        raise ValueError('Destiny exceeds supported int32 range')
    projected = deepcopy(compiled)
    for player, life in zip(projected['effect_players'], credited):
        player['life'] = life
    answer = base_damage(projected, result)
    if not answer.get('resolved'):
        return answer
    after = list(credited)
    after[answer['loser']] -= answer['life_damage']
    answer.update(
        damage_scope='gross_terminal_loss_separate_from_net_destiny_change',
        requested_destiny_gains=list(gains),
        civet_settlement={
            'rule_source': 'explicit_user_confirmation', 'rule_sha256': PROOF_SHA,
            'destiny_before_battle': before, 'destiny_gain': list(gains),
            'destiny_before_terminal_damage': credited,
            'predicted_destiny_after_terminal_damage': after,
            'predicted_net_change': [a-b for a, b in zip(after, before)],
            'gain_cap_at100': False, 'gains_applied_before_survival_check': True,
            'scope': 'civet_gain_plus_terminal_loss_preview; other rewards and counters remain pending',
            'server_balance_calibrated': False, 'match_state_mutated': False,
        },
    )
    return answer
