"""Audit the pinned, locally cached wiki without changing game/model rules.

Builds explicit current-season sect membership from user-confirmed set rules.
The associated numeric metadata remains the old local client snapshot; newer
wiki patch values must not silently relabel old replay battle results.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yixian.card_pool import create_pool, metadata_from_local, snapshot
from yixian.season import SeasonCatalog

SECTS = {1: ("云灵剑宗", "cloud-spirit-sword-sect"),
         2: ("七星阁", "heptastar-pavilion"),
         3: ("五行道盟", "five-elements-alliance"),
         4: ("锻玄宗", "duan-xuan-sect")}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def text(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<br\s*/?>", "\n", fragment)))


def normalized(fragment):
    return re.sub(r"[\s\[\]]+", "", text(fragment))


def audit(cache: Path, gap_file: Path):
    manifest = read(cache / "source-manifest.json")
    endings = read(cache / "source-line-endings.json")
    sources = manifest["files"] + read(cache / "additional-source-manifest.json")
    verified = []
    for row in sources:
        raw = (cache / row["path"]).read_bytes()
        canonical = raw.replace(b"\r\n", b"\n")
        trailing = row.get("source_ends_with_newline", endings.get(row["path"], {}).get("source_ends_with_newline"))
        if trailing is False and canonical.endswith(b"\n"):
            canonical = canonical[:-1]
        git_sha = hashlib.sha1(b"blob " + str(len(canonical)).encode() + b"\0" + canonical).hexdigest()
        if git_sha != row["git_blob_sha1"]:
            raise ValueError(f"Source content no longer matches pinned blob: {row['path']}")
        verified.append({"path": row["path"], "git_blob_sha1": git_sha,
                         "local_sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
    local_path = ROOT / "data/local/2026-11-06/tables/CardConfig.json"
    cards = {x["id"]: x for x in read(local_path)}
    seasons = {}
    for season in ("heavenly-derivation", "hundred-schools"):
        body = (cache / f"zh/seasons/{season}.html").read_text(encoding="utf-8")
        groups = {}
        for section in re.findall(r'<section class="luck-sect">(.*?)</section>', body, re.S):
            name = text(re.search(r"<h3>(.*?)</h3>", section, re.S)[1])
            ids = list(dict.fromkeys(map(int, re.findall(r'data-card-preview="(\d+)"', section))))
            if len(ids) != 8:
                raise ValueError(f"Unexpected season group: {season} {name}")
            groups[name] = sorted(ids)
        if set(groups) != {name for name, _ in SECTS.values()}:
            raise ValueError("Season groups are incomplete")
        seasons[season] = groups
    pools = {}
    for sect, (name, slug) in SECTS.items():
        body = (cache / f"zh/sects/{slug}.html").read_text(encoding="utf-8")
        ids = [int(re.search(r'data-card-key="(\d+)_zh"', x)[1])
               for x in re.findall(r'<article class="card-row">(.*?)</article>', body, re.S)]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate card in sect list")
        whole, previous, current = set(ids), set(seasons["heavenly-derivation"][name]), set(seasons["hundred-schools"][name])
        if previous & current or not (previous | current) <= whole:
            raise ValueError("Season lists conflict with sect catalogue")
        base = whole - previous - current
        allowed = base | current
        for cid in allowed:
            row = cards[cid]
            if (row.get("sect") != sect or row.get("career") != 0
                    or row.get("owner") != 0 or row.get("rarity") != 0
                    or row.get("obsolete") or row.get("hidden")):
                raise ValueError(f"Membership conflicts with local base-card metadata: {cid}")
            if set(row.get("seasonMechanics", [])) - {10}:
                raise ValueError(f"Unexpected old-season membership: {cid}")
        metadata = metadata_from_local(sorted(allowed))
        pool = create_pool(metadata, seed=20261112)
        snapshot(pool)
        pools[str(sect)] = {"name": name, "catalogue_count": len(whole),
                           "base_ids": sorted(base), "removed_heavenly_ids": sorted(previous),
                           "added_hundred_schools_ids": sorted(current),
                           "current_ids": sorted(allowed), "family_count": len(pool["families"]),
                           "physical_copy_count": sum(x["remaining"] for x in pool["families"].values()),
                           "metadata": metadata}
    catalog = read(cache / "cards-zh.json")
    index = {}
    for family, variants in catalog["groups"].items():
        for variant in variants:
            index.setdefault(str(variant["id"]), []).append(family)
    missing = Counter()
    for reason, count in read(gap_file)["reason_counts"].items():
        if reason.startswith("unmapped_cards:"):
            for cid in set(reason.split(":", 1)[1].split(",")):
                missing[cid] += count
    lookup = [{"raw_id": int(cid), "name": cards.get(int(cid), {}).get("name"),
               "first_blocker_records_containing_id": n, "wiki_groups": index.get(cid, []),
               "urls": [f"https://sharpobject.github.io/yxp_wiki/zh/cards/{i}.html" for i in index.get(cid, [])]}
              for cid, n in missing.most_common()]
    details = []
    for path in sorted((cache / "zh/cards").glob("*.html")):
        body = path.read_text(encoding="utf-8")
        for article in re.findall(r'<article class="level-card">(.*?)</article>', body, re.S):
            cid = int(re.search(r'data-card-key="(\d+)_zh"', article)[1])
            desc = re.search(r"<p>(.*?)</p>", article, re.S)[1]
            details.append({"raw_id": cid, "name": cards.get(cid, {}).get("name"),
                            "wiki_description": text(desc).strip(),
                            "local_description": cards.get(cid, {}).get("description_preview"),
                            "text_equal_ignoring_markup_whitespace": normalized(desc) == normalized(cards.get(cid, {}).get("description_preview", ""))})
    fates = (cache / "zh/fates/hundred-schools.html").read_text(encoding="utf-8")
    suanni = {}
    for tier in (1, 2):
        match = re.search(rf'<details class="pool" id="suanni-pool-{tier}"[^>]*>(.*?)</details>', fates, re.S)
        if not match:
            raise ValueError("Missing Suan Ni pool")
        names = [text(x).strip() for x in re.findall(r"<h3>(.*?)</h3>", match[1], re.S)]
        declared = int(re.search(r'<span data-pool-count>(\d+)</span>', match[1])[1])
        if declared != len(names):
            raise ValueError("Suan Ni pool parse incomplete")
        suanni[str(tier)] = {"wiki_count": declared, "wiki_names": names}
    local_season = SeasonCatalog.from_local()
    mapping = []
    for npc in local_season.npcs.values():
        tier = {24: 1, 25: 2}[npc["specialSkip"]]
        reward = {1: 3, 2: 5}[tier]
        if npc["skipGotReplaceChance"] != reward:
            raise ValueError("Local NPC reward conflicts with user confirmation")
        mapping.append({"npc_config_id": npc["id"], "suanni_tier": tier, "repeat_skip_rerolls": reward})
    for tier, npc in [(1, 24), (2, 25)]:
        suanni[str(tier)]["local_available_ids"] = sorted(x["id"] for x in local_season.strategies.values()
                                                       if x.get("npc") == npc and x.get("isAvailable") is True)
    report = {"schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "wiki_commit": manifest["commit"], "wiki_commit_message": manifest["commit_message"],
              "sources": verified, "cached_source_bytes": sum(x["bytes"] for x in verified),
              "card_detail_comparisons": details, "unmapped_card_reference_index": lookup,
              "suanni_pools": suanni, "npc_skip_mapping": mapping,
              "unmapped_unique_ids": len(lookup), "unmapped_ids_with_reference": sum(bool(x["wiki_groups"]) for x in lookup),
              "local_card_config_sha256": hashlib.sha256(local_path.read_bytes()).hexdigest(),
              "prior_battle_metrics_unchanged": True, "battle_training_allowed": False,
              "notes": ["No new battle runs or holdout reads; index availability is not effect execution.",
                        "Wiki patch is newer than local numeric rules; membership and numeric versions are separate.",
                        "Suan Ni pool 1 has a new wiki option; do not add it to older replay candidates.",
                        "Internal enum JinSuiCao was previously called 金穗草; display card name is 金梭兰."]}
    pool_manifest = {"schema_version": 1, "season_mec": 10,
                     "membership_source": "explicit_user_confirmation_plus_pinned_wiki_sect_and_season_lists",
                     "source_commit": manifest["commit"], "numeric_rules_version": "001.0008.0005",
                     "newer_wiki_patch_values_applied": False,
                     "scope": "sect_regular_starting_pool_only_not_professions_or_conditional_rewards",
                     "formula": "base = sect_list - heavenly_eight - hundred_eight; current = base | hundred_eight",
                     "training_allowed": False, "sects": pools}
    return report, pool_manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=ROOT / "data/references/yxp_wiki/20261112-b3d018bd")
    parser.add_argument("--gaps", type=Path, default=ROOT / "runs/stages/20261112T043900Z-s2-permanent-plants/next-gap-queue.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("Use a new audit directory; do not overwrite historical evidence")
    report, pools = audit(args.cache, args.gaps)
    args.out.mkdir(parents=True)
    for name, value in [("report.json", report), ("current-sect-pools.json", pools)]:
        (args.out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.out / "report.json"),
                      "source_files_verified": len(report["sources"]),
                      "unmapped_ids": [report["unmapped_ids_with_reference"], report["unmapped_unique_ids"]],
                      "sect_counts": {v["name"]: {"base": len(v["base_ids"]), "current": len(v["current_ids"]),
                                                   "physical_copies": v["physical_copy_count"]} for v in pools["sects"].values()},
                      "different_descriptions": [x["raw_id"] for x in report["card_detail_comparisons"] if not x["text_equal_ignoring_markup_whitespace"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
