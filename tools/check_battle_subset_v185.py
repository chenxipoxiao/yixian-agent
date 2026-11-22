"""Information, legality, shared-panel and real-engine checks before release."""
from pathlib import Path
from copy import deepcopy
from collections import Counter
import json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from yixian.battle_subset_v185 import *
from tools.run_battle_subset_v185 import Worker

def check(out):
    rows=json.loads((ROOT/'runs/tactical-data/verified-subset-v185/starts.json').read_text('utf8'))
    catalogue={c['id']:c for c in json.loads((ROOT/'data/local/2026-11-06/tables/CardConfig.json').read_text('utf8'))}
    seen={};history=0
    for row in rows:
        assert seen.setdefault(row['game_id'],row['split'])==row['split']
        assert candidate_orders(list(reversed(row['raw_cards'][row['learner']])),catalogue)==row['candidate_orders']
        assert reactive_orders(row['raw_cards'][1-row['learner']],row['opponent_visible_learner_history'],row['round'],catalogue)==row['opponent_orders']
        changed=deepcopy(row);changed['battle']['players'][1-row['learner']]['cards']=['SECRET'];changed['baseline_check']={'winner':999};changed['opponent_orders']=[['SECRET']]
        assert policy_observation(changed)==policy_observation(row)
        for a in row['candidate_orders']:
            for b in row['opponent_orders']:
                x=battle_input(row,a,b)
                assert Counter(x['players'][row['learner']]['cards'])==Counter(row['battle']['players'][row['learner']]['cards'])
                assert all(x['players'][i][k]==v for i in [0,1] for k,v in row['battle']['players'][i].items() if k!='cards')
        h=row['opponent_visible_learner_history']
        if h:assert h['round']<row['round'];history+=1
    try:reactive_orders(rows[0]['raw_cards'][1-rows[0]['learner']],{'round':rows[0]['round'],'board':[]},rows[0]['round'],catalogue)
    except ValueError:pass
    else:raise AssertionError('Current order leakage was accepted')
    try:utility({'terminated':True,'truncated':False,'used_randomness':True,'winner':0,'hp_delta':99},0)
    except ValueError:pass
    else:raise AssertionError('Random reward accepted')
    # Means distinguish a fixed action from a hidden-state-wise artificial maximum.
    results=[{'terminated':True,'truncated':False,'used_randomness':False,'winner':w,'hp_delta':0} for w in [0,1,1,1,0,0]]
    matrix,means=summarize_matrix(results,{'learner':0},2);assert means==[-1/3,1/3] and max(means)<1.
    out.mkdir(parents=True,exist_ok=False);start=time.monotonic();w=Worker(out/'engine.stderr');checks=[]
    try:
        selected=sorted(rows,key=lambda r:digest(r['id']))[:8]
        for row in selected:
            b=deepcopy(row['battle']);b['include_trace']=False;r=w.run([b])[0]
            assert all(r[k]==v for k,v in row['baseline_check'].items()),(row['id'],r,row['baseline_check'])
            variants=w.run([battle_input(row,a,b) for a in row['candidate_orders'] for b in row['opponent_orders']])
            checks.append({'id':row['id'],'baseline_unchanged':True,'counterfactuals':len(variants),
                'resolved':sum(r.get('terminated') and not r.get('truncated') and not r.get('unresolved') for r in variants),
                'random':sum(bool(r.get('used_randomness')) for r in variants),
                'results':variants})
    finally:w.close()
    report={'status':'passed','all_input_states_checked':len(rows),'whole_game_split_checked':len(seen),
        'earlier_public_histories':history,'opponent_secret_and_outcome_invariance':True,
        'candidate_multiset_and_start_state_preserved':True,'fixed_panel_aggregation_checked':True,
        'real_baseline_regressions':len(checks),'real_counterfactuals':sum(r['counterfactuals'] for r in checks),
        'checks':checks,'elapsed_seconds':time.monotonic()-start,'software_checks_are_not_independent_acceptance':True}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='checks'},ensure_ascii=False))
if __name__=='__main__':check(ROOT/sys.argv[1])
