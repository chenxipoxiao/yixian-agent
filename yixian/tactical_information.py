"""Explicit information boundary and sealed simultaneous tactical decisions.

Input is an environment-owned visibility export, NEVER a raw HF publicData.
Replay publicData may contain private handCards and is not this schema.
"""
from __future__ import annotations

from copy import deepcopy

from .tactical_rules import digest

PUBLIC = ('character', 'career', 'realm', 'cultivation', 'destiny', 'alive',
          'fates', 'season_choices', 'inscriptions', 'public_permanent_buffs')
PRIVATE = ('hand', 'board', 'fates', 'season_choices', 'rerolls', 'pool_counts')


def information_set(table, seat):
    if table.get('schema') != 'explicit-seat-visibility-v1':
        raise ValueError('Require visibility-export schema, not raw replay or game state')
    round_number = table['round_number']
    if type(round_number) is not int or round_number < 1 or type(seat) is not int:
        raise ValueError('Invalid decision point')
    seats = table['seats']
    if len(seats) != 8 or {s['seat'] for s in seats} != set(range(8)) or seat not in range(8):
        raise ValueError('Require eight unique seat identities')
    projected = []
    for player in sorted(seats, key=lambda p: p['seat']):
        public = player['public']
        history = []
        for event in player.get('revealed_boards', []):
            if type(event['round']) is not int or not 1 <= event['round'] < round_number:
                # Reject, do not silently use current/future board as observation.
                raise ValueError('Unrevealed current/future board in public history')
            history.append({key: deepcopy(event[key]) for key in
                            ('round', 'board', 'cultivation', 'realm') if key in event})
        if len({event['round'] for event in history}) != len(history):
            raise ValueError('Ambiguous duplicate board history')
        projected.append({'seat': player['seat'], 'public': {key: deepcopy(public[key]) for key in PUBLIC if key in public},
                          'history': sorted(history, key=lambda e: e['round'])})
    own = next(p for p in seats if p['seat'] == seat)
    if 'private' not in own:
        raise ValueError('Own preparation state is unavailable')
    result = {'schema': 'tactical-information-set-v1', 'rules_fingerprint': table['rules_fingerprint'],
              'round_number': round_number, 'seat': seat, 'players': projected,
              'own': {key: deepcopy(own['private'][key]) for key in PRIVATE if key in own['private']}}
    result['digest'] = digest(result)
    return result


def sealed_decisions(table, policies, options):
    """All eight observations are frozen BEFORE any policy decision is applied.

    This collects legal action IDs only. It is not an eight-player match engine.
    """
    if set(policies) != set(range(8)) or set(options) != set(range(8)):
        raise ValueError('Eight explicit decision callbacks and legal option lists required')
    views = {seat: information_set(table, seat) for seat in range(8)}
    legal = deepcopy(options)
    actions = {}
    for seat in range(8):
        choices = legal[seat]
        ids = [choice['id'] for choice in choices]
        if not ids or len(set(ids)) != len(ids):
            raise ValueError('Malformed legal choices')
        choice = policies[seat](deepcopy(views[seat]), deepcopy(choices))
        if choice not in ids:
            raise ValueError('Policy selected an illegal action')
        actions[seat] = deepcopy(choices[ids.index(choice)])
    return {'actions': actions, 'observation_digests': {seat: view['digest'] for seat, view in views.items()},
            'full_match_completed': False}


def match_replay_contexts(contexts, *, character, career, round_number, rules_fingerprint,
                          split, public_core=()):
    """Prefer original tables containing same-career Long Yao using PAST only.

    Context index must be built from public events up to this exact cut-off.
    Unknown profession at opening cannot be selected using a future profession.
    Outcome/future/private fields are never returned or used for matching.
    """
    if split not in ('train', 'validation'):
        raise ValueError('Reserved test data is not a development retrieval pool')
    ranked = []
    for row in contexts:
        if row.get('split') != split or row.get('rules_fingerprint') != rules_fingerprint:
            continue
        if row.get('cutoff_round') != round_number-1:
            continue
        candidates = [p for p in row['public_players'] if p.get('character') == character
                      and p.get('career') == career and p.get('career_known_by_round', round_number) < round_number]
        if not candidates:
            continue
        overlap = max(len(set(public_core) & set(p.get('revealed_core', []))) for p in candidates)
        ranked.append({'game_id': row['game_id'], 'context_id': row['context_id'],
                       'same_character_and_career': True, 'public_core_overlap': overlap,
                       'counter_cards_guaranteed': False, 'causal_counterfactual': False})
    return sorted(ranked, key=lambda r: (-r['public_core_overlap'], r['game_id'], r['context_id']))


def replay_continuation_gate(*, tactical_action_changed):
    # Refuse the tempting but invalid "replay next round after counterfactual battle".
    # An unchanged opponent board does NOT establish unchanged learner/actions,
    # RNG, outcome, resources or rewards. No complete verifier exists here yet.
    return {'can_import_future_recorded_state': False,
            'full_match_training_allowed': False,
            'tactical_action_changed': bool(tactical_action_changed),
            'requires_environment_owned_resources_and_rewards': True}
