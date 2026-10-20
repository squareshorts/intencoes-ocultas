# Intenções Ocultas — manuscript delivery

## Short answer

A **complete computational manuscript draft** and supplement are compiled. The game permits challengeable character claims and third-party protection. Strategic bluffing has a reproducible *conditional* advantage in trusting three- and four-player tables, but that advantage decreases as bluffers become common. An evolutionarily stable mixture is not proven. The results are computational, not evidence about human behaviour.

## New experiment sample

The final frequency/reward study contains 85 profiles × 1,200 = **102,000 complete simulated matches**, plus 5 alternative-rule profiles × 1,200 = **6,000**. The preceding rare-mutant experiment contributes 99,000 strict-coupled matches used as primary evidence and 99,000 uncorrected matches retained for audit only. All 70 tests passed.

## Primary four-player finding, theta=0.05

Blocking policy | Rare-bluffer per-player win advantage | Advantage at 50% frequency | Advantage near all-bluffer
--- | --- | --- | ---
Empirical | +4.38 pp [95% CI +1.86,+7.04] | +3.35 pp [+1.92,+4.73] | -0.08 pp [-2.63,+2.38]
Opponent-aware | +6.94 pp [+4.42,+9.58] | +4.62 pp [+3.17,+6.10] | -1.17 pp [-3.75,+1.17]
Action-specific | +5.75 pp [+3.25,+8.33] | +2.55 pp [+1.16,+4.01] | -2.17 pp [-4.75,+0.25]

Three-player rare advantage was positive with intervals excluding zero; in five-player games it was inconclusive. At high scepticism the agents attempted no false action and the two strategies became indistinguishable in behaviour.

## What is delivered

- `manuscript/main.pdf`: 10-page full scientific draft with references and three figures.
- `manuscript/supplement.pdf`: 4-page technical supplementary methods and numerical tables.
- `manuscript/*.tex`, `references.bib`, PDF figures and `tables_generated.tex`: editable and recompilable sources.
- `src/`, `experiments/`, `tests/`, `requirements.txt`: frozen simulator and all relevant scripts; 70 passing tests.
- `results/frequency_dependence/`: original seed-level observations, protocols, payoffs, curve summaries and 6,000 refund sensitivity games.
- `results/bluff_invasion/`: original prior rare-mutant paired observations; strict-coupled sets are primary, ordinary sets are audit-only.
- `release/SUBMISSION_READINESS_AUDIT.md`: outstanding scientific and administrative issues.

Suggested journal: *Journal of the Royal Society Interface* (candidate; not yet submitted). This is not a guarantee of acceptance or desk review.
