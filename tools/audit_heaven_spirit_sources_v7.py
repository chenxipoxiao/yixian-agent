"""Read only selected original BattleResult members for the1001 switch."""
from pathlib import Path
from copy import deepcopy
from collections import defaultdict
import argparse,hashlib,json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from yixian.combat_calibration import iter_selected_records
from yixian.combat_cohort_projection_v2 import project_record
from yixian.combat_start_context_bindings_v7 import bind_heaven_spirit,validate_additions
from yixian.combat_validation_batch_v7 import verify_sources
from yixian.memory import Memory
read=lambda p:json.loads(Path(p).read_text('utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
 with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,ensure_ascii=False,indent=2)
def audit(plan_path,out):
 plan=read(plan_path);verify_sources(ROOT,plan['source_sha256'])
 rows={r['id']:r for r in map(json.loads,(ROOT/plan['rows']).read_text('utf8').splitlines())}
 v2=read(ROOT/plan['v2_contexts']);old=read(ROOT/plan['previous_contexts']);contexts=deepcopy(old)
 legacy=read(ROOT/plan['legacy_admitted']);selected=set(plan['target_record_ids']);groups=defaultdict(list)
 for source in plan['selected_sources']:groups[source['archive']].append(source)
 assert all(s['split']=='train' for s in plan['selected_sources'])
 assert {rows[r]['game_id'] for r in selected}=={s['game_id'] for s in plan['selected_sources']}
 out.mkdir(parents=True,exist_ok=False);write(out/'plan.json',plan)
 memory=Memory(ROOT/'runs/research.sqlite');exp=memory.register_experiment(plan,{'kind':'original_heaven_spirit_source_binding_v7','training_labels':False,'gpu_jobs':0},role='environment')
 memory.record_experiment(exp,'running',role='environment');write(out/'registration.json',{'experiment_id':exp});start=time.monotonic()
 try:
  pins={a['path']:a for a in plan['archives']};seen=set();verified=[]
  for name,sources in sorted(groups.items()):
   path=ROOT/'data/local/hf-replays'/name
   assert path.stat().st_size==pins[name]['bytes'] and sha(path)==pins[name]['sha256']
   for source,record in iter_selected_records(path,sources):
    projected,projected_contexts=project_record(record,source)
    assert {r['id'] for r in projected}=={r['id'] for r in rows.values() if r['game_id']==source['game_id']}
    assert all(row==rows[row['id']] and projected_contexts[row['id']]==v2[row['id']] for row in projected)
    turns={t['round']:t for t in record['data']['roundStats']}
    for row in projected:
     rid=row['id']
     if rid not in selected:continue
     assert rid not in seen;seen.add(rid)
     contexts[rid]=bind_heaven_spirit(turns[row['round']],source,row,contexts[rid],legacy[rid])
   verified.append(name)
  assert seen==selected
  admitted=validate_additions(list(rows.values()),old,contexts,selected,legacy)
  write(out/'combat-context.json',contexts);write(out/'admitted-records.json',admitted)
  verify_sources(ROOT,plan['source_sha256'])
  report={'experiment_id':exp,'success':True,'selected_train_games':len(plan['selected_sources']),'bound_records':len(admitted),
   'archives_verified':verified,'archive_bytes_hashed':sum(pins[n]['bytes'] for n in verified),
   'legacy_full_map_hashes_verified':True,'existing_context_unchanged_except_declared_additions':True,
   'private_hands_exported':False,'unselected_members_parsed':False,'holdout_opened':False,'download_bytes':0,
   'gpu_jobs':0,'training_labels_emitted':0,'policy_observation_allowed':False,'counterfactual_reuse_allowed':False,
   'elapsed_seconds':time.monotonic()-start,'outputs_sha256':{n:sha(out/n) for n in ['combat-context.json','admitted-records.json']}}
  write(out/'report.json',report);memory.record_experiment(exp,'completed',report,role='environment')
 except Exception as error:
  report={'experiment_id':exp,'success':False,'error':repr(error)};write(out/'failure.json',report);memory.record_experiment(exp,'failed',report,role='environment');raise
 assert memory.verify_integrity();return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 print(json.dumps(audit(a.plan,a.out),ensure_ascii=False))
