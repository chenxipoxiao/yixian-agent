from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from yixian.combat_initialization import (derive_base_combat_state, IncompleteCombatState,
    load_initialization_contract, LEVELS, EVIDENCE, ROOT)
from yixian.research import canonical_json, contract_digest


def public():
    return {'level': 3, 'life': 1, 'hp': 999, 'maxHp': 999, 'extraMaxHp': 777,
            'lastRoundData': {'level': 3, 'life': 100, 'extraMaxHp': 11,
                              'usedCards': [1000003, 0, 1000001], 'usedKeYinCards': []}}


class CombatInitializationTests(unittest.TestCase):
    def test_contract_can_be_registered_as_canonical_json(self):
        import json
        contract = load_initialization_contract()
        self.assertEqual(json.loads(canonical_json(contract)), contract)
        self.assertEqual(len(contract_digest(contract)), 64)

    def test_exact_boundary_and_order_no_double_rewards(self):
        state = public(); before = deepcopy(state)
        result = derive_base_combat_state(state)
        self.assertEqual(result['base_combat'], {'hp': 63, 'max_hp': 63, 'qi': 0, 'def': 0,
            'action_again_per_round': 1, 'raw_cards': [1000003, 0, 1000001], 'raw_keyin_cards': []})
        self.assertEqual(state, before)
        for key in ['effects_applied', 'complete_battle_input', 'training_label_allowed',
                    'source_timing_verified', 'server_parity_verified', 'reapplied_acquisition_rewards']:
            self.assertIs(result[key], False)

    def test_public_level_used_with_disagreement_recorded(self):
        state = public(); state['level'] = 4
        result = derive_base_combat_state(state)
        self.assertEqual(result['base_combat']['hp'], 73)
        self.assertEqual(result['input_evidence']['last_round_level'], 3)
        self.assertIs(result['snapshot_levels_agree'], False)

    def test_level_zero_branch_and_negative_extra(self):
        state = public(); state['level'] = 0
        self.assertEqual(derive_base_combat_state(state)['base_combat']['hp'], 11)
        state['level'] = 1; state['lastRoundData']['extraMaxHp'] = -10
        self.assertEqual(derive_base_combat_state(state)['base_combat']['hp'], 30)

    def test_missing_evidence_never_replaced_by_public_post_state(self):
        for name in ['extraMaxHp', 'usedCards', 'usedKeYinCards']:
            state = public(); state['lastRoundData'].pop(name)
            state[name] = 999 if name=='extraMaxHp' else [777]
            with self.assertRaises(IncompleteCombatState): derive_base_combat_state(state)
        state = public(); state.pop('level')
        with self.assertRaises(IncompleteCombatState): derive_base_combat_state(state)

    def test_absent_snapshot_level_remains_unknown(self):
        state = public(); state['lastRoundData'].pop('level')
        self.assertIsNone(derive_base_combat_state(state)['snapshot_levels_agree'])

    def test_invalid_numeric_evidence_and_card_shape_rejected(self):
        for value in [True, 3.0, -1, 7]:
            state = public(); state['level'] = value
            with self.assertRaises(IncompleteCombatState): derive_base_combat_state(state)
        for value in [True, None, float('inf'), -100]:
            state = public(); state['lastRoundData']['extraMaxHp'] = value
            with self.assertRaises(IncompleteCombatState): derive_base_combat_state(state)
        for value in [[], [True], [-1], [1]*9]:
            state = public(); state['lastRoundData']['usedCards'] = value
            with self.assertRaises(IncompleteCombatState): derive_base_combat_state(state)

    def test_pinned_source_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in [LEVELS, EVIDENCE]:
                path = root/name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT/name).read_bytes())
            self.assertEqual(load_initialization_contract(root)['realm_base_hp']['5'], 75)
            (root/LEVELS).write_text('[]', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'): load_initialization_contract(root)


if __name__ == '__main__':
    unittest.main()
