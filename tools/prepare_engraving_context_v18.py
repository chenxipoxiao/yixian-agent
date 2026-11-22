"""Whitelist immutable preparation grids; never import season usage counters."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

SUPPORTED={13009,13016}

def prepare(base_path,raw_path,out):
    base=json.loads(base_path.read_text(encoding='utf8'));raw=json.loads(raw_path.read_text(encoding='utf8'))
    if set(base)!=set(raw):raise ValueError('Context records differ')
    result=deepcopy(base);explicit=0;missing=0
    for rid,target in result.items():
        source=raw[rid]
        if source['source_raw_sha256']!=target['source_raw_sha256']:raise ValueError('Source mismatch')
        if len(source['players'])!=2:raise ValueError('Two raw players required')
        for a,b in zip(target['players'],source['players']):
            if a['snapshot_slot']!=b['slot']:raise ValueError('Seat mismatch')
            choices=b['start_fields']['xianMoStrategies'];owned=sorted(SUPPORTED.intersection(choices))
            if not owned:continue
            season=b['private_fields_for_schema_only'].get('xianMoData')
            if not isinstance(season,dict) or not isinstance(season.get('tempDatas'),dict):
                missing+=len(owned);continue
            selected=season.get('strategies')
            if not isinstance(selected,list) or any(not isinstance(v,dict) for v in selected):
                missing+=len(owned);continue
            confirmed=sorted({v.get('selected') for v in selected if v.get('selected') in SUPPORTED})
            if confirmed!=owned:raise ValueError('Preparation ownership disagrees with lastRoundData')
            slots={str(i):season['tempDatas'][str(i)] for i in owned if str(i) in season['tempDatas']}
            explicit+=len(slots);missing+=len(owned)-len(slots)
            a['season_engraving_input']={'origin':'privateData.xianMoData.tempDatas:preparation_grid_selection',
                'selected_strategy_ids':owned,'slots':slots}
        target['engraving_source_projection_sha256']=hashlib.sha256(raw_path.read_bytes()).hexdigest()
    with out.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    return {'records':len(result),'explicit_grid_values':explicit,'missing_grid_values_preserved':missing,
        'usage_counters_imported':False,'post_battle_results_imported':False,'private_hands_exported':False,
        'scope':'environment calibration only; not an opponent observation'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--raw',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.base,a.raw,a.out)))
