"""Targeted fate-settlement consistency checks against normalized real replays.

Only round-start fields construct effect inputs. Current/after snapshots are
read, when available, solely as expected counter outputs. This audit neither
replays combat nor silently assumes that unrelated effects were executed.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import math

from .effects import EffectEngine, UnknownEffectState
from .settlement import audit_recorded_damage, ordinary_destiny_damage

# Presence is enough to exclude: a board does not prove whether a card fired.
# These are known potential settlement confounders, not an exhaustive catalog.
UNSUPPORTED_DESTINY_CARDS = {5000006, 5010006, 5020006, 10433}
UNSUPPORTED_DAMAGE_FATES = {7, 27, 65, 83, 154}
TARGETS = ('talent_45', 'talent_105', 'season_2011')


def _ids(state, field):
    values = state.get(field, [])
    if not isinstance(values, list) or any(type(x) is not int for x in values):
        raise ValueError(f'Expected numeric {field} IDs in the start snapshot')
    return set(values)


def _participants(row):
    outcome = row.get('outcome', {})
    if outcome.get('status') != 'recorded_winner':
        return None
    players = row.get('players', [])
    winner_slot = outcome.get('winner_snapshot_slot')
    if (not isinstance(players, list) or len(players) != 2 or winner_slot not in ('p1', 'p2')
            or {p.get('snapshot_slot') for p in players} != {'p1', 'p2'}):
        return None
    winner = next(p for p in players if p['snapshot_slot'] == winner_slot)
    loser = next(p for p in players if p['snapshot_slot'] != winner_slot)
    return winner, loser


def _numeric(value):
    return type(value) in (int, float) and math.isfinite(value)


def _known_exclusions(row, winner, loser):
    reasons = []
    if row.get('game_mode') != 3 or row.get('season_mec') != 10:
        reasons.append('outside_current_ranked_mode')
    for side, player in (('winner', winner), ('loser', loser)):
        state = player['start_snapshot']
        for card in sorted(_ids(state, 'board') & UNSUPPORTED_DESTINY_CARDS):
            reasons.append(f'{side}_unimplemented_destiny_card:{card}')
        if _ids(state, 'fate_strategies'):
            reasons.append(f'{side}_unimplemented_other_season_fate_strategies')
    for fate in sorted(_ids(loser['start_snapshot'], 'talents') & UNSUPPORTED_DAMAGE_FATES):
        reasons.append(f'loser_unimplemented_settlement_fate:{fate}')
    # Missing the entire dictionary is unavailable evidence, while an explicit
    # empty dictionary means the client's ContainsKey(105) check is false.
    if 105 in _ids(loser['start_snapshot'], 'talents'):
        counters = loser['start_snapshot'].get('talentTempDatas')
        if not isinstance(counters, Mapping):
            reasons.append('loser_talent_105_start_counter_dictionary_missing')
        elif type(counters.get('105', 0)) is not int or counters.get('105', 0) not in (0, 1):
            reasons.append('loser_talent_105_start_counter_invalid')
    if 2011 in _ids(winner['start_snapshot'], 'xian_mo_strategies'):
        rerolls = winner['start_snapshot'].get('rerolls')
        if type(rerolls) is not int or rerolls < 0:
            reasons.append('winner_start_rerolls_missing_for_2011')
    return reasons


def _effect_player(player):
    state = player['start_snapshot']
    # Input fields unused by settlement are deliberately not copied. In
    # particular post-battle counters and current season snapshots never enter.
    return {'fates': sorted(_ids(state, 'talents')),
            'season_choices': sorted(_ids(state, 'xian_mo_strategies')),
            'rerolls': state.get('rerolls', 0)}


def audit_effect_settlement(records, *, engine=None):
    """Compare base and implemented damage on the same eligible target records.

    Known unimplemented cards/survival effects exclude a record before reading
    its expected damage or counter. Unknown interactions remain an explicit
    limitation, so even a perfect match is a conditional consistency result.
    """
    rows = list(records)
    engine = engine or EffectEngine()
    results, exclusions, coverage = [], Counter(), {key:Counter() for key in TARGETS}
    eligible, targeted, outside, invalid = 0, 0, 0, 0
    baseline_matches = implemented_matches = counter_matches = counter_checks = 0
    eligible_games = set()
    for row in rows:
        item = {'record_id': row.get('id'), 'game_id': row.get('game_id'), 'round': row.get('round')}
        participants = _participants(row)
        if participants is None or any(not isinstance(p.get('start_snapshot'), dict) for p in participants or []):
            invalid += 1
            results.append(dict(item, status='unresolved_or_missing_start_snapshot'))
            continue
        winner, loser = participants
        wstart, lstart = winner['start_snapshot'], loser['start_snapshot']
        targets = []
        if 45 in _ids(lstart, 'talents'):
            targets.append('talent_45')
        if 105 in _ids(lstart, 'talents'):
            targets.append('talent_105')
        if 2011 in _ids(wstart, 'xian_mo_strategies'):
            targets.append('season_2011')
        if not targets:
            outside += 1
            results.append(dict(item, status='outside_target_effect_scope'))
            continue
        targeted += 1
        item['target_effects'] = targets
        for target in targets:
            coverage[target]['present_records'] += 1
        reasons = _known_exclusions(row, winner, loser)
        outcome = row['outcome']
        delta, recorded = outcome.get('recorded_hp_delta'), outcome.get('recorded_destiny_damage')
        if not _numeric(delta) or not _numeric(recorded) or type(row.get('round')) is not int or row['round'] < 1:
            reasons.append('recorded_outcome_unavailable_or_invalid')
        if reasons:
            exclusions.update(reasons)
            for target in targets:
                coverage[target]['excluded_records'] += 1
            results.append(dict(item, status='excluded', reasons=reasons))
            continue
        try:
            # The winner's 105 cannot affect this settlement. Its counter may
            # nevertheless be required by the general effect-state importer.
            wstate = engine.initialize_player(_effect_player(winner), talent_counters=wstart.get('talentTempDatas'))
            lstate = engine.initialize_player(_effect_player(loser), talent_counters=lstart.get('talentTempDatas'))
            base = ordinary_destiny_damage(row['round'], abs(delta))
            predicted = engine.settle(wstate, lstate, base)
        except (ValueError, UnknownEffectState) as error:
            exclusions['effect_state_unavailable'] += 1
            for target in targets:
                coverage[target]['excluded_records'] += 1
            results.append(dict(item, status='excluded', reasons=['effect_state_unavailable'], detail=str(error)))
            continue
        eligible += 1
        eligible_games.add(row.get('game_id'))
        observed = abs(recorded)
        base_match, implemented_match = base == observed, predicted['life_damage'] == observed
        baseline_matches += base_match
        implemented_matches += implemented_match
        for target in targets:
            coverage[target]['eligible_records'] += 1
            coverage[target]['matching_damage_records'] += implemented_match
            target_id = int(target.rsplit('_', 1)[1])
            coverage[target]['triggered_records'] += any(event.get('effect_id') == target_id for event in predicted['events'])
        result = dict(item, status='compared', base_damage=base, implemented_damage=predicted['life_damage'],
                      recorded_damage_magnitude=observed, baseline_match=base_match,
                      implemented_match=implemented_match, events=predicted['events'],
                      unsupported_effects=predicted.get('unsupported_effects'),
                      validation_kind='conditional_settlement_consistency')
        if 'talent_105' in targets:
            # This is an expected output comparison only. No later state is
            # used to initialize or repair the prediction made above.
            after = loser.get('after_snapshot', {}).get('talentTempDatas')
            if isinstance(after, Mapping) and type(after.get('105', 0)) is int:
                expected = after.get('105', 0)
                actual = predicted['loser']['effect_state']['talent_105_remaining']
                counter_checks += 1
                counter_matches += actual == expected
                result['counter_output_comparison'] = {
                    'input_remaining': lstate['effect_state']['talent_105_remaining'],
                    'predicted_remaining': actual, 'observed_remaining': expected, 'match': actual == expected}
            else:
                result['counter_output_comparison'] = {'status':'observed_output_unavailable'}
        results.append(result)
    comparable_baseline = [row for row in rows if type(row.get('round')) is int and row['round'] > 0
                           and _numeric(row.get('outcome', {}).get('recorded_hp_delta'))
                           and _numeric(row.get('outcome', {}).get('recorded_destiny_damage'))]
    baseline = audit_recorded_damage(comparable_baseline)
    return {'schema_version': 1, 'scope': 'targeted_start_snapshot_settlement_consistency',
            'records_total': len(rows), 'target_records': targeted, 'eligible_records': eligible,
            'excluded_target_records': targeted-eligible, 'outside_target_scope_records': outside,
            'unresolved_records': invalid, 'eligible_whole_games': len(eligible_games),
            'baseline_full_sample': {k:baseline[k] for k in ('records_checked','matching','mismatching')},
            'same_eligible_records': {'base_matching': baseline_matches, 'base_mismatching': eligible-baseline_matches,
                                      'implemented_matching': implemented_matches,
                                      'implemented_mismatching': eligible-implemented_matches},
            'counter_outputs': {'checked':counter_checks, 'matching':counter_matches,
                                'mismatching':counter_checks-counter_matches},
            'coverage': {target:{key:coverage[target][key] for key in
                                ('present_records','eligible_records','excluded_records','matching_damage_records','triggered_records')}
                         for target in TARGETS}, 'exclusion_reasons':dict(exclusions),
            'effect_contract':engine.contract(), 'records':results,
            'current_season_rules_verified':False, 'complete_combat_replayed':False,
            'limitations':[
                'Round snapshots include repeated viewpoints; record counts are not independent battles.',
                'Start snapshot timing is adopted from the normalized replay contract and is not independently certified.',
                'Only recorded HP difference is used; the battle that produced it is not re-simulated.',
                'Known unimplemented settlement interactions are excluded before comparing outcomes; unknown interactions may remain.',
                'After snapshots are expected outputs only; they never initialize or repair effect inputs.',
                'This checks damage and talent 105 remaining uses, not winner reroll rewards or battle-start Qi.',
                'A zero-coverage effect is not validated by this dataset.']}
