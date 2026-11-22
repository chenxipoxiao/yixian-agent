from copy import deepcopy
from .combat_start_context_bindings_v6 import FIELD, SWITCHES, ENGRAVINGS, require

def project_legacy_inputs(row, context, values):
    """Translate validated v6 data, without manufacturing a v77 source hash."""
    projected = deepcopy(row); ctx = deepcopy(context); ctx.pop(FIELD)
    ashes = [[], []]; disabled = []
    for index, player in enumerate(projected['players']):
        owned = player['candidate_start']['xian_mo_strategies']; cp = ctx['players'][index]
        seat = values[index]
        for field, supported in SWITCHES.items():
            ids = sorted(set(owned) & supported)
            if not ids: continue
            entry = {'origin': 'privateData.xianMoData:preparation_switch',
                'source_raw_sha256': row['source']['raw_sha256'], 'environment_only': True,
                'selected_strategy_ids': ids, 'temp_data': {str(x): seat[x] for x in ids}}
            require(field not in cp or cp[field] == entry, 'legacy_switch_conflict')
            cp[field] = entry
        ids = sorted(set(owned) & ENGRAVINGS)
        if ids:
            entry = {'origin': 'privateData.xianMoData.tempDatas:preparation_grid_selection',
                'selected_strategy_ids': ids, 'slots': {str(x): seat[x] for x in ids}}
            require('season_engraving_input' not in cp or cp['season_engraving_input'] == entry, 'legacy_grid_conflict')
            cp['season_engraving_input'] = entry
        ids = sorted(set(owned) & {5001, 5009})
        if ids:
            entry = {'origin': 'privateData.xianMoData.tempDatas:complete_preparation_grid_map',
                'source_raw_sha256': row['source']['raw_sha256'], 'environment_only': True,
                'selected_strategy_ids': ids, 'temp_data': {str(x): seat[x] for x in ids}}
            require('carefree_grid_input' not in cp or cp['carefree_grid_input'] == entry, 'legacy_carefree_conflict')
            cp['carefree_grid_input'] = entry
        if 1010 in owned:
            if seat[1010] != 0:disabled.append(index)
            else:require(ctx.get('_season_batch_v124',{}).get('active1010_players',[]).__contains__(index), 'active1010_unbound')
        if 13015 in owned: ashes[index].append({'strategy_id': 13015, 'slot': seat[13015]})
        player['candidate_start']['xian_mo_strategies'] = [x for x in owned if x not in (1010, 13015)]
    return projected, ctx, ashes, disabled
