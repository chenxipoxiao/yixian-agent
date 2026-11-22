"""Normalize explicit seasonal skip records and wire audited conditional speed."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from . import full_battle_v11 as v11
from .combat_initiative import compare_initiative_candidates
from .combat_speed_metadata import load_speed_metadata

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-start-context-v12.json'
PROOF_SHA='abf7140f809a8317102f21cc030f5516f712e0e7680de0117de792ede6f3abb2'
UnresolvedBattle=v11.UnresolvedBattle
catalogue=v11.catalogue


def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Start context evidence changed')
    facts=json.loads(raw)
    for name,digest in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
            raise UnresolvedBattle('Start context source changed:'+name)
    return facts


def derive_start_initiative(row,*,game_mode=3):
    extension_contract()
    players=[]
    for p in row['players']:
        s=p['candidate_start']
        players.append({'lastRoundData':{'exp':s['exp'],'talents':s['talents'],
            'usedCards':s['board'],'usedKeYinCards':s['used_keyin_cards'],
            'permanentBuffTempDatas':s['permanentBuffTempDatas']}})
    return compare_initiative_candidates(players,game_mode=game_mode,speed_metadata=load_speed_metadata())


def compile_start(row,**kwargs):
    facts=extension_contract()
    projected=deepcopy(row)
    valid_skips={p['id'] for p in json.loads((ROOT/'data/local/2026-11-06/season/XianMoNpcConfig.json').read_text(encoding='utf-8'))}
    skip_records=[];speed_fates=[]
    for p in projected['players']:
        s=p['candidate_start'];choices=s.get('xian_mo_strategies')
        if not isinstance(choices,list) or any(type(v) is not int for v in choices):
            raise UnresolvedBattle('Explicit xian_mo_strategies array required')
        skips=[v for v in choices if 0<v<1000 and v in valid_skips]
        s['xian_mo_strategies']=[v for v in choices if v not in skips]
        skip_records.append(skips)
        fates=s.get('talents')
        if (not isinstance(fates,list) or any(type(v) is not int for v in fates)
                or len(set(fates))!=len(fates)):
            raise UnresolvedBattle('Explicit talent array required')
        handled=[v for v in fates if v in facts['conditional_speed_only_fates']]
        s['talents']=[v for v in fates if v not in handled]
        speed_fates.append(handled)
    independent=kwargs.get('first_player') is None
    initiative=None
    if independent:
        initiative=derive_start_initiative(row,game_mode=kwargs['game_mode'])
        first=initiative['candidate_first_index']
        if first is None:raise UnresolvedBattle('Unknown initiative')
        kwargs['first_player']=first
    elif any(speed_fates):
        initiative=derive_start_initiative(row,game_mode=kwargs['game_mode'])
    result=v11.compile_start(projected,**kwargs)
    if independent:result['initiative_source']='independent_start_speed_comparison'
    for original,effect in zip(row['players'],result['effect_players']):
        effect['season_choices']=deepcopy(original['candidate_start']['xian_mo_strategies'])
        effect['fates']=deepcopy(original['candidate_start']['talents'])
    result['current_start_context']={'evidence_sha256':PROOF_SHA,'skip_records':skip_records,
        'skip_effect':'historical preparation metadata only; rewards never replayed',
        'conditional_initiative':initiative,'speed_fates_not_reapplied':speed_fates,
        'original_input_mutated':False,'training_label_allowed':False}
    return result


def simulate_batch(battles,*,timeout=90):
    extension_contract()
    result=v11.simulate_batch(battles,timeout=timeout)
    result['start_context_compiler_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['start_context_evidence_sha256']=PROOF_SHA
    return result
