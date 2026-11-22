"""Audited seasonal battle-start components on temporary combat state.

The order within one owner follows the extracted OnBattleStart IL. Cross-owner
and ordinary-fate ordering still needs replay calibration. Acquisition changes
are not reapplied to an imported battle snapshot (notably strategy 3002).
"""
from copy import deepcopy

IMPLEMENTED_SEASON_START_IDS = frozenset({1001,1002,1003,1004,1006,3001,3002,
    7036,7066,7078,7094,7095,7096,7098,7103,7105,7123,15018})
NATIVE_SEASON_IDS = frozenset({1005,1007,1008,1009,3004,3011,3012})
TOGGLEABLE_SEASON_IDS = frozenset({1001,1002,1003,1004,1005,1006,1007,1008,1009,7036,7094})
PARTIAL_SEASON_IDS = frozenset({3002})
DEFAULT_PARAMETERS = {1001:[2],1002:[1],1003:[15],1004:[3],1006:[15],3001:[1],3002:[1,4],
    7036:[2,9],7066:[2],7078:[5],7094:[1,2],7095:[8],7096:[4],7098:[4],
    7103:[10],7105:[2],7123:[50,15],15018:[12]}
COMBAT_FIELDS = frozenset({'hp','max_hp','qi','def','increase_atk','internal_injury',
    'decrease_atk','guard_up','hexproof','star_power','penetrate','styx',
    'activate_wood_spirit_stacks','activate_fire_spirit_stacks',
    'activate_earth_spirit_stacks','activate_metal_spirit_stacks'})
# The client checks fire before wood, earth and metal; use evidence order, not ID.
START_ORDER = (1001,1002,1003,1004,1006,3001,3002,7098,7066,7095,7096,
               7036,7078,7094,7103,7105,7123,15018)


def _integer(player, key, *, default=None, minimum=0):
    value = player.get(key, default)
    if type(value) is not int or value < minimum:
        raise ValueError(f'Season effect requires explicit integer {key} >= {minimum}')
    return value


def _add(player, field, amount):
    player[field] = _integer(player, field, default=0) + amount


def _hp(player, amount):
    hp, maximum = _integer(player,'hp'), _integer(player,'max_hp',minimum=1)
    # These hooks change current and maximum health by an equal amount.
    # No combat-end cleanup or persistent health is committed here.
    if hp+amount <= 0 or maximum+amount <= 0:
        raise ValueError('Season HP hook reaches an uncalibrated lethal start boundary')
    player['hp'], player['max_hp'] = hp+amount, maximum+amount


def apply_season_start(players, owned_ids, *, parameters=None):
    """Copy two players and execute only registered battle-start components."""
    if len(players) != 2 or len(owned_ids) != 2:
        raise ValueError('Exactly two players and ownership sets required')
    players = deepcopy(players)
    params = DEFAULT_PARAMETERS if parameters is None else parameters
    events = []
    for owner in range(2):
        me, enemy = players[owner], players[1-owner]
        disabled = set(me.get('effect_state',{}).get('disabled_season_ids',[]))
        for identifier in START_ORDER:
            if identifier not in owned_ids[owner]:
                continue
            if identifier in disabled and identifier != 7036:
                continue
            before = [{k:deepcopy(v) for k,v in p.items() if k in COMBAT_FIELDS} for p in players]
            p = params[identifier]
            if identifier in (1001,1002,1004):
                field = {1001:'qi',1002:'increase_atk',1004:'internal_injury'}[identifier]
                for target in players:
                    _add(target,field,p[0])
            elif identifier in (1003,1006):
                for target in players:
                    amount = _integer(target,'hp') * p[0] // 100
                    _hp(target,amount if identifier == 1003 else -amount)
            elif identifier == 3001:
                _add(enemy,'decrease_atk',p[0])
            elif identifier == 3002:
                _add(me,'guard_up',p[0])
            elif identifier == 7036:
                if identifier not in disabled:
                    _add(me,'hexproof',p[0])
                me['hp'] = min(_integer(me,'max_hp',minimum=1),_integer(me,'hp')+p[1])
            elif identifier == 7066:
                _add(me,'activate_wood_spirit_stacks',1)
                _add(me,'qi',p[0])
            elif identifier == 7078:
                _add(me,'star_power',1+int(_integer(me,'cultivation') >= _integer(enemy,'cultivation')+p[0]))
            elif identifier == 7094:
                _add(me,'increase_atk',p[0]); _add(me,'internal_injury',p[1])
            elif identifier == 7095:
                _add(me,'activate_earth_spirit_stacks',1); _add(me,'def',p[0])
            elif identifier == 7096:
                _add(me,'activate_metal_spirit_stacks',1); _add(me,'penetrate',p[0])
            elif identifier == 7098:
                _add(me,'activate_fire_spirit_stacks',1); _hp(enemy,-p[0])
            elif identifier == 7103:
                _hp(me,_integer(me,'hp')//p[0])
            elif identifier == 7105:
                _add(me,'styx',p[0])
            elif identifier == 7123:
                if _integer(me,'life') <= p[0]:
                    _hp(me,_integer(me,'hp')*p[1]//100)
            elif identifier == 15018:
                if isinstance(me.get('hand_cards'),list):
                    count = len(me['hand_cards'])
                elif type(me.get('hand_card_count')) is int and me['hand_card_count'] >= 0:
                    count = me['hand_card_count']
                else:
                    raise ValueError('Season 15018 requires an explicit current hand')
                if count:
                    _hp(me,_integer(me,'hp')*p[0]//100)
            after = [{k:deepcopy(v) for k,v in player.items() if k in COMBAT_FIELDS} for player in players]
            events.append({'phase':'battle_start','effect_id':identifier,'owner_index':owner,
                           'before':before,'after':after,'scope':'battle_start_component',
                           'qi_before':[b.get('qi',0) for b in before],
                           'qi_after':[a.get('qi',0) for a in after]})
    return {'players':players,'events':events,'cross_effect_order_verified':False}
