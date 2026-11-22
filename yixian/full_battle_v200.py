"""Exact recorded season/paper compositions, environment-only."""
from types import FunctionType
from . import full_battle_v198 as previous
from .combat_compiler_view_v81 import compiler_modules, isolated_compiler
from .full_battle_v45 import digest_json

catalogue = previous.catalogue
derive_start_initiative = previous.derive_start_initiative
UnresolvedBattle = previous.UnresolvedBattle
RECORDS = {
    "replay-c9b7dee0a0109c0ece335076e83813e7c258e63bfb2ccae59901c6b85dc8ca0a-round-9": [
        "481a8b743faa97939fa4e5560f6d3c3f259e8af0ee2b684e028e407586ca52b5",
        "24b2bc74b5e444856ccbc3993096ad51c890c18b9bd923eec4de6bdc5960e9ae"
    ],
    "replay-c9b7dee0a0109c0ece335076e83813e7c258e63bfb2ccae59901c6b85dc8ca0a-round-13": [
        "b9e5d52ba9ad2c1a39db5e5f070cf3b0b170a6891e94ffa15a1e5f34c0d08ce4",
        "0f1303ec1c83d9cfac3f8a73c4cb75d71f257fd1557df642fb286dab68a6a84a"
    ],
    "replay-c9b7dee0a0109c0ece335076e83813e7c258e63bfb2ccae59901c6b85dc8ca0a-round-14": [
        "2a3c5393b49fe7b6148f9c44932e98c06d1aea1cbdc0a8124dccd127707924ac",
        "d90fecdd93b2c5ed3accc4499660264e7954fd39d6aa38bb60cf7beffdbf6ddf"
    ],
    "replay-c9b7dee0a0109c0ece335076e83813e7c258e63bfb2ccae59901c6b85dc8ca0a-round-15": [
        "88aaaaf070bfba8ee8f0d6a8e989d83ec15687ab0d4cfd158a86b696863846fb",
        "683ae8cfd6817d7dde7c79495c11c388ed6bf2857bfaedf21a6f412470b65422"
    ],
    "replay-c9b7dee0a0109c0ece335076e83813e7c258e63bfb2ccae59901c6b85dc8ca0a-round-17": [
        "a36eac866b5381095c1fdbb23ccd136e73d753d3419c70b82dbc72b67aec7491",
        "8950fa69ed12bd14915f8e7105f61af378e131ba20ae813a94e802435599ed3d"
    ],
    "replay-c9b7dee0a0109c0ece335076e83813e7c258e63bfb2ccae59901c6b85dc8ca0a-round-18": [
        "0d63f9b185b333767f17172b53672c6d9682836fbd3718cd041702f47d8eb816",
        "08422aaecad4ecfba56ee770e203b63e6c6b3f8a6fa4990b7ed6551366befe06"
    ]
}

def compile_start(row, **kwargs):
    expected = RECORDS.get(row.get('id'))
    if expected is None:
        return previous.compile_start(row, **kwargs)
    context = kwargs.get('combat_context')
    start = {k:v for k,v in row.items() if k != 'outcome'}
    if [digest_json(start), digest_json(context)] != expected:
        raise UnresolvedBattle('season_paper:recorded_start_changed')
    if (kwargs.get('game_mode'),kwargs.get('season_mec')) != (3,10):
        raise UnresolvedBattle('season_paper:unverified_mode')
    view = isolated_compiler(previous)
    batch = compiler_modules(view)['yixian.full_battle_v124']
    batch.compile_owned_start = FunctionType(compile_paper_batch.__code__, vars(batch))
    result = view.compile_start(start, **kwargs)
    payload = result['battle']
    if payload['falling_paper']['battle_sha256'] != digest_json({k:v for k,v in payload.items() if k!='falling_paper'}):
        raise UnresolvedBattle('season_paper:final_payload_changed')
    return result

def compile_paper_batch(row,context,values,ids,facts,**kwargs):
 players=[];engravings=[[],[]]
 for i,p in enumerate(row['players']):
  source=p['candidate_start'];data={'ids':ids[i],'raw_cards':deepcopy(source['board'])};owned=set(ids[i])
  required=owned&SWITCH_IDS
  if not required<=set(values[i]):raise UnresolvedBattle('season_batch_v124:explicit_switch_required:'+','.join(map(str,sorted(required-set(values[i])))))
  if required:data['switches']={str(x):values[i][x]==0 for x in sorted(required)}
  for x in sorted(owned&GRID_IDS):
   if x not in values[i]:raise UnresolvedBattle('season_batch_v124:explicit_grid_required:'+str(x))
   slot=values[i][x]
   if type(slot)is not int or not 0<=slot<len(source['board']):raise UnresolvedBattle('season_batch_v124:invalid_grid')
   engravings[i].append({'strategy_id':x,'slot':slot})
  if 7024 in owned:
   if not isinstance(source.get('permanentBuffTempDatas'),dict):raise UnresolvedBattle('season_batch_v124:complete_permanent_map_required')
   data['permanent']=deepcopy(source['permanentBuffTempDatas'])
  if owned&{7085,23058}:
   from .full_battle_v13 import _params
   if 199 in source['talents']:data['vase']=_params(context['players'][i],'privateTalentDatas','199')
   else:data['vase']=[]  # Explicit absence of the owning fate, not a missing field.
   if len(data['vase']) not in (0,3):raise UnresolvedBattle('season_batch_v124:explicit_vase_slots')
  players.append(data)
 # This marker is not accepted from callers and is added only after checking
 #the immutable original receipts. It authorizes the narrow1010 projection.
 if '_season_batch_v124' in context:raise UnresolvedBattle('season_batch_v124:external_private_marker')
 translated=deepcopy(context)
 translated['_season_batch_v124']={'active1010_players':[i for i,p in enumerate(players) if 1010 in p['ids']]}
 view=isolated_compiler(previous);modules=compiler_modules(view);leaf=modules['yixian.full_battle']
 leaf._V124_IDS=set(facts['implemented_ids'])-{13002,3013}
 if any(7024 in x for x in ids):leaf.PERMANENT_FIELDS=set(leaf.PERMANENT_FIELDS)|{'10037'}
 leaf.compile_start=rebind(batch_leaf,leaf)
 # v123 makes another private leaf when7120 is present; retain this extension.
 modules['yixian.full_battle_v123'].compile_7120_leaf=batch_leaf
 for name in ('yixian.full_battle_v105','yixian.full_battle_v107'):
  modules[name].project_legacy_inputs=project_legacy_inputs
 modules['yixian.full_battle_v77'].compile_start=rebind(batch_preparation,modules['yixian.full_battle_v77'])
 from .combat_season_swordsmith_v124 import compile_start as swordsmith_start
 modules['yixian.full_battle_v9'].compile_start=rebind(swordsmith_start,modules['yixian.full_battle_v9'])
 from .combat_season_vase_v124 import vase_projection
 modules['yixian.full_battle_v80']._vase_projection=rebind(vase_projection,modules['yixian.full_battle_v80'])
 result=view.compile_start(row,**{**kwargs,'combat_context':translated})
 if result['context'].get('resonance_selected')!=0:raise UnresolvedBattle('season_batch_v124:no_resonance_required')
 battle=result['battle']
 if any('parameter' in key or key=='falling_paper' for key in battle):
  from .full_battle_v45 import digest_json
  paper = battle.get('falling_paper', {})
  owners = [16024 in p['candidate_start']['xian_mo_strategies'] for p in row['players']]
  plain = {k:v for k,v in battle.items() if k!='falling_paper'}
  binding = {'snapshot_sha256':snapshot_binding(row,context),'scope':'unchanged_recorded_battle_only'}
  if (any('parameter' in k for k in plain) or context.get('falling_paper_record')!=binding
      or paper.get('owners')!=owners or paper.get('stream')!=context.get('battle_params')
      or paper.get('battle_sha256')!=digest_json(plain)):
   raise UnresolvedBattle('season_paper:original_binding_required')
 battle['season_batch']={'players':players,'source_binding':{'snapshot_sha256':snapshot_binding(row,context),
  'record_id':row['id'],'environment_only':True,'counterfactual_reuse_allowed':False}}
 if any(engravings):
  engraving=battle.setdefault('season_engraving',{'players':[[],[]]})
  for i,entries in enumerate(engravings):engraving['players'][i].extend(entries);engraving['players'][i].sort(key=lambda x:x['strategy_id'])
 for i,p in enumerate(row['players']):result['effect_players'][i]['season_choices']=deepcopy(p['candidate_start']['xian_mo_strategies'])
 result['season_batch_context_v124']={'evidence_sha256':PROOF_SHA,'ids':ids,'original_start_preserved':True,
  'private_inputs_bound_before_projection':True,'training_label_allowed':False}
 if 'falling_paper' in battle:
  battle['falling_paper']['battle_sha256']=digest_json({k:v for k,v in battle.items() if k!='falling_paper'})
 return result
