"""Game engine for Intenções Ocultas.

Implements the turn sequence of the rulebook: declare, then challenge, then
block or intervention, then challenge of the block, then resolution. Ambiguous
cases follow docs/rules_assumptions.md.
Agents only receive a View (their own cards plus public information).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .rules import BLOCKERS, CLAIM, INTERVENABLE, TARGETED, ActionType, Character, RuleConfig


@dataclass
class View:
    """What player `me` may see when making a decision."""
    me: int
    hand: tuple  # own active (hidden) characters
    coins: tuple
    hidden_counts: tuple  # number of active influences per player
    revealed: tuple  # tuple of tuples of revealed characters per player
    deck_size: int
    treasury: int
    turn: int
    config: RuleConfig

    @property
    def active(self):
        return tuple(i for i, n in enumerate(self.hidden_counts) if n > 0)


class Agent:
    """Decision interface. Subclasses override every method."""

    def act(self, view: View):  # -> (ActionType, target | None)
        raise NotImplementedError

    def challenge(self, view: View, claimant: int, character: Character, action: ActionType,
                  actor: int, target) -> bool:
        raise NotImplementedError

    def block(self, view: View, action: ActionType, actor: int, target, as_interventor: bool):
        """Return a blocking Character (may be a bluff) or None."""
        raise NotImplementedError

    def reveal(self, view: View) -> Character:
        """Choose which own active character to lose."""
        raise NotImplementedError

    def exchange(self, view: View, options: list, keep: int) -> list:
        """Choose `keep` characters from `options` to keep."""
        raise NotImplementedError


@dataclass
class Player:
    hand: list  # active characters
    revealed: list = field(default_factory=list)
    coins: int = 0

    @property
    def alive(self):
        return bool(self.hand)


class IllegalAction(Exception):
    pass


class Game:
    def __init__(self, agents, config: RuleConfig | None = None, seed=None, first_player: int = 0):
        self.config = config or RuleConfig(n_players=len(agents))
        if len(agents) != self.config.n_players:
            raise ValueError("number of agents must equal config.n_players")
        self.agents = list(agents)
        self.rng = random.Random(seed)
        c = self.config
        self.deck = [ch for ch in Character for _ in range(c.copies_per_character)]
        self.rng.shuffle(self.deck)
        self.players = []
        self.treasury = c.treasury
        for _ in range(c.n_players):
            hand = [self.deck.pop() for _ in range(c.influences_per_player)]
            self.players.append(Player(hand=hand, coins=c.starting_coins))
            self.treasury -= c.starting_coins
        self.first_player = first_player
        self.current = first_player
        self.turn = 0
        self.log: list[dict] = []
        self.winner = None
        self.elimination_order: list[int] = []

    # ---------------------------------------------------------------- helpers
    def view(self, i: int) -> View:
        return View(
            me=i,
            hand=tuple(self.players[i].hand),
            coins=tuple(p.coins for p in self.players),
            hidden_counts=tuple(len(p.hand) for p in self.players),
            revealed=tuple(tuple(p.revealed) for p in self.players),
            deck_size=len(self.deck),
            treasury=self.treasury,
            turn=self.turn,
            config=self.config,
        )

    def alive(self):
        return [i for i, p in enumerate(self.players) if p.alive]

    def clockwise_from(self, start: int, exclude=()):
        """Active players clockwise after `start` (start itself excluded)."""
        n = self.config.n_players
        order = [(start + k) % n for k in range(1, n)]
        return [i for i in order if self.players[i].alive and i not in exclude]

    def _pay_from_treasury(self, i: int, amount: int) -> int:
        paid = min(amount, self.treasury)
        self.treasury -= paid
        self.players[i].coins += paid
        return paid

    def _pay_to_treasury(self, i: int, amount: int):
        self.players[i].coins -= amount
        self.treasury += amount

    def lose_influence(self, i: int, cause: str):
        p = self.players[i]
        if not p.alive:
            return
        choice = self.agents[i].reveal(self.view(i)) if len(p.hand) > 1 else p.hand[0]
        if choice not in p.hand:
            choice = p.hand[0]
        p.hand.remove(choice)
        p.revealed.append(choice)
        self.log.append({"turn": self.turn, "event": "lose", "player": i, "card": choice.value, "cause": cause})
        if not p.alive:
            self.elimination_order.append(i)
            self.log.append({"turn": self.turn, "event": "eliminated", "player": i})

    def _swap_proven(self, i: int, ch: Character):
        if not self.config.swap_on_proven_claim:
            return
        p = self.players[i]
        p.hand.remove(ch)
        self.deck.append(ch)
        self.rng.shuffle(self.deck)
        p.hand.append(self.deck.pop())

    def _challenge_phase(self, claimant: int, ch: Character, action: ActionType, actor: int, target, kind: str) -> bool:
        """Offer a challenge on `claimant`'s claim of `ch`. Returns True if the claim stands."""
        for j in self.clockwise_from(claimant):
            if self.agents[j].challenge(self.view(j), claimant, ch, action, actor, target):
                cost = min(self.config.challenge_cost, self.players[j].coins)
                if cost:
                    self._pay_to_treasury(j, cost)
                truthful = ch in self.players[claimant].hand
                self.log.append({"turn": self.turn, "event": "challenge", "kind": kind, "challenger": j,
                                 "claimant": claimant, "character": ch.value, "claim_true": truthful,
                                 "cost": cost})
                if truthful:
                    self._swap_proven(claimant, ch)
                    self.lose_influence(j, "wrong_challenge")
                    return True
                self.lose_influence(claimant, "caught_bluff")
                return False
        return True

    # ---------------------------------------------------------------- turn
    def legal_actions(self, i: int):
        p, c = self.players[i], self.config
        others = [j for j in self.alive() if j != i]
        if p.coins >= c.forced_coup_threshold:
            return [(ActionType.COUP, j) for j in others]
        acts = [(ActionType.INCOME, None), (ActionType.FOREIGN_AID, None), (ActionType.TAX, None),
                (ActionType.EXCHANGE, None)]
        acts += [(ActionType.STEAL, j) for j in others]
        if p.coins >= c.assassinate_cost:
            acts += [(ActionType.ASSASSINATE, j) for j in others]
        if p.coins >= c.coup_cost:
            acts += [(ActionType.COUP, j) for j in others]
        return acts

    def play_turn(self):
        i, c = self.current, self.config
        action, target = self.agents[i].act(self.view(i))
        if (action, target) not in self.legal_actions(i):
            raise IllegalAction(f"player {i}: {action} -> {target}")
        claim = CLAIM[action]
        ev = {"turn": self.turn, "event": "action", "actor": i, "action": action.value, "target": target,
              "claim": claim.value if claim else None,
              "claim_true": (claim in self.players[i].hand) if claim else None}
        self.log.append(ev)
        result = self._resolve(i, action, target, claim)
        ev["result"] = result

    def _resolve(self, i, action, target, claim):
        c, p = self.config, self.players[i]
        if action == ActionType.INCOME:
            self._pay_from_treasury(i, 1)
            return "ok"
        if action == ActionType.COUP:
            self._pay_to_treasury(i, c.coup_cost)
            self.lose_influence(target, "coup")
            return "ok"

        if action == ActionType.ASSASSINATE:
            self._pay_to_treasury(i, c.assassinate_cost)

        if claim is not None and not self._challenge_phase(i, claim, action, i, target, "action"):
            if action == ActionType.ASSASSINATE and c.assassin_refund_on_failed_challenge:
                self._pay_from_treasury(i, c.assassinate_cost)
            return "failed_challenge"
        if not p.alive:
            return "actor_eliminated"
        if target is not None and not self.players[target].alive:
            return "target_eliminated"

        if action in BLOCKERS and self._block_phase(i, action, target):
            return "blocked"

        if action == ActionType.FOREIGN_AID:
            self._pay_from_treasury(i, c.foreign_aid_amount)
        elif action == ActionType.TAX:
            self._pay_from_treasury(i, c.tax_amount)
        elif action == ActionType.STEAL:
            amount = min(c.steal_amount, self.players[target].coins)
            self.players[target].coins -= amount
            p.coins += amount
        elif action == ActionType.ASSASSINATE:
            self.lose_influence(target, "assassinated")
        elif action == ActionType.EXCHANGE:
            self._exchange(i)
        return "ok"

    def _block_phase(self, actor, action, target) -> bool:
        """Returns True if the action is blocked."""
        allowed = BLOCKERS[action]
        blocker, ch, interventor = None, None, False
        if action == ActionType.FOREIGN_AID:
            candidates = [(j, False) for j in self.clockwise_from(actor)]
        else:
            candidates = [(target, False)]
            if self.config.intervention_enabled and action in INTERVENABLE:
                candidates += [(j, True) for j in self.clockwise_from(target, exclude=(actor,))]
        for j, as_int in candidates:
            choice = self.agents[j].block(self.view(j), action, actor, target, as_int)
            if choice is not None and choice in allowed:
                blocker, ch, interventor = j, choice, as_int
                break
        if blocker is None:
            return False
        truthful = ch in self.players[blocker].hand
        ev = {"turn": self.turn, "event": "block", "blocker": blocker, "actor": actor, "target": target,
              "action": action.value, "character": ch.value, "claim_true": truthful,
              "interventor": interventor}
        self.log.append(ev)
        stands = self._challenge_phase(blocker, ch, action, actor, target, "intervention" if interventor else "block")
        ev["stands"] = stands
        if stands and interventor and self.players[blocker].alive:
            ev["reward"] = self._pay_from_treasury(blocker, self.config.intervention_reward)
        return stands

    def _exchange(self, i):
        p = self.players[i]
        drawn = [self.deck.pop() for _ in range(min(2, len(self.deck)))]
        options = p.hand + drawn
        keep = self.agents[i].exchange(self.view(i), list(options), len(p.hand))
        remaining = list(options)
        kept = []
        for ch in keep:
            if ch in remaining and len(kept) < len(p.hand):
                remaining.remove(ch)
                kept.append(ch)
        while len(kept) < len(p.hand):  # invalid choice: keep originals
            kept.append(remaining.pop(0))
        p.hand = kept
        self.deck.extend(remaining)
        self.rng.shuffle(self.deck)

    def advance(self):
        n = self.config.n_players
        for k in range(1, n + 1):
            nxt = (self.current + k) % n
            if self.players[nxt].alive:
                self.current = nxt
                return

    def play(self):
        while self.turn < self.config.max_turns:
            if len(self.alive()) <= 1:
                break
            self.play_turn()
            self.turn += 1
            if len(self.alive()) <= 1:
                break
            self.advance()
        alive = self.alive()
        self.winner = alive[0] if len(alive) == 1 else None
        self.check_invariants()
        return self.winner

    def check_invariants(self):
        c = self.config
        total_coins = self.treasury + sum(p.coins for p in self.players)
        assert total_coins == c.treasury, "coins not conserved"
        assert all(p.coins >= 0 for p in self.players), "negative coins"
        cards = len(self.deck) + sum(len(p.hand) + len(p.revealed) for p in self.players)
        assert cards == c.copies_per_character * len(Character), "cards not conserved"
