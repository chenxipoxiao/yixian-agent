"""Website-only1010 receipt branch; rebound inside the frozen private v77 view.

All names except the function arguments are supplied by that private module.
Legacy receipts retain the exact frozen checks and are not relabelled.
"""
def compile_start(row,**kwargs):
 extension_contract();projected=deepcopy(row);context=deepcopy(kwargs.get('combat_context'));entries=[[],[]];used=[];disabled=[];website_used=False
 for i,p in enumerate(projected['players']):
  choices=p['candidate_start'].get('xian_mo_strategies')
  if not isinstance(choices,list) or any(type(x) is not int for x in choices):raise UnresolvedBattle('Explicit season choices required')
  if not isinstance(context,dict) or not isinstance(context.get('players'),list) or len(context['players'])!=2:
   if any(x in choices for x in [1010,13015]):raise UnresolvedBattle('preparation_v77:context_required')
   continue
  cp=context['players'][i];ids=required_ids(row['players'][i],cp)
  if not ids:continue
  if len(choices)!=len(set(choices)):raise UnresolvedBattle('Duplicate season choices')
  if 1010 in ids and cp.get('website_owner_preparation_v137') is not None:
   values=_website_validate_1010(row,i,cp,ids,context)
   record_source=cp['website_owner_preparation_v137'];website_used=True
  else:
   if context.get('source_raw_sha256')!=row['source']['raw_sha256'] or context.get('engraving_source_projection_sha256')!=PROJECTION_SHA:
    raise UnresolvedBattle('preparation_v77:source_mismatch')
   try:values=validate_entry(row,i,cp.get(FIELD),ids)
   except ValueError as e:raise UnresolvedBattle(str(e)) from e
   record_source=cp[FIELD]
  for id,value in values.items():
   if id==1010:
    if value==0:
     if i not in context.get('_season_batch_v124',{}).get('active1010_players',[]):raise UnresolvedBattle('preparation_v77:active1010_unbound')
    else:disabled.append(i)
   elif id==13015:entries[i].append({'strategy_id':id,'slot':value})
   else:
    engraving=cp.get('season_engraving_input')
    if not isinstance(engraving,dict) or not isinstance(engraving.get('slots'),dict) or str(id) in engraving['slots']:
     raise UnresolvedBattle('preparation_v77:legacy_slot_conflict')
    engraving['slots'][str(id)]=value
  p['candidate_start']['xian_mo_strategies']=[x for x in choices if x not in [1010,13015]]
  used.append({'player_index':i,'values':values,'source':deepcopy(record_source)})
 if context is not None:kwargs={**kwargs,'combat_context':context}
 result=v76.compile_start(projected,**kwargs)
 if any(entries):
  engraving=result['battle'].setdefault('season_engraving',{'players':[[],[]]})
  for i,es in enumerate(entries):engraving['players'][i].extend(es);engraving['players'][i].sort(key=lambda x:x['strategy_id'])
 if used:
  for i,p in enumerate(row['players']):result['effect_players'][i]['season_choices']=deepcopy(p['candidate_start']['xian_mo_strategies'])
  key='website_preparation_v139_context' if website_used else 'preparation_v77_context'
  result[key]={'legacy_execution_evidence_sha256' if website_used else 'evidence_sha256':PROOF_SHA,
      'bindings':used,'disabled1010_players':disabled,'training_label_allowed':False}
 return result
