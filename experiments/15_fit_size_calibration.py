"""Prospective second development cycle after the recorded n=4-only failure.

Table size is PUBLIC. Six action-by-size adjustments are fit on fresh
3/4/5-player on-policy games, using both mixture families and penalized
likelihood. Previous held-out seeds at 3.3m-3.52m are NOT used for training.
A separate final holdout at 6.3m-6.52m is never read by this script.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'experiments'))
from action_calibration_common import (MODELS, predict, predict_rows, score,
                                       stages_for_games, summarize_game_counts)

OUT=ROOT/'results'/'action_calibration'
TRAIN_BASE=4_100_000
SCREEN_BASE=4_900_000
FINAL_BASE=6_000_000
METHODS=('opponent','opponent_action')

def start(base,n,pop):
    return base+n*100_000+(20_000 if pop=='shifted' else 0)


def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not rows: return
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def fit_size_effects(stages,base,ridge=20.):
    """Six independent, shrinkage-penalized log-odds updates for public table size."""
    offsets=[]; counts=[]
    for n in (3,4,5):
        for action in ('Comerciante:roubo','Sombra:ataque'):
            sub=[s for _,s in stages[(n,'mixed')]+stages[(n,'shifted')] if s.action.value==action]
            ps=np.asarray([predict(s,'opponent_action',base) for s in sub])
            ys=np.asarray([s.outcome for s in sub],dtype=float)
            ps=np.clip(ps,1.e-8,1.-1.e-8)
            logits=np.log(ps/(1.-ps))
            delta=0.
            for _ in range(35):
                p=1./(1.+np.exp(-np.clip(logits+delta,-50.,50.)))
                step=(np.sum(p-ys)+ridge*delta)/(np.sum(p*(1.-p))+ridge)
                delta=float(np.clip(delta-step,-1.5,1.5))
                if abs(step)<1.e-9: break
            offsets.append(delta);counts.append(len(sub))
    return tuple(offsets),counts


def run(train=1100,screen=500,boot=600):
    old=json.loads((OUT/'frozen_fit.json').read_text())
    if old['fit_family']!='blend25':
        raise ValueError('first model must be the frozen blend25 model')
    base=tuple(old['offsets'])
    trains={}
    for n in (3,4,5):
        for pop in ('mixed','shifted'):
            seed=start(TRAIN_BASE,n,pop)
            _,stages=stages_for_games(n,pop,'opponent_action',base,seed,train)
            trains[(n,pop)]=stages
            print('TRAIN',n,pop,'games',train,'stages',len(stages),flush=True)
    size,counts=fit_size_effects(trains,base,20.)
    frozen={'status':'size_development_frozen','fit_version':3,
            'parent_frozen_sha256':old['sha256'],
            'action_block_offsets':base,'size_block_offsets':size,
            'size_groups':['3p_steal','3p_assassinate','4p_steal','4p_assassinate','5p_steal','5p_assassinate'],
            'training_stage_counts':counts,'ridge_size':20.0,
            'training_games_per_population_size':train,'dev_screen_games_per_population_size':screen,
            'training_base':TRAIN_BASE,'screen_base':SCREEN_BASE,'untouched_final_base':FINAL_BASE,
            'fit_population':'mixed+shifted, 3/4/5 player tables',
            'mechanistic_challenge_weight':0.25,
            'provenance':'prospective new development and final holdout after failed 9/12 size-transfer test',
            'conformance':'No hidden defender cards or policy identities available to acting agent'}
    frozen['sha256']=hashlib.sha256(json.dumps({'base':base,'size':size}).encode()).hexdigest()
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'frozen_size_fit.json').write_text(json.dumps(frozen,indent=2)+'\n')
    print('FROZEN SIZE ADJUSTMENTS',size, 'SHA256',frozen['sha256'],flush=True)
    screens=[]
    for n in (3,4,5):
        for pop in ('mixed','shifted'):
            seed=start(SCREEN_BASE,n,pop)
            game_rows,stages=stages_for_games(n,pop,'opponent_action',base,seed,screen,size_offsets=size)
            stats=score(predict_rows(stages,base,size,models=METHODS),game_rows,screen,
                        boot=boot,seed=seed+900,models=METHODS)
            for r in stats:
                r.update(n_players=n,population=pop,active_policy='size_calibrated',
                         games=screen,seed_start=seed)
            screens.extend(stats)
            for action in ('steal','assassinate'):
                r=next(x for x in stats if x['action']==action and x['target']=='all'
                       and x['model']=='opponent_action')
                print('SCREEN',n,pop,action,'stages',r['stages'],'gap',round(r['gap'],3),
                      'brier_delta',round(r['brier_delta_vs_opponent'],4),flush=True)
            write_csv(OUT/'size_development_screen.csv',screens)
    return frozen,screens

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--train',type=int,default=1100)
    ap.add_argument('--screen',type=int,default=500)
    ap.add_argument('--boot',type=int,default=600)
    a=ap.parse_args();run(a.train,a.screen,a.boot)
