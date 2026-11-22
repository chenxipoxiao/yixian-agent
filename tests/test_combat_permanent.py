from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest

from yixian.combat_initialization import IncompleteCombatState
from yixian.combat_permanent import (
    ROOT, EVIDENCE, load_permanent_initialization_contract, derive_permanent_combat_state,
)


def snapshot(buffs=None):
    return {'level': 4, 'hp': -50, 'extraMaxHp': 999,
            'permanentBuffTempDatas': {'10023': 900, '10024': 999},
            'lastRoundData': {'level': 4, 'extraMaxHp': 8, 'usedCards': [1000001, 0],
                              'usedKeYinCards': [], 'permanentBuffTempDatas': {} if buffs is None else buffs}}


class PermanentInitializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_permanent_initialization_contract()

    def derive(self, state, **kwargs):
        return derive_permanent_combat_state(state, contract=self.contract, **kwargs)

    def test_positive_physique_increases_maximum_without_healing(self):
        result = self.derive(snapshot({'10023': 13, '10024': 36}))
        self.assertEqual((result['base_combat']['hp'], result['base_combat']['max_hp']), (70, 70))
        combat = result['initialized_combat']
        self.assertEqual((combat['hp'], combat['max_hp']), (70, 83))
        self.assertEqual(combat['raw_buffs'], {'10023': 13, '10024': 36})

    def test_cap_is_not_added_to_hp_or_used_to_clamp_physique(self):
        result = self.derive(snapshot({'10023': 20, '10024': 5}))['initialized_combat']
        self.assertEqual((result['hp'], result['max_hp'], result['physique'], result['physique_cap']), (70, 90, 20, 5))

    def test_explicit_empty_map_uses_client_missing_entry_zero(self):
        result = self.derive(snapshot())['initialized_combat']
        self.assertEqual(result['raw_buffs'], {})
        self.assertEqual((result['physique'], result['physique_cap']), (0, 0))
        self.assertEqual((result['hp'], result['max_hp']), (70, 70))

    def test_missing_map_is_not_inferred_empty_from_current_public_map(self):
        state = snapshot(); del state['lastRoundData']['permanentBuffTempDatas']
        with self.assertRaises(IncompleteCombatState): self.derive(state)

    def test_nonpositive_entries_do_not_apply(self):
        result = self.derive(snapshot({'10023': -3, '10024': 0}))
        self.assertEqual(result['initialized_combat']['raw_buffs'], {})
        self.assertEqual(result['initialized_combat']['max_hp'], 70)
        self.assertEqual(result['initialization_events'][0]['raw_value'], -3)

    def test_other_counters_and_later_hooks_are_preserved_without_execution(self):
        pending = {'10000': 22, '10006': 10, '17': 3, '369': 7, '10008': 2, '99999': 6}
        result = self.derive(snapshot(pending))
        self.assertEqual(result['deferred_permanent_entries'], pending)
        self.assertEqual(result['initialized_combat']['raw_buffs'], {})
        self.assertFalse(result['complete_permanent_effects_applied'])

    def test_repeated_derivation_and_json_restore_never_accumulate(self):
        state = snapshot({'10023': 8, '10024': 46}); original = deepcopy(state)
        first = self.derive(state); second = self.derive(json.loads(json.dumps(state)))
        self.assertEqual(first, second); self.assertEqual(state, original)
        first['initialized_combat']['raw_buffs']['10023'] = 90
        self.assertEqual(self.derive(state)['initialized_combat']['max_hp'], 78)

    def test_evolved_boundary_cannot_be_reapplied_as_public_snapshot(self):
        result = self.derive(snapshot({'10023': 10}))
        with self.assertRaises(IncompleteCombatState): self.derive(result)

    def test_source_current_hp_and_map_do_not_replace_last_round_values(self):
        state = snapshot({'10023': 2}); first = self.derive(state)
        state.update(hp=12345, extraMaxHp=12345, permanentBuffTempDatas={'10023': 9999})
        self.assertEqual(first, self.derive(state))

    def test_map_shape_and_integer_values_are_explicit(self):
        for value in (None, [], {'10023': True}, {'10023': 1.0}, {'10023': '2'}, {'10023': 1_000_001}):
            with self.subTest(value=value), self.assertRaises(IncompleteCombatState):
                state=snapshot(); state['lastRoundData']['permanentBuffTempDatas']=value; self.derive(state)

    def test_noncanonical_keys_rejected(self):
        for key in (10023, '010023', '+10023', '-10023', '０１００２３', '0', 'unknown'):
            with self.subTest(key=key), self.assertRaises(IncompleteCombatState): self.derive(snapshot({key: 1}))

    def test_mode_scope_not_silently_expanded(self):
        for mode in (16, 121, True, '3'):
            with self.subTest(mode=mode), self.assertRaises(IncompleteCombatState): self.derive(snapshot(), game_mode=mode)

    def test_level_disagreement_and_pending_calibration_not_hidden(self):
        state = snapshot({'10023': 4}); state['lastRoundData']['level'] = 3
        result = self.derive(state)
        self.assertFalse(result['snapshot_levels_agree'])
        for flag in ('source_timing_verified','complete_battle_input','training_label_allowed',
                     'server_parity_verified','reapplied_acquisition_rewards','effects_applied'):
            self.assertFalse(result[flag])

    def test_cards_order_slots_and_baseline_resources_preserved(self):
        result = self.derive(snapshot({'10023': 1}))['initialized_combat']
        self.assertEqual(result['raw_cards'], [1000001, 0]); self.assertEqual(result['raw_keyin_cards'], [])
        self.assertEqual((result['qi'], result['def'], result['action_again_per_round']), (0, 0, 1))

    def test_evidence_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root/EVIDENCE; path.parent.mkdir(parents=True)
            path.write_bytes((ROOT/EVIDENCE).read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError, 'evidence hash mismatch'):
                load_permanent_initialization_contract(root)
