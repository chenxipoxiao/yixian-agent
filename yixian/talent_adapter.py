"""Audited raw talent IDs for the pinned, historical yisim combat engine.

Only the combat component is compiled. Acquisition rewards, permanent growth,
match settlement and candidate generation belong to the match environment.
Matching local descriptions is evidence, not current-server verification.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Any

from .simulator import REVISION

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = "2026-11-06"
SCOPE = "legacy_supported_unverified_current_season"
TABLE = ROOT / "data" / "local" / SNAPSHOT / "tables" / "TalentConfig.json"
LOCALIZATION = ROOT / "data" / "local" / SNAPSHOT / "raw" / "Localization.json"
SNAPSHOT_HASHES = {
    "TalentConfig.json": "1913e83d82a392a40f707ce988eecf3f85dead7b8156299ac14fb131513a72e8",
    "Localization.json": "6c0ca0411c897e281015e635eebac3008d22251067b5ac65fc39cfb0b527d68d",
}

# An entry is (engine field, implementation evidence, required player fields).
# The complete source-table hashes below freeze the parameters checked against
# these hooks. Grade variants are explicit raw IDs, never modulo normalization.
_SPECS: dict[int, tuple[str, str, tuple[str, ...]]] = {}


def _family(base: int, suffix: str, source: str, *, grades=(2, 3, 4, 5), needs=()):
    for grade in grades:
        _SPECS[base + (grade - 2) * 10000] = (
            f"p{grade}_{suffix}_stacks", source, tuple(needs))


for _base, _suffix, _source in (
    (13, "store_qi", "apply_p2_fates_setup/apply_p3_fates_setup/apply_p4_fates_setup/apply_p5_fates_setup: qi 1/1/2/3"),
    (16, "sword_rhyme_cultivate", "apply_p2_fates_setup/apply_p3_fates_setup/apply_p4_fates_setup/apply_p5_fates_setup: sword_intent 1/1/1/2"),
    (30, "divination", "apply_p2_fates_setup/apply_p3_fates_setup/apply_p4_fates_setup/apply_p5_fates_setup: hexagram 1/1/2/3"),
    (31, "stargaze", "apply_p2_fates_setup/apply_p3_fates_setup/apply_p4_fates_setup/apply_p5_fates_setup: star_power 1/1/1/1"),
    (57, "sword_formation_guard", "do_sword_formation_guard: first slot, def 1/3/6/9 and moon_water_sword_formation 1"),
    (69, "rule_of_the_cloud", "do_cloud_sword_softheart_and_friends: each cloud sword, def 1/2/2/3"),
    (71, "post_strike", "if_post_action/do_post_strike: first use of post-action card, def/max_hp/hp 2/3/4/5"),
    (102, "cycle_of_five_elements", "do_cycle_of_five_elements_and_friends: generation gives def 3 / qi 1 / max_hp+hp 4 / penetrate 4"),
    (103, "astral_eclipse", "apply_p2_fates_setup/apply_p3_fates_setup/apply_p4_fates_setup/apply_p5_fates_setup/increase_idx_debuff: first enemy debuff +1/1/2/3"),
    (120, "rejuvenation", "increase_idx_hp: max_hp before healing +3/4/5/6"),
    (145, "full_of_force", "apply_p2_fates_setup/apply_p3_fates_setup/apply_p4_fates_setup/apply_p5_fates_setup: force +1, max_force +0/1/2/3"),
    (150, "mark_of_dark_heart", "apply_p2_fates_setup/apply_p3_fates_setup/apply_p4_fates_setup/apply_p5_fates_setup: internal_injury/regen 1/2/2/3"),
):
    _family(_base, _suffix, _source)
_family(70, "mad_obsession", "apply_p4_fates_setup/apply_p5_fates_setup: initial unrestrained_sword_count +1", grades=(4, 5))
_family(127, "mutual_growth", "apply_p2_fates_setup/apply_p4_fates_setup/apply_p5_fates_setup/do_mutual_growth: upgrade first 1/2/3 generated cards", grades=(2, 4, 5))
_family(149, "regenerating_body", "do_regenerating_body: first slot physique 1/1/2/2, hp 1/2/4/6", needs=("physique", "max_physique"))
_family(176, "firmness_body", "apply_p2_fates_setup/apply_p3_fates_setup/apply_p4_fates_setup/apply_p5_fates_setup: heal floor(physique / 10,9,7,6)", needs=("physique", "max_physique"))

for _id, _field, _source in (
    (14, "endurance_as_cloud_sea", "do_cloud_sword_chain_count/if_cloud_hit: cloud chains persist and chain condition holds"),
    (15, "lithe_as_cat", "do_cloud_sword_softheart_and_friends: each cloud sword qi +1"),
    (25, "coral_sword", "do_coral_sword: initial ignore_def +2"),
    (33, "star_moon_folding_fan", "apply_p5_fates_setup: slot index 6 becomes a star point"),
    (61, "astrology", "increase_idx_hexagram: star_power +1 if zero"),
    (62, "astral_divination_hexagram", "do_astral_divination_hexagram: astral move hexagram +1"),
    (64, "birdie_wind", "reduce_idx_hp/increase_idx_hp: hp actually changes, def +1"),
    (66, "sword_in_sheathed", "do_sword_in_sheathed: turn without attack, def +3"),
    (67, "fire_flame_blade", "do_fire_flame_blade: each attack reduces enemy max_hp 1"),
    (68, "drift_ice_blade", "do_drift_ice_blade: each attack def +1, +2 if no def"),
    (82, "mark_of_five_elements", "apply_p2_fates_setup/do_cosmos_seal: next elemental card activates its element"),
    (99, "mark_of_water_spirit", "do_mark_of_water_spirit: activate water and qi +1"),
    (101, "blossom_dance", "do_cycle_of_five_elements_and_friends: generation qi/hp/max_hp +1; peach seal chases"),
    (108, "act_underhand", "if_post_action/if_c_pct: first post-action 1%, consumes hexagram for guaranteed trigger"),
    (110, "innate_mark", "do_innate_mark: activate explicit inherited element"),
    (112, "five_elements_anima", "increase_idx_activate: first wood atk1/fire enemy hp+max_hp -7/earth def12/metal penetrate4/water force2"),
    (125, "the_body_of_fierce_tiger", "do_the_body_of_fierce_tiger: hp >=120 upgrades first eligible level-1 card, preferring innate cards"),
    (134, "peach_branch_ruyi", "do_peach_branch_ruyi: guard_up +1"),
    (137, "fire_spirit_generation", "cards_have_generating_interaction: fire generates/is generated by every other element"),
    (138, "five_elements_explosion", "increase_idx_activate: every activation enemy hp/max_hp -3"),
    (139, "flame_soul_rebirth", "try_revive: first death sets hp/max_hp to 15"),
    (140, "swift_burning_seal", "do_swift_burning_seal: consume first seal and chase"),
    (142, "rest_and_outwit", "gain_qi_to_afford_card: qi 3 and hexagram 3 instead of qi 1"),
    (171, "courage_to_fight", "do_courage_to_fight: initial increase_atk +1 and wound +1"),
    (173, "stance_of_fierce_attack", "do_stance_of_fierce_attack: after physique card extra attack 3"),
    (174, "cracking_fist", "sim_turn: card hp cost instead reduces max_hp"),
    (177, "unwavering_soul", "increase_idx_debuff: heal 1 per gained debuff stack"),
    (179, "entering_styx", "do_entering_styx: initial styx +1"),
    (195, "spirit_hexagram_evolves", "increase_idx_qi/sim_turn: gained qi during own turn gives hexagram 1 at turn end"),
    (200, "herbs_flourish", "do_herbs_flourish/increase_idx_activate: non-element card activates wood; each wood activation max_hp +2"),
    (202, "five_elements_gather_qi", "increase_idx_activate: first activation of each element qi +1; per-element counters initialize to 1"),
    (203, "forget_worries_fate", "do_forget_worries_fate: initial wood activation"),
    (10093, "blade_forging_sharpness", "do_clear_heart: first attack +3"),
    (20093, "blade_forging_stable", "do_clear_heart: first attack -2, def +9"),
    (20094, "sword_pattern_carving_charge", "do_clear_heart: increase_atk +1"),
    (10095, "qi_forging_spiritage", "do_clear_heart: qi +2"),
    (20095, "qi_forging_spiritstat", "do_clear_heart: def +3 per qi"),
    (10096, "quench_of_sword_heart_unrestrained", "do_clear_heart/is_unrestrained_sword: attack +3; next card counts as unrestrained"),
    (20096, "quench_of_sword_heart_cloud", "do_clear_heart/is_cloud_sword: attack -7; next cloud card chases"),
    (30096, "quench_of_sword_heart_ultimate", "do_clear_heart: numeric clear-heart effects +1"),
):
    _SPECS[_id] = (_field + "_stacks", _source, ())
_SPECS[92] = ("swordsmith_stacks", "do_clear_heart: explicit accumulated attack bonus, capped at 18", ())
_SPECS[183] = ("zen_mind_forging_body_stacks", "do_zen_mind_forging_body: initial physique +1; excludes win/realm growth", ("physique", "max_physique"))
_SPECS[184] = ("mind_body_resonance_stacks", "increase_idx_physique: def +min(physique gained, 5)", ("physique", "max_physique"))

KNOWN_INCOMPATIBILITIES = {
    10094: "追击剑纹: current parameter is 6 extra attack; pinned do_clear_heart uses 5.",
    10127: "相生相成金丹: current limit is 2 upgrades; pinned p3_mutual_growth adds only 1.",
    153: "灵涌不竭: pinned code additionally requires/spends physique and max_hp; current description only spends 3 hp per missing qi.",
    209: "灵炁奔涌: pinned post_deck_setup forcibly resets stance to fist; current initial stance and switching are not reconciled.",
}
_DELEGATED = {45, 105}
SUPPORTED_TALENT_IDS = frozenset(_SPECS)
IMPLEMENTED_REGULAR_FATE_IDS = SUPPORTED_TALENT_IDS


@lru_cache(maxsize=1)
def _snapshot():
    contents = {}
    for path in (TABLE, LOCALIZATION):
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != SNAPSHOT_HASHES[path.name]:
            raise ValueError(f"Talent adapter snapshot changed: {path.name}; re-audit before use")
        contents[path.name] = json.loads(raw)
    rows = {int(row["id"]): row for row in contents["TalentConfig.json"]}
    terms = {term["Term"]: term["Languages"][0]
             for term in contents["Localization.json"]["mSource"]["mTerms"]}
    return rows, terms


def talent_adapter_contract() -> dict[str, Any]:
    """Contract must change with implementation or checked rule snapshots."""
    return {"schema_version": 1, "scope": SCOPE, "engine_revision": REVISION,
            "snapshot": SNAPSHOT, "snapshot_sha256": dict(SNAPSHOT_HASHES),
            "adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "current_server_verified": False, "combat_component_only": True,
            "acquisition_and_persistent_growth_implemented": False,
            "supported_raw_ids": sorted(SUPPORTED_TALENT_IDS)}


def compile_talents(fate_ids: Sequence[int], counters: Mapping | None = None,
                    *, player: Mapping | None = None) -> dict[str, Any]:
    """Compile only evidenced combat hooks to additive yisim player fields.

    Merge these increments once into a fresh pre-battle player, then run normal
    yisim setup. Do not also run independent start hooks for these raw IDs.
    Unknown IDs and incomplete required context remain explicitly unsupported.
    `player` supplies pre-battle physique/max_physique when required. Acquisition
    bonuses must already be reflected in those fields, hp and cultivation.

    Counter 92 must be {"swordsmith_attack_bonus": integer 0..18}; counter 110
    must be {"innate_element": "wood"|"fire"|"earth"|"metal"|"water"}. Raw
    replay integers are not silently assigned either interpretation.
    """
    if isinstance(fate_ids, (str, bytes)) or not isinstance(fate_ids, Sequence):
        raise ValueError("fate_ids must be a sequence of raw integer IDs")
    ids = list(fate_ids)
    if any(type(value) is not int or value <= 0 for value in ids):
        raise ValueError("talent IDs must be positive integers")
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate raw talent IDs would double-apply combat effects")
    if counters is not None and not isinstance(counters, Mapping):
        raise ValueError("counters must be a mapping")
    if player is not None and not isinstance(player, Mapping):
        raise ValueError("player must be a mapping")
    counters = counters or {}
    player = player or {}
    rows, terms = _snapshot()
    fields: dict[str, int] = {}
    coverage, unsupported = [], []
    for raw_id in ids:
        row = rows.get(raw_id, {})
        desc_key = f"TalentDesc_{raw_id}"
        if desc_key not in terms:
            desc_key = f"TalentDesc_{row.get('talentId', raw_id)}"
        entry = {"raw_id": raw_id, "name": row.get("name"),
                 "parameters": list(row["otherParams"]) if "otherParams" in row else None,
                 "description": terms.get(desc_key),
                 "scope": SCOPE, "combat_component_only": True,
                 "current_server_verified": False}
        reason = KNOWN_INCOMPATIBILITIES.get(raw_id)
        spec = _SPECS.get(raw_id)
        values = {}
        if raw_id in _DELEGATED:
            reason = "Delegated to match-level EffectEngine; never apply legacy destiny settlement twice."
        elif spec is None and reason is None:
            reason = "No audited pinned-engine mapping for this raw talent ID."
        if spec and reason is None:
            field, evidence, required = spec
            missing = [key for key in required if type(player.get(key)) is not int or player[key] < 0]
            if missing:
                reason = "Explicit pre-battle fields required: " + ", ".join(missing)
            else:
                values[field] = 1
                entry["implementation"] = "external/yisim/gamestate.jscpp::" + evidence
                entry["required_player_fields"] = list(required)
            if raw_id == 25 and 222 in ids:
                reason = "出渊 upgrades 珊瑚剑's attack count; pinned 2-attack hook does not cover that combination."
            if raw_id in (92, 110):
                context = counters.get(str(raw_id), counters.get(raw_id, {}))
                context = context if isinstance(context, Mapping) else {}
                if raw_id == 92:
                    value = context.get("swordsmith_attack_bonus")
                    if type(value) is not int or not 0 <= value <= 18:
                        reason = "Explicit counter 92.swordsmith_attack_bonus in [0,18] is required."
                    else:
                        values[field] = value
                else:
                    element = context.get("innate_element")
                    if element not in ("wood", "fire", "earth", "metal", "water"):
                        reason = "Explicit counter 110.innate_element is required."
                    else:
                        values[f"innate_{element}_stacks"] = 1
            if raw_id == 202:
                # These are reset counters, not earned activation stacks. They
                # equal yisim Player defaults; exposing them documents the
                # fresh-battle precondition without adding them a second time.
                entry["fresh_player_defaults_required"] = {
                    f"five_elements_gather_qi_{element}": 1
                    for element in ("wood", "fire", "earth", "metal", "water")}
        if reason is not None:
            entry.update(status="unsupported", reason=reason, player_fields={})
            unsupported.append(entry)
        else:
            entry.update(status="implemented_legacy_combat", player_fields=values)
            for field, value in values.items():
                fields[field] = fields.get(field, 0) + value
        coverage.append(entry)
    return {"player_fields": fields, "unsupported": unsupported, "coverage": coverage,
            "evidence": {"snapshot": SNAPSHOT, "snapshot_sha256": dict(SNAPSHOT_HASHES),
                         "engine_revision": REVISION, "scope": SCOPE},
            "combat_component_only": True, "current_server_verified": False}
