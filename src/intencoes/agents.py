"""Agent strategies.

HeuristicAgent is a parametric strategy family whose parameters are the
quantities the paper varies (bluffing, scepticism, intervention propensity).
Its scepticism uses card counting: the chance that a claimant actually holds
the claimed character, given every card the agent can see.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from math import comb

from .engine import Agent, View
from .rules import BLOCKERS, CLAIM, ActionType, Character

# Value used when choosing which card to lose / keep (higher = keep).
CARD_VALUE = {
    Character.REGENTE: 5,
    Character.SOMBRA: 4,
    Character.GUARDIAO: 3,
    Character.COMERCIANTE: 2,
    Character.EMBAIXADOR: 1,
}


def p_holds(view: View, claimant: int, ch: Character) -> float:
    """P(claimant holds >=1 copy of ch | cards visible to view.me), uniform prior."""
    c = view.config
    seen = list(view.hand) + [x for r in view.revealed for x in r]
    k = c.copies_per_character - seen.count(ch)
    if k <= 0:
        return 0.0
    unseen = view.deck_size + sum(n for j, n in enumerate(view.hidden_counts) if j != view.me)
    h = view.hidden_counts[claimant]
    if h == 0 or unseen <= 0:
        return 0.0
    return 1.0 - comb(unseen - k, h) / comb(unseen, h)


def p_holds_public(view: View, claimant: int, ch: Character) -> float:
    """How a typical opponent of `claimant` would rate the claim: P(claimant holds ch) using
    only public information (revealed cards, hidden counts, deck size). Used by bluffers to
    anticipate challenges; claims with fewer unseen copies are riskier."""
    c = view.config
    revealed = [x for r in view.revealed for x in r]
    k = c.copies_per_character - revealed.count(ch)
    if k <= 0:
        return 0.0
    others = [n for j, n in enumerate(view.hidden_counts) if j != claimant and n > 0]
    # a challenger sees everything hidden except their own hand
    unseen = view.deck_size + sum(view.hidden_counts) - (sum(others) / len(others) if others else 0)
    unseen = int(round(unseen))
    h = view.hidden_counts[claimant]
    k = min(k, unseen)
    if h == 0 or unseen <= 0:
        return 0.0
    return 1.0 - comb(unseen - k, h) / comb(unseen, h)


class RandomAgent(Agent):
    """Uniformly random legal play; used for stress-testing the engine."""

    def __init__(self, seed=None, p_challenge=0.2, p_block=0.3):
        self.rng = random.Random(seed)
        self.p_challenge, self.p_block = p_challenge, p_block
        self._game = None

    def bind(self, game):
        self._game = game
        return self

    def act(self, view):
        return self.rng.choice(self._game.legal_actions(view.me))

    def _bluff_score(self, view, act):
        """Expected coin-equivalent gain of a bluffed action minus expected loss if challenged."""
        c, (action, target) = view.config, act
        gain = {
            ActionType.TAX: c.tax_amount,
            ActionType.STEAL: min(c.steal_amount, view.coins[target]) if target is not None else 0,
            ActionType.ASSASSINATE: INFLUENCE_VALUE - c.assassinate_cost,
            ActionType.EXCHANGE: EXCHANGE_VALUE,
        }[action]
        p_challenged = 1.0 - p_holds_public(view, view.me, CLAIM[action])
        return gain - p_challenged * INFLUENCE_VALUE + self.rng.random() * 1e-6

    def _credible_block(self, view, options):
        """Bluffed block: claim the character that looks most plausible to the table."""
        if self.p.bluff_target == "random":
            return self.rng.choice(options)
        return max(options, key=lambda ch: p_holds_public(view, view.me, ch) + self.rng.random() * 1e-6)

    def challenge(self, view, claimant, character, action, actor, target):
        return self.rng.random() < self.p_challenge

    def block(self, view, action, actor, target, as_interventor):
        if self.rng.random() < self.p_block:
            return self.rng.choice(BLOCKERS[action])
        return None

    def reveal(self, view):
        return self.rng.choice(view.hand)

    def exchange(self, view, options, keep):
        return self.rng.sample(options, keep)


@dataclass
class Params:
    bluff: float = 0.2  # P(claim an unheld character when choosing an action)
    challenge_threshold: float = 0.25  # challenge if P(claimant holds) < threshold
    stake_bonus: float = 0.15  # added to threshold when the claim targets/blocks me
    block_bluff: float = 0.3  # P(bluff-block when targeted and holding no blocker)
    intervene: float = 0.5  # P(intervene for another player when holding a blocker)
    intervene_bluff: float = 0.0  # P(bluff-intervene when holding no blocker)
    foreign_aid: float = 0.5  # P(foreign aid instead of income when no character action is chosen)
    bluff_target: str = "strategic"  # "strategic" (gain - P(challenged)*cost) or "random" (pre-fix ablation)


# Coin-equivalent value of a successful action, and of losing one influence (one Golpe Direto).
INFLUENCE_VALUE = 7.0
EXCHANGE_VALUE = 0.5


class HeuristicAgent(Agent):
    def __init__(self, params: Params | None = None, seed=None, label: str = "heuristic"):
        self.p = params or Params()
        self.rng = random.Random(seed)
        self.label = label

    # -------------------------------------------------------------- helpers
    def _threat_order(self, view):
        others = [j for j in view.active if j != view.me]
        return sorted(others, key=lambda j: (view.hidden_counts[j], view.coins[j], self.rng.random()), reverse=True)

    # -------------------------------------------------------------- decisions
    def act(self, view):
        c, me, coins = view.config, view.me, view.coins[view.me]
        targets = self._threat_order(view)
        if coins >= c.coup_cost:
            return ActionType.COUP, targets[0]
        hand = set(view.hand)
        rich = [j for j in targets if view.coins[j] >= 1]

        def options(holding):
            opts = []
            if (Character.SOMBRA in hand) == holding and coins >= c.assassinate_cost:
                opts.append((ActionType.ASSASSINATE, targets[0]))
            if (Character.REGENTE in hand) == holding:
                opts.append((ActionType.TAX, None))
            if (Character.COMERCIANTE in hand) == holding and rich:
                opts.append((ActionType.STEAL, max(rich, key=lambda j: view.coins[j])))
            if (Character.EMBAIXADOR in hand) == holding:
                opts.append((ActionType.EXCHANGE, None))
            return opts

        honest, bluffs = options(True), options(False)
        if bluffs and self.rng.random() < self.p.bluff:
            if self.p.bluff_target == "random":
                return self.rng.choice(bluffs)
            return max(bluffs, key=lambda a: self._bluff_score(view, a))
        if honest:
            return honest[0]  # ordered by preference
        if self.rng.random() < self.p.foreign_aid:
            return ActionType.FOREIGN_AID, None
        return ActionType.INCOME, None

    def _bluff_score(self, view, act):
        """Expected coin-equivalent gain of a bluffed action minus expected loss if challenged."""
        c, (action, target) = view.config, act
        gain = {
            ActionType.TAX: c.tax_amount,
            ActionType.STEAL: min(c.steal_amount, view.coins[target]) if target is not None else 0,
            ActionType.ASSASSINATE: INFLUENCE_VALUE - c.assassinate_cost,
            ActionType.EXCHANGE: EXCHANGE_VALUE,
        }[action]
        p_challenged = 1.0 - p_holds_public(view, view.me, CLAIM[action])
        return gain - p_challenged * INFLUENCE_VALUE + self.rng.random() * 1e-6

    def _credible_block(self, view, options):
        """Bluffed block: claim the character that looks most plausible to the table."""
        if self.p.bluff_target == "random":
            return self.rng.choice(options)
        return max(options, key=lambda ch: p_holds_public(view, view.me, ch) + self.rng.random() * 1e-6)

    def challenge(self, view, claimant, character, action, actor, target):
        threshold = self.p.challenge_threshold
        if target == view.me or actor == view.me:
            threshold += self.p.stake_bonus
        p = p_holds(view, claimant, character)
        return p == 0.0 or p < threshold  # a provably false claim is always challenged

    def block(self, view, action, actor, target, as_interventor):
        options = BLOCKERS[action]
        held = [ch for ch in options if ch in view.hand]
        if as_interventor:
            if held and self.rng.random() < self.p.intervene:
                return held[0]
            if not held and self.rng.random() < self.p.intervene_bluff:
                return self._credible_block(view, options)
            return None
        if action == ActionType.FOREIGN_AID:
            if held:
                return held[0]
            return options[0] if self.rng.random() < self.p.block_bluff * 0.5 else None
        if held:
            return held[0]
        bluff_p = self.p.block_bluff
        if action == ActionType.ASSASSINATE and view.hidden_counts[view.me] == 1:
            bluff_p = 1.0  # nothing left to lose
        return self._credible_block(view, options) if self.rng.random() < bluff_p else None

    def reveal(self, view):
        return min(view.hand, key=lambda ch: CARD_VALUE[ch])

    def exchange(self, view, options, keep):
        ranked = sorted(options, key=lambda ch: CARD_VALUE[ch], reverse=True)
        chosen = []
        for ch in ranked:  # prefer distinct characters
            if ch not in chosen and len(chosen) < keep:
                chosen.append(ch)
        for ch in ranked:
            if len(chosen) < keep and ranked.count(ch) > chosen.count(ch):
                chosen.append(ch)
        return chosen[:keep]
