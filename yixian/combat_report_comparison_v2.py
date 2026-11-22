"""Audit the declared195 representation migration without dropping battle data.

Every old terminal, per-turn state, RNG flag and settlement field is retained.
Only the exact native195 input/coverage -> v79 context translation is allowed;
new195 event diagnostics have no old counterpart and are validated separately.
"""
from copy import deepcopy
from .combat_report_comparison_v1 import cases_equal


def v79_contract_only_change(previous,current):
    if cases_equal(previous,current):return False
    from .full_battle_v79r2 import PROOF_SHA
    try:
        expected=deepcopy(previous);c=expected['compiled'];b=c['battle']
        entries=[];owners=[]
        for i,p in enumerate(c['effect_players']):
            if 197 in p['fates']:return False
            own=[195] if 195 in p['fates'] else []
            entries.append({'fate_ids':own,'starting_raw_cards':deepcopy(c['declared_components'][i]['raw_cards'])})
            if not own:continue
            owners.append(i)
            if b['players'][i].pop('spirit_hexagram_evolves_stacks')!=1:return False
            if expected['simulation']['initial'][i].pop('spirit_hexagram_evolves_stacks')!=1:return False
            cf=c['declared_components'][i]['compiled_fates']
            if cf['player_fields'].pop('spirit_hexagram_evolves_stacks')!=1:return False
            old_coverage=cf['coverage'];cf['coverage']=[x for x in old_coverage if x['raw_id']!=195]
            if len(old_coverage)-len(cf['coverage'])!=1:return False
        if not owners:return False
        b['hexagram_fates']={'players':entries}
        c['hexagram_fates_v79_context']={'evidence_sha256':PROOF_SHA,'ownership_from_start':True,'original_board_required':True,'training_label_allowed':False}
        meta=current['simulation']['hexagram_fates_v79']
        if set(meta)!={'evidence_sha256','events','players','recorded_action_log','training_label_allowed'}:return False
        if meta['evidence_sha256']!=PROOF_SHA or meta['recorded_action_log'] is not False or meta['training_label_allowed'] is not False:return False
        #195 lifecycle is part of the new diagnostics, not an old observable.
        pending={0:False,1:False}
        for e in meta['events']:
            i=e['player_index']
            if i not in owners or e['fate_id']!=195:return False
            if e['phase']=='positive_qi_add439':
                if set(e)!={'fate_id','phase','player_index','active_player_index','amount'}:return False
                if pending[i] or e['active_player_index'] not in (0,1) or type(e['amount']) is not int or e['amount']<=0:return False
                pending[i]=True
            elif e['phase']=='owner_turn_end_add_hexagram_then_remove439':
                if set(e)!={'fate_id','phase','player_index','before','after'} or not pending[i]:return False
                for field in ('before','after'):
                    if set(e[field])!={'hp','max_hp','qi','hexagram','def','weaken','flaw','internal_injury'}:return False
                    if any(type(v) is not int for v in e[field].values()):return False
                pending[i]=False
            else:return False
        players={p['player_index']:p for p in meta['players']}
        if set(players)!={0,1} or len(meta['players'])!=2:return False
        hex_bases={4000001,4000002,4000003,4000015,4000016,4000025,4000026,4000034}
        hex_ids={x+g*10000 for x in hex_bases for g in range(3)}
        for i,e in enumerate(entries):
            wanted={'player_index':i,'fate_ids':e['fate_ids'],'qualifying_start_count':sum(x in hex_ids for x in e['starting_raw_cards']),'explain_active':False,'pending439':pending[i]}
            if players[i]!=wanted:return False
        expected['simulation']['hexagram_fates_v79']=deepcopy(meta)
        return cases_equal(expected,current)
    except (KeyError,TypeError,ValueError):return False
