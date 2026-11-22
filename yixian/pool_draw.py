"""Environment-only bridge from explicit pool state to round draw requests.

The callable returns only raw card IDs. Its private remaining counts, random
state and audit events must never be copied into a policy observation.
"""
from collections.abc import Mapping
from copy import deepcopy
import hashlib
from pathlib import Path

from .card_pool import contract as pool_contract, draw_card, snapshot
from .research import canonical_json

DRAW_RECEIPTS = 'draw_once_receipts'


def _digest(value):
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()


class RoundDrawProvider:
    """Own one player's pool across calls; commit each request batch atomically.

    ``eligible_provider(request, observation)`` supplies a raw-ID whitelist for
    that request. It receives detached copies of public input only, never the
    private pool/RNG. For combined_remaining it must explicitly provide the
    union of the legal sect and profession candidates. The draw is weighted by
    remaining physical copies across that whole union, without a category toss.
    """

    def __init__(self, pool, eligible_provider):
        if not callable(eligible_provider):
            raise ValueError('An explicit eligible-provider callback is required')
        self._pool = snapshot(pool)
        self._eligible_provider = eligible_provider
        self._last_events = []
        receipts = self._pool.get(DRAW_RECEIPTS, {})
        if not isinstance(receipts, dict):
            raise ValueError('Draw receipts must be an object')
        for key, receipt in receipts.items():
            if (not isinstance(key, str) or not key or not isinstance(receipt, dict)
                    or not isinstance(receipt.get('drawn'), list)
                    or any(type(x) is not int or x == 0 or x < -1 for x in receipt['drawn'])
                    or not isinstance(receipt.get('events'), list)
                    or not isinstance(receipt.get('request_sha256'), str)
                    or receipt.get('receipt_sha256') != _digest({k: v for k, v in receipt.items() if k != 'receipt_sha256'})):
                raise ValueError('Invalid draw-once receipt')

    def __call__(self, requests, observation):
        if not isinstance(requests, list) or not isinstance(observation, Mapping):
            raise ValueError('Expected a list of draw requests and a public observation object')
        working = snapshot(self._pool)
        drawn, events = [], []
        for index, request in enumerate(requests):
            if not isinstance(request, Mapping):
                raise ValueError('Each draw request must be an object')
            category = request.get('pool')
            if category not in ('sect', 'profession', 'combined_remaining'):
                raise ValueError('Unknown round-draw pool category')
            count = request.get('count')
            if type(count) is not int or count < 0:
                raise ValueError('Draw request count must be a nonnegative integer')
            if not count:
                continue
            eligible = self._eligible_provider(deepcopy(dict(request)), deepcopy(dict(observation)))
            if not isinstance(eligible, (list, tuple)):
                raise ValueError('Eligible provider must return explicit raw card IDs')
            allowed_categories = {'sect', 'profession'} if category == 'combined_remaining' else {category}
            for card_id in eligible:
                if type(card_id) is not int or card_id <= 0:
                    raise ValueError('Eligible provider must return positive raw CardConfig IDs')
                metadata = working['cards'].get(str(card_id))
                if metadata is None or metadata['category'] not in allowed_categories:
                    raise ValueError('Eligible raw card is unknown or outside the requested category')
            for draw_index in range(count):
                result = draw_card(working, list(eligible))
                working = result['pool']
                drawn.append(result['card_id'])
                events.append({'request_index': index, 'draw_index': draw_index, 'pool': category,
                               'card_id': result['card_id'], 'events': result['events'],
                               'sampling': 'uniform_remaining_eligible_card_entities'})
        # An invalid later request cannot partially spend inventory or randomness.
        self._pool, self._last_events = working, events
        return drawn

    def draw_once(self, event_key, requests, observation):
        """Commit a keyed draw batch atomically; exact retries reuse its receipt.

        Receipts live in the environment pool snapshot and survive restoration.
        Ordinary unkeyed round draws remain caller-managed. This is not a full
        match transaction or permission to reuse a pool for a different player.
        """
        if not isinstance(event_key, str) or not event_key:
            raise ValueError('A stable draw event key is required')
        fingerprint = _digest({'requests': requests, 'observation': observation, 'provider': self.contract()})
        previous = self._pool.get(DRAW_RECEIPTS, {}).get(event_key)
        if previous is not None:
            if previous['request_sha256'] != fingerprint:
                raise ValueError('Draw event context changed; refusing to redraw or reinterpret it')
            self._last_events = []
            return deepcopy(previous['drawn'])
        staged = RoundDrawProvider(self._pool, self._eligible_provider)
        drawn = staged(requests, observation)
        receipt = {'request_sha256': fingerprint, 'drawn': drawn, 'events': staged.last_events()}
        receipt['receipt_sha256'] = _digest(receipt)
        staged._pool.setdefault(DRAW_RECEIPTS, {})[event_key] = receipt
        self._pool = snapshot(staged._pool)
        self._last_events = staged.last_events()
        return list(drawn)

    def snapshot(self):
        """Environment persistence only; never add this to an observation."""
        return snapshot(self._pool)

    def last_events(self):
        """Environment diagnostic events, detached from the live provider."""
        return deepcopy(self._last_events)

    def contract(self):
        return {'schema_version': 1,
                'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'pool': pool_contract(self._pool),
                'scope': 'environment_provider_for_explicit_eligible_pool',
                'server_eligible_pool_verified': False,
                'combined_sampling': 'uniform_remaining_entity_without_category_coin_flip',
                'returns_to_flow': 'raw_card_ids_only',
                'keyed_draws': 'persistent_context_checked_receipts; ordinary_round_calls_are_not_idempotent',
                'pool_and_rng_in_policy_observation': False}


def make_round_draw_provider(pool, eligible_provider):
    return RoundDrawProvider(pool, eligible_provider)
