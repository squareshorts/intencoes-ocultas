"""Agent strategies.

HeuristicAgent is a parametric strategy family whose parameters are the
quantities the paper varies (bluffing, scepticism, intervention propensity).
Its scepticism uses card counting: the chance that a claimant actually holds
the claimed character, given every card the agent can see.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from math import comb, exp, log

from .engine import Agent, View
from .rules import BLOCKERS, CLAIM, INTERVENABLE, ActionType, Character

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
    """Public posterior P(claimant holds ch), averaging over opponents' private hands.

    Publicly unseen cards include all active hidden hands plus the deck. Do not
    subtract a hypothetical challenger's hand without subtracting its expected
    character counts as well; that changes the posterior incoherently.
    """
    revealed = [card for hand in view.revealed for card in hand]
    k = view.config.copies_per_character - revealed.count(ch)
    h = view.hidden_counts[claimant]
    unseen = view.deck_size + sum(view.hidden_counts)
    if k <= 0 or h <= 0 or unseen < h:
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

    def _gain(self, view, act):
        """Expected coin-equivalent value of an action, net of the chance it is blocked.

        Steal and assassination are discounted by P(blocked): the chance, from this agent's
        view, that the target or any eligible interventor holds a blocking character.
        The assassination cost is paid even when blocked (A4).
        """
        c, (action, target) = view.config, act
        if action == ActionType.TAX:
            return c.tax_amount
        if action == ActionType.EXCHANGE:
            return EXCHANGE_VALUE
        p_ok = 1.0 - self._p_blocked(view, action, target)
        if action == ActionType.STEAL:
            return p_ok * (min(c.steal_amount, view.coins[target]) if target is not None else 0)
        return p_ok * INFLUENCE_VALUE - c.assassinate_cost  # ASSASSINATE

    def _p_blocked(self, view, action, target):
        """P(at least one hidden card of the potential blockers is a blocking character)."""
        c = view.config
        if self.p.bluff_target == "random":
            return 0.0  # pre-fix valuation ignored blocks
        blockers = set(BLOCKERS[action])
        seen = list(view.hand) + [x for r in view.revealed for x in r]
        k = sum(c.copies_per_character - seen.count(ch) for ch in blockers)
        unseen = view.deck_size + sum(n for j, n in enumerate(view.hidden_counts) if j != view.me)
        who = [target]
        if c.intervention_enabled and action in INTERVENABLE:
            who += [j for j in view.active if j not in (view.me, target)]
        h = sum(view.hidden_counts[j] for j in who)
        if k <= 0 or unseen <= 0 or h <= 0:
            return 0.0
        h = min(h, unseen)
        return 1.0 - comb(unseen - k, h) / comb(unseen, h)

    def _bluff_score(self, view, act):
        """Expected gain of a bluffed action minus expected loss if challenged.

        P(challenged) = riskiness of the claim (1 - p_holds_public) scaled by how often this
        table has challenged so far (Laplace estimate; prior 0.5 gives scale 1).
        """
        rate = (view.challenges + 1) / (view.claims + 2)
        p_challenged = min(1.0, 2 * rate * (1.0 - p_holds_public(view, view.me, CLAIM[act[0]])))
        return self._gain(view, act) - p_challenged * INFLUENCE_VALUE + self.rng.random() * 1e-6

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
    bluff_target: str = "strategic"  # strategic, random_isolated, or random (confounded legacy)
    block_prediction: str = "empirical"  # empirical, opponent, opponent_pool, opponent_prior, card_only, none
    block_prior_strength: float = 2.0  # pseudo-offers anchoring the public success-rate estimate
    # Policy priors for OTHER players. These do not inherit this player's own
    # defensive traits and must not be inferred from hidden simulator labels.
    opponent_intervene: float = 0.5
    opponent_intervene_bluff: float = 0.1
    opponent_block_bluff: float = 0.3
    opponent_pool_strength: float = 2.0  # pseudo-observations from other public offers
    opponent_challenge_threshold: float = 0.25  # public policy prior, not actual opponent trait
    opponent_challenge_stake_bonus: float = 0.15
    # Conservative structural correction. The complete mechanistic model is
    # available as an ablation; blending limits policy-induced distribution
    # shifts until the heterogeneous-policy assumptions are learnable.
    opponent_challenge_weight: float = 0.25
    # Log-odds adjustments: (steal target 2, steal target 1,
    # assassination target 2, assassination target 1). Fit on development
    # games only. Zero is the unfitted mechanistic forecast.
    action_block_offsets: tuple[float, float, float, float] = (0., 0., 0., 0.)
    # Public table-size refinement. Order: 3p steal, 3p Sombra,
    # 4p steal, 4p Sombra, 5p steal, 5p Sombra.
    size_block_offsets: tuple[float, float, float, float, float, float] = (0.,)*6


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
        c, coins = view.config, view.coins[view.me]
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
        # Preserve the historical random-action branch; it is NOT an isolated ablation.
        if self.p.bluff_target == "random":
            if bluffs and self.rng.random() < self.p.bluff:
                return self.rng.choice(bluffs)
            if honest:
                return honest[0]
            return self._fallback_action(view)
        if self.p.bluff_target not in ("strategic", "random_isolated"):
            raise ValueError(f"unknown bluff_target {self.p.bluff_target!r}")

        fallback_value = self._fallback_value(view)
        honest_value = max([self._gain(view, a) for a in honest] + [fallback_value])
        if bluffs and self.rng.random() < self.p.bluff:
            # Both modes use identical valuation, acceptance rule, honest policy
            # and blocking beliefs. Only the candidate selection differs.
            if self.p.bluff_target == "random_isolated":
                candidate = self.rng.choice(bluffs)
            else:
                candidate = max(bluffs, key=lambda a: self._bluff_score(view, a))
            if self._bluff_score(view, candidate) > honest_value:
                return candidate
        if honest:
            best_honest = max(honest, key=lambda a: self._gain(view, a) + self.rng.random() * 1e-6)
            if self._gain(view, best_honest) >= fallback_value:
                return best_honest
        return self._fallback_action(view)

    def _fallback_value(self, view):
        aid = self._gain(view, (ActionType.FOREIGN_AID, None))
        income = self._gain(view, (ActionType.INCOME, None))
        return self.p.foreign_aid * aid + (1 - self.p.foreign_aid) * income

    def _fallback_action(self, view):
        if self.rng.random() < self.p.foreign_aid:
            return ActionType.FOREIGN_AID, None
        return ActionType.INCOME, None

    def _gain(self, view, act):
        """Coin-equivalent expected payoff *conditional on the claim surviving*.

        A blocked Sombra action still spends its three coins under assumption A4.
        Claims challenged before the block phase are handled in _bluff_score.
        """
        c, (action, target) = view.config, act
        if action == ActionType.INCOME:
            return min(1, view.treasury)
        if action == ActionType.FOREIGN_AID:
            return (1.0 - self._p_blocked(view, action, target)) * min(c.foreign_aid_amount, view.treasury)
        if action == ActionType.TAX:
            return min(c.tax_amount, view.treasury)
        if action == ActionType.EXCHANGE:
            return EXCHANGE_VALUE
        if action == ActionType.STEAL:
            return (1.0 - self._p_blocked(view, action, target)) * min(c.steal_amount, view.coins[target])
        if action == ActionType.ASSASSINATE:
            return (1.0 - self._p_blocked(view, action, target)) * INFLUENCE_VALUE - c.assassinate_cost
        if action == ActionType.COUP:
            return INFLUENCE_VALUE - c.coup_cost
        raise ValueError(f"unsupported action {action!r}")

    def predicted_block_probability(self, view, action, target):
        """Publicly auditable attack forecast, conditional on reaching the block phase."""
        return self._p_blocked(view, action, target)

    def _block_card_probability(self, view, player, action):
        """Probability player holds >=1 legitimate blocker using private/public counts."""
        blockers = set(BLOCKERS[action])
        seen = list(view.hand) + [card for hand in view.revealed for card in hand]
        k = sum(view.config.copies_per_character - seen.count(ch) for ch in blockers)
        unseen = view.deck_size + sum(n for j, n in enumerate(view.hidden_counts) if j != view.me)
        h = view.hidden_counts[player]
        if k <= 0 or unseen <= 0 or h <= 0:
            return 0.0
        return 1.0 - comb(unseen - k, h) / comb(unseen, h)

    def _card_only_block_probability(self, view, action, target):
        """Historical, over-pessimistic P(any potential holder); kept for ablation."""
        if action == ActionType.FOREIGN_AID:
            who = [j for j in view.active if j != view.me]
        else:
            who = [target]
            if view.config.intervention_enabled and action in INTERVENABLE:
                who += [j for j in view.active if j not in (view.me, target)]
        blockers = set(BLOCKERS[action])
        seen = list(view.hand) + [card for hand in view.revealed for card in hand]
        k = sum(view.config.copies_per_character - seen.count(ch) for ch in blockers)
        unseen = view.deck_size + sum(n for j, n in enumerate(view.hidden_counts) if j != view.me)
        h = sum(view.hidden_counts[j] for j in who)
        if k <= 0 or unseen <= 0 or h <= 0:
            return 0.0
        return 1.0 - comb(unseen - k, h) / comb(unseen, h)

    def _ordered_defenders(self, view, action, target):
        """Order of offers from Game._block_phase (important after a failed bluff)."""
        n = view.config.n_players
        if action == ActionType.FOREIGN_AID:
            return [((view.me + k) % n, "aid") for k in range(1, n)
                    if (view.me + k) % n in view.active]
        candidates = [(target, "target")]
        if view.config.intervention_enabled and action in INTERVENABLE:
            candidates += [((target + k) % n, "intervention") for k in range(1, n)
                           if (target + k) % n in view.active
                           and (target + k) % n != view.me]
        return candidates

    def _fake_block_survival(self, view, blocker, action, target, claimed):
        """P(no challenge | a defender FAKELY claims `claimed`).

        The attacker makes a deterministic card-counting challenge; each
        other challenger is integrated over *their unknown private copies*
        using a finite hypergeometric recursion. Conditioning the fake
        blocker to hold NO legitimate blocker makes remaining claimed copies
        available to challengers. No hidden game state or policy label enters.

        Thresholds for other challengers are fixed public policy priors. This
        computes block-claim survival, not challenge truth or overall action
        survival; a true block always stands even when challenged.
        """
        if claimed not in BLOCKERS[action]:
            raise ValueError("character cannot block this action")
        if blocker == view.me:
            return 0.0
        # The actor is always in the challenge order and uses known own cards.
        own_evidence = p_holds(view, blocker, claimed)
        own_threshold = self.p.challenge_threshold + self.p.stake_bonus
        if own_evidence == 0.0 or own_evidence < own_threshold:
            return 0.0
        seen = list(view.hand) + [card for cards in view.revealed for card in cards]
        remaining = view.config.copies_per_character - seen.count(claimed)
        unknown = view.deck_size + sum(h for i, h in enumerate(view.hidden_counts) if i != view.me)
        # The declared false blocker has none of the blocking characters,
        # in particular none of `claimed`. Condition on this absence.
        unknown -= view.hidden_counts[blocker]
        if remaining > unknown or unknown < 0:
            return 0.0  # conditioning event impossible
        # Number of claimed cards already publicly revealed (private to nobody)
        publicly_seen = sum(cards.count(claimed) for cards in view.revealed)
        challengers = [k for k in view.active if k not in (view.me, blocker)]
        # Challenge order is immaterial to *whether any* challenge occurs.
        states = {(unknown, remaining): 1.0}
        for k in challengers:
            size = view.hidden_counts[k]
            updated = {}
            for (N, K), mass in states.items():
                if size > N:
                    continue
                for copies in range(max(0, size-(N-K)), min(size, K)+1):
                    prob = comb(K, copies) * comb(N-K, size-copies) / comb(N, size)
                    # The opponent knows its own copies plus publicly revealed.
                    available = view.config.copies_per_character - publicly_seen - copies
                    other_unseen = view.deck_size + sum(view.hidden_counts) - size
                    if available <= 0 or other_unseen < view.hidden_counts[blocker]:
                        evidence = 0.0
                    else:
                        evidence = 1.0 - comb(other_unseen-available, view.hidden_counts[blocker]) / comb(other_unseen, view.hidden_counts[blocker])
                    threshold = self.p.opponent_challenge_threshold
                    if k == target or k == view.me:
                        threshold += self.p.opponent_challenge_stake_bonus
                    if evidence == 0.0 or evidence < threshold:
                        continue
                    key = (N-size, K-copies)
                    updated[key] = updated.get(key, 0.0) + mass * prob
            states = updated
            if not states:
                return 0.0
        return max(0.0, min(1.0, sum(states.values())))

    def _block_claim_prior(self, view, j, action, mode, defender_policy=None,
                           challenge_model="legacy", target=None):
        """(P(claim), P(claim and stand)) before observing this defender's offers.

        The public prior is independent of the attacker's own defensive traits.
        `defender_policy` is allowed only in offline oracle diagnostics; no
        opponent strategy parameters are contained in View.
        """
        q = self._block_card_probability(view, j, action)
        if defender_policy is None:
            intervention = self.p.opponent_intervene
            intervention_bluff = self.p.opponent_intervene_bluff
            block_bluff = self.p.opponent_block_bluff
        else:
            intervention = defender_policy.intervene
            intervention_bluff = defender_policy.intervene_bluff
            block_bluff = defender_policy.block_bluff
        if mode == "intervention":
            honest, fake = intervention, intervention_bluff
        elif mode == "target":
            honest, fake = 1.0, block_bluff
            if action == ActionType.ASSASSINATE and view.hidden_counts[j] == 1:
                fake = 1.0
        else:  # foreign aid
            honest, fake = 1.0, block_bluff * 0.5
        honest = max(0., min(1., honest))
        fake = max(0., min(1., fake))
        if challenge_model == "mechanistic":
            # A false blocker selects the most publicly credible character;
            # ties are random (tiny RNG tiebreak in _credible_block). Use an
            # equal mixture over tied claims, without sampling a hidden hand.
            credibility = {ch: p_holds_public(view, j, ch) for ch in BLOCKERS[action]}
            best = max(credibility.values())
            choices = [ch for ch, p in credibility.items() if abs(p-best) < 1e-12]
            survival = sum(self._fake_block_survival(view, j, action, target, ch)
                           for ch in choices) / len(choices)
        elif challenge_model == "legacy":
            claim = max(BLOCKERS[action], key=lambda ch: p_holds_public(view, j, ch))
            evidence = p_holds(view, j, claim)
            threshold = self.p.challenge_threshold + self.p.stake_bonus
            challenge_rate = (view.challenges + 1) / (view.claims + 2)
            survival = (0.0 if evidence == 0 or evidence < threshold
                        else 1.0 - challenge_rate)
        else:
            raise ValueError(f"invalid challenge model {challenge_model!r}")
        p_true = q * honest
        p_fake = (1.0 - q) * fake
        return p_true + p_fake, p_true + p_fake * survival

    def _opponent_block_probability(self, view, action, target, history_model="individual", challenge_model="legacy"):
        """Per-defender public posterior with ordered first-claim stopping.

        A false claim that is challenged still PREVENTS offers to later players
        in this engine. Consequently, the probability of reaching the next
        defender is P(no claim), not P(no successful block). Counts of offers,
        claims and stood claims must be estimated separately.
        """
        if history_model not in ("individual", "pooled", "none"):
            raise ValueError(f"unsupported history model {history_model!r}")
        individual = {(j, a, mode): (n, c, s)
                      for j, a, mode, n, c, s in view.player_block_history}
        pooled = {}
        for (j, a, mode), (n, c, s) in individual.items():
            aggregate = pooled.setdefault((a, mode), [0, 0, 0])
            aggregate[0] += n
            aggregate[1] += c
            aggregate[2] += s
        if history_model == "none":
            individual, pooled = {}, {}
        elif history_model == "pooled":
            # Identity-blind ablation: retain only aggregate public offers.
            # Every defender has the same population information for a mode.
            individual = {}
        own_weight = max(0., self.p.block_prior_strength)
        peer_weight = max(0., self.p.opponent_pool_strength)
        p_reached, p_stands = 1.0, 0.0
        for j, mode in self._ordered_defenders(view, action, target):
            prior_claim, prior_stand = self._block_claim_prior(
                view, j, action, mode, challenge_model=challenge_model, target=target)
            prior_cond = prior_stand / prior_claim if prior_claim else 0.0
            n, c, s = individual.get((j, action, mode), (0, 0, 0))
            total_n, total_c, total_s = pooled.get((action, mode), (0, 0, 0))
            # Leave the focal player's observations OUT of the population pool.
            # This avoids reusing the same response as independent evidence.
            peer_n, peer_c, peer_s = total_n - n, total_c - c, total_s - s
            peers_claim = ((peer_c + own_weight * prior_claim) / (peer_n + own_weight)
                           if peer_n + own_weight else prior_claim)
            peers_cond = ((peer_s + own_weight * prior_cond) / (peer_c + own_weight)
                          if peer_c + own_weight else prior_cond)
            weight = own_weight + peer_weight
            p_claim = ((c + own_weight * prior_claim + peer_weight * peers_claim) / (n + weight)
                       if n + weight else prior_claim)
            p_cond = ((s + own_weight * prior_cond + peer_weight * peers_cond) / (c + weight)
                      if c + weight else prior_cond)
            p_claim = max(0., min(1., p_claim))
            p_cond = max(0., min(1., p_cond))
            p_stands += p_reached * p_claim * p_cond
            p_reached *= (1.0 - p_claim)
        return max(0., min(1., p_stands))

    def oracle_policy_block_probability(self, view, action, target, defender_params):
        """Research diagnostic only: knows defensive *policies*, not cards.

        Never call this from act(), challenge(), or the game engine. The
        mapping is supplied by the evaluator and is not available in View.
        """
        reached, stood = 1.0, 0.0
        for j, mode in self._ordered_defenders(view, action, target):
            claim, success = self._block_claim_prior(view, j, action, mode,
                                                      defender_policy=defender_params[j])
            stood += reached * success
            reached *= 1.0 - claim
        return stood

    def _p_blocked(self, view, action, target):
        """Estimated P(a block stands | action reaches the block phase).

        Offers and successful blocks are *public* counts. Each per-offer
        posterior already includes the probability the player owns a card;
        we must not multiply that empirical rate by card availability again.
        The product across eligible players is an independence approximation.
        """
        if action not in BLOCKERS:
            return 0.0
        if self.p.bluff_target == "random":
            return 0.0  # legacy random policy bypassed block-aware valuation
        if self.p.block_prediction == "none":
            return 0.0
        if self.p.block_prediction == "card_only":
            return self._card_only_block_probability(view, action, target)
        if self.p.block_prediction == "opponent":
            return self._opponent_block_probability(view, action, target)
        if self.p.block_prediction in ("opponent_challenge", "opponent_action"):
            structural = self._opponent_block_probability(view, action, target,
                                                           challenge_model="mechanistic")
            if self.p.block_prediction == "opponent_challenge":
                return structural
            traditional = self._opponent_block_probability(view, action, target)
            w = max(0.0, min(1.0, self.p.opponent_challenge_weight))
            base = (1.0-w) * traditional + w * structural
            if action in (ActionType.STEAL, ActionType.ASSASSINATE):
                index = (0 if action == ActionType.STEAL else 2) + (view.hidden_counts[target] == 1)
                if base <= 0.0 or base >= 1.0:
                    return base
                size_index = (view.config.n_players - 3)*2 + (0 if action == ActionType.STEAL else 1)
                offset = self.p.action_block_offsets[index] + self.p.size_block_offsets[size_index]
                return 1.0 / (1.0 + exp(-(log(base / (1.0-base)) + offset)))
            return base
        if self.p.block_prediction == "opponent_pool":
            return self._opponent_block_probability(view, action, target, "pooled")
        if self.p.block_prediction == "opponent_prior":
            return self._opponent_block_probability(view, action, target, "none")
        if self.p.block_prediction != "empirical":
            raise ValueError(f"unknown block_prediction {self.p.block_prediction!r}")
        if action == ActionType.FOREIGN_AID:
            candidates = [(j, "aid") for j in view.active if j != view.me]
        else:
            candidates = [(target, "target")]
            if view.config.intervention_enabled and action in INTERVENABLE:
                # Target gets the first chance; third parties follow clockwise.
                candidates += [((target + offset) % view.config.n_players, "intervention")
                               for offset in range(1, view.config.n_players)
                               if (target + offset) % view.config.n_players in view.active
                               and (target + offset) % view.config.n_players != view.me]
        p_unblocked = 1.0
        history = {(a, mode): (offers, stands) for a, mode, offers, stands in view.block_history}
        challenge_rate = (view.challenges + 1) / (view.claims + 2)
        weight = max(0.0, self.p.block_prior_strength)
        for j, mode in candidates:
            q = self._block_card_probability(view, j, action)
            if mode == "intervention":
                p_honest, p_bluff = self.p.intervene, self.p.intervene_bluff
            elif mode == "target":
                p_honest, p_bluff = 1.0, self.p.block_bluff
                if action == ActionType.ASSASSINATE and view.hidden_counts[j] == 1:
                    p_bluff = 1.0
            else:
                p_honest, p_bluff = 1.0, self.p.block_bluff * 0.5
            # In particular, a last-influence Sombra target will nearly always
            # *claim* a bluff-block, but the actor may deterministically expose it.
            # Predict the claimed blocker by the defender's public credibility rule.
            claim = max(BLOCKERS[action], key=lambda ch: p_holds_public(view, j, ch))
            my_threshold = self.p.challenge_threshold + self.p.stake_bonus
            my_evidence = p_holds(view, j, claim)
            bluff_survival = (0.0 if my_evidence < my_threshold or my_evidence == 0
                              else 1.0 - challenge_rate)
            prior = q * p_honest + (1.0 - q) * p_bluff * bluff_survival
            offers, stands = history.get((action, mode), (0, 0))
            estimate = (stands + weight * prior) / (offers + weight) if offers + weight else prior
            p_unblocked *= (1.0 - max(0.0, min(1.0, estimate)))
        return 1.0 - p_unblocked

    def _bluff_score(self, view, act):
        """Expected bluff payoff, accounting for lost action *and* lost influence.

        The historical score deducted influence cost but retained action gain
        even when the challenge succeeded. For Sombra, the up-front cost is
        also lost on a successful challenge under default assumption A4.
        """
        rate = (view.challenges + 1) / (view.claims + 2)
        p_challenged = min(1.0, 2 * rate * (1.0 - p_holds_public(view, view.me, CLAIM[act[0]])))
        challenge_loss = INFLUENCE_VALUE
        if act[0] == ActionType.ASSASSINATE and not view.config.assassin_refund_on_failed_challenge:
            challenge_loss += view.config.assassinate_cost
        return ((1 - p_challenged) * self._gain(view, act)
                - p_challenged * challenge_loss + self.rng.random() * 1e-6)

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
