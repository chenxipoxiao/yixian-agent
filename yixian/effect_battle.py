"""Run the supported fate hooks around an actual legacy fixed-card battle.

Uses explicit yisim card IDs. Raw replay IDs and additional legacy fate flags
are deliberately not guessed. This adapter does not certify current-rule combat.
"""
from copy import deepcopy

from .effects import EffectEngine, _ids
from .settlement import ordinary_destiny_damage
from .simulator import simulate_battle
from .season_start import COMBAT_FIELDS, NATIVE_SEASON_IDS
from .talent_adapter import compile_talents, talent_adapter_contract
from .death_fates import DEATH_FATES

SUPPORTED_REFERENCE_CARDS = frozenset([f'111{number:02d}1' for number in range(1,13)] + ['601011'])


def simulate_effect_battle(battle, match_players, *, engine=None, simulator=simulate_battle):
    engine = engine or EffectEngine.from_local()
    if not isinstance(match_players, list) or len(match_players) != 2:
        raise ValueError('Exactly two explicit match-effect states are required')
    source = deepcopy(battle)
    if 'season_runtime' in source:
        raise ValueError('Season runtime ownership must come from match_players, not duplicated battle flags')
    if not isinstance(source.get('players'), list) or len(source['players']) != 2:
        raise ValueError('Exactly two battle players are required')
    allowed = {'character','hp','max_hp','cultivation','round_number','destiny','cards','qi','def','physique','max_physique'}
    for index, combatant in enumerate(source['players']):
        if set(combatant) - allowed:
            raise ValueError('Extra legacy effect flags are not allowed in this subset adapter')
        if any(card not in SUPPORTED_REFERENCE_CARDS for card in combatant.get('cards', [])):
            raise ValueError('This effect adapter only supports the explicit basic-cloud/practice card subset; combat destiny changes are not yet separated')
        if match_players[index].get('life') != combatant.get('destiny'):
            raise ValueError('Battle destiny must match persistent match life')
    number = source['players'][0]['round_number']
    if number != source['players'][1]['round_number']:
        raise ValueError('Both players must use the same round number')
    states = deepcopy(match_players)
    cleanup = []
    for index, player in enumerate(states):
        rerolls = player.get('rerolls')
        if type(rerolls) is not int or rerolls < 0:
            raise ValueError('Explicit nonnegative rerolls are required')
        if rerolls > 25:
            player['rerolls'] = 25
            cleanup.append({'player_index':index, 'before':rerolls, 'after':25, 'phase':'battle_start'})
    inputs = [dict(deepcopy(player), **{k:v for k,v in source['players'][i].items()
              if k in COMBAT_FIELDS or k == 'cultivation'}) for i,player in enumerate(states)]
    started = engine.battle_start(*inputs)
    native = []
    for player in started['players']:
        owned = _ids(player,'season_choices') & NATIVE_SEASON_IDS
        native.append({'ids':sorted(owned), 'disabled_ids':sorted(owned & set(player['effect_state']['disabled_season_ids']))})
    has_native = any(p['ids'] for p in native)
    if has_native:
        source['season_runtime'] = native
    compiled = []
    for index, player in enumerate(started['players']):
        source['players'][index].update({k:v for k,v in player.items() if k in COMBAT_FIELDS})
        fates = [x for x in player.get('fates',[]) if type(x) is int and x not in DEATH_FATES | {45,105}]
        talents = compile_talents(fates, player.get('talent_counters'), player=source['players'][index])
        compiled.append(talents)
        for field, amount in talents['player_fields'].items():
            source['players'][index][field] = source['players'][index].get(field,0)+amount
    result = simulator(source)
    if (type(result.get('terminated')) is not bool or type(result.get('truncated')) is not bool
            or result['terminated'] == result['truncated']):
        raise ValueError('Battle did not report a valid terminal boundary')
    winner = result.get('winner')
    if winner is not None and (type(winner) is not int or winner not in (0, 1)):
        raise ValueError('Invalid battle winner')
    usable = result['terminated'] and not result['truncated'] and winner is not None
    settlement = None
    if usable:
        loser = 1-winner
        delta = result['players'][winner]['hp']-result['players'][loser]['hp']
        base = ordinary_destiny_damage(number, delta)
        settled = engine.settle(states[winner], states[loser], base)
        states[winner], states[loser] = settled['winner'], settled['loser']
        states[loser]['life'] -= settled['life_damage']
        settlement = {'base_damage': base, 'life_damage': settled['life_damage'],
                      'events': settled['events'], 'unsupported_effects': settled['unsupported_effects'],
                      'pending_actions': settled['pending_actions'], 'complete_resolution': settled['complete_resolution']}
        usable = usable and settled['complete_resolution']
    # A terminal result may still omit an unimplemented effect. Such diagnostic
    # simulations are not admitted as training labels.
    unknown = any(c['unsupported'] for c in compiled)
    unknown |= any(any(type(f) is not int for f in p.get('fates',[])) for p in states)
    unknown |= any(set(c['unsupported_season']) - NATIVE_SEASON_IDS for c in started['unsupported_effects'])
    start_ids = {event['effect_id'] for event in started['events']}
    # Direct attribute writes also do not dispatch one seasonal start effect
    # through another (e.g. hexproof reacting to an incoming injury aura).
    missing_cross_effect_dispatch = (any(c['player_fields'] for c in compiled) and (bool(started['events']) or has_native)
                                     or has_native and bool(started['events']) or len(start_ids)>1)
    usable = usable and not unknown and not missing_cross_effect_dispatch
    # yisim also performs its own legacy destiny calculation. That output is
    # never applied to our match state; this adapter uses one explicit settlement.
    combat = deepcopy(result)
    for player in combat.get('players', []):
        player.pop('destiny', None)
    return {'scope': 'supported_effects_with_legacy_fixed_card_battle',
            'effect_contract': engine.contract(), 'current_season_verified': False,
            'talent_adapter_contract': talent_adapter_contract(), 'regular_fate_components': compiled,
            'unimplemented_effects_present': bool(unknown),
            'missing_cross_effect_dispatch': missing_cross_effect_dispatch,
            'label_scope': 'restricted_legacy_reference_only_not_current_season_or_full_match',
            'ordinary_season_start_interleaving_verified': False,
            'full_match_agent': False, 'label_usable': usable,
            'starting_qi': [p['qi'] for p in started['players']], 'start_events': started['events'],
            'reroll_overflow_cleanup': cleanup, 'supported_reference_cards': sorted(SUPPORTED_REFERENCE_CARDS),
            'unsupported_effects': started['unsupported_effects'],
            'combat': combat, 'settlement': settlement, 'match_players': states,
            'legacy_destiny_settlement_discarded': True}
