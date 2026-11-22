"""Explain frozen v11 exclusions, without executing or relaxing combat rules."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.full_battle_v11 import catalogue, compile_start, derive_start_initiative, UnresolvedBattle

LABELS = {
    'unmapped_cards': '卡牌尚未接入当前完整战斗入口',
    'unsupported_season_combat': '百家效果未完成接入或阶段分类',
    'season_start_interleaving_pending': '已有百家开局组件，但整场触发顺序未接通',
    'unknown_season_effect': '跳过百家记录被误当作未知仙命ID',
    'unsupported_combat_fates': '普通仙命缺少执行映射或存在版本差异',
    'permanent_hooks_pending': '永久字段尚未确认开战转换/保留方式',
    'Mirror/unknown mirror context': '镜像战斗不在当前准入范围',
    'Explicit valid destiny required': '开战命元为0被严格校验拒绝',
    'Conditional talent family128 needs element/card metadata': '条件速度计算没有接入五行元数据',
    'cloud_hand_composition_required': '残云牌需要手牌组成，当前投影只保留数量',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def clean(value):
    return str(value).replace('|', '\\|').replace('\r', '').replace('\n', '；')


def explain(report_path, pilot_path, context_path, out):
    out.mkdir(parents=True, exist_ok=True)
    report, contexts = read(report_path), read(context_path)
    assert sha(pilot_path) == report['source_sha256']
    assert sha(context_path) == report['context_sha256']
    rows = {r['id']: r for r in map(json.loads, pilot_path.read_text(encoding='utf-8').splitlines())}
    tables = catalogue()
    cards, mapping, talents, season = tables
    catalog_path = ROOT/'data/local/2026-11-06/combat-fates.json'
    entries = {(r['namespace'], r['id']): r for r in read(catalog_path)['entries']}
    characters_path = ROOT/'data/local/2026-11-06/tables/CharacterConfig.json'
    characters = {r['id']: r['name'] for r in read(characters_path)}
    skip_path = ROOT/'data/inspection/current-season-logic.json'
    logic = read(skip_path)
    skip = [m for m in logic['methods'] if m['type'] == 'XianMoModule' and m['name'] == 'IsSkipStrategy']
    assert len(skip) == 1
    assert skip[0]['instructions'] == [
        ['0x1', 'ldarg.0', None], ['0x2', 'ldc.i4', '1000'],
        ['0x7', 'clt', None], ['0x9', 'ret', None],
    ]
    assert logic['source_sha256'] == sha(ROOT/'data/local/2026-11-06/raw/DarkSun.HotUpdate.dll')
    observed = Counter()
    items = []
    named = defaultdict(Counter)
    fate_groups = Counter()
    cooccurring_board_records = 0
    for excluded in report['excluded']:
        row = rows[excluded['record_id']]
        assert row['split'] == 'train'
        context = contexts[row['id']]
        origin = None
        unsupported = []
        try:
            initiative = derive_start_initiative(row, game_mode=context['game_mode'])
            first = (None if initiative['candidate_first_index'] is not None else
                     {'p1': 0, 'p2': 1}.get(row['outcome'].get('first_player_snapshot_slot')))
            compile_start(row, first_player=first, seed='diagnostic-'+row['id'],
                          game_mode=context['game_mode'], season_mec=context['season_mec'],
                          combat_context=context, tables=tables)
        except (UnresolvedBattle, ValueError) as error:
            assert str(error) == excluded['reason'], (row['id'], str(error), excluded['reason'])
            tb = error.__traceback__
            while tb:
                frame = tb.tb_frame
                if (Path(frame.f_code.co_filename).resolve() == ROOT/'yixian/full_battle.py'
                        and frame.f_code.co_name == 'compile_start'):
                    origin = frame.f_locals.get('index')
                    compiled = frame.f_locals.get('compiled')
                    if excluded['reason'].startswith('unsupported_combat_fates:') and isinstance(compiled, dict):
                        unsupported = [{k: u[k] for k in ('raw_id', 'name', 'reason')}
                                       for u in compiled['unsupported']]
                tb = tb.tb_next
        else:
            raise AssertionError('Frozen excluded record unexpectedly compiled: '+row['id'])
        reason = excluded['reason']
        category, _, raw_suffix = reason.partition(':')
        assert category in LABELS, category
        observed[category] += 1
        ids = [int(x) for x in raw_suffix.split(',')] if raw_suffix else []
        details = []
        if category == 'unmapped_cards':
            for raw in sorted(set(ids)):
                card = cards[raw]
                details.append({'id': raw, 'name': card['name'], 'level': card['level'],
                                'description': card.get('description_preview', card.get('desc')),
                                'in_current_mapping': raw in mapping})
            named[category].update(set(d['name'] for d in details))
        elif category in ('unsupported_season_combat', 'season_start_interleaving_pending'):
            for raw in ids:
                e = entries[('season', raw)]
                details.append({'id': raw, 'name': e['name'], 'npc_name': e['npc_name'],
                                'description': e['description'], 'configuration_battle_flag': season[raw]['isBattleEffect']})
            named[category].update(d['name'] for d in details)
        elif category == 'unsupported_combat_fates':
            assert unsupported
            for u in unsupported:
                e = entries[('regular', u['raw_id'])]
                details.append({**u, 'description': e['description']})
            named[category].update(d['name'] for d in details)
            fate_groups[tuple(d['name'] for d in details)] += 1
        elif category == 'unknown_season_effect':
            assert all(0 < raw < 1000 and raw not in season for raw in ids)
            details = [{'id': raw, 'meaning': 'XianMoModule.IsSkipStrategy(id) is true',
                        'classification_corrected': True, 'battle_adapter_fixed': False} for raw in ids]
            named[category].update(str(raw) for raw in ids)
        elif category == 'permanent_hooks_pending':
            details = [{'id': raw, 'value': row['players'][origin]['candidate_start']['permanentBuffTempDatas'][str(raw)]} for raw in ids]
        elif category == 'Mirror/unknown mirror context':
            assert origin in (0, 1) and context['players'][origin]['is_mirror'] is True
            details = [{'is_mirror': True, 'missing_flag': False}]
        elif category == 'Explicit valid destiny required':
            value = row['players'][origin]['candidate_start']['destiny']
            assert value == 0
            details = [{'recorded_start_destiny': value, 'required_minimum': 1}]
        elif category == 'Conditional talent family128 needs element/card metadata':
            details = [{'snapshot_slot': p['snapshot_slot'], 'talents': [f for f in p['candidate_start']['talents'] if f % 10000 == 128]} for p in row['players']]
        elif category == 'cloud_hand_composition_required':
            details = [{'id': raw, 'name': cards[raw]['name'], 'description': cards[raw].get('description_preview')}
                       for p in row['players'] for raw in p['candidate_start']['board']
                       if cards[raw]['name'].startswith('残云')]
        other_board = [{'snapshot_slot': p['snapshot_slot'], 'ids': sorted(set(raw for raw in p['candidate_start']['board'] if raw not in mapping))}
                       for p in row['players']]
        has_board = any(p['ids'] for p in other_board)
        cooccurring_board_records += int(has_board)
        items.append({
            'number': len(items)+1, 'record_id': row['id'], 'game_id': row['game_id'],
            'round': row['round'], 'rules_version': row['source_rules_version'],
            'characters': [characters[p['character_id']] for p in row['players']],
            'original_first_reason': reason, 'category': category, 'explanation': LABELS[category],
            'first_blocked_slot': ('p1', 'p2')[origin] if origin in (0, 1) else None,
            'details': details,
            'unmapped_boards_both_players_static_inventory': other_board,
            'remaining_checks_not_exhaustively_run': True,
            'combat_executed': False, 'training_label_allowed': False,
        })
    assert len(items) == 303
    assert dict(observed) == report['summary']['exclusion_counts']
    sources = [report_path, pilot_path, context_path, catalog_path, characters_path, skip_path,
               ROOT/'yixian/full_battle.py', ROOT/'yixian/talent_adapter.py', Path(__file__)]
    summary = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'records': len(items), 'games': len({x['game_id'] for x in items}),
        'first_blocker_counts': dict(observed),
        'named_first_blocker_counts': {k: dict(v.most_common()) for k, v in named.items()},
        'actual_fate_blocker_combinations': [{'fates': list(k), 'records': v} for k,v in fate_groups.most_common()],
        'skip_marker_records_identified': observed['unknown_season_effect'],
        'all_mirror_flags_explicit_true': True,
        'all_exclusions_reproduced_without_simulation': True,
        'records_with_any_unmapped_card_in_either_player': cooccurring_board_records,
        'cards_are_static_inventory_not_new_execution_results': True,
        'no_source_or_model_changes': True, 'S2_accepted': False,
        'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sources},
        'limitations': ['first blocker counts are mutually exclusive, named content counts can overlap',
                        'current execution report unchanged; identification does not imply a repair or newly passing battle',
                        'source training pilot already used for diagnosis, not independent acceptance'],
    }
    result = {'summary': summary, 'records': items}
    with (out/'blockers-detail.json').open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    lines = ['# 303条完整战斗阻断原因逐条核对', '',
             '这些记录尚未执行完完整战斗，不是303条已算错的战果。原有222条可执行结果与训练准入状态不变。', '',
             '本次重新通过同一个冻结入口核对全部303条，首个阻断原因全部复现。以下按首个阻断点计数，一条记录可另有未到达的缺口。', '',
             '| 首个阻断原因 | 条数 |', '| --- | ---: |']
    for key, count in observed.items():
        lines.append(f'| {LABELS[key]} | {count} |')
    lines += ['', '新澄清：21条小ID（1、5、7、10、13、15）满足当前客户端 IsSkipStrategy 的 id<1000 判定，属于跳过记录；原完整战斗入口误当作未知仙命。这里只更正原因，尚未修改冻结战斗入口。', '',
              '23条普通仙命阻断中，旧错误字符串列出的筋骨健壮、占星、布星问卦、百草生息已经有映射，不应算作实际不支持项。真正阻断为下表组合：', '',
              '| 实际阻断仙命组合 | 条数 |', '| --- | ---: |']
    for group, count in fate_groups.most_common():
        lines.append(f'| {"、".join(group)} | {count} |')
    for category in ('unmapped_cards', 'unsupported_season_combat', 'season_start_interleaving_pending'):
        lines += ['', f'## {LABELS[category]}：涉及内容', '', '| 名称 | 涉及首阻断记录数 |', '| --- | ---: |']
        for name, count in named[category].most_common():
            lines.append(f'| {clean(name)} | {count} |')
    lines += ['', '## 303条明细', '',
              '完整记录ID、来源整局ID、原始原因、两侧额外未映射牌清单与配置说明保存在同目录 blockers-detail.json。这里的序号与JSON一一对应；回放ID本身的round后缀不是显示轮次，以下使用记录中的真实轮次。', '',
              '| 序号 | 记录简称 | 第几轮 | 双方角色 | 阻断原因 | 具体内容 |',
              '| ---: | --- | ---: | --- | --- | --- |']
    for item in items:
        specifics = []
        for d in item['details']:
            if 'name' in d: specifics.append(f"{d['name']}（{d.get('id',d.get('raw_id'))}）")
            elif 'id' in d: specifics.append(str(d['id']))
            else: specifics.append(json.dumps(d, ensure_ascii=False, separators=(',', ':')))
        lines.append(f"| {item['number']} | {item['record_id'][7:19]} | {item['round']} | {' / '.join(item['characters'])} | {clean(item['explanation'])} | {clean('；'.join(specifics))} |")
    with (out/'blockers-detail.md').open('x', encoding='utf-8') as f:
        f.write('\n'.join(lines)+'\n')
    print(json.dumps({k: summary[k] for k in ('records','games','first_blocker_counts','actual_fate_blocker_combinations','records_with_any_unmapped_card_in_either_player')}, ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--pilot', type=Path, required=True)
    parser.add_argument('--context', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    explain(args.report.resolve(), args.pilot.resolve(), args.context.resolve(), args.out.resolve())
