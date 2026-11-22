"""Project the witnessed season-10 refine counter out of single-battle inputs."""
from copy import deepcopy

from . import full_battle_v196 as previous

catalogue = previous.catalogue
derive_start_initiative = previous.derive_start_initiative
UnresolvedBattle = previous.UnresolvedBattle


def compile_start(row, **kwargs):
    candidates = [player.get('candidate_start', {}) for player in row.get('players', [])]
    owners = [
        seat for seat, start in enumerate(candidates)
        if isinstance(start.get('permanentBuffTempDatas'), dict)
        and '20081' in start['permanentBuffTempDatas']
    ]
    if not owners:
        return previous.compile_start(row, **kwargs)
    if (kwargs.get('game_mode'), kwargs.get('season_mec'), row.get('source_rules_version')) != (
        3, 10, '001.0008.0005'
    ):
        raise UnresolvedBattle('refine_counter_20081:unverified_rules')
    projected = deepcopy(row)
    evidence = []
    for seat in owners:
        start = projected['players'][seat]['candidate_start']
        value = start['permanentBuffTempDatas'].pop('20081')
        strategies = start.get('xian_mo_strategies')
        if type(value) is not int or value < 0 or not isinstance(strategies, list) or 22002 not in strategies:
            raise UnresolvedBattle('refine_counter_20081:invalid_or_unbound')
        evidence.append({'seat': seat, 'remaining_refine_uses': value})
    compiled = previous.compile_start(projected, **kwargs)
    compiled['preparation_counter_20081'] = evidence
    return compiled
