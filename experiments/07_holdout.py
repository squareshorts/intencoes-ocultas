"""Held-out n-player and heterogeneous-table blocking forecast stress test.

Do not use these data to tune defaults. All prior variants use the same seeds.
"""
from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import replace
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from intencoes.agents import Params,HeuristicAgent
from intencoes.egta import ARCHETYPES
from intencoes.engine import Game
from intencoes.rules import RuleConfig

spec=spec_from_file_location('calibration5', ROOT/'experiments'/'05_calibration.py')
module=module_from_spec(spec)
spec.loader.exec_module(module)

MIX=('Default','HonestProtector','Bluffer','Pushover','BlufferFakeProtector')


def simulate(games,n,mixed,prior):
    cfg=RuleConfig(n_players=n,intervention_enabled=True)
    for seed in range(games):
        if mixed:
            params=[replace(ARCHETYPES[MIX[(seed+k)%len(MIX)]],
                            block_prediction='empirical',block_prior_strength=prior)
                    for k in range(n)]
        else:
            params=[Params(block_prediction='empirical',block_prior_strength=prior)]*n
        agents=[HeuristicAgent(params[k],seed=seed*31+k) for k in range(n)]
        g=Game(agents,cfg,seed=seed,first_player=seed%n)
        g.play()
        yield g

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--games',type=int,default=600)
    args=ap.parse_args()
    rows=[]
    for n in (3,4,5):
        for mixed in (False,True):
            for prior in ((2,) if not (n==4 and mixed) else (0,1,2,4)):
                s,_=module.summarise_games(simulate(args.games,n,mixed,prior))
                bs=s['stood_per_attack_stage']
                base_brier=bs*(1-bs)
                row={'n_players':n,'mixed':mixed,'prior':prior,'games':args.games,
                     'attacks_per_game':s['attacks_per_game'],
                     'third_party_claims_per_game':s['third_party_claims_per_game'],
                     'stage_count':s['stage_n'],
                     'stage_forecast':s['stage_predicted_stood'],
                     'stage_observed':bs,
                     'calibration_gap':s['stage_predicted_stood']-bs,
                     'brier':s['stage_brier'],
                     'brier_skill':1-s['stage_brier']/base_brier if base_brier>0 else None}
                rows.append(row)
                print('HOLDOUT',n,'mixed',mixed,'prior',prior,'stages',row['stage_count'],
                      'forecast',round(row['stage_forecast'],3),'observed',round(bs,3),
                      'skill',round(row['brier_skill'],3),flush=True)
    out=ROOT/'results'/'calibration'/'holdout.csv'
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)
