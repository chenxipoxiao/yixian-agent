"""Compare frozen train-only snapshot speed candidates with recorded first actor.

This is a component diagnostic, not combat validation or a training-label source.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from yixian.combat_initiative import load_initiative_contract,compare_initiative_candidates
from yixian.combat_speed_metadata import load_speed_metadata
from yixian.combat_initialization import IncompleteCombatState
from yixian.order_data import game_split
from yixian.memory import Memory

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def write(p,data):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')


def public_view(player,*,include_board=False):
    required={'exp','talents','usedKeYinCards','permanentBuffTempDatas'}
    if include_board:required.add('usedCards')
    if not required.issubset(player['source_start_field_names']):
        raise IncompleteCombatState('Required original start fields absent from source')
    start=player['candidate_start']
    result={'lastRoundData':{'exp':start['exp'],'talents':start['talents'],
                            'usedKeYinCards':start['used_keyin_cards'],
                            'permanentBuffTempDatas':start['permanentBuffTempDatas']}}
    if include_board:result['lastRoundData']['usedCards']=start['board']
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pilot',type=Path,required=True);p.add_argument('--plan-sha256',required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--conditional-metadata',action='store_true');args=p.parse_args()
    assert sha(args.pilot/'plan.json')==args.plan_sha256,'Pilot plan pin mismatch'
    prior=read(args.pilot/'report.json');source=args.pilot/'evidence-rounds.jsonl'
    assert prior['plan_sha256']==args.plan_sha256 and sha(source)==prior['output_sha256']['evidence-rounds.jsonl']
    files=['yixian/combat_initiative.py','yixian/combat_permanent.py','yixian/combat_initialization.py',
           'yixian/order_data.py','tools/audit_combat_initiative.py','tests/test_combat_initiative.py',
           'data/inspection/combat-initiative-v1.json','yixian/combat_speed_metadata.py',
           'tests/test_combat_speed_metadata.py','data/inspection/conditional-speed-metadata-v1.json',
           'data/inspection/conditional-speed-evidence-v1.json']
    contract=load_initiative_contract(include_conditional_metadata=args.conditional_metadata)
    metadata=load_speed_metadata() if args.conditional_metadata else None
    plan={'scope':'S2_train_only_displayed_speed_diagnostic','created_at_utc':datetime.now(timezone.utc).isoformat(),
          'pilot_plan_sha256':args.plan_sha256,'evidence_sha256':sha(source),'fixed_source_games':64,'fixed_round_snapshots':525,
          'source_sha256':{n:sha(ROOT/n) for n in files},'contract':contract,
          'hypothesis':'For strict unequal scores, higher recorded cultivation plus covered client-display speed predicts recorded first actor; omissions remain possible.',
          'exclusions':['missing or malformed required source fields','conditional talent family128','speed engraving family42'],
          'tie_policy':'abstain; no inferred random outcome, resonance, or use of buff17 as predictor',
          'paired_baseline':'cultivation-only on exactly those rows where both candidates are non-tied',
          'secondary_diagnostic':'On computed ties only, compare existing buff17 with recorded second actor; never input17 to predictor.',
          'training_labels_allowed':False,'current_server_certification_allowed':False,
          'new_gpu_jobs':0,'new_download_bytes':0,'heldout_groups_used':0}
    if args.conditional_metadata:
        plan.update(scope='S2_train_only_conditional_speed_diagnostic',conditional_metadata_enabled=True,
                    hypothesis='Pinned128 name conditions and42 exact parameters extend displayed-speed diagnostics; compare the same train-only development cohort without using outcome fields as inputs.',
                    exclusions=['missing or malformed required source fields','unknown card metadata for128','unknown exact128 or42 parameter'],
                    historical_diagnostic_preserved='runs/calibration/20261111T2014-initiative/report.json')
    args.out.mkdir(parents=True,exist_ok=False);write(args.out/'plan.json',plan)
    for name in files:
        path=args.out/'source'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/name).read_bytes())
    memory=Memory(ROOT/'runs/research.sqlite');assert memory.verify_integrity()
    experiment=memory.register_experiment(plan,contract,role='environment')
    write(args.out/'registration.json',{'experiment_id':experiment});memory.record_experiment(experiment,'running',role='environment')
    try:
        rows=[json.loads(s) for s in source.read_text(encoding='utf-8').splitlines()]
        assert len(rows)==525 and len({r['game_id'] for r in rows})==64
        assert all(r['split']=='train' and game_split(r['game_id'])=='train' for r in rows)
        results=[];counts=Counter();exclusions=Counter();paired=Counter();mismatch_games=set();tie_flags=Counter();component_counts=Counter()
        for row in rows:
            item={'record_id':row['id'],'game_id':row['game_id'],'round':row['round'],'training_label_allowed':False}
            try:
                assert [v['snapshot_slot'] for v in row['players']]==['p1','p2']
                views=[public_view(player,include_board=args.conditional_metadata) for player in row['players']]
                # Only snapshot fields enter the candidate. Read the target afterwards.
                candidate=compare_initiative_candidates(views,game_mode=3,speed_metadata=metadata)
                item.update(status='candidate_derived',candidate=candidate);counts['candidate_derived']+=1
                for player in candidate['players']:
                    component_counts['players_with_family128']+=int(bool(player['conditional_talent_components']))
                    component_counts['players_with_family42']+=int(bool(player['engraving_speed_components']))
            except IncompleteCombatState as error:
                item.update(status='unsupported_or_incomplete',reason=str(error));exclusions[str(error)]+=1
                results.append(item);continue
            observed=row['outcome'].get('first_player_snapshot_slot')
            item['recorded_first_slot']=observed
            if observed not in ('p1','p2'):
                counts['unresolved_recorded_first']+=1;results.append(item);continue
            target=('p1','p2').index(observed);prediction=candidate['candidate_first_index']
            if prediction is None:
                counts['score_ties_abstained']+=1
                flags=[v['lastRoundData']['permanentBuffTempDatas'].get('17',0)>0 for v in views]
                item['post_prediction_tie_marker17']=flags
                if sum(flags)==1:
                    tie_flags['single_positive_marker']+=1
                    tie_flags['on_recorded_second' if flags[1-target] else 'on_recorded_first']+=1
                else:tie_flags['no_single_marker']+=1
            else:
                counts['strict_candidates_compared']+=1
                matches=prediction==target;item['candidate_matches_record']=matches
                counts['candidate_matches' if matches else 'candidate_mismatches']+=1
                if not matches:mismatch_games.add(row['game_id'])
                exp=[v['lastRoundData']['exp'] for v in views]
                baseline=None if exp[0]==exp[1] else (0 if exp[0]>exp[1] else 1)
                item['cultivation_only_candidate_index']=baseline
                if baseline is None:counts['strict_candidate_with_cultivation_tie']+=1
                else:
                    paired['rows']+=1;paired['speed_matches']+=int(matches);paired['cultivation_matches']+=int(baseline==target)
                    paired['speed_corrected_cultivation_error']+=int(matches and baseline!=target)
                    paired['speed_broke_correct_cultivation']+=int(not matches and baseline==target)
            results.append(item)
        with (args.out/'diagnostics.jsonl').open('x',encoding='utf-8',newline='\n') as f:
            for item in results:f.write(json.dumps(item,ensure_ascii=False,separators=(',',':'))+'\n')
        report={'scope':plan['scope'],'experiment_id':experiment,'completed_at_utc':datetime.now(timezone.utc).isoformat(),
                'plan_sha256':sha(args.out/'plan.json'),'contract':contract,'source_games':64,'round_snapshots':525,
                'counts':dict(counts),'exclusion_reasons':dict(exclusions),'paired_baseline':dict(paired),
                'conditional_component_counts':dict(component_counts),
                'mismatch_source_games':len(mismatch_games),'tie_marker17_diagnostic':dict(tie_flags),
                'diagnostics_sha256':sha(args.out/'diagnostics.jsonl'),'observed_first_used_as_input':False,
                'new_gpu_jobs':0,'new_download_bytes':0,'heldout_groups_used':0,'training_labels_emitted':0,
                'full_initiative_rules_recovered':False,'current_server_calibration_passed':False,'complete_combat_replayed':False,
                'reference_engine_battle_metrics':None,'real_game_strength':None,
                'limits':['Client-display subset and score-order diagnostic only; no server-authoritative full initiative implementation.',
                          'Missing resonance context remains unknown; ties are not randomized or assigned from recorded labels.',
                          'Repeated rounds are grouped into64 source games, not independent matches.']}
        write(args.out/'report.json',report)
        memory.record_experiment(experiment,'completed',{'report':str(args.out/'report.json'),'report_sha256':sha(args.out/'report.json'),'training_labels':0},role='environment')
        assert memory.verify_integrity();print(json.dumps({k:v for k,v in report.items() if k not in ('contract','limits')},ensure_ascii=False))
    except Exception as error:
        write(args.out/'failure.json',{'experiment_id':experiment,'error':str(error),'error_type':type(error).__name__})
        memory.record_experiment(experiment,'failed',{'failure':str(args.out/'failure.json')},role='environment');raise


if __name__=='__main__':main()
