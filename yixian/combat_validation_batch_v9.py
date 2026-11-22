"""Review the combined v85 card-body correction, with unchanged starting inputs."""
import json
from pathlib import Path
from . import combat_validation_batch_v7 as previous
from .combat_report_comparison_v1 import cases_equal
verify_sources = previous.verify_sources

def create_plan(root, **kwargs):
    if kwargs['engine_module'] != 'yixian.full_battle_v85':
        raise ValueError('v9 review requires v85 card bodies')
    for name in ['yixian/combat_validation_batch_v9.py','yixian/full_battle_v85.py']:
        if name not in kwargs['source_sha256']:
            raise ValueError('Missing frozen source: '+name)
    return previous.create_plan(root, **kwargs)

def terminal(case):
    return {k:case['simulation'][k] for k in
            ['terminated','truncated','winner','turns','hp_delta','used_randomness']}

def review_case(old, new, *, selected):
    if cases_equal(old,new):return {'allowed':True,'kind':'identical'}
    if not selected:return {'allowed':False,'kind':'unselected_changed'}
    if not cases_equal({'compiled':old['compiled']},{'compiled':new['compiled']}):
        return {'allowed':False,'kind':'starting_input_changed'}
    if old['simulation']['initial']!=new['simulation']['initial']:
        return {'allowed':False,'kind':'runtime_initial_changed'}
    for key in ['record_id','game_id','round','expected','initiative','initiative_matches_record']:
        if old[key]!=new[key]:return {'allowed':False,'kind':'comparison_changed'}
    before,after=terminal(old),terminal(new)
    if old['all_four_match'] and (before!=after or old['settlement']!=new['settlement']):
        return {'allowed':False,'kind':'previous_matched_terminal_changed'}
    return {'allowed':True,'kind':'current_card_body','before':before,'after':after,
            'previous_all_four_match':old['all_four_match'],'current_all_four_match':new['all_four_match'],
            'settlement_unchanged':old['settlement']==new['settlement']}

def run_plan(root, plan, *, full=False):
    report=previous.run_plan(root,plan,full=full)
    old=json.loads((Path(root)/plan['baseline']).read_text('utf-8-sig'))
    baseline={c['record_id']:c for c in old['cases']}
    targets=set(plan['selection']['target_record_ids'])
    review={c['record_id']:review_case(baseline[c['record_id']],c,selected=c['record_id'] in targets)
            for c in report['cases'] if c['record_id'] in baseline}
    disallowed=[rid for rid,r in review.items() if not r['allowed']]
    report['v85_change_review']={'method':'Starting raw-card/hand/dependency union; exact start and comparison preservation; unchanged non-targets; all previous matched terminals and settlement retained.',
        'disallowed_changes':disallowed,'changed_cases':{rid:r for rid,r in review.items() if r['kind']!='identical'},
        'identical_cases':sum(r['kind']=='identical' for r in review.values()),
        'source_and_difference_review_required_before_publication':True}
    r=report['regression'];s=report['summary']
    s['batch_release_candidate']=bool(s['full_development_pass'] and not disallowed and not r['previous_matches_lost']
        and not r['previous_executable_now_blocked'] and len(review)==len(baseline)
        and report['excluded']==old['excluded'])
    return report
