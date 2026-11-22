"""Train-replay diagnostics for the ordinary Dragon Scale damage component.

The observed HP difference supplies the base damage; this is not a re-simulated
battle or full-rule calibration. After-state fields are expected outputs only.
"""
from collections import Counter
from collections.abc import Mapping

from .effects import EffectEngine
from .effect_validation import _participants, _ids, _numeric, _known_exclusions
from .settlement import ordinary_destiny_damage
from .order_data import CHARACTER, VERSION


def audit_dragon_scale(records, *, engine=None):
    engine = engine or EffectEngine()
    results, observations = [], []
    exclusions, transitions = Counter(), Counter()
    targeted = 0
    for row in records:
        identity = {key: row.get(key) for key in ('id', 'game_id', 'round')}
        participants = _participants(row)
        if participants is None:
            continue
        winner, loser = participants
        for player in row['players']:
            start, after = player.get('start_snapshot', {}), player.get('after_snapshot', {})
            if (player.get('character_id') != CHARACTER or player.get('is_ai') is not False
                    or 27 not in _ids(start, 'talents')):
                continue
            before_map, after_map = start.get('talentTempDatas'), after.get('talentTempDatas')
            before = before_map.get('27', 'absent') if isinstance(before_map, Mapping) else 'dictionary_missing'
            after_value = after_map.get('27', 'absent') if isinstance(after_map, Mapping) else 'dictionary_missing'
            transitions[f'{before}->{after_value}'] += 1
            observations.append(dict(identity, slot=player['snapshot_slot'],
                won=player['snapshot_slot'] == winner['snapshot_slot'],
                start_life=start.get('destiny'), after_life=after.get('destiny'),
                raw_counter_before=before, raw_counter_after=after_value,
                start_board=start.get('board'), after_board=after.get('board'),
                counter_meaning_verified=False, after_fields_used_as_prediction_inputs=False))
        start = loser.get('start_snapshot', {})
        if (loser.get('character_id') != CHARACTER or loser.get('is_ai') is not False
                or 27 not in _ids(start, 'talents')):
            continue
        targeted += 1
        reasons = [reason for reason in _known_exclusions(row, winner, loser)
                   if reason != 'loser_unimplemented_settlement_fate:27']
        if row.get('source_rules_version') != VERSION:
            reasons.append('outside_pinned_game_version')
        if type(start.get('destiny')) is not int or start['destiny'] <= 0:
            reasons.append('pre_battle_life_unavailable_or_eliminated')
        for player in (winner, loser):
            side = 'winner' if player is winner else 'loser'
            context = player.get('audit_context', {})
            if context.get('is_mirror') is not False:
                reasons.append(side+'_mirror_or_unknown_mirror_status')
            # HasTalentResonance/IsTalentResonanceEffective read this private
            # selection, not a nonexistent lastRoundData resonance flag map.
            # Current selection is used only for conservative exclusion.
            selection = context.get('resonance_selected')
            if type(selection) is not int or selection != 0:
                reasons.append(side+'_resonance_selected_or_unknown')
        outcome = row['outcome']
        delta, observed = outcome.get('recorded_hp_delta'), outcome.get('recorded_destiny_damage')
        if (not _numeric(delta) or not _numeric(observed) or type(row.get('round')) is not int
                or row['round'] < 1):
            reasons.append('recorded_outcome_unavailable_or_invalid')
        if reasons:
            exclusions.update(reasons)
            results.append(dict(identity, status='excluded', reasons=reasons))
            continue
        # Project only the declared damage chain, not unknown complete fates.
        # A victory reroll balance is required when 2011 is present, and its
        # reward is never scored by this cap-only audit.
        wstart = winner['start_snapshot']
        win = {'fates': [], 'season_choices': [2011] if 2011 in _ids(wstart, 'xian_mo_strategies') else [],
               'rerolls': wstart.get('rerolls', 0)}
        lose = {'fates': sorted(_ids(start, 'talents') & {27, 45, 105}),
                'season_choices': [], 'life': start['destiny'], 'is_mirror': False}
        lose = engine.initialize_player(lose, talent_counters=start.get('talentTempDatas'))
        base = ordinary_destiny_damage(row['round'], abs(delta))
        predicted = engine.settle(win, lose, base)
        results.append(dict(identity, status='compared', base_damage=base,
            predicted_damage=predicted['life_damage'], recorded_damage=abs(observed),
            baseline_match=base == abs(observed), component_match=predicted['life_damage'] == abs(observed),
            cap_triggered=any(e.get('effect_id') == 27 for e in predicted['events']),
            events=predicted['events'], training_label_allowed=False))
    compared = [r for r in results if r['status'] == 'compared']
    return {'scope': 'ordinary_dragon_scale_conditional_damage_consistency',
            'targeted_losing_snapshots': targeted, 'compared_snapshots': len(compared),
            'compared_games': len({r['game_id'] for r in compared}),
            'excluded_snapshots': targeted-len(compared), 'exclusion_reasons': dict(exclusions),
            'baseline_matches': sum(r['baseline_match'] for r in compared),
            'component_matches': sum(r['component_match'] for r in compared),
            'component_mismatches': sum(not r['component_match'] for r in compared),
            'cap_triggered_snapshots': sum(r['cap_triggered'] for r in compared),
            'counter_observation_snapshots': len(observations), 'counter_transitions': dict(transitions),
            'counter_semantics_verified': False, 'upgrade_reward_implemented': False,
            'records': results, 'counter_observations': observations,
            'training_labels_emitted': 0, 'whole_fate_implemented': False,
            'complete_combat_replayed': False, 'current_server_calibration_passed': False,
            'limitations': ['Recorded HP difference is an input; winner and combat trajectory are not simulated.',
                           'Only known settlement confounders are excluded; unknown effects may remain.',
                           'Snapshot timing is not independently certified.',
                           'Counter and board after-states are evidence only, not policy or initialization inputs.',
                           'No post-battle upgrade selection, reward, or usage-state transition is implemented.']}
