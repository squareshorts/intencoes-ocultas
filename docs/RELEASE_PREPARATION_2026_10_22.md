# Release preparation — 22 October 2026

## Status
Manuscript declaration update committed. This document prepares, but does not constitute, a published release or Zenodo deposit. The repository is private and no public archive DOI is assigned. Do not claim archival completeness solely from a GitHub-generated source ZIP.

## Suggested GitHub release fields
Tag: v1.0.0
Target: paper/frequency-dependent-deception (after synchronizing current Overleaf revision)
Release title: v1.0.0 — Frequency-dependent strategic deception: reproducibility archive
Pre-release: No (once verified)
Latest release: Yes (once verified)

## Release description
Reproducibility archive for "Frequency-dependent strategic deception in a multiplayer hidden-information game with third-party protection."

The study uses agent-based simulations of Intenções Ocultas to evaluate rare-bluffer advantage, frequency-dependent selection, scepticism, multiplayer blocking forecasts, attack avoidance, and third-party protection. The evolutionary results are payoff-derived projections under specified random-matching and imitation assumptions, not observations of human behaviour.

The source tree includes the simulator, analysis scripts, tests, manuscript LaTeX, figures and available summary payoff tables. Seed-level simulation data supporting the article must be supplied separately in the deposited research archive. The primary analysis uses the strict random-history-coupled rare-mutant comparisons; noncoupled runs are historical diagnostics only. Historical Experiments 2–4 are not confirmatory evidence for this manuscript. One held-out action-specific blocking-calibration stratum failed its prespecified criterion.

Funding: CNPq Grant 309589/2023-1 to A.P.; CAPES.
Competing interests: None declared.

## Scientific checks before release
- Synchronize the latest revised Overleaf manuscript and supporting bibliography into GitHub.
- Confirm author list, contributions and affiliations.
- Include complete seed-level frequency and rare-mutant observations in the archival ZIP; do not assume the GitHub tree contains them.
- Confirm all data paths and regenerate figures/tables from archived data where possible.
- Run the project regression tests on the frozen source and record the results.
- Publish a versioned immutable release and deposit the final complete research package into Zenodo.
- Insert the minted Zenodo version DOI into the manuscript before submission.

## Suggested Zenodo record fields
Upload type: Software
Title: Frequency-dependent strategic deception in a multiplayer hidden-information game with third-party protection: Reproducibility archive
Version: 1.0.0
Publication date: actual deposit publication date
Creators: verify all manuscript authors and their exact order before publication
Description: Use the GitHub release description with the model's assumptions and limitations intact
Keywords: agent-based simulation; strategic deception; evolutionary game theory; bluffing; hidden information; third-party protection; reproducibility
Related identifier: matching public GitHub version-tag URL (version, IsSupplementTo or IsSourceOf as appropriate)
License: confirm with authors before choosing; no license is currently established here

## Workflow
1. Sync the current manuscript, prepare and verify the exact archival contents.
2. Make GitHub public if using direct GitHub-Zenodo integration (explicit owner action).
3. Enable Zenodo GitHub integration before publishing the release, if using its automated ingestion.
4. Create GitHub release with tag v1.0.0 targeting the verified commit.
5. Verify Zenodo deposit, files, creator order, version DOI, and concept DOI.
6. Replace DOI placeholder in manuscript and make a final post-deposition source update without changing the tagged research snapshot.
