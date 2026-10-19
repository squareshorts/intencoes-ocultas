"""Public, opponent-specific forecasts and sequential claim-order correctness."""
from dataclasses import replace

import pytest

from intencoes.agents import HeuristicAgent, Params
from intencoes.engine import Game, View
from intencoes.rules import ActionType, Character, RuleConfig


R, C, S, G, E = Character


def fixture_view(*, history=(), per_player=(), hand=(R, G), h=(2, 2, 2),
                 revealed=((), (), ()), cfg=None):
    cfg = cfg or RuleConfig(n_players=3)
    return View(me=0, hand=hand, coins=(3,) * 3, hidden_counts=h,
                revealed=revealed, deck_size=15 - sum(h) - sum(map(len, revealed)),
                treasury=45, turn=0, config=cfg,
                block_history=history, player_block_history=per_player)


def agent(**kw):
    return HeuristicAgent(Params(block_prediction="opponent", **kw), seed=42)


def test_sequential_false_claim_precludes_third_party_intervention():
    # Target claims every time, but every block is challenged away. Since
    # the engine stops after the first claim, nobody else gets an offer.
    a = agent(block_prior_strength=0, opponent_pool_strength=0)
    v = fixture_view(per_player=(
        (1, ActionType.STEAL, "target", 10, 10, 0),
        (2, ActionType.STEAL, "intervention", 10, 10, 10),
    ))
    assert a._p_blocked(v, ActionType.STEAL, 1) == pytest.approx(0.)


def test_defenders_with_distinct_public_histories_get_distinct_predictions():
    a = agent(block_prior_strength=1, opponent_pool_strength=0)
    empty = fixture_view()
    low = fixture_view(per_player=((1, ActionType.STEAL, "target", 20, 0, 0),))
    high = fixture_view(per_player=((1, ActionType.STEAL, "target", 20, 20, 20),))
    assert a._p_blocked(low, ActionType.STEAL, 1) < a._p_blocked(empty, ActionType.STEAL, 1)
    assert a._p_blocked(high, ActionType.STEAL, 1) > a._p_blocked(empty, ActionType.STEAL, 1)


def test_public_opponent_prior_independent_of_own_defensive_traits():
    v = fixture_view()
    conservative = agent(intervene=0, intervene_bluff=0, block_bluff=0)
    aggressive = agent(intervene=1, intervene_bluff=1, block_bluff=1)
    assert conservative._p_blocked(v, ActionType.STEAL, 1) == pytest.approx(
        aggressive._p_blocked(v, ActionType.STEAL, 1))


def test_ablation_disentangles_person_identity_from_population_history():
    p = Params(block_prediction='opponent', block_prior_strength=1,
               opponent_pool_strength=1)
    a = HeuristicAgent(p)
    # These are both observations of TARGET defence by different players,
    # which can legitimately have different policies.
    samples = ((1, ActionType.STEAL, 'target', 20, 0, 0),
               (2, ActionType.STEAL, 'target', 20, 20, 20))
    v1 = fixture_view(per_player=samples)
    v2 = fixture_view(per_player=(samples[1][:1]+samples[0][1:],
                                          samples[0][:1]+samples[1][1:]))
    # Swap identities of the observations, keeping the public population
    # information identical. The seat-specific estimate must move.
    assert a._opponent_block_probability(v1, ActionType.STEAL, 1) != pytest.approx(
        a._opponent_block_probability(v2, ActionType.STEAL, 1))
    assert a._opponent_block_probability(v1, ActionType.STEAL, 1, 'pooled') == pytest.approx(
        a._opponent_block_probability(v2, ActionType.STEAL, 1, 'pooled'))
    assert a._opponent_block_probability(v1, ActionType.STEAL, 1, 'none') == pytest.approx(
        a._opponent_block_probability(v2, ActionType.STEAL, 1, 'none'))


def test_agent_does_not_see_opponent_cards_or_policy_labels():
    players = [agent(), agent(), agent()]
    g = Game(players, RuleConfig(n_players=3), seed=10)
    view1 = g.view(0)
    prediction = players[0]._p_blocked(view1, ActionType.STEAL, 1)
    g.players[1].hand[0], g.players[2].hand[0] = g.players[2].hand[0], g.players[1].hand[0]
    assert players[0]._p_blocked(g.view(0), ActionType.STEAL, 1) == pytest.approx(prediction)
    assert not hasattr(view1, "opponent_params")
    assert not hasattr(view1, "has_blocker")


def test_per_player_counts_sum_to_public_group_counts():
    for seed in range(12):
        agents = [agent() for _ in range(4)]
        g = Game(agents, RuleConfig(n_players=4), seed=seed)
        g.play()
        v = g.view(0)
        for action, mode, offers, stands in v.block_history:
            individual = [(n, c, s) for _, a, m, n, c, s in v.player_block_history
                          if (a, m) == (action, mode)]
            assert sum(x[0] for x in individual) == offers
            assert sum(x[2] for x in individual) == stands
            assert all(0 <= s <= c <= n for n, c, s in individual)
        g.check_invariants()


def test_oracle_is_explicit_and_does_not_use_private_card_truth():
    v = fixture_view()
    a = agent()
    innocent = Params(intervene=0, intervene_bluff=0, block_bluff=0)
    protective = Params(intervene=1, intervene_bluff=1, block_bluff=1)
    low = a.oracle_policy_block_probability(v, ActionType.STEAL, 1,
                                            {1: innocent, 2: innocent})
    high = a.oracle_policy_block_probability(v, ActionType.STEAL, 1,
                                             {1: innocent, 2: protective})
    assert 0 <= low < high <= 1
    # Policy knowledge alone does not reveal cards.
    changed = replace(v, hand=(S, S))
    assert a.oracle_policy_block_probability(changed, ActionType.STEAL, 1,
                                             {1: innocent, 2: protective}) != pytest.approx(high)


def test_proper_scoring_bounds_on_synthetic_all_observations():
    a = agent(block_prior_strength=1, opponent_pool_strength=1)
    v = fixture_view(per_player=((1, ActionType.STEAL, "target", 2, 1, 1),
                                 (2, ActionType.STEAL, "intervention", 2, 1, 0)))
    assert 0 <= a._p_blocked(v, ActionType.STEAL, 1) <= 1
    with pytest.raises(ValueError):
        HeuristicAgent(Params(block_prediction='invalid'))._p_blocked(v, ActionType.STEAL, 1)
