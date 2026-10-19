"""Paired game-seed contrasts and stage reliability for Experiment 10.

All tests are diagnostic, not preregistered and not estimates of evolutionary
fixation. Comparisons of predictions ON a common stage use paired errors;
comparisons of outcomes ACROSS decision policies use game-seed paired arms,
not per-stage matching (the actions and stage distributions differ).
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results'/'policy_gate'
RAW = ROOT/'results'/'raw'
METRICS = ('attacks','block_stages','intervention_offers',
           'intervention_claims','intervention_stands','first_turn_uptake','turns')
PREDICTORS = ('empirical','opponent_prior','opponent_pool','opponent')


def read():
    games = pd.read_csv(RAW/'policy_gate_games.csv')
    stages = pd.read_csv(RAW/'policy_gate_stages.csv')
    conditions = pd.read_csv(OUT/'conditions.csv')
    if games.duplicated(['scenario','game_id']).any():
        raise ValueError('duplicate game IDs in raw records')
    if (stages['stood'].isna().any() or
            not stages['stood'].isin([0,1]).all()):
        raise ValueError('invalid block stage truth')
    return games, stages, conditions


def contrasts(games, conditions, boot, rng_seed):
    index = {tuple(r[['population','belief','opportunity_dose','reward',
                      'anticipation','intervention_enabled']]):r['scenario']
             for _,r in conditions.iterrows()}
    arrays = {s:df.sort_values('game_id').set_index('game_id')
              for s,df in games.groupby('scenario', sort=False)}
    rng = np.random.default_rng(rng_seed)
    output = []

    def one(pop, belief, dose0, dose1, reward0, reward1,
            anticipation0, anticipation1, enabled0, enabled1, kind):
        a = index.get((pop,belief,dose0,reward0,anticipation0,enabled0))
        b = index.get((pop,belief,dose1,reward1,anticipation1,enabled1))
        if a is None or b is None:
            return
        left, right = arrays[a].align(arrays[b], join='inner', axis=0)
        if len(left) != len(arrays[a]) or len(right) != len(arrays[b]):
            raise ValueError('seed or game ID mismatch in paired contrasts')
        # All arms have common initial RNG seed, deck and starting player.
        gids = left.index.to_numpy()
        if not np.array_equal(gids, np.arange(len(gids))):
            raise ValueError('game_id not sequential')
        samples = rng.integers(0,len(gids),size=(boot,len(gids)))
        for metric in METRICS:
            delta = (right[metric]-left[metric]).to_numpy(float)
            bs = delta[samples].mean(axis=1)
            lo,hi = np.quantile(bs, [.025,.975])
            output.append({'contrast':kind,'population':pop,'belief':belief,
                           'opportunity_dose_before':dose0,'opportunity_dose_after':dose1,
                           'reward_before':reward0,'reward_after':reward1,
                           'anticipation_before':anticipation0,'anticipation_after':anticipation1,
                           'enabled_before':enabled0,'enabled_after':enabled1,
                           'scenario_before':a,'scenario_after':b,
                           'games':len(gids), 'metric':metric,
                           'value_before':float(left[metric].mean()),
                           'value_after':float(right[metric].mean()),
                           'difference_after_minus_before':float(delta.mean()),
                           'ci_low':float(lo),'ci_high':float(hi)})

    for pop in ('mixed','shifted'):
        for belief in ('empirical','opponent'):
            for dose in (0.,1.):
                one(pop,belief,dose,dose,1,1,'aware','blind',True,True,'suppress_anticipation')
                one(pop,belief,dose,dose,1,1,'blind','blind',False,True,'enable_real_intervention')
                one(pop,belief,dose,dose,0,2,'aware','aware',True,True,'raise_reward_0_to_2')
            one(pop,belief,0.,1.,1,1,'aware','aware',True,True,'encourage_truthful_steals')
    return output


def stage_strata(stages, conditions, boot=800, seed=8484):
    # Breakdown for active policy, both naturally chosen and randomly
    # prompted truthful-steal stages. Confidence intervals are game-clustered.
    all_output=[]; bins=[]; rng=np.random.default_rng(seed)
    keep=conditions[(conditions['population'].isin(['mixed','shifted'])) &
                    (conditions.reward==1) &
                    (conditions.anticipation=='aware') &
                    (conditions.intervention_enabled) &
                    (conditions.belief.isin(['empirical','opponent']))]
    for _,conf in keep.iterrows():
        sid=conf['scenario']; source=stages[stages['scenario']==sid]
        n_games=int(conf['games'])
        for forced in (0,1):
            sub=source[source.forced==forced]
            if sub.empty: continue
            ids=sub['game_id'].to_numpy(int)
            y=sub['stood'].to_numpy(float)
            counts=np.bincount(ids,minlength=n_games)
            draw=rng.integers(0,n_games,size=(boot,n_games))
            denom=np.maximum(1,counts[draw].sum(axis=1))
            ref=(sub['empirical'].to_numpy(float)-y)**2
            for method in PREDICTORS:
                p=sub[method].to_numpy(float)
                loss=(p-y)**2
                gap=p-y
                per_game=np.bincount(ids,weights=gap,minlength=n_games)
                gap_ci=np.quantile(per_game[draw].sum(axis=1)/denom,[.025,.975])
                delta=loss-ref
                by_game=np.bincount(ids,weights=delta,minlength=n_games)
                delta_ci=np.quantile(by_game[draw].sum(axis=1)/denom,[.025,.975])
                all_output.append({'scenario':sid,'population':conf.population,
                                   'belief':conf.belief,'opportunity_dose':conf.opportunity_dose,
                                   'forced_stage':forced,'model':method,
                                   'is_active':method==conf.belief,'stages':len(sub),
                                   'predicted':float(p.mean()),'actual':float(y.mean()),
                                   'gap':float(gap.mean()),
                                   'gap_ci_low':float(gap_ci[0]),'gap_ci_high':float(gap_ci[1]),
                                   'brier':float(loss.mean()),
                                   'brier_delta_vs_empirical':float(delta.mean()),
                                   'delta_ci_low':float(delta_ci[0]),
                                   'delta_ci_high':float(delta_ci[1])})
                if method != conf.belief: continue
                for idx in range(5):
                    lo,hi=idx/5,(idx+1)/5
                    subset=(p>=lo)&((p<hi) if idx<4 else (p<=hi))
                    n=int(subset.sum())
                    bins.append({'scenario':sid,'population':conf.population,
                                 'belief':conf.belief,'opportunity_dose':conf.opportunity_dose,
                                 'forced_stage':forced,'bin_low':lo,'bin_high':hi,'stages':n,
                                 'predicted':float(p[subset].mean()) if n else None,
                                 'actual':float(y[subset].mean()) if n else None})
    return all_output,bins


def action_calibration(stages, conditions, boot=800, seed=9951):
    """Action-specific forecast error; do not conceal offsets by pooling actions."""
    rng=np.random.default_rng(seed)
    output=[]
    keep=conditions[(conditions.population.isin(['mixed','shifted'])) &
                    (conditions.reward==1) & (conditions.anticipation=='aware') &
                    (conditions.intervention_enabled) &
                    (conditions.belief.isin(['empirical','opponent']))]
    for _,conf in keep.iterrows():
        data=stages[stages.scenario==conf.scenario]
        n_games=int(conf.games)
        for action in sorted(data.action.unique()):
            for forced in (0,1):
                sub=data[(data.action==action)&(data.forced==forced)]
                if len(sub)<10: continue
                ids=sub.game_id.to_numpy(int)
                y=sub.stood.to_numpy(float)
                p=sub[conf.belief].to_numpy(float)
                reference=sub.empirical.to_numpy(float)
                diff=(p-y)**2-(reference-y)**2
                gap=p-y
                weights=np.bincount(ids, minlength=n_games)
                samples=rng.integers(0,n_games,size=(boot,n_games))
                den=np.maximum(1,weights[samples].sum(axis=1))
                def bsc(sample_weights):
                    per_game=np.bincount(ids,weights=sample_weights,minlength=n_games)
                    return np.quantile(per_game[samples].sum(axis=1)/den,[.025,.975])
                ci_gap=bsc(gap);ci_delta=bsc(diff)
                output.append({'population':conf.population,'belief':conf.belief,
                    'opportunity_dose':conf.opportunity_dose,'scenario':conf.scenario,
                    'action':action,'forced':forced,'stages':len(sub),
                    'predicted':float(p.mean()),'actual':float(y.mean()),
                    'gap':float(gap.mean()),'gap_ci_low':float(ci_gap[0]),
                    'gap_ci_high':float(ci_gap[1]),
                    'brier':float(np.mean((p-y)**2)),
                    'delta_vs_empirical':float(diff.mean()),
                    'delta_ci_low':float(ci_delta[0]),
                    'delta_ci_high':float(ci_delta[1])})
    return output


def write_csv(path, rows):
    if not rows: return
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as fh:
        writer=csv.DictWriter(fh,fieldnames=list(dict.fromkeys(k for row in rows for k in row)),lineterminator="\n")
        writer.writeheader();writer.writerows(rows)


def run(boot=800):
    games, stages, cond=read()
    cs=contrasts(games,cond,boot,80880)
    ss,bs=stage_strata(stages,cond,boot=boot)
    acts=action_calibration(stages,cond,boot=boot)
    write_csv(OUT/'contrasts.csv',cs)
    write_csv(OUT/'stage_strata.csv',ss)
    write_csv(OUT/'reliability_bins.csv',bs)
    write_csv(OUT/'action_calibration.csv',acts)
    print('paired contrasts:',len(cs),'stage strata:',len(ss),'reliability bins:',len(bs))
    for pop in ('mixed','shifted'):
        for metric in ('attacks','intervention_offers','intervention_stands'):
            q=[r for r in cs if r['population']==pop and r['belief']=='opponent'
               and r['contrast']=='suppress_anticipation' and r['opportunity_dose_before']==0
               and r['metric']==metric][0]
            print(pop,'anticipation effect',metric,f"{q['difference_after_minus_before']:+.3f}",
                  f"[{q['ci_low']:+.3f},{q['ci_high']:+.3f}]")
    for pop in ('mixed','shifted'):
        active=cond[(cond.population==pop)&(cond.belief=='opponent') &
                    (cond.opportunity_dose==0)&(cond.reward==1)&
                    (cond.anticipation=='aware') & (cond.intervention_enabled)]
        print(pop,'natural intervention claims',int(round(float(active.iloc[0]['intervention_claims_per_game'])*float(active.iloc[0]['games']))))
    return cs,ss,bs


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--boot',type=int,default=800)
    args=ap.parse_args();run(args.boot)
