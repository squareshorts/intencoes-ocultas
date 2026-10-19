"""Shared diagnostics for the action-specific public protection forecast.

Research-only evaluator: it never passes simulated card truth, oracle policies,
future responses, or held-out coefficients to an acting agent. Snapshots are
captured immediately before the first blocking offer.
"""
from __future__ import annotations

import importlib.util
import random
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from intencoes.agents import HeuristicAgent
from intencoes.rules import ActionType, RuleConfig
from intencoes.sim import game_record

spec = importlib.util.spec_from_file_location('intencoes_policy_reference', ROOT/'experiments'/'10_endogenous_opportunity.py')
pg = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pg
spec.loader.exec_module(pg)

ACTIONS = (ActionType.STEAL, ActionType.ASSASSINATE)
MODELS = ('empirical', 'opponent_pool', 'opponent', 'opponent_challenge', 'opponent_action')


def fit_group(stage):
    a = 0 if stage.action == ActionType.STEAL else 2
    return a + int(stage.view.hidden_counts[stage.target] == 1)


def stages_for_games(n, population, policy, offsets, first_seed, count, size_offsets=(0.,)*6):
    """Independent full games with normal endogenous action choice and no forced moves."""
    rows, stages = [], []
    for gid in range(count):
        seed = first_seed + gid
        strategies = [replace(p, action_block_offsets=tuple(offsets),
                              size_block_offsets=tuple(size_offsets))
                      for p in pg.seat_params(n, seed, population, policy)]
        agents = [pg.EncouragedAgent(strategies[j], seed=seed*31+j,
                                     opportunity_dose=0,
                                     encouragement_seed=seed*10007 + 89*j + 100003)
                  for j in range(n)]
        g = pg.InstrumentedGame(agents, RuleConfig(n_players=n, intervention_reward=1),
                                seed=seed, first_player=seed % n)
        g.play()
        rec = game_record(g)
        rows.append({'game_id': gid, 'attacks': sum(e['event']=='action' and
                     e['action'] in (ActionType.STEAL.value, ActionType.ASSASSINATE.value)
                     for e in g.log), 'block_stages': len(g.snapshots),
                     'intervention_offers': rec['intervention_offers'],
                     'intervention_claims': rec['interventions'],
                     'intervention_stands': rec['interventions_stood'],
                     'winner': g.winner if g.winner is not None else -1})
        for stage in g.snapshots:
            # Stage is research only. All prediction inputs are View and Params.
            stages.append((gid, stage))
    return rows, stages


def predict(stage, model, offsets, size_offsets=(0.,)*6):
    params = replace(stage.actor_params, block_prediction=model,
                     action_block_offsets=tuple(offsets),
                     size_block_offsets=tuple(size_offsets))
    return float(HeuristicAgent(params).predicted_block_probability(
        stage.view, stage.action, stage.target))


def predict_rows(stages, offsets, size_offsets=(0.,)*6, models=MODELS):
    out = []
    for gid, stage in stages:
        values = {method: predict(stage, method, offsets, size_offsets) for method in models}
        if abs(stage.in_game_probability - values[stage.actor_params.block_prediction]) > 1e-10:
            raise AssertionError('forecast changed between online and offline evaluation')
        out.append({'game_id':gid, 'action':stage.action.value, 'target_influences':stage.view.hidden_counts[stage.target],
                    'stood':stage.outcome, 'turn':stage.view.turn,
                    'actor_forecast':stage.in_game_probability, **values})
    return out


def fit_offsets(stages, ridge=10.0):
    """Four *predefined* action x target-influence log-odds offsets.

    A penalized logistic likelihood is optimized via one-dimensional Newton
    iterations. The candidate selection, grouping and penalty are locked
    before viewing holdout results. All stages are from development games.
    """
    offsets = []
    for idx in range(4):
        sub = [s for _, s in stages if fit_group(s) == idx]
        old = np.asarray([predict(s, 'opponent_action', (0.,)*4) for s in sub])
        y = np.asarray([s.outcome for s in sub], dtype=float)
        logits = np.log(np.clip(old, 1.e-8, 1.-1.e-8) / (1-np.clip(old, 1.e-8, 1.-1.e-8)))
        delta = 0.0
        for _ in range(30):
            p = 1. / (1. + np.exp(-np.clip(logits+delta, -50, 50)))
            grad = np.sum(p-y) + ridge*delta
            hess = np.sum(p*(1-p)) + ridge
            step = grad/hess
            delta = float(np.clip(delta-step, -2.5, 2.5))
            if abs(step) < 1.e-9:
                break
        offsets.append(delta)
    return tuple(offsets)


def score(stages, rows, games, boot=600, seed=33, models=MODELS):
    """Paired forecast comparisons on identical events, game-clustered CIs."""
    rng = np.random.default_rng(seed)
    samples = rng.integers(0, games, (boot,games))
    result = []
    filters = [('all', lambda x: True),
               ('steal', lambda x: x['action'] == ActionType.STEAL.value),
               ('assassinate', lambda x: x['action'] == ActionType.ASSASSINATE.value)]
    for action, pred in filters:
        for target in ('all', 'one', 'two') if action != 'all' else ('all',):
            selected = [r for r in stages if pred(r) and
                        (target == 'all' or r['target_influences'] == (1 if target == 'one' else 2))]
            if not selected:
                continue
            gids = np.asarray([r['game_id'] for r in selected], dtype=int)
            y = np.asarray([r['stood'] for r in selected], dtype=float)
            stage_ct = np.bincount(gids, minlength=games)
            counts = stage_ct[samples].sum(axis=1)
            valid = counts > 0
            for model in models:
                p = np.asarray([r[model] for r in selected])
                base = np.asarray([r['opponent'] for r in selected])
                gap = p-y
                error = (p-y)**2
                delta = error - (base-y)**2
                by_gap = np.bincount(gids, weights=gap, minlength=games)
                by_delta = np.bincount(gids, weights=delta, minlength=games)
                gap_bs = by_gap[samples[valid]].sum(axis=1) / counts[valid]
                d_bs = by_delta[samples[valid]].sum(axis=1) / counts[valid]
                row = {'action': action, 'target': target, 'model': model,
                       'stages': len(selected), 'predicted': float(p.mean()),
                       'observed': float(y.mean()), 'gap': float(gap.mean()),
                       'brier': float(error.mean()), 'brier_delta_vs_opponent':float(delta.mean())}
                row['gap_ci_low'], row['gap_ci_high'] = map(float, np.quantile(gap_bs, [0.025,0.975]))
                row['brier_delta_ci_low'], row['brier_delta_ci_high'] = map(float, np.quantile(d_bs, [0.025,0.975]))
                result.append(row)
    return result


def summarize_game_counts(rows):
    return {k: float(np.mean([r[k] for r in rows])) for k in
            ('attacks', 'block_stages', 'intervention_offers', 'intervention_claims', 'intervention_stands')}
