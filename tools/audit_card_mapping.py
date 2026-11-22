"""Audit candidate ID links; matching names/IDs do not prove effect equivalence."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def audit(cards, names, simulated_ids):
    # Only ordinary three-level cards use this mapping. Dream/special cards require
    # an explicit conversion contract and stay unclassified here.
    lookup = {n["other_id"]: n for n in names if isinstance(n.get("other_id"), int) and n["other_id"] >= 0 and not n.get("non_playable")}
    mappings, unmatched, excluded = [], [], []
    for row in cards:
        if row["id"] < 0 or row["rarity"] not in (0, 1, 2):
            excluded.append(row["id"])
            continue
        base = row["id"] - row["rarity"] * 10000
        reference = lookup.get(base)
        candidate = None
        if reference:
            refid = str(reference["id"])
            if refid.isdigit() and refid.endswith("1"):
                candidate = str(int(refid) + row["rarity"])
        if candidate not in simulated_ids:
            unmatched.append({"id": row["id"], "name": row["name"], "rarity": row["rarity"],
                              "hidden": row["hidden"], "obsolete": row["obsolete"]})
        else:
            mappings.append({"client_id": row["id"], "simulator_id": candidate, "name": row["name"]})
    return {"status": "candidate_mapping_only", "effect_parity_verified": False,
            "current_season_pool_verified": False, "local_entries": len(cards),
            "candidate_matches": len(mappings), "unmatched_entries": len(unmatched),
            "special_entries_not_classified": len(excluded),
            "mappings": mappings, "unmatched": unmatched, "excluded": excluded}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cards', type=Path, default=Path('data/local/2026-11-06/tables/CardConfig.json'))
    p.add_argument('--engine', type=Path, default=Path('external/yisim'))
    p.add_argument('--out', type=Path, default=Path('data/inspection/card-mapping.json'))
    a = p.parse_args()
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    report = audit(read(a.cards), read(a.engine / 'names.json'), read(a.engine / 'swogi.json'))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k,v in report.items() if k not in ('mappings','unmatched','excluded')}, ensure_ascii=False))
