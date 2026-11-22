"""Exercise explicit pool draws and cultivation accounting with replay opponents.

This deliberately bounded card whitelist is a fixture, not a complete legal
server pool. Combat outcomes remain flow fixtures and produce no training data.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from yixian.card_pool import create_pool, metadata_from_local
from yixian.pool_draw import make_round_draw_provider
from yixian.replay_pool import build_flow_pool, load_rounds
from yixian.match_flow import FlowRules, run_match
from yixian.round_rules import reroll_grant, round_rules_contract

ROOT=Path(__file__).resolve().parents[1]


def main():
    sample=ROOT/'runs/replays/b592caa9bc6c-34499000-g8/rounds.jsonl'
    replay_pool=build_flow_pool(load_rounds(sample),seed=19)
    ids=[1000001,1000002,1000003,1000004,1000005,1000006,2000001,2000002,2000003]
    metadata=metadata_from_local(ids,local_root=ROOT/'data/local/2026-11-06')
    pool=create_pool(metadata,seed=19)
    def eligible(request,observation):
        return [r['card_id'] for r in metadata if r['realm']<=observation['self']['level']
                and (request['pool']=='combined_remaining' or r['category']==request['pool'])]
    provider=make_round_draw_provider(pool,eligible)
    rules=FlowRules(max_rounds=6,initial_rerolls=3,
                    reroll_grants_by_round=tuple(reroll_grant(r) for r in range(1,8)))
    report=run_match(replay_pool['opponents'],rules=rules,seed=19,round_draw_provider=provider)
    report.update(scope='bounded_pool_and_cultivation_flow_check',
        pool_scope='explicit_nine_card_fixture_not_full_server_pool',
        pool_contract=provider.contract(),round_rules_contract=round_rules_contract(),
        sample_sha256=hashlib.sha256(sample.read_bytes()).hexdigest(),
        final_pool=provider.snapshot())
    own=report['players'][0]
    assert len(own['hand_cards'])==15 and own['exp']==15
    assert all(account['balanced'] for account in report['cultivation_accounts'])
    initial_count=sum(f['remaining'] for f in pool['families'].values())
    final_count=sum(f['remaining'] for f in report['final_pool']['families'].values())
    assert initial_count-final_count==15
    output=ROOT/'runs/diagnostics'/('pool-flow-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2)
    print(json.dumps({'report':str(output),'rounds':6,'cards_drawn':15,'round_6_overflow_cultivation':3,
                     'cultivation':own['exp'],'pool_reduction':initial_count-final_count,
                     'all_accounts_balanced':True,'policy_training_allowed':False},ensure_ascii=False))


if __name__=='__main__':main()
