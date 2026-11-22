"""Export data/configuration assets from an owned installation, read-only."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import warnings
from pathlib import Path
import UnityPy
from inspect_catalog import read_catalog


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(game: Path, out: Path, unity_version: str):
    UnityPy.config.FALLBACK_UNITY_VERSION = unity_version
    root = game / "YiXianPai_Data/StreamingAssets/aa"
    catalog = root / "catalog.json"
    rows = read_catalog(catalog)
    wanted = {r["key"]: r for r in rows if r["key"].endswith("Config") or r["key"] in ("DarkSun.HotUpdate", "Localization")}
    bundles = sorted({b for r in wanted.values() for b in r["bundles"]})
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"source_installation": str(game.resolve()), "catalog_sha256": digest(catalog),
                "catalog_versions": sorted(p.name for p in root.rglob("catalog_*.hash")),
                "unity_version": unity_version, "assets": [], "errors": [],
                "scope": "local configuration snapshot; not proof of server rule equivalence"}
    for bundle in bundles:
        source = root / "StandaloneWindows64" / bundle
        if not source.exists():
            manifest["errors"].append({"bundle": bundle, "error": "missing"})
            continue
        env = UnityPy.load(str(source))
        for obj in env.objects:
            if obj.type.name == "TextAsset":
                asset = obj.read()
                if asset.m_Name not in wanted:
                    continue
                payload = asset.m_Script.encode("utf-8", "surrogateescape")
                suffix = ".dll" if payload.startswith(b"MZ") else ".bytes"
                target = out / (re.sub(r"[^A-Za-z0-9_.-]", "_", asset.m_Name) + suffix)
                target.write_bytes(payload)
                manifest["assets"].append({"name": asset.m_Name, "path": target.name,
                    "bytes": len(payload), "sha256": digest(target), "bundle": bundle,
                    "bundle_sha256": digest(source), "path_id": obj.path_id})
            elif obj.type.name == "MonoBehaviour" and any(r["key"] == "Localization" and bundle in r["bundles"] for r in wanted.values()):
                try:
                    tree = obj.read_typetree()
                    if tree.get("m_Name") != "Localization":
                        continue
                    target = out / "Localization.json"
                    target.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
                    manifest["assets"].append({"name": "Localization", "path": target.name,
                        "bytes": target.stat().st_size, "sha256": digest(target), "bundle": bundle,
                        "bundle_sha256": digest(source), "path_id": obj.path_id})
                except Exception as error:
                    manifest["errors"].append({"bundle": bundle, "error": str(error)})
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game", type=Path)
    parser.add_argument("--out", type=Path, default=Path("data/local/2026-11-06/raw"))
    parser.add_argument("--unity-version", default="2020.3.49f1", help="Use installed UnityPlayer.dll ProductVersion")
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="No valid Unity version found.*")
        report = extract(args.game, args.out, args.unity_version)
    print(json.dumps({"extracted": len(report["assets"]), "errors": report["errors"], "output": str(args.out)}, ensure_ascii=False))
