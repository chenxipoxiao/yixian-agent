"""Audit Long Yao reward transitions on the same frozen training pilot."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.import_replays import file_hash
from yixian.combat_calibration import iter_selected_records
from yixian.dragon_scale_reward import contract, CHARACTER
from yixian.dragon_scale_reward_validation import audit_reward_snapshot, summarize_reward_audit
from yixian.memory import Memory
from yixian.order_data import game_split
from yixian.replays import normalize_replay


def write(path,data):
    with path.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot',type=Path,required=True)
    parser.add_argument('--plan-sha256',required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--upgrade-evidence',type=Path,required=True)
    args=parser.parse_args()
    if file_hash(args.pilot/'plan.json')!=args.plan_sha256:raise ValueError('Pilot plan hash mismatch')
    prior=json.loads((args.pilot/'plan.json').read_text(encoding='utf-8'))
    prior_report=json.loads((args.pilot/'report.json').read_text(encoding='utf-8'))
    evidence=args.pilot/'evidence-rounds.jsonl'
    if (prior_report['plan_sha256']!=args.plan_sha256 or
        file_hash(evidence)!=prior_report['output_sha256']['evidence-rounds.jsonl']):raise ValueError('Pilot evidence mismatch')
    expected={(r['source']['raw_sha256'],r['round']) for r in (json.loads(line) for line in evidence.open(encoding='utf-8'))}
    selected=prior['selected_sources']
    if any(s['split']!='train' or game_split(s['game_id'])!='train' for s in selected):raise ValueError('Only train sources allowed')
    metadata=ROOT/'data/local/2026-11-06/tables/CardConfig.json'
    metadata_hash=file_hash(metadata)
    if metadata_hash!='5f999faf2e59c6f46d816582354829397b84088e021eccba22360de9d69dd641':raise ValueError('Card metadata pin mismatch')
    cards={r['id']:r for r in json.loads(metadata.read_text(encoding='utf-8'))}
    sources=['yixian/dragon_scale_reward.py','yixian/dragon_scale_reward_validation.py',
             'tools/audit_dragon_scale_rewards.py','yixian/replays.py','yixian/combat_calibration.py',
             'yixian/order_data.py','tools/import_replays.py']
    plan={'created_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'S2_conditional_dragon_scale_reward_outcome_sets',
          'pilot_plan_sha256':args.plan_sha256,'pilot_evidence_sha256':file_hash(evidence),
          'selected_sources':selected,'contract':contract(),'card_metadata_sha256':metadata_hash,
          'source_sha256':{s:file_hash(ROOT/s) for s in sources},
          'upgrade_evidence_sha256':file_hash(args.upgrade_evidence),
          'prediction_protocol':'Enumerate outputs before reading expected private usedCards and after-counter; no random probability inferred.',
          'condition':'Recorded post-battle destiny supplies phase condition only; no battle/policy input claim.',
          'new_download_bytes':0,'gpu_jobs':0,'heldout_test_groups_used':0}
    args.out.mkdir(parents=True,exist_ok=False);write(args.out/'plan.json',plan)
    for name in sources:
        target=args.out/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    (args.out/'upgrade-evidence.json').write_bytes(args.upgrade_evidence.read_bytes())
    memory=Memory(ROOT/'runs/research.sqlite')
    experiment=memory.register_experiment(plan,contract(),role='environment')
    write(args.out/'registration.json',{'experiment_id':experiment})
    memory.record_experiment(experiment,'running',role='environment')
    try:
        by_archive=defaultdict(list)
        for source in selected:by_archive[source['archive']].append(source)
        archives={a['path']:a for a in prior['archives']}
        rows=[];seen=set();contexts=Counter()
        for name,selection in sorted(by_archive.items()):
            path=ROOT/'data/local/hf-replays'/name
            if path.stat().st_size!=archives[name]['bytes'] or file_hash(path)!=archives[name]['sha256']:raise ValueError('Cached archive mismatch')
            for source,raw in iter_selected_records(path,selection):
                normalized=normalize_replay(raw,dict(source,artifact=f'{name}::{source["member"]}'))
                for turn,row in zip(raw['data']['roundStats'],normalized,strict=True):
                    key=(source['raw_sha256'],row['round'])
                    if key not in expected:continue
                    if key in seen:raise ValueError('Duplicate pilot round')
                    seen.add(key)
                    for player in row['players']:
                        raw_player=turn[player['snapshot_slot']]
                        private=raw_player['privateData'];public=raw_player['publicData']
                        contexts['private_resonance_object_present' if 'talentResonanceData' in private else 'private_resonance_object_absent']+=1
                        flags=public.get('resonanceTalentFlags')
                        contexts['public_resonance_flags_empty' if flags=={} else 'public_resonance_flags_nonempty_or_missing']+=1
                        if (player.get('character_id')!=CHARACTER or player.get('is_ai') is not False
                            or 27 not in player.get('start_snapshot',{}).get('talents',[])):continue
                        result={k:row[k] for k in ('id','game_id','round')};result['slot']=player['snapshot_slot']
                        player['audit_context']={'is_mirror':public.get('isMirror')}
                        try:result.update(audit_reward_snapshot(player,cards))
                        except ValueError as error:result.update(status='input_unresolved',error=str(error),training_label_allowed=False)
                        rows.append(result)
        if seen!=expected:raise ValueError('Missing selected pilot round')
        with (args.out/'reward-comparisons.jsonl').open('x',encoding='utf-8') as stream:
            for row in rows:stream.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
        report=summarize_reward_audit(rows)
        report.update(schema_version=1,experiment_id=experiment,completed_at_utc=datetime.now(timezone.utc).isoformat(),
            plan_sha256=file_hash(args.out/'plan.json'),source_games=len(selected),round_snapshots=len(seen),
            reward_games=len({r['game_id'] for r in rows}),resonance_field_presence=dict(contexts),
            missing_resonance_selection_assumed_zero=False,
            comparisons_sha256=file_hash(args.out/'reward-comparisons.jsonl'),new_download_bytes=0,gpu_job_seconds=0,heldout_test_groups_used=0)
        write(args.out/'report.json',report)
        memory.record_experiment(experiment,'completed',{'report':str(args.out/'report.json'),'report_sha256':file_hash(args.out/'report.json'),'training_labels':0},role='environment')
        print(json.dumps(report,ensure_ascii=False))
    except Exception as error:
        write(args.out/'failure.json',{'experiment_id':experiment,'error_type':type(error).__name__,'error':str(error)})
        memory.record_experiment(experiment,'failed',{'failure':str(args.out/'failure.json')},role='environment')
        raise


if __name__=='__main__':main()
