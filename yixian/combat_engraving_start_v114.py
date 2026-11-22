"""Original 13002 selected-grid start projection; no result-dependent inputs."""
from copy import deepcopy
from . import full_battle_v113 as source_engine
from . import full_battle_v112 as base_engine
from . import full_battle_v105 as legacy_engine
from .combat_compiler_view_v81 import isolated_compiler, compiler_modules
from .combat_start_context_bindings_v8 import validate_receipt

UnresolvedBattle = source_engine.UnresolvedBattle


def compile_exorcism_start(row, **kwargs):
    receipt = source_engine.extension_contract()['admitted_records'].get(row.get('id'))
    legacy = legacy_engine.extension_contract()['admitted_records'].get(row.get('id'))
    if receipt is None or legacy is None:
        raise UnresolvedBattle('exorcism_v114:original_receipt_required')
    try:
        plain, entries = validate_receipt(row, kwargs.get('combat_context'), receipt, legacy)
    except (ValueError, KeyError, TypeError) as error:
        raise UnresolvedBattle(str(error)) from error
    slots = []
    for entry in entries:
        if entry and 13002 in entry['selected_strategy_ids']:
            if '13002' not in entry['temp_data']:
                raise UnresolvedBattle('exorcism_v114:explicit_grid_required')
            slots.append([{'strategy_id': 13002, 'slot': entry['temp_data']['13002']}])
        else:
            slots.append([])
    if not any(slots):
        raise UnresolvedBattle('exorcism_v114:owner_required')
    view = isolated_compiler(base_engine)
    for name, module in compiler_modules(view).items():
        if name not in ('yixian.full_battle_v105', 'yixian.full_battle_v107'):
            continue
        original = module.project_legacy_inputs

        def project(original_row, original_context, values, _original=original):
            projected, translated, ashes, disabled = _original(original_row, original_context, values)
            for player in projected['players']:
                owned = player['candidate_start']['xian_mo_strategies']
                player['candidate_start']['xian_mo_strategies'] = [x for x in owned if x != 13002]
            return projected, translated, ashes, disabled

        module.project_legacy_inputs = project
    result = view.compile_start(row, **{**kwargs, 'combat_context': plain})
    engraving = result['battle'].setdefault('season_engraving', {'players': [[], []]})
    for i, selected in enumerate(slots):
        engraving['players'][i].extend(selected)
        engraving['players'][i].sort(key=lambda e: e['strategy_id'])
        result['effect_players'][i]['season_choices'] = deepcopy(row['players'][i]['candidate_start']['xian_mo_strategies'])
    result['original_engraving_context_v114'] = {
        'source_evidence_sha256': source_engine.PROOF_SHA, **receipt,
        'scope': 'original_recorded_battle_only', 'policy_observation_allowed': False,
        'counterfactual_reuse_allowed': False, 'training_label_allowed': False,
    }
    return result
