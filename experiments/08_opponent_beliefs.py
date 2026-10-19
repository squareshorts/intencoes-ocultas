"""Matched-event public-opponent calibration, training/held-out splits.

No hidden hands or strategy labels are given to the *acting agents*. The
policy-oracle comparator sees simulator strategy parameters ONLY at evaluation
time. All three methods predict the SAME already-selected blocking stages.
This establishes conditional event prediction, not counterfactual policy value.

Usage: PYTHONPATH=src python experiments/08_opponent_beliefs.py --train 500 --games 650
Outputs: results/opponent_beliefs/{selection.csv,holdout.csv,behaviour.csv}
         results/raw/opponent_beliefs_stages.csv (untracked regenerable event data)
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from intencoes.agents import HeuristicAgent, Params
from intencoes.egta import ARCHETYPES
from intencoes.engine import Game
from intencoes.rules import ActionType, RuleConfig
from intencoes.sim import game_record

ATTACKS = (ActionType.STEAL, ActionType.ASSASSINATE)
MIX = ("Default", "HonestProtector", "Bluffer", "Pushover", "BlufferFakeProtector")
SHIFT = ("FakeProtector", "HonestTrusting", "ScepticProtector", "HonestSceptic", "BlufferFakeProtector")


@dataclass
class Stage:
    gid: int
    action: str
    target: int
    view: object
    self_policy: Params
    policies: dict[int, Params]  # evaluation-only: never passed to agent/engine view
    stood: int


class DiagnosticGame(Game):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.snapshots = []

    def _block_phase(self, actor, action, target):
        if action not in ATTACKS:
            return super()._block_phase(actor, action, target)
        view = self.view(actor)  # before an offer or any outcome is known
        policies = {j: a.p for j, a in enumerate(self.agents)}
        stood = super()._block_phase(actor, action, target)
        self.snapshots.append(Stage(-1, action.value, target, view, self.agents[actor].p,
                                    policies, int(stood)))
        return stood


def seat_params(n, seed, kind, belief):
    if kind == "homogeneous":
        kinds = ["Default"] * n
    else:
        group = MIX if kind == "mixed" else SHIFT
        kinds = [group[(seed + k) % len(group)] for k in range(n)]
        random.Random(seed * 1009 + 17).shuffle(kinds)
    return [replace(ARCHETYPES[name], block_prediction=belief) for name in kinds]


def generate(n_games, n, kind, first_seed, belief="empirical", keep_games=False):
    data, records = [], []
    cfg = RuleConfig(n_players=n)
    for i in range(n_games):
        seed = first_seed + i
        strategies = seat_params(n, seed, kind, belief)
        agents = [HeuristicAgent(strategies[j], seed=seed * 31 + j) for j in range(n)]
        g = DiagnosticGame(agents, cfg, seed=seed, first_player=seed % n)
        g.play()
        for snap in g.snapshots:
            snap.gid = i
        data.extend(g.snapshots)
        if keep_games:
            rec = game_record(g)
            rec["game_id"] = i
            records.append(rec)
    return data, records


def forecast(stage, method, candidate=None):
    # Pure deterministic predictors on a frozen pre-offer view. No RNG called.
    if method == "oracle_policy":
        estimator = HeuristicAgent(stage.self_policy)
        return estimator.oracle_policy_block_probability(stage.view,
                                                         ActionType(stage.action),
                                                         _target(stage), stage.policies)
    kw = {"block_prediction": method}
    if candidate is not None:
        kw.update({k: v for k, v in candidate.items() if k not in ("train_stages", "train_brier")})
    estimator = HeuristicAgent(replace(stage.self_policy, **kw))
    return estimator.predicted_block_probability(stage.view,
                                                ActionType(stage.action), _target(stage))


def _target(stage):
    # Target is held separately by the diagnostic (not exposed in View).
    return stage.target


def summarize(rows, group, n, seed_base, games, rng_seed=91, boot=500):
    """Paired stage-level Brier, clustered by game (not by stage)."""
    ys = np.array([r["stood"] for r in rows], dtype=float)
    if not len(rows):
        return []
    gids = np.array([r["game_id"] for r in rows], dtype=int)
    old = np.array([r["empirical"] for r in rows])
    pooled = np.array([r["opponent_pool"] for r in rows])
    total = games
    counts = np.bincount(gids, minlength=total)
    out = []
    rng = np.random.default_rng(rng_seed)
    samples = rng.integers(0, total, size=(boot, total))
    sampled_counts = counts[samples].sum(axis=1)
    sampled_counts = np.maximum(1, sampled_counts)
    for name in ("empirical", "opponent_prior", "opponent_pool", "opponent", "oracle_policy"):
        p = np.array([r[name] for r in rows], dtype=float)
        error = (p - ys) ** 2
        diff = error - (old - ys) ** 2
        diff_pool = error - (pooled - ys) ** 2
        by_game = np.bincount(gids, weights=diff, minlength=total)
        bootdiff = by_game[samples].sum(axis=1) / sampled_counts
        qlo, qhi = np.quantile(bootdiff, [0.025, 0.975])
        by_game_pool = np.bincount(gids, weights=diff_pool, minlength=total)
        bootdiff_pool = by_game_pool[samples].sum(axis=1) / sampled_counts
        pool_lo, pool_hi = np.quantile(bootdiff_pool, [.025, .975])
        out.append({
            "condition": group, "n_players": n, "first_seed": seed_base,
            "games": total, "stages": len(rows), "model": name,
            "predicted": float(p.mean()), "observed": float(ys.mean()),
            "gap": float(p.mean() - ys.mean()),
            "brier": float(error.mean()),
            "brier_delta_vs_empirical": float(diff.mean()),
            "brier_delta_ci_low": float(qlo), "brier_delta_ci_high": float(qhi),
            "brier_delta_vs_pool": float(diff_pool.mean()),
            "pool_delta_ci_low": float(pool_lo), "pool_delta_ci_high": float(pool_hi),
        })
    return out


def tune(stages):
    """Tiny prespecified grid on development data; no test-stage access."""
    scores = []
    candidates = [dict(opponent_intervene=i, opponent_intervene_bluff=b,
                       opponent_block_bluff=t, block_prior_strength=w,
                       opponent_pool_strength=2.0)
                  for i in (0.25, 0.5, 0.75)
                  for b in (0.0, 0.15)
                  for t in (0.1, 0.4)
                  for w in (1.0, 4.0)]
    for options in candidates:
        preds = [forecast(s, "opponent", options) for s in stages]
        ys = np.array([s.stood for s in stages])
        score = float(np.mean((np.array(preds) - ys) ** 2)) if len(ys) else float("inf")
        scores.append({**options, "train_stages": len(stages), "train_brier": score})
    scores.sort(key=lambda x: x["train_brier"])
    return scores[0], scores


def write_csv(path, rows):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def assess(stages, best, label, n, seed_base, games, boot):
    rows = []
    for s in stages:
        rows.append({"game_id": s.gid, "condition": label, "n_players": n,
                     "seed": seed_base + s.gid, "action": s.action,
                     "stood": s.stood,
                     "empirical": forecast(s, "empirical"),
                     "opponent_prior": forecast(s, "opponent_prior", best),
                     "opponent_pool": forecast(s, "opponent_pool", best),
                     "opponent": forecast(s, "opponent", best),
                     "oracle_policy": forecast(s, "oracle_policy")})
    return rows, summarize(rows, label, n, seed_base, games, boot=boot)


def run(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=int, default=450)
    ap.add_argument("--games", type=int, default=650)
    ap.add_argument("--policy-games", type=int, default=350)
    ap.add_argument("--boot", type=int, default=500)
    args = ap.parse_args(argv)
    out = ROOT / "results" / "opponent_beliefs"
    dev, _ = generate(args.train, 4, "mixed", 200_000)
    best, score_table = tune(dev)
    write_csv(out / "selection.csv", score_table)
    print("Development:", len(dev), "stages; best public prior", best, flush=True)
    allrows, summary = [], []
    for n in (3, 4, 5):
        for condition in ("homogeneous", "mixed", "shifted"):
            seed_base = 300_000 + n * 10_000 + {"homogeneous":0,"mixed":2000,"shifted":4000}[condition]
            stages, _ = generate(args.games, n, condition, seed_base)
            rows, scores = assess(stages, best, condition, n, seed_base, args.games, args.boot)
            allrows.extend(rows)
            summary.extend(scores)
            old, prior, pool, new, oracle = scores
            print("TEST", n, condition, "stages", len(rows),
                  "gap(old/prior/pool/new/oracle)", *(round(x['gap'],3) for x in scores),
                  "Brier(old/prior/pool/new/oracle)", *(round(x['brier'],3) for x in scores),
                  "Delta CI", (round(new['brier_delta_ci_low'],4),round(new['brier_delta_ci_high'],4)),
                  flush=True)
    write_csv(out / "holdout.csv", summary)
    write_csv(ROOT / "results" / "raw" / "opponent_beliefs_stages.csv", allrows)
    behaviour = []
    for condition in ("mixed", "shifted"):
        for method in ("empirical", "opponent"):
            # Selection coefficients are the frozen development choices.
            # The unmodified opponent model is used only for estimates; for
            # endogenous games the calibrated parameters are injected below.
            n = 4
            seed_base = 400_000 + (2000 if condition == "shifted" else 0)
            cfg = RuleConfig(n_players=n)
            aggregate = defaultdict(float)
            for i in range(args.policy_games):
                seed = seed_base + i
                params = seat_params(n, seed, condition, method)
                if method == "opponent":
                    params = [replace(p, **{k:v for k,v in best.items()
                                             if k not in ('train_stages','train_brier')})
                              for p in params]
                agents = [HeuristicAgent(p,seed=seed*31+j) for j,p in enumerate(params)]
                g = Game(agents,cfg,seed=seed,first_player=seed%n)
                g.play()
                rec = game_record(g)
                for key in ("intervention_offers", "interventions", "interventions_stood",
                            "target_block_offers", "target_block_stands", "turns"):
                    aggregate[key] += rec[key]
                for stage in g.log:
                    if stage['event'] != 'block_stage' or stage['action'] not in (a.value for a in ATTACKS):
                        continue
                    predicted = stage.get('p_blocked_pred')
                    if predicted is None:
                        continue
                    aggregate['stage_count'] += 1
                    aggregate['stage_pred_sum'] += predicted
                    aggregate['stage_observed_sum'] += stage['stood']
                    aggregate['stage_brier_sum'] += (predicted - int(stage['stood'])) ** 2
                aggregate["attack_declarations"] += sum(e["event"]=="action" and e["action"] in
                                                        (ActionType.STEAL.value,ActionType.ASSASSINATE.value)
                                                        for e in g.log)
            stages = max(1, aggregate['stage_count'])
            behaviour.append({"condition":condition,"belief":method,"games":args.policy_games,
                              **{k:v/args.policy_games for k,v in aggregate.items()
                                 if k not in ('stage_pred_sum','stage_observed_sum','stage_brier_sum')},
                              "stage_predicted":aggregate['stage_pred_sum']/stages,
                              "stage_observed":aggregate['stage_observed_sum']/stages,
                              "stage_brier":aggregate['stage_brier_sum']/stages})
            print("POLICY",condition,method,dict(behaviour[-1]),flush=True)
    write_csv(out / "behaviour.csv", behaviour)
    return best, summary


if __name__ == "__main__":
    run()
