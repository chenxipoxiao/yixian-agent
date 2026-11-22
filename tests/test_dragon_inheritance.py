from copy import deepcopy
import json
import unittest

from yixian.dragon_inheritance import (initialize_inheritance, request_inheritance_draw,
    resolve_inheritance_draw, LEDGER, PENDING, UnknownInheritanceState, contract)
from yixian.pool_draw import make_round_draw_provider, DRAW_RECEIPTS
from yixian.effects import EffectEngine, UnknownEffectState, SUPPORTED_FATES
from yixian.fate_catalog import discover_runtime_support
from test_pool_draw import initial_pool, candidates


def actor(hand=None):
    return initialize_inheritance({'id': 'agent', 'character_id': 1000003, 'level': 1,
        'fates': [24], 'hand_cards': list(hand or []), 'cards': [1], 'exp': 0, 'life': 100}, fresh_match=True)


def pending(player=None, pool=None):
    return request_inheritance_draw(actor() if player is None else player, 'first_round', round_number=1, pool_category=pool)


class InheritanceTests(unittest.TestCase):
    def test_first_round_then_realm5_consume_distinct_two_card_batches_once(self):
        provider = make_round_draw_provider(initial_pool(), candidates)
        first = resolve_inheritance_draw(pending(), provider)
        self.assertEqual(len(first['player']['hand_cards']), 2)
        self.assertTrue(all(e['pool']=='combined_remaining' for e in first['events'][0]['pool_audit']))
        self.assertEqual(sum(f['remaining'] for f in provider.snapshot()['families'].values()), 14)
        player = first['player']; player['level'] = 5
        second_request = request_inheritance_draw(player, 'realm5', round_number=9, previous_level=4)
        second = resolve_inheritance_draw(second_request, provider)
        self.assertEqual(len(second['player']['hand_cards']), 4)
        self.assertTrue(all(e['pool']=='combined_remaining' for e in second['events'][0]['pool_audit']))
        self.assertEqual(sum(f['remaining'] for f in provider.snapshot()['families'].values()), 12)
        before = provider.snapshot()
        retry = request_inheritance_draw(second['player'], 'realm5', round_number=9, previous_level=4)
        self.assertEqual(resolve_inheritance_draw(retry, provider)['events'], [])
        self.assertEqual(provider.snapshot(), before)

    def test_confirmed_combined_pool_is_bound_without_caller_guess(self):
        provider = make_round_draw_provider(initial_pool(), candidates); before = provider.snapshot()
        request = pending(pool=None); original = deepcopy(request)
        self.assertEqual(request['effect_state'][PENDING]['pool'],'combined_remaining')
        result = resolve_inheritance_draw(request)
        self.assertFalse(result['complete_resolution'])
        self.assertEqual(result['pending_actions'][0]['reason'], 'pool_provider_required')
        self.assertEqual(provider.snapshot(), before)
        self.assertEqual(request, original)
        resolved = resolve_inheritance_draw(result['player'], provider)
        self.assertTrue(resolved['complete_resolution'])
        self.assertEqual(len(resolved['player']['hand_cards']), 2)

    def test_explicit_pool_without_provider_stays_pending(self):
        result = resolve_inheritance_draw(pending())
        self.assertEqual(result['pending_actions'][0]['reason'], 'pool_provider_required')
        with self.assertRaises(ValueError): resolve_inheritance_draw(pending(), lambda *_: [1, 1])

    def test_fate_draws_ignore_overfull_hand_without_adding_cultivation(self):
        provider = make_round_draw_provider(initial_pool(), candidates)
        first = resolve_inheritance_draw(pending(actor([1]*13)), provider)['player']
        self.assertEqual((len(first['hand_cards']), first['exp']), (15, 0))
        first['level'] = 5
        second = request_inheritance_draw(first, 'realm5', round_number=10, previous_level=4)
        final = resolve_inheritance_draw(second, provider)['player']
        self.assertEqual((len(final['hand_cards']), final['exp']), (17, 0))

    def test_snapshot_import_does_not_replay_either_historical_reward(self):
        player = {'id': 'opponent', 'character_id': 1000003, 'level': 5, 'fates': [24]}
        imported = initialize_inheritance(player, snapshot_round=12)
        self.assertTrue(all(e['status']=='imported_snapshot' for e in imported['effect_state'][LEDGER]['events'].values()))
        self.assertEqual(request_inheritance_draw(imported, 'first_round', round_number=12), imported)
        self.assertEqual(request_inheritance_draw(imported, 'realm5', round_number=12), imported)
        self.assertNotIn('hand_cards', imported)

    def test_consumed_simulation_history_survives_reinitialization_and_import(self):
        provider = make_round_draw_provider(initial_pool(), candidates)
        player = resolve_inheritance_draw(pending(), provider)['player']
        self.assertEqual(initialize_inheritance(player, fresh_match=True), player)
        self.assertEqual(initialize_inheritance(player, snapshot_round=3), player)
        self.assertEqual(player['effect_state'][LEDGER]['events']['realm5']['status'], 'available')

    def test_import_before_realm5_allows_only_an_explicit_later_transition(self):
        player = {'id': 'opponent', 'character_id': 1000003, 'level': 4, 'fates': [24], 'hand_cards': []}
        player = initialize_inheritance(player, snapshot_round=8)
        self.assertEqual(player['effect_state'][LEDGER]['events']['realm5']['status'], 'available')
        player['level'] = 5
        provider = make_round_draw_provider(initial_pool(), candidates)
        request = request_inheritance_draw(player, 'realm5', round_number=9, previous_level=4)
        self.assertEqual(len(resolve_inheritance_draw(request, provider)['player']['hand_cards']), 2)

    def test_stale_hand_realm_identity_and_category_are_rejected_before_draw(self):
        provider = make_round_draw_provider(initial_pool(), candidates); before = provider.snapshot()
        for field, value in [('hand_cards', [2]), ('level', 2), ('id', 'different-player')]:
            player = pending(); player[field] = value
            with self.assertRaises(UnknownInheritanceState): resolve_inheritance_draw(player, provider)
        with self.assertRaises(ValueError): resolve_inheritance_draw(pending(), provider, pool_category='profession')
        self.assertEqual(provider.snapshot(), before)

    def test_unhandled_first_round_and_wrong_transition_are_not_guessed(self):
        with self.assertRaises(UnknownInheritanceState): request_inheritance_draw(actor(), 'first_round', round_number=2)
        fresh = actor(); fresh['level'] = 5
        with self.assertRaises(UnknownInheritanceState): request_inheritance_draw(fresh, 'realm5', round_number=9, previous_level=4)
        imported = initialize_inheritance({'id': 'x', 'character_id': 1000003, 'fates': [24], 'level': 4, 'hand_cards': []}, snapshot_round=8)
        imported['level'] = 5
        for previous in (3, 5, None):
            with self.assertRaises(UnknownInheritanceState): request_inheritance_draw(imported, 'realm5', round_number=9, previous_level=previous)

    def test_pending_draw_prevents_battle_and_new_settlement(self):
        engine = EffectEngine(); player = pending(pool=None)
        with self.assertRaises(UnknownEffectState): engine.battle_start(player, player)
        with self.assertRaises(UnknownEffectState): engine.settle(player, player, 10)

    def test_other_modes_mirrors_and_characters_are_not_included(self):
        base = {'id': 'x', 'character_id': 1000003, 'level': 1, 'fates': [24], 'hand_cards': []}
        with self.assertRaises(UnknownInheritanceState): initialize_inheritance(base, fresh_match=True, game_mode=16)
        for key, value in [('character_id', 1000004), ('is_mirror', True), ('level', 5)]:
            player = dict(base, **{key: value})
            with self.assertRaises(UnknownInheritanceState): initialize_inheritance(player, fresh_match=True)
        with self.assertRaises(UnknownInheritanceState): initialize_inheritance(base)

    def test_empty_eligible_pool_returns_fallback_and_consumes_trigger_once(self):
        provider = make_round_draw_provider(initial_pool(sect=0, profession=0), candidates)
        result = resolve_inheritance_draw(pending(), provider)
        self.assertEqual(result['player']['hand_cards'], [-1, -1])
        self.assertEqual(result['player']['effect_state'][LEDGER]['events']['first_round']['status'], 'completed')
        self.assertEqual(resolve_inheritance_draw(result['player'], provider)['events'], [])

    def test_invalid_eligibility_is_atomic_for_pool_and_player(self):
        provider = make_round_draw_provider(initial_pool(), lambda *_: [999])
        request = pending(); original = deepcopy(request); before = provider.snapshot()
        with self.assertRaises(ValueError): resolve_inheritance_draw(request, provider)
        self.assertEqual(request, original)
        self.assertEqual(provider.snapshot(), before)

    def test_pool_or_rng_never_leaks_to_eligibility_observation(self):
        seen = []
        def eligible(request, observation):
            seen.append(deepcopy(observation)); return [1]
        provider = make_round_draw_provider(initial_pool(), eligible)
        resolve_inheritance_draw(pending(), provider)
        encoded = json.dumps(seen)
        self.assertNotIn('rng_state', encoded)
        self.assertNotIn('families', encoded)
        self.assertNotIn(DRAW_RECEIPTS, encoded)

    def test_registry_and_contract_remain_conditional(self):
        self.assertEqual(discover_runtime_support()['partial_regular'][24], ['conditional_extra_draw'])
        self.assertNotIn(24, SUPPORTED_FATES)
        self.assertFalse(contract()['automatic_flow_hook_available'])
        self.assertFalse(contract()['current_server_rules_verified'])
        self.assertEqual(contract()['pool_category'],'combined_remaining')

    def test_both_triggers_use_physical_copy_weighting_across_categories(self):
        # A lone sect copy and nine profession copies: seed1's first two
        # draws are both profession, rather than selecting categories 50/50.
        for trigger in ('first_round','realm5'):
            p=actor()
            if trigger=='realm5':
                p=initialize_inheritance({'id':'agent','character_id':1000003,'level':4,'fates':[24],
                                          'hand_cards':[1]*13,'exp':20},snapshot_round=8)
                p['level']=5
            req=request_inheritance_draw(p,trigger,round_number=1 if trigger=='first_round' else 9,
                                         previous_level=4 if trigger=='realm5' else None)
            provider=make_round_draw_provider(initial_pool(seed=1,sect=1,profession=9),candidates)
            out=resolve_inheritance_draw(req,provider)
            self.assertEqual(out['player']['hand_cards'][-2:],[2,2])
            self.assertEqual(provider.snapshot()['families']['family-1']['remaining'],1)
            self.assertEqual(provider.snapshot()['families']['family-2']['remaining'],7)
            self.assertEqual(out['events'][0]['cultivation_gain'],0)

    def test_sect_and_profession_overrides_are_rejected(self):
        provider=make_round_draw_provider(initial_pool(),candidates);before=provider.snapshot()
        for pool in ('sect','profession','wrong'):
            with self.assertRaises(ValueError):pending(pool=pool)
            with self.assertRaises(ValueError):resolve_inheritance_draw(pending(),provider,pool_category=pool)
        self.assertEqual(provider.snapshot(),before)

    def test_old_pending_requests_are_not_silently_reinterpreted(self):
        provider=make_round_draw_provider(initial_pool(),candidates);before=provider.snapshot()
        for pool in (None,'sect','profession','combined_remaining'):
            req=pending();req['effect_state'][PENDING].pop('rules_version')
            req['effect_state'][PENDING]['pool']=pool;original=deepcopy(req)
            with self.assertRaises(UnknownInheritanceState):resolve_inheritance_draw(req,provider)
            self.assertEqual(req,original);self.assertEqual(provider.snapshot(),before)

    def test_explicit_confirmed_pool_is_equivalent_to_default(self):
        self.assertEqual(pending(),pending(pool='combined_remaining'))


class PersistentDrawReceiptTests(unittest.TestCase):
    def test_retry_and_snapshot_restore_do_not_spend_pool_or_rng_again(self):
        provider = make_round_draw_provider(initial_pool(), candidates)
        request = pending(); first = resolve_inheritance_draw(request, provider)
        snapshot = json.loads(json.dumps(provider.snapshot()))
        restored = make_round_draw_provider(snapshot, candidates)
        retry = resolve_inheritance_draw(request, restored)
        self.assertEqual(retry['player'], first['player'])
        self.assertTrue(retry['events'][0]['pool_receipt_reused'])
        self.assertEqual(restored.snapshot(), snapshot)
        self.assertEqual(restored.last_events(), [])

    def test_same_event_key_cannot_be_rebound_to_another_request(self):
        provider = make_round_draw_provider(initial_pool(), candidates)
        provider.draw_once('event', [{'pool':'sect','count':2}], {'round':1})
        before = provider.snapshot()
        with self.assertRaises(ValueError): provider.draw_once('event', [{'pool':'profession','count':2}], {'round':1})
        with self.assertRaises(ValueError): provider.draw_once('event', [{'pool':'sect','count':2}], {'round':2})
        self.assertEqual(provider.snapshot(), before)

    def test_later_invalid_batch_does_not_leave_partial_receipt(self):
        provider = make_round_draw_provider(initial_pool(), candidates); before = provider.snapshot()
        with self.assertRaises(ValueError): provider.draw_once('bad', [{'pool':'sect','count':2}, {'pool':'bad','count':1}], {})
        self.assertEqual(provider.snapshot(), before)

    def test_tampered_receipt_is_rejected_during_restore(self):
        provider = make_round_draw_provider(initial_pool(), candidates)
        provider.draw_once('event', [{'pool':'sect','count':2}], {})
        snapshot = provider.snapshot(); snapshot[DRAW_RECEIPTS]['event']['drawn'] = [2, 2]
        with self.assertRaises(ValueError): make_round_draw_provider(snapshot, candidates)

