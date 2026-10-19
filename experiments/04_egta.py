"""Experiment 4: EGTA payoff tables, alpha-Rank and replicator dynamics.

Stage `simulate`: for every table size n in {3, 4, 5}, reward r in {0, 1, 2} and
challenge cost c in {0, 1}, play each multiset of n archetypes `--games` times
(seats shuffled). Saves win counts to results/raw/exp4_counts.npz.

Stage `analyze`:
  results/exp4_alpharank.csv   stationary mass per archetype (alpha grid; bootstrap CI at alpha=50)
  results/exp4_replicator.csv  replicator rest points with basin shares
  results/exp4_payoffs.csv     monomorphic payoffs and pairwise invasion payoffs (for figures)
"""
import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from intencoes.egta import NAMES, PayoffTable, alpha_rank, profiles, rest_points, simulate_profile  # noqa: E402
from intencoes.rules import RuleConfig  # noqa: E402

OUT = ROOT / "results"
RAW = OUT / "raw" / "exp4_counts.npz"
NS, REWARDS, COSTS = [3, 4, 5], [0, 1, 2], [0, 1]
ALPHAS = [1, 10, 50, 100]
M = 50


def key(n, r, c, prof):
    return f"{n}|{r}|{c}|{','.join(map(str, prof))}"


def task(args):
    n, r, c, prof, games, seed = args
    wins, _ = simulate_profile(prof, RuleConfig(n_players=n, intervention_reward=r, challenge_cost=c), games, seed)
    return key(n, r, c, prof), wins


def simulate(games):
    k = len(NAMES)
    tasks = [(n, r, c, prof, games, hash((n, r, c, prof)) & 0xFFFFFFFF)
             for n in NS for r in REWARDS for c in COSTS for prof in profiles(k, n)]
    t, raw = time.time(), {}
    with ProcessPoolExecutor() as ex:
        for i, (kk, w) in enumerate(ex.map(task, tasks, chunksize=4)):
            raw[kk] = w
            if (i + 1) % 500 == 0:
                print(f"{i + 1}/{len(tasks)} profiles, {time.time() - t:.0f}s", flush=True)
    RAW.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(RAW, games=games, **raw)


def load_tables():
    data = np.load(RAW)
    games = int(data["games"])
    k = len(NAMES)
    tables = {}
    for n in NS:
        for r in REWARDS:
            for c in COSTS:
                counts = {prof: data[key(n, r, c, prof)] for prof in profiles(k, n)}
                tables[(n, r, c)] = PayoffTable(k, n, counts, games)
    return tables


def analyze_one(args):
    (n, r, c), table, boot = args
    rng = np.random.default_rng(1000 * n + 10 * r + c)
    meta = {"n_players": n, "reward": r, "challenge_cost": c}
    ar_rows, rp_rows, pay_rows = [], [], []
    for alpha in ALPHAS:
        pi, _ = alpha_rank(table, alpha=alpha, M=M)
        ci = None
        if alpha == 50 and boot:
            bs = np.array([alpha_rank(table.resample(rng), alpha=alpha, M=M)[0] for _ in range(boot)])
            ci = np.percentile(bs, [2.5, 97.5], axis=0)
        for i, name in enumerate(NAMES):
            ar_rows.append({**meta, "alpha": alpha, "archetype": name, "mass": pi[i],
                            "ci_low": ci[0, i] if ci is not None else np.nan,
                            "ci_high": ci[1, i] if ci is not None else np.nan})
    for j, rp in enumerate(rest_points(table, starts=60, seed=1)):
        rp_rows.append({**meta, "rest_point": j, "basin": rp["basin"],
                        **{name: rp["x"][i] for i, name in enumerate(NAMES)}})
    for i, a in enumerate(NAMES):
        for jj, b in enumerate(NAMES):
            # payoff of one `a` among n-1 `b`s, relative to fair share 1/n
            pay_rows.append({**meta, "focal": a, "resident": b, "rel_payoff": n * table.u(i, (jj,) * (n - 1))})
    return ar_rows, rp_rows, pay_rows


def analyze(boot):
    tables = load_tables()
    ar, rp, pay = [], [], []
    with ProcessPoolExecutor() as ex:
        for a_, r_, p_ in ex.map(analyze_one, [(k, t, boot) for k, t in tables.items()]):
            ar += a_
            rp += r_
            pay += p_
            top = max(a_[-len(NAMES):], key=lambda row: row["mass"])
            print({k: a_[0][k] for k in ("n_players", "reward", "challenge_cost")},
                  "alpha=100 top:", top["archetype"], round(top["mass"], 3), flush=True)
    pd.DataFrame(ar).to_csv(OUT / "exp4_alpharank.csv", index=False)
    pd.DataFrame(rp).to_csv(OUT / "exp4_replicator.csv", index=False)
    pd.DataFrame(pay).to_csv(OUT / "exp4_payoffs.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["simulate", "analyze", "all"], default="all")
    ap.add_argument("--games", type=int, default=3000)
    ap.add_argument("--boot", type=int, default=200)
    args = ap.parse_args()
    t = time.time()
    if args.stage in ("simulate", "all"):
        simulate(args.games)
    if args.stage in ("analyze", "all"):
        analyze(args.boot)
    print(f"done in {time.time() - t:.0f}s")
