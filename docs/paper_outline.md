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

## Status
- [x] Engine, agents, tests (`src/`, `tests/`)
- [x] Pilot experiment 1 (`results/exp1_*.csv`): positive selection for honest intervention at r = 0, 1, 2. The CIs are not yet valid (shared seeds across cells).
- [ ] Per-game paired bootstrap statistics
- [ ] Add bluffed intervention and evolving θ to the strategy space (H2, H3)
- [ ] Explicit challenge cost parameter (H3); currently the only cost is the lost influence
- [ ] EGTA + α-Rank pipeline; Moran dynamics
- [ ] Analytic sub-models
- [ ] Confirm ⚠ rule assumptions with the author
