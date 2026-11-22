"""CPU-only bridge to a pinned legacy yisim single-battle research reference."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

from .research import canonical_json, contract_digest

ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIRECTORY = ROOT / "external" / "yisim"
BRIDGE = ROOT / "tools" / "yisim_bridge.mjs"
REVISION = "c24e891283bf0e9e310ae2ba41993280ab328535"


class SimulatorError(RuntimeError):
    """Engine setup, input validation or simulation failed."""


def is_available() -> bool:
    """Lightweight installation check; simulate_battle additionally verifies hashes."""
    return bool(shutil.which("node") and (ENGINE_DIRECTORY / "research-manifest.json").is_file()
                and (ENGINE_DIRECTORY / "gamestate_full.js").is_file())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def engine_contract() -> dict[str, Any]:
    """Verify pinned source/build and return the actual research engine contract.

    The contract intentionally does not borrow the installed client's version:
    an extracted card table does not prove this simulator follows current rules.
    """
    try:
        manifest = json.loads((ENGINE_DIRECTORY / "research-manifest.json").read_text(encoding="utf-8"))
        if manifest["revision"] != REVISION:
            raise SimulatorError("External yisim revision differs from the supported pinned revision.")
        source_hashes = {}
        for entry in manifest["files"]:
            path = ENGINE_DIRECTORY / entry["path"]
            if path.parent.resolve() != ENGINE_DIRECTORY.resolve():
                raise SimulatorError("Unexpected external manifest file path.")
            actual = _sha256(path)
            if actual != entry["sha256"]:
                raise SimulatorError(f"External source changed: {entry['path']}. Run tools/setup_yisim.py.")
            source_hashes[entry["path"]] = actual
        generated_hash = _sha256(ENGINE_DIRECTORY / "gamestate_full.js")
        if generated_hash != manifest["generated_sha256"]:
            raise SimulatorError("Generated simulator changed. Rebuild with tools/setup_yisim.py.")
        for package, version in manifest["dependencies"].items():
            installed = json.loads((ENGINE_DIRECTORY / "node_modules" / package / "package.json").read_text(encoding="utf-8"))
            if installed["version"] != version:
                raise SimulatorError(f"Unexpected dependency version: {package}")
        return {
            "engine": "sharpobject/yisim",
            "revision": REVISION,
            "status": "legacy_unverified",
            "rules_version": None,
            "rules_verified": False,
            "full_match_environment": False,
            "observation_schema": "yixian-battle-v1",
            "action_schema": "fixed-eight-slot-decks-v1",
            "source_files_sha256": source_hashes,
            "generated_sha256": generated_hash,
            "bridge_sha256": _sha256(BRIDGE),
            "season_runtime_sha256": _sha256(ROOT/'tools/season_runtime.mjs'),
            "dependencies": manifest["dependencies"],
        }
    except (OSError, ValueError, KeyError) as error:
        raise SimulatorError("External yisim is not set up correctly. Run python tools/setup_yisim.py.") from error


def simulate_battle(battle: Mapping[str, Any], *, timeout: float = 20) -> dict[str, Any]:
    """Run a seeded fixed-deck battle, returning original player indices.

    Both players need eight explicit yisim card IDs, hp, max_hp, cultivation,
    round_number and destiny. first_player is supplied explicitly, not inferred.
    A capped rollout has truncated=True and winner=None; it is not a win label.
    """
    node = shutil.which("node")
    if node is None:
        raise SimulatorError("Node.js is required. Install it before setting up yisim.")
    if not isinstance(battle, Mapping):
        raise ValueError("battle must be a JSON object")
    payload = canonical_json(dict(battle))
    contract = engine_contract()
    try:
        process = subprocess.run(
            [node, "--experimental-default-type=module", str(BRIDGE)],
            input=payload, text=True, encoding="utf-8", capture_output=True,
            cwd=ROOT, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise SimulatorError(f"Battle simulation exceeded {timeout:g} seconds; no result label was produced.") from error
    except OSError as error:
        raise SimulatorError(f"Cannot start the simulator: {error}") from error
    if process.returncode:
        raise SimulatorError(process.stderr.strip() or f"Simulator exited with code {process.returncode}")
    try:
        result = json.loads(process.stdout)
        if not isinstance(result, dict) or result.get("schema_version") != 1:
            raise ValueError("unexpected response schema")
    except ValueError as error:
        raise SimulatorError("Simulator returned an invalid JSON response.") from error
    result["engine_contract"] = contract_digest(contract)
    return result
