"""Freeze the next S1 dataset only after group-count and test-retirement gates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from yixian.corpus_merge import freeze_corpus, sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry',type=Path,default=ROOT/'configs/longyao_corpora.json')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    plan=json.loads((ROOT/'configs/training_stages.json').read_text(encoding='utf-8'))
    gates=next(stage for stage in plan['stages'] if stage['id']=='S1')['planning_gates']
    registry=json.loads(args.registry.read_text(encoding='utf-8'))
    expected_card_hash=sha(ROOT/'data/local/2026-11-06/tables/CardConfig.json')
    for entry in registry['corpora']:
        parent=json.loads((ROOT/entry['directory']/'manifest.json').read_text(encoding='utf-8'))
        if parent['card_config_sha256']!=expected_card_hash:
            raise ValueError('Local rules snapshot differs from a registered corpus')
    manifest=freeze_corpus(args.registry,args.out,root=ROOT,minimum_games={
        'train':gates['minimum_training_games'],'validation':gates['minimum_validation_games'],
        'test':gates['minimum_new_test_games']})
    print(json.dumps({'ready':str(args.out),'split_summary':manifest['split_summary'],
        'retired_test_games':manifest['retired_test_game_count'],'test_model_evaluations':0}))


if __name__=='__main__':main()
