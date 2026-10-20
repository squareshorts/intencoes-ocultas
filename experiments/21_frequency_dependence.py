"""Frequency dependence of strategic bluffing in Intencoes Ocultas.

Prespecified before running the data-generating experiments on 2026-10-19.
Do not alter frozen heuristics, calibration offsets, or historical outputs.

For every profile k=0..n bluffers at a n-player table, simulate complete
matches, randomizing and balancing type assignments across seats. All
players share scepticism theta and their block-forecast family. Bluffers
differ from honest-action agents only in Params.bluff (0.8 vs 0.0).
CoupledBluffAgent preserves the honest policy and RNG state if a proposed
false action is not selected, avoiding the prior rejected-bluff RNG artefact.

Outputs checkpoint once per entire cell, atomically; resumable runs.
Shared seed IDs within cells support profile-level paired uncertainty.
"""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, itertools, json, sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from intencoes.agents import HeuristicAgent
from intencoes.engine import Game
from intencoes.rules import ActionType, RuleConfig

spec=importlib.util.spec_from_file_location('rare_bluff', ROOT/'experiments'/'19_bluff_invasion.py')
rare=importlib.util.module_from_spec(spec)
spec.loader.exec_module(rare)
CoupledBluffAgent=rare.CoupledBluffAgent
make_params=rare.make_params
OUTPUT=ROOT/'results'/'frequency_dependence'
THETAS=[.05,.30,.50]
POLICIES=['empirical','opponent','opponent_action']
FIELDNAMES=['seed_id','seed','players','theta','policy','reward','k_bluffers',
            'winner_type','winner_seat','draw','b_wins','h_wins','false_action_claims',
            'action_claims','attacks','intervention_offers','intervention_claims',
            'interventions_stood','turns','seats_bluffers']

def cases(scope, games):
    if scope=='primary':
        return [(4,t,p,1,k,games) for t in THETAS for p in POLICIES for k in range(5)]
    if scope=='cross_size':
        return [(n,.05,p,1,k,games) for n in [3,5] for p in POLICIES for k in range(n+1)]
    if scope=='reward':
        return [(4,.05,'opponent',r,k,games) for r in [0,2] for k in range(5)]
    raise ValueError(scope)

def filename(n,t,p,r,k):
    return OUTPUT/f'n{n}_t{t:.2f}_{p}_r{r}_k{k}.csv'

def _seed_formula(n,t,p,r,j):
    # disjoint from earlier 9,500,000 rare-mutant series; k shares seeds
    z=25_000_000+n*1_000_000+int(round(t*100))*20_000+POLICIES.index(p)*2_000+r*100_000
    return z+j

def run_cell(args):
    n,theta,policy,reward,k,games=args
    target=filename(n,theta,policy,reward,k)
    if target.exists():
        with target.open(encoding='utf-8') as f:
            r=csv.DictReader(f)
            count=sum(1 for _ in r)
        if count==games: return str(target),count,True
        raise RuntimeError(f'inconsistent existing cell: {target}, {count} != {games}')
    cfg=RuleConfig(n_players=n,intervention_reward=reward)
    honest=make_params(policy,theta,False)
    bluffer=make_params(policy,theta,True)
    combos=list(itertools.combinations(range(n),k))
    # Independent counterbalancing: every subset occurs under every
    # first-player seat equally often in n*LCM(C(n,k), all k) games.
    # Unlike first_player=seed%n, this avoids phase-locking first turn
    # with which strategy is seated in a particular position.
    seat_period={3:3,4:12,5:10}[n]
    records=[]
    for j in range(games):
        seed=_seed_formula(n,theta,policy,reward,j)
        # exactly balanced over seating subsets when games divisible by C(n,k)
        occupied=set(combos[j%len(combos)])
        agents=[(CoupledBluffAgent if seat in occupied else HeuristicAgent)(
                 bluffer if seat in occupied else honest,seed=seed*31+seat)
                for seat in range(n)]
        g=Game(agents,cfg,seed=seed,first_player=(j//seat_period)%n)
        w=g.play()
        bluff_wins=int(w in occupied) if w is not None else 0
        honest_wins=int(w not in occupied) if w is not None else 0
        rows=g.log
        declared=[e for e in rows if e['event']=='action']
        block=[e for e in rows if e['event']=='block']
        offers=[e for e in rows if e['event']=='block_offer']
        records.append(dict(seed_id=j,seed=seed,players=n,theta=theta,policy=policy,
            reward=reward,k_bluffers=k,winner_type=('draw' if w is None else
                 'B' if w in occupied else 'H'),winner_seat=(-1 if w is None else w),
            draw=int(w is None),b_wins=bluff_wins,h_wins=honest_wins,
            false_action_claims=sum(e['claim_true'] is False for e in declared),
            action_claims=sum(e['claim'] is not None for e in declared),
            attacks=sum(e['action'] in (ActionType.STEAL.value,ActionType.ASSASSINATE.value) for e in declared),
            intervention_offers=sum(e['mode']=='intervention' for e in offers),
            intervention_claims=sum(e['interventor'] for e in block),
            interventions_stood=sum(e['interventor'] and e['stands'] for e in block),
            turns=g.turn,seats_bluffers=';'.join(map(str,sorted(occupied)))))
    OUTPUT.mkdir(parents=True,exist_ok=True)
    temp=target.with_suffix('.tmp')
    with temp.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,FIELDNAMES)
        writer.writeheader();writer.writerows(records)
    temp.replace(target)
    return str(target),games,False

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--scope',choices=('primary','cross_size','reward'),default='primary')
    ap.add_argument('--games',type=int,default=1800)
    ap.add_argument('--workers',type=int,default=4)
    args=ap.parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    tasklist=cases(args.scope,args.games)
    metadata=dict(scope=args.scope,games_per_profile=args.games,workers=args.workers,
        setup='all type-seat subsets x first-player position independently counterbalanced using LCM period; common game seeds across k',
        seed_formula='25M+n*1M+theta100*20k+policyindex*2k+reward*100k+j',
        params_honest_bluff=0.0,params_bluffer_bluff=0.8,
        shared_scepticism=True,forecast_prior='frozen',
        no_human_participants=True,
        primary_payoff='win probability per PLAYER of each type, not raw group win probability',
        analysis='two-type Bernoulli payoff, n-player binomial-matched replicator and fixation sensitivities',
        revision='pre-specified before inspecting frequency-composition outcomes',
        repo_parent='7f6b57f6ab71652f4a3ce96c66c33152d5ef3bcf',
        fossil_coeff_file_sha256=hashlib.sha256(rare.FROZEN_PATH.read_bytes()).hexdigest())
    (OUTPUT/f'protocol_{args.scope}.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futs=[pool.submit(run_cell,t) for t in tasklist]
        for i,f in enumerate(as_completed(futs),1):
            path,num,skipped=f.result()
            print(f'{i:02}/{len(futs)} {Path(path).name} games={num} {"reused" if skipped else "new"}',flush=True)
    print('DONE',args.scope,flush=True)

if __name__=='__main__':main()
