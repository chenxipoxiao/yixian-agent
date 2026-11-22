"""Round rules supported by supplied official FAQ images and user confirmation.

These functions plan one grant; they do not advance a match, manufacture a card
pool, or claim server calibration. The caller commits a round's plan exactly
once. In particular, the overflow hand count is the count at the draw boundary,
not a count inferred from future draws or a replay's later hand.
"""
from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
import hashlib
import math
from pathlib import Path

from .settlement import ordinary_destiny_damage


RULE_SOURCES = {
    "round_growth": {
        "kind": "description_backed", "origin": "user_supplied_official_faq_screenshots",
        "statement": "Each battle round grants 2 cultivation and 2 maximum health.",
    },
    "ordinary_draws": {
        "kind": "description_backed", "origin": "user_supplied_official_faq_screenshots",
        "statement": "Each round draws 2 sect cards and 1 profession card.",
    },
    "late_combined_draw": {
        "kind": "user_confirmed", "origin": "user_clarification_of_official_faq",
        "statement": "Round 12 onward adds one card uniformly from the remaining combined sect/profession card entities; do not choose category 50/50 first.",
    },
    "ordinary_rerolls": {
        "kind": "description_backed", "origin": "user_supplied_official_faq_screenshots",
        "statement": "Rounds 1-9 grant 3 rerolls; 10-14 grant 4; 15-19 grant 5; 20 onward grant 6.",
    },
    "season_rerolls": {
        "kind": "user_confirmed", "origin": "user_current_baijia_season_confirmation",
        "statement": "The current Baijia season has additional seasonal cards, so round 13 onward grants 6 rerolls.",
    },
    "hand_overflow": {
        "kind": "user_confirmed", "origin": "user_clarification_of_official_faq",
        "evidence": "data/inspection/user-draw-clarification-2026-11-12.json",
        "statement": "Only ordinary round-start draws: each hand card above12 cancels one scheduled draw for1 cultivation, capped by the scheduled count. Cancel from the end of sect,sect,profession,optional late combined draw; fate draws and replacements are exempt.",
    },
    "terminal_winner": {
        "kind": "description_backed", "origin": "user_supplied_official_faq_screenshots",
        "statement": "After terminal confirmation and all revival handling, when both HP values are negative the higher HP wins; equal negative HP favors the first player. Zero/zero is not established.",
    },
    "ordinary_destiny_damage": {
        "kind": "description_backed", "origin": "user_supplied_official_faq_and_existing_client_branch",
        "implementation": "yixian.settlement.ordinary_destiny_damage",
        "statement": "Reuse the existing piecewise ordinary destiny-damage rule; fate and seasonal modifiers remain separate.",
    },
}


def _round(value):
    if type(value) is not int or value < 1:
        raise ValueError("round_number must be a positive integer")
    return value


def _hand(value):
    if type(value) is not int or value < 0:
        raise ValueError("hand_card_count must be a nonnegative integer")
    return value


def reroll_grant(round_number: int, extra_season_cards: bool = True) -> int:
    """Return the grant for this round, before storage-cap or spending logic."""
    number = _round(round_number)
    if type(extra_season_cards) is not bool:
        raise ValueError("extra_season_cards must be an explicit boolean")
    if extra_season_cards and number >= 13:
        return 6
    if number < 10:
        return 3
    if number < 15:
        return 4
    if number < 20:
        return 5
    return 6


def round_draw_requests(round_number: int) -> list[dict]:
    """Describe draws in execution order, leaving normal pool rules external.

    The optional fourth card is sampled after the ordinary three draws, from
    the remaining physical entities in both pools. Duplicate card IDs are
    separate entities when they represent separate remaining copies.
    """
    number = _round(round_number)
    requests = [
        {"pool": "sect", "count": 2, "sampling": "external_pool_rule", "source": "ordinary_draws"},
        {"pool": "profession", "count": 1, "sampling": "external_pool_rule", "source": "ordinary_draws"},
    ]
    if number >= 12:
        requests.append({"pool": "combined_remaining", "count": 1,
                         "sampling": "uniform_remaining_card_entity",
                         "after_previous_requests": True, "source": "late_combined_draw"})
    return requests


def overflow_conversion(round_number: int, hand_card_count: int) -> dict:
    """Convert one round-start draw per excess hand card, removing the tail.

    Passing the prior round's ending hand is valid only if no intervening hand
    changes occurred. The threshold is tested once, before this grant's draws.
    """
    count = _hand(hand_card_count)
    requests = round_draw_requests(round_number)
    scheduled_count = sum(request["count"] for request in requests)
    missing_cards = min(max(0, count - 12), scheduled_count)
    remaining_count = scheduled_count - missing_cards
    retained, converted = [], []
    for request in requests:
        keep = min(request["count"], remaining_count)
        if keep:
            retained.append(dict(request, count=keep))
        if keep < request["count"]:
            converted.append(dict(request, count=request["count"] - keep))
        remaining_count -= keep
    return {
        "draw_requests": retained,
        "converted_draw_requests": converted,
        "scheduled_card_count": scheduled_count,
        "actual_draw_count": scheduled_count - missing_cards,
        "converted_card_count": missing_cards,
        "cultivation_gain": missing_cards,
        "pending": False,
        "hand_count_at_draw_boundary": count,
        "conversion_per_card": 1,
        "source": "hand_overflow",
        "source_kind": "user_confirmed",
        "applies_to": "ordinary_round_start_only",
        "cancellation_order": "last_scheduled_card_first",
    }


def round_resource_plan(round_number: int, hand_card_count: int, *, extra_season_cards: bool = True) -> dict:
    """Return amounts for one round without committing them or mutating state.

    Base growth and draw conversion are separate ledger entries. A caller that
    already credited post-battle base growth must add only the conversion gain
    at the draw boundary, not this plan's total cultivation a second time.
    """
    number = _round(round_number)
    conversion = overflow_conversion(number, hand_card_count)
    return {
        "round_number": number,
        "base_cultivation": 2,
        "converted_cultivation": conversion["cultivation_gain"],
        "total_cultivation": 2 + conversion["cultivation_gain"],
        "max_hp_gain": 2,
        "reroll_grant": reroll_grant(number, extra_season_cards),
        "draw_requests": deepcopy(conversion["draw_requests"]),
        "conversion": conversion,
        "sources": ["round_growth", "ordinary_draws", "hand_overflow",
                    "season_rerolls" if extra_season_cards and number >= 13 else "ordinary_rerolls"]
                   + (["late_combined_draw"] if number >= 12 else []),
        "state_committed": False,
        "current_server_verified": False,
    }


def draw_from_combined_remaining(sect_pool: Sequence, profession_pool: Sequence, *, rng) -> dict:
    """Draw one uniformly indexed remaining entity; return detached pools.

    Ordinary realm/rarity eligibility and the preceding three draws must have
    been resolved by the caller. This helper never invents those distributions.
    Pool entries are explicit card IDs, with repeated IDs denoting copies.
    """
    pools = []
    for pool in (sect_pool, profession_pool):
        if isinstance(pool, (str, bytes)) or not isinstance(pool, Sequence):
            raise ValueError("Each remaining pool must be a sequence of explicit card IDs")
        items = list(pool)
        if any(not ((type(card) is int and card > 0) or (isinstance(card, str) and card)) for card in items):
            raise ValueError("Pool entries must be positive integer or nonempty string card IDs")
        pools.append(items)
    total = len(pools[0]) + len(pools[1])
    if total == 0:
        raise ValueError("Cannot draw from an empty combined remaining pool")
    if not callable(getattr(rng, "randrange", None)):
        raise ValueError("An explicit random source with randrange is required")
    index = rng.randrange(total)
    if type(index) is not int or not 0 <= index < total:
        raise ValueError("Random source returned an invalid entity index")
    pool_index = int(index >= len(pools[0]))
    local_index = index - len(pools[0]) if pool_index else index
    card = pools[pool_index].pop(local_index)
    return {"card": card, "pool": "profession" if pool_index else "sect",
            "entity_index": index, "entity_count_before": total,
            "remaining_sect_pool": pools[0], "remaining_profession_pool": pools[1],
            "sampling": "uniform_remaining_card_entity", "source": "late_combined_draw"}


def select_terminal_winner(hps: Sequence, first_player: int, terminal_confirmed: bool) -> dict:
    """Resolve confirmed final HP, never predict death before revival handling.

    ``terminal_confirmed=True`` is the caller's assertion that battle execution
    and all revival/death-prevention hooks have finished. Equal zero and the
    zero-versus-negative boundary remain unresolved by the supplied evidence.
    """
    if (isinstance(hps, (str, bytes)) or not isinstance(hps, Sequence) or len(hps) != 2
            or any(type(hp) not in (int, float) or not math.isfinite(hp) for hp in hps)):
        raise ValueError("hps must contain exactly two finite numeric values")
    if type(first_player) is not int or first_player not in (0, 1):
        raise ValueError("first_player must be 0 or 1")
    if type(terminal_confirmed) is not bool:
        raise ValueError("terminal_confirmed must be an explicit boolean")
    result = {"winner": None, "resolved": False, "reason": "terminal_not_confirmed",
              "source": "terminal_winner", "source_kind": "description_backed",
              "current_server_verified": False}
    if not terminal_confirmed:
        return result
    alive = [hp > 0 for hp in hps]
    if alive[0] != alive[1]:
        result.update(winner=0 if alive[0] else 1, resolved=True, reason="single_survivor")
    elif hps[0] < 0 and hps[1] < 0:
        if hps[0] == hps[1]:
            result.update(winner=first_player, resolved=True, reason="equal_negative_hp_first_player")
        else:
            result.update(winner=0 if hps[0] > hps[1] else 1, resolved=True, reason="higher_negative_hp")
    elif hps[0] == 0 and hps[1] == 0:
        result["reason"] = "zero_hp_tie_unverified"
    elif not any(alive):
        result["reason"] = "zero_hp_boundary_unverified"
    else:
        result["reason"] = "no_defeated_player"
    return result


def round_rules_contract() -> dict:
    return {"schema_version": 2,
            "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "source_types": ["description_backed", "user_confirmed"],
            "sources": deepcopy(RULE_SOURCES),
            "current_server_verified": False,
            "ordinary_draw_sampling_distribution_implemented": False,
            "combined_remaining_entity_sampling_implemented": True,
            "zero_hp_tie_resolved": False}
