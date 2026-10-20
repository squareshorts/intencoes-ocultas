# Intenções Ocultas — manuscript readiness audit

**Status:** Complete, compiled **manuscript draft**, not yet a journal-ready submission. Proposed venue: *Journal of the Royal Society Interface* (scope/format should be checked against current guidance at submission). All conclusions concern computer-controlled game agents; no human outcomes were measured.

## Verification completed

- **102,000 new games:** frequency profiles and reward sweep: 45 four-player profiles, 30 three-/five-player profiles, and 10 additional reward profiles, 1,200 games/profile; all seat/first-player scheduling bias fixed before final analysis. Earlier phase-locked pilot was rejected and excluded from every public deliverable.
- **6,000 further games:** alternative Sombra-refund rule, 5 profiles of 1,200 games each. Compared to default qualitatively; seeds are independent, so numerical difference is not paired causal inference.
- **198,000 preceding games:** 99,000 strict-coupling rare-mutant counterfactual simulations used for inference; another 99,000 originally noncoupled games retained only to expose the RNG-stream confound.
- **70/70 regression tests passed.** The frozen game model is unchanged; scripts 21--24 calculate results from completed simulations. All three belief models were frozen before the composition study.
- Correct per-player profile-payoff estimators, seed-clustered bootstrap intervals, three types of figures and their source tables, Fermi/replicator sensitivity.
- PDF main manuscript (10 pages, 186-word abstract) and supplement (4 pages) compiled with pdflatex and biber. Visually inspected figures, principal table, front page and supplementary numerical tables; compilation produced no overfull warnings.

## Scientific conclusions warranted

1. Under low scepticism, rare strategic action-bluffing increases focal winning probability in three- and four-player populations; results are positive across all three freezing blocking forecasts, with 95% CIs above zero.
2. In four-player populations, the bluffer's payoff advantage remains positive at intermediate composition (x=0.5) but decreases at high prevalence. The estimated near-all-bluffer selection advantage has 95% intervals crossing zero: **stable interior coexistence is not established**.
3. Five-player rare invasion is not statistically established, even though the all-bluffer boundary favors bluffers under the tested low-scepticism policies.
4. At theta=0.50, the action-selection heuristic attempts no actual bluffs; the two parameterized agent types are behaviourally identical. Small computed selection differences arise from finite-sample label noise.
5. Attacks and third-party intervention events become scarcer in high-bluffer compositions. The latter is chiefly an **exposure** outcome, not direct evidence that defenders are less willing to help conditional on being asked.
6. Replicator and Fermi imitation predictions are **conditional transformations of game payoffs**, not observed generational evolution or fixation, and depend on specified matching, population size and selection intensity.

## Issues to resolve before submission

- **Authors:** confirm all coauthors, precise affiliations, CRediT contributions, corresponding author and email; this draft carries an explicit placeholder. Do not attribute authorship to a generative AI.
- **Game rules:** confirm the three flagged rules in `docs/rules_assumptions.md`: victory condition, permissible Observer participation and refund/nonrefund of failed Sombra attack cost. Refund-only sensitivity cannot establish robustness to the other two.
- **Repository/data:** current source is in a private GitHub review branch. Make the full source, exact seeded simulation observations, plots and manuscript openly available with a versioned Zenodo DOI or equivalent before journal submission. Archive raw results outside of Git if needed; the ZIP contains them. No DOI exists for this study at present.
- **Independent external validation:** no human experiment; all conclusions are within the simulator. This is acceptable for a theoretical paper only if framed as an illustrative computational game, not a behavioural finding.
- **Calibration exception:** the action-specific blocker forecast failed 1/12 predefined held-out action calibration strata (three-player Sombra); retain this limitation and avoid declaring it fully calibrated.
- **Statistical boundaries:** profile-frequency comparison and reward sweep are exploratory. Do not call candidate interior equilibria proven ESS; the negative upper boundary has a confidence interval including zero. Do not overinterpret independent-seed refund effect.
- **Venue and formalities:** apply final journal LaTeX template, exact reference style, word limits, figures, declarations, AI assistance disclosure, funder-specific policies and open-data requirements. This document is a neutral LaTeX draft, not a journal typeset proof.
- **Original broad project:** prior Experiments 2--4 and the original hypothesis set H1--H5 about emergence of rewarded third-party protection, fake protection, verification costs and inequality are **not validated** by these new experiments. The new manuscript investigates a narrower question and does not claim to have settled those hypotheses.

## Research audit decisions

- Rejected prebalance pilot files were neither committed nor included in the final manuscript dataset.
- Old noncoupled rare-mutant runs are marked audit-only.
- Existing historical Experiments 2--4 preserved with no replacements.
- No changes made to the model coefficients or agent mechanism while fitting new frequency results.
- This is a simulation-based theoretical manuscript draft, not a completed accepted or ready-to-submit article.
