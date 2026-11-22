"""Eight-player process verification with replay opponents and explicit test rules.

This is a state-machine smoke test. Its default combat resolver does not execute
card effects. Replay snapshots are environment-side fixtures, not observations
or predictions of how a human would react to a changed match.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass
import random
from typing import Mapping, Sequence
from .season_start import TOGGLEABLE_SEASON_IDS
from .death_fates import UnknownDeathFateState, AmbiguousDeathFateOrder
from .round_rules import overflow_conversion
from .dragon_scale_reward import initialize_reward
from .post_battle import begin_post_battle_phase, resolve_post_battle_phase, contract as post_battle_contract
from .fate_acquisition import (grant_acquired_fate_cards, import_fate_acquisition_state,
                              owned_grant_fates, unacknowledged_grant_fates,
                              contract as acquisition_contract, IMPLEMENTED_ACQUISITION_FATE_IDS)


@dataclass(frozen=True)
class FlowRules:
    initial_life: int = 100
    max_rounds: int = 32
    initial_exp: int = 0
    initial_rerolls: int = 0
    exp_gain_per_round: int = 2
    extra_hp_gain_per_round: int = 2
    initial_max_physique: int = 6
    max_physique_gain_per_round: int = 5
    rerolls_gain_per_round: int = 3
    reroll_grants_by_round: tuple[int, ...] = ()
    rerolls_cap: int = 25
    level_thresholds: tuple[int, ...] = (0, 9, 21, 36, 55, 75)
    base_max_hp: tuple[int, ...] = (40, 45, 52, 62, 75, 100)
    profession_options: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7)
    low_damage_through_round: int = 12
    early_life_damage: int = 2
    late_life_damage: int = 20
    late_damage_growth: int = 2

    def validate(self):
        for name in ('initial_life', 'max_rounds', 'rerolls_cap'):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f'{name} must be a positive integer')
        for name in ('initial_exp', 'initial_rerolls', 'exp_gain_per_round', 'extra_hp_gain_per_round',
                     'rerolls_gain_per_round', 'low_damage_through_round', 'early_life_damage',
                     'late_life_damage', 'late_damage_growth', 'initial_max_physique', 'max_physique_gain_per_round'):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise ValueError(f'{name} must be a nonnegative integer')
        if self.initial_rerolls > self.rerolls_cap:
            raise ValueError('initial rerolls exceed their cap')
        if (not isinstance(self.reroll_grants_by_round, tuple)
                or any(type(x) is not int or x < 0 for x in self.reroll_grants_by_round)):
            raise ValueError('Reroll grants must be a tuple of nonnegative integers')
        if (not self.level_thresholds or len(self.level_thresholds) != len(self.base_max_hp)
                or self.level_thresholds[0] != 0
                or any(type(x) is not int or x < 0 for x in self.level_thresholds)
                or any(b <= a for a, b in zip(self.level_thresholds, self.level_thresholds[1:]))
                or any(type(x) is not int or x <= 0 for x in self.base_max_hp)):
            raise ValueError('Invalid realm thresholds or base health table')
        if (not self.profession_options or len(set(self.profession_options)) != len(self.profession_options)
                or any(type(x) is not int or x < 1 for x in self.profession_options)):
            raise ValueError('Profession options need unique positive configuration ids')

    def fixture_life_damage(self, round_number):
        if round_number <= self.low_damage_through_round:
            return self.early_life_damage
        return self.late_life_damage + self.late_damage_growth * (round_number-self.low_damage_through_round-1)

    def next_round_rerolls(self, completed_round):
        if self.reroll_grants_by_round:
            return self.reroll_grants_by_round[min(completed_round, len(self.reroll_grants_by_round)-1)]
        return self.rerolls_gain_per_round

    def provenance(self):
        return {
            'scope': 'eight_player_flow_fixture', 'current_rules_verified': False,
            'base_max_hp_and_need_exp': 'data/local/2026-11-06/tables/LevelConfig.json; copied local configuration, not server validation',
            'round_exp_and_extra_hp': 'Localization Tips_7: after a battle round +2 cultivation and +2 maximum health; configurable here',
            'rerolls_cap': 'Localization Tips_9: cap 25; configurable here',
            'max_physique': 'Localization CardKeywordDesc_体魄: initial retention cap 6, +5 each round; description-backed offline default',
            'reroll_schedule': ('Caller-supplied community reference; server timing and grants not calibrated'
                                if self.reroll_grants_by_round else 'Constant per-round grant is a process-test fixture'),
            'unverified_test_rules': [
                'rerolls_gain_per_round and its growth timing',
                'ascending uses cumulative thresholds without consuming cultivation',
                'fresh battle health resets to computed maximum',
                'pairing uses seeded random pairs and a bye for odd survivor counts',
                'default battle results and life damage are artificial process-test fixtures',
                'same-round elimination ties use remaining life then id',
                'regular and season fate effects are recorded but not executed',
                'a recorded opponent follows its replay trajectory instead of reacting to this agent'],
            'card_generation': 'not implemented; caller may supply draw_cards_by_round',
        }


class ScriptedFlowAgent:
    """Legal deterministic choices solely for exercising the process."""
    def choose_profession(self, observation, options):
        return options[0]

    def choose_ascend(self, observation, next_level, required_exp):
        return True

    def choose_fate(self, observation, candidates):
        return candidates[0]

    def choose_season(self, observation, offer):
        return next((x for x in offer['candidates'] if x != offer.get('skip_id')), offer['candidates'][0])

    def arrange(self, observation, cards):
        return list(cards)

    def choose_effect_toggles(self, observation, available_effects):
        return []


def fixture_battle(left, right, round_number, seed):
    """A reproducible coin flip, explicitly unrelated to Yi Xian card strength."""
    rng = random.Random(seed)
    winner = rng.randrange(2)
    surviving_hp = max(1, int((left, right)[winner]['max_hp'] * rng.uniform(.2, .9)))
    return {'winner': winner, 'remaining_hp': [surviving_hp, 0] if winner == 0 else [0, surviving_hp],
            'hp_delta': surviving_hp if winner == 0 else -surviving_hp,
            'resolver': 'flow_fixture_coin_flip', 'card_effects_executed': False}


def _cards(value):
    if not isinstance(value, (list, tuple)) or len(value) > 8:
        raise ValueError('Board must be a sequence of at most eight slots')
    if any(type(x) not in (str, int) or isinstance(x, str) and not x for x in value):
        raise ValueError('Cards must be explicit configuration ids; empty slots may be zero')
    return list(value)


def _integer(value, field, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{field} must be an integer >= {minimum}')
    return value


def _round_map(values, label):
    if values is None:
        return {}
    if not isinstance(values, Mapping):
        raise ValueError(f'{label} must map round numbers to values')
    result = {}
    for key, value in values.items():
        if type(key) is int:
            number = key
        elif isinstance(key, str) and key.isdecimal():
            number = int(key)
        else:
            raise ValueError(f'{label} has a noninteger round')
        if number < 1 or number in result:
            raise ValueError(f'{label} has a duplicate or invalid round')
        result[number] = deepcopy(value)
    return result


def _resource_snapshot(player):
    return {key: deepcopy(player[key]) for key in ('life', 'level', 'exp', 'extra_max_hp', 'max_hp', 'rerolls')}


def _own_observation(player, round_number):
    # Current enemy boards, hidden hands, future snapshots and environment seeds
    # are never supplied to the agent. Outcomes are only supplied after combat.
    result = {'round': round_number, 'self': {key: deepcopy(player[key]) for key in
            ('id', 'character_id', 'career', 'life', 'level', 'exp', 'max_hp', 'extra_max_hp',
             'rerolls', 'cards', 'hand_cards', 'fates', 'season_choices')}}
    if 'effect_state' in player:
        result['self']['effect_state'] = deepcopy(player['effect_state'])
    return result


def _battle_view(player):
    result = {key: deepcopy(player[key]) for key in
            ('id', 'character_id', 'career', 'cards', 'life', 'level', 'exp', 'max_hp', 'extra_max_hp', 'fates', 'season_choices')}
    result['qi'] = 0
    result['hp'] = result['max_hp']
    result['cultivation'] = result['exp']
    result['hand_card_count'] = len(player['hand_cards'])
    return result


def _effect_view(player):
    # Do not pass the replay trajectory or its integer-keyed round map into
    # effect handlers. Only current match state belongs to the effect contract.
    return {key: deepcopy(player[key]) for key in
            ('id', 'character_id', 'cards', 'is_mirror', 'life', 'rerolls', 'fates', 'season_choices', 'effect_state', 'exp',
             'max_hp', 'extra_max_hp', 'max_physique', 'physique', 'hand_cards', 'is_ai') if key in player}


def _initialize_flow_reward(player, *, talent_counters=None, newly_acquired=False):
    if not any(type(x) is int and x == 27 for x in player['fates']):
        return
    view = _effect_view(player)
    view['fates'] = [27]
    initialized = initialize_reward(view, talent_counters=talent_counters, newly_acquired=newly_acquired)
    player['effect_state'] = initialized['effect_state']


def _refresh_opponent(player, round_number, rules, *, preserve_rerolls=False):
    available = [number for number in player['_rounds'] if number <= round_number]
    if not available:
        raise ValueError(f"Opponent {player['id']} has no available past snapshot")
    source_round = max(available)
    snapshot = player['_rounds'][source_round]
    if not isinstance(snapshot, Mapping):
        raise ValueError('Opponent snapshot must be an object')
    before = _resource_snapshot(player)
    if player.get('_board_branch'):
        raise ValueError('Counterfactual board requires an explicit continuation; replay refresh cannot overwrite it')
    if 'cards' in snapshot:
        player['cards'] = _cards(snapshot['cards'])
    for key in ('character_id', 'career'):
        if key in snapshot:
            player[key] = deepcopy(snapshot[key])
    if 'is_mirror' in snapshot:
        if type(snapshot['is_mirror']) is not bool:
            raise ValueError('Mirror marker must be boolean')
        player['is_mirror'] = snapshot['is_mirror']
    for key in ('level', 'exp', 'rerolls'):
        if key in player.get('_independent_resources', []):
            continue
        if key == 'rerolls' and preserve_rerolls and player.get('_rerolls_initialized', False):
            continue
        if key in snapshot:
            player[key] = _integer(snapshot[key], key, 1 if key == 'level' else 0)
    if preserve_rerolls:
        player['_rerolls_initialized'] = True
    if player['level'] > len(rules.base_max_hp):
        raise ValueError('Replay realm is outside the configured level table')
    if 'extra_max_hp' in snapshot and 'extra_max_hp' not in player.get('_independent_resources', []):
        value = snapshot['extra_max_hp']
        if type(value) is not int:
            raise ValueError('extra_max_hp must be an integer')
        player['extra_max_hp'] = value
    player['max_hp'] = rules.base_max_hp[player['level']-1] + player['extra_max_hp']
    if player['max_hp'] <= 0:
        raise ValueError('Replay-derived maximum health must be positive')
    for key in ('fates', 'season_choices'):
        if key in snapshot:
            if not isinstance(snapshot[key], list):
                raise ValueError(f'{key} must be a list')
            player[key] = deepcopy(snapshot[key])
    for key in ('hand_cards','max_physique','physique','is_ai'):
        if key in snapshot and key not in player.get('_independent_resources', []):
            player[key] = deepcopy(snapshot[key])
    # In particular, do NOT copy life/alive/rank from a counterfactual replay.
    return {'source_round': source_round, 'snapshot_carried_forward': source_round != round_number,
            'recorded_life_ignored': snapshot.get('life'), 'before': before, 'after': _resource_snapshot(player)}


def run_match(opponents: Sequence[Mapping], *, rules: FlowRules | None = None, agent=None,
              resolver=None, seed=0, self_cards=None, season_offers=None,
              normal_fate_offers=None, draw_cards_by_round=None, self_character_id=None,
              effect_engine=None, self_fates=None, self_season_choices=None, draw_five_elements=None,
              round_draw_provider=None, post_battle_card_catalog=None, dragon_scale_choice_provider=None,
              fate_acquisition_card_catalog=None):
    """Run a bounded eight-player process test using seven replay trajectories.

    An opponent is ``{id, rounds: {round: snapshot}, source}``. Round one must
    exist. A snapshot may carry cards, character_id, career, level, exp, life,
    extra_max_hp, rerolls, fates and season_choices; life is NEVER overlaid.

    Season offers are ``{round: [{npc_id, candidates, skip_id?, source?}]}``.
    The selected id is a request receipt only. Optional draw cards are supplied
    externally; this runner does not invent a current-season card pool.

    resolver(left, right, round, seed) returns winner=0/1/None, optionally a
    nonnegative life_damage and JSON-like hp_delta/remaining_hp diagnostics.
    The default resolver is a test coin flip, not the legacy battle engine.
    Optional post_battle_card_catalog enables raw-card Dragon Scale rewards.
    dragon_scale_choice_provider(request) supplies an environment random result,
    never a policy action. Missing results stop at a serializable reward phase.
    An upgraded replay opponent stops before its next preparation: card-instance
    history cannot be inferred by overlaying a later recorded board.
    fate_acquisition_card_catalog enables explicit new 85/86 card grants to
    hand. Imported opponent ownership never replays the acquisition reward.
    """
    rules = rules or FlowRules()
    rules.validate()
    _integer(seed, 'seed')
    if not isinstance(opponents, Sequence) or len(opponents) != 7:
        raise ValueError('A match needs exactly seven distinct opponent trajectories')
    agent = agent or ScriptedFlowAgent()
    resolver = resolver or fixture_battle
    if not callable(resolver):
        raise TypeError('resolver must be callable')
    if post_battle_card_catalog is not None and (not isinstance(post_battle_card_catalog, Mapping) or effect_engine is None):
        raise ValueError('Post-battle rewards require explicit card metadata and an effect engine')
    if dragon_scale_choice_provider is not None and (not callable(dragon_scale_choice_provider) or post_battle_card_catalog is None):
        raise ValueError('An environment choice provider requires enabled post-battle rewards')
    if fate_acquisition_card_catalog is not None and (not isinstance(fate_acquisition_card_catalog, Mapping) or effect_engine is None):
        raise ValueError('Fate acquisition requires explicit raw-card metadata and an effect engine')
    offers = _round_map(season_offers, 'season_offers')
    fate_offers = _round_map(normal_fate_offers, 'normal_fate_offers')
    draws = _round_map(draw_cards_by_round, 'draw_cards_by_round')
    rng = random.Random(seed)
    journal = []

    def event(phase, round_number=0, **data):
        journal.append({'event': len(journal)+1, 'round': round_number, 'phase': phase, **deepcopy(data)})

    def cultivation_event(player, before, round_number, reason, *, reconstructed=True):
        if player['exp'] != before:
            event('cultivation_change', round_number, player=player['id'], before=before,
                  after=player['exp'], delta=player['exp']-before, reason=reason,
                  original_actions_reconstructed=reconstructed)

    def initial(identifier):
        return {'id': identifier, 'character_id': None, 'career': 0, 'life': rules.initial_life,
                'alive': True, 'level': 1, 'exp': rules.initial_exp, 'extra_max_hp': 0,
                'max_hp': rules.base_max_hp[0], 'rerolls': rules.initial_rerolls,
                'physique':0, 'max_physique':rules.initial_max_physique, 'is_mirror':False,
                'cards': [], 'hand_cards': [], 'fates': [], 'season_choices': [], 'rank': None}

    own = initial('agent')
    own['cards'] = _cards([] if self_cards is None else self_cards)
    own['character_id'] = self_character_id
    own['fates'] = deepcopy(self_fates or [])
    own['season_choices'] = deepcopy(self_season_choices or [])
    if effect_engine is not None:
        own = effect_engine.initialize_player(own, newly_acquired_fates=[x for x in own['fates'] if type(x) is int],
                                              talent_counters={}, season_temp_datas={})
    if post_battle_card_catalog is not None:
        _initialize_flow_reward(own, newly_acquired=True)
    if fate_acquisition_card_catalog is not None:
        granted = grant_acquired_fate_cards(_effect_view(own), owned_grant_fates(own),
                                            fate_acquisition_card_catalog, source_ref='explicit_initial_fresh_fates')
        own['effect_state'] = granted['player']['effect_state']
        own['hand_cards'] = granted['player']['hand_cards']
        if granted['events']:
            event('fate_acquisition_effects', player=own['id'], effects=granted['events'], pool_delta=0)
    players = [own]
    seen = {'agent'}
    for record in opponents:
        if not isinstance(record, Mapping) or not isinstance(record.get('id'), str) or not record['id'].strip():
            raise ValueError('Each opponent needs a nonempty id')
        if record['id'] in seen:
            raise ValueError('Opponent ids must be unique')
        seen.add(record['id'])
        rounds = _round_map(record.get('rounds'), 'opponent rounds')
        if 1 not in rounds:
            raise ValueError('An opponent must have a round-one snapshot; future state cannot fill it')
        opponent = initial(record['id'])
        opponent['_rounds'] = rounds
        opponent['source'] = deepcopy(record.get('source', {}))
        players.append(opponent)
    profession = agent.choose_profession(_own_observation(own, 0), list(rules.profession_options))
    if type(profession) is not int or profession not in rules.profession_options:
        raise ValueError('Agent selected an unavailable profession')
    own['career'] = profession
    event('choose_profession', player='agent', selected=profession, effects_applied=False)
    total_battles = 0
    completed_rounds = 0
    unresolved_effect_actions = []
    pending_post_battle_phase = None
    for round_number in range(1, rules.max_rounds+1):
        alive = [player for player in players if player['alive']]
        if len(alive) <= 1:
            break
        branched = [p for p in alive if p.get('_board_branch')]
        if branched:
            unresolved_effect_actions = [{'player': p['id'], 'kind': 'counterfactual_board_continuation_required',
                                         'branch': deepcopy(p['_board_branch'])} for p in branched]
            event('effect_resolution_blocked', round_number, actions=unresolved_effect_actions)
            break
        event('round_start', round_number, alive=[p['id'] for p in alive])
        for opponent in alive:
            if opponent is own:
                continue
            if fate_acquisition_card_catalog is not None and 'hand_cards' in opponent.get('_independent_resources', []):
                source_round = max(r for r in opponent['_rounds'] if r <= round_number)
                source_fates = opponent['_rounds'][source_round].get('fates', opponent['fates'])
                unacknowledged = unacknowledged_grant_fates(_effect_view(opponent), source_fates)
                if unacknowledged:
                    unresolved_effect_actions = [{'player': opponent['id'], 'kind': 'counterfactual_acquisition_continuation_required',
                                                  'source_round': source_round, 'fates': unacknowledged}]
                    event('effect_resolution_blocked', round_number, actions=unresolved_effect_actions)
                    break
            refreshed = _refresh_opponent(opponent, round_number, rules, preserve_rerolls=effect_engine is not None)
            cultivation_event(opponent, refreshed['before']['exp'], round_number,
                              'recorded_opponent_snapshot_adjustment', reconstructed=False)
            if effect_engine is not None:
                snapshot = opponent['_rounds'][refreshed['source_round']]
                initialized = effect_engine.initialize_player(_effect_view(opponent),
                    talent_counters=snapshot.get('talent_counters', {}),
                    season_temp_datas=snapshot.get('season_temp_datas', {}))
                opponent['effect_state'] = initialized['effect_state']
                if post_battle_card_catalog is not None:
                    _initialize_flow_reward(opponent, talent_counters=snapshot.get('talent_counters'))
                if fate_acquisition_card_catalog is not None:
                    imported = import_fate_acquisition_state(_effect_view(opponent),
                                                             source_ref=f"replay-snapshot-round-{refreshed['source_round']}")
                    opponent['effect_state'] = imported['player']['effect_state']
                    if imported['events']:
                        event('fate_acquisition_import', round_number, player=opponent['id'], effects=imported['events'])
            event('opponent_refresh', round_number, player=opponent['id'], source=opponent['source'], **refreshed)
        if unresolved_effect_actions:
            break
        if own['alive']:
            draw_plan = overflow_conversion(round_number, len(own['hand_cards']))
            supplied_draws = draws.get(round_number, [])
            if not isinstance(supplied_draws, list) or any(type(x) not in (int, str) for x in supplied_draws):
                raise ValueError('External draw records must be lists of card ids')
            drawn = []
            if draw_plan['cultivation_gain']:
                exp_before = own['exp']
                own['exp'] += draw_plan['cultivation_gain']
                cultivation_event(own, exp_before, round_number, 'overfull_hand_missed_draws')
            if draw_plan['draw_requests'] and round_draw_provider is not None:
                if round_number in draws:
                    raise ValueError('Use either a draw provider or explicit cards for each round')
                drawn = round_draw_provider(deepcopy(draw_plan['draw_requests']), _own_observation(own,round_number))
                expected = sum(request['count'] for request in draw_plan['draw_requests'])
                if not isinstance(drawn,list) or len(drawn) != expected or any(type(x) not in (int,str) for x in drawn):
                    raise ValueError('Round draw provider must resolve every explicit draw request')
            elif draw_plan['draw_requests']:
                drawn = deepcopy(supplied_draws)
                if (draw_plan['converted_card_count']
                        and len(drawn) > sum(r['count'] for r in draw_plan['draw_requests'])):
                    raise ValueError('Explicit round draws exceed the remaining overflow-adjusted grant')
            own['hand_cards'].extend(drawn)
            event('round_draws', round_number, plan=draw_plan, drawn_cards=drawn,
                  generator_supplied=round_draw_provider is not None,
                  normal_draws_generated=(round_draw_provider is not None or not draw_plan['draw_requests']),
                  original_eligible_pool_verified=False)
            event('self_resources', round_number, resources=_resource_snapshot(own))
            while own['level'] < len(rules.level_thresholds):
                target = own['level']+1
                threshold = rules.level_thresholds[target-1]
                if own['exp'] < threshold:
                    event('ascend_unavailable', round_number, next_level=target, required_exp=threshold, exp=own['exp'])
                    break
                choice = agent.choose_ascend(_own_observation(own, round_number), target, threshold)
                if type(choice) is not bool:
                    raise ValueError('Ascending requires a boolean decision')
                if not choice:
                    event('ascend_declined', round_number, next_level=target)
                    break
                before = _resource_snapshot(own)
                own['level'] = target
                own['max_hp'] = rules.base_max_hp[target-1]+own['extra_max_hp']
                event('ascend', round_number, before=before, after=_resource_snapshot(own), cultivation_consumed=0,
                      threshold_semantics_verified=False)
                candidates = fate_offers.get(target, [f'fixture-fate-{target}-{i}' for i in range(3)])
                if (not isinstance(candidates, list) or not candidates
                        or any(type(x) not in (str, int) for x in candidates)):
                    raise ValueError('A normal fate offer requires candidates')
                selected = agent.choose_fate(_own_observation(own, round_number), deepcopy(candidates))
                if type(selected) not in (str, int) or selected not in candidates:
                    raise ValueError('Agent selected an unavailable fate')
                own['fates'].append(deepcopy(selected))
                acquisition_applied = False
                if effect_engine is not None:
                    initialized = effect_engine.initialize_player(own, newly_acquired_fates=[selected] if type(selected) is int else [],
                                                                  talent_counters={}, season_temp_datas={})
                    own['effect_state'] = initialized['effect_state']
                    if post_battle_card_catalog is not None:
                        _initialize_flow_reward(own, newly_acquired=selected == 27)
                if fate_acquisition_card_catalog is not None and selected in IMPLEMENTED_ACQUISITION_FATE_IDS:
                    granted = grant_acquired_fate_cards(_effect_view(own), [selected], fate_acquisition_card_catalog,
                                                        source_ref=f'round-{round_number}-ascend-{target}')
                    own['effect_state'] = granted['player']['effect_state']
                    own['hand_cards'] = granted['player']['hand_cards']
                    acquisition_applied = bool(granted['events'])
                    if granted['events']:
                        event('fate_acquisition_effects', round_number, player=own['id'], effects=granted['events'], pool_delta=0)
                event('choose_fate', round_number, level=target, candidates=candidates, selected=selected,
                      source='external' if target in fate_offers else 'fixture', effects_applied=acquisition_applied)
            supplied = offers.get(round_number, [])
            if not isinstance(supplied, list):
                raise ValueError('A season round must contain a list of offers')
            for offer in supplied:
                if not isinstance(offer, Mapping) or not isinstance(offer.get('candidates'), list) or not offer['candidates']:
                    raise ValueError('Season offers require explicit candidate lists')
                candidates = offer['candidates']
                if (any(type(x) not in (str, int) for x in candidates) or len(set(candidates)) != len(candidates)
                        or ('skip_id' in offer and offer['skip_id'] not in candidates)):
                    raise ValueError('Invalid season candidates or skip id')
                visible_offer = {key: deepcopy(offer[key]) for key in ('npc_id', 'candidates', 'skip_id') if key in offer}
                selected = agent.choose_season(_own_observation(own, round_number), visible_offer)
                if type(selected) not in (str, int) or selected not in candidates:
                    raise ValueError('Agent selected an unavailable season fate')
                receipt = {'npc_id': offer.get('npc_id'), 'selected': selected,
                           'kind': 'skip' if selected == offer.get('skip_id') else 'select', 'round': round_number}
                own['season_choices'].append(receipt)
                if effect_engine is not None:
                    initialized = effect_engine.initialize_player(own, talent_counters={}, season_temp_datas={})
                    own['effect_state'] = initialized['effect_state']
                event('choose_season', round_number, candidates=candidates, receipt=receipt,
                      source=offer.get('source'), effects_applied=False, authoritative_confirmation=False)
            if effect_engine is not None:
                available = sorted(identifier for identifier in TOGGLEABLE_SEASON_IDS if any(value == identifier or isinstance(value, dict) and
                    value.get('kind') != 'skip' and value.get('selected') == identifier for value in own['season_choices']))
                requested = agent.choose_effect_toggles(_own_observation(own, round_number), available)
                if not isinstance(requested, list) or len(requested) > len(available):
                    raise ValueError('Effect toggle actions must be a list of owned toggleable effects')
                seen_toggles = set()
                for toggle in requested:
                    if (not isinstance(toggle, Mapping) or set(toggle) != {'effect_id', 'enabled'}
                            or toggle['effect_id'] not in available or toggle['effect_id'] in seen_toggles
                            or type(toggle['enabled']) is not bool):
                        raise ValueError('Invalid or duplicate effect toggle action')
                    changed = effect_engine.set_season_enabled(own, toggle['effect_id'], toggle['enabled'])
                    own['effect_state'] = changed['effect_state']
                    seen_toggles.add(toggle['effect_id'])
                    event('toggle_effect', round_number, player='agent', **dict(toggle))
            event('card_management', round_number, externally_supplied_draws=drawn,
                  card_pool_generation_implemented=False, replace_card_sampling_implemented=False,
                  hand_count=len(own['hand_cards']), rerolls=own['rerolls'])
            arranged = agent.arrange(_own_observation(own, round_number), list(own['cards']))
            arranged = _cards(arranged)
            if Counter(arranged) != Counter(own['cards']):
                raise ValueError('Arrangement must preserve every existing card and empty slot')
            own['cards'] = arranged
            event('arrange', round_number, player='agent', cards=arranged)
        pairing = list(alive)
        rng.shuffle(pairing)
        bye = pairing.pop() if len(pairing) % 2 else None
        pairs = [pairing[i:i+2] for i in range(0, len(pairing), 2)]
        event('matchmaking', round_number, pairs=[[p['id'] for p in pair] for pair in pairs],
              bye=bye['id'] if bye else None, rule='fixture_seeded_pairs_with_bye')
        for left, right in pairs:
            battle_seed = rng.randrange(2**31)
            first = 0 if left['exp'] > right['exp'] else 1 if right['exp'] > left['exp'] else random.Random(battle_seed).randrange(2)
            combatants = [_battle_view(left), _battle_view(right)]
            if effect_engine is not None:
                for player in (left, right):
                    if player['rerolls'] > rules.rerolls_cap:
                        before = player['rerolls']
                        player['rerolls'] = rules.rerolls_cap
                        event('reroll_overflow_expired', round_number, player=player['id'],
                              before=before, after=player['rerolls'], timing='battle_start')
                effect_inputs = [dict(combatants[i], effect_state=deepcopy(player['effect_state']))
                                 for i, player in enumerate((left, right))]
                started = effect_engine.battle_start(*effect_inputs)
                combatants = started['players']
                event('battle_start_effects', round_number, players=[left['id'], right['id']],
                      effects=started['events'], unsupported_effects=started.get('unsupported_effects', []),
                      starting_qi=[player['qi'] for player in combatants])
            result = resolver(*combatants, round_number, battle_seed)
            if not isinstance(result, Mapping) or 'winner' not in result:
                raise ValueError('Battle resolver must return an explicit winner field')
            winner = result.get('winner')
            if winner is not None and (type(winner) is not int or winner not in (0, 1)):
                raise ValueError('Invalid battle winner')
            if result.get('truncated') is True or result.get('terminated') is False:
                winner = None
            damage = result.get('life_damage', rules.fixture_life_damage(round_number)) if winner is not None else 0
            damage = _integer(damage, 'life_damage')
            total_battles += 1
            event('battle', round_number, players=[left['id'], right['id']], first_player=first,
                  winner=(left, right)[winner]['id'] if winner is not None else None,
                  result=dict(result), battle_seed=battle_seed)
            if winner is not None:
                victor = (left, right)[winner]
                loser = (left, right)[1-winner]
                if effect_engine is not None:
                    try:
                        settled = effect_engine.settle(_effect_view(victor), _effect_view(loser), damage,
                                                       draw_five_elements=draw_five_elements)
                    except (UnknownDeathFateState, AmbiguousDeathFateOrder) as error:
                        unresolved_effect_actions = [{'player':loser['id'], 'reason':str(error)}]
                        event('effect_resolution_blocked', round_number, actions=unresolved_effect_actions)
                        break
                    for player, update in ((victor, settled['winner']), (loser, settled['loser'])):
                        exp_before = player['exp']
                        for key in ('effect_state','rerolls','exp','max_hp','extra_max_hp','max_physique','hand_cards'):
                            if key in update:
                                if player is not own and key in ('exp','extra_max_hp','max_physique','hand_cards') and update[key] != player.get(key):
                                    independent = set(player.get('_independent_resources', []))
                                    independent.add(key)
                                    player['_independent_resources'] = sorted(independent)
                                player[key] = deepcopy(update[key])
                        cultivation_event(player, exp_before, round_number, 'settlement_fate_effect')
                    event('settlement_effects', round_number, winner=victor['id'], loser=loser['id'],
                          base_damage=damage, final_damage=settled['life_damage'],
                          effects=settled['events'], unsupported_effects=settled.get('unsupported_effects', []))
                    damage = settled['life_damage']
                    unresolved_effect_actions = deepcopy(settled.get('pending_actions', []))
                before_life = loser['life']
                loser['life'] -= damage
                event('settlement', round_number, loser=loser['id'], life_before=before_life,
                      life_damage=damage, life_after=loser['life'],
                      damage_source='resolver' if 'life_damage' in result else 'fixture_rules')
                if unresolved_effect_actions:
                    event('effect_resolution_blocked', round_number, actions=unresolved_effect_actions)
                    break
                if post_battle_card_catalog is not None:
                    phase = begin_post_battle_phase([_effect_view(p) for p in (left, right)],
                                                    battle_id=f'round-{round_number}-battle-{total_battles}')
                    resolved = resolve_post_battle_phase(phase, post_battle_card_catalog)
                    reward_events = resolved['new_events']
                    phase = resolved['phase']
                    if phase['pending_actions'] and dragon_scale_choice_provider is not None:
                        choices = {}
                        for request in phase['pending_actions']:
                            selected_slot = dragon_scale_choice_provider(deepcopy(request))
                            if selected_slot is not None:
                                choices[request['player']] = selected_slot
                        if choices:
                            resolved = resolve_post_battle_phase(phase, post_battle_card_catalog, selected_slots=choices)
                            reward_events.extend(resolved['new_events'])
                            phase = resolved['phase']
                    for player, update in zip((left, right), phase['players']):
                        if player is not own and player['cards'] != update['cards']:
                            player['_board_branch'] = {'round': round_number, 'battle_id': phase['battle_id'],
                                                      'before': list(player['cards']), 'after': list(update['cards'])}
                        player['cards'] = deepcopy(update['cards'])
                        player['effect_state'] = deepcopy(update['effect_state'])
                    event('post_battle_rewards', round_number, battle_id=phase['battle_id'], effects=reward_events,
                          complete_resolution=phase['complete_resolution'], pending_actions=phase['pending_actions'])
                    if not phase['complete_resolution']:
                        pending_post_battle_phase = phase
                        unresolved_effect_actions = deepcopy(phase['pending_actions'])
                        event('effect_resolution_blocked', round_number, actions=unresolved_effect_actions)
                        break
            else:
                event('settlement_unresolved', round_number, players=[left['id'], right['id']],
                      life_damage=0, training_label_usable=False)
        if unresolved_effect_actions:
            completed_rounds = round_number
            break
        eliminated = sorted([p for p in alive if p['life'] <= 0], key=lambda p: (p['life'], p['id']))
        for offset, player in enumerate(eliminated):
            player['alive'] = False
            player['rank'] = len(alive)-offset
            event('elimination', round_number, player=player['id'], rank=player['rank'], life=player['life'])
        if own['alive']:
            before = _resource_snapshot(own)
            own['exp'] += rules.exp_gain_per_round
            cultivation_event(own, before['exp'], round_number, 'ordinary_round_growth')
            own['extra_max_hp'] += rules.extra_hp_gain_per_round
            own['max_physique'] += rules.max_physique_gain_per_round
            own['max_hp'] = rules.base_max_hp[own['level']-1]+own['extra_max_hp']
            grant = rules.next_round_rerolls(round_number)
            granted = min(rules.rerolls_cap, own['rerolls']+grant)
            own['rerolls'] = max(own['rerolls'], granted) if effect_engine is not None else granted
            event('round_growth', round_number, player='agent', before=before, after=_resource_snapshot(own),
                  timing='after_round', next_round_reroll_grant=grant,
                  opponent_growth='read_from_next_replay_snapshot')
        if effect_engine is not None:
            # Counterfactual rewards belong to this match. Initialize opponent
            # rerolls once, then advance this account instead of copying a later
            # replay balance that could erase or double-count simulated wins.
            for opponent in players[1:]:
                if opponent['alive']:
                    if 'exp' in opponent.get('_independent_resources', []):
                        exp_before = opponent['exp']
                        opponent['exp'] += rules.exp_gain_per_round
                        cultivation_event(opponent, exp_before, round_number, 'ordinary_round_growth_after_branching_from_replay')
                    if 'extra_max_hp' in opponent.get('_independent_resources', []):
                        opponent['extra_max_hp'] += rules.extra_hp_gain_per_round
                        opponent['max_hp'] = rules.base_max_hp[opponent['level']-1]+opponent['extra_max_hp']
                    if 'max_physique' in opponent.get('_independent_resources', []):
                        opponent['max_physique'] += rules.max_physique_gain_per_round
                    before = opponent['rerolls']
                    grant = rules.next_round_rerolls(round_number)
                    opponent['rerolls'] = max(before, min(rules.rerolls_cap, before+grant))
                    event('opponent_reroll_growth', round_number, player=opponent['id'], before=before,
                          after=opponent['rerolls'], grant=grant, replay_spending_not_reconstructed=True)
        event('round_end', round_number, alive=[p['id'] for p in players if p['alive']])
        completed_rounds = round_number
    survivors = [p for p in players if p['alive']]
    terminated = len(survivors) == 1
    if terminated:
        survivors[0]['rank'] = 1
        event('match_end', completed_rounds, winner=survivors[0]['id'])
    else:
        event('match_truncated', completed_rounds, survivors=[p['id'] for p in survivors],
              reason='pending_effect_resolution' if unresolved_effect_actions else 'round_limit', unresolved_ranks=True)
    public_results = [{key: deepcopy(value) for key, value in player.items() if not key.startswith('_')}
                      for player in players]
    cultivation_accounts = []
    for player in players:
        entries = [e for e in journal if e['phase']=='cultivation_change' and e['player']==player['id']]
        balance = rules.initial_exp
        for entry in entries:
            if entry['before'] != balance or entry['after'] != balance+entry['delta']:
                raise AssertionError('Cultivation ledger continuity failed')
            balance = entry['after']
        if balance != player['exp']:
            raise AssertionError('An unrecorded cultivation mutation occurred')
        cultivation_accounts.append({'player':player['id'],'opening_balance':rules.initial_exp,
            'closing_balance':balance,'net_change':sum(e['delta'] for e in entries),
            'balanced':True,'contains_unreconstructed_replay_actions':any(not e['original_actions_reconstructed'] for e in entries)})
    provenance = rules.provenance()
    if effect_engine is not None:
        provenance['unverified_test_rules'] = [text for text in provenance['unverified_test_rules']
                                              if text != 'regular and season fate effects are recorded but not executed']
        provenance['effect_execution'] = 'Registered effect components execute through event hooks; remaining components are reported as unsupported'
    return {'schema_version': 1, 'scope': 'eight_player_process_verification', 'seed': seed,
            'current_rules_verified': False, 'full_game_rules_implemented': False,
            'policy_training_allowed': False, 'strength_claim': False,
            'unresolved_effect_actions': unresolved_effect_actions,
            'pending_post_battle_phase': pending_post_battle_phase,
            'post_battle_rewards_enabled': post_battle_card_catalog is not None,
            'post_battle_contract': post_battle_contract() if post_battle_card_catalog is not None else None,
            'fate_acquisition_enabled': fate_acquisition_card_catalog is not None,
            'fate_acquisition_contract': acquisition_contract() if fate_acquisition_card_catalog is not None else None,
            'cultivation_accounts': cultivation_accounts,
            'terminated': terminated, 'truncated': not terminated,
            'winner': survivors[0]['id'] if terminated else None, 'rounds': completed_rounds,
            'fully_completed_rounds': sum(e['phase'] == 'round_end' for e in journal),
            'battle_count': total_battles, 'player_count': len(players),
            'rules': {key: list(value) if isinstance(value, tuple) else value for key, value in asdict(rules).items()},
            'rule_provenance': provenance, 'players': public_results,
            'effect_engine_enabled': effect_engine is not None,
            'agent_rank': own['rank'], 'journal': journal,
            'limitations': ['Default combat is a test fixture, not card-effect simulation.',
                            'Recorded opponents do not react to altered match histories.',
                            'Effects outside the enabled effect registry, draw pools and replace-card sampling are not implemented.',
                            'True server matching, life damage and ties require calibration.']}
