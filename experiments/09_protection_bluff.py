"""Trait-isolated protection-bluff invasion screening, not Experiments 2--4.

For a fixed resident defence/challenge policy, seat 0 varies ONE parameter:
block_bluff or intervene_bluff. Common seeds pair baseline and mutant games;
95% intervals bootstrap the seed-paired *focal win difference*.

Usage: PYTHONPATH=src python experiments/09_protection_bluff.py --games 1200
"""
from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from intencoes.agents import HeuristicAgent, Params
from intencoes.engine import Game
from intencoes.rules import RuleConfig


def play(params, seed):
    agents = [HeuristicAgent(p, seed=seed * 31 + j) for j, p in enumerate(params)]
    g = Game(agents, RuleConfig(n_players=4), seed=seed, first_player=seed % 4)
    winner = g.play()
    offer = [e for e in g.log if e['event'] == 'block_offer' and e['player'] == 0]
    block = [e for e in g.log if e['event'] == 'block' and e['blocker'] == 0]
    return (int(winner == 0), len(offer), sum(e['mode'] == 'intervention' for e in offer),
            sum(not e['claim_true'] for e in block),
            sum(e['interventor'] and not e['claim_true'] for e in block))


def compare(trait, theta, games, seed0, options):
    other = {k:v for k,v in options.items() if k not in ('train_stages', 'train_brier')}
    base = Params(bluff=0.02, intervene=0.7, challenge_threshold=theta,
                  block_bluff=0.05, intervene_bluff=0.0,
                  block_prediction='opponent', **other)
    changed = replace(base, **{trait: 0.80})
    w0 = np.empty(games, dtype=float)
    w1 = np.empty(games, dtype=float)
    sums = np.zeros((2,4), dtype=float)
    for i in range(games):
        seed = seed0 + i
        ctrl = play([base] * 4, seed)
        mut = play([changed] + [base] * 3, seed)
        w0[i], w1[i] = ctrl[0], mut[0]
        sums[0] += ctrl[1:]
        sums[1] += mut[1:]
    rng = np.random.default_rng(4802)
    paired = w1 - w0
    means = paired[rng.integers(0, games, (1500, games))].mean(axis=1)
    lo, hi = np.quantile(means, [.025, .975])
    return {
        'trait':trait, 'theta':theta, 'games_per_arm':games,
        'focal_baseline_win_prob':float(w0.mean()),
        'focal_mutant_win_prob':float(w1.mean()),
        'focal_win_diff':float(paired.mean()),
        'paired_diff_ci_low':float(lo), 'paired_diff_ci_high':float(hi),
        'baseline_offers_per_game':float(sums[0,0]/games),
        'mutant_offers_per_game':float(sums[1,0]/games),
        'baseline_intervention_offers_per_game':float(sums[0,1]/games),
        'mutant_intervention_offers_per_game':float(sums[1,1]/games),
        'baseline_fake_block_claims_per_game':float(sums[0,2]/games),
        'mutant_fake_block_claims_per_game':float(sums[1,2]/games),
        'baseline_fake_interventions_per_game':float(sums[0,3]/games),
        'mutant_fake_interventions_per_game':float(sums[1,3]/games),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--games', type=int, default=1200)
    ap.add_argument('--prior', default='results/opponent_beliefs/selection.csv')
    args = ap.parse_args()
    import pandas as pd
    fit = pd.read_csv(ROOT / args.prior).iloc[0]
    options = {k:float(fit[k]) for k in ('opponent_intervene','opponent_intervene_bluff',
                                       'opponent_block_bluff','block_prior_strength',
                                       'opponent_pool_strength')}
    rows = []
    for i, trait in enumerate(('block_bluff', 'intervene_bluff')):
        for j, theta in enumerate((0., 0.3, 0.6)):
            row = compare(trait, theta, args.games, 500_000 + i*10000 + j*2000, options)
            rows.append(row)
            print('ISOLATED', trait, 'theta', theta, 'delta', round(row['focal_win_diff'],3),
                  'CI',round(row['paired_diff_ci_low'],3),round(row['paired_diff_ci_high'],3),
                  'fake block claims/game',round(row['mutant_fake_block_claims_per_game'],3),flush=True)
    output = ROOT / 'results' / 'opponent_beliefs' / 'protection_bluff.csv'
    output.parent.mkdir(exist_ok=True, parents=True)
    with output.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


if __name__ == '__main__':
    main()
