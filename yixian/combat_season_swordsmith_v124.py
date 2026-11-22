"""Rebound only to private v9 globals by the v124 compiler."""
def compile_start(row,**kwargs):
    extension_contract();projected=deepcopy(row);metadata=[]
    if len(projected.get('players',[]))!=2:raise UnresolvedBattle('Two start snapshots required')
    for player in projected['players']:
        start=player.get('candidate_start',{});fates=start.get('talents');counters=start.get('talentTempDatas')
        if not isinstance(fates,list) or any(type(f) is not int for f in fates) or len(fates)!=len(set(fates)):
            raise UnresolvedBattle('Unique explicit talent list required')
        if not isinstance(counters,dict):raise UnresolvedBattle('Explicit talent dictionary required')
        entry={'native_fates':{EXTRA_FATES[f]:1 for f in fates if f in EXTRA_FATES}}
        if 92 in fates:
            value=counters.get('92',0)
            uncapped=bool({7012,7134}&set(start.get('xian_mo_strategies',[])))
            if type(value) is not int or not (0<=value<=1000000 if uncapped else 0<=value<=18):raise UnresolvedBattle('swordsmith_start_counter_outside_reviewed_range')
            entry['uncapped_season_counter']=uncapped
            entry['swordsmith_start_counter']=value
            entry['counter_key_present']='92' in counters
            counters['92']={'swordsmith_attack_bonus':value}
        start['talents']=[f for f in fates if f not in EXTRA_FATES and not (f==92 and entry.get('uncapped_season_counter'))]
        metadata.append(entry)
    if 'tables' not in kwargs:kwargs['tables']=catalogue()
    result=v8.compile_start(projected,**kwargs)
    for original,raw,effect,entry in zip(row['players'],result['battle']['players'],result['effect_players'],metadata):
        if entry.get('uncapped_season_counter'):raw['swordsmith_stacks']=entry['swordsmith_start_counter']
        for field,value in entry['native_fates'].items():
            if field in raw:raise UnresolvedBattle('Duplicate native effect:'+field)
            raw[field]=value
        effect['fates']=deepcopy(original['candidate_start']['talents'])
        effect['talent_counters']=deepcopy(original['candidate_start']['talentTempDatas'])
    result['current_clear_heart']={'evidence_sha256':PROOF_SHA,'players':metadata,'training_label_allowed':False}
    return result

