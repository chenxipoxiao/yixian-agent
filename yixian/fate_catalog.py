"""Readable fate inventory with explicit, component-level execution coverage.

Classification is a search aid based on configuration flags and description
patterns, not a recovered event program. Descriptions never become executable
rules automatically. Whole-effect support and component support stay separate.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PHASES = ('battle_start', 'card_play', 'attack', 'turn_start', 'turn_end',
          'battle_end', 'death_prevention', 'acquisition_buff', 'ongoing_combat')
PHASE_LABELS = {'battle_start':'战斗开始', 'card_play':'出牌触发', 'attack':'攻击/受击',
                'turn_start':'回合开始', 'turn_end':'回合结束', 'battle_end':'战后结算',
                'death_prevention':'保命/复活', 'acquisition_buff':'取得时改变战斗属性',
                'acquisition_card_grant':'取得时获得牌', 'conditional_extra_draw':'首轮/突破额外抽牌',
                'ongoing_combat':'持续战斗机制'}
STATUS_LABELS = {'existing_implemented':'已有执行组件', 'legacy_candidate':'旧引擎候选，未接入',
                 'not_implemented':'未实现'}


def _terms(localization):
    return {row['Term']:row.get('Languages', [''])[0]
            for row in localization['mSource']['mTerms'] if row.get('Languages')}


def render_description(template, parameters, *, card_names=None, talent_names=None):
    """Substitute only literal verified fields/indices; never evaluate an expression."""
    def parameter(match):
        key, index = match.group(1), match.group(2)
        value = parameters.get(key)
        if index is not None:
            if not isinstance(value, list) or int(index) >= len(value):
                return match.group(0)
            value = value[int(index)]
        return str(value) if type(value) in (int, float, str) else match.group(0)
    text = re.sub(r'\{([A-Za-z_][A-Za-z_0-9]*)(?:\[(\d+)\])?\}', parameter, template)
    text = text.replace('\\n', '\n')
    text = re.sub(r'<[^>]*>', '', text)
    cards, talents = card_names or {}, talent_names or {}
    def reference(match):
        key = match.group(1)
        if key.startswith('KEYWORD_'):
            return '【'+key[8:]+'】'
        if key.startswith('TALENT_') and key[7:].isdigit():
            name = talents.get(int(key[7:]))
            return '【'+name+'】' if name else match.group(0)
        if key.isdigit() and int(key) in cards:
            return '【'+cards[int(key)]+'】'
        return match.group(0)
    return re.sub(r'【([^】]+)】', reference, text)


def classify(description, *, battle_flag=False):
    """Return a transparent heuristic event index; preserve all matching phases."""
    phases, reasons = [], []
    patterns = {
        'battle_start':r'战斗开始|每场战斗开始|开始战斗',
        'card_play':r'使用.{0,35}(?:后|时)|打出|出牌|每.{0,10}(?:张|次).{0,12}牌|下.{0,8}次使用|卡组.{0,12}(?:格|位)',
        'attack':r'攻击|受到伤害|受伤|造成伤害|反伤|攻击伤害|攻击时|被击',
        'turn_start':r'回合开始|自身回合开始|对方回合开始',
        'turn_end':r'回合结束|自身回合结束|对方回合结束',
        'battle_end':r'战斗结束|战斗胜利|战斗失败|战斗后|每次胜利|胜利.{0,8}场战斗|战败|战胜|败者|命元.{0,12}伤害|伤害.{0,12}命元|损失.{0,8}命元',
        'death_prevention':r'命元耗尽|保留1点命元|不被淘汰|免疫.{0,12}命元|复活|生命耗尽',
    }
    for phase, pattern in patterns.items():
        if re.search(pattern, description):
            phases.append(phase)
            reasons.append({'phase':phase, 'basis':'description_pattern', 'pattern':pattern})
    # Ignore card references when indexing direct attribute changes. Merely
    # receiving a named card is not an implementation of that card's effect.
    stat_text = re.sub(r'【(?:\d+|TALENT_[^】]+)】', '', description)
    stat = re.search(r'生命上限|体魄上限|生命.{0,3}[+＋]|灵气.{0,3}[+＋]|获得.{0,8}(?:剑意|星力|卦象|加攻)|加.{0,8}(?:生命|体魄)', stat_text)
    if stat and not any(x in phases for x in ('battle_start','turn_start','turn_end','card_play','attack','battle_end')):
        phases.append('acquisition_buff')
        reasons.append({'phase':'acquisition_buff','basis':'description_pattern', 'matched':stat.group(0)})
    card_modifier = re.search(r'(?:攻|防)[+＋]|(?:加|减)\d+攻', description)
    if card_modifier and not phases:
        phases.append('ongoing_combat')
        reasons.append({'phase':'ongoing_combat','basis':'description_pattern','matched':card_modifier.group(0)})
    if battle_flag and not phases:
        phases.append('ongoing_combat')
        reasons.append({'phase':'ongoing_combat', 'basis':'configuration_battle_flag'})
    return {'combat_relevant':bool(phases), 'phases':[p for p in PHASES if p in phases],
            'classification_verified':False, 'classification_basis':reasons,
            'limitation':'Configuration/text search classification; execution timing and full rule dependencies need implementation review.'}


def discover_runtime_support():
    """Read declared runtime registries; do not infer support from matching names."""
    from .effects import SUPPORTED_FATES, SUPPORTED_SEASON
    # These original four event handlers have a complete declared-effect audit.
    # A broader execution whitelist is not proof that acquisition, conditional
    # context and interactions have all been implemented.
    result = {'regular':set(SUPPORTED_FATES) & {45, 105},
              'season':set(SUPPORTED_SEASON) & {1001, 2011},
              'partial_regular':{}, 'partial_season':{},
              'legacy_candidate_regular':set(), 'legacy_candidate_season':set(),
              'registry_sources':['yixian.effects.SUPPORTED_FATES', 'yixian.effects.SUPPORTED_SEASON']}
    declarations = [
        ('season_start', 'IMPLEMENTED_SEASON_START_IDS', 'partial_season', ['battle_start']),
        ('death_fates', 'IMPLEMENTED_DEATH_FATES', 'partial_regular', ['death_prevention']),
        ('dragon_scale', 'IMPLEMENTED_DRAGON_SCALE_COMPONENT_IDS', 'partial_regular', ['destiny_damage_cap']),
        ('fate_acquisition', 'IMPLEMENTED_ACQUISITION_FATE_IDS', 'partial_regular', ['acquisition_card_grant']),
        ('dragon_inheritance', 'IMPLEMENTED_INHERITANCE_COMPONENT_IDS', 'partial_regular', ['conditional_extra_draw']),
        ('talent_adapter', 'SUPPORTED_TALENT_IDS', 'partial_regular', ['legacy_battle_adapter']),
    ]
    for module_name, constant, target, components in declarations:
        if not (ROOT/'yixian'/f'{module_name}.py').exists():
            continue
        module = importlib.import_module(f'yixian.{module_name}')
        ids = getattr(module, constant, ())
        for identifier in ids:
            if type(identifier) is not int:
                raise ValueError(f'{module_name}.{constant} must contain integer IDs')
            if identifier in result[target.removeprefix('partial_')]:
                continue
            result[target][identifier] = sorted(set(result[target].get(identifier, ())) | set(components))
        if ids:
            result['registry_sources'].append(f'yixian.{module_name}.{constant}')
    native = ROOT/'tools/season_runtime.mjs'
    if native.exists():
        declaration = re.search(r'export const IMPLEMENTED_SEASON_RUNTIME_IDS = Object\.freeze\((\[[^\]]*\])\);',
                                native.read_text(encoding='utf-8'))
        if declaration is None:
            raise ValueError('Missing literal native season-runtime support declaration')
        for identifier in json.loads(declaration.group(1)):
            if type(identifier) is not int:
                raise ValueError('Native season-runtime IDs must be integers')
            result['partial_season'][identifier] = sorted(set(result['partial_season'].get(identifier, ())) | {'native_battle_runtime'})
        result['registry_sources'].append('tools/season_runtime.mjs:IMPLEMENTED_SEASON_RUNTIME_IDS')
    return result


def _execution(kind, identifier, support):
    partial = support.get('partial_'+kind, {})
    if identifier in partial:
        return {'status':'existing_implemented', 'complete_effect':False,
                'coverage_scope':'component_only', 'components':list(partial[identifier]),
                'current_server_rules_verified':False}
    if identifier in support.get(kind, ()):
        return {'status':'existing_implemented', 'complete_effect':True,
                'coverage_scope':'whole_declared_effect', 'components':['all_declared_effect_components'],
                'current_server_rules_verified':False}
    if identifier in support.get('legacy_candidate_'+kind, ()):
        return {'status':'legacy_candidate', 'complete_effect':False,
                'coverage_scope':'unintegrated_reference', 'components':[], 'current_server_rules_verified':False}
    return {'status':'not_implemented', 'complete_effect':False,
            'coverage_scope':'none', 'components':[], 'current_server_rules_verified':False}


def build_catalog(talents, season, localization, *, cards=(), npc_names=None, runtime_support=None):
    """Retain every record, including unavailable/legacy variants, in a typed inventory."""
    terms = _terms(localization)
    card_names = {row['id']:row['name'] for row in cards if row.get('name')}
    talent_names = {row['id']:row.get('name', '') for row in talents}
    support = runtime_support if runtime_support is not None else discover_runtime_support()
    entries, seen = [], set()
    for kind, rows, name_prefix, desc_prefix, battle_flag in (
        ('regular', talents, 'Talent_', 'TalentDesc_', 'isBattleTalent'),
        ('season', season, 'XianMoStrategyName_', 'XianMoStrategyDesc_', 'isBattleEffect')):
        for row in rows:
            identifier = row.get('id')
            if type(identifier) is not int or (kind,identifier) in seen:
                raise ValueError('Configuration IDs must be unique within each namespace')
            seen.add((kind,identifier))
            name = row.get('name') or terms.get(name_prefix+str(identifier)) or f'{kind}:{identifier}'
            key = desc_prefix+str(identifier)
            description = terms.get(key)
            if description is None and kind == 'regular' and 'talentId' in row:
                key = desc_prefix+str(row['talentId'])
                description = terms.get(key)
            description = description or ''
            rendered = render_description(description, row, card_names=card_names, talent_names=talent_names)
            classification = classify(description, battle_flag=row.get(battle_flag) is True)
            execution = _execution(kind, identifier, support)
            if execution['status'] == 'existing_implemented' and not classification['combat_relevant']:
                classification['combat_relevant'] = True
                preparation = [phase for phase in ('acquisition_card_grant', 'conditional_extra_draw')
                               if phase in execution['components']]
                classification['phases'] = preparation or ['ongoing_combat']
                classification['classification_basis'].append({'basis':'declared_runtime_component'})
            entries.append({'namespace':kind, 'id':identifier, 'name':name,
                'description':rendered, 'description_template':description, 'description_key':key,
                'description_found':bool(description),
                'unresolved_placeholders':sorted(set(re.findall(r'\{[^{}]+\}', rendered))),
                'battle_flag':row.get(battle_flag) is True,
                'available':row.get('isAvailable') if kind=='season' else None,
                'availability_note':'ordinary table has no equivalent verified current-pool availability flag' if kind=='regular' else None,
                'npc_config_id':row.get('npc') if kind=='season' else None,
                'npc_name':(npc_names or {}).get(row.get('npc')) if kind=='season' else None,
                'level':row.get('level'), 'base_talent_id':row.get('talentId'),
                'parameters':{k:deepcopy(row[k]) for k in ('otherParams','countParam','effectRound') if k in row},
                'eligibility':{k:deepcopy(row[k]) for k in ('sect','charId','includeCharacters','excludeCharacters','excludeSects','isMiJingTalent','diffDescInGameModes') if k in row},
                'has_unparsed_expression_fields':bool(row.get('_unknown_fields')),
                'execution':execution, **classification})
    entries.sort(key=lambda row:(row['namespace'], row['id']))
    combat = [row for row in entries if row['combat_relevant']]
    totals = {kind:{'all_records':sum(row['namespace']==kind for row in entries),
                     'battle_flag_records':sum(row['namespace']==kind and row['battle_flag'] for row in entries),
                     'combat_related_records':sum(row['namespace']==kind for row in combat),
                     'combat_available_records':sum(row['namespace']==kind and row['available'] is True for row in combat) if kind=='season' else None,
                     'execution_status_counts':dict(Counter(row['execution']['status'] for row in combat if row['namespace']==kind)),
                     'complete_declared_effects':sum(row['namespace']==kind and row['execution']['complete_effect'] for row in combat),
                     'component_only_records':sum(row['namespace']==kind and row['execution']['coverage_scope']=='component_only' for row in combat)}
              for kind in ('regular','season')}
    return {'schema_version':1, 'asset_catalog':'2026.11.06.06.05.32', 'summary':totals,
            'phase_counts':dict(Counter(phase for row in combat for phase in row['phases'])),
            'runtime_registry_sources':support.get('registry_sources', []), 'entries':entries,
            'limits':['Counts are configuration records including levels, variants and unavailable entries, not unique currently drawable fates.',
                      'Event classification is a text/configuration index, not recovered executable semantics.',
                      'A component-only implementation is not a complete fate; acquisition effects, active use or later triggers may remain missing.',
                      'Runtime availability does not certify correspondence to current online-server rules.']}


def export_catalog(root=ROOT/'data/local/2026-11-06', *, json_path=None, markdown_path=None, runtime_support=None):
    root = Path(root)
    paths = {'talents':root/'tables/TalentConfig.json','season':root/'season/XianMoStrategyConfig.json',
             'localization':root/'raw/Localization.json','cards':root/'tables/CardConfig.json',
             'mechanics':root/'season/mechanics.json'}
    raw = {name:path.read_bytes() for name,path in paths.items()}
    parsed = {name:json.loads(content) for name,content in raw.items()}
    catalog = build_catalog(parsed['talents'],parsed['season'],parsed['localization'],cards=parsed['cards'],
        npc_names={row['id']:row['display_name'] for row in parsed['mechanics']['npcs']},runtime_support=runtime_support)
    catalog['sources'] = {name:{'path':str(path.resolve()),'sha256':hashlib.sha256(raw[name]).hexdigest()}
                          for name,path in paths.items()}
    catalog['generator_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    json_path = Path(json_path) if json_path else root/'combat-fates.json'
    markdown_path = Path(markdown_path) if markdown_path else ROOT/'docs/COMBAT_FATES.md'
    json_path.parent.mkdir(parents=True,exist_ok=True)
    json_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    markdown_path.parent.mkdir(parents=True,exist_ok=True)
    markdown_path.write_text(render_markdown(catalog),encoding='utf-8')
    return catalog


def render_markdown(catalog):
    lines = ['# 战斗相关仙命目录', '',
             '由本地配置和中文说明生成。分类是检索索引；名称、参数、说明存在不代表效果已经执行。配置条数包含等级、变体与不可用记录。', '',
             '`已有执行组件`必须继续看覆盖列：`完整声明效果`表示当前注册处理器覆盖声明效果；`组件`仅覆盖列出的阶段，不能算整条仙命完成。全部项目仍未认证为当前服务器规则完全一致。', '',
             '重建：`.venv/Scripts/python.exe -X utf8 tools/export_fate_catalog.py`。机器可读完整目录包含非战斗项目、来源指纹和未解析表达式标记。', '',
             '| 类别 | 全部配置 | 战斗标志为真 | 本目录战斗相关 | 已有组件 | 完整声明效果 | 待实现 |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for kind, label in [('regular','普通仙命'),('season','百家之道')]:
        s=catalog['summary'][kind]
        lines.append(f"| {label} | {s['all_records']} | {s['battle_flag_records']} | {s['combat_related_records']} | {s['execution_status_counts'].get('existing_implemented',0)} | {s['complete_declared_effects']} | {s['execution_status_counts'].get('not_implemented',0)} |")
    for kind,label in [('regular','普通仙命'),('season','百家之道')]:
        lines += ['',f'## {label}', '', '| ID / 名称 | 阶段索引 | 状态 / 覆盖 | 说明 |', '| --- | --- | --- | --- |']
        for row in catalog['entries']:
            if row['namespace'] != kind or not row['combat_relevant']:
                continue
            execution=row['execution']; status=STATUS_LABELS[execution['status']]
            cover='完整声明效果' if execution['complete_effect'] else '组件：'+','.join(execution['components']) if execution['components'] else '无'
            extras=[]
            if row['available'] is False:extras.append('配置标记不可用')
            if row['has_unparsed_expression_fields']:extras.append('含未解码表达式')
            if row['unresolved_placeholders']:extras.append('含未解析占位符')
            description=row['description'] or '未找到说明'
            if extras:description+='；'+'；'.join(extras)
            escape=lambda text:str(text).replace('|','\\|').replace('\n','<br>')
            title=f"{row['id']} {row['name']}"+(f"（{row['npc_name']}）" if row['npc_name'] else '')
            lines.append('| '+' | '.join(map(escape,[title,'、'.join(PHASE_LABELS[p] for p in row['phases']),status+' / '+cover,description]))+' |')
    return '\n'.join(lines)+'\n'
