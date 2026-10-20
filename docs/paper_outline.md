# Paper 1 — outline (target: *Journal of the Royal Society Interface*)

**Working title:** *Rewarded third-party protection under deception: an evolutionary analysis of a hidden-role card game*

Model-only paper. Human-data protocol comes later, for paper 2.
Literature: `literature/review.md`, `literature/references.bib` (72 refs, DOIs verified).

## Core claim (to be tested, not assumed)
Intervenção is the rule that lets any bystander block an attack on someone else, possibly by bluffing, for a small reward. It combines three classic structures:
- a **volunteer's dilemma**: only one player may intervene;
- an **inspection game**: a protection claim can be challenged at a risk;
- **reward-induced deception**: rewarding protection invites fake protection (McNally & Jackson 2013).

No existing model combines all three. Theory of third parties is dominated by *punishment* (Fehr & Fischbacher 2004; Jordan et al. 2016; Roos et al. 2014). Yet people prefer *protecting or compensating victims* (Raihani & Bshary 2015).

## Hypotheses (from literature/review.md, adjusted by the pilot)
- **H1 — reward threshold.** Intervention evolves only above a reward r\*.
  *Pilot (exp1, honest-only intervention):* the selection gradient was positive even at r = 0. This suggests r\* ≤ 0 when interventors are honest card-holders, i.e. "low-cost volunteers" (links to H5). Needs confirmation with proper statistics.
- **H2 — reward invites faked protection.** A higher r raises bluffed interventions. Scepticism, not bluffing, adjusts. P(protection is genuine) may fall as r rises.
- **H3 — verification cost.** A higher challenge cost shifts the population from honest to faked protection. Expect bistability in the (r, challenge cost) plane.
- **H4 — distributional effects.** Intervention lowers coin and survival inequality and delays the first elimination. Per-capita intervention falls with n (3→5), while P(anyone intervenes) holds.
  *Pilot:* first-player advantage ≈ 0 in all conditions. Intervention shortens games slightly.
- **H5 — who protects.** Interventors are mostly real Guardião/Embaixador holders. The share of honest interventions falls with r.

## Structure
1. **Introduction:** third-party punishment vs protection; deception and verification; games as minimal models; the gap.
2. **Model** (ODD protocol in the supplementary material):
   - rules and the assumptions table (`docs/rules_assumptions.md`);
   - the strategy space: bluff rate, Bayesian challenge threshold θ, intervention propensity, bluffed-intervention propensity;
   - fitness = win probability.
3. **Analytic sub-models:** volunteer's-dilemma and inspection-game reductions, giving closed-form predictions to validate the simulations against.
4. **Methods:**
   - empirical game-theoretic analysis (payoff tables over strategy types, sample sizes from Tuyls et al. 2020 bounds);
   - replicator dynamics and α-Rank;
   - Moran/Fermi finite-population dynamics with a selection-strength sweep;
   - pairwise invasibility plots;
   - paired bootstrap over game seeds.
5. **Results:**
   - (i) baseline balance: seat fairness, game length, outcome Gini against a balanced benchmark (Utt & Fort 2002);
   - (ii) the reward ablation;
   - (iii) evolution of honest vs faked protection (H1, H2, H5);
   - (iv) the (r, verification cost) phase diagram (H3);
   - (v) table size n = 3–5 and inequality/survival (H4, Kaplan–Meier).
6. **Robustness:**
   - every ⚠ rule assumption toggled;
   - agent heuristics varied;
   - Sobol sensitivity analysis;
   - a reduced 3-player CFR equilibrium benchmark (OpenSpiel).
7. **Discussion:**
   - design lessons for institutions that reward defenders (bystander programmes, moderation, whistle-blower rewards);
   - limits of a game model;
   - a bridge to paper 2 (human data).

## Findings so far (4 players, rulebook defaults otherwise)
**Exp 2 — invasion with paired bootstrap** (40,000 paired games per cell, 95% CIs; `results/exp2_*.csv`):
- **Honest intervention is favoured at every reward**, even r = 0. Gradient: +0.011 [0.003, 0.020] at r = 0 and +0.025 [0.016, 0.034] at r = 2. A challenge cost of 1 strengthens it.
- **Faked intervention is selected against at every reward** (gradient ≈ −0.057 to −0.060, CIs exclude 0). With θ = 0.25 residents, this goes against H2.
- **Third-party scepticism is a public good:**
  - the θ gradient is ≈ −2.8 (θ grid 0–0.6), steeper with a challenge cost (≈ −2.9);
  - a never-challenge mutant invades θ = 0.6 residents at +1.64 relative fitness;
  - this is the second-order free-rider problem of verification.
- **Action bluffing is selected against** (gradient ≈ −1.82) when residents check claims.

**Exp 3 — co-evolution of five traits** (Wright–Fisher, N = 120, 600 generations, 5 reps per condition; `results/exp3_*.csv`):
- All conditions converge to **honest and trusting** play: bluff ≈ 0.02–0.03, θ ≈ 0.01–0.02. Games lengthen from ~14 to ~50 turns.
- Intervention propensity stays intermediate (0.3–0.6), with large variance between reps, which may be drift.
- The faked-protection share rises with reward and challenge cost (0.15 at r = 0, c = 0; 0.45 at r = 3, c = 1). Suggestive for H2/H3, but with 5 reps and large SDs it is not conclusive. It is also not yet reconciled with exp 2.
- ⚠ **Confound:** the stake bonus (extra scepticism when a claim involves you) is fixed at 0.15. Verification by involved parties is therefore built in and may be what keeps bluffing down. It must evolve too before exp 3 can be interpreted.

**Exp 4 — EGTA over 9 archetypes** (n = 3, 4, 5 × r = 0–2 × c = 0–1; 3,000 games per profile; α-Rank with M = 50 and a 200-sample multinomial bootstrap; replicator rest points from 60 starts; `results/exp4_*.csv`):
- All α-Rank mass falls in the honest, non-sceptical cluster: HonestTrusting, HonestProtector, Pushover. At n = 5 Pushover takes everything (CI [1, 1]). At n = 3–4, the ordering *within* the cluster is not robust (bootstrap CIs 0–1).
- Sceptics are crushed: one HonestSceptic among honest players gets 0–4% of its fair share.
- The replicator keeps HonestProtector at ≈ 0.58 for n = 3, r = 0. Protection mostly vanishes at larger tables and higher r. This contrasts with exp 2's positive gradient; reconcile later.
- ⚠ **Model artifact (found in exp 4):** when bluffing, `HeuristicAgent.act` claims a *random* unheld character, often a weak action such as exchange. "Bluffing" therefore conflates lying with playing worse. A lone Bluffer among Pushovers (who never challenge) gets only 0.60 of fair share at n = 5. Every bluffing result in exp 2–4 is affected. **Fix:** bluff by claiming the most valuable action. Then rerun exp 2–4.

**Bluff-policy fix and smoke-test gate (2026-10-19)** — not passed; the long reruns were not launched.
- Implemented `Params.bluff_target = "strategic"` (the default):
  - an action bluff claims the unheld action maximising gain − P(challenged)·7, where P(challenged) = 1 − `p_holds_public`;
  - a bluffed block or intervention claims the most credible character;
  - `"random"` keeps the pre-fix behaviour, so the 0e270d5 results serve as the "bluff target selection" ablation.
- `stake_bonus` is now an evolving trait in `evolution.TRAITS`, initialised at 0.15.
- Gate: a lone Bluffer among non-sceptical residents, 4,000 games per cell, relative payoff [95% CI]:

  | Residents | n | strategic | random |
  |---|---|---|---|
  | Pushover | 4 | 1.04 [0.99, 1.09] | 0.97 [0.92, 1.02] |
  | Pushover | 5 | 0.69 [0.64, 0.75] | 0.59 [0.54, 0.65] |
  | HonestTrusting | 4 | 0.60 [0.56, 0.65] | 0.49 [0.45, 0.53] |
  | HonestTrusting | 5 | 0.55 [0.50, 0.60] | 0.42 [0.37, 0.46] |

- Diagnosis:
  - stake bonus is not the cause: the stake-0 Bluffer gets 0.83 / 0.70;
  - a Pushover with action bluff 0.5 and nothing else still gets 0.70 / 0.64 against never-challengers.
  - **Remaining artifact:** the `bluff` coin flip replaces the honest action even when the honest action is better, and even when the best bluff's score is negative.
- **Proposed fix (needs the author's go-ahead):** bluff only if the best bluff's score exceeds the best honest option's value, with `bluff` acting as a propensity/temperature. Then rerun the gate before exp 2–4.

**Gate, second attempt (2026-10-19)** — not passed; reruns not launched.
- Changes:
  - a bluff happens only if its score beats the best honest option;
  - P(challenged) = min(1, 2·rate·(1 − p_public)), where rate = Laplace estimate of the table's public challenge frequency (`View.claims`, `View.challenges`).
- Lone focal, 4,000 games per cell:

  | Focal | Residents | n = 4 | n = 5 |
  |---|---|---|---|
  | Bluffer | HonestSceptic | 2.70 | 2.89 |
  | Bluffer | Pushover | 1.05 [0.99, 1.10] | 0.60 |
  | Pushover + bluff 0.5 | Pushover | 0.59 | 0.52 |

- Diagnosis (instrumented, 3,000 games):
  - the bluffer is rarely caught (0.12 caught lies per game);
  - it bluffs Sombra 2.1×/game; each attempt costs 3 coins up front (A4, no refund) and is often blocked by a real Guardião, held by the target or an interventor;
  - it saves for fewer Golpes Diretos (0.81 vs 1.45 per game).
- **Remaining artifact:** `_gain` values an assassination at 7 − 3 = 4 and a steal at its face amount, ignoring P(blocked). Intervention makes blocks *more* likely. This also affects honest play.
- **Proposed fix:** discount steal/assassination gains by the public probability that the target or any eligible interventor holds a blocker. Then re-gate.

**Gate, third attempt — passed (2026-10-19).**
- Change: steal/assassination gains are discounted by P(blocked), computed by card counting over the target and every eligible interventor.
- Result:
  - bluffers invade non-sceptics: 1.31–1.52× fair share, all CIs exclude 1;
  - sceptics resist them: 0.80–0.84.

**Exp 2–4 rerun with the corrected agents** (`experiments/summarise.py`; pre-fix results in `results/ablation_random_bluff/`):
- **Exp 2** (20,000 paired games per cell):
  - bluff gradient −0.25 to −0.27; θ gradient −0.88 to −1.05;
  - intervene and intervene_bluff gradients ≈ 0;
  - **identical across rewards**, i.e. the reward has no effect.
- **Exp 3** (20 reps × 400 generations):
  - bluff ≈ 0.26, θ ≈ 0.12, stake bonus ≈ 0.06;
  - intervention traits drift (≈ 0.5 ± 0.3);
  - 0.01 interventions per game.
- **Exp 4:** α-Rank mass moves to Bluffer / BlufferFakeProtector for every n (they are tied because protection never happens). Wide bootstrap CIs.
- ⚠ **Why intervention vanished — miscalibrated deterrence** (n = 4 diagnostic, 2,000 games):
  - attacks drop from 4.4/game (pre-fix) to 0.53 (intervention on) vs 1.18 (off), so Intervenção halves attacks;
  - but only 8% of the remaining attacks are actually blocked;
  - agents' P(blocked) assumes every eligible holder always intervenes.
  - **Proposed fix:** scale the interventor term by the table's observed intervention rate per opportunity (Laplace estimate from public counts, mirroring the challenge-rate fix). Then re-gate and rerun.
  - The deterrence effect itself is a candidate result, but only once beliefs are calibrated.

## Follow-up calibration audit (2026-10-19)

The diagnostic continuation is documented in
`docs/calibration_2026_10_19.md`. New public block-offer counters prevent
conflating card holding with successful defence. A revised estimate accounts
for a false blocker being exposed by the attacker. In 1,500 four-player
voluntary games with intervention, empirical estimates yielded 1.501 attacks
and 0.056 third-party claims per game. Conditional block-stage forecasts
were 0.371 against 0.361 observed (1,438 evaluated stages). This is only
within-scenario evidence; ex-ante forecasts and heterogeneous-table beliefs
are not yet validated. In held-out heterogeneous 3/4/5-player tests, the model
underestimated standing blocks by 0.112, 0.095 and 0.101, respectively;
prior-strength sensitivity did not eliminate this error. In forced
credible-attack probes (1,100 per cell),
intervention claims vary monotonically with conditional intervention propensity.
The existing compound Bluffer archetype beats HonestSceptic, so the old gate
fails as an archetype contrast; in an action-bluff-only contrast, a theta=0
resident is invadable, while theta=0.3 is inconclusive. Full Experiments 2--4
must NOT be replaced until the held-out gate is passed.

## Status
- [x] Engine, agents, tests (`src/`, `tests/`)
- [x] Pilot experiment 1 (`results/exp1_*.csv`). Superseded by exp 2 for inference.
- [x] Per-game paired bootstrap statistics (`src/intencoes/stats.py`, exp 2)
- [x] Bluffed intervention, bluffing and evolving θ in the strategy space (exp 3)
- [x] Explicit challenge-cost parameter (`RuleConfig.challenge_cost`)
- [ ] Make the stake bonus an evolving trait; rerun exp 3 with ≥20 reps and longer runs
- [ ] Reconcile exp 2 (faked protection selected against) with exp 3 (faked share rises with r)
- [x] EGTA + α-Rank pipeline, n = 3, 4, 5 (exp 4) — pre-fix, see artifact note
- [x] Strategic bluff target + random-mode ablation; stake bonus evolves
- [x] Bluff only when it beats the honest option; table-adaptive challenge risk
- [x] Block-aware valuation; gate passed; exp 2–4 rerun (pre-fix archived as ablation)
- [ ] Complete held-out P(blocked) calibration and trait-isolated gates; only then rerun exp 2–4
- [ ] Moran/Fermi dynamics with a selection-strength sweep
- [ ] Analytic sub-models (volunteer's dilemma, inspection game)
- [ ] Confirm ⚠ rule assumptions with the author

## Opponent-conditioned forecasting and trait-isolated protection (2026-10-19)

Full audit, sampling plan, seed ranges and uncertainty in
`docs/opponent_beliefs_2026_10_19.md`; reproducibility in
`experiments/08_opponent_beliefs.py` and `09_protection_bluff.py`.

- Added seat-indexed, public `(offers, claims, stands)` observations to `View`
  and an independent opponent-policy prior. The forecast handles a challenged
  false blocker halting later defence offers. There is **no hidden hand or
  opponent strategy-parameter access** in the acting agent.
- On separate held-out event snapshots, n=4 mixed-strategy Brier score was
  0.197 (earlier empirical), 0.196 (new prior only), 0.168 (pooled history),
  **0.163** (seat-specific history). 95% game-bootstrap CI for seat-specific
  improvement over pooling: -0.0099 to -0.0007. The oracle's 0.160 is a
  research-only policy-information comparator, not a mathematical bound.
- In all nine held-out populations (850 games each, n=3/4/5 and three
  mixtures), eight Brier scores improved relative to empirical. Seven paired
  CIs excluded zero. Five-player homogeneous was slightly worse and
  inconclusive. Pooled public observations account for most of the gain.
- **The in-policy opportunity problem remains:** in 450-game n=4 mixed-policy
  simulations, the new prior reduced attacks from 1.60 to 1.05 and third-party
  claims from 0.22 to 0.089 per game. Predictions and realized stage outcomes
  are conditional on different policy-selected events in these two arms.
- **Isolated bluff contrast:** raising the propensity for false target blocks
  from 0.05 to 0.80 reduced focal win probability by 0.108 at resident
  challenge threshold theta=0.30 and by 0.144 at theta=0.60, with CIs
  excluding zero (1,600 paired games per arm). False third-party protection
  effects were ~0.004--0.008 lower win probability, but opportunities
  were rare (~0.05--0.09 per focal game). These are exploratory, not complete
  evolutionary selection gradients.
- The `opponent` model remains an **explicit option**, not the default; the
  completed Exp 2--4 CSVs are preserved unchanged. Conditional mixed-policy
  forecast gate partially passed, but the in-policy calibration/exposure
  gate still fails; **NO-GO for replacing main results**.

Additional status:
- [x] Public seat-indexed opponent-response history and ordered block forecast.
- [x] Matched-event, seed-separated mixed-population calibration (3/4/5 players).
- [x] Pool-only vs individual-opponent ablation and research-only policy oracle.
- [x] Trait-isolated target/block and third-party false-protection screen.
- [ ] Demonstrate in-policy calibration and sufficient intervention opportunity
  across heterogeneous mixtures and intervention-reward settings before redoing
  full Experiments 2--4.


## Endogenous opportunity, deterrence, and action-specific forecast gate (2026-10-19)

See `docs/endogenous_opportunities_2026_10_19.md` and reproducible
`experiments/10_endogenous_opportunity.py`–`12_size_holdout.py`. This extension
keeps previous empirical and evolutionary CSVs untouched.

- [x] Randomized first-turn opportunity encouragement with explicit
  assignment/eligibility/uptake, attack stage and third-party offer denominators.
- [x] Anticipation-only ablation: in mixed n=4 `opponent` games attacks rose
  1.056 → 2.054 and standing third-party interventions 0.074 → 0.248/game
  when actors stopped anticipating intervention, actual blocking still active.
- [x] Proper matched-event scoring and game-seed clustered uncertainty on
  29,500 full four-player games, 14,400 additional 3/5-player games and
  7,200 standardized one-turn reward probes.
- [x] Reward-response limitation: immediate intervention Bernoulli policy
  cannot respond to the reward, which affects only future coins/evolution.
- [ ] Action-specific calibration repair before main reruns. Mixed n=4
  natural-play mean block-stage bias +0.008 hides steals +0.095 and Sombra
  -0.088; shifted Sombra error -0.134 (CIs exclude zero). Independent
  shifted n=5 aggregate bias -0.094; broad generalization not established.
- [ ] Once action-specific in-policy performance passes independent
  mixed/shifted 3/4/5-player checks, rerun the expensive Exp 2–4 pipeline.
- [ ] In parallel, draft the mechanism paper and develop a small analytic
  volunteer/inspection model; do not imply simulations prove human behaviour.


## Action-specific public-belief validation (2026-10-19; exploratory, not new Exp 2–4)

The prior opponent-aware forecast had opposite-signed errors for steals and Sombra attacks. `docs/action_specific_calibration_2026_10_19.md` now records a full, independent two-stage calibration sequence. A hypergeometric false-block challenge model, combined with a conservative structural blend and public action/target/table-size offsets, improved conditional prediction on identical pre-block events. The first frozen predictor passed 9/12 prespecified action strata on 16,800 independent games. A second predictor was retrained using new 3/4/5-player development seeds and evaluated on 7,800 *untouched* full games; **11/12 conditions passed**. Remaining shifted three-player Sombra bias was −9.5 percentage points, 95% game-clustered CI [−14.2, −5.2]. Pooled final Brier score was 0.1832 versus 0.1874 for the previous opponent estimator, measured on 7,999 stage observations under the final predictor's own policy. Pooled proper-score gains do not imply action-level calibration.

**Interpretation:** The within-simulator deterrence and opportunity-manipulation mechanisms have support from earlier randomized and anticipation-ablation experiments, but evolutionary selection conclusions remain contingent on unverified behavioural beliefs. Do not repeat Exp 2–4 wholesale as replacements or claim an action-calibration PASS; instead predeclare a small sensitivity design across fixed forecast families, then proceed to analytical reductions, ODD protocol, and discussion of external validity. Do not continue adaptive tuning against completed validation datasets.

## 2026-10-19 — rare-bluffer invasion experiment (frozen policy sensitivity)

See `docs/bluff_invasion_2026_10_19.md` for all estimates, seed counts, exact Holm-adjusted tests, and limitations; reproducibility scripts are `experiments/19_bluff_invasion.py` and `experiments/20_summarise_bluff_invasion.py`. The primary strict-coupling four-player experiment found a +5.04 to +6.92 percentage-point win advantage at low scepticism across the empirical/opponent/action-specific blocking forecasts, with 2,500 paired seeds per condition. Three-player results were positive; five-player advantages were small and inconclusive. Moderate-scepticism effects were close to zero; at high scepticism no false action was selected under this heuristic. Original noncoupled results are retained separately because RNG consumption while considering a rejected bluff can confound outcomes. This is a rare-mutant win-rate sensitivity screen, not finite-population evolution or proof of invasion/fixation. The previous forecast calibration failure and unresolved rule assumptions remain open. Do not replace the original Experiments 2–4 CSVs. Next: frequency-dependent mutant composition, and separately controlled intervention reward/exposure.

## Confirmed rule clarifications — 20 October 2026

A1, A3 and A4 were approved as the study's reference rules: victory goes to the last active-influence holder, Observers have informal voice without formal decisions, and Sombra's three-coin declaration cost is nonrefundable on failed attacks. The model and published simulation summaries already implement these choices, so this is a documentation/interpretation change only. See `docs/rules_assumptions.md` and `README.md`. Historical notes above accurately describe assumptions as unresolved at the time of each earlier experiment; the date-stamped present clarification supersedes that status. The numerical 400-turn cutoff is not part of the physical-game rules.
