"""Apply frozen ordinary-fate imitation weights to an explicit choice menu."""
import json
import math
from pathlib import Path

from .match_flow import ScriptedFlowAgent


class FateChoiceFlowAgent(ScriptedFlowAgent):
    """Use learned fate preferences and the existing scripted actions elsewhere."""

    def __init__(self, weights_path):
        weights = json.loads(Path(weights_path).read_text(encoding="utf-8"))
        self.weights = {int(key): float(score) for key, score in weights.items()}
        if not all(math.isfinite(score) for score in self.weights.values()):
            raise ValueError("Fate preference scores must be finite")

    def choose_fate(self, observation, candidates):
        if not candidates or any(type(candidate) is not int for candidate in candidates):
            raise ValueError("An explicit nonempty menu of ordinary fate IDs is required")
        return max(candidates, key=lambda candidate: self.weights.get(candidate, 0.0))
