"""A bounded deck-order curriculum, not a complete Yi Xian match environment.

The learner chooses a permutation of eight cards already owned by player zero.
Only the player's own initial state and chosen slots are observable. Opponent
hidden state, random seeds and future results never enter policy observations.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import math
import random
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .research import canonical_json
from .simulator import simulate_battle


class EnvironmentProtocolError(RuntimeError):
    """The injected simulator did not provide a trustworthy terminal status."""


class DeckOrderEnv:
    observation_dim = obs_dim = 217
    action_dim = 8
    observation_schema = "deck-order-v2-217"
    scope = "fixed_battle_deck_order_curriculum"
    full_match_environment = False
    current_season_verified = False
    _SCALARS = (("hp", 100), ("max_hp", 100), ("qi", 20), ("def", 100),
                ("cultivation", 100), ("round_number", 20), ("destiny", 100), ("physique", 100))

    def __init__(self, battle_pool: Sequence[Mapping[str, Any]] | Mapping[str, Any],
                 simulator: Callable[[dict], dict] = simulate_battle, *, shuffle_cards: bool = True):
        if isinstance(battle_pool, Mapping):
            battle_pool = [battle_pool]
        if not isinstance(battle_pool, Sequence) or not battle_pool:
            raise ValueError("battle_pool must contain at least one battle")
        self._pool = []
        identifiers = set()
        for index, item in enumerate(battle_pool):
            if not isinstance(item, Mapping):
                raise ValueError("Each battle case must be an object")
            battle = deepcopy(item.get("battle", item))
            case_id = item.get("id", f"case-{index}") if "battle" in item else f"case-{index}"
            if not isinstance(case_id, str) or not case_id.strip() or case_id in identifiers:
                raise ValueError("Every case needs a unique, nonempty string id")
            identifiers.add(case_id)
            canonical_json(battle)
            if not isinstance(battle, dict) or not isinstance(battle.get("players"), list) or len(battle["players"]) != 2:
                raise ValueError("Each battle must have two players")
            for player in battle["players"]:
                if (not isinstance(player, dict) or not isinstance(player.get("cards"), list)
                        or len(player["cards"]) != 8
                        or not all(isinstance(card, str) and card for card in player["cards"])):
                    raise ValueError("Both players require eight explicit card ids")
            for field, _ in self._SCALARS:
                value = battle["players"][0].get(field, 0)
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise ValueError(f"Own visible scalar {field} must be finite")
            if not isinstance(battle["players"][0].get("character", ""), str):
                raise ValueError("Own character must be a string")
            self._pool.append((case_id, battle))
        if not callable(simulator):
            raise TypeError("simulator must be callable")
        self._simulator = simulator
        self.shuffle_cards = bool(shuffle_cards)
        self._battle = None
        self._order: list[int] = []
        self._done = False

    @staticmethod
    def _token_features(token: str, width: int) -> list[float]:
        # Stable across processes and independent of Python's randomized hash().
        # This is a small curriculum encoding, not a pretrained card embedding.
        return [value / 127.5 - 1 for value in hashlib.sha256(token.encode("utf-8")).digest()[:width]]

    def observation(self) -> list[float]:
        self._require_reset()
        features = [0.0] * 64
        for position, slot in enumerate(self._order):
            features[position * 8 + slot] = 1.0
        features.extend(self.action_mask())
        features.append(len(self._order) / 8)
        for card in self._cards:
            features.extend(self._token_features(card, 16))
        own = self._battle["players"][0]
        features.extend(max(-4.0, min(4.0, own.get(field, 0) / scale)) for field, scale in self._SCALARS)
        features.extend(self._token_features(own.get("character", ""), 8))
        assert len(features) == self.observation_dim
        return features

    def reset(self, seed: int) -> tuple[list[float], dict]:
        if type(seed) is not int:
            raise ValueError("An explicit integer episode seed is required")
        rng = random.Random(seed)
        case_id, battle = self._pool[rng.randrange(len(self._pool))]
        new_battle = deepcopy(battle)
        cards = list(new_battle["players"][0]["cards"])
        if self.shuffle_cards:
            rng.shuffle(cards)
        new_battle["players"][0]["cards"] = cards
        new_battle["seed"] = seed
        self._battle, self._cards, self._case_id, self._seed = new_battle, cards, case_id, seed
        self._order, self._done = [], False
        return self.observation(), self._info()

    def _require_reset(self):
        if self._battle is None:
            raise RuntimeError("Call reset(seed) before using the environment")

    def legal_actions(self) -> list[int]:
        self._require_reset()
        return [] if self._done else [slot for slot in range(8) if slot not in self._order]

    def action_mask(self) -> list[float]:
        legal = set(self.legal_actions())
        return [float(slot in legal) for slot in range(8)]

    def _info(self) -> dict:
        return {"case_id": self._case_id, "scope": self.scope,
                "full_match_environment": False, "current_season_verified": False,
                "action_mask": self.action_mask(), "selected_slots": list(self._order),
                "observation_schema": self.observation_schema}

    def step(self, action: int) -> tuple[list[float], float, bool, bool, dict]:
        self._require_reset()
        if type(action) is not int or action not in self.legal_actions():
            raise ValueError("Action must be an unselected original card slot from 0 to 7")
        proposed = self._order + [action]
        if len(proposed) < 8:
            self._order = proposed
            return self.observation(), 0.0, False, False, self._info()
        battle = deepcopy(self._battle)
        battle["players"][0]["cards"] = [self._cards[slot] for slot in proposed]
        # Do not commit the final action until simulation and result validation succeed.
        result = self._simulator(battle)
        if not isinstance(result, dict) or type(result.get("terminated")) is not bool or type(result.get("truncated")) is not bool:
            raise EnvironmentProtocolError("Simulator must report boolean terminated and truncated flags")
        terminated, truncated = result["terminated"], result["truncated"]
        if terminated == truncated:
            raise EnvironmentProtocolError("A full battle rollout must terminate or truncate, exclusively")
        winner = result.get("winner")
        if winner is not None and (type(winner) is not int or winner not in (0, 1)):
            raise EnvironmentProtocolError("Invalid winner index")
        # Ignore any alleged winner on a capped rollout: it cannot label learning.
        reward = 0.0 if truncated or winner is None else (1.0 if winner == 0 else -1.0)
        self._order, self._done = proposed, True
        info = self._info()
        info.update({"winner": None if truncated else winner,
                     "label_usable": terminated and winner is not None,
                     "battle_result": deepcopy(result), "ordered_cards": list(battle["players"][0]["cards"])})
        return self.observation(), reward, terminated, truncated, info

    def contract(self) -> dict:
        return {"environment": self.scope, "observation_schema": self.observation_schema,
                "observation_dim": self.observation_dim, "action_dim": self.action_dim,
                "full_match_environment": False, "current_season_verified": False,
                "shuffle_cards": self.shuffle_cards,
                "cases_sha256": hashlib.sha256(canonical_json(self._pool_as_json()).encode("utf-8")).hexdigest()}

    def _pool_as_json(self):
        return [{"id": case_id, "battle": battle} for case_id, battle in self._pool]
