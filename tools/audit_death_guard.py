"""Audit initial guard17 derivation on the fixed train-only pilot; no lethal trajectory inference."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib,json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from yixian.combat_calibration import iter_selected_records
from yixian.combat_death_guard import load_death_guard_contract, derive_death_guard_opening
from yixian.combat_initialization import IncompleteCombatState
from yixian.order_data import game_split
from yixian.memory import Memory

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def write(path,data):
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot',type=Path,required=True)
    parser.add_argument('--plan-sha256',required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    assert sha(args.pilot/'plan.json')==args.plan_sha256,'Pilot plan pin differs'
    prior_plan,prior_report=read(args.pilot/'plan.json'),read(args.pilot/'report.json')
    rows_path=args.pilot/'evidence-rounds.jsonl'
    assert prior_report['plan_sha256']==args.plan_sha256
    assert sha(rows_path)==prior_report['output_sha256']['evidence-rounds.jsonl']
    rows=[json.loads(s) for s in rows_path.read_text(encoding='utf-8').splitlines()]
    expected={(r['source']['raw_sha256'],r['round']):r for r in rows}
    assert len(expected)==len(rows) and all(r['split']=='train' and game_split(r['game_id'])=='train' for r in rows)
    selected=prior_plan['selected_sources']
    assert all(s['split']=='train' and game_split(s['game_id'])=='train' for s in selected)
    contract=load_death_guard_contract()
    source_files=['yixian/combat_death_guard.py','yixian/combat_permanent.py','yixian/combat_initialization.py','yixian/combat_calibration.py',
                  'yixian/order_data.py','tools/audit_death_guard.py',
                  'data/inspection/permanent-combat-initialization-v1.json','data/inspection/base-combat-initialization-v1.json','data/local/2026-11-06/tables/LevelConfig.json','data/inspection/death-guard-v1.json','tests/test_combat_death_guard.py']
    plan={'scope':'S2_initial_guard17_boundary_not_full_opening','created_at_utc':datetime.now(timezone.utc).isoformat(),
          'pilot_plan_sha256':args.plan_sha256,'pilot_report_sha256':sha(args.pilot/'report.json'),
          'pilot_evidence_sha256':sha(rows_path),'selected_sources':selected,'expected_rounds':len(rows),
          'contract':contract,'source_sha256':{n:sha(ROOT/n) for n in source_files},
          'new_gpu_jobs':0,'new_download_bytes':0,'heldout_groups_used':0,'training_labels_allowed':False,
          'measurements':['derivable states','positive permanent17 count grouped by source game','HP unchanged at17 opening','missing evidence; no use of final HP to reconstruct intermediate lethal events']}
    args.out.mkdir(parents=True,exist_ok=False);write(args.out/'plan.json',plan)
    for n in source_files:
        target=args.out/'source'/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/n).read_bytes())
    memory=Memory(ROOT/'runs/research.sqlite');assert memory.verify_integrity()
    experiment=memory.register_experiment(plan,contract,role='environment')
    write(args.out/'registration.json',{'experiment_id':experiment});memory.record_experiment(experiment,'running',role='environment')
    try:
        archives=defaultdict(list)
        for s in selected:archives[s['archive']].append(s)
        archive_hashes={entry['path']:entry['sha256'] for entry in prior_plan['archives']}
        results=[];seen=set()
        for archive,selection in sorted(archives.items()):
            path=ROOT/'data/local/hf-replays'/archive
            assert sha(path)==archive_hashes[archive],'Cached archive pin differs'
            for source,record in iter_selected_records(path,selection):
                for turn in record['data']['roundStats']:
                    key=(source['raw_sha256'],turn['round'])
                    if key not in expected:continue
                    assert key not in seen and expected[key]['game_id']==source['game_id'];seen.add(key)
                    for slot in ('p1','p2'):
                        public=turn[slot]['publicData']
                        result={'record_id':expected[key]['id'],'game_id':source['game_id'],'round':turn['round'],
                                'slot':slot,'character_id':public['characterId']}
                        try:
                            result.update(status='initial_guard17_derived',initialization=derive_death_guard_opening(public,game_mode=record['data']['gameMode']))
                        except IncompleteCombatState as error:
                            result.update(status='incomplete_evidence',error=str(error),training_label_allowed=False)
                        results.append(result)
        assert seen==set(expected),'Frozen pilot rounds missing'
        valid=[r for r in results if r['status']=='initial_guard17_derived']
        positive=[r for r in valid if r['initialization']['guard17_applied_value']>0]
        assert all(r['initialization']['guard_opening_combat']['hp']==r['initialization']['initialized_combat']['hp'] for r in valid)
        assert all(r['initialization']['guard_opening_combat']['max_hp']==r['initialization']['initialized_combat']['max_hp'] for r in valid)
        with (args.out/'initialized-states.jsonl').open('x',encoding='utf-8',newline='\n') as f:
            for r in results:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
        report={'scope':plan['scope'],'experiment_id':experiment,'completed_at_utc':datetime.now(timezone.utc).isoformat(),
                'plan_sha256':sha(args.out/'plan.json'),'contract':contract,'source_games':len({r['game_id'] for r in results}),
                'round_snapshots':len(seen),'player_snapshots':len(results),'derived_states':len(valid),'incomplete_states':len(results)-len(valid),
                'positive_guard17_states':len(positive),'positive_guard17_source_games':len({r['game_id'] for r in positive}),
                'positive_guard17_longyao_states':sum(r['character_id']==1000003 for r in positive),
                'positive_guard17_values':dict(Counter(str(r['initialization']['guard17_applied_value']) for r in positive)),
                'hp_unchanged_at_guard_opening':len(valid),'max_hp_unchanged_at_guard_opening':len(valid),
                'states_sha256':sha(args.out/'initialized-states.jsonl'),'new_gpu_jobs':0,'new_download_bytes':0,'heldout_groups_used':0,
                'unselected_raw_members_parsed':False,'original_acquisition_rewards_reapplied':False,
                'recorded_first_used_to_assign_guard':False,'recorded_final_hp_used_to_infer_activation':False,
                'lethal_activation_trajectories_verified':0,'guard_expiry_trajectories_verified':0,
                'independently_observed_starting_hp':False,'current_server_calibration_passed':False,'complete_combat_replayed':False,
                'training_labels_emitted':0,'reference_engine_battle_metrics':None,'real_game_strength':None,
                'limits':['Snapshot-derived guard17 at opening, not independently measured combat start.',
                          'No action logs: lethal activation and cleanup are software/static checks, not replay trajectory calibration.',
                          'Other opening effects and full action scheduling remain pending; repeated player/round observations are not independent trials.']}
        write(args.out/'report.json',report)
        memory.record_experiment(experiment,'completed',{'report':str(args.out/'report.json'),'report_sha256':sha(args.out/'report.json'),'training_labels':0},role='environment')
        assert memory.verify_integrity()
        print(json.dumps({k:v for k,v in report.items() if k not in ('contract','deferred_key_player_snapshots','limits')},ensure_ascii=False))
    except Exception as error:
        write(args.out/'failure.json',{'experiment_id':experiment,'type':type(error).__name__,'error':str(error)})
        memory.record_experiment(experiment,'failed',{'failure':str(args.out/'failure.json')},role='environment')
        raise


if __name__=='__main__':main()
