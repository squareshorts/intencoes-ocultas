"""Regression tests for conditional blocking beliefs and decision-value fixes."""
from dataclasses import replace
from math import comb

import pytest

from intencoes.agents import HeuristicAgent, Params, p_holds_public
from intencoes.engine import Game, View
from intencoes.rules import ActionType, Character, RuleConfig


def view(*, history=(), revealed=(), h=(2, 2, 2), me=0, hand=None, coins=None,
         claims=0, challenges=0, intervention_enabled=False):
    cfg = RuleConfig(n_players=3, intervention_enabled=intervention_enabled)
    hand = (Character.REGENTE, Character.REGENTE) if hand is None else hand
    revealed = revealed or ((), (), ())
    return View(me=me, hand=hand, coins=coins or (3, 2, 2), hidden_counts=h,
                revealed=revealed, deck_size=15 - sum(h) - sum(len(r) for r in revealed),
                treasury=47, turn=0, config=cfg, claims=claims, challenges=challenges,
                block_history=history)


def test_public_posterior_uses_all_publicly_unseen_cards():
    v = view()
    # Three out of 15 cards are Guardiao. The claimant has two hidden cards.
    expect = 1 - comb(12, 2) / comb(15, 2)
    assert p_holds_public(v, 1, Character.GUARDIAO) == pytest.approx(expect)
    assert p_holds_public(v, 1, Character.REGENTE) == pytest.approx(expect)
    assert p_holds_public(view(h=(2, 1, 2), revealed=((), (), (Character.GUARDIAO,))),
                          1, Character.GUARDIAO) == pytest.approx(2 / 14)


def test_empirical_offer_rate_not_multiplied_by_card_availability():
    v = view(history=((ActionType.STEAL, 'target', 20, 4),))
    a = HeuristicAgent(Params(block_prediction='empirical', block_prior_strength=0))
    assert a._p_blocked(v, ActionType.STEAL, 1) == pytest.approx(0.2)
    # A historical card-only estimate is intentionally distinct.
    old = HeuristicAgent(Params(block_prediction='card_only'))
    assert old._p_blocked(v, ActionType.STEAL, 1) != pytest.approx(0.2)


def test_target_and_intervention_have_distinct_posteriors():
    v = view(intervention_enabled=True, history=(
        (ActionType.STEAL, 'target', 10, 2),
        (ActionType.STEAL, 'intervention', 10, 1),
    ))
    a = HeuristicAgent(Params(block_prediction='empirical', block_prior_strength=0))
    # One target (20%) and one third-party defender (10%).
    assert a._p_blocked(v, ActionType.STEAL, 1) == pytest.approx(1 - 0.8 * 0.9)
    assert a._p_blocked(replace(v, config=RuleConfig(n_players=3, intervention_enabled=False)),
                        ActionType.STEAL, 1) == pytest.approx(0.2)


def test_public_forecast_does_not_read_private_hands_of_opponents():
    agents = [HeuristicAgent(seed=i) for i in range(3)]
    g = Game(agents, RuleConfig(n_players=3), seed=20)
    orig = g.view(0)
    forecast = agents[0]._p_blocked(orig, ActionType.STEAL, 1)
    # Swap two opponents' private cards; public cards/counts and player's own hand stay the same.
    g.players[1].hand[0], g.players[2].hand[0] = g.players[2].hand[0], g.players[1].hand[0]
    assert agents[0]._p_blocked(g.view(0), ActionType.STEAL, 1) == pytest.approx(forecast)
    assert not any(isinstance(x, bool) for rec in orig.block_history for x in rec)


def test_failed_assassination_bluff_challenge_loses_cost_and_influence():
    v = view(hand=(Character.REGENTE, Character.EMBAIXADOR), coins=(3, 2, 2))
    a = HeuristicAgent(Params(block_prediction='none'), seed=0)
    q = p_holds_public(v, 0, Character.SOMBRA)
    p = min(1.0, (2 * ((v.challenges + 1) / (v.claims + 2))) * (1 - q))
    expected = (1 - p) * (7 - 3) - p * (7 + 3)
    assert a._bluff_score(v, (ActionType.ASSASSINATE, 1)) == pytest.approx(expected, abs=1e-5)
    refunded = replace(v, config=replace(v.config, assassin_refund_on_failed_challenge=True))
    expected_refund = (1 - p) * (7 - 3) - p * 7
    assert a._bluff_score(refunded, (ActionType.ASSASSINATE, 1)) == pytest.approx(expected_refund, abs=1e-5)


def test_foreign_aid_value_accounts_for_defence():
    v = view(history=((ActionType.FOREIGN_AID, 'aid', 10, 10),))
    a = HeuristicAgent(Params(block_prediction='empirical', block_prior_strength=0))
    assert a._gain(v, (ActionType.FOREIGN_AID, None)) == 0
    assert a._gain(v, (ActionType.INCOME, None)) == 1


def test_engine_logs_real_offers_without_exposing_hidden_truth_in_view():
    class Attacker(HeuristicAgent):
        def act(self, _):
            return ActionType.STEAL, 1

    class Passive(HeuristicAgent):
        def challenge(self, *args):
            return False
        def block(self, *args):
            return None

    agents = [Attacker(seed=0), Passive(seed=1), Passive(seed=2)]
    g = Game(agents, RuleConfig(n_players=3), seed=4)
    g.play_turn()
    offers = [e for e in g.log if e['event'] == 'block_offer']
    assert [e['mode'] for e in offers] == ['target', 'intervention']
    assert all(not e['claimed'] for e in offers)
    public = g.view(0).block_history
    assert (ActionType.STEAL, 'target', 1, 0) in public
    assert (ActionType.STEAL, 'intervention', 1, 0) in public
    assert all(len(entry) == 4 for entry in public)
    assert 'p_blocked_pred' in next(e for e in g.log if e['event'] == 'action')
    g.check_invariants()


def test_block_history_counts_standing_not_merely_claimed():
    class Attacker(HeuristicAgent):
        def act(self, _):
            return ActionType.STEAL, 1
        def challenge(self, view, claimant, character, action, actor, target):
            return claimant == 1

    class Defender(HeuristicAgent):
        def challenge(self, *args):
            return False
        def block(self, view, action, actor, target, as_interventor):
            return Character.GUARDIAO if not as_interventor else None

    agents = [Attacker(seed=0), Defender(seed=1), Defender(seed=2)]
    g = Game(agents, RuleConfig(n_players=3), seed=12)
    # Make sure seat 1 never holds the claimed Guardiao.
    if Character.GUARDIAO in g.players[1].hand:
        idx = g.players[1].hand.index(Character.GUARDIAO)
        choice = next(c for c in g.deck if c != Character.GUARDIAO)
        g.deck.remove(choice)
        g.deck.append(Character.GUARDIAO)
        g.players[1].hand[idx] = choice
    g.play_turn()
    h = {(action, mode): (offers, stood) for action, mode, offers, stood in g.view(0).block_history}
    assert h[(ActionType.STEAL, 'target')] == (1, 0)
    assert (ActionType.STEAL, 'intervention') not in h  # first claimant locks out later defenders
    assert any(e['event'] == 'block' and not e['stands'] for e in g.log)
    g.check_invariants()


def test_invalid_prediction_model_is_rejected():
    a = HeuristicAgent(Params(block_prediction='unsupported'))
    with pytest.raises(ValueError):
        a._p_blocked(view(), ActionType.STEAL, 1)


def test_blocking_oracle_card_count_versus_bluff_exposure():
    # The actor can see all Guardiao cards (two in hand, one revealed).
    v = view(hand=(Character.GUARDIAO, Character.GUARDIAO),
             h=(2, 1, 2), revealed=((), (), (Character.GUARDIAO,)))
    a = HeuristicAgent(Params(block_prediction='empirical',block_bluff=1.0),seed=1)
    assert a._p_blocked(v, ActionType.ASSASSINATE, 1) == 0
    assert a._block_card_probability(v,1,ActionType.ASSASSINATE) == 0


def test_full_game_record_tracks_public_opportunities():
    from intencoes.sim import game_record
    ag=[HeuristicAgent(seed=s) for s in range(4)]
    g=Game(ag,RuleConfig(),seed=30)
    g.play()
    v=g.view(0)
    rec=game_record(g)
    assert rec['intervention_offers'] == sum(offers for action,mode,offers,stands
                                            in v.block_history if mode=='intervention')
    assert rec['intervention_stands'] <= rec['intervention_offers']
    assert rec['target_block_stands'] <= rec['target_block_offers']


def test_original_smoke_engines_and_evolution():
    from intencoes.evolution import EvoConfig, evolve
    for players in (3,4,5):
        for seed in range(20):
            g=Game([HeuristicAgent(seed=seed*10+k) for k in range(players)],
                   RuleConfig(n_players=players),seed=seed)
            assert g.play() is not None
    hist,beh=evolve(RuleConfig(),EvoConfig(pop=8,rounds=2,generations=3,record_every=1),seed=1)
    assert len(hist) == 3
    assert all(0 <= r['interventions_per_offer'] <= 1 for r in beh)
