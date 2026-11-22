"""Bind archived 7135 preparation switches to exact native starts."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from . import full_battle_v203 as previous
from .full_battle_v45 import digest_json

catalogue = previous.catalogue
derive_start_initiative = previous.derive_start_initiative
UnresolvedBattle = previous.UnresolvedBattle


@lru_cache(maxsize=1)
def _records():
    path = Path(__file__).resolve().parents[1] / 'data/inspection/native-regen-switch-v204.json'
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != 'ab565eca636b4ea4d8c39e35e6b8f29664dadd5598844eb92d4d8499e97a9478':
        raise UnresolvedBattle('regen_switch:source_changed')
    return json.loads(raw)


def compile_start(row, **kwargs):
    record = _records().get(row.get('id'))
    if record is None:
        return previous.compile_start(row, **kwargs)
    start = {key: value for key, value in row.items() if key != 'outcome'}
    context = kwargs.get('combat_context')
    if (kwargs.get('game_mode'), kwargs.get('season_mec')) != (3, 10) or (
            digest_json(start), digest_json(context)) != (record['start'], record['context']):
        raise UnresolvedBattle('regen_switch:recorded_start_changed')
    enriched = deepcopy(context)
    player = enriched['players'][record['seat']]
    if 'regen_opening_switch' in player:
        raise UnresolvedBattle('regen_switch:duplicate')
    player['regen_opening_switch'] = deepcopy(record['receipt'])
    return previous.compile_start(start, **{**kwargs, 'combat_context': enriched})
