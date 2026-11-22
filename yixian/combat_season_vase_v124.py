"""Raw vase identity is retained for new read-only element consumers.

The function is rebound into a private v80 module; its frozen fallback
continues to restore199 and all previous input provenance.
"""
def vase_projection(row,context,tables,facts):
 cards,mapping,_,_=tables;entries=[]
 for index,(player,ctx) in enumerate(zip(row['players'],context['players'])):
  start=player['candidate_start'];fates=start.get('talents')
  if not isinstance(fates,list) or any(type(x)is not int for x in fates) or len(fates)!=len(set(fates)):
   raise UnresolvedBattle('start_context_v80:unique_explicit_talents_required')
  if 199 not in fates:continue
  stored=vase._params(ctx,'privateTalentDatas','199')
  if len(stored) not in (0,3):raise UnresolvedBattle('Explicit three vase slots required')
  if not any(v not in mapping or v not in cards for v in stored):continue
  owned=set(start['xian_mo_strategies'])
  if any(v not in cards for v in stored):raise UnresolvedBattle('start_context_v80:unknown_vase_raw_card')
  if stored[0] not in mapping:raise UnresolvedBattle('start_context_v80:vase_first_slot_unmapped')
  inactive=[i for i in (1,2) if stored[i] not in mapping]
  if not owned&{7085,23058} and any(stored[i] not in facts['reviewed_inactive_vase_raw_ids'] for i in inactive):
   raise UnresolvedBattle('start_context_v80:unreviewed_inactive_vase_card')
  native=[mapping[v] if v and v in mapping else None for v in stored]
  entries.append({'player_index':index,'raw_slots':list(stored),'read_slot_indices':[0],
   'omitted_runtime_slot_indices':inactive,'native_cards':native,
   'additional_raw_metadata_reads':([0,1,2] if 7085 in owned else [1] if 23058 in owned else [])})
 return entries
