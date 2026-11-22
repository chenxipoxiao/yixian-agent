"""Small CPU PPO learner for explicitly scoped, masked discrete curricula.

This is a trainable MLP baseline, not TavernAgent's architecture and not evidence
of full-match or current-season skill. Truncated episodes are excluded completely.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import tempfile
import time
from typing import Callable, Mapping

import numpy as np

from .research import canonical_json, contract_digest


@dataclass(frozen=True)
class PPOConfig:
    updates: int = 4
    episodes_per_update: int = 16
    epochs: int = 3
    minibatch_size: int = 64
    hidden_size: int = 32
    learning_rate: float = 0.001
    seed: int = 0
    training_seed_base: int = 10000
    action_dim: int = 8
    gamma: float = 1.0
    gae_lambda: float = 0.95
    clip_ratio: float = 0.2
    entropy_coefficient: float = 0.01
    value_coefficient: float = 0.5
    max_grad_norm: float = 0.5
    max_episode_steps: int = 64
    reserved_evaluation_seeds: tuple[int, ...] = ()

    def validate(self):
        for name in ("updates", "episodes_per_update", "epochs", "minibatch_size",
                     "hidden_size", "action_dim", "max_episode_steps"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("seed", "training_seed_base"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        for name in ("learning_rate", "max_grad_norm"):
            if not np.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive and finite")
        for name in ("gamma", "gae_lambda"):
            if not 0 <= getattr(self, name) <= 1:
                raise ValueError(f"{name} must be in [0, 1]")
        if not 0 < self.clip_ratio < 1:
            raise ValueError("clip_ratio must be in (0, 1)")
        for name in ("entropy_coefficient", "value_coefficient"):
            if not np.isfinite(getattr(self, name)) or getattr(self, name) < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if any(type(s) is not int or s < 0 for s in self.reserved_evaluation_seeds):
            raise ValueError("reserved evaluation seeds must be nonnegative integers")


def masked_softmax(logits, mask):
    logits, mask = np.asarray(logits, dtype=np.float64), np.asarray(mask, dtype=bool)
    if logits.ndim != 2 or logits.shape != mask.shape or not np.all(mask.any(axis=1)):
        raise ValueError("Each logits row needs a same-size mask with a legal action")
    if not np.all(np.isfinite(logits)):
        raise ValueError("Nonfinite logits")
    masked = np.where(mask, logits, -np.inf)
    weights = np.exp(masked - np.max(masked, axis=1, keepdims=True))
    return weights / weights.sum(axis=1, keepdims=True)


def compute_gae(rewards, values, terminated, *, gamma=1.0, gae_lambda=0.95, bootstrap_value=0.0):
    """GAE, with termination resetting both bootstrap and recursive advantage.

    Truncation is deliberately not represented here. The collector drops such
    episodes. A caller using this helper for a nonterminal segment supplies its
    final bootstrap value explicitly.
    """
    rewards, values = np.asarray(rewards, dtype=float), np.asarray(values, dtype=float)
    terminated = np.asarray(terminated, dtype=bool)
    if rewards.ndim != 1 or rewards.shape != values.shape or values.shape != terminated.shape:
        raise ValueError("GAE arrays must have the same one-dimensional shape")
    if not (np.all(np.isfinite(rewards)) and np.all(np.isfinite(values)) and np.isfinite(bootstrap_value)):
        raise ValueError("Nonfinite GAE inputs")
    advantages = np.zeros_like(rewards)
    carry, next_value = 0.0, float(bootstrap_value)
    for index in reversed(range(len(rewards))):
        continuation = 0.0 if terminated[index] else 1.0
        delta = rewards[index] + gamma * next_value * continuation - values[index]
        carry = delta + gamma * gae_lambda * continuation * carry
        advantages[index] = carry
        next_value = values[index]
    return advantages, advantages + values


class PolicyValueNet:
    def __init__(self, obs_dim: int, action_dim: int = 8, hidden_size: int = 32, seed: int = 0):
        if any(type(x) is not int or x < 1 for x in (obs_dim, action_dim, hidden_size)):
            raise ValueError("Network dimensions must be positive integers")
        self.obs_dim, self.action_dim, self.hidden_size = obs_dim, action_dim, hidden_size
        rng = np.random.default_rng(seed)
        self.params = {
            "w1": rng.normal(0, 1 / np.sqrt(obs_dim), (obs_dim, hidden_size)),
            "b1": np.zeros(hidden_size),
            "wp": rng.normal(0, 0.01 / np.sqrt(hidden_size), (hidden_size, action_dim)),
            "bp": np.zeros(action_dim),
            "wv": rng.normal(0, 1 / np.sqrt(hidden_size), hidden_size),
            "bv": np.zeros(1),
        }
        self.contract_digest: str | None = None
        self.training_state: dict = {}
        self.optimizer: dict | None = None

    @property
    def parameter_count(self):
        return sum(array.size for array in self.params.values())

    def forward(self, observations, masks):
        x = np.asarray(observations, dtype=float)
        if x.ndim != 2 or x.shape[1] != self.obs_dim or not np.isfinite(x).all():
            raise ValueError("Invalid observation shape or nonfinite observation")
        h = np.tanh(x @ self.params["w1"] + self.params["b1"])
        probabilities = masked_softmax(h @ self.params["wp"] + self.params["bp"], masks)
        values = h @ self.params["wv"] + self.params["bv"][0]
        return probabilities, values, h

    def act(self, observation, legal_actions, *, rng=None, deterministic=False):
        mask = action_mask(legal_actions, self.action_dim)
        probabilities, values, _ = self.forward([observation], [mask])
        if deterministic:
            action = int(np.argmax(probabilities[0]))
        else:
            if rng is None:
                raise ValueError("Stochastic actions require an explicit RNG")
            action = int(rng.choice(self.action_dim, p=probabilities[0]))
        return action, float(np.log(max(probabilities[0, action], 1e-300))), float(values[0])

    def loss_and_gradients(self, batch, config: PPOConfig):
        x = np.asarray(batch["observations"], dtype=float)
        masks = np.asarray(batch["masks"], dtype=bool)
        actions = np.asarray(batch["actions"], dtype=int)
        old_logs = np.asarray(batch["old_log_probs"], dtype=float)
        advantage = np.asarray(batch["advantages"], dtype=float)
        returns = np.asarray(batch["returns"], dtype=float)
        n = len(x)
        if n == 0 or any(len(v) != n for v in (actions, old_logs, advantage, returns)):
            raise ValueError("Empty or inconsistent PPO batch")
        if np.any(actions < 0) or np.any(actions >= self.action_dim) or not masks[np.arange(n), actions].all():
            raise ValueError("PPO batch contains an illegal action")
        if not all(np.isfinite(v).all() for v in (old_logs, advantage, returns)):
            raise ValueError("Nonfinite PPO targets")
        probs, values, hidden = self.forward(x, masks)
        log_probs = np.log(np.maximum(probs, 1e-300))
        selected_logs = log_probs[np.arange(n), actions]
        ratios = np.exp(selected_logs - old_logs)
        if not np.isfinite(ratios).all():
            raise ValueError("Nonfinite PPO importance ratio")
        clipped = np.clip(ratios, 1 - config.clip_ratio, 1 + config.clip_ratio)
        policy_loss = -np.minimum(ratios * advantage, clipped * advantage).mean()
        value_loss = 0.5 * np.mean((values - returns) ** 2)
        entropy = -np.sum(probs * log_probs, axis=1)
        loss = policy_loss + config.value_coefficient * value_loss - config.entropy_coefficient * entropy.mean()

        active = ((advantage >= 0) & (ratios <= 1 + config.clip_ratio)) | ((advantage < 0) & (ratios >= 1 - config.clip_ratio))
        dlog = -advantage * ratios * active / n
        one_hot = np.zeros_like(probs)
        one_hot[np.arange(n), actions] = 1
        dlogits = dlog[:, None] * (one_hot - probs)
        dlogits += config.entropy_coefficient * probs * (log_probs + entropy[:, None]) / n
        dlogits[~masks] = 0.0
        dvalue = config.value_coefficient * (values - returns) / n
        dh = (dlogits @ self.params["wp"].T + dvalue[:, None] * self.params["wv"]) * (1 - hidden ** 2)
        grads = {
            "w1": x.T @ dh, "b1": dh.sum(axis=0),
            "wp": hidden.T @ dlogits, "bp": dlogits.sum(axis=0),
            "wv": hidden.T @ dvalue, "bv": np.array([dvalue.sum()]),
        }
        diagnostics = {"loss": float(loss), "policy_loss": float(policy_loss),
                       "value_loss": float(value_loss), "entropy": float(entropy.mean()),
                       "clip_fraction": float(np.mean(np.abs(ratios - 1) > config.clip_ratio)),
                       "approx_kl": float(np.mean((ratios - 1) - (selected_logs - old_logs)))}
        return float(loss), grads, diagnostics


def action_mask(legal_actions, action_dim):
    legal = list(legal_actions)
    if not legal or any(type(a) is not int or a < 0 or a >= action_dim for a in legal) or len(set(legal)) != len(legal):
        raise ValueError("Invalid legal action list")
    result = np.zeros(action_dim, dtype=bool)
    result[legal] = True
    return result


def _adam_step(model, gradients, config):
    if model.optimizer is None:
        model.optimizer = {"step": 0, "m": {k: np.zeros_like(v) for k,v in model.params.items()},
                           "v": {k: np.zeros_like(v) for k,v in model.params.items()}}
    norm = float(np.sqrt(sum(np.sum(g * g) for g in gradients.values())))
    if not np.isfinite(norm):
        raise ValueError("Nonfinite gradient")
    scale = min(1.0, config.max_grad_norm / max(norm, 1e-12))
    state = model.optimizer
    state["step"] += 1
    for key, gradient in gradients.items():
        gradient = gradient * scale
        state["m"][key] = 0.9 * state["m"][key] + 0.1 * gradient
        state["v"][key] = 0.999 * state["v"][key] + 0.001 * gradient ** 2
        m = state["m"][key] / (1 - 0.9 ** state["step"])
        v = state["v"][key] / (1 - 0.999 ** state["step"])
        model.params[key] -= config.learning_rate * m / (np.sqrt(v) + 1e-8)
    return norm


def _config_dict(config):
    result = asdict(config)
    result["reserved_evaluation_seeds"] = list(result["reserved_evaluation_seeds"])
    return result


def save_checkpoint(path, model: PolicyValueNet, contract: Mapping, *, config: PPOConfig):
    digest = contract_digest(contract)
    if model.contract_digest not in (None, digest):
        raise ValueError("Model contract differs from checkpoint contract")
    metadata = {"format_version": 1, "algorithm": "masked_mlp_ppo", "scope": "deck_order_curriculum",
                "contract": dict(contract), "contract_digest": digest,
                "obs_dim": model.obs_dim, "action_dim": model.action_dim, "hidden_size": model.hidden_size,
                "config": _config_dict(config), "training_state": model.training_state,
                "optimizer_step": model.optimizer["step"] if model.optimizer else 0}
    arrays = {"metadata": np.array(canonical_json(metadata))}
    arrays.update({"parameter_" + k: v for k,v in model.params.items()})
    if model.optimizer:
        arrays.update({f"adam_{group}_{k}": v for group in ("m", "v") for k,v in model.optimizer[group].items()})
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".npz", delete=False) as stream:
        temp = Path(stream.name)
        try:
            np.savez_compressed(stream, **arrays)
        except BaseException:
            stream.close()
            temp.unlink(missing_ok=True)
            raise
    temp.replace(target)


def load_checkpoint(path, contract: Mapping) -> PolicyValueNet:
    with np.load(path, allow_pickle=False) as archive:
        meta = json.loads(str(archive["metadata"].item()))
        digest = contract_digest(contract)
        if meta.get("format_version") != 1 or meta.get("algorithm") != "masked_mlp_ppo":
            raise ValueError("Unsupported checkpoint format")
        if meta.get("contract_digest") != digest or contract_digest(meta["contract"]) != digest:
            raise ValueError("Checkpoint engine/observation/action contract mismatch")
        model = PolicyValueNet(meta["obs_dim"], meta["action_dim"], meta["hidden_size"])
        for key, initial in model.params.items():
            array = archive["parameter_" + key]
            if array.shape != initial.shape or not np.isfinite(array).all():
                raise ValueError("Malformed checkpoint parameter")
            model.params[key] = array.copy()
        step = meta["optimizer_step"]
        if step:
            model.optimizer = {"step": step, "m": {}, "v": {}}
            for group in ("m", "v"):
                for key, parameter in model.params.items():
                    array = archive[f"adam_{group}_{key}"]
                    if array.shape != parameter.shape or not np.isfinite(array).all():
                        raise ValueError("Malformed checkpoint optimizer")
                    model.optimizer[group][key] = array.copy()
        model.contract_digest = digest
        model.training_state = meta["training_state"]
        model.checkpoint_config = meta["config"]
        return model


def _episode(env, model, seed, rng, config, deterministic=False):
    observation, reset_info = env.reset(seed=seed)
    data = {key: [] for key in ("observations", "masks", "actions", "old_log_probs", "values", "rewards", "terminated")}
    total_reward = 0.0
    for step in range(config.max_episode_steps):
        legal = env.legal_actions()
        action, log_prob, value = model.act(observation, legal, rng=rng, deterministic=deterministic)
        data["observations"].append(list(observation))
        data["masks"].append(action_mask(legal, model.action_dim))
        data["actions"].append(action)
        data["old_log_probs"].append(log_prob)
        data["values"].append(value)
        observation, reward, terminated, truncated, info = env.step(action)
        if not np.isfinite(reward):
            raise ValueError("Environment returned nonfinite reward")
        total_reward += float(reward)
        data["rewards"].append(float(reward))
        data["terminated"].append(bool(terminated))
        if truncated:
            return None, {"seed": seed, "status": "truncated", "steps": step + 1,
                          "case_id": reset_info.get("case_id")}
        if terminated:
            if info.get("label_usable") is False:
                return None, {"seed": seed, "status": "unresolved_outcome", "steps": step + 1,
                              "case_id": reset_info.get("case_id")}
            adv, returns = compute_gae(data["rewards"], data["values"], data["terminated"],
                                       gamma=config.gamma, gae_lambda=config.gae_lambda)
            data["advantages"], data["returns"] = adv, returns
            return data, {"seed": seed, "status": "terminated", "reward": total_reward,
                          "steps": step + 1, "case_id": reset_info.get("case_id")}
    return None, {"seed": seed, "status": "collector_step_limit", "steps": config.max_episode_steps,
                  "case_id": reset_info.get("case_id")}


def train(env, config: PPOConfig | Mapping, contract: Mapping, checkpoint_path, *, resume=False,
          on_update: Callable[[dict], None] | None = None) -> dict:
    """Perform additional update rounds and save all continuation state atomically.

    ``updates`` counts collection rounds (a fully truncated round performs no
    optimization). Resuming requires unchanged hyperparameters except updates.
    """
    config = PPOConfig(**config) if isinstance(config, Mapping) else config
    config.validate()
    digest = contract_digest(contract)
    rng = np.random.default_rng(config.seed)
    if resume:
        model = load_checkpoint(checkpoint_path, contract)
        requested, saved = _config_dict(config), dict(model.checkpoint_config)
        requested.pop("updates"); saved.pop("updates")
        if canonical_json(requested) != canonical_json(saved):
            raise ValueError("Resume hyperparameters changed; only updates may differ")
        rng.bit_generator.state = model.training_state["rng_state"]
    else:
        observation, _ = env.reset(seed=config.training_seed_base)
        model = PolicyValueNet(len(observation), config.action_dim, config.hidden_size, config.seed)
        model.contract_digest = digest
        model.training_state = {"rounds": 0, "episodes_attempted": 0, "episodes_trained": 0,
                                "episodes_excluded": 0, "training_seeds": [], "history": []}
    start = time.perf_counter()
    state = model.training_state
    reserved = set(config.reserved_evaluation_seeds)
    # Validate the complete upcoming seed schedule before any update can happen.
    upcoming = range(config.training_seed_base + state["episodes_attempted"],
                     config.training_seed_base + state["episodes_attempted"] + config.updates * config.episodes_per_update)
    if any(seed in reserved for seed in upcoming):
        raise ValueError("Training schedule overlaps reserved evaluation seeds")
    for _ in range(config.updates):
        trajectories, outcomes = [], []
        for _ in range(config.episodes_per_update):
            seed = config.training_seed_base + state["episodes_attempted"]
            trajectory, outcome = _episode(env, model, seed, rng, config)
            state["episodes_attempted"] += 1
            state["training_seeds"].append(seed)
            outcomes.append(outcome)
            if trajectory is None:
                state["episodes_excluded"] += 1
            else:
                trajectories.append(trajectory)
                state["episodes_trained"] += 1
        stats = {"round": state["rounds"] + 1, "episodes": len(outcomes),
                 "eligible_episodes": len(trajectories), "excluded_episodes": len(outcomes) - len(trajectories),
                 "mean_reward": float(np.mean([x["reward"] for x in outcomes if x["status"] == "terminated"])) if trajectories else None,
                 "transition_count": 0}
        if trajectories:
            keys = ("observations", "masks", "actions", "old_log_probs", "advantages", "returns")
            batch = {k: np.concatenate([np.asarray(t[k]) for t in trajectories], axis=0) for k in keys}
            advantages = batch["advantages"]
            if len(advantages) > 1 and advantages.std() > 1e-8:
                batch["advantages"] = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
            diagnostics = []
            for _ in range(config.epochs):
                indices = rng.permutation(len(advantages))
                for offset in range(0, len(indices), config.minibatch_size):
                    selected = indices[offset:offset + config.minibatch_size]
                    _, gradients, metrics = model.loss_and_gradients({k:v[selected] for k,v in batch.items()}, config)
                    metrics["gradient_norm_before_clip"] = _adam_step(model, gradients, config)
                    diagnostics.append(metrics)
            stats["transition_count"] = len(advantages)
            stats.update({k: float(np.mean([d[k] for d in diagnostics])) for k in diagnostics[0]})
        state["rounds"] += 1
        state["history"].append(stats)
        state["rng_state"] = rng.bit_generator.state
        save_checkpoint(checkpoint_path, model, contract, config=config)
        if on_update:
            on_update(dict(stats))
    return {"algorithm": "masked_mlp_ppo", "scope": "deck_order_curriculum", "full_match_agent": False,
            "contract_digest": digest, "checkpoint": str(Path(checkpoint_path).resolve()),
            "checkpoint_sha256": hashlib.sha256(Path(checkpoint_path).read_bytes()).hexdigest(),
            "parameter_count": model.parameter_count, "obs_dim": model.obs_dim, "action_dim": model.action_dim,
            "rounds": state["rounds"], "episodes_attempted": state["episodes_attempted"],
            "episodes_trained": state["episodes_trained"], "episodes_excluded": state["episodes_excluded"],
            "training_seeds": list(state["training_seeds"]), "history": list(state["history"]),
            "elapsed_seconds": time.perf_counter() - start}


def evaluate(env, model: PolicyValueNet, seeds, *, contract: Mapping, deterministic=True,
             sampling_seed=0, max_episode_steps=64):
    seeds = list(seeds)
    if not seeds or any(type(s) is not int or s < 0 for s in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("Evaluation needs unique nonnegative integer seeds")
    digest = contract_digest(contract)
    if model.contract_digest != digest:
        raise ValueError("Evaluation model contract mismatch")
    if set(seeds) & set(model.training_state.get("training_seeds", [])):
        raise ValueError("Training/evaluation seed overlap")
    rng = np.random.default_rng(sampling_seed)
    config = PPOConfig(action_dim=model.action_dim, max_episode_steps=max_episode_steps)
    config.validate()
    outcomes = [_episode(env, model, seed, rng, config, deterministic)[1] for seed in seeds]
    completed = [o for o in outcomes if o["status"] == "terminated"]
    rewards = [o["reward"] for o in completed]
    return {"scope": "deck_order_curriculum", "contract_digest": digest,
            "policy": "greedy" if deterministic else "sampled", "sampling_seed": sampling_seed,
            "seeds": seeds, "episodes": len(seeds), "completed": len(completed),
            "excluded": len(seeds) - len(completed),
            "mean_reward": float(np.mean(rewards)) if rewards else None,
            "win_fraction": float(np.mean(np.asarray(rewards) > 0)) if rewards else None,
            "outcomes": outcomes,
            "limitation": "Seed separation alone does not separate source game/case families; split those externally."}
