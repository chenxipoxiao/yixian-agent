"""V84 batch review: retain v7 selection and report every source-supported delta."""
from copy import deepcopy
import json
from pathlib import Path
from . import combat_validation_batch_v7 as previous
from .combat_report_comparison_v1 import cases_equal

verify_sources = previous.verify_sources

def create_plan(root, **kwargs):
    if kwargs['engine_module'] != 'yixian.full_battle_v84':
        raise ValueError('v8 review is restricted to the declared v84 conversion')
    for name in ['yixian/combat_validation_batch_v8.py','yixian/full_battle_v84.py']:
        if name not in kwargs['source_sha256']:
            raise ValueError('Missing frozen review source: '+name)
    return previous.create_plan(root, **kwargs)

def review_case(old, new):
    """Only204 owners may change. All old inputs except the one binding survive."""
    from .full_battle_v84 import PROOF_SHA
    if cases_equal(old,new):return {'allowed':True,'kind':'identical'}
    try:
        entries=[{'owned':204 in p['fates'],'season17071_owned':17071 in p['season_choices']}
                 for p in old['compiled']['effect_players']]
        if not any(e['owned'] for e in entries):return {'allowed':False,'kind':'nonowner_changed'}
        restored=deepcopy(new['compiled']);meta=restored.pop('mortal_body_v84_context')
        if meta != {'evidence_sha256':PROOF_SHA,'players':entries,
                    'scope':'ordinary ranked no resonance; all previous admission gates retained',
                    'training_label_allowed':False}:return {'allowed':False,'kind':'unexpected_metadata'}
        initial=deepcopy(new['simulation']['initial'])
        for i,e in enumerate(entries):
            if not e['owned']:continue
            expected=int(not e['season17071_owned'])
            if restored['battle']['players'][i].pop('mortal_body_stacks')!=expected or initial[i].pop('mortal_body_stacks')!=expected:
                return {'allowed':False,'kind':'incorrect_binding'}
            declared=restored['declared_components'][i]
            if declared.pop('fate204_combat_conversion') != {**e,'enabled':bool(expected),
                'acquisition_replayed':False,'counter_reapplied':False,'input_hp_or_physique_preadded':False,'evidence_sha256':PROOF_SHA}:
                return {'allowed':False,'kind':'unexpected_declaration'}
            expected_preparation=[x for x in old['compiled']['declared_components'][i]['preparation_fates_not_reapplied'] if x!=204]
            if declared['preparation_fates_not_reapplied']!=expected_preparation:
                return {'allowed':False,'kind':'other_preparation_changed'}
            declared['preparation_fates_not_reapplied']=deepcopy(old['compiled']['declared_components'][i]['preparation_fates_not_reapplied'])
        if not cases_equal({'compiled':old['compiled']},{'compiled':restored}) or initial!=old['simulation']['initial']:
            return {'allowed':False,'kind':'unrelated_start_changed'}
        for key in ['record_id','game_id','round','expected','initiative','initiative_matches_record']:
            if old[key]!=new[key]:return {'allowed':False,'kind':'comparison_or_initiative_changed'}
        def terminal(c):
            s=c['simulation'];return {k:s[k] for k in ['terminated','truncated','winner','turns','hp_delta','used_randomness']}
        before,after=terminal(old),terminal(new)
        if old['all_four_match'] and (before!=after or old['settlement']!=new['settlement']):
            return {'allowed':False,'kind':'previous_matched_terminal_changed'}
        ordinary=deepcopy(new['simulation']);ordinary['initial']=initial
        return {'allowed':True,'kind':'fate204_source_binding','before':before,'after':after,
                'ordinary_simulation_unchanged':ordinary==old['simulation'],
                'settlement_unchanged':old['settlement']==new['settlement'],
                'previous_all_four_match':old['all_four_match'],'current_all_four_match':new['all_four_match']}
    except (KeyError,TypeError,ValueError):return {'allowed':False,'kind':'malformed_change'}

def run_plan(root,plan,*,full=False):
    report=previous.run_plan(root,plan,full=full)
    old=json.loads((Path(root)/plan['baseline']).read_text('utf-8-sig'))
    baseline={c['record_id']:c for c in old['cases']}
    review={c['record_id']:review_case(baseline[c['record_id']],c) for c in report['cases'] if c['record_id'] in baseline}
    disallowed=[rid for rid,r in review.items() if not r['allowed']]
    report['v84_change_review']={'method':'explicit204 ownership and exact starting binding; all nonowners exact; old matched terminal and settlement preserved',
        'disallowed_changes':disallowed,'changed_cases':{rid:r for rid,r in review.items() if r['kind']!='identical'},
        'identical_nonowner_or_owner_cases':sum(r['kind']=='identical' for r in review.values()),
        'human_review_required_before_publication':True}
    r=report['regression'];s=report['summary']
    s['batch_release_candidate']=bool(s['full_development_pass'] and not disallowed and not r['previous_matches_lost']
        and not r['previous_executable_now_blocked'] and len(review)==len(baseline)
        and report['excluded']==old['excluded'])
    return report
