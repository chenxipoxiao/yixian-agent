"""Website-source diagnostics; no changes to the frozen v130 input contract.

This is a conditional current-rule experiment, not certified source-version
recovery. Missing private hands remain None and the bridge traps their reads.
"""
from copy import deepcopy
import inspect
from pathlib import Path
from . import full_battle_v130 as engine
from .combat_compiler_view_v81 import isolated_compiler, compiler_modules

ORIGIN = 'website:privatePlayer:immediately_before_authoritative_battle'
EXTENSION = 'website:explicit_start_metadata'
UnresolvedBattle = engine.UnresolvedBattle


def nullable_hand_integer(source, field, minimum=0):
    value = source.get(field)
    if field == 'hand_count' and value is None and source.get('website_hand_unknown') is True:
        return None
    if type(value) is not int or value < minimum or value > 1_000_000:
        raise UnresolvedBattle(f'Explicit valid {field} required')
    return value


def web_params(context, kind, key):
    extension = context.get('start_extensions')
    if not isinstance(extension, dict) or extension.get('origin') != EXTENSION:
        raise UnresolvedBattle('website_start_metadata_required:' + key)
    values = extension.get(kind)
    if not isinstance(values, dict) or key not in values:
        raise UnresolvedBattle('website_start_metadata_unknown:' + key)
    params = values[key].get('commonParams')
    if not isinstance(params, list) or any(type(v) is not int or v < 0 for v in params):
        raise UnresolvedBattle('website_numeric_metadata_required:' + key)
    return params


def web_switches(row, context, facts):
    result = []
    for p, ctx in zip(row['players'], context['players']):
        supplied = ctx.get('website_strategy_parameters', {})
        owned = set(p['candidate_start']['xian_mo_strategies'])
        result.append({int(k): v for k, v in supplied.items() if int(k) in owned})
    return result


def replace_function(module, name, replacements):
    """Rebind a private function only; preserve every other check and branch."""
    text = inspect.getsource(getattr(module, name))
    for old, new in replacements:
        if old not in text:
            raise ValueError('Website adapter source anchor changed: ' + old)
        text = text.replace(old, new)
    exec(compile(text, str(Path(__file__)), 'exec'), vars(module))


def compiler():
    view = isolated_compiler(engine)
    modules = compiler_modules(view)
    modules['yixian.full_battle']._integer = nullable_hand_integer
    modules['yixian.full_battle_v13']._params = web_params
    modules['yixian.full_battle_v124'].original_switches = web_switches
    replace_function(modules['yixian.full_battle_v34'], 'compile_start', [
        ('privateData.xianMoData:preparation_switch', ORIGIN)])
    replace_function(modules['yixian.full_battle_v35'], 'compile_start', [
        ('publicData.lastRoundData.handCards', ORIGIN)])
    replace_function(modules['yixian.full_battle_v124'], 'compile_owned_start', [
        ('from .full_battle_v13 import _params', 'from .website_battles_v132 import web_params as _params')])
    return view


def compile_case(case, view, tables):
    row, context = case['row'], case['combat_context']
    if case['input_conflicts']:
        raise UnresolvedBattle('website_input_conflict:' + ','.join(case['input_conflicts']))
    # Null is retained for missing fate counters; no absent-counter -> zero rule.
    for p in row['players']:
        s = p['candidate_start']
        for fid in (7, 19, 27, 65, 83, 92, 105, 114, 151, 154):
            if fid in s['talents'] and type(s['talentTempDatas'].get(str(fid))) is not int:
                raise UnresolvedBattle('website_required_fate_counter_unknown:' + str(fid))
    result = view.compile_start(deepcopy(row), seed=case['seed'], first_player=case['first_player'],
        game_mode=3, season_mec=10, combat_context=deepcopy(context), tables=tables,
        include_trace=True, max_turns=128)
    result['website_source'] = {'case_id': row['id'], 'rules_under_test': '001.0008.0005',
        'source_rules_version_observed': False, 'source_timing_stratum': case['timing_differences'],
        'source_contract_complete': False, 'training_label_allowed': False}
    return result
