"""Freeze calibrated starts and earlier public history from pinned train views."""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from yixian.battle_subset_v185 import admission_reason, candidate_orders, reactive_orders, split_game, digest
from yixian.combat_calibration import iter_selected_records
from yixian.order_data import game_split

REPORT_DIR='runs/stages/20261118T011600Z-s2-season-card-identities-v183'
ROW_FILES=['runs/calibration/20261111T1616-longyao-train-pilot/evidence-rounds.jsonl',
 'runs/stages/20261115T011300Z-s2-second-training-pilot/source-intake/evidence-rounds.jsonl',
 'runs/stages/20261117T203800Z-s2-third-training-cohort/source-intake/evidence-rounds.jsonl']
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
    with p.open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)

def prepare(out):
    out.mkdir(parents=True,exist_ok=False)
    sources={};rawrows={}
    for name in ROW_FILES:
        for line in (ROOT/name).read_text('utf8').splitlines():
            row=json.loads(line);rawrows[row['id']]=row;sources[row['game_id']]=row['source']
            assert row['split']=='train' and game_split(row['game_id'])=='train'
    catalogue={c['id']:c for c in read(ROOT/'data/local/2026-11-06/tables/CardConfig.json')}
    cases=sum((read(ROOT/REPORT_DIR/n)['cases'] for n in ['full-battle-report-old-native.json','full-battle-report-native.json']),[])
    accepted=[];rejected=[]
    for c in cases:
        reason=admission_reason(c)
        if reason:rejected.append({'id':c['record_id'],'reason':reason});continue
        for seat,p in enumerate(c['compiled']['battle']['players']):
            if p['character']!='sw3':continue
            cards=[d['raw_cards'] for d in c['compiled']['declared_components']]
            if any(not 3<=len(b)<=8 or len(set(b))<2 for b in cards):
                rejected.append({'id':c['record_id'],'learner':seat,'reason':'uninformative_multiset'});continue
            r={'id':c['record_id']+f'-seat{seat}','record_id':c['record_id'],'game_id':c['game_id'],
               'split':split_game(c['game_id']),'round':c['round'],'learner':seat,
               'career':rawrows[c['record_id']]['players'][seat]['career'],
               'battle':c['compiled']['battle'],'raw_cards':cards,
               'baseline_check':{k:c['simulation'][k] for k in ['winner','hp_delta','turns','used_randomness']},
               'calibration_four_metrics_match':True}
            accepted.append(r)
    groups=defaultdict(list)
    selected_games={r['game_id'] for r in accepted}
    for game in sorted(selected_games):groups[sources[game]['archive']].append(sources[game])
    histories={};archive_receipts=[]
    for archive,selected in sorted(groups.items()):
        archive_path=ROOT/'data/local/hf-replays'/archive
        archive_receipts.append({'archive':archive,'sha256':sha(archive_path),'selected_members':len(selected)})
        for source,record in iter_selected_records(archive_path,selected):
            past={}
            for turn in sorted(record['data']['roundStats'],key=lambda t:t['round']):
                number=turn['round'];players=[turn[s]['publicData'] for s in ('p1','p2')]
                for seat,p in enumerate(players):
                    # uid is used ONLY inside this one pinned replay; never exported.
                    if p.get('characterId')==1000003:
                        histories[source['game_id'],number,seat]=past.get(p['uid'])
                for p in players:
                    board=p.get('lastRoundData',{}).get('usedCards')
                    if isinstance(board,list) and board and all(type(c) is int and c in catalogue for c in board):
                        past[p['uid']]={'round':number,'board':board,
                            'source':'earlier_completed_battle.publicData.lastRoundData.usedCards'}
        print(json.dumps({'archive':archive,'selected_views':len(selected)}),flush=True)
    for row in accepted:
        history=histories[row['game_id'],row['round'],row['learner']]
        row['opponent_visible_learner_history']=history
        row['candidate_orders']=candidate_orders(row['raw_cards'][row['learner']],catalogue)
        row['opponent_orders']=reactive_orders(row['raw_cards'][1-row['learner']],history,row['round'],catalogue)
        row['opponent_observation_digest']=digest({'own_cards':sorted(row['raw_cards'][1-row['learner']]),'earlier_public_target':history})
        row['policy_input_fields']=['own_card_multiset']
        row['same_original_table_opponent']=True
    write(out/'starts.json',accepted);write(out/'excluded.json',rejected)
    write(out/'manifest.json',{'schema':'verified-subset-input-v185','created_utc':datetime.now(timezone.utc).isoformat(),
        'runtime':'tools/full_battle_bridge_web_v183r2.mjs','source_battle_records':len(cases),
        'starts':len(accepted),'unique_battles':len({r['record_id'] for r in accepted}),
        'games':len(selected_games),'split_records':dict(Counter(r['split'] for r in accepted)),
        'split_games':dict(Counter(split_game(g) for g in selected_games)),
        'public_history_available':sum(r['opponent_visible_learner_history'] is not None for r in accepted),
        'starts_sha256':sha(out/'starts.json'),'source_reports':{n:sha(ROOT/REPORT_DIR/n) for n in ['full-battle-report-old-native.json','full-battle-report-native.json']},
        'source_rows':{n:sha(ROOT/n) for n in ROW_FILES},'archives':archive_receipts,
        'all_source_games_previously_training':True,'holdout_opened':False,
        'validation_seen_by_warm_start':True,'validation_is_independent_acceptance':False,
        'labels_not_yet_generated':True,'raw_replays_or_private_hands_exported':False,
        'S2_accepted':False,'full_match_training':False,
        'limit':'Simple start schema only; every counterfactual must complete without randomness, otherwise reject whole state.'})
    return read(out/'manifest.json')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    print(json.dumps(prepare(a.out),ensure_ascii=False))
