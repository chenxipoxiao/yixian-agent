"""Export a readable inventory and component coverage of combat-related fates."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from yixian.fate_catalog import ROOT, export_catalog


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT/'data/local/2026-11-06')
    parser.add_argument('--json',type=Path)
    parser.add_argument('--markdown',type=Path)
    args=parser.parse_args()
    result=export_catalog(args.root,json_path=args.json,markdown_path=args.markdown)
    print(json.dumps(result['summary'],ensure_ascii=False,indent=2))


if __name__=='__main__':main()
