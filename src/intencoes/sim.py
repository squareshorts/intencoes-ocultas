"""Batch simulation: run many games and reduce each to one row of outcome metrics."""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

import numpy as np
import pandas as pd

from .agents import HeuristicAgent, Params
from .engine import Game
from .rules import RuleConfig


def game_record(g: Game) -> dict:
    rec = {"winner": g.winner, "turns": g.turn, "first_player": g.first_player}
    n = g.config.n_players
    for k in ("actions", "bluffs", "challenges", "challenges_correct", "blocks", "block_bluffs",
              "interventions", "interventions_stood", "intervention_bluffs", "intervention_reward"):
        rec[k] = 0
    rec["intervened_by"] = [0] * n
    for e in g.log:
        if e["event"] == "action":
            rec["actions"] += 1
            rec["bluffs"] += e["claim_true"] is False
        elif e["event"] == "challenge":
            rec["challenges"] += 1
            rec["challenges_correct"] += not e["claim_true"]
        elif e["event"] == "block":
            if e["interventor"]:
                rec["interventions"] += 1
                rec["interventions_stood"] += bool(e.get("stands"))
                rec["intervention_bluffs"] += not e["claim_true"]
                rec["intervention_reward"] += e.get("reward", 0)
                rec["intervened_by"][e["blocker"]] += 1
            else:
                rec["blocks"] += 1
                rec["block_bluffs"] += not e["claim_true"]
    return rec


def _run_chunk(args):
    params_by_seat, config, seeds = args
    rows = []
    n = config.n_players
    for s in seeds:
        first = s % n  # rotate who starts
        agents = [HeuristicAgent(params_by_seat[k], seed=s * 31 + k) for k in range(n)]
        g = Game(agents, config, seed=s, first_player=first)
        g.play()
        rows.append({"seed": s, **game_record(g)})
    return rows


def winners(params_by_seat, config: RuleConfig, seeds) -> np.ndarray:
    """Single-process: winning seat per seed (-1 = draw). First player rotates with the seed."""
    out = np.empty(len(seeds), dtype=np.int8)
    n = config.n_players
    for i, s in enumerate(seeds):
        s = int(s)
        agents = [HeuristicAgent(params_by_seat[k], seed=s * 31 + k) for k in range(n)]
        w = Game(agents, config, seed=s, first_player=s % n).play()
        out[i] = -1 if w is None else w
    return out


def run(params_by_seat, config: RuleConfig, n_games: int, seed0: int = 0, workers: int | None = None) -> pd.DataFrame:
    """Simulate n_games with fixed seat strategies; returns one row per game."""
    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    seeds = np.arange(seed0, seed0 + n_games)
    chunks = [(params_by_seat, config, list(map(int, c))) for c in np.array_split(seeds, workers * 4) if len(c)]
    rows = []
    with ProcessPoolExecutor(workers) as ex:
        for part in ex.map(_run_chunk, chunks):
            rows.extend(part)
    return pd.DataFrame(rows)


def homogeneous(params: Params, config: RuleConfig, n_games: int, **kw) -> pd.DataFrame:
    return run([params] * config.n_players, config, n_games, **kw)


def focal(focal_params: Params, resident_params: Params, config: RuleConfig, n_games: int, **kw) -> pd.DataFrame:
    """Seat 0 plays the focal (mutant) strategy, others the resident; first player rotates."""
    return run([focal_params] + [resident_params] * (config.n_players - 1), config, n_games, **kw)


__all__ = ["run", "homogeneous", "focal", "game_record", "Params", "RuleConfig", "replace"]
