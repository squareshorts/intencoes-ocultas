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
- [ ] Bluff only when it beats the honest option (gate failed without this); re-gate, then rerun exp 2–4
- [ ] Moran/Fermi dynamics with a selection-strength sweep
- [ ] Analytic sub-models (volunteer's dilemma, inspection game)
- [ ] Confirm ⚠ rule assumptions with the author
