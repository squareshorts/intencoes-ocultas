"""Experiment 1: what does rewarded third-party intervention do?

A. Ablation (homogeneous tables): intervention disabled vs reward 0-3,
   crossed with the population's intervention propensity.
B. Invasion analysis: one focal (mutant) player with intervention propensity x
   among residents with propensity y. Invasion fitness = n * P(focal wins), so
   neutral = 1. This gives a pairwise invasibility plot (PIP) per reward level.

Common random numbers: every condition uses the same game seeds.
Outputs: results/exp1_ablation.csv, results/exp1_invasion.csv
"""
import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from intencoes.sim import Params, RuleConfig, focal, homogeneous  # noqa: E402

OUT = ROOT / "results"


def summarize(df, n):
    first_wins = (df.winner == df.first_player).mean()
    return {
        "games": len(df),
        "turns_mean": df.turns.mean(),
        "draw_rate": df.winner.isna().mean(),
        "first_player_advantage": first_wins - 1 / n,
        "interventions_per_game": df.interventions.mean(),
        "intervention_success": df.interventions_stood.sum() / max(1, df.interventions.sum()),
        "bluffs_per_game": df.bluffs.mean(),
        "challenges_per_game": df.challenges.mean(),
        "challenge_accuracy": df.challenges_correct.sum() / max(1, df.challenges.sum()),
    }


def ablation(n_games, n_players):
    rows = []
    for reward in [None, 0, 1, 2, 3]:  # None = intervention disabled
        cfg = RuleConfig(n_players=n_players, intervention_enabled=reward is not None,
                         intervention_reward=reward or 0)
        for prop in [0.0, 0.25, 0.5, 0.75, 1.0]:
            if reward is None and prop > 0:
                continue
            df = homogeneous(replace(Params(), intervene=prop), cfg, n_games)
            rows.append({"reward": "off" if reward is None else reward, "intervene": prop,
                         **summarize(df, n_players)})
            print(rows[-1], flush=True)
    return pd.DataFrame(rows)


def invasion(n_games, n_players, rewards, grid):
    rows = []
    for reward in rewards:
        cfg = RuleConfig(n_players=n_players, intervention_reward=reward)
        for y in grid:
            for x in grid:
                df = focal(replace(Params(), intervene=x), replace(Params(), intervene=y), cfg, n_games)
                p = (df.winner == 0).mean()
                se = np.sqrt(p * (1 - p) / len(df))
                rows.append({"reward": reward, "resident": y, "mutant": x, "p_win": p,
                             "fitness": n_players * p, "fitness_se": n_players * se,
                             "mutant_interventions": df.intervened_by.map(lambda v: v[0]).mean()})
            print(f"reward={reward} resident={y:.1f} done", flush=True)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=20000)
    ap.add_argument("--players", type=int, default=4)
    ap.add_argument("--part", choices=["ablation", "invasion", "all"], default="all")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    t = time.time()
    if args.part in ("ablation", "all"):
        ablation(args.games, args.players).to_csv(OUT / "exp1_ablation.csv", index=False)
    if args.part in ("invasion", "all"):
        grid = np.round(np.linspace(0, 1, 6), 2)
        invasion(args.games, args.players, [0, 1, 2], grid).to_csv(OUT / "exp1_invasion.csv", index=False)
    print(f"done in {time.time() - t:.0f}s")
