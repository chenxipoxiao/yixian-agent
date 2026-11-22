"""Numerical search bridge to pinned yisim: REFERENCE diagnostics only.

This adapter deliberately uses reference card IDs and an engine fingerprint,
not the current client's numeric catalogue fingerprint. No fuzzy ID mapping.
"""
from copy import deepcopy

from .research import contract_digest
from .simulator import engine_contract, simulate_battle


class ReferenceBattleEvaluator:
    def __init__(self, *, own_state, max_turns=64):
        self.own_state = deepcopy(own_state)
        self.max_turns = max_turns
        self.contract = {'engine': engine_contract(), 'utility': 'own_terminal_hp_minus_opponent_terminal_hp',
                         'training_allowed': False, 'current_server_verified': False}
        self.rules_fingerprint = contract_digest(self.contract)

    def __call__(self, board, scenario):
        if set(scenario) != {'opponent_state', 'first_player', 'seed'}:
            raise ValueError('Explicit hypothesis state, initiative and random seed required')
        if len(board) != 8 or len(scenario['opponent_state']['cards']) != 8:
            raise ValueError('This reference interface requires eight explicit slots')
        own = deepcopy(self.own_state); own['cards'] = list(board)
        battle = {'players': [own, deepcopy(scenario['opponent_state'])],
                  'first_player': scenario['first_player'], 'seed': scenario['seed'],
                  'max_turns': self.max_turns, 'include_log': False}
        result = simulate_battle(battle)
        resolved = result['terminated'] and not result['truncated'] and result['winner'] in (0, 1)
        return {'rules_fingerprint': self.rules_fingerprint, 'resolved': resolved,
                'terminated': result['terminated'], 'truncated': result['truncated'],
                'utility': result['players'][0]['hp'] - result['players'][1]['hp'] if resolved else None,
                'winner': result['winner'], 'turns': result['turns'],
                'scope': 'legacy_reference_terminal_hp_margin_not_live_strength',
                'current_server_verified': False, 'training_label_allowed': False}
