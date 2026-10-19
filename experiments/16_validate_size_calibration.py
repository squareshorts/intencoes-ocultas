"""Independent final held-out validation for size-dependent action calibration.

Uses fresh seed ranges 6.3m-6.52m, never inspected during fitting. All
criteria are the same as the first 12-stratum test: count >=150, abs gap
<=7 points, Brier delta <=0.01 vs opponent forecast on matching events.
Checkpoints each condition; resume avoids repeated computation. Do not retune
once this dataset has been opened.
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'experiments'))
from action_calibration_common import (predict_rows,score,stages_for_games,summarize_game_counts)
from importlib import util
sp=util.spec_from_file_location('sizecalfit',ROOT/'experiments'/'15_fit_size_calibration.py')
sizefit=util.module_from_spec(sp);sys.modules[sp.name]=sizefit;sp.loader.exec_module(sizefit)
OUT=ROOT/'results'/'action_calibration'
METHODS=('opponent','opponent_action')

def read_csv(path):
    if not path.exists():return []
    with path.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))


def run(games=1300,boot=750,resume=False):
    frozen=json.loads((OUT/'frozen_size_fit.json').read_text())
    base=tuple(frozen['action_block_offsets'])
    size=tuple(frozen['size_block_offsets'])
    if len(size)!=6 or frozen['status']!='size_development_frozen':
        raise ValueError('invalid frozen size model')
    scores=read_csv(OUT/'final_score.csv') if resume else []
    behaviours=read_csv(OUT/'final_policy.csv') if resume else []
    gates=read_csv(OUT/'final_gates.csv') if resume else []
    completed={(int(v['n_players']),v['population']) for v in behaviours}
    for n in (3,4,5):
        for pop in ('mixed','shifted'):
            if (n,pop) in completed:
                print('SKIP checkpoint',n,pop,flush=True);continue
            seed=sizefit.start(sizefit.FINAL_BASE,n,pop)
            game_rows,stages=stages_for_games(n,pop,'opponent_action',base,seed,games,size_offsets=size)
            predictions=predict_rows(stages,base,size,models=METHODS)
            stats=score(predictions,game_rows,games,boot=boot,seed=seed+1999,models=METHODS)
            for r in stats:
                r.update(n_players=n,population=pop,active_policy='size_calibrated',
                         games=games,seed_start=seed,fit_sha256=frozen['sha256'])
            scores.extend(stats)
            behaviours.append({'n_players':n,'population':pop,'games':games,
                               'seed_start':seed,'stages':len(predictions),
                               **summarize_game_counts(game_rows)})
            for action in ('steal','assassinate'):
                r=next(x for x in stats if x['action']==action and x['target']=='all'
                       and x['model']=='opponent_action')
                b=next(x for x in stats if x['action']==action and x['target']=='all'
                       and x['model']=='opponent')
                passed=r['stages']>=150 and abs(r['gap'])<=.07 and r['brier_delta_vs_opponent']<=.01
                gates.append({'n_players':n,'population':pop,'action':action,
                              'stages':r['stages'],'new_gap':r['gap'],'old_gap':b['gap'],
                              'brier_delta':r['brier_delta_vs_opponent'],'passed':int(passed)})
                print('FINAL',n,pop,action,'n',r['stages'],'new gap',round(r['gap'],3),
                      'old gap',round(b['gap'],3),
                      'Brier delta',round(r['brier_delta_vs_opponent'],4),
                      'gate', 'PASS' if passed else 'FAIL',flush=True)
            sizefit.write_csv(OUT/'final_score.csv',scores)
            sizefit.write_csv(OUT/'final_policy.csv',behaviours)
            sizefit.write_csv(OUT/'final_gates.csv',gates)
            # Every arm gets its own raw predictions checkpoint; no hidden state.
            sizefit.write_csv(OUT/f'final_stages_{n}_{pop}.csv',
                              [{'game_id':r['game_id'],'seed':seed+r['game_id'],
                                'action':r['action'],'target_influences':r['target_influences'],
                                'stood':r['stood'],**{m:r[m] for m in METHODS}}
                               for r in predictions])
    decision={'version':3,'frozen_sha256':frozen['sha256'],
              'gate':'PASS' if len(gates)==12 and all(int(r['passed']) for r in gates) else 'FAIL',
              'passed':sum(int(r['passed']) for r in gates), 'total':len(gates),
              'criteria':'12 in-policy action strata, n>=150, abs gap<=0.07, Brier delta vs opponent<=0.01',
              'interpretation':'Even PASS would only validate simulation calibration, not evolutionary hypotheses or real people.'}
    (OUT/'final_decision.json').write_text(json.dumps(decision,indent=2)+'\n',encoding='utf-8')
    print('FINAL HELDOUT DECISION',decision,flush=True)
    return decision

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--games',type=int,default=1300)
    ap.add_argument('--boot',type=int,default=750)
    ap.add_argument('--resume',action='store_true')
    a=ap.parse_args();run(a.games,a.boot,a.resume)
