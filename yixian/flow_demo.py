"""Connect real replay snapshots to the explicitly limited eight-player smoke test."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid

from .match_flow import FlowRules, ScriptedFlowAgent, fixture_battle, run_match
from .memory import Memory
from .replay_pool import build_flow_pool, load_rounds
from .season import SeasonAction, SeasonCatalog, SeasonDecision
from .settlement import audit_recorded_damage, ordinary_destiny_damage
from .effects import EffectEngine
from .effect_validation import audit_effect_settlement
from .effect_battle import simulate_effect_battle
from .talent_adapter import talent_adapter_contract
from .death_validation import validate_death_fate_replays
from .round_rules import reroll_grant, round_rules_contract

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = ROOT/'runs/replays/b592caa9bc6c-34499000-g8/rounds.jsonl'


class ProcessAgent(ScriptedFlowAgent):
    """Exercise choices, not trained gameplay or predicted optimal decisions."""
    def __init__(self, catalog):
        self.season = SeasonDecision(catalog)

    def choose_season(self, observation, offer):
        self.season.begin_offer(f'flow-offer-{len(self.season.snapshot()["receipts"])}',
                                offer['npc_id'], offer['candidates'], skip_strategy_id=offer.get('skip_id'))
        actions = self.season.legal_actions()
        selected = next((action for action in actions if action.kind == 'select'), actions[0])
        self.season.step(selected)
        return selected.strategy_id

    def arrange(self, observation, cards):
        # A transparent deterministic exercise of the arrangement interface.
        # It makes no assertion that numerical card-id order is a good policy.
        return sorted(cards, key=lambda card: (card == 0, str(card)))


def base_damage_test_battle(left, right, round_number, seed):
    result = fixture_battle(left, right, round_number, seed)
    result['life_damage'] = ordinary_destiny_damage(round_number, abs(result['hp_delta']))
    result['damage_rule'] = 'client_ordinary_branch_without_mode_or_fate_modifiers'
    return result


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def run_flow_demo(sample=DEFAULT_SAMPLE, *, seed=19, output_root=ROOT/'runs/flow'):
    sample = Path(sample).resolve()
    rows = load_rounds(sample)
    pool = build_flow_pool(rows, seed=seed)
    catalog = SeasonCatalog.from_local()
    agent = ProcessAgent(catalog)
    effects = EffectEngine.from_local()
    rules = FlowRules(initial_rerolls=3, reroll_grants_by_round=tuple(reroll_grant(r,extra_season_cards=True) for r in range(1,34)))
    talents = json.loads((ROOT/'data/local/2026-11-06/tables/TalentConfig.json').read_text(encoding='utf-8'))
    normal_offers = {}
    for level in range(2, 7):
        candidates = [row['id'] for row in talents if row.get('level') == level and
                      row.get('charId', 0) == 0 and row.get('sect', 0) == 0 and not row.get('isMiJingTalent', False)]
        if candidates:
            normal_offers[level] = candidates[:3]
    own = pool['self_template']
    report = run_match(pool['opponents'], rules=rules, agent=agent, resolver=base_damage_test_battle,
                       seed=seed, self_cards=own['rounds']['1']['cards'], self_character_id=own['character_id'],
                       season_offers=pool['season_offers'], normal_fate_offers=normal_offers, effect_engine=effects)
    names = {item['id']: item['display_name'] for item in json.loads(
        (ROOT/'data/local/2026-11-06/season/mechanics.json').read_text(encoding='utf-8'))['npcs']}
    schedule = [{'round': number, 'npc_config_id': offer['npc_id'], 'npc_name': names.get(offer['npc_id']),
                 'candidates': offer['candidates'], 'skip_id': offer.get('skip_id'),
                 'source_observed_at_round': offer['source_observed_at_round'],
                 'source_member': offer['source'].get('member')}
                for number, offers in sorted(pool['season_offers'].items()) for offer in offers]
    report['season_schedule'] = schedule
    report['season_decision_receipts'] = agent.season.snapshot()['receipts']
    report['source_data'] = {'sample': str(sample), 'sample_sha256': hashlib.sha256(sample.read_bytes()).hexdigest(),
                             'round_records': len(rows), 'opponents_from_distinct_source_games': 7,
                             'source_versions': sorted({row['source_rules_version'] for row in rows}),
                             'whole_game_ids': [track['game_id'] for track in pool['opponents']],
                             'player_identity_scope': 'one source replay; no alias merging across viewpoints'}
    report['normal_fate_offer_source'] = 'Local generic config IDs to exercise choices; not reconstructed server offers'
    report['resource_profile'] = {'initial_rerolls': 3, 'reroll_grants_by_round': list(rules.reroll_grants_by_round),
                                  'source': 'user_supplied_in_game_FAQ_and_current_season_confirmation',
                                  'round_rules_contract':round_rules_contract(),
                                  'round_exp_gain': 2, 'round_extra_max_hp_gain': 2,
                                  'growth_source': 'local Localization Tips_7'}
    report['combat_mode'] = 'Test coin-flip outcome; registered seasonal start components execute, card attacks remain a fixture'
    report['settlement_mode'] = 'Client ordinary damage plus registered modifiers and death protections; pending rewards block progression'
    report['effect_contract'] = effects.contract()
    report['effect_source_sha256'] = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
        ('yixian/effects.py','yixian/season_start.py','yixian/death_fates.py','yixian/talent_adapter.py',
         'yixian/match_flow.py','yixian/effect_validation.py','yixian/effect_battle.py')}
    report['reference_battle_talents'] = talent_adapter_contract()
    report['effect_events'] = dict(Counter(str(effect['effect_id']) for event in report['journal']
        for effect in event.get('effects', []) if 'effect_id' in effect))
    phases = Counter(event['phase'] for event in report['journal'])
    summary = {'scope': report['scope'], 'terminated': report['terminated'], 'truncated': report['truncated'],
               'players': report['player_count'], 'rounds': report['rounds'], 'test_battles': report['battle_count'],
               'phase_counts': dict(phases), 'season_schedule': schedule, 'effect_events': report['effect_events'],
               'effect_contract': effects.contract(), 'unresolved_effect_actions':report['unresolved_effect_actions'],
               'card_combat_verified': False, 'current_rules_verified': False, 'policy_training_allowed': False,
               'limitation': 'A complete process test, not a complete current-season simulator or a strength result.'}
    output = Path(output_root).resolve()/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    output.mkdir(parents=True)
    write_json(output/'report.json', report)
    write_json(output/'summary.json', summary)
    audit = audit_recorded_damage(rows)
    write_json(output/'recorded-damage-audit.json', audit)
    effect_audit = audit_effect_settlement(rows, engine=effects)
    write_json(output/'effect-replay-validation.json', effect_audit)
    write_json(output/'death-fate-replay-validation.json', validate_death_fate_replays(sample))
    # Also check the start hook against real card execution in the constrained
    # legacy adapter: Tiger Sword cannot attack immediately without enough Qi.
    example = {'seed':73,'max_turns':1,'first_player':0,'players':[
        {'character':'sw1','hp':40,'max_hp':40,'cultivation':10,'round_number':1,'destiny':100,'cards':['111071']*8},
        {'character':'sw2','hp':40,'max_hp':40,'cultivation':9,'round_number':1,'destiny':100,'cards':['601011']*8}]}
    initial = [effects.initialize_player({'life':100,'rerolls':3,'fates':[],'season_choices':[1001]},season_temp_datas={}),
               effects.initialize_player({'life':100,'rerolls':3,'fates':[],'season_choices':[]})]
    on = simulate_effect_battle(example, initial, engine=effects)
    off_initial = [effects.set_season_enabled(initial[0],1001,False),initial[1]]
    off = simulate_effect_battle(example, off_initial, engine=effects)
    write_json(output/'start-effect-card-check.json', {'scope':'same_seed_same_cards_one_turn_hook_check',
        'enabled':on, 'disabled':off, 'opponent_hp_enabled':on['combat']['players'][1]['hp'],
        'opponent_hp_disabled':off['combat']['players'][1]['hp'], 'real_game_validation':False})
    memory = Memory(ROOT/'runs/research.sqlite')
    memory.append('finding', 'environment', {
        'statement': f'8-player flow test completed={report["terminated"]}, rounds={report["rounds"]}, test battles={report["battle_count"]}. Combat outcomes are fixtures, not card simulation.',
        'claim': 'measured', 'evidence': [str(output/'report.json'), str(sample)]})
    memory.append('finding', 'evaluation', {
        'statement': f'Ordinary damage branch matched {audit["matching"]}/{audit["records_checked"]} recorded magnitudes; {audit["mismatching"]} require modifier/input investigation. Repeated perspectives are included.',
        'claim': 'measured', 'evidence': [str(output/'recorded-damage-audit.json')]})
    memory.append('finding', 'evaluation', {
        'statement': f'Original targeted settlement comparison: {effect_audit["same_eligible_records"]}. Dataset has zero settlement coverage for 2011; expanded death consequences are audited separately, not assumed to verify combat.',
        'claim':'measured','evidence':[str(output/'effect-replay-validation.json'),str(output/'start-effect-card-check.json')]})
    write_json(Path(output_root).resolve()/'latest.json', {'run_dir': str(output), 'summary': str(output/'summary.json')})
    return {'run_dir': str(output), 'summary': summary,
            'effect_validation': effect_audit['same_eligible_records'],
            'damage_audit': {k:audit[k] for k in ('records_checked','matching','mismatching')}}
