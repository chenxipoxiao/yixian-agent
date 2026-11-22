"""v43 CLI reports either a complete battle or the explicit unresolved reason."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.simulate_full_battle_v43 import calculate


def summarize(result):
    simulation=result['simulation']
    if simulation.get('unresolved_reason'):
        return {'resolved':False,'reason':simulation['unresolved_reason'],
                'winner':None,'hp_delta':None,'action_turns':None,
                'settlement':result['settlement'],'training_label_allowed':False}
    return {'resolved':simulation.get('terminated') is True,
            'winner':simulation.get('winner'),'hp_delta':simulation.get('hp_delta'),
            'action_turns':simulation.get('turns'),'settlement':result['settlement'],
            'training_label_allowed':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('start',type=Path)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--max-turns',type=int,default=128)
    a=p.parse_args();result=calculate(json.loads(a.start.read_text(encoding='utf-8-sig')),max_turns=a.max_turns)
    with a.out.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(summarize(result),ensure_ascii=False))
