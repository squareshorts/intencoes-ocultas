# Intenções Ocultas — rare-bluffer invasion experiment (19 October 2026)

## Status and scientific decision

**Completed.** The primary rare-mutant experiment demonstrates a conditional winning advantage of strategic bluffing at very low scepticism in four-player games. The strict counterfactual rerun confirms that the result is not an artefact of the random-number stream. There is no comparable established advantage at moderate or high scepticism. A three-player follow-up supports the positive result; a five-player follow-up is inconclusive despite frequent false claims. This is a strategy-conditional outcome in a simulator, not a proof of evolutionary invasion under population dynamics.

## Experimental design

- Source: committed frozen model, review branch `review/action-specific-calibration` at `7a9d83415bde469e556adfa14755d97b96f629ff` (parent baseline `269f418`). No changes were made to production agents or engine.
- Four-player primary: **2,500 paired random seeds per cell**, 3 forecasts × 3 scepticism thresholds; 45,000 full games in strict-coupling contrasts.
- Exploratory 3-/5-player tests: **1,500 paired seeds per cell** in each table size; 54,000 further games in strict-coupling contrasts.
- Original ordinary-agent comparisons were also performed at identical sizes and sample counts (99,000 games) as an audit; see below. **Total: 198,000 full games**, excluding smoke tests.
- One focal mutant plus N−1 identically parameterized honest-action residents, contrasted against N all-honest-action players. First player rotates by seed. Only focal `Params.bluff` changes from **0.0** to **0.8**; the mutation is a *propensity to consider* a strategic bluff, not a forced claim.
- All agents share the same threshold within a cell: θ ∈ {0.05, 0.30, 0.50}. Fixed stake bonus 0.15; block-bluff propensity 0.0 except for the preexisting last-influence Sombra survival rule; intervene=0.5; intervention reward=1.
- All three belief policies fixed: `empirical`, `opponent`, and `opponent_action` with development-only frozen size/action offsets. No validation or experiment seeds were used for tuning.
- Endpoint: mean paired difference in focal win probability (mutant minus honest control). CI: nonparametric seed-paired 95% bootstrap. Primary hypothesis tests: exact matched-pair McNemar/sign tests with **Holm familywise adjustment over nine primary cells**. Secondary endpoints count actual false actions and claim outcomes.

## Primary result: four-player games

| Scepticism θ | Forecast | Honest control | Rare bluffer | Δ win (pp), 95% CI | Holm-adjusted p | False actions/game |
|---|---|---:|---:|---:|---:|---:|
| 0.05 | empirical | 25.64% | 30.68% | +5.04 [+3.36, +6.72] | 2.70e-08 | 2.445 |
| 0.05 | opponent | 24.88% | 31.80% | +6.92 [+5.24, +8.56] | 4.00e-15 | 2.502 |
| 0.05 | opponent_action | 25.64% | 31.92% | +6.28 [+4.64, +8.00] | 2.53e-12 | 2.510 |
| 0.30 | empirical | 26.36% | 25.92% | -0.44 [-0.72, -0.16] | 0.0171 | 0.030 |
| 0.30 | opponent | 26.08% | 25.88% | -0.20 [-0.40, -0.04] | 0.25 | 0.017 |
| 0.30 | opponent_action | 26.00% | 25.56% | -0.44 [-0.72, -0.20] | 0.00586 | 0.033 |
| 0.50 | empirical | 24.72% | 24.72% | +0.00 [+0.00, +0.00] | 1 | 0.000 |
| 0.50 | opponent | 24.92% | 24.92% | +0.00 [+0.00, +0.00] | 1 | 0.000 |
| 0.50 | opponent_action | 25.16% | 25.16% | +0.00 [+0.00, +0.00] | 1 | 0.000 |

At θ=0.05, all three adjusted tests reject neutral win-rate difference and gains are approximately **+5.0 to +6.9 percentage points** in the counterfactual-coupled design. At θ=0.30, actual bluffs are exceedingly rare (0.017–0.033 per game); any negative win-rate effect is very small (−0.2 to −0.44 pp), not a general large penalty. At θ=0.50, the strategic bluffer does not choose any false action under the tested policy. Strict coupling then makes every matched game identical, so the measured effect is exactly zero by construction. These statements describe the tested heuristic policy only.

## Cross-size check at low scepticism (θ=0.05)

| Players | Empirical Δ (pp, 95% CI) | Opponent-aware Δ | Frozen action-specific Δ |
|---|---:|---:|---:|
| 3 | +6.67 [+4.67, +8.73] | +7.87 [+5.67, +10.00] | +7.33 [+5.27, +9.40] |
| 4 | +5.04 [+3.36, +6.72] | +6.92 [+5.24, +8.56] | +6.28 [+4.64, +8.00] |
| 5 | +0.53 [-1.47, +2.53] | +1.27 [-0.73, +3.33] | +0.60 [-1.40, +2.67] |

The positive low-scepticism effect is also observed in three-player games. Five-player results show small positive point estimates with 95% CIs spanning zero in all three forecasts, even though the focal player makes approximately three false action claims per game. **No claim that bluffing is neutral or disadvantageous in five-player games is justified by these data.** Table size may change the conversion of successful deception into game wins and should be tested directly.

## Audit: why strict RNG coupling was needed

In the original unmodified `HeuristicAgent.act`, the mutant can consume additional RNG draws while evaluating and rejecting possible bluff actions. When no false claim is actually chosen, this can nevertheless alter later random tie-breaks, resulting in a spurious treatment–control difference. For example, under four-player θ=0.30 opponent-aware policies the ordinary comparison gave Δ=−2.0 pp, while strict counterfactual coupling gave Δ=−0.20 pp. The primary causal contrast therefore uses `CoupledBluffAgent`, an **experiment-only adapter**: evaluate the frozen mutant policy, recompute the honest action from the identical RNG state, and retain the mutant path only when an actual false action is selected. If no false action is selected, the entire focal action and RNG state match the honest control. Assertions checked the equality of all recorded game metrics for every such matched game. The unmodified results are provided as an audit, not as causal estimates.

## Limitations / publication boundary

- This is a rare-mutant **win-probability advantage** in a fixed table. It is not population invasion probability, fixation probability, evolution over generations, α-Rank, or human deception data.
- The model is a specific value-based heuristic that avoids risky bluffs; θ=0.50 therefore yields zero *actual* bluffs, not a demonstration that any arbitrary deceptive opponent can be defeated by scepticism.
- Previously identified action-specific blocking forecast calibration fails one strict held-out condition (11/12), so all findings must be labelled forecast-conditional.
- Three flagged rule assumptions (win condition, Observers, Sombra refund) have not been confirmed with the game designer.
- The cross-size comparisons are exploratory (no multiplicity claims), and only the specified payoff/reward/stake values were examined.

## Reproducibility and status

The archive contains the exact experiment code, seed-level CSVs for both ordinary and strict-coupled comparisons, metadata protocols, frozen calibration coefficients, summary output, and these notes. The 67 relevant tests passed. No production agent code or the historical Exp 2–4 result files were replaced.

```bash
PYTHONPATH=src python experiments/19_bluff_invasion.py --players 4 --games 2500 --boot 2000 --batch 250 --coupled
PYTHONPATH=src python experiments/19_bluff_invasion.py --players 3 --games 1500 --boot 2000 --batch 250 --coupled
PYTHONPATH=src python experiments/19_bluff_invasion.py --players 5 --games 1500 --boot 2000 --batch 250 --coupled
PYTHONPATH=src python experiments/20_summarise_bluff_invasion.py --boots 5000
PYTHONPATH=src pytest -q tests
```

## Next scientifically justified step

Separate the **decision to lie** from the **ability to win by lying**, and test whether rare bluffers retain their advantage when bluffing is more common. Then test a predeclared protection reward manipulation with measured intervention opportunities, before full population-dynamics experiments.
