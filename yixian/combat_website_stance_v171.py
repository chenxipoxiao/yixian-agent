"""Private v15 leaf extension; only a source-validated27023/206 receipt is new.

This function is rebound into an isolated v15 namespace. All other names and
the preceding/following compiler contracts remain the frozen v15 definitions.
"""
def compile_start(row, **kwargs):
    extension_contract()
    projected = deepcopy(row)
    extra, admitted = [], []
    for index, p in enumerate(projected['players']):
        s = p['candidate_start']
        fates = s.get('talents')
        native = {}
        if (not isinstance(fates, list) or any(type(v) is not int for v in fates)
                or len(set(fates)) != len(fates)):
            raise UnresolvedBattle('Unique explicit talents required')
        if {206, 209} & set(fates) and p['character_id'] != 4000005:
            receipt = _website_stance_receipt_v171(row, kwargs.get('combat_context'), index)
            if receipt is None or 209 in fates or 206 not in fates:
                raise UnresolvedBattle('Non-native stance fate context pending')
            admitted.append(receipt)
        if p['character_id'] == 4000005:
            native['stance'] = 1
        for fate, field in [(153, 'unbounded_qi_stacks'),
                            (206, 'indomitable_will_stacks'),
                            (209, 'surge_of_qi_stacks')]:
            if fate in fates:
                native[field] = 1
        s['talents'] = [f for f in fates if f not in (153, 206, 209)]
        extra.append(native)
    result = v14.compile_start(projected, **kwargs)
    for p, raw, effect, native in zip(row['players'], result['battle']['players'],
                                    result['effect_players'], extra):
        for key, val in native.items():
            if key in raw:
                raise UnresolvedBattle('Duplicate native state:' + key)
            raw[key] = val
        effect['fates'] = deepcopy(p['candidate_start']['talents'])
    result['current_qi_stance'] = {
        'evidence_sha256': PROOF_SHA, 'players': extra, 'training_label_allowed': False}
    if admitted:
        result['current_qi_stance']['website_extension_v171'] = admitted
    return result
