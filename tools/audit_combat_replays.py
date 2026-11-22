"""Freeze and audit a train-only S2 replay pilot using already cached archives."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.audit_card_mapping import audit as audit_mapping
from tools.import_replays import file_hash
from yixian.combat_calibration import select_sources, iter_selected_records, project_rounds, summarize_rounds
from yixian.pretrain_protocol import load_development_corpus
from yixian.effect_battle import SUPPORTED_REFERENCE_CARDS
from yixian.effect_validation import audit_effect_settlement
from yixian.effects import SUPPORTED_FATES
from yixian.talent_adapter import SUPPORTED_TALENT_IDS
from yixian.season_start import IMPLEMENTED_SEASON_START_IDS, NATIVE_SEASON_IDS
from yixian.death_fates import DEATH_FATES
from yixian.memory import Memory


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--games', type=int, default=64)
    args = parser.parse_args()
    manifest, partitions, _ = load_development_corpus(args.data, expected_manifest_sha256=args.manifest_sha256)
    selected = select_sources(partitions['train'], games=args.games)
    by_archive = defaultdict(list)
    for source in selected:
        by_archive[source['archive']].append(source)
    pinned = {row['path']: row for row in manifest['archives']}
    source_paths = ['yixian/combat_calibration.py', 'tools/audit_combat_replays.py',
                    'tools/audit_card_mapping.py', 'tools/import_replays.py',
                    'yixian/pretrain_protocol.py', 'yixian/order_data.py', 'yixian/replays.py',
                    'yixian/effect_battle.py', 'yixian/effect_validation.py', 'yixian/effects.py',
                    'yixian/talent_adapter.py', 'yixian/season_start.py', 'yixian/death_fates.py',
                    'yixian/settlement.py', 'external/yisim/names.json', 'external/yisim/swogi.json',
                    'data/local/2026-11-06/tables/CardConfig.json',
                    'data/local/2026-11-06/tables/TalentConfig.json',
                    'data/local/2026-11-06/season/XianMoStrategyConfig.json']
    source_hashes = {p: file_hash(ROOT/p) for p in source_paths}
    if source_hashes['data/local/2026-11-06/tables/CardConfig.json'] != manifest['card_config_sha256']:
        raise ValueError('Card catalog differs from frozen corpus')
    args.out.mkdir(parents=True, exist_ok=False)
    plan = {'schema_version': 1, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'scope': 'S2_train_only_combat_evidence_audit', 'games': args.games,
            'corpus': str(args.data), 'manifest_sha256': args.manifest_sha256,
            'dataset': manifest['source'], 'revision': manifest['revision'],
            'selection': 'lexicographically first train game hashes; first pinned source per game',
            'selected_sources': selected, 'archives': [pinned[name] for name in sorted(by_archive)],
            'source_hashes': source_hashes, 'no_network_acquisition': True,
            'heldout_test_file_opened': False, 'gpu_jobs': 0, 'training_labels': False}
    write(args.out/'plan.json', plan)
    for relative in source_paths:
        if relative.endswith('.py'):
            dest = args.out/'source'/relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ROOT/relative).read_bytes())
    memory = Memory(ROOT/'runs/research.sqlite')
    experiment = memory.register_experiment(plan, {'source_hashes': source_hashes,
        'policy_observations': False, 'complete_combat_replayed': False}, role='environment')
    write(args.out/'registration.json', {'experiment_id': experiment, 'plan_sha256': file_hash(args.out/'plan.json')})
    memory.record_experiment(experiment, 'running', role='environment')
    try:
        evidence, normalized, archives_verified = [], [], []
        for name in sorted(by_archive):
            path = ROOT/'data/local/hf-replays'/name
            if path.stat().st_size != pinned[name]['bytes'] or file_hash(path) != pinned[name]['sha256']:
                raise ValueError(f'Cached archive does not match pin: {name}')
            for source, record in iter_selected_records(path, by_archive[name]):
                enriched = dict(source, dataset=manifest['source'], revision=manifest['revision'],
                                archive_sha256=pinned[name]['sha256'])
                projected, settlement = project_rounds(record, enriched)
                if not projected:
                    raise ValueError('Selected view has no human Long Yao round')
                evidence.extend(projected)
                normalized.extend(settlement)
            archives_verified.append(name)
        read = lambda p: json.loads((ROOT/p).read_text(encoding='utf-8'))
        cards = read('data/local/2026-11-06/tables/CardConfig.json')
        mapping = audit_mapping(cards, read('external/yisim/names.json'), read('external/yisim/swogi.json'))
        card_links = {row['client_id']: row['simulator_id'] for row in mapping['mappings']}
        report = summarize_rounds(evidence, card_mapping=card_links,
            reference_subset=SUPPORTED_REFERENCE_CARDS,
            regular_components=SUPPORTED_TALENT_IDS | SUPPORTED_FATES | DEATH_FATES,
            season_components=IMPLEMENTED_SEASON_START_IDS | NATIVE_SEASON_IDS | {2011})
        if report['source_games'] != args.games:
            raise ValueError('Pilot did not preserve all selected whole games')
        catalogs = {'cards': {c['id']: c for c in cards},
                    'talents': {c['id']: c for c in read('data/local/2026-11-06/tables/TalentConfig.json')},
                    'season': {c['id']: c for c in read('data/local/2026-11-06/season/XianMoStrategyConfig.json')}}
        for role, kinds in report['content_inventory'].items():
            for kind, entries in kinds.items():
                for entry in entries:
                    config = catalogs.get(kind, {}).get(entry['raw_id'], {})
                    entry['name'] = config.get('name')
                    if kind == 'cards':
                        entry['catalog_sect'] = config.get('sect')
                        entry['catalog_career'] = config.get('career')
        settlement = audit_effect_settlement(normalized)
        report.update({'schema_version': 1, 'experiment_id': experiment,
            'completed_at_utc': datetime.now(timezone.utc).isoformat(),
            'plan_sha256': file_hash(args.out/'plan.json'), 'archives_verified': archives_verified,
            'sample_is_representative_random_sample': False, 'heldout_test_file_opened': False,
            'unselected_archive_payloads_parsed': False, 'download_bytes': 0, 'gpu_job_seconds': 0,
            'settlement_check_scope': 'recorded_hp_delta_to_destiny_damage_only_not_battle_simulation',
            'settlement_diagnostic_summary': {k: v for k, v in settlement.items() if k not in ('records', 'effect_contract', 'limitations')}})
        with (args.out/'evidence-rounds.jsonl').open('x', encoding='utf-8') as stream:
            for row in evidence:
                stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':'))+'\n')
        write(args.out/'settlement-diagnostics.json', settlement)
        write(args.out/'content-candidates.json', {'scope': 'observed_development_content_not_training_whitelist',
              'content_inventory': report.pop('content_inventory'), 'admitted_for_training': [],
              'whole_effect_and_interactions_verified': False})
        report['output_sha256'] = {name: file_hash(args.out/name) for name in
            ('evidence-rounds.jsonl', 'settlement-diagnostics.json', 'content-candidates.json')}
        write(args.out/'report.json', report)
        memory.record_experiment(experiment, 'completed', {'report': str(args.out/'report.json'),
            'report_sha256': file_hash(args.out/'report.json'), 'training_labels': 0}, role='environment')
        print(json.dumps({k: v for k, v in report.items() if k not in ('start_field_counts', 'output_sha256', 'archives_verified')}, ensure_ascii=False))
    except Exception as error:
        write(args.out/'failure.json', {'error_type': type(error).__name__, 'error': str(error),
                                       'experiment_id': experiment})
        memory.record_experiment(experiment, 'failed', {'failure': str(args.out/'failure.json')}, role='environment')
        raise


if __name__ == '__main__':
    main()
