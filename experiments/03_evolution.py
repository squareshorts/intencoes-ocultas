"""Experiment 3: co-evolution of protection, faked protection and scepticism.

Conditions: intervention reward r in {0, 1, 2, 3} x challenge cost c in {0, 1},
`--reps` independent replicates each, uniform random initial traits.
Outputs: results/exp3_traits.csv, results/exp3_behaviour.csv
"""
import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from intencoes.evolution import EvoConfig, evolve  # noqa: E402
from intencoes.rules import RuleConfig  # noqa: E402

OUT = ROOT / "results"


def job(args):
    r, c, rep, evo = args
    hist, beh = evolve(RuleConfig(intervention_reward=r, challenge_cost=c), evo, seed=1000 * r + 100 * c + rep)
    meta = {"reward": r, "challenge_cost": c, "rep": rep}
    return [{**meta, **h} for h in hist], [{**meta, **b} for b in beh]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--generations", type=int, default=600)
    args = ap.parse_args()
    evo = replace(EvoConfig(), generations=args.generations)
    tasks = [(r, c, rep, evo) for r in [0, 1, 2, 3] for c in [0, 1] for rep in range(args.reps)]
    t = time.time()
    traits, beh = [], []
    with ProcessPoolExecutor() as ex:
        for h, b in ex.map(job, tasks, chunksize=1):
            traits += h
            beh += b
            print(f"{h[0]['reward']=} {h[0]['challenge_cost']=} rep {h[0]['rep']} done, {time.time() - t:.0f}s", flush=True)
    OUT.mkdir(exist_ok=True)
    pd.DataFrame(traits).to_csv(OUT / "exp3_traits.csv", index=False)
    pd.DataFrame(beh).to_csv(OUT / "exp3_behaviour.csv", index=False)
    print(f"done in {time.time() - t:.0f}s")
