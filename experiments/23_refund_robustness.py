"""Sensitivity to unconfirmed assumption A4: refund Sombra cost after failed action challenge.

Exploratory rule sensitivity. Does not change frozen agent parameters; 1200
seeds for each of k=0,...,4 profiles at 4p, theta=.05, opponent forecast.
"""
import argparse, csv, importlib.util, itertools, sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from intencoes.agents import HeuristicAgent
from intencoes.engine import Game
from intencoes.rules import RuleConfig, ActionType
sp=importlib.util.spec_from_file_location('rare',ROOT/'experiments'/'19_bluff_invasion.py')
rare=importlib.util.module_from_spec(sp);sp.loader.exec_module(rare)
from intencoes.agents import HeuristicAgent
OUT=ROOT/'results'/'frequency_dependence'

def run(k,N):
    cfg=RuleConfig(n_players=4,assassin_refund_on_failed_challenge=True)
    hp=rare.make_params('opponent',.05,False);bp=rare.make_params('opponent',.05,True)
    combos=list(itertools.combinations(range(4),k));rows=[]
    path=OUT/f'refund_n4_t0.05_opponent_r1_k{k}.csv'
    for j in range(N):
        seed=34_000_000+j;occupied=set(combos[j%len(combos)])
        agents=[(rare.CoupledBluffAgent if i in occupied else HeuristicAgent)(bp if i in occupied else hp,seed=seed*31+i) for i in range(4)]
        g=Game(agents,cfg,seed=seed,first_player=(j//12)%4);w=g.play()
        rows.append(dict(seed_id=j,seed=seed,k_bluffers=k,b_wins=int(w in occupied) if w is not None else 0,
                         h_wins=int(w not in occupied) if w is not None else 0,draw=int(w is None),
                         false_action_claims=sum(e['event']=='action' and e['claim_true'] is False for e in g.log)))
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return k,N

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--games',type=int,default=1200);a=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(run,k,a.games) for k in range(5)]
        for f in as_completed(futures):print('REFUND',f.result(),flush=True)
if __name__=='__main__':main()
