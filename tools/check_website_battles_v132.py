"""Build a separate 90-case website experiment, then simulate and score it."""
from pathlib import Path
from collections import Counter
import copy, hashlib, json, subprocess, sys
sys.setrecursionlimit(20000)

ROOT = Path(__file__).resolve().parents[1]
S = ROOT/'runs/stages/20261116T114200Z-s2-website-battles'
PRIOR = ROOT/'runs/stages/20261116T110900Z-s2-opening-inputs'
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(PRIOR))
from audit_web_inputs import states, read, OUT
from yixian.website_battles_v132 import compiler, compile_case, ORIGIN, EXTENSION
from yixian import full_battle_v130, terminal_damage_v129


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p, value):
    with Path(p).open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)


def extract():
    cases=[]; observations=[]
    for path in sorted(OUT.glob('r-*-decoded.json')):
        record=read(path); rid=record['id']; uid=record['targetUid']
        for n,before,after,step in states(record):
            if 'battle' not in step: continue
            battle=step['battle']; private=before.get('privatePlayer',{})
            eligible=[m for m in battle['matchups'] if m.get('authoritative') is True and uid in m['players']]
            if not eligible: continue  # Spectated/non-target summary, outside the registered cohort.
            assert len(eligible)==1
            players=eligible[0]['players']; owner=players[uid]
            opponent=players[owner['opponentUid']]; pair=[owner,opponent]
            assert private['uid']==uid and private['deck']==owner['deck'] and before['round']==battle['round']
            assert before['gameMode']==3 and before['seasonMechanic']==10
            caseid=rid+'/round'+str(battle['round'])
            row={'id':caseid,'game_id':rid,'round':battle['round'],
                # This is the hypothesis tested, NOT an observed source version.
                'source_rules_version':'001.0008.0005','source_version_is_test_hypothesis':True,
                'source':{'raw_sha256':sha(path),'path':str(path),'step':n},'players':[]}
            context={'game_mode':3,'season_mec':10,'source_raw_sha256':sha(path),'players':[]}
            differences=[]; conflicts=[]
            for i,p in enumerate(pair):
                public=before['players'][p['uid']]; known_private=i==0
                for field in ('cultivation','physique'):
                    if public[field]!=p[field]:differences.append({'seat':i,'field':field,'last_public':public[field],'battle_start':p[field]})
                if int(str(public['phase']).split()[0])!=p['phase']:differences.append({'seat':i,'field':'phase'})
                if [x['id'] for x in public['talents']]!=[x['id'] for x in p['talents']]:differences.append({'seat':i,'field':'talents'})
                assert type(public['extraMaxHp']) is int
                assert type(public['life']) is int
                permanent={str(x['id']):x['value'] for x in p['battleBuffs']}
                for key,field in [('10023','physique'),('10024','maxPhysique')]:
                    assert key not in permanent or permanent[key]==p[field]
                    permanent[key]=p[field]
                counters={}; counter_sources={}
                observed_talents={x['id']:x for x in public['talents']}
                for t in p['talents']:
                    for origin, ref in [('battle_start_summary',t),('last_prebattle_public_observation',observed_talents.get(t['id'],{}))]:
                        runtime=ref.get('runtime')
                        if isinstance(runtime,dict) and runtime.get('kind')=='fate counter' and type(runtime.get('value')) is int:
                            counters[str(t['id'])]=runtime['value'];counter_sources[str(t['id'])]=origin;break
                start={'board':p['deck'],'unlocked_slots':len(p['deck']),'level':p['phase'],
                    'extra_max_hp_modifier':public['extraMaxHp'],'exp':p['cultivation'],'destiny':p['lifeBefore'],
                    'talents':[x['id'] for x in p['talents']],'talentTempDatas':counters,
                    'xian_mo_strategies':[x['id'] for x in p['xianMoStrategies']],
                    'fate_strategies':[x['id'] for x in p['fateStrategies']],
                    # Website sigil slots are mechanic7; this is explicitly mechanic10.
                    # Season10 enchantments are NOT removed: strategy handlers read them.
                    'used_keyin_cards':[],'permanentBuffTempDatas':permanent}
                row['players'].append({'snapshot_slot':('p1','p2')[i],'character_id':p['characterId'],'candidate_start':start})
                ctx={'snapshot_slot':('p1','p2')[i],'public_level':p['phase'],'is_mirror':bool(p.get('innerDemon')) or p['lifeBefore']<=0,
                    'hand_values_are_numeric':True,'hand_count':len(private['hand']) if known_private else None,
                    'website_hand_unknown':not known_private,'website_strategy_parameters':{},'website_counter_sources':counter_sources,
                    'start_extensions':{'origin':EXTENSION,'talentDatas':{'189':{'commonParams':p['enlightenedCards']}},'privateTalentDatas':{}}}
                if known_private:
                    ctx['start_extensions']['privateTalentDatas']['199']={'commonParams':private['cardStorage']['199']}
                    refs={r['id']:r for r in private['selectedXianMoStrategies']}
                    if (set(refs)-set(start['talents']))!=set(start['xian_mo_strategies']):
                        conflicts.append('private_vs_battle_strategy_ownership')
                    for fid,r in refs.items():
                        assert type(r['locked']) is bool
                        ctx['website_strategy_parameters'][str(fid)]=int(r['locked'])
                        if 'enchantedSlot' in r:ctx['website_strategy_parameters'][str(fid)]=r['enchantedSlot']-1
                    if 1001 in refs:
                        ctx['heaven_spirit_switch']={'origin':ORIGIN,'source_raw_sha256':sha(path),'environment_only':True,
                            'selected_strategy_ids':[1001],'temp_data':{'1001':int(refs[1001]['locked'])}}
                    if 7069 in refs:
                        ctx['clouds_rain_hand']={'origin':ORIGIN,'source_raw_sha256':sha(path),'environment_only':True,'raw_cards':private['hand']}
                context['players'].append(ctx)
            assert sum(p['first'] is True for p in pair)==1
            first=next(i for i,p in enumerate(pair) if p['first'])
            speeds=[p['cultivation']+p['speed'] for p in pair]
            seed=int(hashlib.sha256(caseid.encode()).hexdigest()[:8],16)
            cases.append({'row':row,'combat_context':context,'seed':seed,'first_player':first,
                'initiative':'recorded_tie' if speeds[0]==speeds[1] else 'recorded_strict_speed',
                'speed_consistent':speeds[0]==speeds[1] or first==(0 if speeds[0]>speeds[1] else 1),
                'timing_differences':differences,'input_conflicts':conflicts,'preparation_owner_verified':True,
                'mechanisms':{'vase_raw':private['cardStorage']['199'],'hand_raw':private['hand'],
                    'switch1001':next((r['locked'] for r in private['selectedXianMoStrategies'] if r['id']==1001),None)},
                'url':'https://sharpobject.github.io/yxp_wiki/zh/'+('recordings_751' if owner['characterId']==3000006 else 'recordings_longyao')+'/?season=10&recording='+rid+'&step='+str(n)})
            observations.append({'id':caseid,'result':[p['result'] for p in pair],'life_delta':[p['lifeDelta'] for p in pair],
                'hp_delta':None,'turns':None,'metrics_comparison_only':True})
    assert len(cases)==90
    write(S/'cases-v2.json',cases);write(S/'observations-v2.json',observations)
    print(json.dumps({'cases':len(cases),'timing_consistent':sum(not c['timing_differences'] for c in cases)}))


def run(label):
    out=S/label;out.mkdir(exist_ok=False)
    cases=read(S/'cases-v2.json'); expected={v['id']:v for v in read(S/'observations-v2.json')}
    view=compiler();tables=full_battle_v130.catalogue();compiled=[];rows=[]
    for c in cases:
        record={'id':c['row']['id'],'url':c['url'],'timing_differences':c['timing_differences'],'initiative':c['initiative'],'mechanisms':c['mechanisms']}
        try:
            value=compile_case(c,view,tables);record['compiled_index']=len(compiled);compiled.append(value)
            record['status']='compiled'
        except Exception as exc: record.update(status='input_unresolved',reason=str(exc),error_type=type(exc).__name__)
        rows.append(record)
    write(out/'compiled.json',compiled);write(out/'input-screening.json',rows)
    print(json.dumps({'compiled':len(compiled),'input_unresolved':dict(Counter(r.get('reason') for r in rows if r['status']!='compiled'))},ensure_ascii=False),flush=True)
    if not compiled:return
    process=subprocess.run(['node','--experimental-default-type=module',str(ROOT/'tools/full_battle_bridge_web_v132.mjs')],
        input=json.dumps([v['battle'] for v in compiled],ensure_ascii=False),text=True,encoding='utf-8',capture_output=True,cwd=ROOT,timeout=120)
    write(out/'process.json',{'exit_code':process.returncode,'stderr':process.stderr})
    if process.returncode:raise RuntimeError(process.stderr)
    results=json.loads(process.stdout);assert len(results)==len(compiled);write(out/'simulations.json',results)
    for row in rows:
        if row['status']!='compiled':continue
        j=row['compiled_index']; result=results[j]
        if result.get('unresolved'):
            row.update(status='runtime_unresolved',reason=result['reason']);continue
        if not result['terminated'] or result['truncated']:
            row.update(status='not_terminated');continue
        obs=expected[row['id']];winner=result['winner'];row.update(status='complete',used_randomness=result['used_randomness'],
            predicted_winner=winner,observed_results=obs['result'],winner_match=obs['result'][winner]=='win',simulated_hp_delta=result['hp_delta'],simulated_turns=result['turns'])
        try:
            settlement=terminal_damage_v129.calculate_terminal_damage(compiled[j],result)
            row['settlement']=settlement
            if settlement.get('resolved'):
                delta=[0,0];delta[1-winner]=-settlement['life_damage']
                row.update(predicted_deduction_delta=delta,observed_deduction_delta=obs['life_delta'],deduction_match=delta==obs['life_delta'],
                    simulated_separate_civet_gain=settlement.get('requested_destiny_gains'))
        except Exception as exc:row['settlement_unresolved']=str(exc)
    complete=[r for r in rows if r['status']=='complete'];deterministic=[r for r in complete if not r['used_randomness']]
    summary={'records':len(rows),'compiled':len(compiled),'statuses':dict(Counter(r['status'] for r in rows)),
        'complete':len(complete),'winner_matches':sum(r['winner_match'] for r in complete),'deduction_matches':sum(r.get('deduction_match',False) for r in complete),
        'deterministic':len(deterministic),'deterministic_winner_matches':sum(r['winner_match'] for r in deterministic),
        'deterministic_both_match':sum(r['winner_match'] and r.get('deduction_match',False) for r in deterministic),
        'missing_terminal_hp_and_turns':True,'source_version_certified':False,'source_start_completeness_certified':False,
        'S2_accepted':False,'training_label_allowed':False,'independent_acceptance':False,'new_gpu_jobs':0}
    write(out/'full-battle-report.json',{'summary':summary,'rows':rows})
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':
    if sys.argv[1]=='extract':extract()
    else:run(sys.argv[1])
