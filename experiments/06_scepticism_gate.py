"""Trait-isolated scepticism stress test, preserving the EGTA archetype gate as context.

Each row compares a focal player to residents who are identical except for
focal action-bluff propensity. This avoids changing block_bluff and scepticism
at the same time (a confound in the existing Bluffer archetype).
"""
from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import replace
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from intencoes.egta import ARCHETYPES
from intencoes.rules import RuleConfig
from intencoes.agents import HeuristicAgent
from intencoes.engine import Game
from importlib.util import spec_from_file_location, module_from_spec

spec=spec_from_file_location('calibration5',ROOT/'experiments'/'05_calibration.py')
module=module_from_spec(spec)
spec.loader.exec_module(module)

def isolated_gate(games,theta):
    resident=replace(ARCHETYPES['Pushover'],challenge_threshold=theta,stake_bonus=0.15)
    focal=replace(resident,bluff=0.5)
    a=module.gate(games,focal,resident)
    r=module.gate(games,resident,resident)
    # We estimate relative to residents in each focal group and note that
    # the raw null focal win rate may vary with seat and first-player distribution.
    return {'theta':theta,'mutant_wins':a['wins'],'mutant_fit':a['relative_fitness'],
            'ci_low':a['ci_low'],'ci_high':a['ci_high'],
            'null_wins':r['wins'],'null_fit':r['relative_fitness'],'n_games':games}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--games',type=int,default=1200)
    args=parser.parse_args()
    rows=[]
    for theta in (0,0.15,0.3,0.45,0.6):
        v=isolated_gate(args.games,theta)
        rows.append(v)
        print('THETA',theta,'isolated bluff fitness',round(v['mutant_fit'],3),
              '[',round(v['ci_low'],3),round(v['ci_high'],3),']',
              'null',round(v['null_fit'],3),flush=True)
    out=ROOT/'results'/'calibration'/'scepticism_sweep.csv'
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)
