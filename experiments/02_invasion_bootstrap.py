"""Experiment 2: invasion analysis with paired-bootstrap uncertainty.

For each trait (intervene, intervene_bluff, challenge_threshold), reward
r in {0, 1, 2} and challenge cost c in {0, 1}, a focal player (seat 0)
with trait value x plays three residents with value y. Other traits stay
at their Params defaults. All cells of one (trait, r, c) block share the
same seeds; see intencoes.stats.

Outputs:
  results/raw/exp2_winners.npz  per-game winners (regenerable, gitignored)
  results/exp2_invasion.csv     relative invasion fitness + 95% CI per cell
  results/exp2_gradients.csv    selection gradient + 95% CI per block
"""
import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from intencoes.agents import Params  # noqa: E402
from intencoes.rules import RuleConfig  # noqa: E402
from intencoes.sim import winners  # noqa: E402
from intencoes.stats import invasion_table  # noqa: E402

OUT = ROOT / "results"
GRIDS = {
    "bluff": np.round(np.linspace(0, 1, 6), 2),
    "intervene": np.round(np.linspace(0, 1, 6), 2),
    "intervene_bluff": np.round(np.linspace(0, 1, 6), 2),
    "challenge_threshold": np.round(np.linspace(0, 0.6, 6), 2),
}
REWARDS = [0, 1, 2]
COSTS = [0, 1]


def cell(args):
    trait, r, c, x, y, n_games, n_players = args
    cfg = RuleConfig(n_players=n_players, intervention_reward=r, challenge_cost=c)
    mut, res = replace(Params(), **{trait: x}), replace(Params(), **{trait: y})
    return args[:5], winners([mut] + [res] * (n_players - 1), cfg, np.arange(n_games))


def key(trait, r, c, x, y):
    return f"{trait}|{r}|{c}|{x}|{y}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=40000)
    ap.add_argument("--players", type=int, default=4)
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--traits", nargs="+", default=list(GRIDS), help="rerun only these; others kept from existing CSVs")
    args = ap.parse_args()
    GRIDS = {k: v for k, v in GRIDS.items() if k in args.traits}
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    t = time.time()

    tasks = [(trait, r, c, float(x), float(y), args.games, args.players)
             for trait, grid in GRIDS.items() for r in REWARDS for c in COSTS for y in grid for x in grid]
    raw = {}
    with ProcessPoolExecutor() as ex:
        for i, (k, w) in enumerate(ex.map(cell, tasks, chunksize=1)):
            raw[key(*k)] = w
            if (i + 1) % 36 == 0:
                print(f"{i + 1}/{len(tasks)} cells, {time.time() - t:.0f}s", flush=True)
    raw_path = OUT / "raw" / "exp2_winners.npz"
    if raw_path.exists():  # keep cells of traits not rerun
        old = dict(np.load(raw_path))
        raw = {**{k: v for k, v in old.items() if k.split("|")[0] not in GRIDS}, **raw}
    np.savez_compressed(raw_path, **raw)

    tables, grads = [], []
    for trait, grid in GRIDS.items():
        for r in REWARDS:
            for c in COSTS:
                block = {(float(x), float(y)): raw[key(trait, r, c, float(x), float(y))] for y in grid for x in grid}
                table, grad = invasion_table(block, args.players, n_boot=args.boot)
                meta = {"trait": trait, "reward": r, "challenge_cost": c}
                tables.append(table.assign(**meta))
                grads.append({**meta, **grad})
                print(meta, {k: round(v, 4) if isinstance(v, float) else v for k, v in grad.items()}, flush=True)
    for name, new in [("exp2_invasion.csv", pd.concat(tables)), ("exp2_gradients.csv", pd.DataFrame(grads))]:
        path = OUT / name
        if path.exists():
            old = pd.read_csv(path)
            new = pd.concat([old[~old.trait.isin(list(GRIDS))], new])
        new.to_csv(path, index=False)
    print(f"done in {time.time() - t:.0f}s")
