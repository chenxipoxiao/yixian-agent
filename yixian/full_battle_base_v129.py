"""Complete two-deck diagnostics with strict start-state preparation.

Executes cards, turns and death in pinned yisim; separately measures agreement
with the current replay version. A mapped ID is not a parity certificate.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from .effects import EffectEngine
from .ranked_rules import ranked_context
from .combat_initiative import compare_initiative_candidates
from .simulator import engine_contract, SimulatorError
from .talent_adapter import compile_talents, SUPPORTED_TALENT_IDS, KNOWN_INCOMPATIBILITIES

ROOT=Path(__file__).resolve().parents[1]
BRIDGE=ROOT/'tools/full_battle_bridge.mjs'
PREPARATION_FATES={7,24,27,29,45,65,83,85,86,105,129,154}
PERMANENT_FIELDS={'17','10000','10022','10023','10024','10012','10045','10056','369'}


from .full_battle import UnresolvedBattle  # retain ancestor exception identity


def _integer(source,field,minimum=0):
    value=source.get(field)
    if type(value) is not int or value<minimum or value>1_000_000:
        raise UnresolvedBattle(f'Explicit valid {field} required')
    return value


def _ids(source,field):
    value=source.get(field)
    if not isinstance(value,list) or any(type(x) is not int for x in value):
        raise UnresolvedBattle(f'Explicit {field} array required')
    return value


def catalogue():
    table=ROOT/'data/local/2026-11-06/tables/CardConfig.json'
    mapping=ROOT/'data/inspection/card-mapping.json'
    cards={r['id']:r for r in json.loads(table.read_text(encoding='utf-8'))}
    candidate={r['client_id']:r['simulator_id'] for r in json.loads(mapping.read_text(encoding='utf-8'))['mappings']}
    candidate[0]='601011'  # Explicit ordinary attack, not a fabricated empty slot.
    talents={r['id']:r for r in json.loads((ROOT/'data/local/2026-11-06/tables/TalentConfig.json').read_text(encoding='utf-8'))}
    season={r['id']:r for r in json.loads((ROOT/'data/local/2026-11-06/season/XianMoStrategyConfig.json').read_text(encoding='utf-8'))}
    return cards,candidate,talents,season


def derive_start_initiative(row, *, game_mode=3):
    players=[]
    for player in row['players']:
        s=player['candidate_start']
        players.append({'lastRoundData':{'exp':s['exp'],'talents':s['talents'],
            'usedKeYinCards':s['used_keyin_cards'],'permanentBuffTempDatas':s['permanentBuffTempDatas']}})
    return compare_initiative_candidates(players,game_mode=game_mode)


def compile_start(row, *, first_player=None, seed, game_mode, season_mec, combat_context,
                  max_turns=128, include_trace=True, tables=None, _cloud_record_guard=None):
    """Read start fields only. The caller chooses initiative, never a winner.

    Replay has no direct initial HP: use the frozen client realm initializer.
    Non-battle metadata is a diagnostic scope declaration, not effect parity.
    Unknown permanent/engraving/active effects reject the entire battle.
    """
    context=ranked_context(version=row['source_rules_version'],game_mode=game_mode,season_mec=season_mec)
    cards,mapping,talents,season=tables or catalogue()
    facts=json.loads((ROOT/'data/inspection/full-battle-patches-v1.json').read_text(encoding='utf-8'))
    runtime_season=set(facts['season_runtime_callsite_ids'])
    if not isinstance(combat_context,dict) or (combat_context.get('game_mode'),combat_context.get('season_mec'))!=(game_mode,season_mec):
        raise UnresolvedBattle('Explicit matching combat context required')
    if combat_context.get('source_raw_sha256')!=row.get('source',{}).get('raw_sha256'):
        raise UnresolvedBattle('Combat context source mismatch')
    initiative_source='explicit_environment_first_player'
    if first_player is None:
        first_player=derive_start_initiative(row,game_mode=game_mode)['candidate_first_index']
        initiative_source='independent_start_speed_comparison'
    if first_player not in (0,1) or type(first_player) is not int:
        raise UnresolvedBattle('Unknown initiative')
    players=[];effect_players=[];declared=[]
    if len(row.get('players',[]))!=2:raise UnresolvedBattle('Two start snapshots required')
    for index,p in enumerate(row['players']):
        if p.get('snapshot_slot')!=('p1','p2')[index]:raise UnresolvedBattle('Unexpected snapshot order')
        s=p['candidate_start'];board=_ids(s,'board')
        private=combat_context['players'][index]
        if private.get('snapshot_slot')!=p['snapshot_slot']:raise UnresolvedBattle('Context seat mismatch')
        if private.get('public_level')!=s.get('level'):raise UnresolvedBattle('Realm snapshot timing mismatch')
        if type(private.get('is_mirror')) is not bool:raise UnresolvedBattle('Explicit mirror boolean required')
        if private.get('hand_values_are_numeric') is not True:raise UnresolvedBattle('Unknown hand representation')
        hand_count=_integer(private,'hand_count')
        if not 1<=len(board)<=8 or len(board)!=_integer(s,'unlocked_slots',1):
            raise UnresolvedBattle('Board must preserve every unlocked slot')
        unknown=[c for c in board if c not in cards or c not in mapping]
        if unknown:raise UnresolvedBattle('unmapped_cards:'+','.join(map(str,unknown)))
        if _ids(s,'used_keyin_cards'):raise UnresolvedBattle('engraving_execution_pending')
        if _ids(s,'fate_strategies'):raise UnresolvedBattle('old_season_strategies_pending')
        permanent=s.get('permanentBuffTempDatas')
        if not isinstance(permanent,dict) or any(not isinstance(k,str) or type(v) is not int for k,v in permanent.items()):
            raise UnresolvedBattle('Explicit permanent dictionary required')
        unknown=set(permanent)-PERMANENT_FIELDS
        if unknown:raise UnresolvedBattle('permanent_hooks_pending:'+','.join(sorted(unknown)))
        level=_integer(s,'level',1)
        bases={1:40,2:45,3:52,4:62,5:75,6:100}
        extra=s.get('extra_max_hp_modifier')
        if level not in bases or type(extra) is not int:raise UnresolvedBattle('Unknown realm HP')
        hp=bases[level]+extra;physique=max(0,permanent.get('10023',0))
        character=p['character_id'];sect,number=divmod(character,1_000_000)
        if sect not in (1,2,3,4) or number not in range(1,7):raise UnresolvedBattle('Unknown reference character')
        raw={'character':{1:'sw',2:'he',3:'fe',4:'dx'}[sect]+str(number),
             'hp':hp,'max_hp':hp+physique,'qi':0,'def':0,
             'physique':physique,'max_physique':max(0,permanent.get('10024',0)),
             'cultivation':_integer(s,'exp'),'round_number':_integer(row,'round',1),
             'destiny':_integer(s,'destiny',1),'cards':[mapping[c] for c in board],
             'hand_count':hand_count,
             'can_last_stand':int(permanent.get('17',0)>0)}
        if any(c['name'].startswith('残云') for c in (cards[id] for id in board)):
            if _cloud_record_guard is None or not _cloud_record_guard(row, index, board):
                raise UnresolvedBattle('cloud_hand_composition_required')
        fate_ids=_ids(s,'talents');active=[];prepared=[]
        for f in fate_ids:
            if f not in talents:raise UnresolvedBattle(f'unknown_fate:{f}')
            if f in SUPPORTED_TALENT_IDS or f in KNOWN_INCOMPATIBILITIES:active.append(f)
            elif f in PREPARATION_FATES or talents[f].get('isBattleTalent') is False:prepared.append(f)
            else:active.append(f)
        compiled=compile_talents(active,s.get('talentTempDatas'),player=raw)
        if compiled['unsupported']:
            raise UnresolvedBattle('unsupported_combat_fates:'+','.join(map(str,active)))
        for field,amount in compiled['player_fields'].items():raw[field]=raw.get(field,0)+amount
        choices=_ids(s,'xian_mo_strategies');combat_season=[];preparation_season=[]
        for f in choices:
            if f not in season:raise UnresolvedBattle(f'unknown_season_effect:{f}')
            if f in runtime_season and f not in {2011,23062}:combat_season.append(f)
            elif season[f].get('isBattleEffect') is False:preparation_season.append(f)
            else:combat_season.append(f)
        engine=EffectEngine.from_local()
        unknown=set(combat_season)-set(engine.contract()['supported_season_effects'])
        if unknown:raise UnresolvedBattle('unsupported_season_combat:'+','.join(map(str,sorted(unknown))))
        # Toggle state is not present in this projection; never assume enabled.
        if set(combat_season)&{1005,1007,1008,1009}:raise UnresolvedBattle('season_toggle_state_missing')
        if combat_season:raise UnresolvedBattle('season_start_interleaving_pending:'+','.join(map(str,combat_season)))
        if 183 in fate_ids and 23062 in choices:
            # Client OnBattleStarted adds one to talent183's argument, then
            # dispatches a SINGLE ModifyTiPo. Increment its startup parameter,
            # not initial physique (which would apply health/cap hooks twice).
            raw['zen_mind_forging_body_stacks']+=1
        players.append(raw)
        effect_players.append({'fates':fate_ids,'season_choices':choices,'life':raw['destiny'],
                               'talent_counters':deepcopy(s.get('talentTempDatas')),'is_mirror':private['is_mirror']})
        declared.append({'raw_cards':board,'mapped_cards':raw['cards'],'compiled_fates':compiled,
                         'preparation_fates_not_reapplied':prepared,
                         'preparation_season_not_reapplied':[f for f in preparation_season if f!=23062],
                         'season23062_extra_start_physique':int(183 in fate_ids and 23062 in choices)})
    return {'battle':{'players':players,'first_player':first_player,'seed':seed,'max_turns':max_turns,
                      'include_trace':include_trace},
            'context':context,'effect_players':effect_players,'declared_components':declared,
            'initiative_source':initiative_source,
            'initialization':'client realm base + recorded extra HP; physique increases cap only; base qi/def zero',
            'complete_current_rules_verified':False,'training_label_allowed':False}


def simulate_batch(battles, *, timeout=90):
    contract=engine_contract()
    if not isinstance(battles,list) or not battles or len(battles)>1000:raise ValueError('Require 1–1000 battles')
    proc=subprocess.run([shutil.which('node') or 'node','--experimental-default-type=module',str(BRIDGE)],
                        input=json.dumps(battles,ensure_ascii=False,allow_nan=False),encoding='utf-8',
                        text=True,capture_output=True,cwd=ROOT,timeout=timeout)
    if proc.returncode:raise SimulatorError(proc.stderr.strip())
    results=json.loads(proc.stdout)
    if len(results)!=len(battles):raise SimulatorError('Batch result count mismatch')
    return {'results':results,'engine':contract,'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),
            'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'adapter_contract':{'schema':'complete-single-battle-diagnostic-v1',
                'slots':'1-8 explicit unlocked slots; never pad',
                'rules_version':'001.0008.0005','mode':3,'season_mec':10,
                'upstream_contract_preserved':True,'upstream_files_modified':False,
                'settlement':'separate terminal_damage preview; upstream destiny deduction disabled',
                'complete_current_content_coverage':False,'full_match_environment':False},
            'current_server_verified':False,'training_label_allowed':False}
