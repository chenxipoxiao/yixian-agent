from copy import deepcopy
import unittest
from yixian.dragon_scale_reward_validation import audit_reward_snapshot, summarize_reward_audit
from test_dragon_scale_reward import catalog


def player(board, after_board, before=1, after=0, life=20):
    return {'audit_context': {'is_mirror':False},
            'start_snapshot': {'board':board, 'talentTempDatas':{'27':before}, 'destiny':30},
            'after_snapshot': {'destiny':life, 'talentTempDatas':{'27':after}},
            'private_snapshot': {'board':after_board}}


class DragonScaleRewardValidationTests(unittest.TestCase):
    def test_prediction_set_does_not_use_observed_choice(self):
        left=player([15,16],[10015,16]);right=player([15,16],[15,10016])
        a,b=(audit_reward_snapshot(p,catalog()) for p in (left,right))
        self.assertEqual(a['predicted_outputs'],b['predicted_outputs'])
        self.assertTrue(a['allowed_output_match'] and b['allowed_output_match'])
        self.assertFalse(a['deterministic'])
        self.assertEqual(a['allowed_choice_count'],2)

    def test_wrong_priority_and_counter_remain_visible_mismatches(self):
        result=audit_reward_snapshot(player([15,101],[15,10101]),catalog())
        self.assertFalse(result['allowed_output_match'])
        result=audit_reward_snapshot(player([15],[10015],after=1),catalog())
        self.assertFalse(result['allowed_output_match'])

    def test_missing_expected_board_is_not_filled_from_input(self):
        p=player([15],[10015]);del p['private_snapshot']['board']
        self.assertEqual(audit_reward_snapshot(p,catalog())['status'],'expected_output_missing')

    def test_mirror_and_eliminated_context_do_not_become_live_reward_evidence(self):
        p=player([15],[10015]);p['audit_context']['is_mirror']=True
        self.assertEqual(audit_reward_snapshot(p,catalog())['status'],'mirror_or_unknown_context')
        p['audit_context']['is_mirror']=False;p['start_snapshot']['destiny']=0
        self.assertEqual(audit_reward_snapshot(p,catalog())['status'],'already_eliminated_or_unknown_start_destiny')

    def test_no_candidate_and_used_counter_noop_are_distinguished(self):
        no_card=audit_reward_snapshot(player([10101],[10101],after=1),catalog())
        used=audit_reward_snapshot(player([101],[101],before=0),catalog())
        summary=summarize_reward_audit([no_card,used])
        self.assertEqual(summary['allowed_output_matches'],2)
        self.assertEqual(summary['no_candidate_charge_preserved_snapshots'],1)
        self.assertFalse(summary['current_server_calibration_passed'])
        self.assertEqual(summary['training_labels_emitted'],0)
