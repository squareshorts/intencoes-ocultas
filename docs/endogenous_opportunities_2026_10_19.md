# Endogenous calibration, deterrence, and randomized opportunities

**Date:** 2026-10-19. **Source:** private `squareshorts/intencoes-ocultas`,
`269f418599a1bc5024a9ce6053043a61d728ffbb`, plus the previous
calibration/opponent-belief diagnostics. **This is a simulation-only diagnostic,
not a replacement for historical Experiments 2–4 or evidence of human behaviour.**

## Scientific decision

**The intervention-opportunity milestone is complete and the deterrence mechanism
is established *within this simulator*. General in-policy action-specific
calibration is still inadequate for promoting the opponent-aware model to the
main evolutionary experiments.** In particular, a small calibration error
averaged over steals and assassinations conceals large errors of opposite sign.
No model hyperparameters were retuned on the results presented below.

The previous opponent-belief estimator was trained on 550 independent mixed
four-player games and its five priors were fixed at
`opponent_intervene=0.5`, `opponent_intervene_bluff=0.15`,
`opponent_block_bluff=0.4`, `block_prior_strength=1`, and
`opponent_pool_strength=2`. It remains opt-in; the code's main experiment
default is `empirical`.

## Design and estimands

`experiments/10_endogenous_opportunity.py` generated **59 distinct four-player
conditions**, each comprising **500 full games** (29,500 games); common game
seeds were 640000–640499, distinct from the earlier prior-selection and
matched-event holdouts. Three population types (homogeneous, mixed, shifted),
three public-belief models (empirical, pooled, individual), and randomized
first-turn truthful-steal encouragement doses 0, 0.5 and 1.0 were examined at
intervention reward 1. Subsets additionally varied the reward (0 or 2) or
whether actors anticipated third-party protection during **action choice**.
Actual blocking behaviour was unchanged in the anticipation ablation. Another
arm disabled actual third-party intervention while keeping the actor
*blind* to it, to separate the rule's realized consequences from its expected
ones. These are model perturbations, not observed human treatments.

The intervention is an **encouragement** evaluated at each agent's first
surviving turn: with assigned probability, an agent *holding Comerciante* is
instructed to make a truthful steal against a randomly chosen living opponent
with coins, if the action is legal. Eligibility depends on the current game
state; some instructed actions never reach blocking after a challenge. Hence
assignment is randomized *conditional on an agent receiving a first decision*,
but actual defender offers and protection are endogenous and must be measured,
not assumed. This changes action selection and the selected hand distribution;
forced stages do not constitute a natural-play sample.

`experiments/12_size_holdout.py` independently generated **24 additional
conditions** with 600 games each (14,400 full games) for **3- and 5-player
tables**, seeds 850000–850599 for n=3 and 870000–870599 for n=5. The
opponent priors were held fixed. `forced_probe` additionally provides 1,200
conditioned, one-turn truthful Comer steals per mixture and each reward 0/1/2:
7,200 one-turn probes; all three reward arms share exactly the same accepted
seed/deck draws. These probes condition explicitly on opener seat 0 holding
Comerciante, unlike unconstrained new games.

The four-player comparisons use **paired game-seed bootstrap** (1,000 draws)
for differences in per-game action or protection counts; this is not pairing
individual block stages across different policies. **Within any fixed arm**,
old and new forecasts are scored on the *same* pre-offer game snapshots,
clustered by game. Predictions never inspect opponents' true hidden cards.
Outcomes are whether a block *stands*, not merely whether a card is held or a
block is claimed. Stages are conditional on the attack surviving the initial
claim challenge. Raw stage observations are available for regeneration and
independent checking.

## Four-player opportunity and anticipation results

For the `opponent` belief, reward=1, **no encouragement**:

| Population | Choice regime | Attacks/game | Third-party offers/game | Claims/game | Standing interventions/game |
|---|---|---:|---:|---:|---:|
| Mixed | Normal anticipation | 1.056 | 0.424 | 0.088 | 0.074 |
| Mixed | Anticipation suppressed | 2.054 | 1.086 | 0.278 | 0.248 |
| Shifted | Normal anticipation | 1.344 | 0.338 | 0.174 | 0.122 |
| Shifted | Anticipation suppressed | 2.050 | 0.734 | 0.334 | 0.264 |

Suppressing anticipation increases **attacks per game** by +0.998
[95% paired CI +0.844, +1.160] in the mixed population and +0.706
[+0.470, +0.894] in shifted. Third-party defense **offers** increase by
+0.662 [+0.530, +0.808] and +0.396 [+0.296, +0.504], respectively.
Standing third-party protection increases by +0.174 [+0.126, +0.222] and
+0.142 [+0.096, +0.192]. This is compelling **within-model** evidence for
anticipatory deterrence suppressing intervention opportunities, but changes in
action selection can also affect later wealth, challenges and card states.
It is not an isolated estimate of human altruism or of a genetic selection
coefficient.

Random encouragement increases offers in a dose-dependent way. With normal
anticipation, moving dose 0 → 1 changes third-party offers/game from 0.424 to
0.836 (mixed; delta +0.412 [95% CI +0.274, +0.546]) and from 0.338 to
0.976 (shifted; delta +0.638 [+0.534, +0.744]). Standing intervention
increases by +0.220 [+0.170, +0.274] and +0.286 [+0.230, +0.342]. Thus the
mechanism is measurable when opportunity exposure is manipulated; it does not
establish that an evolutionary intervention trait will be favored.

## The key result: action-specific calibration failures

Under **natural selection of actions** (`dose=0`, `opponent` estimator,
4 players, 500 independent games per mixture):

| Population and action | Reached stages | Predicted P(standing block) | Observed | Bias (prediction − observation), 95% game-clustered CI |
|---|---:|---:|---:|---:|
| Mixed, steal | 254 | 0.465 | 0.370 | **+0.095** [+0.035, +0.152] |
| Mixed, assassination | 229 | 0.217 | 0.306 | **−0.088** [−0.140, −0.039] |
| Shifted, steal | 237 | 0.376 | 0.409 | −0.033 [−0.118, +0.031] |
| Shifted, assassination | 296 | 0.272 | 0.405 | **−0.134** [−0.188, −0.084] |

Mixed *pooled* error of +0.008 across all reached stages is misleading because
steals and assassinations have opposing biases. The shifted pooled error is
−0.089 [−0.132, −0.043], confirming failure across a new distribution of the
same simulated archetypes. Encouragement improves global block-stage Brier but
changes the action and hand distribution: 732 of the 1,126 mixed dose-1
reached stages are first-turn forced truthful steals, of which 93.4% were
successfully blocked. These events cannot be pooled with natural attacks to
claim natural-game calibration.

The improved opponent estimator can still have a lower Brier score on
conditional stages than empirical: in shifted four-player natural play the
in-policy Brier is 0.211 (empirical alternative on *those same stages* is
0.231), even with an 8.9 percentage-point forecast bias. Proper-score
improvement does **not** imply action-specific calibration.

### Independent 3- and 5-player test (natural play)

| Players | Mixture | Reached stages | Mean forecast bias | 95% game-clustered CI |
|---|---|---:|---:|---:|
| 3 | Mixed | 292 | +0.012 | [−0.043, +0.063] |
| 3 | Shifted | 319 | −0.048 | [−0.098, −0.004] |
| 5 | Mixed | 790 | +0.009 | [−0.019, +0.033] |
| 5 | Shifted | 972 | **−0.094** | [−0.122, −0.068] |

No additional prior fitting was performed on these test sets. All natural
mixture means are vulnerable to the same action-mix cancellation and require
mode-specific inspection in a future preregistered replication.

## What varying the intervention reward demonstrates—and what it cannot

In **one-turn** conditioned truthful-steal probes, the reward 0, 1 and 2 arms
produced the *same* number of immediate third-party blocking offers and
claims, by construction. For the mixed population there were 471 intervention
offers, 209 claims and 208 standing interventions per 1,200 probes; for
shifted, 795 offers, 466 claims and 388 standing interventions. The target
blocked first in 897/1,200 mixed and 598/1,200 shifted probes, preventing
many possible third-party offers. A challenged but unsuccessful first block
can also exclude later intervention attempts.

The reason for immediate reward invariance is **mechanistic**, not an
empirical finding about incentives: `HeuristicAgent.block()` uses an
`intervene` Bernoulli policy that does not read `intervention_reward`.
Rewards influence an agent's subsequent wealth and, in an evolutionary
model, may eventually change frequencies of strategy types with different
intervention propensities. These diagnostics do **not** demonstrate a direct
reward-sensitive decision rule or test an evolved equilibrium.

The full-game reward sweep (0→2) produced nearly zero change in the number
of mixed-population attacks or third-party offers with opponent forecasting
and no encouragement (paired offers delta −0.002, CI −0.012 to +0.008),
with similarly small shifts under shifted composition. Do not interpret
lack of an acute effect as a test of evolutionary reward selection.

## Reproducibility and safeguards

- Three new self-contained scripts: `10_endogenous_opportunity.py` (main
  conditions and standardized probes), `11_analyse_opportunity.py` (paired
  game contrasts, action-level calibration, reliability curves), and
  `12_size_holdout.py` (independent 3/5-player validation).
- `results/policy_gate/*.csv` are summarized outputs; the much larger raw
  game/stage records are in `results/raw/policy_gate_{games,stages}.csv`
  (regenerable, not in the Git patch).
- Tested 27 focused regression tests plus 1,500 complete-game invariants
  across random and opponent-aware strategies, n=3/4/5. The reconstructed
  baseline does not contain the repository's original `tests/test_engine.py`;
  the full upstream suite must also be executed in the owner's checkout.
- The original `results/exp*.csv` were **not** modified. The private GitHub
  `main` branch was not changed. Unconfirmed source-rule assumptions A1,
  A3, A4 were not silently resolved.
- This run is an exploratory mechanistic diagnosis, not a preregistered
  hypothesis test. Bootstrap intervals describe simulation variation;
  neither agent-policy uncertainty nor external human validity is covered.

## Concrete follow-on decision

**Opportunity-manipulation gate: PASS.** The experiment produces increased,
measured third-party offers and standing protection, and the deterrence ablation
has substantial paired effects under both mixed compositions.

**Action-conditional in-policy calibration gate: FAIL.** The failure persists in
independent mixtures and 3/5-player size tests; aggregate Brier or mean bias
are insufficient acceptance criteria. The model is now scientifically
characterized, not ready to replace the primary evolutionary results.

**Next constrained implementation:** preregister action-specific calibration
objectives on fresh development seeds; improve the probabilistic representation
of the assassin target's block and challengers' responses without reading hidden
cards, while keeping a fixed held-out 3/4/5-player, mixed/shifted test. Compare
against the existing empirical and opponent_pool baselines on identical events
*and* under each active policy. Validate reward effects through evolving
intervention traits, not by expecting an immediate reward response from the
unchanged Bernoulli policy. Paper writing, intervention-mechanism description,
and analytical volunteer/inspection models can proceed in parallel—expensive
full Experiment 2–4 replacements should not precede that targeted validation.

## Re-run commands

```powershell
$env:PYTHONPATH = 'src'
py -3.13 -m pytest -q tests/test_calibration.py tests/test_opponent_beliefs.py tests/test_policy_gate.py
py -3.13 experiments/10_endogenous_opportunity.py --games 500 --probes 1200 --boot 800 --keep-raw
py -3.13 experiments/11_analyse_opportunity.py --boot 1000
py -3.13 experiments/12_size_holdout.py --games 600 --boot 800
```
