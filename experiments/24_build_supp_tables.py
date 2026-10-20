"""Generate supplementary LaTeX tables from frozen empirical CSV summaries."""
from pathlib import Path
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parents[1]
P=R/'manuscript'/'tables_generated.tex'
S=pd.read_csv(R/'results'/'frequency_dependence'/'evolutionary_summary.csv')
D=pd.read_csv(R/'results'/'frequency_dependence'/'payoff_profiles.csv')
fmt=lambda r: f"{100*r:+.2f}"
ci=lambda row,c,lo,hi: f"{fmt(row[c])} [{100*row[lo]:+.2f}, {100*row[hi]:+.2f}]"
lines=[]
lines += [r'\begin{table}[htbp]\centering\scriptsize',
    r'\caption{All four-player frequency-study selection endpoints, in percentage points. Confidence intervals are 95\% seed-clustered bootstrap intervals. Near-null values at $\theta=0.50$ reflect sampling noise; all corresponding simulations had identical trajectories across compositions.}',
    r'\label{tab:s1}',r'\begin{tabular}{llrrr}\toprule',
    r'$\theta$ & Forecast & $\Delta(0)$ & $\Delta(0.5)$ & $\Delta(1)$ \\ \midrule']
for t in [.05,.30,.50]:
 for p in ['empirical','opponent','opponent_action']:
  row=S[(S.players==4)&(S.theta==t)&(S.forecast==p)&(S.reward==1)].iloc[0]
  lines.append(f"{t:.2f} & {p.replace('_',r'\_')} & {ci(row,'rare_advantage','rare_ci_low','rare_ci_high')} & {ci(row,'mid_advantage','mid_ci_low','mid_ci_high')} & {ci(row,'honest_invasion_barrier','barrier_ci_low','barrier_ci_high')} \\\\")
lines += [r'\bottomrule\end{tabular}\end{table}']
lines += [r'\begin{table}[htbp]\centering\scriptsize',
    r'\caption{Per-player win probabilities and action frequencies by four-player table composition under low scepticism. Every row represents 1,200 games; $k=0$ has no bluffer payoff, and $k=4$ has no honest-player payoff.}',
    r'\label{tab:s2}',r'\begin{tabular}{llrrrrr}\toprule',
    r'Forecast & $k$ & $u_H$ & $u_B$ & False claims/game & Attacks/game & Standing interventions/game \\ \midrule']
for p in ['empirical','opponent','opponent_action']:
 for k in range(5):
  row=D[(D.players==4)&(D.theta==.05)&(D.reward==1)&(D.forecast==p)&(D.k_bluffers==k)].iloc[0]
  ph='--' if k==4 else f'{row.payoff_H:.3f}'
  pb='--' if k==0 else f'{row.payoff_B:.3f}'
  lines.append(f"{p.replace('_',r'\_')} & {k} & {ph} & {pb} & {row.bluff_actions_per_game:.2f} & {row.attacks_per_game:.2f} & {row.stood_interventions_per_game:.3f} \\\\")
lines += [r'\bottomrule\end{tabular}\end{table}']
lines += [r'\begin{table}[htbp]\centering\scriptsize',
    r'\caption{Cross-table-size selection endpoints at low scepticism ($\theta=0.05$). Units are percentage points; uncertainty is propagated by resampling whole game-seed clusters.}',
    r'\label{tab:s3}',r'\begin{tabular}{llrr}\toprule',
    r'Players & Forecast & $\Delta(0)$ [95\% CI] & $\Delta(1)$ [95\% CI] \\ \midrule']
for n in [3,5]:
 for p in ['empirical','opponent','opponent_action']:
  row=S[(S.players==n)&(S.theta==.05)&(S.forecast==p)&(S.reward==1)].iloc[0]
  lines.append(f"{n} & {p.replace('_',r'\_')} & {ci(row,'rare_advantage','rare_ci_low','rare_ci_high')} & {ci(row,'honest_invasion_barrier','barrier_ci_low','barrier_ci_high')} \\\\")
lines += [r'\bottomrule\end{tabular}\end{table}']
lines += [r'\begin{table}[htbp]\centering\scriptsize',
    r'\caption{Exploratory intervention-reward sensitivity for four players, low scepticism and the opponent-aware forecast. Reward does not directly modify the agents\' fixed intervention propensity.}',
    r'\label{tab:s4}',r'\begin{tabular}{crr}\toprule',
    r'Reward (coins) & $\Delta(0)$ [95\% CI], pp & $\Delta(0.5)$ [95\% CI], pp \\ \midrule']
for reward in [0,1,2]:
 row=S[(S.players==4)&(S.theta==.05)&(S.forecast=='opponent')&(S.reward==reward)].iloc[0]
 lines.append(f"{reward} & {ci(row,'rare_advantage','rare_ci_low','rare_ci_high')} & {ci(row,'mid_advantage','mid_ci_low','mid_ci_high')} \\\\")
lines += [r'\bottomrule\end{tabular}\end{table}']
P.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('saved',P,len(lines),'lines')
