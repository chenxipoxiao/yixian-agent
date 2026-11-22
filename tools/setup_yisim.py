"""Install a pinned, unmodified external yisim research reference (standard library).

The upstream repository has no declared license in the inspected revision.
Files stay under external/ and are not part of this project's own source.
This engine is not validated against the currently installed YiXian season.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "external" / "yisim"
REVISION = "c24e891283bf0e9e310ae2ba41993280ab328535"
UPSTREAM = "https://github.com/sharpobject/yisim"
# Git blob ids from the tree of REVISION, checked before every write.
FILES = {
    "README.md": "dab11302d795955a7937035c1978299bc031a445",
    "bun.lock": "cef99258c07ecd1e4e3802921ce11fcbf9e2053b",
    "card_actions.js": "f285a663479f226bc182378b27af1712532f9a93",
    "card_info.js": "fc37f4e4eee6fd441ed97d2fedd05c0286708c80",
    "card_json_node.js": "89696deecd087bc74d1559bf3ccfd682927b3804",
    "deps.js": "a62a5874648cf1dbec43a5ffd4ff341645cc1b71",
    "gamestate.jscpp": "55761b87e6f3283ad98ad922eec7831943fbd283",
    "names.json": "c02d1005d8d556a3bba7725a829441dde44f5409",
    "package.json": "d27c692516300c1085081d65010f39d83799abcd",
    "preprocess.js": "8272dfe697e065ebbc45152bc841455928f1800e",
    "preprocessor.js": "289910f2761c9f46610b6e2132344f433d183fa7",
    "swogi.json": "ce91efe77ece1ed5eff26934e79f50244c6e6b4e",
    "todo_patches.txt": "b6f5c8d4a3ce0563de4b30c466772083942ef190"
}

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

def download(name: str, expected_sha: str) -> dict:
    destination = DESTINATION / name
    data = destination.read_bytes() if destination.exists() else b""
    if git_blob_sha(data) != expected_sha:
        url = f"https://raw.githubusercontent.com/sharpobject/yisim/{REVISION}/{name}"
        request = urllib.request.Request(url, headers={"User-Agent": "YiXian-Research-Setup"})
        with urllib.request.urlopen(request, timeout=25) as response:
            data = response.read()
        if git_blob_sha(data) != expected_sha:
            raise RuntimeError(f"Upstream content hash mismatch: {name}")
        destination.write_bytes(data)
    return {"path": name, "git_blob_sha1": expected_sha, "sha256": hashlib.sha256(data).hexdigest()}

def main() -> int:
    node = shutil.which("node")
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not node or not npm:
        raise RuntimeError("Node.js and npm are required.")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as executor:
        entries = list(executor.map(lambda pair: download(*pair), FILES.items()))
    print(f"Verified {len(entries)} pinned upstream files.", flush=True)
    # Pin dependencies explicitly; do not run any dependency lifecycle scripts.
    subprocess.run(
        [npm, "install", "--ignore-scripts", "--no-audit", "--no-fund", "--no-save",
         "@leeoniya/ufuzzy@1.0.14", "seedrandom@3.0.5"],
        cwd=DESTINATION, check=True, timeout=120,
    )
    subprocess.run(
        [node, "--experimental-default-type=module", "preprocess.js"],
        cwd=DESTINATION, check=True, timeout=30,
    )
    generated = DESTINATION / "gamestate_full.js"
    manifest = {
        "upstream": UPSTREAM,
        "revision": REVISION,
        "status": "legacy_unverified",
        "rules_version": None,
        "current_season_verified": False,
        "license": "not_declared_in_inspected_revision",
        "files": entries,
        "generated_sha256": hashlib.sha256(generated.read_bytes()).hexdigest(),
        "dependencies": {"@leeoniya/ufuzzy": "1.0.14", "seedrandom": "3.0.5"},
    }
    (DESTINATION / "research-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print("Built gamestate_full.js from the pinned source. Current-season fidelity is UNVERIFIED.")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Setup failed: {error}", file=sys.stderr)
        raise SystemExit(1)

