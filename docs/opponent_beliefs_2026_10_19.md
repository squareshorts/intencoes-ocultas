# Opponent-policy beliefs: conditional holdout and isolated protection-bluff tests

Date: 2026-10-19. Lineage: `squareshorts/intencoes-ocultas@269f418` plus
`intencoes_calibration_269f418.patch`. This is a diagnostic continuation,
**not** a replacement for the historical Experiments 2--4.

## Code/model changes

- `View.player_block_history` records each publicly offered defender's
  `(seat, action, role, offers, claims, standing_claims)`; it contains no
  hidden card truth, agent label, or `Params` of another player. The
  researcher-only `Game.log` still has card truth for audits.
- New `Params.block_prediction="opponent"`: independent priors about other
  players' willingness to block truthfully or as a bluff, conditional on
  card-counting probabilities; these priors are **not** copied from the
  attacker's own defensive strategy. A two-level shrinkage estimate combines
  each player's public history with other public offers in the same action/role.
- The defence forecast now respects the engine's *first claimant stops the
  search* rule: even a false block that is challenged prevents subsequent
  third-party offers. It estimates the chance of claiming and the chance of
  standing given a claim separately, in actual clockwise order. It still
  approximates card and challenge dependencies.
- Mechanistic ablations: `opponent_prior` (public-card-counting/behavioural
  prior only), `opponent_pool` (aggregate public history but no seat identity),
  `opponent` (per-seat history), alongside the previous `empirical`,
  `card_only`, and `none`. The `oracle_policy` reference is available **only**
  to offline diagnostic code and knows the simulated *strategy parameters*,
  never the opponents' current hidden cards. It is not a strict statistical
  performance ceiling.
- The default `Params.block_prediction` is still `empirical`: the new policy
  has **not** been promoted for the main evolutionary experiments.

## Independent, matched-event predictive calibration

The **same pre-offer View snapshots** and **same realized outcomes** are
scored under all forecasting policies. This removes the earlier comparison's
selection bias from different models choosing different attacks. No
prediction function queries hidden card truth or changes the original
simulated episode. The episode-generating acting agents use the existing
`empirical` policy, not the new policy.

- Development sample: 550 heterogeneous four-player games, seeds
  200000--200549, yielding 922 attack block stages. An explicit 48-cell
  grid was selected **only on this sample** by Brier score:
  `opponent_intervene=0.5`, `opponent_intervene_bluff=0.15`,
  `opponent_block_bluff=0.4`, `block_prior_strength=1`,
  `opponent_pool_strength=2`.
- Test samples: 850 games per cell across 3/4/5 players and
  `homogeneous`, `mixed`, and `shifted` mixtures: **7,650 held-out games**;
  seeds 330000+ (not overlapping the training, earlier holdout, or gate).
  The `mixed` roster contains Default, HonestProtector, Bluffer,
  Pushover and BlufferFakeProtector. The shifted roster substitutes
  FakeProtector, HonestTrusting, ScepticProtector and HonestSceptic, while
  retaining BlufferFakeProtector. The shifted group tests a different
  distribution of the existing simulated archetypes, not novel agent algorithms.
- Metric: Brier score = mean squared error for predicting whether any
  protective claim **stands**, conditional on an attack having reached the
  blocking phase. Uncertainty uses 600 **game-clustered, paired bootstrap**
  resamples (games can contribute multiple block stages). Each policy is
  scored on exactly the same stage observations. The denominator is *stages*,
  not all declared attacks or opportunities.

Four-player held-out comparison (lower Brier is better):

| Population | Stages | Previous empirical | New prior only | Pooled public history | Individual opponent | Oracle policy |
|---|---:|---:|---:|---:|---:|---:|
| Homogeneous | 830 | 0.218 | 0.212 | 0.214 | 0.214 | 0.212 |
| Mixed | 1,432 | 0.197 | 0.196 | 0.168 | **0.163** | 0.160 |
| Shifted | 1,387 | 0.216 | 0.213 | 0.181 | **0.176** | 0.181 |

The four-player mixed attack-stage outcome rate was 0.497. The historical
forecast was 0.403 (bias -0.094), versus 0.507 for the new model
(bias +0.011). The new-versus-empirical paired Brier difference was
-0.0342 [95% CI -0.0467, -0.0239]. The **extra seat-identity contribution**
(new minus pooled) was -0.0049 [95% CI -0.0099, -0.0007]. Thus most of the
improvement comes from using pooled *public behaviour* and correctly
accounting for offer order; person-specific updating supplies a smaller
additional improvement in this population.

Across all nine held-out test conditions, the opponent-aware model had a
lower Brier score in eight. Seven of those improvements excluded zero under
the paired 95% intervals versus the empirical baseline. The five-player
homogeneous Brier score worsened slightly (0.209 to 0.211), with an interval
that included zero. The four-player homogeneous test also showed a larger
forecast bias despite a small Brier improvement. **Do not claim calibration
universally across population compositions.**

## Endogenous-policy diagnostic (NOT a matched calibration comparison)

With the beliefs actually used in action selection, both policies were
simulated with **450 games per scenario and policy** (seeds 400000+),
otherwise identical rule settings. Because selected attacks differ,
forecast/outcome pairs across these arms have different denominators and
**must not** be directly compared as paired predictive performance.

| Four-player population | Belief | Attacks/game | Third-party claims/game | Predicted vs actual standing blocks at reached stages |
|---|---|---:|---:|---|
| Mixed | Empirical | 1.604 | 0.220 | 0.432 vs 0.544 |
| Mixed | Opponent | 1.053 | 0.089 | 0.353 vs 0.315 |
| Shifted | Empirical | 1.484 | 0.291 | 0.393 vs 0.608 |
| Shifted | Opponent | 1.222 | 0.156 | 0.336 vs 0.427 |

The new policy changes the encounter distribution and generally **reduces**
observed third-party protection opportunities. This is compatible with
anticipatory deterrence but does not yet show improved strategy or an
adequate intervention-opportunity base for evolutionary inference. The
shifted population retains a -0.091 conditional forecast bias even in the
new policy's own encounters.

## Trait-isolated protection-bluff screen

`experiments/09_protection_bluff.py` compares a seat-0 focal agent with
otherwise identical residents, holding all settings fixed **except one**
trait. Four-player simulations use the tuned opponent priors above and
1,600 games **per control/treatment arm** (paired initial seeds), three
challenge thresholds. A game-clustered, paired 1,500-bootstrap 95% interval
is reported for the *difference in seat-0 win probability*; it is **not** a
confidence interval for stationary evolutionary fixation probability.

| Changed trait | Resident challenge threshold | Difference in focal win probability [95% CI] |
|---|---:|---:|
| Target `block_bluff` 0.05 -> 0.80 | 0.00 | +0.011 [-0.003, +0.025] |
| Target `block_bluff` 0.05 -> 0.80 | 0.30 | **-0.108 [-0.127, -0.090]** |
| Target `block_bluff` 0.05 -> 0.80 | 0.60 | **-0.144 [-0.163, -0.125]** |
| Third-party `intervene_bluff` 0 -> 0.80 | 0.00 | -0.006 [-0.011, -0.002] |
| Third-party `intervene_bluff` 0 -> 0.80 | 0.30 | -0.008 [-0.013, -0.003] |
| Third-party `intervene_bluff` 0 -> 0.80 | 0.60 | -0.004 [-0.008, -0.002] |

The third-party fake-protection effect is very small, with only ~0.05--0.09
focal-player intervention offers per game. The tests are exploratory,
without multiplicity adjustment or external behavioural calibration. Do not
interpret these estimates as general selection gradients across all strategy
mixtures.

## Decision

**Conditional mixed-population prediction gate: improved (limited PASS).**
**General in-policy calibration and opportunity gate: NOT YET PASSED.**
**Full Experiments 2--4 replacement: NO-GO.** Preserve their original CSVs.

Next work should explicitly test the *in-policy* forecast under exogenously
varied opportunity frequency, intervention rewards, and population mixtures,
and separate the effects of anticipation from intervention actually
occurring. Consider stronger public opponent-policy learning only if it
improves game-clustered held-out Brier beyond the pooled-only ablation.
Eventually test source-rule assumptions A1, A3 and A4 against the author.

## Reproducibility

```powershell
# From repo root, with the patch applied and Python dependencies installed:
$env:PYTHONPATH="src"
py -3.13 -m pytest -q tests/test_calibration.py tests/test_opponent_beliefs.py
py -3.13 experiments/08_opponent_beliefs.py --train 550 --games 850 --policy-games 450 --boot 600
py -3.13 experiments/09_protection_bluff.py --games 1600
```

New outputs are isolated under `results/opponent_beliefs/`, including
per-block-stage held-out event records and fitted prior choices.
