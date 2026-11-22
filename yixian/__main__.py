from __future__ import annotations
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="弈仙牌离线研究工具")
    sub = p.add_subparsers(dest="command", required=True)
    cards = sub.add_parser("cards", help="查询本地提取的卡牌配置")
    cards.add_argument("query", help="卡牌中文名称或精确数字ID")
    cards.add_argument("--table", type=Path, default=Path(__file__).resolve().parents[1] / "data/local/2026-11-06/tables/CardConfig.json")
    fates = sub.add_parser('fates', help='查询普通仙命和百家之道说明及实际执行范围')
    fates.add_argument('query', nargs='?', help='中文名称或精确数字ID；省略显示覆盖统计')
    battle = sub.add_parser("simulate", help="运行单场离线参考战斗，当前版本规则尚未验证")
    battle.add_argument("input", type=Path)
    battle.add_argument("--out", type=Path)
    cycle = sub.add_parser("cycle", help="按论文研究闭环运行一次本机排牌训练与独立评测")
    cycle.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] / "configs/curriculum.json")
    cycle.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "runs")
    status = sub.add_parser("status", help="查看最近实验、规则缺口和研究记录")
    status.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "runs")
    arrange = sub.add_parser("arrange", help="用已训练的课程模型给离线局面排牌")
    arrange.add_argument("run", type=Path, help="含 policy.npz 和 contract.json 的实验目录")
    arrange.add_argument("input", type=Path)
    arrange.add_argument("--out", type=Path)
    sub.add_parser("season", help="查看本地当前赛季配置及实现边界")
    flow = sub.add_parser("flow", help="用7名回放对手验证8人整局阶段；战斗结果使用测试数据")
    flow.add_argument("--sample", type=Path, default=Path(__file__).resolve().parents[1] / 'runs/replays/b592caa9bc6c-34499000-g8/rounds.jsonl')
    flow.add_argument("--seed", type=int, default=19)
    args = p.parse_args()
    if args.command == "cards":
        if not args.table.exists():
            p.error("还没有提取卡牌配置，请先运行 README 中的数据提取步骤。")
        rows = json.loads(args.table.read_text(encoding="utf-8"))
        results = [r for r in rows if str(r["id"]) == args.query or args.query in r["name"]]
        for row in results:
            print(f"{row['name']}  ID={row['id']}  rarity={row['rarity']}  level={row['level']}")
            print(row["description_preview"])
            if row["hidden"] or row["obsolete"]:
                print(f"配置标记：hidden={row['hidden']} obsolete={row['obsolete']}")
            print()
        print(f"找到 {len(results)} 条配置；包含等级、历史与特殊条目，不能直接当作当前可抽卡池。")
    elif args.command == 'fates':
        from .fate_catalog import export_catalog
        catalog = export_catalog()
        if not args.query:
            print(json.dumps(catalog['summary'],ensure_ascii=False,indent=2))
        else:
            for row in catalog['entries']:
                if str(row['id']) == args.query or args.query in row['name']:
                    print(f"{row['namespace']} / {row['id']} {row['name']}")
                    print(row['description'] or '未找到中文说明')
                    print(json.dumps(row['execution'],ensure_ascii=False))
    elif args.command == "simulate":
        from .simulator import SimulatorError, simulate_battle
        try:
            result = simulate_battle(json.loads(args.input.read_text(encoding="utf-8")))
        except (OSError, ValueError, SimulatorError) as error:
            p.error(str(error))
        rendered = json.dumps(result, ensure_ascii=False, indent=2)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(rendered, encoding="utf-8")
        print(rendered)
    elif args.command == "cycle":
        from .pipeline import run_cycle
        try:
            report = run_cycle(args.config, output_root=args.output)
        except (OSError, ValueError, RuntimeError) as error:
            p.error(str(error))
        print(f"模型参数：{report['parameter_count']}；有效训练对局：{report['training_episodes']}")
        for name, label in (("validation", "验证集"), ("test", "独立测试集")):
            values = report['metrics'][name]
            print(f"{label}：模型胜率={values['candidate_win_fraction']}；随机基线={values['baseline_win_fractions']['random']}")
        print("以上仅为合成牌序课程结果；完整对局与当前赛季实战能力尚未验证。")
    elif args.command == "status":
        root = Path(__file__).resolve().parents[1]
        project = json.loads((root / 'configs/project.json').read_text(encoding='utf-8'))
        result = {"project": project}
        latest = args.output / 'latest.json'
        if latest.exists():
            pointer = json.loads(latest.read_text(encoding='utf-8'))
            result['latest_experiment'] = json.loads(Path(pointer['report']).read_text(encoding='utf-8'))
        if (args.output / 'research.sqlite').exists():
            from .memory import Memory
            result['research_memory'] = Memory(args.output / 'research.sqlite').summary()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "arrange":
        from .pipeline import arrange as arrange_battle, write_json
        try:
            result = arrange_battle(args.run, json.loads(args.input.read_text(encoding='utf-8-sig')))
        except (OSError, ValueError, RuntimeError) as error:
            p.error(str(error))
        if args.out:
            write_json(args.out, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "season":
        from .season import SeasonCatalog
        from .effects import EffectEngine
        catalog = SeasonCatalog.from_local()
        result = {"season": "百家之道", "public_season_number": 11, "internal_mechanism": 10,
                  "npc_configuration_groups": len(catalog.npcs), "effect_configurations": len(catalog.strategies),
                  "available_effect_configurations": sum(r.get('isAvailable') is True for r in catalog.strategies.values()),
                  "contract": catalog.contract(),
                  "implemented": "外部候选验证、选择/跳过请求、首跳过后续、共享候选一致性校验",
                  "missing": "服务器候选生成、未支持仙命的效果及完整真实对局核对",
                  "effect_components": EffectEngine.from_local().contract()}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "flow":
        from .flow_demo import run_flow_demo
        try:
            result = run_flow_demo(args.sample, seed=args.seed)
        except (OSError, ValueError, RuntimeError) as error:
            p.error(str(error))
        report = result['summary']
        print(f"整局流程：{report['players']} 人，{report['rounds']} 轮，{report['test_battles']} 场测试对战，已终局={report['terminated']}")
        for entry in report['season_schedule']:
            print(f"第 {entry['round']} 轮：{entry['npc_name']}，候选={entry['candidates']}")
        print(f"基础扣血对照：{result['damage_audit']}")
        print(f"首批仙命结算核对：{result['effect_validation']}")
        print(f"报告：{result['run_dir']}")
        print('已执行注册的开局与结算组件；普通持续仙命另由参考单场引擎执行。整局战果仍为测试数据，不代表模型实力。')


if __name__ == "__main__":
    main()
