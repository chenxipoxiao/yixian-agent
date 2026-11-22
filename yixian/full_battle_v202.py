"""Compose frozen prebattle hand receipts with earlier preparation validators."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from . import full_battle_v201 as previous
from .combat_compiler_view_v81 import compiler_modules, isolated_compiler
from .combat_season_inputs_v124 import validate_inputs
from .combat_start_context_bindings_v6 import validate_receipt
from .full_battle_v45 import digest_json

catalogue = previous.catalogue
derive_start_initiative = previous.derive_start_initiative
UnresolvedBattle = previous.UnresolvedBattle


@lru_cache(maxsize=1)
def _records():
    path = Path(__file__).resolve().parents[1] / 'data/inspection/native-hand-receipts-v202.json'
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != 'b5299c3b2124c72bbfeebab16a15a4d95e5329e321da25414c76c7b79a66de19':
        raise UnresolvedBattle('hand_receipts:source_changed')
    return json.loads(raw)


def compile_start(row, **kwargs):
    record = _records().get(row.get('id'))
    if record is None:
        return previous.compile_start(row, **kwargs)
    start = {k: v for k, v in row.items() if k != 'outcome'}
    context = deepcopy(kwargs.get('combat_context'))
    if (kwargs.get('game_mode'), kwargs.get('season_mec')) != (3, 10) or (
            digest_json(start), digest_json(context)) != (record['start'], record['context']):
        raise UnresolvedBattle('hand_receipts:recorded_start_changed')
    for hand in record['hands']:
        player = context['players'][hand['seat']]
        if hand['field'] in player:
            raise UnresolvedBattle('hand_receipts:duplicate')
        player[hand['field']] = deepcopy(hand['receipt'])

    def legacy_validator(validate):
        def verify(row, enriched, expected):
            original = deepcopy(enriched)
            for hand in record['hands']:
                if original['players'][hand['seat']].pop(hand['field'], None) != hand['receipt']:
                    raise UnresolvedBattle('hand_receipts:projection_changed')
            return validate(row, original, expected)
        return verify

    view = isolated_compiler(previous)
    for module in compiler_modules(view).values():
        for name in ('validate_inputs', 'validate_receipt', 'validate_legacy'):
            validate = getattr(module, name, None)
            if validate in (validate_inputs, validate_receipt):
                setattr(module, name, legacy_validator(validate))
    from . import full_battle_v180
    compiler_modules(view)['yixian.full_battle_v180'].validate_registration = legacy_validator(full_battle_v180.validate_registration)
    return view.compile_start(start, **{**kwargs, 'combat_context': context})

