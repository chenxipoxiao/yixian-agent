"""Explicit user-confirmed current-ranked context, never a missing-field default."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT/'data/inspection/user-ranked-resonance-2026-11-12.json'


def ranked_context(*, version, game_mode, season_mec, observed_resonance=None):
    evidence = json.loads(PROOF.read_text(encoding='utf-8'))
    if (version not in evidence['replay_version_scope'] or type(game_mode) is not int
            or type(season_mec) is not int or (game_mode, season_mec) != (3, 10)):
        raise ValueError('No confirmed resonance rule for this version/mode/season')
    if observed_resonance is not None and (type(observed_resonance) is not int or observed_resonance != 0):
        raise ValueError('Observed resonance contradicts current ranked scope')
    return {'version':version, 'game_mode':game_mode, 'season_mec':season_mec,
            'resonance_selected':0, 'source':'explicit_user_current_ranked_rule',
            'evidence_sha256':hashlib.sha256(PROOF.read_bytes()).hexdigest(),
            'independent_server_verification':False}
