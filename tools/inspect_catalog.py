"""Read Unity Addressables catalogs without launching the game."""
from __future__ import annotations
import argparse
import base64
import json
import struct
from pathlib import Path


def read_catalog(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    key_data = base64.b64decode(data["m_KeyDataString"])
    buckets_data = base64.b64decode(data["m_BucketDataString"])
    entries_data = base64.b64decode(data["m_EntryDataString"])
    i32 = lambda buf, offset: struct.unpack_from("<i", buf, offset)[0]
    buckets = []
    pos = 4
    for _ in range(i32(buckets_data, 0)):
        key_offset, count = struct.unpack_from("<ii", buckets_data, pos)
        pos += 8
        indices = list(struct.unpack_from(f"<{count}i", buckets_data, pos))
        pos += 4 * count
        kind = key_data[key_offset]
        if kind in (0, 1):
            length = i32(key_data, key_offset + 1)
            raw = key_data[key_offset + 5:key_offset + 5 + length]
            key = raw.decode("ascii" if kind == 0 else "utf-16-le")
        else:
            key = f"<key-type-{kind}@{key_offset}>"
        buckets.append((key, indices))
    count = i32(entries_data, 0)
    if len(entries_data) != 4 + count * 28:
        raise ValueError("Unexpected catalog entry format")
    entries = [struct.unpack_from("<7i", entries_data, 4 + i * 28) for i in range(count)]

    def bundles_for(index: int, seen: set[int]) -> set[str]:
        if index in seen:
            return set()
        seen.add(index)
        internal, provider, dependency, _, _, _, _ = entries[index]
        if provider == 0:
            return {data["m_InternalIds"][internal].replace("\\", "/").split("/")[-1]}
        if dependency < 0:
            return set()
        result = set()
        for linked in buckets[dependency][1]:
            result.update(bundles_for(linked, seen))
        return result

    rows = []
    for i, (internal, provider, dependency, _, _, primary, resource_type) in enumerate(entries):
        rows.append({
            "entry": i, "key": buckets[primary][0],
            "internal_id": data["m_InternalIds"][internal],
            "type": data["m_resourceTypes"][resource_type]["m_ClassName"],
            "bundles": sorted(bundles_for(i, set())),
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game", type=Path)
    parser.add_argument("--out", type=Path, default=Path("data/inspection/catalog-index.json"))
    args = parser.parse_args()
    path = args.game / "YiXianPai_Data/StreamingAssets/aa/catalog.json"
    rows = read_catalog(path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    selected = [r for r in rows if r["type"] in ("UnityEngine.TextAsset", "I2.Loc.LanguageSourceAsset")]
    print(json.dumps({"entries": len(rows), "text_assets": len(selected),
                      "keys": [r["key"] for r in selected if r["key"].endswith("Config") or r["key"] in ("Localization", "DarkSun.HotUpdate")]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
