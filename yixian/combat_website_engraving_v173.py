"""Source-bound owner slot branch inside the private v21 compiler view."""
def compile_start(row,**kwargs):
    extension_contract();projected=deepcopy(row);entries=[];website_receipts=[]
    context=kwargs.get('combat_context')
    for index,p in enumerate(projected['players']):
        start=p['candidate_start'];choices=start.get('xian_mo_strategies')
        if not isinstance(choices,list) or any(type(v) is not int for v in choices):
            raise UnresolvedBattle('Explicit xian_mo_strategies array required')
        owned=sorted(SUPPORTED.intersection(choices));values=[]
        if owned:
            if len(choices)!=len(set(choices)):raise UnresolvedBattle('Duplicate season choices')
            if (not isinstance(context,dict) or context.get('source_raw_sha256')!=row['source']['raw_sha256']
                    or not isinstance(context.get('players'),list) or len(context['players'])!=2):
                raise UnresolvedBattle('Explicit engraving source context required')
            receipt=_website_engraving_receipt_v173(row,context,index,owned)
            if receipt is not None:
                slots={'13003':receipt['slot']};selected=[13003];website_receipts.append(receipt)
            else:
                data=context['players'][index].get('season_engraving_input')
                if not isinstance(data,dict) or data.get('origin')!=ORIGIN:
                    raise UnresolvedBattle('engraving_preparation_slot_missing:'+str(owned))
                slots=data.get('slots');selected=data.get('selected_strategy_ids')
            if not isinstance(slots,dict) or selected!=owned:
                raise UnresolvedBattle('engraving_preparation_ownership_mismatch:'+str(owned))
            for identifier in owned:
                slot=slots.get(str(identifier))
                # Client default zero is not evidence of an omitted replay field.
                if type(slot) is not int or not 0<=slot<8:
                    raise UnresolvedBattle('engraving_preparation_slot_missing:'+str(identifier))
                values.append({'strategy_id':identifier,'slot':slot})
            start['xian_mo_strategies']=[v for v in choices if v not in SUPPORTED]
        entries.append(values)
    result=v17.compile_start(projected,**kwargs)
    if any(entries):
        result['battle']['season_engraving']={'players':entries}
        if any(e['strategy_id'] in (13003,13007) for values in entries for e in values):
            result['battle']['season_transform_cards']={'players':[
                p['candidate_start']['board'][:p['candidate_start']['unlocked_slots']] for p in row['players']]}
        for source,effect in zip(row['players'],result['effect_players']):
            effect['season_choices']=deepcopy(source['candidate_start']['xian_mo_strategies'])
        result['current_engraving_context']={'evidence_sha256':PROOF_SHA,'slots_origin':ORIGIN,
            'scope':'environment calibration only; never opponent policy observation',
            'round_or_battle_counters_imported':False,'training_label_allowed':False}
    if website_receipts:
        result['current_engraving_context']['slots_origin']='source-bound website prebattle enchantedSlot'
        result['current_engraving_context']['website_receipts_v173']=website_receipts
    return result
