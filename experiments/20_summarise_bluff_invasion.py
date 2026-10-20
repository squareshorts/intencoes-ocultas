"""Summarize paired rare-bluffer trials with Holm correction and checks.

Run after experiments/19_bluff_invasion.py finishes. No refitting.
"""
import argparse
import csv
import math
from pathlib import Path
import numpy as np
from scipy.stats import binomtest

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results'/'bluff_invasion'
POLICIES=('empirical','opponent','opponent_action')
THETAS=(.05,.30,.50)


def read_csv(path):
    with path.open(newline='',encoding='utf-8') as f:
        return [{k:int(v) for k,v in row.items()} for row in csv.DictReader(f)]


def main():
    a=argparse.ArgumentParser()
    a.add_argument('--boots',type=int,default=2500)
    args=a.parse_args()
    rows=[]
    for coupled in [False,True]:
        for n in (3,4,5):
            for theta in THETAS:
                for policy in POLICIES:
                    file=OUT/f"paired{'_coupled' if coupled else ''}_n{n}_theta{theta:.2f}_{policy}.csv"
                    if not file.exists():
                        continue
                    d=read_csv(file)
                    wins=np.array([r['delta_win'] for r in d],float)
                    nr=len(d)
                    if coupled:
                        unbluffed=[r for r in d if r['mutant_focal_bluffs']==0]
                        assert all(r['delta_win']==0 and r['baseline_turns']==r['mutant_turns'] for r in unbluffed)
                    plus=sum(wins==1);minus=sum(wins==-1)
                    p=binomtest(plus,plus+minus).pvalue if plus+minus else 1.0
                    rng=np.random.default_rng(int(n*100000+theta*1000+sum(map(ord,policy))+(1000 if coupled else 0)))
                    boots=np.empty(args.boots,float)
                    for j in range(args.boots):
                        boots[j]=wins[rng.integers(0,nr,size=nr)].mean()
                    lo,hi=np.quantile(boots,[.025,.975])
                    mean=lambda name:sum(r[name] for r in d)/nr
                    rows.append(dict(n_players=n,theta=theta,forecast=policy,coupling='strict' if coupled else 'ordinary',
                        games=nr,control_win=mean('baseline_win'),mutant_win=mean('mutant_win'),
                        delta_win=float(wins.mean()),ci_low=float(lo),ci_high=float(hi),p_exact=p,
                        discordant_plus=plus,discordant_minus=minus,
                        bluff_games=sum(r['mutant_focal_bluffs']>0 for r in d),
                        bluff_actions_per_game=mean('mutant_focal_bluffs'),
                        bluff_actions_challenged_per_game=mean('mutant_focal_bluffs_challenged'),
                        bluff_actions_succeeded_per_game=mean('mutant_focal_bluffs_succeeded'),
                        attacks_control=mean('baseline_attack_actions'),attacks_mutant=mean('mutant_attack_actions'),
                        third_party_offers_control=mean('baseline_intervention_offers'),
                        third_party_offers_mutant=mean('mutant_intervention_offers')))
    # Prespecified nine primary tests: STRICT coupling, four players, 3 forecasts x 3 thresholds.
    primary=[row for row in rows if row['coupling']=='strict' and row['n_players']==4]
    if len(primary)!=9: print('WARNING incomplete primary',len(primary))
    sorted_rows=sorted(primary,key=lambda r:r['p_exact'])
    rolling=0
    m=len(sorted_rows)
    for rank,row in enumerate(sorted_rows):
        rolling=max(rolling,min(1.0,(m-rank)*row['p_exact']))
        row['holm_p']=rolling
        row['holm_decision']='significant' if rolling<.05 else 'inconclusive'
    keys=list(rows[0]) + ['holm_p','holm_decision']
    keys=list(dict.fromkeys(keys))
    with (OUT/'summary.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore')
        w.writeheader();w.writerows(rows)
    print('STRICT COUPLED, FOUR PLAYERS')
    for row in sorted(primary,key=lambda r:(r['theta'],r['forecast'])):
        print(f"theta={row['theta']:.2f} {row['forecast']:15s} win={row['mutant_win']:.3f} "
              f"control={row['control_win']:.3f} delta={row['delta_win']:+.4f} "
              f"CI=[{row['ci_low']:+.4f}, {row['ci_high']:+.4f}] "
              f"holm={row['holm_p']:.4g} bluffs/game={row['bluff_actions_per_game']:.3f}")
    print('STRICT COUPLED, LOW SCEPTICISM, OTHER SIZES')
    for row in rows:
        if row['coupling']=='strict' and row['theta']==.05 and row['n_players']!=4:
            print(row['n_players'],row['forecast'],f"delta={row['delta_win']:+.4f}",
                  f"CI=[{row['ci_low']:+.4f},{row['ci_high']:+.4f}]",'bluffs',f"{row['bluff_actions_per_game']:.3f}")
    print('TOTAL games',sum(2*r['games'] for r in rows))

if __name__=='__main__':main()
