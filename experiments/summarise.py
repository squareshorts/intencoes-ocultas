"""Compact summaries of experiment outputs (at most ~30 lines per experiment).

Usage: python experiments/summarise.py [exp2|exp3|exp4 ...]   (default: all)
Reads results/ (or results/ablation_random_bluff with --ablation).
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", None)


def exp2(d):
    g = pd.read_csv(d / "exp2_gradients.csv")
    g["gradient [95% CI]"] = g.apply(lambda r: f"{r.gradient:+.3f} [{r.ci_low:+.3f}, {r.ci_high:+.3f}]", axis=1)
    t = g.pivot_table(index="trait", columns=["reward", "challenge_cost"], values="gradient [95% CI]", aggfunc="first")
    print("Exp 2 — selection gradient d(rel. fitness)/d(trait); columns = (reward, challenge cost)")
    print(t.to_string())


def exp3(d):
    t = pd.read_csv(d / "exp3_traits.csv")
    b = pd.read_csv(d / "exp3_behaviour.csv")
    last = t[t.generation == t.generation.max()]
    cols = [c for c in last.columns if c.endswith("_mean")]
    m = last.groupby(["reward", "challenge_cost"])[cols]
    out = m.mean().round(2).astype(str) + "±" + m.std().round(2).astype(str)
    out.columns = [c.replace("_mean", "") for c in out.columns]
    reps = last.groupby(["reward", "challenge_cost"]).size().iloc[0]
    print(f"Exp 3 — final trait means ± SD over {reps} reps (generation {t.generation.max()})")
    print(out.to_string())
    lb = b[b.generation == b.generation.max()]
    keep = ["interventions_per_game", "faked_protection_share", "challenges_per_game", "turns_mean"]
    print(lb.groupby(["reward", "challenge_cost"])[keep].mean().round(2).to_string())


def exp4(d):
    a = pd.read_csv(d / "exp4_alpharank.csv")
    s = a[a.alpha == 50]
    top = s.sort_values("mass", ascending=False).groupby(["n_players", "reward", "challenge_cost"]).head(2)
    top = top.assign(v=top.archetype + " " + top.mass.round(2).astype(str)
                     + " [" + top.ci_low.round(2).astype(str) + "," + top.ci_high.round(2).astype(str) + "]")
    print("Exp 4 — alpha-Rank (alpha=50), top-2 archetypes [95% bootstrap CI]")
    print(top.groupby(["n_players", "reward", "challenge_cost"]).v.apply(" | ".join).to_string())


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    d = ROOT / "results" / ("ablation_random_bluff" if "--ablation" in sys.argv else "")
    for name in args or ["exp2", "exp3", "exp4"]:
        try:
            globals()[name](d)
        except FileNotFoundError as e:
            print(f"{name}: missing ({Path(e.filename).name})")
        print()
