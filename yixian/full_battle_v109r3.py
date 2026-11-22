"""Admit the audited preparation capacity key without converting it to combat state."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
from . import full_battle_v108r3 as previous
from .combat_compiler_view_v81 import isolated_compiler, compiler_modules

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/current-consumption-capacity-v109r3.json'
PROOF_SHA = '2025dfee63d86daf398d0ee1cc8f63a46f57877e6c7b6383ca9988a7d1a50f22'
UnresolvedBattle = previous.UnresolvedBattle
catalogue = previous.catalogue
derive_start_initiative = previous.derive_start_initiative


def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('capacity_v109r3:evidence_changed')
    facts = json.loads(raw)
    for name, digest in facts['source_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise UnresolvedBattle('capacity_v109r3:source_changed:' + name)
    return facts


def owns_content(row):
    return any('10049' in p['candidate_start'].get('permanentBuffTempDatas', {}) or 2015 in p['candidate_start'].get('xian_mo_strategies', [])
               for p in row['players'])


def compile_start(row, **kwargs):
    extension_contract()
    if not owns_content(row):return previous.compile_start(row, **kwargs)
    return compile_content_start(row, **kwargs)


def compile_content_start(row, **kwargs):
    if 'tables' not in kwargs:
        kwargs['tables'] = catalogue()
    # Preserve the public catalogue and all original ownership/receipt inputs.
    tables = list(kwargs['tables'])
    season = dict(tables[3])
    if season[2015] != extension_contract()['season2015']['config']:
        raise UnresolvedBattle('capacity_v109r3:season_config_changed')
    season[2015] = {**season[2015], 'isBattleEffect': False}
    tables[3] = season
    kwargs['tables'] = tuple(tables)
    values = []
    for player in row['players']:
        buffs = player['candidate_start'].get('permanentBuffTempDatas')
        if not isinstance(buffs, dict):
            raise UnresolvedBattle('capacity_v109r3:explicit_permanent_map_required')
        present = '10049' in buffs
        value = buffs.get('10049')
        if present and (type(value) is not int or not -(2**31) <= value < 2**31):
            raise UnresolvedBattle('capacity_v109r3:invalid_signed_value')
        values.append({'present': present, 'value': value})
    if isinstance(kwargs.get('combat_context'), dict) and 'cloud_sword_record' in kwargs['combat_context']:
        raise UnresolvedBattle('capacity_v109r3:cloud_leaf_combination_pending')
    # Clone the full compiler graph so every source-bound receipt still sees
    # the exact original row, and all previous public entrypoints stay frozen.
    view = isolated_compiler(previous)
    leaf = compiler_modules(view)['yixian.full_battle']
    leaf.PERMANENT_FIELDS = leaf.PERMANENT_FIELDS | {'10049'}
    result = view.compile_start(row, **kwargs)
    result['consumption_capacity_context_v109r3'] = {
        'evidence_sha256': PROOF_SHA,
        'permanent10049': deepcopy(values),
        'season2015_owned': [2015 in p['candidate_start']['xian_mo_strategies'] for p in row['players']],
        'extra_max_hp_modifier_preserved': True,
        'preparation_effect_reapplied': False,
        'source_row_rewritten': False,
        'cross_round_rules_implemented': False,
        'training_label_allowed': False,
    }
    return result


def simulate_batch(battles, *, timeout=90):
    extension_contract()
    result = previous.simulate_batch(battles, timeout=timeout)
    result['adapter_contract'] = {
        **result['adapter_contract'],
        'schema': 'complete-single-battle-diagnostic-v109r3',
        'evidence_sha256': PROOF_SHA,
        'training_label_allowed': False,
    }
    return result
