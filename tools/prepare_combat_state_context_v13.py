"""Project only pre-battle talent parameters from the pinned local extraction."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path


def prepare(base_path, raw_path, out):
    base=json.loads(base_path.read_text(encoding='utf-8'))
    raw=json.loads(raw_path.read_text(encoding='utf-8'))
    if set(base)!=set(raw):raise ValueError('Context records differ')
    result=deepcopy(base)
    for key,target in result.items():
        origin=raw[key]
        if origin['source_raw_sha256']!=target['source_raw_sha256']:
            raise ValueError('Raw source mismatch')
        if len(origin['players'])!=2:raise ValueError('Two players required')
        for a,b in zip(target['players'],origin['players']):
            if a['snapshot_slot']!=b['snapshot_slot'] or a['hand_count']!=b['hand_count']:
                raise ValueError('Start snapshot mismatch')
            public=b['raw_start_talentDatas'];private=b['raw_start_privateTalentDatas']
            if not isinstance(public,dict) or not isinstance(private,dict):
                raise ValueError('Explicit raw start dictionaries required')
            a['start_extensions']={'origin':'publicData.lastRoundData',
                'talentDatas':{k:v for k,v in public.items() if k=='189'},
                'privateTalentDatas':{k:v for k,v in private.items() if k=='199'}}
        target['start_extension_source_sha256']=hashlib.sha256(raw_path.read_bytes()).hexdigest()
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    return {'records':len(result),'private_hands_exported':False,'battle_outcomes_imported':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True)
    p.add_argument('--raw-start',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.base,a.raw_start,a.out)))
