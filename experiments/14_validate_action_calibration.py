"""Sealed 3/4/5-player, mixed/shifted, in-policy validation of frozen fit.

This script ONLY reads the frozen JSON generated on different seeds by 13.
It never modifies coefficients. Each method is scored on identical snapshots
under each active policy; the two active policies also induce different games.
Run: python experiments/14_validate_action_calibration.py --games 1400
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'experiments'))
from action_calibration_common import (MODELS, predict_rows, score,
                                       stages_for_games, summarize_game_counts)
OUT=ROOT/'results'/'action_calibration'


def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not rows: return
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def read_csv(path):
    if not path.exists():
        return []
    with path.open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f))


def run(games=1400,boot=750,resume=False):
    frozen=json.loads((OUT/'frozen_fit.json').read_text(encoding='utf-8'))
    if frozen['status']!='development_frozen' or len(frozen['offsets'])!=4:
        raise ValueError('must supply a valid frozen development fit')
    offsets=tuple(frozen['offsets'])
    report=read_csv(OUT/'heldout_score.csv') if resume else []
    behaviour=read_csv(OUT/'heldout_policy.csv') if resume else []
    gates=read_csv(OUT/'heldout_gates.csv') if resume else []
    raw=[]
    completed={(int(row['n_players']),row['population'],row['active_policy'])
               for row in behaviour}
    for n in (3,4,5):
        for pop in ('mixed','shifted'):
            start=3_000_000+n*100_000+(20_000 if pop=='shifted' else 0)
            for policy in ('opponent','opponent_action'):
                if (n,pop,policy) in completed:
                    print('RESUME SKIP',n,pop,policy,flush=True)
                    continue
                games_rows,samples=stages_for_games(n,pop,policy,offsets,start,games)
                rows=predict_rows(samples,offsets)
                stats=score(rows,games_rows,games,boot=boot,seed=start+700)
                for r in stats:
                    r.update(n_players=n,population=pop,active_policy=policy,
                             games=games,seed_start=start)
                report.extend(stats)
                counts=summarize_game_counts(games_rows)
                behaviour.append({'n_players':n,'population':pop,'active_policy':policy,
                                  'games':games,'seed_start':start,'stages':len(rows),**counts})
                for action in ('steal','assassinate'):
                    r=next(t for t in stats if t['action']==action and
                           t['target']=='all' and t['model']=='opponent_action')
                    baseline=next(t for t in stats if t['action']==action and
                                  t['target']=='all' and t['model']=='opponent')
                    print('TEST',n,pop,policy,action,'n',r['stages'],
                          'gap',round(r['gap'],3), 'old_gap',round(baseline['gap'],3),
                          'brier_delta',round(r['brier_delta_vs_opponent'],4),flush=True)
                    if policy=='opponent_action':
                        # Predeclared action-conditional acceptance criteria:
                        # enough samples; point-calibration within +/- 7 pp;
                        # no material (>0.01) Brier degradation vs old on same events.
                        gate=(r['stages']>=150 and abs(r['gap'])<=0.07 and
                              r['brier_delta_vs_opponent']<=0.01)
                        gates.append({'n_players':n,'population':pop,'action':action,
                                      'stage_count':r['stages'],'gap':r['gap'],
                                      'brier_delta':r['brier_delta_vs_opponent'],
                                      'passed':int(gate)})
                # Raw predictions carry no opponent private cards.
                raw.extend({'n_players':n,'population':pop,'active_policy':policy,
                            'game_id':r['game_id'],'seed':start+r['game_id'],
                            'action':r['action'],'target_influences':r['target_influences'],
                            'stood':r['stood'], **{m:r[m] for m in MODELS}}
                           for r in rows)
                write_csv(OUT/'heldout_score.csv',report)
                write_csv(OUT/'heldout_policy.csv',behaviour)
                write_csv(OUT/'heldout_gates.csv',gates)
                write_csv(ROOT/'results'/'raw'/'action_calibration_remaining_stages.csv',raw)
    # The original long job was terminated after seven checkpointed arms;
    # in resume mode, complete aggregate summaries without fabricating raw
    # per-stage data for the already checkpointed arms.
    decision={'frozen_fit_sha256':frozen['sha256'], 'stage_count':sum(int(x['stages']) for x in behaviour),
              'games_per_condition':games,
              'raw_stage_export_partial_after_resume':bool(resume),
              'gate': 'PASS' if len(gates)==12 and all(int(r['passed']) for r in gates) else 'FAIL',
              'criteria':'12 independent in-policy action strata (3/4/5 x mixed/shifted x steal/assassinate): n>=150, abs(mean forecast error)<=0.07, Brier delta vs opponent on same events<=0.01',
              'passed_strata':sum(int(r['passed']) for r in gates),'total_strata':len(gates),
              'interpretation':'PASS permits considering further simulations; does not establish human behaviour or evolutionary findings'}
    (OUT/'heldout_decision.json').write_text(json.dumps(decision,indent=2)+'\n',encoding='utf-8')
    print('FROZEN HELDOUT GATE',decision['gate'],decision['passed_strata'],'/',decision['total_strata'],flush=True)
    return report,behaviour,gates

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--games',type=int,default=1400)
    ap.add_argument('--boot',type=int,default=750)
    ap.add_argument('--resume',action='store_true',help='resume from saved completed-arm CSV checkpoints')
    args=ap.parse_args()
    run(args.games,args.boot,args.resume)
