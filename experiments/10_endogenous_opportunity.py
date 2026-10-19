"""Endogenous blocking calibration and randomized opportunity-encouragement gate.

Run from repository root::
    python experiments/10_endogenous_opportunity.py --games 350 --probes 600 --boot 700

The encouragement arm randomizes an *instruction to choose a truthful steal* on
an actor's FIRST turn, provided that the actor privately holds Comerciante and
a target has coins. It does not force third parties to protect and cannot
ensure that the resulting action survives the challenge and target-block phases.
The random assignment, NOT the realized offer count, is exogenous; realized
opportunity exposure is reported explicitly. No estimate is called fitness.

All in-policy forecasts are evaluated at pre-offer snapshots; paired estimators
score the SAME stages. Games are the bootstrap units; stages are not iid.
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from intencoes.agents import HeuristicAgent  # noqa: E402
from intencoes.egta import ARCHETYPES  # noqa: E402
from intencoes.engine import Game  # noqa: E402
from intencoes.rules import ActionType, Character, RuleConfig  # noqa: E402
from intencoes.sim import game_record  # noqa: E402

MIX = ('Default', 'HonestProtector', 'Bluffer', 'Pushover', 'BlufferFakeProtector')
SHIFT = ('FakeProtector', 'HonestTrusting', 'ScepticProtector',
         'HonestSceptic', 'BlufferFakeProtector')
PRIOR = dict(opponent_intervene=0.5, opponent_intervene_bluff=0.15,
             opponent_block_bluff=0.4, block_prior_strength=1.0,
             opponent_pool_strength=2.0)
METHODS = ('empirical', 'opponent_prior', 'opponent_pool', 'opponent')
ATTACKS = (ActionType.STEAL, ActionType.ASSASSINATE)


def seat_params(n, seed, population, belief):
    if population == 'homogeneous':
        names = ['Default'] * n
    else:
        group = MIX if population == 'mixed' else SHIFT
        names = [group[(seed + j) % len(group)] for j in range(n)]
        random.Random(seed * 1009 + 17).shuffle(names)
    return [replace(ARCHETYPES[name], block_prediction=belief, **PRIOR) for name in names]


class EncouragedAgent(HeuristicAgent):
    """Randomized first-turn truthful-steal encouragement; no hidden-opponent access."""

    def __init__(self, *args, opportunity_dose=0.0, blind_anticipation=False,
                 encouragement_seed=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.dose = opportunity_dose
        self.blind = blind_anticipation
        self.encourage_rng = random.Random(encouragement_seed)
        self.first_act = True
        self.eligible = 0
        self.assigned = 0
        self.forced = 0
        self.just_forced = False

    def act(self, view):
        self.just_forced = False
        if self.first_act:
            self.first_act = False
            # Assignment is independent of beliefs. Uptake is only possible
            # for truthful legal steals; report actual eligibility separately.
            self.assigned = int(self.encourage_rng.random() < self.dose)
            targets = [j for j in view.active if j != view.me and view.coins[j] > 0]
            possible = (Character.COMERCIANTE in view.hand and
                        view.coins[view.me] < view.config.forced_coup_threshold and bool(targets))
            self.eligible = int(possible)
            if self.assigned and possible:
                self.forced = 1
                self.just_forced = True
                return ActionType.STEAL, self.encourage_rng.choice(targets)
        if self.blind:
            # Mechanical ablation: suppress *anticipation* of intervention
            # during action selection, but actual challenge and block phases
            # use the unchanged View and Game.config. Not a normative agent.
            counterfactual = replace(view, config=replace(view.config, intervention_enabled=False))
            return super().act(counterfactual)
        return super().act(view)


@dataclass(frozen=True)
class Stage:
    game_id: int
    action: ActionType
    target: int
    view: object
    actor_params: object
    outcome: int
    forced: bool
    in_game_probability: float


class InstrumentedGame(Game):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.snapshots = []

    def _block_phase(self, actor, action, target):
        if action not in ATTACKS:
            return super()._block_phase(actor, action, target)
        pre_offer = self.view(actor)
        params = self.agents[actor].p
        forced = bool(getattr(self.agents[actor], 'just_forced', False))
        log_start = len(self.log)
        stood = super()._block_phase(actor, action, target)
        block_event = next(e for e in self.log[log_start:] if e["event"] == "block_stage")
        self.snapshots.append(Stage(-1, action, target, pre_offer, params, int(stood),
                                    forced, block_event.get("p_blocked_pred", float("nan"))))
        return stood


def predict(stage, model):
    # Research-only *offline* scoring. Acting agents never receive oracle labels
    # or the sampled truth of any defender's private cards.
    agent = HeuristicAgent(replace(stage.actor_params, block_prediction=model))
    return float(agent.predicted_block_probability(stage.view, stage.action, stage.target))


def game_iteration(seed, population, belief, dose, reward, anticipation='aware',
                   enabled=True, n=4):
    params = seat_params(n, seed, population, belief)
    agents = [EncouragedAgent(params[j], seed=seed * 31 + j,
                              opportunity_dose=dose,
                              blind_anticipation=(anticipation == 'blind'),
                              encouragement_seed=seed * 10007 + 89 * j + 100003)
              for j in range(n)]
    cfg = RuleConfig(n_players=n, intervention_reward=reward,
                     intervention_enabled=enabled)
    g = InstrumentedGame(agents, cfg, seed=seed, first_player=seed % n)
    g.play()
    return g


def row_from_game(g, game_id, scenario):
    rec = game_record(g)
    attacks = [e for e in g.log if e['event'] == 'action' and e['action'] in
               (ActionType.STEAL.value, ActionType.ASSASSINATE.value)]
    blocks = [e for e in g.log if e['event'] == 'block' and e['interventor']]
    first = [e for e in attacks if e['turn'] < g.config.n_players]
    row = {'game_id': game_id, 'scenario': scenario, 'attacks': len(attacks),
           'first_round_attacks': len(first), 'block_stages': len(g.snapshots),
           'action_challenge_failures': sum(e.get('result') == 'failed_challenge' for e in attacks),
           'intervention_offers': rec['intervention_offers'],
           'intervention_claims': rec['interventions'],
           'intervention_stands': rec['interventions_stood'],
           'target_offers': rec['target_block_offers'],
           'target_stands': rec['target_block_stands'],
           'first_turn_eligible': sum(a.eligible for a in g.agents),
           'first_turn_assigned': sum(a.assigned for a in g.agents),
           'first_turn_uptake': sum(a.forced for a in g.agents),
           'turns': rec['turns'],
           'winner': rec['winner'] if rec['winner'] is not None else -1,
           'declared_intervention_bluffs': sum(not e['claim_true'] for e in blocks)}
    return row


def scenarios(include_reward=True, include_anticipation=True):
    base = []
    # Primary held-out, in-policy calibration: three populations, two
    # expectation mechanisms, three levels of randomized encouragement.
    for pop in ('homogeneous', 'mixed', 'shifted'):
        for belief in ('empirical', 'opponent_pool', 'opponent'):
            for dose in (0., 0.5, 1.):
                base.append((pop, belief, dose, 1, 'aware', True))
    if include_reward:
        for pop in ('mixed', 'shifted'):
            for belief in ('empirical', 'opponent'):
                for dose in (0., 1.):
                    for reward in (0, 2):
                        base.append((pop, belief, dose, reward, 'aware', True))
    if include_anticipation:
        for pop in ('mixed', 'shifted'):
            for belief in ('empirical', 'opponent'):
                for dose in (0., 1.):
                    base += [(pop, belief, dose, 1, 'blind', True),
                             (pop, belief, dose, 1, 'blind', False)]
    return list(dict.fromkeys(base))


def label(s):
    pop, belief, dose, reward, anticipation, enabled = s
    return f'{pop}|{belief}|dose={dose:g}|reward={reward}|{anticipation}|enabled={int(enabled)}'


def bootstrap_stats(game_rows, stage_rows, games, boot, seed):
    rng = np.random.default_rng(seed)
    ids = rng.integers(0, games, size=(boot, games))
    def interval(v):
        return tuple(float(x) for x in np.quantile(v, (0.025, 0.975)))
    metrics = ('attacks', 'first_round_attacks', 'block_stages', 'intervention_offers',
               'intervention_claims', 'intervention_stands', 'target_offers',
               'target_stands', 'first_turn_eligible', 'first_turn_assigned',
               'first_turn_uptake', 'turns')
    row = {'games': games, 'stages': len(stage_rows)}
    for k in metrics:
        val = np.asarray([r[k] for r in game_rows], dtype=float)
        ci = interval(val[ids].mean(axis=1))
        row[f'{k}_per_game'] = float(val.mean())
        row[f'{k}_low'], row[f'{k}_high'] = ci
    row['offers_per_attack'] = (sum(r['intervention_offers'] for r in game_rows) /
                                max(1, sum(r['attacks'] for r in game_rows)))
    row['claims_per_offer'] = (sum(r['intervention_claims'] for r in game_rows) /
                               max(1, sum(r['intervention_offers'] for r in game_rows)))
    row['stands_per_offer'] = (sum(r['intervention_stands'] for r in game_rows) /
                               max(1, sum(r['intervention_offers'] for r in game_rows)))
    row['block_stages_per_attack'] = (sum(r['block_stages'] for r in game_rows) /
                                      max(1, sum(r['attacks'] for r in game_rows)))
    if not stage_rows:
        return row, []
    gids = np.asarray([r['game_id'] for r in stage_rows], dtype=int)
    y = np.asarray([r['stood'] for r in stage_rows], dtype=float)
    stage_counts = np.bincount(gids, minlength=games)
    denominator = np.maximum(1, stage_counts[ids].sum(axis=1))
    reference = np.asarray([r['empirical'] for r in stage_rows])
    brier_ref = (reference - y)**2
    reliability = []
    for method in METHODS:
        p = np.asarray([r[method] for r in stage_rows], dtype=float)
        errors = (p - y)**2
        diff = errors - brier_ref
        by_game = np.bincount(gids, weights=diff, minlength=games)
        delta_samples = by_game[ids].sum(axis=1) / denominator
        # Calibration-in-the-large interval, resampled at game level.
        gap_by_game = np.bincount(gids, weights=p - y, minlength=games)
        gap_samples = gap_by_game[ids].sum(axis=1) / denominator
        low, high = interval(delta_samples)
        gap_low, gap_high = interval(gap_samples)
        reliability.append({'model': method, 'stages': len(stage_rows),
                            'predicted': float(p.mean()), 'actual': float(y.mean()),
                            'calibration_gap': float(p.mean()-y.mean()),
                            'gap_ci_low': gap_low, 'gap_ci_high': gap_high,
                            'brier': float(errors.mean()),
                            'brier_delta_vs_empirical': float(diff.mean()),
                            'delta_ci_low': low, 'delta_ci_high': high})
    # The actor's forecast should equal the offline version of the same model.
    own = [r['actor_forecast']-r[r['belief']] for r in stage_rows]
    row['own_forecast_max_difference'] = max((abs(v) for v in own), default=0.)
    if row['own_forecast_max_difference'] > 1e-10:
        raise AssertionError('in-game and offline forecasts disagree')
    return row, reliability


def run_scenario(s, games, boot, seed0=640000, save_raw=False, n_players=4):
    pop, belief, dose, reward, anticipation, enabled = s
    rows, stages = [], []
    scenario_label = label(s) if n_players == 4 else label(s) + f"|players={n_players}"
    # Seed base is shared across arms for game-paired comparisons. Population
    # rosters and initial deck are identical for a given game ID and pop.
    for i in range(games):
        seed = seed0 + i
        g = game_iteration(seed, pop, belief, dose, reward, anticipation, enabled, n=n_players)
        rows.append(row_from_game(g, i, scenario_label))
        for snap in g.snapshots:
            pred = {m: predict(snap, m) for m in METHODS}
            stages.append({'game_id': i, 'turn': snap.view.turn,
                           'action': snap.action.value, 'stood': snap.outcome,
                           'belief': belief, 'forced': int(snap.forced),
                           'actor_forecast': snap.in_game_probability, **pred})
    summary, calibration = bootstrap_stats(rows, stages, games, boot, seed0+918)
    summary.update(population=pop, belief=belief, opportunity_dose=dose, reward=reward,
                   anticipation=anticipation, intervention_enabled=enabled,
                   n_players=n_players, scenario=scenario_label)
    for x in calibration:
        x.update(population=pop, belief=belief, opportunity_dose=dose, reward=reward,
                 anticipation=anticipation, intervention_enabled=enabled,
                 n_players=n_players, scenario=scenario_label,
                 active_model=(x['model'] == belief))
    return summary, calibration, rows if save_raw else [], stages if save_raw else []


def forced_probe(n_games, population, reward, first_seed=960000, n=4):
    """One-turn truthful Comer claim, conditioning on opener holding card.

    Uses the identical accepted deck seeds across reward arms. The resulting
    exposure is exogenous to endogenous action selection but card-conditioned;
    it MUST NOT be pooled with full-game estimates.
    """
    accepted = 0
    seed = first_seed
    c = Counter()
    while accepted < n_games:
        params = seat_params(n, seed, population, 'opponent')
        agents = [EncouragedAgent(params[j], seed=seed*31+j) for j in range(n)]
        g = InstrumentedGame(agents, RuleConfig(n_players=n, intervention_reward=reward),
                             seed=seed, first_player=0)
        seed += 1
        if Character.COMERCIANTE not in g.players[0].hand:
            continue
        # The opener is fixed at seat zero, target at seat one, no choice by
        # the actor. This is a standardized exposure test, not regular play.
        def action_override(_view):
            return ActionType.STEAL, 1
        agents[0].act = action_override
        g.play_turn()
        g.check_invariants()
        c['attack'] += 1
        c['block_stages'] += len(g.snapshots)
        for e in g.log:
            if e['event'] == 'block_offer':
                c[e['mode']+'_offers'] += 1
                c[e['mode']+'_claims'] += int(e['claimed'])
                c[e['mode']+'_stands'] += int(e['stood'])
                c[e['mode']+'_has_card'] += int(e['has_blocker'])
            elif e['event'] == 'block' and e['interventor']:
                c['intervention_claim_true'] += int(e['claim_true'])
        accepted += 1
    rec = {'population':population,'reward':reward,'games':n_games,'seed_start':first_seed,
           'seed_end_exclusive':seed, 'card_conditioned':True}
    rec.update({k: v for k,v in c.items()})
    for mode in ('target','intervention'):
        rec[f'{mode}_offers_per_probe'] = c[f'{mode}_offers']/n_games
        rec[f'{mode}_claims_per_offer'] = (c[f'{mode}_claims']/c[f'{mode}_offers']
                                           if c[f'{mode}_offers'] else None)
        rec[f'{mode}_stands_per_offer'] = (c[f'{mode}_stands']/c[f'{mode}_offers']
                                           if c[f'{mode}_offers'] else None)
    return rec


def write_csv(path, rows):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def run(args):
    out = ROOT/'results'/'policy_gate'
    out.mkdir(parents=True, exist_ok=True)
    setups = scenarios(not args.skip_rewards, not args.skip_anticipation)
    if args.only:
        setups = [s for s in setups if args.only in label(s)]
    summaries, calibration, raw_game, raw_stages = [], [], [], []
    for num, s in enumerate(setups, 1):
        summary, cal, games_rows, stages_rows = run_scenario(
            s, args.games, args.boot, args.seed0, save_raw=args.keep_raw)
        summaries.append(summary)
        calibration.extend(cal)
        if args.keep_raw:
            raw_game.extend(games_rows)
            raw_stages.extend({**r, 'scenario':label(s)} for r in stages_rows)
        print(f'{num}/{len(setups)} {label(s)} stages={summary["stages"]} '
              f'attacks={summary["attacks_per_game"]:.2f} '
              f'intervention_offers={summary["intervention_offers_per_game"]:.2f} '
              f'intervention_stands={summary["intervention_stands_per_game"]:.2f} '
              f'active_Brier={next((x["brier"] for x in cal if x["model"]==s[1]), float("nan")):.3f}',
              flush=True)
        # Save checkpoint incrementally so interruptions do not discard work.
        write_csv(out/'conditions.csv', summaries)
        write_csv(out/'calibration.csv', calibration)
    probes = []
    if args.probes:
        for population in ('mixed','shifted'):
            for reward in (0,1,2):
                result = forced_probe(args.probes, population, reward,
                                      first_seed=args.probe_seed0)
                probes.append(result)
                print('PROBE',population,reward,'stage',result['block_stages'],
                      'intervention_offers',result.get('intervention_offers',0),
                      'stands',result.get('intervention_stands',0),flush=True)
    write_csv(out/'forced_probe.csv',probes)
    if args.keep_raw:
        # These files are diagnostic and regenerable; do not commit to Git.
        write_csv(ROOT/'results'/'raw'/'policy_gate_games.csv',raw_game)
        write_csv(ROOT/'results'/'raw'/'policy_gate_stages.csv',raw_stages)
    return summaries, calibration, probes


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--games', type=int, default=400)
    ap.add_argument('--probes', type=int, default=900)
    ap.add_argument('--boot', type=int, default=600)
    ap.add_argument('--seed0', type=int, default=640000)
    ap.add_argument('--probe-seed0', type=int, default=960000)
    ap.add_argument('--skip-rewards', action='store_true')
    ap.add_argument('--skip-anticipation', action='store_true')
    ap.add_argument('--keep-raw', action='store_true')
    ap.add_argument('--only', default='', help='substring filter on scenario labels')
    args = ap.parse_args()
    run(args)
