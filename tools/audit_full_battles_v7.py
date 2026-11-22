"""Run complete battles on the pinned training pilot, then open target outcomes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from yixian.full_battle_v7 import compile_start, derive_start_initiative, simulate_batch, catalogue, UnresolvedBattle
from yixian.terminal_damage import calculate_terminal_damage

PILOT_SHA='b51d9fac1b935b63b64c0c4d0531effd6bdb9a1ab888874f87b02c6d75efb67f'


def audit(pilot, context_path, out):
    source=pilot.read_bytes()
    if hashlib.sha256(source).hexdigest()!=PILOT_SHA:raise ValueError('Unexpected development source')
    contexts=json.loads(context_path.read_text(encoding='utf-8'))
    rows=list(map(json.loads,source.decode('utf-8').splitlines()))
    compiled=[];included=[];excluded=[];tables=catalogue();initiatives=[]
    for row in rows:
        if row.get('split')!='train':raise ValueError('Training games only')
        try:
            context=contexts[row['id']]
            initiative=derive_start_initiative(row,game_mode=context['game_mode'])
            # Unequal speeds independently choose the first actor. For ties
            # only, condition on the recorded environment tiebreak outcome.
            first=(None if initiative['candidate_first_index'] is not None else
                   {'p1':0,'p2':1}.get(row['outcome'].get('first_player_snapshot_slot')))
            c=compile_start(row,first_player=first,seed='diagnostic-'+row['id'],
                game_mode=context['game_mode'],season_mec=context['season_mec'],
                combat_context=context,tables=tables)
        except (UnresolvedBattle, ValueError) as error:
            excluded.append({'record_id':row['id'],'game_id':row['game_id'],'reason':str(error)})
        else:compiled.append(c);included.append(row);initiatives.append(initiative)
    if not compiled:raise ValueError('No executable battles')
    simulated=simulate_batch([c['battle'] for c in compiled]);cases=[]
    for row,c,result,initiative in zip(included,compiled,simulated['results'],initiatives):
        try:damage=calculate_terminal_damage(c,result)
        except ValueError as error:damage={'resolved':False,'reason':str(error),'life_damage':None}
        actual=row['outcome']
        signed_damage=(damage['life_damage']*(1 if result['winner']==0 else -1)
                       if damage['resolved'] else None)
        comparisons={
            'winner':result['winner']=={'p1':0,'p2':1}.get(actual['winner_snapshot_slot']),
            'hp_delta':result['hp_delta']==actual['recorded_hp_delta'],
            'turns':result['turns']==actual['recorded_turn_count'],
            'destiny_damage':signed_damage==actual['recorded_destiny_damage']}
        cases.append({'record_id':row['id'],'game_id':row['game_id'],'round':row['round'],
            'compiled':c,'simulation':result,'settlement':damage,'expected':actual,
            'comparison':comparisons,'all_four_match':all(comparisons.values()),
            'initiative':initiative,'initiative_matches_record':c['battle']['first_player']==
                {'p1':0,'p2':1}.get(actual['first_player_snapshot_slot'])})
    def totals(group):
        return {'records':len(group),'games':len({c['game_id'] for c in group}),
                'matches':{k:sum(c['comparison'][k] for c in group) for k in ('winner','hp_delta','turns','destiny_damage')},
                'all_four_match':sum(c['all_four_match'] for c in group)}
    deterministic=[c for c in cases if not c['simulation']['used_randomness']]
    stochastic=[c for c in cases if c['simulation']['used_randomness']]
    summary={'source_records':len(rows),'source_games':len({r['game_id'] for r in rows}),
             'simulated':totals(cases),'deterministic':totals(deterministic),
             'stochastic_unconditioned':totals(stochastic),'excluded':len(excluded),
             'exclusion_counts':dict(Counter(e['reason'].split(':')[0] for e in excluded)),
             'truncated':sum(c['simulation']['truncated'] for c in cases),
             'independently_computed_initiative':sum(c['initiative']['candidate_first_index'] is not None for c in cases),
             'initiative_matches_record':sum(c['initiative_matches_record'] for c in cases),
             'training_labels_emitted':0,'S2_accepted':False,
             'scope':'complete single-battle development differential; recorded initiative supplied only on speed ties',
             'limitations':['same training pilot used to diagnose patches; not independent holdout',
                 'stochastic replay RNG not reconstructed; no seed search',
                 'unknown cards/effects reject entire battle',
                 'terminal match does not prove every intermediate action or interaction',
                 'not full eight-player management or real-game policy strength']}
    report={'summary':summary,'source_sha256':PILOT_SHA,
            'context_sha256':hashlib.sha256(context_path.read_bytes()).hexdigest(),
            'engine':{k:v for k,v in simulated.items() if k!='results'},
            'cases':cases,'excluded':excluded}
    with out.open('x',encoding='utf-8') as handle:json.dump(report,handle,ensure_ascii=False,indent=2)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pilot',type=Path,required=True)
    p.add_argument('--context',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.pilot,a.context,a.out),ensure_ascii=False,indent=2))
