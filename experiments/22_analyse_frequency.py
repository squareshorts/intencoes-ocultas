"""Analyze held-out frequency profiles without fitting agent parameters.

Produces per-type payoffs, n-player replicator selection curves, finite
population fixation sensitivity and GAME-seed clustered bootstrap intervals.
All calculations are conditional model extrapolations, not observed births.
"""
from __future__ import annotations
import argparse, csv, json, math, sys
from pathlib import Path
from scipy.optimize import brentq
from scipy.special import comb
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from intencoes.egta import PayoffTable, fixation_probability
DATA=ROOT/'results'/'frequency_dependence'
FIG=ROOT/'figures'/'frequency_dependence'
OUT=ROOT/'results'/'frequency_dependence'
THETAS=(.05,.30,.50);POLICIES=('empirical','opponent','opponent_action')
LABELS={'empirical':'Pooled-empirical','opponent':'Opponent-aware','opponent_action':'Action-specific'}


def load(n,theta,policy,reward):
    rs=[]
    for k in range(n+1):
        f=DATA/f'n{n}_t{theta:.2f}_{policy}_r{reward}_k{k}.csv'
        if not f.exists():return None
        df=pd.read_csv(f)
        if not (df.k_bluffers==k).all() or not (df.seed_id.values==np.arange(len(df))).all():
            raise ValueError('inconsistent frequency table '+str(f))
        rs.append(df)
    if len({len(x) for x in rs})!=1:raise ValueError('unequal replicates across profiles')
    # Paired seed checks: n_players common and same deck RNG across k.
    if any(not np.array_equal(x.seed.values,rs[0].seed.values) for x in rs[1:]):
        raise ValueError('seed not paired across compositions')
    return rs


def per_player(payoff,n):
    # payoff shape (n+1,2): total per-game wins H,B in each profile
    u_h=np.divide(payoff[:,0],np.arange(n,-1,-1),out=np.full(n+1,np.nan),where=np.arange(n,-1,-1)>0)
    u_b=np.divide(payoff[:,1],np.arange(n+1),out=np.full(n+1,np.nan),where=np.arange(n+1)>0)
    return u_h,u_b


def selection(u_h,u_b,n,x):
    """B versus H fitness at population prevalence x in large panmictic population.

    Opponents of focal B: j of n-1 B -> profile j+1.
    Opponents of focal H: j B -> profile j.
    """
    x=np.asarray(x,dtype=float)
    coef=np.array([math.comb(n-1,j) for j in range(n)],float)
    weights=np.array([coef[j]*x**j*(1-x)**(n-1-j) for j in range(n)])
    d=np.asarray([u_b[j+1]-u_h[j] for j in range(n)])
    return np.tensordot(d,weights,axes=(0,0))


def roots(u_h,u_b,n):
    xgrid=np.linspace(0,1,4001)
    v=selection(u_h,u_b,n,xgrid)
    root_list=[]
    for idx in range(len(xgrid)-1):
        if v[idx]*v[idx+1]<0:
            r=brentq(lambda t:float(selection(u_h,u_b,n,t)),xgrid[idx],xgrid[idx+1]);root_list.append(float(r))
    def derivative(x):
        h=.00001
        return float((selection(u_h,u_b,n,min(1,x+h))-selection(u_h,u_b,n,max(0,x-h)))/(min(1,x+h)-max(0,x-h)))
    return [{'prevalence':r,'stability':'stable' if derivative(r)<0 else 'unstable'} for r in root_list]


def evolve_fixation(u_h,u_b,n,M=30,alpha=5):
    # Build exact existing code pathway for symmetric multi-player payoffs.
    counts={}
    for k in range(n+1):
        counts[tuple([0]*(n-k)+[1]*k)]=np.array([u_h[k]*(n-k) if k<n else 0.,u_b[k]*k if k>0 else 0.])*30000
    # rounding total per-game counts immaterial (<1e-6), keep float to avoid quantization.
    tab=PayoffTable(2,n,counts,30000)
    rho_b=fixation_probability(tab,1,0,M,alpha)
    rho_h=fixation_probability(tab,0,1,M,alpha)
    return float(rho_b),float(rho_h),float(rho_b/(rho_b+rho_h))


def bootstrap(rs,boots,seed):
    n=len(rs)-1;N=len(rs[0]);rng=np.random.default_rng(seed)
    # One cluster is a SEED across all compositions, not an individual event.
    # For in-experiment seeds, all k profiles share a shuffled deck RNG seed;
    # resampling the same index across profiles retains their dependence.
    cells=np.stack([np.column_stack((x.h_wins.to_numpy(),x.b_wins.to_numpy())) for x in rs])
    endpoint=np.empty((boots,3));rank=np.empty((boots,3));interior=np.zeros(boots,bool)
    for b in range(boots):
        ind=rng.integers(0,N,N)
        counts=cells[:,ind,:].mean(axis=1)
        h,z=per_player(counts,n)
        endpoint[b]=[z[1]-h[0],float(selection(h,z,n,.5)),z[n]-h[n-1]]
        rank[b]=evolve_fixation(h,z,n,30,5)
        # boundary selection signs are sufficient for an intermediate
        # crossing with B invasion AND H invasion under continuity.
        interior[b]=(endpoint[b,0]>0 and endpoint[b,2]<0)
    return endpoint,rank,interior


def run(boots):
    output=[];profiles=[];grid_curves=[];plot_data={}
    conditions=[(n,t,p,1) for n in [4] for t in THETAS for p in POLICIES]
    conditions += [(n,.05,p,1) for n in [3,5] for p in POLICIES]
    conditions += [(4,.05,'opponent',r) for r in [0,2]]
    for n,t,p,r in conditions:
        rs=load(n,t,p,r)
        if rs is None:continue
        N=len(rs[0]);tot=np.array([[x.h_wins.mean(),x.b_wins.mean()] for x in rs]);h,b=per_player(tot,n)
        seedsig=n*100000+int(t*100)*1000+POLICIES.index(p)*100+r
        bs,fix_bs,stable=bootstrap(rs,boots,seed=seedsig)
        low,mid,high=bs.mean(axis=0)
        deltas=[b[1]-h[0],float(selection(h,b,n,.5)),b[n]-h[n-1]]
        fix=evolve_fixation(h,b,n,30,5)
        rr=roots(h,b,n)
        row=dict(players=n,theta=t,forecast=p,reward=r,games_per_profile=N,games_total=N*(n+1),
                 rare_advantage=deltas[0],rare_ci_low=np.quantile(bs[:,0],.025),rare_ci_high=np.quantile(bs[:,0],.975),
                 mid_advantage=deltas[1],mid_ci_low=np.quantile(bs[:,1],.025),mid_ci_high=np.quantile(bs[:,1],.975),
                 honest_invasion_barrier=deltas[2],barrier_ci_low=np.quantile(bs[:,2],.025),barrier_ci_high=np.quantile(bs[:,2],.975),
                 stable_interior_prob=stable.mean(),eq_roots_json=json.dumps(rr),
                 fixation_B=fix[0],fixation_H=fix[1],alpha_rank_B=fix[2],
                 rankB_ci_low=np.quantile(fix_bs[:,2],.025),rankB_ci_high=np.quantile(fix_bs[:,2],.975),
                 draw_count=sum(int(x.draw.sum()) for x in rs))
        output.append(row)
        for k,df in enumerate(rs):
            profiles.append(dict(players=n,theta=t,forecast=p,reward=r,k_bluffers=k,games=N,
                wins_B=int(df.b_wins.sum()),wins_H=int(df.h_wins.sum()),draws=int(df.draw.sum()),
                payoff_B=float(b[k]) if k>0 else None,payoff_H=float(h[k]) if k<n else None,
                gap_B_minus_H=float(b[k]-h[k]) if 0<k<n else None,
                bluff_actions_per_game=float(df.false_action_claims.mean()),
                attacks_per_game=float(df.attacks.mean()),
                third_party_offers_per_game=float(df.intervention_offers.mean()),
                stood_interventions_per_game=float(df.interventions_stood.mean()),
                turns_per_game=float(df.turns.mean())))
        x=np.linspace(0,1,201)
        plot_data[(n,t,p,r)]=dict(x=x,d=selection(h,b,n,x),
                                  h=h,b=b,ci_boot=bs)
        for x0,dx in zip(x,selection(h,b,n,x)):
            grid_curves.append(dict(players=n,theta=t,forecast=p,reward=r,prevalence=float(x0),selection_B_minus_H=float(dx)))
        print('ANALYSED',n,t,p,r,'rare',f'{deltas[0]:+.4f}',
            'mid',f'{deltas[1]:+.4f}','rare-Hinv',f'{deltas[2]:+.4f}',
            'rankB',f'{fix[2]:.3f}','roots',rr,flush=True)
    if not output:raise RuntimeError('no completed data')
    pd.DataFrame(output).to_csv(OUT/'evolutionary_summary.csv',index=False)
    pd.DataFrame(profiles).to_csv(OUT/'payoff_profiles.csv',index=False)
    pd.DataFrame(grid_curves).to_csv(OUT/'selection_curves.csv',index=False)
    FIG.mkdir(exist_ok=True,parents=True)
    # Figure 1: primary n4 selection gradient vs population frequency by scepticism.
    fig,axes=plt.subplots(1,3,figsize=(12.9,3.65),sharey=True)
    pal=['#2f5e8b','#ac5a3d','#398365']
    for ax,theta in zip(axes,THETAS):
        for idx,p in enumerate(POLICIES):
            z=plot_data.get((4,theta,p,1))
            if not z:continue
            ax.plot(z['x'],100*z['d'],color=pal[idx],lw=2,label=LABELS[p])
            # Seed-clustered bootstrap CI for the entire frequency curve.
            # A large number of plot simulations was avoided; these bands
            # quantify uncertainty in the empirical profile payoff table.
            table=load(4,theta,p,1)
            N=len(table[0]);rng_plot=np.random.default_rng(9300+int(theta*100)+idx)
            group_b=np.stack([q.b_wins.to_numpy() for q in table])
            group_h=np.stack([q.h_wins.to_numpy() for q in table])
            wgt=np.array([math.comb(3,j)*z['x']**j*(1-z['x'])**(3-j) for j in range(4)])
            curves=[]
            for bb in range(500):
                select_idx=rng_plot.integers(0,N,N)
                wb=group_b[:,select_idx].mean(axis=1)
                wh=group_h[:,select_idx].mean(axis=1)
                delta=np.array([wb[j+1]/(j+1)-wh[j]/(4-j) for j in range(4)])
                curves.append(delta@wgt)
            limits=np.quantile(np.asarray(curves),[.025,.975],axis=0)
            ax.fill_between(z['x'],100*limits[0],100*limits[1],color=pal[idx],alpha=.10,lw=0)
        ax.axhline(0,lw=.9,color='#333333',ls=':')
        ax.set_title(f'Scepticism  $\\theta={theta:.2f}$',fontsize=11)
        ax.set_xlabel('Population frequency of bluffers',fontsize=9)
        ax.grid(alpha=.12)
    axes[0].set_ylabel('Selection difference (pp in win probability)',fontsize=9)
    axes[0].legend(loc='upper right',fontsize=7,frameon=False)
    fig.suptitle('Frequency-dependent payoff differences in four-player games',y=1.04,fontsize=12)
    fig.tight_layout()
    fig.savefig(FIG/'figure1_selection_by_scepticism.pdf',bbox_inches='tight')
    fig.savefig(FIG/'figure1_selection_by_scepticism.png',dpi=210,bbox_inches='tight')
    plt.close(fig)
    # Figure 2: within-match payoff by #bluffers, 4-player low scepticism.
    fig,ax=plt.subplots(figsize=(7.2,4.4))
    for i,p in enumerate(POLICIES):
        z=plot_data.get((4,.05,p,1))
        if z is None:continue
        k=np.arange(5)
        ax.plot(k[1:],100*z['b'][1:],ls='-',marker=['o','s','D'][i],color=pal[i],label=LABELS[p]+' bluffer')
        ax.plot(k[:4],100*z['h'][:4],ls='--',marker='.',color=pal[i],alpha=.65,label=LABELS[p]+' honest')
    ax.set_xticks(np.arange(5));ax.set_xlabel('Number of bluffers at the table')
    ax.set_ylabel('Per-player probability of winning (%)')
    ax.set_title('Empirical game payoffs, low scepticism ($\\theta=.05$)')
    ax.grid(alpha=.12)
    ax.legend(fontsize=7,ncol=2,loc='upper right',frameon=False)
    fig.tight_layout();fig.savefig(FIG/'figure2_composition_payoffs.pdf',bbox_inches='tight');fig.savefig(FIG/'figure2_composition_payoffs.png',dpi=210,bbox_inches='tight');plt.close(fig)
    # Figure 3: attacks and interventions by profile at low scepticism.
    fig,axes=plt.subplots(1,2,figsize=(9.8,3.8))
    low=pd.DataFrame(profiles)
    low=low[(low.players==4)&(low.theta==.05)&(low.reward==1)]
    for idx,p in enumerate(POLICIES):
        df=low[low.forecast==p].sort_values('k_bluffers')
        for ax,col in zip(axes,['attacks_per_game','stood_interventions_per_game']):
            ax.plot(df.k_bluffers,df[col],marker='o',color=pal[idx],label=LABELS[p])
    for ax,title in zip(axes,['Steals and Sombra attacks','Successful third-party interventions']):
        ax.set_title(title,fontsize=10);ax.set_xlabel('Number of bluffers at table')
        ax.set_xticks(np.arange(5));ax.grid(alpha=.15)
    axes[0].set_ylabel('Events per completed game')
    axes[0].legend(fontsize=7,frameon=False)
    fig.tight_layout();fig.savefig(FIG/'figure3_attack_and_protection.pdf',bbox_inches='tight');fig.savefig(FIG/'figure3_attack_and_protection.png',dpi=210,bbox_inches='tight');plt.close(fig)
    (OUT/'ANALYSIS_PROTOCOL.md').write_text('Computed using seed-clustered bootstrap resampling across strategy profiles. Invasion into honest population: u_B(1)-u_H(0). Invasion of honest into bluffing population: u_H(n-1)-u_B(n). Replicator payoff function averages opponent composition under binomial mixing. Finite-population Fermi pairwise comparison: M=30, intensity alpha=5; no empirical selection rate. Perfect defence of neutrality cannot be proven with a nonsignificant test.\n',encoding='utf-8')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--boots',type=int,default=1500);args=ap.parse_args();run(args.boots)
