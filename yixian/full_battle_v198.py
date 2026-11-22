"""Map positive ShiLiCao stock into the holder's existing plant opening hook."""
from copy import deepcopy
from . import full_battle_v197 as previous

catalogue = previous.catalogue
derive_start_initiative = previous.derive_start_initiative
UnresolvedBattle = previous.UnresolvedBattle


def compile_start(row, **kwargs):
    stocks = []
    for seat, player in enumerate(row.get('players', [])):
        per = player.get('candidate_start', {}).get('permanentBuffTempDatas')
        if isinstance(per, dict) and '10018' in per:
            stocks.append((seat, per['10018']))
    if not stocks:
        return previous.compile_start(row, **kwargs)
    if (kwargs.get('game_mode'), kwargs.get('season_mec'), row.get('source_rules_version')) != (
        3, 10, '001.0008.0005'
    ):
        raise UnresolvedBattle('lose_power_grass:unverified_rules')
    projected = deepcopy(row)
    for seat, value in stocks:
        if type(value) is not int or not 0 < value <= 2147483647:
            raise UnresolvedBattle('lose_power_grass:unverified_stock')
        del projected['players'][seat]['candidate_start']['permanentBuffTempDatas']['10018']
    compiled = previous.compile_start(projected, **kwargs)
    for seat, value in stocks:
        holder = compiled['battle']['players'][seat]
        if 'lose_power_grass_stacks' in holder:
            raise UnresolvedBattle('lose_power_grass:duplicate_source')
        holder['lose_power_grass_stacks'] = value
    return compiled
