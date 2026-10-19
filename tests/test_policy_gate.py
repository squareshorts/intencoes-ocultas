"""Focused invariants for endogenous action-selection and exposure diagnostics."""
import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from intencoes.agents import HeuristicAgent, Params
from intencoes.engine import Game
from intencoes.rules import ActionType, Character, RuleConfig


PATH = Path(__file__).resolve().parents[1]/'experiments'/'10_endogenous_opportunity.py'
spec = importlib.util.spec_from_file_location('policy_gate_experiment', PATH)
pg = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pg
spec.loader.exec_module(pg)


def suitable_view():
    g = Game([HeuristicAgent(seed=k) for k in range(4)], RuleConfig(), seed=5)
    p = g.players[0]
    if Character.COMERCIANTE not in p.hand:
        substitute = p.hand[0]
        g.deck.remove(Character.COMERCIANTE)
        g.deck.append(substitute)
        p.hand[0] = Character.COMERCIANTE
    return g.view(0)


def test_encouragement_requires_own_held_character_and_first_action():
    v = suitable_view()
    a = pg.EncouragedAgent(Params(), seed=3, opportunity_dose=1,
                          encouragement_seed=42)
    action, target = a.act(v)
    assert action == ActionType.STEAL and target in (1, 2, 3)
    assert a.forced == a.eligible == a.assigned == 1
    assert a.just_forced
    a.act(v)
    assert a.forced == 1 and not a.just_forced
    empty_hand = replace(v, hand=(Character.GUARDIAO, Character.EMBAIXADOR))
    b = pg.EncouragedAgent(Params(), opportunity_dose=1, encouragement_seed=42)
    b.act(empty_hand)
    assert b.assigned == 1 and b.eligible == b.forced == 0


def test_blind_ablation_changes_only_action_selection_view(monkeypatch):
    v = suitable_view()
    noticed = []
    def spy_act(self, x):
        noticed.append(x.config.intervention_enabled)
        return ActionType.INCOME, None
    monkeypatch.setattr(HeuristicAgent, 'act', spy_act)
    a = pg.EncouragedAgent(Params(), opportunity_dose=0,
                          blind_anticipation=True)
    assert a.act(v) == (ActionType.INCOME, None)
    assert noticed == [False]
    assert v.config.intervention_enabled is True
    b = pg.EncouragedAgent(Params(), opportunity_dose=0)
    b.act(v)
    assert noticed == [False, True]


def test_pre_offer_forecast_consistency_and_public_history():
    g = pg.game_iteration(640031, 'mixed', 'opponent', 1, 1)
    for snap in g.snapshots:
        assert 0 <= snap.in_game_probability <= 1
        assert pg.predict(snap, 'opponent') == pytest.approx(snap.in_game_probability)
        assert not hasattr(snap.view, 'players')
        assert all(len(r) == 6 for r in snap.view.player_block_history)
        assert 0 <= snap.outcome <= 1
    g.check_invariants()


def test_scenarios_have_unique_labels_and_exposure_both_on_off():
    setup = pg.scenarios()
    assert len(setup) == len({pg.label(s) for s in setup})
    assert any(s[4] == 'blind' and not s[5] for s in setup)
    assert any(s[2] == 1 and s[4] == 'aware' for s in setup)


def test_score_zero_delta_for_reference_and_no_missing_outcomes():
    s = ('mixed', 'opponent', 0.5, 1, 'aware', True)
    summary, cal, games, stages = pg.run_scenario(s, 25, 50, save_raw=True)
    assert len(games) == 25
    assert summary['own_forecast_max_difference'] < 1e-10
    assert len(stages) == summary['stages']
    assert all(0 <= stage[m] <= 1 for stage in stages for m in pg.METHODS)
    empirical = next(r for r in cal if r['model'] == 'empirical')
    assert empirical['brier_delta_vs_empirical'] == pytest.approx(0)
    assert empirical['delta_ci_high'] == pytest.approx(0)


def test_forced_probe_is_one_turn_card_conditioned_and_reward_invariant():
    x = pg.forced_probe(30, 'mixed', 0, first_seed=999991)
    y = pg.forced_probe(30, 'mixed', 2, first_seed=999991)
    assert x['block_stages'] == y['block_stages']
    assert x['target_offers'] == y['target_offers']
    assert x.get('intervention_offers', 0) == y.get('intervention_offers', 0)
    assert x.get('intervention_claims', 0) == y.get('intervention_claims', 0)
    assert x['seed_end_exclusive'] == y['seed_end_exclusive']
    assert x['card_conditioned']


def test_randomized_encouragement_nondecreasing_forced_ups_given_seed():
    x = pg.game_iteration(640042, 'mixed', 'opponent', 0, 1)
    y = pg.game_iteration(640042, 'mixed', 'opponent', 1, 1)
    assert sum(a.assigned for a in x.agents) == 0
    assert sum(a.forced for a in x.agents) == 0
    assert sum(a.assigned for a in y.agents) >= sum(a.forced for a in y.agents)
