"""Recover combat-only context from the same pinned training-game perspectives."""
from collections import defaultdict
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from yixian.combat_calibration import iter_selected_records


def extract(pilot, destination):
    plan=json.loads((pilot/'plan.json').read_text(encoding='utf-8-sig'))
    raw=(pilot/'evidence-rounds.jsonl').read_bytes()
    if hashlib.sha256(raw).hexdigest()!='b51d9fac1b935b63b64c0c4d0531effd6bdb9a1ab888874f87b02c6d75efb67f':
        raise ValueError('Unexpected development pilot')
    targets={(r['source']['raw_sha256'],r['round']):r for r in map(json.loads,raw.decode('utf-8').splitlines())}
    archives={a['path']:a for a in plan['archives']};groups=defaultdict(list)
    for source in plan['selected_sources']:
        if source['split']!='train':raise ValueError('Training games only')
        groups[source['archive']].append(source)
    output={}
    for name,selected in sorted(groups.items()):
        path=ROOT/'data/local/hf-replays'/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=archives[name]['sha256']:
            raise ValueError('Archive changed')
        for source,record in iter_selected_records(path,selected):
            for turn in record['data']['roundStats']:
                key=(source['raw_sha256'],turn['round'])
                if key not in targets:continue
                target=targets[key];players=[]
                for slot in ('p1','p2'):
                    public=turn[slot]['publicData'];start=public['lastRoundData'];hand=start.get('handCards')
                    # Keep numeric combat state only. Never export private card IDs
                    # as an opponent observation or upload the raw replay archive.
                    players.append({'snapshot_slot':slot,'hand_count':len(hand) if isinstance(hand,list) else None,
                        'hand_values_are_numeric':isinstance(hand,list) and all(type(c) is int for c in hand),
                        'is_mirror':public.get('isMirror'),'public_level':public.get('level'),
                        'battle_start_level':start.get('level'),
                        'after_talent_counters':public.get('talentTempDatas'),
                        'start_private_field_names':sorted(turn[slot].get('privateData',{})),
                        'source_fields':{'hand_count':'publicData.lastRoundData.handCards.length','is_mirror':'publicData.isMirror'}})
                output[target['id']]={'players':players,'battle_params':turn.get('battleParams'),
                    'game_mode':record['data']['gameMode'],'season_mec':record['data']['seasonMec'],
                    'source_raw_sha256':source['raw_sha256'],'game_id':source['game_id'],
                    'scope':'environment_calibration_only_not_policy_observation'}
    if len(output)!=len(targets):raise ValueError('Incomplete source read')
    with destination.open('x',encoding='utf-8') as f:json.dump(output,f,ensure_ascii=False,indent=2)
    return {'records':len(output),'games':len(plan['selected_sources']),'raw_hands_exported':False,'holdout_opened':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pilot',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(extract(a.pilot,a.out)))
