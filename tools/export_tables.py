"""Decode exported configuration protobufs using statically verified field maps."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from yixian.protobuf_wire import decode_row, table_rows


def render_description(row):
    def replace(match):
        key, index = match.group(1), match.group(2)
        value = row.get(key)
        if index is not None:
            if not isinstance(value, list) or int(index) >= len(value):
                return match.group(0)
            value = value[int(index)]
        return str(value) if isinstance(value, (str, int, float)) else match.group(0)
    return re.sub(r"\{([A-Za-z_][A-Za-z_0-9]*)(?:\[(\d+)\])?\}", replace, row.get("desc", "")).replace("\\n", "\n")


def export(raw: Path, schemas: Path, out: Path):
    definitions = json.loads(schemas.read_text(encoding="utf-8"))
    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    report = {"source_catalog_sha256": manifest["catalog_sha256"],
              "schema_sha256": hashlib.sha256(schemas.read_bytes()).hexdigest(),
              "tables": {}, "claim": "configuration entries, including upgrades/legacy/test entries; not current playable card-pool counts"}
    out.mkdir(parents=True, exist_ok=True)
    for name, schema in definitions.items():
        source = raw / (name + ".bytes")
        entries = [decode_row(row, schema) for row in table_rows(source.read_bytes())]
        for row in entries:
            if "desc" in row:
                row["description_preview"] = render_description(row)
        (out / (name + ".json")).write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
        report["tables"][name] = {"rows": len(entries), "rows_with_unknown_fields": sum("_unknown_fields" in row for row in entries),
                                 "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
    (out / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, default=Path("data/local/2026-11-06/raw"))
    p.add_argument("--schema", type=Path, default=Path("data/inspection/protobuf-decode-schemas.json"))
    p.add_argument("--out", type=Path, default=Path("data/local/2026-11-06/tables"))
    a = p.parse_args()
    print(json.dumps(export(a.raw, a.schema, a.out), ensure_ascii=False, indent=2))
