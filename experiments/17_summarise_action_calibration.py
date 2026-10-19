"""Print the frozen action-specific outcomes without rerunning simulations."""
import json
from pathlib import Path
import pandas as pd
P=Path(__file__).resolve().parents[1]/'results'/'action_calibration'
for prefix,title in (('heldout','First 4-player-trained model: 16,800 games'),
                     ('final','Size-aware model: 7,800 games')):
    decision=json.loads((P/('heldout_decision.json' if prefix=='heldout' else 'final_decision.json')).read_text())
    df=pd.read_csv(P/('heldout_score.csv' if prefix=='heldout' else 'final_score.csv'))
    policy_col='active_policy'
    df=df[(df.model=='opponent_action')&(df.target=='all')&(df.action!='all')]
    if prefix=='heldout':df=df[df[policy_col]=='opponent_action']
    df=df.assign(action=df.action.map({'steal':'steal','assassinate':'Sombra'}))
    print('\n',title,'Gate',decision['gate'], 'passed',decision.get('passed',decision.get('passed_strata')),'/12')
    print(df[['n_players','population','action','stages','gap','gap_ci_low',
              'gap_ci_high','brier_delta_vs_opponent']].round(3).to_string(index=False))
print('\nCoefficients frozen in results/action_calibration/frozen_size_fit.json')
