from copy import deepcopy
import unittest

from yixian.dragon_scale_reward import (initialize_reward, apply_post_battle_upgrade,
    upgrade_candidates, REMAINING, PENDING, UnknownDragonScaleReward)
from yixian.effects import EffectEngine, UnknownEffectState


def catalog():
    result = {}
    for card, owner in ((15, 1000003), (16, 1000003), (101, 0), (102, 0)):
        for rarity in (0, 1, 2):
            identifier = card + rarity * 10000
            result[identifier] = dict(id=identifier, name=str(card), owner=owner, level=3,
                                      sect=0, career=0, rarity=rarity, noUpgrade=rarity==2)
    return result


def actor(board, life=20):
    return initialize_reward({'character_id': 1000003, 'fates': [27], 'life': life,
                              'board': list(board), 'hand_cards': [15], 'rerolls': 7}, newly_acquired=True)


class DragonScaleRewardTests(unittest.TestCase):
    def test_singleton_upgrades_once_and_preserves_other_resources(self):
        player = actor([101, 10101, 0]); before = deepcopy(player)
        result = apply_post_battle_upgrade(player, catalog())
        self.assertEqual(result['player']['board'], [10101, 10101, 0])
        self.assertEqual(result['player']['effect_state'][REMAINING], 0)
        self.assertEqual(result['player']['hand_cards'], [15])
        self.assertEqual(result['player']['rerolls'], 7)
        self.assertEqual(result['player']['life'], 20)
        self.assertEqual(player, before)
        again = apply_post_battle_upgrade(result['player'], catalog())
        self.assertEqual(again['events'], [])

    def test_threshold_does_not_require_alive_and_does_not_deduct_destiny(self):
        for life, upgraded in ((21, False), (20, True), (1, True), (0, True), (-17, True)):
            result = apply_post_battle_upgrade(actor([101], life), catalog())
            self.assertEqual(result['player']['board'][0], 10101 if upgraded else 101)
            self.assertEqual(result['player']['life'], life)

    def test_exclusive_card_has_priority_over_ordinary_and_hand_is_not_candidate(self):
        player = actor([101, 16, 0])
        self.assertEqual([c['slot'] for c in upgrade_candidates(player['board'], catalog())], [1])
        result = apply_post_battle_upgrade(player, catalog())
        self.assertEqual(result['player']['board'], [101, 10016, 0])
        with self.assertRaises(ValueError): apply_post_battle_upgrade(player, catalog(), selected_slot=0)

    def test_multiple_eligible_slots_leave_pending_without_choosing_or_consuming(self):
        player = actor([15, 16, 101])
        result = apply_post_battle_upgrade(player, catalog())
        self.assertFalse(result['complete_resolution'])
        self.assertEqual(result['pending_actions'][0]['candidate_slots'], [0, 1])
        self.assertEqual(result['player']['effect_state'][REMAINING], 1)
        self.assertEqual(result['player']['board'], player['board'])
        selected = apply_post_battle_upgrade(result['player'], catalog(), selected_slot=1)
        self.assertEqual(selected['player']['board'], [15, 10016, 101])
        self.assertNotIn(PENDING, selected['player']['effect_state'])

    def test_duplicate_instances_are_distinct_slots(self):
        self.assertEqual([c['slot'] for c in upgrade_candidates([101, 101], catalog())], [0, 1])

    def test_no_candidate_retains_charge_and_later_board_can_use_it(self):
        player = actor([10101, 10102], 1)
        result = apply_post_battle_upgrade(player, catalog())
        self.assertEqual(result['player']['effect_state'][REMAINING], 1)
        self.assertEqual(result['player']['hand_cards'], [15])
        result['player']['board'][1] = 102
        later = apply_post_battle_upgrade(result['player'], catalog())
        self.assertEqual(later['player']['effect_state'][REMAINING], 0)

    def test_used_ledger_cannot_be_reset_by_replay_or_reacquisition(self):
        used = apply_post_battle_upgrade(actor([101]), catalog())['player']
        imported = initialize_reward(used, talent_counters={'27':1}, newly_acquired=True)
        self.assertEqual(imported['effect_state'][REMAINING], 0)

    def test_missing_raw_state_does_not_grant_a_free_charge(self):
        player={'character_id':1000003,'fates':[27]}
        for counters in (None, {}):
            with self.assertRaises(UnknownDragonScaleReward): initialize_reward(player, talent_counters=counters)
        for counter in (True, -1, 2):
            with self.assertRaises(ValueError): initialize_reward(player,talent_counters={'27':counter})
        self.assertEqual(initialize_reward(player,talent_counters={'27':0})['effect_state'][REMAINING],0)

    def test_unknown_metadata_and_invalid_choice_leave_input_unchanged(self):
        player=actor([15,16]);before=deepcopy(player)
        for choice in (2, True, -1):
            with self.assertRaises(ValueError): apply_post_battle_upgrade(player,catalog(),selected_slot=choice)
        self.assertEqual(player,before)
        metadata=catalog();del metadata[10015]
        with self.assertRaises(UnknownDragonScaleReward): apply_post_battle_upgrade(player,metadata)
        self.assertEqual(player,before)

    def test_pending_choice_cannot_follow_a_changed_board(self):
        player=apply_post_battle_upgrade(actor([15,16]),catalog())['player']
        player['board'].reverse()
        with self.assertRaises(UnknownDragonScaleReward): apply_post_battle_upgrade(player,catalog(),selected_slot=0)

    def test_pending_upgrade_blocks_new_combat_or_settlement(self):
        player=apply_post_battle_upgrade(actor([15,16]),catalog())['player']
        other={'fates':[], 'life':100, 'rerolls':0}
        with self.assertRaises(UnknownEffectState): EffectEngine().battle_start(player,other)
        with self.assertRaises(UnknownEffectState): EffectEngine().settle(other,player,10)
        with self.assertRaises(UnknownEffectState): EffectEngine().settle(player,other,10)

    def test_unowned_fate_and_other_characters_are_not_implicitly_enabled(self):
        player={'character_id':1000003,'fates':[]}
        self.assertEqual(apply_post_battle_upgrade(player,{})['events'],[])
        with self.assertRaises(ValueError): initialize_reward(player,newly_acquired=True)
        with self.assertRaises(UnknownDragonScaleReward): initialize_reward({'character_id':1000001,'fates':[27]},newly_acquired=True)
