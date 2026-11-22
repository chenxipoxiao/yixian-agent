"""Calculate a full single battle and terminal destiny damage from explicit starts.

The JSON contains start, combat_context, first_player, and seed. It must contain
all combat-relevant state accepted by the current diagnostic compiler. Unknown
effects stop calculation; this tool never derives input from a terminal result.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from yixian.full_battle_v74 import compile_start, simulate_batch
from yixian.terminal_damage_v47 import calculate_terminal_damage


def calculate(value, *, max_turns=128):
    context=value['combat_context']
    compiled=compile_start(value['start'],combat_context=context,
        first_player=value.get('first_player'),seed=value['seed'],
        game_mode=context['game_mode'],season_mec=context['season_mec'],max_turns=max_turns)
    result=simulate_batch([compiled['battle']])['results'][0]
    return {'simulation':result,'settlement':calculate_terminal_damage(compiled,result),
            'declared_components':compiled['declared_components'],
            'context':compiled['context'],'training_label_allowed':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('start',type=Path)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--max-turns',type=int,default=128)
    a=p.parse_args();result=calculate(json.loads(a.start.read_text(encoding='utf-8-sig')),max_turns=a.max_turns)
    with a.out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'winner':result['simulation'].get('winner'),'hp_delta':result['simulation'].get('hp_delta'),
        'action_turns':result['simulation'].get('turns'),'settlement':result['settlement'],'unresolved_reason':result['simulation'].get('unresolved_reason')},ensure_ascii=False))
