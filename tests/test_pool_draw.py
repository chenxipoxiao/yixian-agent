from copy import deepcopy
import json
import unittest

from yixian.card_pool import create_pool
from yixian.pool_draw import make_round_draw_provider
from yixian.round_rules import round_draw_requests


def metadata(card_id, category, copies):
    return {'card_id': card_id, 'name': f'card-{card_id}', 'family': f'family-{card_id}',
            'realm': 1, 'category': category, 'copy_count': copies, 'replace_effect': False}


def initial_pool(seed=1, sect=8, profession=8):
    return create_pool([metadata(1, 'sect', sect), metadata(2, 'profession', profession)], seed=seed)


def candidates(request, observation):
    return {'sect': [1], 'profession': [2], 'combined_remaining': [1, 2]}[request['pool']]


class PoolDrawTests(unittest.TestCase):
    def test_normal_round_draws_persist_and_return_only_raw_ids(self):
        initial = initial_pool()
        provider = make_round_draw_provider(initial, candidates)
        result = provider(round_draw_requests(1), {'round': 1, 'self': {'level': 1}})
        self.assertEqual(result, [1, 1, 2])
        self.assertEqual([provider.snapshot()['families'][key]['remaining']
                          for key in ('family-1', 'family-2')], [6, 7])
        self.assertEqual(initial['families']['family-1']['remaining'], 8)
        provider(round_draw_requests(2), {'round': 2})
        self.assertEqual(provider.snapshot()['families']['family-1']['remaining'], 4)

    def test_combined_draw_after_ordinary_requests_uses_remaining_entities(self):
        provider = make_round_draw_provider(initial_pool(sect=2, profession=9), candidates)
        result = provider(round_draw_requests(12), {'round': 12})
        self.assertEqual(result, [1, 1, 2, 2])
        self.assertEqual(provider.snapshot()['families']['family-1']['remaining'], 0)
        self.assertEqual(provider.snapshot()['families']['family-2']['remaining'], 7)

    def test_combined_sampling_does_not_choose_categories_half_and_half(self):
        # Seed 1 randrange(10)==2, so the profession's nine physical copies win.
        # A forbidden preliminary randrange(2)==0 would instead choose the sect.
        provider = make_round_draw_provider(initial_pool(seed=1, sect=1, profession=9), candidates)
        result = provider([{'pool': 'combined_remaining', 'count': 1}], {'round': 12})
        self.assertEqual(result, [2])

    def test_snapshot_roundtrip_restarts_the_same_next_draw(self):
        provider = make_round_draw_provider(initial_pool(seed=9), candidates)
        provider(round_draw_requests(12), {'round': 12})
        restored = make_round_draw_provider(json.loads(json.dumps(provider.snapshot())), candidates)
        self.assertEqual(provider(round_draw_requests(13), {'round': 13}),
                         restored(round_draw_requests(13), {'round': 13}))
        self.assertEqual(provider.snapshot(), restored.snapshot())

    def test_pool_and_rng_never_passed_to_eligibility_callback_or_observation(self):
        observed = []
        observation = {'round': 1, 'self': {'level': 1, 'hand_cards': []}}
        frozen = deepcopy(observation)
        def checking_provider(request, public):
            observed.append(deepcopy(public))
            public['self']['hand_cards'].append('mutated-by-callback')
            request['count'] = 999
            return [1]
        provider = make_round_draw_provider(initial_pool(), checking_provider)
        self.assertEqual(provider([{'pool': 'sect', 'count': 1}], observation), [1])
        self.assertEqual(observation, frozen)
        self.assertEqual(observed, [frozen])
        self.assertFalse(provider.contract()['pool_and_rng_in_policy_observation'])

    def test_invalid_later_request_does_not_partially_consume_pool(self):
        provider = make_round_draw_provider(initial_pool(), candidates)
        before = provider.snapshot()
        with self.assertRaises(ValueError):
            provider([{'pool': 'sect', 'count': 2}, {'pool': 'wrong', 'count': 1}], {'round': 1})
        self.assertEqual(provider.snapshot(), before)
        self.assertEqual(provider.last_events(), [])

    def test_wrong_category_is_rejected_and_empty_pool_returns_fallback(self):
        provider = make_round_draw_provider(initial_pool(), lambda request, observation: [2])
        with self.assertRaises(ValueError):
            provider([{'pool': 'sect', 'count': 1}], {})
        empty = make_round_draw_provider(initial_pool(sect=0, profession=0), candidates)
        self.assertEqual(empty(round_draw_requests(12), {'round': 12}), [-1, -1, -1, -1])

    def test_snapshot_and_audit_accessors_are_detached_environment_copies(self):
        provider = make_round_draw_provider(initial_pool(), candidates)
        provider([{'pool': 'sect', 'count': 1}], {})
        snap = provider.snapshot()
        snap['families']['family-1']['remaining'] = 0
        events = provider.last_events()
        events[0]['card_id'] = 999
        self.assertEqual(provider.snapshot()['families']['family-1']['remaining'], 7)
        self.assertEqual(provider.last_events()[0]['card_id'], 1)


if __name__ == '__main__':
    unittest.main()
