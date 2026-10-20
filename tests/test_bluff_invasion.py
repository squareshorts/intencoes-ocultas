"""Regression tests for experimental bluff-invasion protocol, not for production engine."""
import importlib.util
from dataclasses import asdict
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
MOD=ROOT/'experiments'/'19_bluff_invasion.py'
spec=importlib.util.spec_from_file_location('bluff_invasion_experiment',MOD)
invasion=importlib.util.module_from_spec(spec)
spec.loader.exec_module(invasion)


@pytest.mark.parametrize('policy',invasion.POLICIES)
def test_isolates_action_bluff_trait(policy):
    a=asdict(invasion.make_params(policy,.3,False))
    b=asdict(invasion.make_params(policy,.3,True))
    diff={key for key in a if a[key]!=b[key]}
    assert diff=={'bluff'}
    assert a['bluff']==0.0 and b['bluff']==.8


@pytest.mark.parametrize('policy',invasion.POLICIES)
def test_counterfactual_identical_without_bluffs(policy):
    cfg=invasion.RuleConfig(n_players=4,intervention_reward=1)
    for seed in range(9_999_000,9_999_008):
        row=invasion.pair(cfg,theta=.50,policy=policy,seed=seed,coupled=True)
        assert row['mutant_focal_bluffs']==0
        assert row['delta_win']==0
        assert row['baseline_turns']==row['mutant_turns']
        assert row['baseline_attack_actions']==row['mutant_attack_actions']


def test_replay_determinism():
    cfg=invasion.RuleConfig(n_players=4,intervention_reward=1)
    a=invasion.pair(cfg,theta=.05,policy='opponent',seed=9_987_876,coupled=True)
    b=invasion.pair(cfg,theta=.05,policy='opponent',seed=9_987_876,coupled=True)
    assert a==b
