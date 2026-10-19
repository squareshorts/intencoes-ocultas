# Behavioural calibration and intervention-opportunity audit

Date: 2026-10-19. Baseline: `squareshorts/intencoes-ocultas@269f418`.
This is a diagnostic continuation, not a replacement for Experiments 2--4.

## Scientific question

The previous model replaced the event "a defender possesses a blocker" with
"the attack will be blocked". The original observation of approximately 8%
blocked attacks uses declared attacks as its denominator; it is not the
conditional probability of a standing block **after the challenge phase**.
We therefore distinguish (i) attack declarations, (ii) surviving claims that
reach the block stage, (iii) target offers, (iv) intervention offers, (v)
block claims, and (vi) block claims that stand after possible challenges.

## Changes made in this diagnostic branch

- Added public per-action, per-defender-role counters `(offers, stands)` to
  `View.block_history`. All card-truth information remains in the
  *research-only* `Game.log` (`block_offer.has_blocker`); an agent sees only
  public counters and its own hand.
- Added `Params.block_prediction = empirical | card_only | none`. The
  `card_only` and `none` options are mechanistic ablations. The empirical
  estimate is a Beta-style smoothed **standing block per offer**, with a weak
  card-counting/behavioural prior. The observed rate is not multiplied again
  by card availability. Sequential candidate decisions are approximated as
  independent; shared deck constraints are not represented exactly.
- Corrected the prior for an exposed fake blocker: the acting player may
  deterministically challenge a claimed blocking character on the basis of
  its own hand and publicly revealed cards. This is essential for terminal
  Sombra targets that attempt desperate false blocks.
- Corrected the public card-counting posterior. Corrected the bluff expected
  payoff: successfully challenged action bluffs lose both the proposed gain
  and one influence, plus the non-refundable Sombra cost under rule A4.
- Valued foreign aid net of estimated blocking; added
  `bluff_target=random_isolated` to vary **only** action-bluff candidate choice.
  `bluff_target=random` is retained solely as the historically confounded
  legacy policy, not as a causal control.
- Added reproducible full-game and forced-opportunity diagnostics and
  instrumented evolutionary behaviour output with offers per game.

## Focused simulations (diagnostic, not publication-level inference)

Four players, common seeds within each scenario, 1,500 voluntary games per
cell, unchanged default rule assumptions and default heuristic traits:

| Belief model | Intervention | Attacks/game | Third-party claims/game | Block-stage P(stood): forecast vs observed | Stages |
|---|---|---:|---:|---|---:|
| card_only | off | 3.123 | 0 | 0.407 vs 0.455 | 3,718 |
| card_only | on | 0.841 | 0.003 | 0.248 vs 0.281 | 595 |
| empirical | off | 2.359 | 0 | 0.353 vs 0.366 | 2,627 |
| empirical | on | 1.501 | 0.056 | 0.371 vs 0.361 | 1,438 |
| none | off | 4.683 | 0 | 0 vs 0.566 | 6,006 |
| none | on | 4.719 | 0.479 | 0 vs 0.672 | 6,127 |

The `none` model is intentionally misspecified; its higher attack rate is
not evidence that it is strategically superior. Conditional stage forecasts
were collected **after** action challenges. The earlier decision-time
forecast for empirical/intervention-on was 0.429, versus 0.361 eventual
blocking *among attacks reaching that stage*. Its stronger mismatch warns
against claiming complete calibration of anticipatory deterrence.

A forced-opportunity experiment drew valid decks conditioned on a truthful
first-turn attack claim, fixed the initial coins to 3 for every player, and
observed one attack per game (1,100 replicates per cell). Third-party
intervention *claims per forced attack* were:

| Intervene conditional on having blocker | Steal | Assassination |
|---|---:|---:|
| 0 | 0 | 0 |
| 0.5 | 0.164 | 0.130 |
| 1 | 0.259 | 0.216 |

Claim counts are not all successful blocks. These results verify that the
intervention rule has a measurable behavioural effect under standardized
exposure. They are conditioned on the attacker having a legitimate action
card and are not representative of ordinary full-game encounter rates.

## Bluffing gate and confounding

In 1,700 games per comparison, the original **Bluffer archetype** scored
relative fitness 1.485 [1.343, 1.643] against Pushover and 1.885
[1.710, 2.078] against HonestSceptic (Wilson-based 95% intervals on focal
win probability, transformed to ratios). This gate **fails** if interpreted
as evidence that sceptics suppress this *compound archetype*. Importantly,
Bluffer differs from HonestSceptic in action-bluff propensity, block-bluff
propensity, and scepticism; its success cannot be attributed to action
bluffing alone.

In 1,800 games per cell of a trait-isolated diagnostic, the focal player
changed **only action-bluff propensity** from 0.02 to 0.5 relative to
resident strategies:

| Resident challenge threshold theta | Relative fitness [95% CI] |
|---|---|
| 0 | 1.183 [1.068, 1.311] |
| 0.15 | 1.036 [0.932, 1.151] |
| 0.30 | 0.968 [0.869, 1.078] |
| 0.45 | 1.042 [0.938, 1.158] |
| 0.60 | 1.069 [0.963, 1.188] |

These diagnostic intervals do **not** establish selective disadvantage
against sceptics; for theta >= 0.15 they generally include neutral fitness.

## Held-out population-mixture stress test

The initial four-player calibration does not generalize without qualification.
Using 650 games per condition, strategies varied across seats and seeds from
`Default`, `HonestProtector`, `Bluffer`, `Pushover` and
`BlufferFakeProtector` (no fitting to the held-out outcomes):

| Table size | Blocking stages | Forecast | Observed | Forecast minus observed |
|---|---:|---:|---:|---:|
| 3 | 651 | 0.413 | 0.525 | -0.112 |
| 4 | 1,091 | 0.419 | 0.514 | -0.095 |
| 5 | 1,474 | 0.388 | 0.489 | -0.101 |

The 4-player heterogeneous prior sensitivity test (`block_prior_strength`
0, 1, 2, 4) generated forecast minus observed gaps of -0.197, -0.120,
-0.095, -0.105, respectively. The test conditions themselves induce different
attack-selection patterns, so these are descriptive policy-specific gaps,
not a fitted common calibration curve.

The likely structural limitation is that an agent's own `Params` currently
stand in for other players' propensity to make truthful or bluffed defence
claims. This assumption is acceptable as a simple homogeneous-agent prior,
but not as a demonstrated general predictor of heterogeneous defensive
strategies. Future work needs a separate opponent-policy prior or posterior
based on public behavior, preferably benchmarked against an oracle that
knows the simulated strategy composition, with an independent held-out set.

## Decision and remaining requirements

**NO-GO for replacing Experiments 2--4 now.** Mechanistic instrumentation
and conditional block-stage forecasting are substantially improved. Before
large evolutionary runs, resolve the demonstrated heterogeneous-table calibration failure and test
both action-bluff and protection-bluff isolated contrasts.
Treat within-game public rates as sparse estimates, especially when attacks
are deterred. Preserve the original CSVs unchanged. Confirm A1, A3, and A4
with the game author before treating rule assumptions as settled.

Reproduce with:

```powershell
py -3.13 -m pytest -q
py -3.13 experiments/05_calibration.py --games 1500 --probes 1100 --gate 1700
py -3.13 experiments/06_scepticism_gate.py --games 1800
py -3.13 experiments/07_holdout.py --games 650
```
