"""Empirical game-theoretic analysis (EGTA) over strategy archetypes.

1. Payoff table: every multiset of n archetypes (a "profile") is simulated
   G times with seats shuffled each game. Stored as win counts per type, so
   the table can be bootstrapped by multinomial resampling of game outcomes.
2. alpha_rank: single-population alpha-Rank (Omidshafiei et al. 2019). A
   Markov chain over monomorphic populations; transitions use Fermi fixation
   probabilities in a finite population of size M, with payoffs averaged over
   hypergeometric table draws.
3. replicator: n-player replicator dynamics on the simplex (infinite
   population, multinomial table draws).
Payoff = win probability of one player of that type.
"""
from __future__ import annotations

import itertools
import random
from dataclasses import replace
from math import comb, factorial

import numpy as np

from .agents import HeuristicAgent, Params
from .engine import Game
from .rules import RuleConfig

_HONEST = dict(bluff=0.02, block_bluff=0.05)
_BLUFFER = dict(bluff=0.5, block_bluff=0.5)
ARCHETYPES = {
    "HonestTrusting": replace(Params(), **_HONEST, challenge_threshold=0.0, intervene=0.0),
    "HonestProtector": replace(Params(), **_HONEST, challenge_threshold=0.0, intervene=1.0),
    "HonestSceptic": replace(Params(), **_HONEST, challenge_threshold=0.3, intervene=0.0),
    "ScepticProtector": replace(Params(), **_HONEST, challenge_threshold=0.3, intervene=1.0),
    "Bluffer": replace(Params(), **_BLUFFER, challenge_threshold=0.0, intervene=0.0),
    "BlufferFakeProtector": replace(Params(), **_BLUFFER, challenge_threshold=0.0, intervene=1.0,
                                    intervene_bluff=0.5),
    "FakeProtector": replace(Params(), **_HONEST, challenge_threshold=0.0, intervene=1.0, intervene_bluff=1.0),
    "Pushover": replace(Params(), **_HONEST, challenge_threshold=0.0, stake_bonus=0.0, intervene=0.0),
    "Default": Params(),
}
NAMES = list(ARCHETYPES)


def profiles(k: int, n: int):
    """All multisets of n types out of k, as sorted tuples of type indices."""
    return list(itertools.combinations_with_replacement(range(k), n))


def simulate_profile(profile, config: RuleConfig, games: int, seed: int, archetypes=None):
    """Returns (wins per type index, draws) over `games` games of this profile."""
    params = [p for p in (archetypes or ARCHETYPES).values()]
    rng = random.Random(seed)
    k = len(params)
    wins = np.zeros(k, dtype=np.int64)
    draws = 0
    seats = list(profile)
    n = config.n_players
    for g in range(games):
        rng.shuffle(seats)
        agents = [HeuristicAgent(params[t], seed=rng.getrandbits(32)) for t in seats]
        w = Game(agents, config, seed=rng.getrandbits(32), first_player=rng.randrange(n)).play()
        if w is None:
            draws += 1
        else:
            wins[seats[w]] += 1
    return wins, draws


class PayoffTable:
    """Symmetric n-player payoff table from win counts."""

    def __init__(self, k: int, n: int, counts: dict, games: int):
        self.k, self.n, self.counts, self.games = k, n, counts, games
        self.payoff = {}
        for prof, wins in counts.items():
            mult = np.bincount(prof, minlength=k)
            with np.errstate(divide="ignore", invalid="ignore"):
                self.payoff[prof] = np.where(mult > 0, wins / (games * np.maximum(mult, 1)), np.nan)

    def resample(self, rng: np.random.Generator) -> "PayoffTable":
        """Parametric bootstrap: redraw each profile's outcomes from its empirical frequencies."""
        new = {}
        for prof, wins in self.counts.items():
            p = np.append(wins, self.games - wins.sum()) / self.games
            new[prof] = rng.multinomial(self.games, p)[:-1]
        return PayoffTable(self.k, self.n, new, self.games)

    def u(self, i: int, others) -> float:
        """Payoff to a type-i player whose n-1 opponents have the given type multiset."""
        return self.payoff[tuple(sorted((i, *others)))][i]

    # ------------------------------------------------------------ replicator
    def fitness(self, x: np.ndarray) -> np.ndarray:
        """Expected payoff of each type when the n-1 opponents are drawn iid from x."""
        if not hasattr(self, "_opp"):
            opps = list(itertools.combinations_with_replacement(range(self.k), self.n - 1))
            self._opp = np.array([np.bincount(o, minlength=self.k) for o in opps])  # multiplicities
            self._coef = np.array([factorial(self.n - 1) / np.prod([factorial(c) for c in m]) for m in self._opp])
            self._U = np.array([[self.u(i, o) for i in range(self.k)] for o in opps])
        with np.errstate(divide="ignore"):
            logx = np.log(x)
        logp = self._opp @ np.where(np.isfinite(logx), logx, -1e300)
        prob = self._coef * np.exp(np.maximum(logp, -745))
        prob[np.any((self._opp > 0) & (x == 0), axis=1)] = 0.0
        return prob @ self._U


def replicator(table: PayoffTable, x0: np.ndarray, steps: int = 4000, dt: float = 0.5, tol: float = 1e-9):
    x = np.asarray(x0, float)
    x = x / x.sum()
    for _ in range(steps):
        f = table.fitness(x)
        dx = x * (f - x @ f)
        x = np.clip(x + dt * dx, 0, None)
        x /= x.sum()
        if np.abs(dx).max() < tol:
            break
    return x


def rest_points(table: PayoffTable, starts: int = 60, seed: int = 0, **kw):
    """Integrate from random interior starts; return distinct end states and basin shares."""
    rng = np.random.default_rng(seed)
    ends = [replicator(table, rng.dirichlet(np.ones(table.k)), **kw) for _ in range(starts)]
    clusters = []
    for e in ends:
        for c in clusters:
            if np.abs(c["x"] - e).max() < 0.02:
                c["count"] += 1
                break
        else:
            clusters.append({"x": e, "count": 1})
    for c in clusters:
        c["basin"] = c.pop("count") / starts
    return sorted(clusters, key=lambda c: -c["basin"])


# ---------------------------------------------------------------- alpha-Rank
from functools import lru_cache


@lru_cache(maxsize=None)
def _hypergeom_weights(M: int, n: int):
    """W_mut[k, j], W_res[k, j]: P(j of the n-1 opponents are mutants | k mutants in M)."""
    Wm, Wr = np.zeros((M, n)), np.zeros((M, n))
    for k in range(1, M):
        for j in range(n):
            Wm[k, j] = comb(k - 1, j) * comb(M - k, n - 1 - j) / comb(M - 1, n - 1)
            Wr[k, j] = comb(k, j) * comb(M - k - 1, n - 1 - j) / comb(M - 1, n - 1)
    return Wm, Wr


def _two_type_payoffs(table: PayoffTable, mutant: int, resident: int, M: int):
    """Mean payoffs of mutant and resident when k mutants are in a population of M (index k = 1..M-1)."""
    n = table.n
    Wm, Wr = _hypergeom_weights(M, n)
    um = np.array([table.u(mutant, (mutant,) * j + (resident,) * (n - 1 - j)) for j in range(n)])
    ur = np.array([table.u(resident, (mutant,) * j + (resident,) * (n - 1 - j)) for j in range(n)])
    return Wm @ um, Wr @ ur


def fixation_probability(table, mutant, resident, M, alpha):
    pm, pr = _two_type_payoffs(table, mutant, resident, M)
    d = -alpha * (pm[1:] - pr[1:])  # k = 1..M-1
    s = np.cumsum(d)
    s = np.clip(s, -700, 700)
    return 1.0 / (1.0 + np.exp(s).sum())


def alpha_rank(table: PayoffTable, alpha: float = 50.0, M: int = 50):
    """Stationary distribution over monomorphic states (alpha-Rank)."""
    k = table.k
    C = np.zeros((k, k))
    for r in range(k):
        for m in range(k):
            if m != r:
                C[r, m] = fixation_probability(table, m, r, M, alpha) / (k - 1)
        C[r, r] = 1 - C[r].sum()
    w, v = np.linalg.eig(C.T)
    pi = np.real(v[:, np.argmin(np.abs(w - 1))])
    pi = np.abs(pi) / np.abs(pi).sum()
    return pi, C
