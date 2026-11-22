"""Run bounded real reference-engine search (not a replay or strength test)."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.tactical_reference import ReferenceBattleEvaluator
from yixian.tactical_search import Scenario, unique_orders, search_lineups


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    battle = json.loads((ROOT/'examples/battle.json').read_text(encoding='utf-8'))
    evaluator = ReferenceBattleEvaluator(own_state=battle['players'][0])
    view = {'digest': 'declared-software-scenario-not-replay', 'rules_fingerprint': evaluator.rules_fingerprint}
    scenarios = []
    for initiative in (0, 1):
        payload = {'opponent_state': deepcopy(battle['players'][1]), 'first_player': initiative, 'seed': battle['seed']}
        scenarios.append(Scenario(str(initiative), .5, payload, view['digest'], view['rules_fingerprint'], 'declared_prior'))
    cards = battle['players'][0]['cards']
    results = search_lineups(view, cards, unique_orders(cards, 8), scenarios, evaluator, max_evaluations=16)
    results.update(engine_contract=evaluator.contract, source='examples/battle.json',
                   real_reference_simulator_executed=True, real_replay_battles_reproduced=0,
                   own_initial_board=cards, scenario_probability_empirically_estimated=False)
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(results, stream, indent=2)
    print(json.dumps({k:v for k,v in results.items() if k not in ('candidates','engine_contract')}))


if __name__ == '__main__':
    run()
