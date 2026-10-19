"""Individual-based co-evolution of protection and scepticism traits.

Each agent carries heritable traits (default: all five below):
  bluff                P(claim an unheld character when acting)
  block_bluff          P(bluff-block when targeted and holding no blocker)
  intervene            P(protect another player when holding a valid blocker)
  intervene_bluff      P(protect another player when *not* holding one) — faked protection
  challenge_threshold  θ: challenge a claim when P(claimant holds the card) < θ
  stake_bonus          added to θ when the claim involves the agent (initialised at 0.15)
Other behaviour stays at the Params defaults.

Generation: the population is shuffled into tables of n players, `rounds` times.
Fitness: 1 + wins (weak-selection Wright–Fisher). Offspring traits mutate with
probability `mu` by Gaussian steps of size `sigma`, clipped to [0, 1].
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace

import numpy as np

from .agents import HeuristicAgent, Params
from .engine import Game
from .rules import RuleConfig
from .sim import game_record

TRAITS = ("bluff", "block_bluff", "intervene", "intervene_bluff", "challenge_threshold", "stake_bonus")


@dataclass(frozen=True)
class EvoConfig:
    pop: int = 120
    rounds: int = 20  # games per agent per generation
    generations: int = 600
    mu: float = 0.1
    sigma: float = 0.05
    selection: float = 1.0  # fitness = 1 + selection * wins
    record_every: int = 10


def evolve(rules: RuleConfig, evo: EvoConfig, seed: int, init: str = "uniform"):
    rng = np.random.default_rng(seed)
    pyrng = random.Random(seed)
    n = rules.n_players
    if evo.pop % n:
        raise ValueError("population must be a multiple of the table size")
    if init == "uniform":
        traits = rng.random((evo.pop, len(TRAITS)))
        traits[:, TRAITS.index("stake_bonus")] = Params().stake_bonus  # start at the old fixed value
    else:  # start from the Params defaults
        base = Params()
        traits = np.tile([getattr(base, t) for t in TRAITS], (evo.pop, 1)).astype(float)
    history, behaviour = [], []
    game_seed = seed * 10_000_000
    for gen in range(evo.generations):
        wins = np.zeros(evo.pop)
        stats = {"games": 0, "interventions": 0, "intervention_bluffs": 0, "interventions_stood": 0,
                 "challenges": 0, "challenges_correct": 0, "turns": 0}
        record = gen % evo.record_every == 0 or gen == evo.generations - 1
        for _ in range(evo.rounds):
            order = rng.permutation(evo.pop)
            for t in range(0, evo.pop, n):
                seats = order[t:t + n]
                agents = [HeuristicAgent(replace(Params(), **dict(zip(TRAITS, traits[i]))),
                                         seed=pyrng.getrandbits(32)) for i in seats]
                game_seed += 1
                g = Game(agents, rules, seed=game_seed, first_player=pyrng.randrange(n))
                w = g.play()
                if w is not None:
                    wins[seats[w]] += 1
                if record:
                    rec = game_record(g)
                    stats["games"] += 1
                    for k in stats:
                        if k != "games":
                            stats[k] += rec[k]
        if record:
            row = {"generation": gen}
            for j, t in enumerate(TRAITS):
                row[f"{t}_mean"] = traits[:, j].mean()
                row[f"{t}_sd"] = traits[:, j].std()
            history.append(row)
            g_ = max(1, stats["games"])
            behaviour.append({
                "generation": gen,
                "interventions_per_game": stats["interventions"] / g_,
                "faked_protection_share": stats["intervention_bluffs"] / max(1, stats["interventions"]),
                "protection_success": stats["interventions_stood"] / max(1, stats["interventions"]),
                "challenges_per_game": stats["challenges"] / g_,
                "challenge_accuracy": stats["challenges_correct"] / max(1, stats["challenges"]),
                "turns_mean": stats["turns"] / g_,
            })
        fitness = 1 + evo.selection * wins
        parents = rng.choice(evo.pop, size=evo.pop, p=fitness / fitness.sum())
        traits = traits[parents].copy()
        mutate = rng.random(traits.shape) < evo.mu
        traits = np.clip(traits + mutate * rng.normal(0, evo.sigma, traits.shape), 0, 1)
    return history, behaviour
