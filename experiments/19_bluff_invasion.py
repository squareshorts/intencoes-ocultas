"""Prospective rare-bluffer invasion experiment on frozen Intencoes Ocultas agents.

Run: python experiments/19_bluff_invasion.py --players 4 --games 1200 --boot 2000

Scientific contrast: one strategically bluffing player (bluff propensity 0.8)
versus an otherwise identical honest-action resident (bluff propensity 0),
competing against n-1 honest-action residents. No other trait changes within a
paired contrast. Theta is varied across the ENTIRE table. Blocking forecast is
held fixed within a cell and varied as a sensitivity factor. Individual
seeds are paired for each cell and the focal first-player advantage rotates.

Important: 'honest-action' means no chosen false ACTION claims. The existing
heuristic's forced last-influence defensive bluff remains in force for all players.

Output: one CSV per size, theta, forecast, with paired game-level observations.
Files are written after each completed cell so interrupted runs are resumable.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from intencoes.agents import HeuristicAgent, Params
from intencoes.engine import Game
from intencoes.rules import ActionType, CLAIM, RuleConfig
from intencoes.sim import game_record

OUT = ROOT / 'results' / 'bluff_invasion'
FROZEN_PATH = ROOT / 'results' / 'action_calibration' / 'frozen_size_fit.json'
FROZEN = json.loads(FROZEN_PATH.read_text(encoding='utf-8'))
assert FROZEN['status'] == 'size_development_frozen'
POLICIES = ('empirical', 'opponent', 'opponent_action')
THETAS = (0.05, 0.30, 0.50)
BASE = dict(bluff=0.0, stake_bonus=0.15, block_bluff=0.0,
            intervene=0.5, intervene_bluff=0.0, foreign_aid=0.5,
            bluff_target='strategic')
PUBLIC_PRIOR = dict(opponent_intervene=.5, opponent_intervene_bluff=.15,
                    opponent_block_bluff=.4, block_prior_strength=1.0,
                    opponent_pool_strength=2.0)
MUTANT_BLUFF = 0.80


class CoupledBluffAgent(HeuristicAgent):
    """Control common RNG until an ACTUAL false action is selected.

    A bluff propensity can consume extra RNG when a candidate bluff is
    considered and rejected. This subclass compares the focal action against
    its counterfactual honest policy from the exact same RNG state. If no
    false action is ultimately selected, it takes the honest action AND its
    RNG state. For actual bluffs, it retains the original heuristic's action
    and RNG state. Other strategies and the engine are unchanged.

    Used only as an experimental control, not as a replacement agent.
    """
    def act(self, view):
        if self.p.bluff == 0:
            return super().act(view)
        initial_state = self.rng.getstate()
        proposed = super().act(view)
        proposed_state = self.rng.getstate()
        self.rng.setstate(initial_state)
        original_params = self.p
        try:
            self.p = replace(original_params, bluff=0.0)
            honest_action = super().act(view)
        finally:
            self.p = original_params
        character = CLAIM[proposed[0]]
        if character is not None and character not in view.hand:
            self.rng.setstate(proposed_state)
            return proposed
        return honest_action


def make_params(policy, theta, mutant=False):
    kwargs = {**BASE, **PUBLIC_PRIOR, 'challenge_threshold':theta,
              'block_prediction':policy, 'bluff': MUTANT_BLUFF if mutant else 0.0}
    if policy == 'opponent_action':
        kwargs['action_block_offsets'] = tuple(FROZEN['action_block_offsets'])
        kwargs['size_block_offsets'] = tuple(FROZEN['size_block_offsets'])
    return Params(**kwargs)


def one_game(config, params, seed, coupled=False):
    n = config.n_players
    agents = [(CoupledBluffAgent if coupled and i==0 else HeuristicAgent)(
              params[i], seed=seed * 31 + i) for i in range(n)]
    g = Game(agents, config, seed=seed, first_player=seed % n)
    g.play()
    rec = game_record(g)
    actions = [e for e in g.log if e['event'] == 'action' and e['actor']==0]
    false_actions = [e for e in actions if e['claim_true'] is False]
    contested_actions = [e for e in g.log if e['event']=='challenge'
                         and e['kind']=='action' and e['claimant']==0]
    all_actions = [e for e in g.log if e['event']=='action']
    attacks = sum(e['action'] in (ActionType.STEAL.value, ActionType.ASSASSINATE.value)
                  for e in all_actions)
    return dict(won=int(g.winner==0),draw=int(g.winner is None),
                focal_turns=len(actions),
                focal_claimed=sum(e['claim'] is not None for e in actions),
                focal_bluffs=len(false_actions),
                focal_bluffs_challenged=sum(e['result']=='failed_challenge' for e in false_actions),
                focal_bluffs_succeeded=sum(e['result']=='ok' for e in false_actions),
                focal_challenges_received=len(contested_actions),
                attack_actions=attacks,
                intervention_offers=rec['intervention_offers'],
                interventions_stood=rec['interventions_stood'],
                turns=g.turn)


def pair(config, theta, policy, seed, coupled=False):
    resident=make_params(policy,theta)
    bluffer=make_params(policy,theta,True)
    baseline=one_game(config,[resident]*config.n_players,seed,coupled)
    treatment=one_game(config,[bluffer]+[resident]*(config.n_players-1),seed,coupled)
    if coupled and treatment['focal_bluffs']==0:
        assert treatment==baseline, ('unrealized bluff changed the game',seed,theta,policy)
    d={'seed':seed,'baseline_win':baseline['won'],
       'mutant_win':treatment['won'],'delta_win':treatment['won']-baseline['won']}
    for key in treatment:
        if key!='won':
            d['mutant_'+key]=treatment[key]
            d['baseline_'+key]=baseline[key]
    return d


def save_csv(path,records):
    temp=path.with_suffix('.tmp')
    with temp.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=records[0].keys())
        writer.writeheader();writer.writerows(records)
    temp.replace(path)


def summarize_cell(n,theta,policy,records,boot):
    a=np.array([r['delta_win'] for r in records],float)
    rng=np.random.default_rng(46_013+n*100+int(theta*1000)+sum(map(ord,policy)))
    if boot:
        ix=rng.integers(0,len(a),size=(boot,len(a)))
        lo,hi=np.quantile(a[ix].mean(axis=1),[.025,.975])
    else:
        lo,hi=float('nan'),float('nan')
    up=sum(r['delta_win']==1 for r in records)
    down=sum(r['delta_win']==-1 for r in records)
    p=binomtest(up,up+down,.5).pvalue if up+down else 1.
    def mean(k): return float(np.mean([r[k] for r in records]))
    return dict(players=n,theta=theta,policy=policy,games=len(records),
                win_base=mean('baseline_win'),win_bluffer=mean('mutant_win'),
                delta_win=mean('delta_win'),ci_low=float(lo),ci_high=float(hi),
                paired_mcnemar_p=float(p),discordant_plus=up,discordant_minus=down,
                focal_bluffs_per_game=mean('mutant_focal_bluffs'),
                focal_bluffs_challenged_per_game=mean('mutant_focal_bluffs_challenged'),
                focal_bluffs_succeeded_per_game=mean('mutant_focal_bluffs_succeeded'),
                focal_claims_per_game=mean('mutant_focal_claimed'),
                attacks_mutant=mean('mutant_attack_actions'),
                attacks_base=mean('baseline_attack_actions'),
                intervention_offers_mutant=mean('mutant_intervention_offers'),
                intervention_offers_base=mean('baseline_intervention_offers'))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--players',type=int,choices=(3,4,5),default=4)
    parser.add_argument('--games',type=int,default=1200)
    parser.add_argument('--boot',type=int,default=2000)
    parser.add_argument('--batch',type=int,default=100)
    parser.add_argument('--coupled',action='store_true',help='strict counterfactual RNG coupling')
    args=parser.parse_args()
    OUT.mkdir(exist_ok=True,parents=True)
    prefix='paired_coupled' if args.coupled else 'paired'
    cfg=RuleConfig(n_players=args.players,intervention_reward=1)
    protocol=dict(n_players=args.players,theta=THETAS,forecasts=POLICIES,
        mutant_bluff=MUTANT_BLUFF,resident_bluff=0.0,
        base=BASE,public_prior=PUBLIC_PRIOR,rule_config=asdict(cfg),
        frozen_model_sha256=FROZEN['sha256'],
        frozen_coefficients_file_sha256=hashlib.sha256(FROZEN_PATH.read_bytes()).hexdigest(),
        seed_start_formula='9500000 + n_players*100000 + theta_index*20000',
        games_requested=args.games,
        primary_endpoint='paired difference in focal win probability relative to all-honest table',
        secondary_endpoints=['observed action bluffs','caught bluffs','successful bluffs','attacks','third-party exposure'],
        ci='95% paired game-seed bootstrap',
        multiplicity='Holm adjustment across 9 comparisons at primary n=4',
        note='No holdout refitting; exploratory simulation on frozen agents; unconfirmed rules unchanged',
        strict_coupling=args.coupled)
    (OUT/f'protocol_{prefix}_n{args.players}.json').write_text(json.dumps(protocol,indent=2)+'\n',encoding='utf-8')
    for ti,theta in enumerate(THETAS):
        for policy in POLICIES:
            path=OUT/f'{prefix}_n{args.players}_theta{theta:.2f}_{policy}.csv'
            if path.exists():
                with path.open(newline='',encoding='utf-8') as f:
                    records=list(csv.DictReader(f))
                if len(records)>args.games:
                    records=records[:args.games]
                for r in records:
                    for k,v in list(r.items()):r[k]=int(v)
            else: records=[]
            seed_start=9_500_000+args.players*100_000+ti*20_000
            for i in range(len(records),args.games):
                records.append(pair(cfg,theta,policy,seed_start+i,args.coupled))
                if len(records)%args.batch==0:
                    save_csv(path,records)
                    print('PROGRESS',prefix,args.players,theta,policy,len(records),'/',args.games,flush=True)
            if records:save_csv(path,records)
            summ=summarize_cell(args.players,theta,policy,records,args.boot)
            print('RESULT',prefix,args.players,theta,policy,'diff',round(summ['delta_win'],4),
                  'CI',round(summ['ci_low'],4),round(summ['ci_high'],4),
                  'bluff/game',round(summ['focal_bluffs_per_game'],3),flush=True)
    print('COMPLETE',prefix,args.players,flush=True)

if __name__=='__main__':main()
