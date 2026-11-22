"""Batch development checks without silently treating skipped battles as tested.

Selection uses starting state, never recorded winners/HP or diagnostic outcomes.
It is a conservative work queue, not a proof that all other rows are unaffected.
Every batch still needs a full development pass before publication.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import importlib
import json
from pathlib import Path
import re

PILOT_SHA = 'b51d9fac1b935b63b64c0c4d0531effd6bdb9a1ab888874f87b02c6d75efb67f'
SCHEMA = 'combat-validation-batch-v1'
ID_FIELDS = ('card_ids', 'fate_ids', 'season_ids', 'permanent_ids', 'character_ids')
GLOBAL_SCOPES = {'shared_engine', 'initialization', 'scheduler', 'damage', 'death',
                 'settlement', 'unknown'}
LOCAL_SCOPES = {'card', 'fate', 'season', 'permanent', 'character'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _ids(values):
    if not isinstance(values, list) or any(type(v) is not int for v in values):
        raise ValueError('Content IDs must be explicit integer lists, including all changed grades')
    return set(values)


def _numeric_values(value):
    """Only called on declared pre-battle extension payloads; over-selection is OK."""
    if type(value) is int:
        return {value}
    if isinstance(value, str) and re.fullmatch(r'-?\d+', value):
        return {int(value)}
    if isinstance(value, list):
        return set().union(*(_numeric_values(v) for v in value)) if value else set()
    if isinstance(value, dict):
        return set().union(*(_numeric_values(v) for v in value.values())) if value else set()
    return set()


def _raw_cards(value):
    if isinstance(value, dict):
        found = _numeric_values(value.get('raw_cards', []))
        for key, child in value.items():
            if key.startswith(('after_', 'recorded_')) or key in {'outcome', 'battle_params'}:
                continue
            found |= _raw_cards(child)
        return found
    if isinstance(value, list):
        return set().union(*(_raw_cards(v) for v in value)) if value else set()
    return set()


def start_content(row, context):
    found = {key: set() for key in ID_FIELDS}
    players = row.get('players')
    if not isinstance(players, list) or len(players) != 2:
        raise ValueError('Both starting players are required for impact selection')
    for player in players:
        start = player.get('candidate_start')
        if not isinstance(start, dict) or not isinstance(start.get('board'), list):
            raise ValueError('Missing starting board; cannot screen this record safely')
        found['character_ids'].add(player['character_id'])
        for key in ('board', 'hand_cards', 'handCards', 'used_keyin_cards'):
            found['card_ids'] |= _numeric_values(start.get(key, []))
        found['fate_ids'] |= _numeric_values(start.get('talents', []))
        for key in ('talentTempDatas', 'talentDatas', 'privateTalentDatas'):
            found['fate_ids'] |= _numeric_values(list(start.get(key, {})))
        for key in ('fate_strategies', 'xian_mo_strategies'):
            found['season_ids'] |= _numeric_values(start.get(key, []))
        found['permanent_ids'] |= _numeric_values(list(start.get('permanentBuffTempDatas', {})))
    for player in context.get('players', []):
        # Includes pinned hand/copy candidates, even when absent from the board.
        found['card_ids'] |= _raw_cards(player)
        # Legacy vase/card metadata may be nested here. Conservative numeric
        # matches may include an extra row; never inspect after_talent_counters.
        found['card_ids'] |= _numeric_values(player.get('start_extensions', {}))
        for key, value in player.items():
            if isinstance(value, dict) and not key.startswith(('after_', 'recorded_')):
                found['season_ids'] |= _numeric_values(value.get('selected_strategy_ids', []))
    return found


def select_records(rows, contexts, changes, *, control_count=4):
    if type(control_count) is not int or not 0 <= control_count <= 32:
        raise ValueError('control_count must be between 0 and 32')
    if not changes or not isinstance(changes, list):
        raise ValueError('Declare the batch changes before checking outcomes')
    declared = []
    force_full = []
    for change in changes:
        if not change.get('name') or not change.get('dependency_review'):
            raise ValueError('Every change needs a name and a dependency review')
        scope = change.get('scope')
        if scope not in GLOBAL_SCOPES | LOCAL_SCOPES:
            raise ValueError('Unknown change scope; use explicit unknown for a full pass')
        identifiers = {k: _ids(change.get(k, [])) for k in ID_FIELDS}
        if scope in GLOBAL_SCOPES or change.get('dependency_complete') is not True:
            force_full.append(change['name'])
        elif not any(identifiers.values()):
            raise ValueError('A local change requires content IDs')
        declared.append((change['name'], identifiers))
    row_ids = [r['id'] for r in rows]
    if len(row_ids) != len(set(row_ids)):
        raise ValueError('Duplicate record IDs')
    if any(r.get('split') != 'train' for r in rows):
        raise ValueError('Development selection accepts training-source records only')
    reasons = {}
    for row in rows:
        if row['id'] not in contexts:
            raise ValueError('Missing combat context: ' + row['id'])
        if force_full:
            reasons[row['id']] = ['full_scope:' + name for name in force_full]
            continue
        content = start_content(row, contexts[row['id']])
        hits = [name + ':' + key for name, ids in declared for key in ID_FIELDS
                if content[key] & ids[key]]
        if hits:
            reasons[row['id']] = hits
    targeted = [r for r in row_ids if r in reasons]
    # A source-ID hash fixes controls without reading results, counts or RNG.
    controls = sorted((r for r in row_ids if r not in reasons),
                      key=lambda r: hashlib.sha256(('batch-control-v1:' + r).encode()).hexdigest())[:control_count]
    for rid in controls:
        reasons[rid] = ['fixed_unrelated_control']
    selected = [r for r in row_ids if r in reasons]
    return {'target_record_ids': targeted, 'control_record_ids': controls,
            'selected_record_ids': selected, 'selection_reasons': reasons,
            'full_required_by_scope': bool(force_full), 'full_scope_changes': force_full,
            'unselected_count': len(rows) - len(selected),
            'selection_is_dependency_proof': False,
            'release_requires_full_pass': True}


def load_sources(pilot, context, baseline):
    if digest(pilot) != PILOT_SHA:
        raise ValueError('Unexpected development source; never substitute a holdout')
    rows = [json.loads(line) for line in Path(pilot).read_text('utf8').splitlines()]
    contexts = json.loads(Path(context).read_text('utf8'))
    previous = json.loads(Path(baseline).read_text('utf8'))
    if previous['source_sha256'] != PILOT_SHA:
        raise ValueError('Baseline source mismatch')
    return rows, contexts, previous


def verify_sources(root, hashes):
    root = Path(root).resolve()
    if not hashes:
        raise ValueError('Freeze the candidate sources before running a batch')
    for name, expected in hashes.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or digest(path) != expected:
            raise ValueError('Frozen dependency changed: ' + name)


def create_plan(root, *, batch_id, pilot, context, baseline, changes, engine_module,
                settlement_module, source_sha256, control_count=4):
    if not re.fullmatch(r'yixian\.full_battle_v\d+(?:r\d+)?', engine_module):
        raise ValueError('Use an explicit versioned complete-battle adapter')
    if not re.fullmatch(r'yixian\.terminal_damage_v\d+', settlement_module):
        raise ValueError('Use an explicit versioned settlement adapter')
    verify_sources(root, source_sha256)
    for name in (engine_module, settlement_module, 'yixian.combat_validation_batch'):
        if name.replace('.', '/') + '.py' not in source_sha256:
            raise ValueError('Candidate source manifest lacks ' + name)
    rows, contexts, previous = load_sources(pilot, context, baseline)
    selection = select_records(rows, contexts, changes, control_count=control_count)
    if previous['context_sha256'] != digest(context) and not selection['full_required_by_scope']:
        raise ValueError('Context changed: declare an initialization/full batch')
    def relative(path):
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    return {'schema': SCHEMA, 'batch_id': batch_id, 'changes': changes,
            'engine_module': engine_module, 'settlement_module': settlement_module,
            'pilot': relative(pilot), 'context': relative(context), 'baseline': relative(baseline),
            'source_sha256': PILOT_SHA, 'context_sha256': digest(context),
            'baseline_sha256': digest(baseline), 'candidate_sources': source_sha256,
            'control_count': control_count, 'selection': selection,
            'source_records': len(rows), 'S2_training_allowed': False}


def compare_previous(cases, excluded, baseline):
    previous = {c['record_id']: c for c in baseline['cases']}
    return {'previous_cases_retested': sum(c['record_id'] in previous for c in cases),
            'previous_matches_lost': [c['record_id'] for c in cases
                if previous.get(c['record_id'], {}).get('all_four_match') and not c['all_four_match']],
            'previous_executable_now_blocked': [c['record_id'] for c in excluded if c['record_id'] in previous],
            'new_executable_record_ids': [c['record_id'] for c in cases if c['record_id'] not in previous],
            'identical_full_case_outputs': sum(previous.get(c['record_id']) == c for c in cases)}


def execute_rows(rows, contexts, engine, settlement):
    """Same start/seed/tiebreak/comparison protocol as the frozen v49 audit."""
    compiled, included, initiatives, excluded = [], [], [], []
    tables = engine.catalogue()
    for row in rows:
        try:
            context = contexts[row['id']]
            initiative = engine.derive_start_initiative(row, game_mode=context['game_mode'])
            first = (None if initiative['candidate_first_index'] is not None else
                     {'p1': 0, 'p2': 1}.get(row['outcome'].get('first_player_snapshot_slot')))
            c = engine.compile_start(row, first_player=first, seed='diagnostic-' + row['id'],
                game_mode=context['game_mode'], season_mec=context['season_mec'],
                combat_context=context, tables=tables)
        except (engine.UnresolvedBattle, ValueError) as error:
            excluded.append({'record_id': row['id'], 'game_id': row['game_id'], 'reason': str(error)})
        else:
            compiled.append(c); included.append(row); initiatives.append(initiative)
    simulated = engine.simulate_batch([c['battle'] for c in compiled]) if compiled else {'results': []}
    cases = []
    for row, c, result, initiative in zip(included, compiled, simulated['results'], initiatives, strict=True):
        if result.get('unresolved_reason'):
            excluded.append({'record_id': row['id'], 'game_id': row['game_id'], 'reason': result['unresolved_reason']})
            continue
        try:
            damage = settlement.calculate_terminal_damage(c, result)
        except ValueError as error:
            damage = {'resolved': False, 'reason': str(error), 'life_damage': None}
        actual = row['outcome']
        signed_damage = (damage['life_damage'] * (1 if result['winner'] == 0 else -1)
                         if damage['resolved'] else None)
        comparisons = {'winner': result['winner'] == {'p1': 0, 'p2': 1}.get(actual['winner_snapshot_slot']),
                       'hp_delta': result['hp_delta'] == actual['recorded_hp_delta'],
                       'turns': result['turns'] == actual['recorded_turn_count'],
                       'destiny_damage': signed_damage == actual['recorded_destiny_damage']}
        cases.append({'record_id': row['id'], 'game_id': row['game_id'], 'round': row['round'],
            'compiled': c, 'simulation': result, 'settlement': damage, 'expected': actual,
            'comparison': comparisons, 'all_four_match': all(comparisons.values()),
            'initiative': initiative, 'initiative_matches_record': c['battle']['first_player'] ==
                {'p1': 0, 'p2': 1}.get(actual['first_player_snapshot_slot'])})
    return cases, excluded, {k: v for k, v in simulated.items() if k != 'results'}


def run_plan(root, plan, *, full=False):
    root = Path(root)
    if plan['schema'] != SCHEMA:
        raise ValueError('Batch schema mismatch')
    verify_sources(root, plan['candidate_sources'])
    for key in ('pilot', 'context', 'baseline'):
        expected = plan['source_sha256' if key == 'pilot' else key + '_sha256']
        if digest(root / plan[key]) != expected:
            raise ValueError('Frozen ' + key + ' changed')
    rows, contexts, baseline = load_sources(root / plan['pilot'], root / plan['context'], root / plan['baseline'])
    selection = select_records(rows, contexts, plan['changes'], control_count=plan['control_count'])
    if selection != plan['selection']:
        raise ValueError('Impact selection changed; register a new plan')
    if baseline['context_sha256'] != plan['context_sha256'] and not selection['full_required_by_scope']:
        raise ValueError('Changed context requires a full batch')
    is_full = bool(full or selection['full_required_by_scope'])
    ids = {r['id'] for r in rows} if is_full else set(selection['selected_record_ids'])
    selected = [r for r in rows if r['id'] in ids]
    cases, excluded, engine = execute_rows(selected, contexts,
        importlib.import_module(plan['engine_module']), importlib.import_module(plan['settlement_module']))
    verify_sources(root, plan['candidate_sources'])
    regression = compare_previous(cases, excluded, baseline)
    summary = {'source_records': len(rows), 'attempted_records': len(selected),
               'fresh_simulated_records': len(cases), 'fresh_all_four_match': sum(c['all_four_match'] for c in cases),
               'fresh_blocked_records': len(excluded), 'untested_records': len(rows) - len(selected),
               'cached_records_counted_as_tested': 0, 'full_development_pass': is_full,
               'batch_release_candidate': is_full and not regression['previous_matches_lost']
                    and not regression['previous_executable_now_blocked'],
               'S2_accepted': False, 'training_labels_emitted': 0,
               'exclusion_counts': dict(Counter(c['reason'].split(':')[0] for c in excluded)),
               'scope': 'full_development_batch' if is_full else 'targeted_development_batch_not_release',
               'limitation': 'No holdout or game-strength claim; partial output never replaces a full coverage report.'}
    return {'schema': SCHEMA, 'batch_id': plan['batch_id'], 'summary': summary,
            'source_sha256': plan['source_sha256'], 'context_sha256': plan['context_sha256'],
            'baseline_sha256': plan['baseline_sha256'], 'engine': engine,
            'regression': regression,
            'cases': cases, 'excluded': excluded}
