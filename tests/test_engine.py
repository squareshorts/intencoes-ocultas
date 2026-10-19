import pytest

from intencoes.agents import HeuristicAgent, Params, RandomAgent, p_holds
from intencoes.engine import Agent, Game, IllegalAction
from intencoes.rules import ActionType, Character, RuleConfig

R, C, S, G, E = (Character.REGENTE, Character.COMERCIANTE, Character.SOMBRA,
                 Character.GUARDIAO, Character.EMBAIXADOR)


class Scripted(Agent):
    """Deterministic agent: fixed action, challenge/block/intervene flags."""

    def __init__(self, action=(ActionType.INCOME, None), challenge=False, block=None, intervene=None):
        self.action, self.ch, self.bl, self.iv = action, challenge, block, intervene

    def act(self, view):
        return self.action

    def challenge(self, view, claimant, character, action, actor, target):
        return self.ch

    def block(self, view, action, actor, target, as_interventor):
        return self.iv if as_interventor else self.bl

    def reveal(self, view):
        return view.hand[0]

    def exchange(self, view, options, keep):
        return options[:keep]


def make_game(agents, hands, coins=None, **cfg):
    g = Game(agents, RuleConfig(n_players=len(agents), **cfg), seed=0)
    pool = [ch for ch in Character for _ in range(3)]
    for p, hand in zip(g.players, hands):
        p.hand = list(hand)
        for ch in hand:
            pool.remove(ch)
    g.deck = pool  # dealt hands were replaced; deck is the remainder
    if coins:
        g.treasury += sum(p.coins for p in g.players) - sum(coins)
        for p, c in zip(g.players, coins):
            p.coins = c
    return g


@pytest.mark.parametrize("n", [3, 4, 5])
def test_random_games_terminate_and_conserve(n):
    for seed in range(300):
        agents = [RandomAgent(seed=seed * 10 + k) for k in range(n)]
        g = Game(agents, RuleConfig(n_players=n), seed=seed)
        for a in agents:
            a.bind(g)
        g.play()  # check_invariants runs inside
        assert g.winner is not None or g.turn >= g.config.max_turns


@pytest.mark.parametrize("n", [3, 4, 5])
def test_heuristic_games_terminate(n):
    for seed in range(200):
        g = Game([HeuristicAgent(seed=seed * 10 + k) for k in range(n)], RuleConfig(n_players=n), seed=seed)
        assert g.play() is not None


def test_forced_coup_at_ten():
    g = make_game([Scripted(), Scripted(), Scripted()], [(R, C), (S, G), (E, E)], coins=[10, 2, 2])
    assert {a for a, _ in g.legal_actions(0)} == {ActionType.COUP}
    with pytest.raises(IllegalAction):
        g.play_turn()


def test_true_claim_challenger_loses_and_claimant_swaps():
    g = make_game([Scripted((ActionType.TAX, None)), Scripted(challenge=True), Scripted()],
                  [(R, C), (S, G), (E, E)])
    g.play_turn()
    assert g.players[0].coins == 2 + 3
    assert len(g.players[1].hand) == 1
    assert len(g.players[0].hand) == 2
    g.check_invariants()


def test_caught_bluff_loses_influence_and_action_fails():
    g = make_game([Scripted((ActionType.TAX, None)), Scripted(challenge=True), Scripted()],
                  [(C, C), (S, G), (E, E)])
    g.play_turn()
    assert g.players[0].coins == 2
    assert len(g.players[0].hand) == 1 and len(g.players[1].hand) == 2


def test_target_block_stops_steal():
    g = make_game([Scripted((ActionType.STEAL, 1)), Scripted(block=G), Scripted()],
                  [(C, R), (G, S), (E, E)])
    g.play_turn()
    assert g.players[0].coins == 2 and g.players[1].coins == 2


def test_intervention_blocks_and_is_rewarded():
    g = make_game([Scripted((ActionType.ASSASSINATE, 1)), Scripted(), Scripted(intervene=G)],
                  [(S, R), (C, C), (G, E)], coins=[3, 2, 2])
    g.play_turn()
    assert len(g.players[1].hand) == 2  # protected
    assert g.players[2].coins == 3  # +1 reward
    assert g.players[0].coins == 0  # assassination cost not refunded (A4)
    ev = [e for e in g.log if e["event"] == "block"][0]
    assert ev["interventor"] and ev["stands"] and ev["reward"] == 1


def test_bluffed_intervention_exposed_gets_no_reward():
    agents = [Scripted((ActionType.STEAL, 1), challenge=True), Scripted(), Scripted(intervene=G)]
    g = make_game(agents, [(C, R), (S, S), (E, E)])
    g.play_turn()
    assert g.players[2].coins == 2 and len(g.players[2].hand) == 1
    assert g.players[0].coins == 4 and g.players[1].coins == 0


def test_no_intervention_when_disabled():
    g = make_game([Scripted((ActionType.ASSASSINATE, 1)), Scripted(), Scripted(intervene=G)],
                  [(S, R), (C, C), (G, E)], coins=[3, 2, 2], intervention_enabled=False)
    g.play_turn()
    assert len(g.players[1].hand) == 1


def test_target_block_precludes_intervention():
    g = make_game([Scripted((ActionType.STEAL, 1)), Scripted(block=G), Scripted(intervene=G)],
                  [(C, R), (G, S), (G, E)])
    g.play_turn()
    assert g.players[2].coins == 2


def test_actor_cannot_intervene_and_observer_cannot_act():
    g = make_game([Scripted((ActionType.STEAL, 1), intervene=G), Scripted(), Scripted(intervene=G), Scripted()],
                  [(C, G), (S, S), (R, R), (E, E)])
    g.players[2].revealed, g.players[2].hand = list(g.players[2].hand), []  # player 2 is an Observer
    g.play_turn()
    assert g.players[0].coins == 4  # steal went through; nobody eligible intervened


def test_p_holds_zero_when_all_copies_seen():
    g = make_game([Scripted()] * 3, [(R, R), (S, G), (E, E)])
    g.players[1].revealed = [R]
    g.players[1].hand = [S]
    g.deck.remove(G)  # keep card count consistent for the view
    v = g.view(0)
    assert p_holds(v, 2, R) == 0.0
    assert 0 < p_holds(v, 2, C) < 1


def test_challenge_cost_paid_by_challenger():
    g = make_game([Scripted((ActionType.TAX, None)), Scripted(challenge=True), Scripted()],
                  [(C, C), (S, G), (E, E)], challenge_cost=1)
    g.play_turn()
    assert g.players[1].coins == 1  # paid even though the challenge succeeded
    g.check_invariants()


def test_paired_bootstrap_detects_known_effect():
    import numpy as np
    from intencoes.stats import invasion_table
    rng = np.random.default_rng(1)
    base = rng.integers(0, 4, 5000)
    better = np.where(rng.random(5000) < 0.1, 0, base)  # focal (seat 0) wins ~7.5 pp more
    table, grad = invasion_table({(0.0, 0.0): base, (1.0, 0.0): better}, n_players=4, n_boot=500)
    row = table[(table.mutant == 1.0)].iloc[0]
    assert row.ci_low > 0 and grad["ci_low"] > 0
    assert table[(table.mutant == 0.0)].rel_fitness.iloc[0] == 0


def test_evolution_smoke():
    from intencoes.evolution import EvoConfig, evolve
    hist, beh = evolve(RuleConfig(), EvoConfig(pop=8, rounds=2, generations=3, record_every=1), seed=1)
    assert "bluff_mean" in hist[0]
    assert len(hist) == 3 and all(0 <= h["intervene_mean"] <= 1 for h in hist)
    assert "faked_protection_share" in beh[0]


def _synthetic_table(k, n, games, winner_rule):
    import numpy as np
    from intencoes.egta import PayoffTable, profiles
    counts = {}
    for prof in profiles(k, n):
        wins = np.zeros(k, dtype=np.int64)
        for t, share in winner_rule(prof).items():
            wins[t] = int(round(share * games))
        counts[prof] = wins
    return PayoffTable(k, n, counts, games)


def test_alpha_rank_and_replicator_find_dominant_type():
    import numpy as np
    from intencoes.egta import alpha_rank, rest_points
    # type 0 wins every game it is in; otherwise the lowest index wins
    table = _synthetic_table(3, 4, 1000, lambda prof: {min(prof): 1.0})
    pi, _ = alpha_rank(table, alpha=20, M=20)
    assert pi[0] > 0.95
    rp = rest_points(table, starts=10)
    assert rp[0]["x"][0] > 0.99 and rp[0]["basin"] == 1.0


def test_alpha_rank_uniform_for_neutral_game():
    import numpy as np
    from intencoes.egta import alpha_rank
    table = _synthetic_table(3, 4, 1000, lambda prof: {t: np.bincount(prof, minlength=3)[t] / 4 for t in set(prof)})
    pi, _ = alpha_rank(table, alpha=20, M=20)
    assert np.allclose(pi, 1 / 3, atol=1e-6)


def test_simulate_profile_counts_are_consistent():
    from intencoes.egta import simulate_profile
    wins, draws = simulate_profile((0, 0, 4, 8), RuleConfig(), games=50, seed=3)
    assert wins.sum() + draws == 50 and wins[[1, 2, 3, 5, 6, 7]].sum() == 0
