"""Allow only bound additive v77 preparation evidence before targeted + full checking."""
from copy import deepcopy
import json
from pathlib import Path
from . import combat_validation_batch as v1
from .combat_validation_batch import *

from .preparation_context_v77 import validate_additions as validate_switch_context

def create_plan(root,*,previous_context=None,**kwargs):
 if previous_context is None:return v1.create_plan(root,**kwargs)
 root=Path(root);context=Path(kwargs['context']);context=context if context.is_absolute() else root/context
 oldpath=root/previous_context
 spec={**kwargs,'context':oldpath};plan=v1.create_plan(root,**spec)
 rows,new,previous=v1.load_sources(root/plan['pilot'],context,root/plan['baseline'])
 old=json.loads(oldpath.read_text('utf8'));selection=v1.select_records(rows,new,kwargs['changes'],control_count=kwargs.get('control_count',4))
 added=validate_switch_context(rows,old,new,selection['target_record_ids'])
 plan.update(context=context.resolve().relative_to(root.resolve()).as_posix(),context_sha256=v1.digest(context),selection=selection,
  additive_context={'previous_context':previous_context,'previous_sha256':v1.digest(oldpath),'additions':added})
 if 'yixian/combat_validation_batch_v5.py' not in plan['candidate_sources']:raise ValueError('Freeze additive validator')
 return plan

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
    additive_verified=False
    if 'additive_context' in plan:
        a=plan['additive_context'];p=root/a['previous_context']
        if digest(p)!=a['previous_sha256'] or baseline['context_sha256']!=a['previous_sha256']:raise ValueError('Previous context changed')
        old=json.loads(p.read_text('utf8'))
        if validate_switch_context(rows,old,contexts,selection['target_record_ids'])!=a['additions']:raise ValueError('Additive context changed')
        additive_verified=True
    if baseline['context_sha256'] != plan['context_sha256'] and not selection['full_required_by_scope'] and not additive_verified:
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
