"""Blocking-calibration gate: voluntary play, forced opportunities, invasion smoke.

This is a deliberately small *diagnostic*, NOT Experiments 2--4. It reports
conditional block-stage forecasts (not all declared attacks) and offer rates.

Run: PYTHONPATH=src python experiments/05_calibration.py --games 600 --probes 600 --gate 1200
Outputs are isolated in results/calibration; historical results are unchanged.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from intencoes.agents import HeuristicAgent, Params  # noqa: E402
from intencoes.egta import ARCHETYPES  # noqa: E402
from intencoes.engine import Game  # noqa: E402
from intencoes.rules import CLAIM, ActionType, RuleConfig  # noqa: E402

ATTACKS = {ActionType.STEAL.value, ActionType.ASSASSINATE.value}


def wilson(k, n, z=1.96):
    if not n:
        return 0, 1
    p = k / n
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = (z / d) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return center - half, center + half


def ratio(k, n, players):
    p = k / n
    lo, hi = wilson(k, n)
    f = lambda v: ((players - 1) * v / (1 - v)) if v < 1 else float('inf')
    return f(p), f(lo), f(hi)


def summarise_games(games):
    data = Counter()
    by_offer = defaultdict(Counter)
    pred = defaultdict(list)
    stage_pred = defaultdict(list)
    for g in games:
        data['games'] += 1
        data['turns'] += g.turn
        data['wins'] += g.winner is not None
        for e in g.log:
            if e['event'] == 'action' and e['action'] in ATTACKS:
                data['declared_attacks'] += 1
                if e['result'] in ('ok', 'blocked'):
                    data['attack_block_stages'] += 1
                    data['standing_blocks'] += e['result'] == 'blocked'
                    if 'p_blocked_pred' in e:
                        pred[e['action']].append((e['p_blocked_pred'], int(e['result'] == 'blocked')))
            if e['event'] == 'block_stage' and e['action'] in ATTACKS and 'p_blocked_pred' in e:
                stage_pred[e['action']].append((e['p_blocked_pred'],int(e['stood'])))
            if e['event'] == 'block_offer':
                m = e['mode']
                if e['action'] not in ATTACKS:
                    continue
                counts = by_offer[(e['action'], m)]
                counts['offers'] += 1
                counts['can_hold'] += e['has_blocker']
                counts['claims'] += e['claimed']
                counts['claims_holding'] += e['claimed'] and e['has_blocker']
                counts['claims_without'] += e['claimed'] and not e['has_blocker']
                counts['stands'] += e['stood']
    n = data['games']
    out = {'games': n, 'turns_per_game': data['turns']/n,
           'attacks_per_game': data['declared_attacks']/n,
           'block_stages_per_game': data['attack_block_stages']/n,
           'third_party_offers_per_game': sum(v['offers'] for (a,m),v in by_offer.items() if m=='intervention')/n,
           'third_party_claims_per_game': sum(v['claims'] for (a,m),v in by_offer.items() if m=='intervention')/n,
           'stood_per_attack_stage': data['standing_blocks']/max(1,data['attack_block_stages'])}
    all_pred = [x for samples in pred.values() for x in samples]
    if all_pred:
        out['predicted_stood_per_attack_stage'] = sum(p for p,y in all_pred)/len(all_pred)
        out['forecast_brier'] = sum((p-y)**2 for p,y in all_pred)/len(all_pred)
        out['forecast_n'] = len(all_pred)
    else:
        out.update(predicted_stood_per_attack_stage=None, forecast_brier=None, forecast_n=0)
    stage_samples = [x for samples in stage_pred.values() for x in samples]
    if stage_samples:
        out['stage_predicted_stood'] = sum(p for p,y in stage_samples)/len(stage_samples)
        out['stage_brier'] = sum((p-y)**2 for p,y in stage_samples)/len(stage_samples)
        out['stage_n'] = len(stage_samples)
    else:
        out.update(stage_predicted_stood=None,stage_brier=None,stage_n=0)
    rows = []
    for (a,m),v in sorted(by_offer.items()):
        rows.append({'action':a,'mode':m, 'offers':v['offers'],
                     'card_available_per_offer':v['can_hold']/v['offers'],
                     'claims_per_offer':v['claims']/v['offers'],
                     'stands_per_offer':v['stands']/v['offers'],
                     'claims_given_holding':v['claims_holding']/v['can_hold'] if v['can_hold'] else None,
                     'claims_without_holding':v['claims_without']/(v['offers']-v['can_hold']) if v['offers']>v['can_hold'] else None})
    return out,rows


def voluntary(games, mode, enabled):
    cfg = RuleConfig(n_players=4, intervention_enabled=enabled)
    params = Params(block_prediction=mode)
    for seed in range(games):
        agents = [HeuristicAgent(params, seed=seed * 31 + k) for k in range(4)]
        g = Game(agents, cfg, seed=seed, first_player=seed % 4)
        g.play()
        yield g


class ProbeAttacker(HeuristicAgent):
    def __init__(self, action, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.probe_action = action
    def act(self, view):
        return self.probe_action, 1


def forced(games, action, *, intervene):
    """Forced credible claims on turn zero to measure defense without attack selection.

    Simulated deck is sampled unconditionally, then restricted to the actor
    holding the claimed character. This conditioning is explicit and differs
    from the unrestricted 2-coin game: all players start at 3 coins here.
    """
    cfg = RuleConfig(n_players=4, starting_coins=3, intervention_enabled=True)
    params = replace(Params(), intervene=intervene)
    accepted = 0
    seed = 0
    while accepted < games:
        ag = [ProbeAttacker(action, Params(), seed=seed*31)]
        ag.extend(HeuristicAgent(params, seed=seed*31+k) for k in range(1,4))
        g = Game(ag, cfg, seed=seed, first_player=0)
        seed += 1
        if CLAIM[action] not in g.players[0].hand:
            continue
        g.play_turn()
        g.check_invariants()
        accepted += 1
        yield g


def gate(games, focal, resident, *, enabled=True):
    cfg = RuleConfig(n_players=4, intervention_enabled=enabled)
    victories = 0
    draws = 0
    for seed in range(games):
        agents = [HeuristicAgent(focal, seed=seed*31)] + [HeuristicAgent(resident,seed=seed*31+k) for k in range(1,4)]
        g = Game(agents, cfg, seed=seed, first_player=seed%4)
        w = g.play()
        victories += w == 0
        draws += w is None
    r,low,high = ratio(victories, games-draws, 4)
    return {'n_games': games, 'wins': victories, 'draws': draws, 'relative_fitness':r, 'ci_low':low, 'ci_high':high}


def write_csv(path,rows):
    if not rows:
        return
    with path.open('w',newline='',encoding='utf-8') as f:
        dw = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        dw.writeheader()
        dw.writerows(rows)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--games',type=int,default=600)
    ap.add_argument('--probes',type=int,default=600)
    ap.add_argument('--gate',type=int,default=1200)
    args=ap.parse_args()
    out=ROOT/'results'/'calibration'
    out.mkdir(parents=True,exist_ok=True)
    summary=[]; offers=[]; gates=[]
    for mode in ('card_only','empirical','none'):
        for enabled in (False,True):
            s,offer=summarise_games(voluntary(args.games,mode,enabled))
            s.update(context='voluntary',block_prediction=mode,intervention_enabled=enabled)
            summary.append(s)
            offers.extend({**r,'context':'voluntary','block_prediction':mode,'intervention_enabled':enabled} for r in offer)
            print('VOLUNTARY',mode,enabled,'attacks',round(s['attacks_per_game'],3),
                  'third_party_claims',round(s['third_party_claims_per_game'],3),
                  'pred',round(s['predicted_stood_per_attack_stage'] or 0,3),
                  'stage_pred',round(s['stage_predicted_stood'] or 0,3),
                  'actual',round(s['stood_per_attack_stage'],3),flush=True)
    for action in (ActionType.STEAL,ActionType.ASSASSINATE):
        for intervene in (0.0,0.5,1.0):
            s,offer=summarise_games(forced(args.probes, action, intervene=intervene))
            s.update(context='forced_honest_claim',action=action.value,intervene=intervene)
            summary.append(s)
            offers.extend({**r,'context':'forced_honest_claim','intervene':intervene} for r in offer)
            print('FORCED',action.name,intervene,'offers',round(s['third_party_offers_per_game'],3),
                  'claims',round(s['third_party_claims_per_game'],3),flush=True)
    for resident_name in ('Pushover','HonestSceptic'):
        r=gate(args.gate,ARCHETYPES['Bluffer'],ARCHETYPES[resident_name])
        r.update(focal='Bluffer',resident=resident_name)
        gates.append(r)
        print('GATE',resident_name,'relative',round(r['relative_fitness'],3),
              '[',round(r['ci_low'],3),round(r['ci_high'],3),']',flush=True)
    for name,rows in (('summary.csv',summary),('offers.csv',offers),('gate.csv',gates)):
        write_csv(out/name,rows)
    print('COMPLETE',out,flush=True)
