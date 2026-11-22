"""Full comparison with strictly additive original-record parameter bindings."""
from copy import deepcopy
import json
from pathlib import Path
from . import combat_validation_batch_v7 as previous
from .combat_report_comparison_v1 import cases_equal
verify_sources=previous.verify_sources
create_plan=previous.create_plan

def review_case(old,new,*,admitted):
    if cases_equal(old,new):return {'allowed':True,'kind':'identical'}
    if not admitted:return {'allowed':False,'kind':'unbound_record_changed'}
    c=deepcopy(new['compiled']);payload=c['battle'].pop('debuff_parameters',None)
    metadata=c.pop('debuff_parameter_context_v87r2',None)
    if payload is None or metadata is None or not cases_equal({'compiled':old['compiled']},{'compiled':c}):
        return {'allowed':False,'kind':'ordinary_start_changed'}
    for key in ['record_id','game_id','round','expected','initiative','initiative_matches_record']:
        if old[key]!=new[key]:return {'allowed':False,'kind':'comparison_changed'}
    if old['simulation']['initial']!=new['simulation']['initial']:
        return {'allowed':False,'kind':'runtime_initial_changed'}
    before={k:old['simulation'][k] for k in ['winner','turns','hp_delta','terminated','truncated']}
    after={k:new['simulation'][k] for k in before}
    if old['all_four_match'] and (before!=after or old['settlement']!=new['settlement']):
        return {'allowed':False,'kind':'previous_match_changed'}
    m=new['simulation'].get('debuff_parameters_v87r2',{})
    if m.get('consumed')!=len(payload['stream']) or m.get('record_conditioned') is not True:
        return {'allowed':False,'kind':'incomplete_parameter_use'}
    return {'allowed':True,'kind':'recorded_parameter_condition','before':before,'after':after,
        'previous_all_four_match':old['all_four_match'],'current_all_four_match':new['all_four_match'],
        'parameter_count':m['consumed'],'old_used_randomness':old['simulation']['used_randomness']}

def run_plan(root,plan,*,full=False):
    report=previous.run_plan(root,plan,full=full)
    old=json.loads((Path(root)/plan['baseline']).read_text('utf-8-sig'))
    from .full_battle_v87r2 import extension_contract
    admitted=extension_contract()['admitted_records'];baseline={c['record_id']:c for c in old['cases']}
    review={c['record_id']:review_case(baseline[c['record_id']],c,admitted=c['record_id'] in admitted)
        for c in report['cases'] if c['record_id'] in baseline}
    bad=[rid for rid,r in review.items() if not r['allowed']]
    report['v87r2_change_review']={'disallowed_changes':bad,
        'changed_cases':{rid:r for rid,r in review.items() if r['kind']!='identical'},
        'identical_cases':sum(r['kind']=='identical' for r in review.values()),
        'source_and_difference_review_required_before_publication':True}
    regression=report['regression']
    report['summary']['batch_release_candidate']=bool(report['summary']['full_development_pass'] and not bad
        and not regression['previous_matches_lost'] and not regression['previous_executable_now_blocked']
        and len(review)==len(baseline) and report['excluded']==old['excluded'])
    return report
