"""Independent 3/5-player in-policy calibration and opportunity holdout.

This extends the 4-player endogenous gate without refitting any parameters.
Seeds have no overlap with earlier calibration or policy-gate samples.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

path=ROOT/'experiments'/'10_endogenous_opportunity.py'
spec=importlib.util.spec_from_file_location('endogenous_policy_gate',path)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


def main(args):
    cals,conds=[],[]
    for n in (3,5):
        for pop in ('mixed','shifted'):
            for belief in ('empirical','opponent_pool','opponent'):
                for dose in (0.,1.):
                    s=(pop,belief,dose,1,'aware',True)
                    summary,cal,_,_=mod.run_scenario(s,args.games,args.boot,
                        seed0=args.seed0+n*10000,n_players=n)
                    conds.append(summary);cals+=cal
                    chosen=next(x for x in cal if x['model']==belief)
                    print('SIZE',n,pop,belief,dose,'stages',summary['stages'],
                          'intervention_offers',round(summary['intervention_offers_per_game'],3),
                          'forecast_gap',round(chosen['calibration_gap'],3),
                          'Brier',round(chosen['brier'],3),flush=True)
                    mod.write_csv(ROOT/'results'/'policy_gate'/'size_conditions.csv',conds)
                    mod.write_csv(ROOT/'results'/'policy_gate'/'size_calibration.csv',cals)
    return conds,cals

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--games',type=int,default=500)
    ap.add_argument('--boot',type=int,default=600)
    ap.add_argument('--seed0',type=int,default=820000)
    main(ap.parse_args())
