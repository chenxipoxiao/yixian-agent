"""Read only a previously frozen, train-only whole-game source selection."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import argparse,hashlib,json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from yixian.combat_calibration import iter_selected_records
from yixian.combat_cohort_projection_v2 import project_record
from yixian.memory import Memory
read=lambda p:json.loads(Path(p).read_text('utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
    with p.open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def audit(plan_path,out):
    plan=read(plan_path)
    if plan['status']!='metadata_only_frozen_not_executed':raise ValueError('Require an unexecuted frozen source selection')
    for p,h in plan['source_sha256'].items():
        if sha(ROOT/p)!=h:raise ValueError('Changed source:'+p)
    selected=plan['selected_sources'];groups=defaultdict(list)
    if len({s['game_id'] for s in selected})!=plan['selected_games']:raise ValueError('Duplicate game selection')
    for source in selected:
        if source['split']!='train' or source['game_id'] in plan['excluded_prior_game_ids']:raise ValueError('Invalid new training group')
        groups[source['archive']].append(source)
    files=['tools/audit_training_cohort_v2.py','yixian/combat_cohort_projection_v2.py','yixian/combat_calibration.py',
           'yixian/replays.py','yixian/order_data.py','tests/test_combat_cohort_projection_v2.py']
    hashes={p:sha(ROOT/p) for p in files}
    out.mkdir(exist_ok=False,parents=True)
    frozen={**plan,'consumed_selection_path':str(plan_path),'selection_plan_sha256':sha(plan_path),
        'extractor_source_sha256':hashes,'projection_contract':'start_only_cohort_v2_no_current_private_fallback',
        'created_at_utc':datetime.now(timezone.utc).isoformat()}
    write(out/'plan.json',frozen)
    for p in files:
        q=out/'source'/p;q.parent.mkdir(exist_ok=True,parents=True)
        with q.open('xb') as f:f.write((ROOT/p).read_bytes())
    memory=Memory(ROOT/'runs/research.sqlite')
    exp=memory.register_experiment(frozen,{'kind':'new_training_cohort_source_audit','training_labels':False,'gpu_jobs':0},role='environment')
    write(out/'registration.json',{'experiment_id':exp,'plan_sha256':sha(out/'plan.json')})
    memory.record_experiment(exp,'running',role='environment');start=time.monotonic()
    try:
        pins={a['path']:a for a in plan['archives']};rows=[];contexts={};verified=[]
        for name,sources in sorted(groups.items()):
            p=ROOT/'data/local/hf-replays'/name;pin=pins[name]
            if p.stat().st_size!=pin['bytes'] or sha(p)!=pin['sha256']:raise ValueError('Archive mismatch:'+name)
            for source,record in iter_selected_records(p,sources):
                projected,ctx=project_record(record,source)
                if not projected:raise ValueError('Selected training view has no human Long Yao snapshot')
                if set(contexts)&set(ctx):raise ValueError('Duplicate record IDs')
                rows.extend(projected);contexts.update(ctx)
            verified.append(name)
        if len({r['game_id'] for r in rows})!=plan['selected_games']:raise ValueError('Selected games lost')
        with (out/'evidence-rounds.jsonl').open('x',encoding='utf8') as f:
            for row in rows:f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
        write(out/'combat-context.json',contexts)
        inventory={key:Counter() for key in ['cards','fates','season','permanent_keys']}
        for row in rows:
            for player in row['players']:
                s=player['candidate_start']
                for key,field in [('cards','board'),('fates','talents'),('season','xian_mo_strategies')]:
                    inventory[key].update(s.get(field,[]) or [])
                inventory['permanent_keys'].update((s.get('permanentBuffTempDatas') or {}).keys())
        write(out/'content-candidates.json',{'scope':'observed_start_incidence_not_rule_admission',
            'counts':{k:dict(sorted(v.items(),key=lambda item:str(item[0]))) for k,v in inventory.items()},'training_admitted':False})
        result={'schema':'training-cohort-source-audit-v2','experiment_id':exp,'source_games':len(selected),
            'source_records':len(rows),'archives_verified':verified,'archive_bytes_hashed':sum(pins[n]['bytes'] for n in verified),
            'elapsed_seconds':time.monotonic()-start,'prior_pilot_game_overlap':0,
            'raw_selected_views_parsed':len(selected),'unselected_archive_payloads_parsed':False,
            'current_private_fields_imported':False,'raw_hands_exported':False,'postbattle_inputs_imported':False,
            'missing_start_extensions':sum(c['players'][i]['start_extensions'][k] is None for c in contexts.values() for i in (0,1) for k in ['talentDatas','privateTalentDatas']),
            'mirror_context_counts':dict(Counter(str(p['is_mirror']) for c in contexts.values() for p in c['players'])),
            'parameter_record_counts':dict(Counter('missing' if c['battle_params'] is None else 'empty' if c['battle_params']==[] else 'nonempty' for c in contexts.values())),
            'holdout_opened':False,'independent_acceptance':False,'download_bytes':0,'gpu_jobs':0,'training_labels_emitted':0,
            'outputs_sha256':{n:sha(out/n) for n in ['evidence-rounds.jsonl','combat-context.json','content-candidates.json']}}
        write(out/'report.json',result);memory.record_experiment(exp,'completed',result,role='environment')
        assert memory.verify_integrity();return result
    except Exception as error:
        result={'error':repr(error),'experiment_id':exp};write(out/'failure.json',result)
        memory.record_experiment(exp,'failed',result,role='environment');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();r=audit(a.plan,a.out)
    print(json.dumps({k:v for k,v in r.items() if k not in ['archives_verified','outputs_sha256']},ensure_ascii=False))
