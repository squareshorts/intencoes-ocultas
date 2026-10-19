# Action-specific public blocking forecasts: development and two independent validations

**Date:** 19 October 2026. **Source baseline:** `squareshorts/intencoes-ocultas`, commit `269f418599a1bc5024a9ce6053043a61d728ffbb` plus the cumulative calibration and endogenous-opportunity patch. **Status: exploratory simulation research, not new evolutionary results.** Earlier Experiments 2–4 files were preserved. This document supersedes the open action-specific work item in `docs/HANDOFF.md`.

## Executive decision

**The action-specific calibration objective is substantially improved but did not fully pass.** The first frozen model passed 9/12 in-policy action-level holdout cells. A second version, trained on new development data across 3/4/5-player tables and evaluated on entirely fresh seeds, passed **11/12**. The remaining failure was **three-player, shifted-composition Sombra attacks: prediction − observation = −0.0947**, with a game-bootstrap 95% CI **[−0.1423, −0.0515]**. On those identical events the previous `opponent` estimator had an error of −0.1442. The improved Brier score (0.2302 vs 0.2457) does **not** erase the calibration failure.

The new estimator **must remain opt-in**. The default `Params.block_prediction` is unchanged (`empirical`), and the existing `results/exp2*`, `exp3*`, and `exp4*` are untouched. There is no sound basis for describing any present evolutionary result as a result of this new policy until a declared sensitivity design has been evaluated.

## Mechanism and information boundaries

`HeuristicAgent._fake_block_survival` integrates out the unknown private copies of a claimed blocking character among potential challengers, conditional on the claiming defender not possessing a legitimate blocker. The acting attacker's challenge is evaluated deterministically from its own hand, public revelations, and scepticism threshold. Unknown challengers' card counts are integrated with a finite hypergeometric recursion using fixed *public* challenger-policy priors (`opponent_challenge_threshold=0.25`, `opponent_challenge_stake_bonus=0.15`). This is **not** an oracle for opponents' actual private threshold parameters. True blocks stand even if challenged; challenged false blocks prevent later intervention offers because the engine stops at the first blocking claim.

`block_prediction="opponent_challenge"` exposes the unblended mechanistic model as an ablation. That complete mechanistic model proved unstable under its own action selection on development games, despite its interpretable structure. The active opt-in proposal, `block_prediction="opponent_action"`, conservatively blends **25% mechanistic** and **75% historical opponent-specific** estimates, then applies a monotone log-odds shift. The first four shifts distinguish steal/Sombra and whether the target has one or two live influences. A second set of six shifts distinguishes action type at each public table size, n=3/4/5. All calibration coefficients are fitted **offline from game snapshots**, never from an opponent's hidden cards at the time of play.

The 25% weighting and log-odds adjustment were selected during **exploratory development**, after the unblended candidate failed its development screen. They were held fixed in subsequent held-out evaluations. They should not be described as an analytically derived evolutionary mechanism or as universally optimal.

## Samples and decisions

1. The first new four-player training set comprised **3,200** normal-play games (1,600 mixed and 1,600 shifted) under the old `opponent` policy, with seed starts 1,350,000 and 1,370,000. A separate 2,400-game development screen used starts 1,390,000 and 1,410,000, under both acting policies. Four shrunken action-by-target-influence offsets were frozen in `results/action_calibration/frozen_fit.json` (SHA256 in that file).
2. The first **independent** holdout comprised 1,400 games for each of 12 combinations of n=3/4/5, population=mixed/shifted and active policy=old/new: **16,800 games**. Starts were `3,000,000 + n*100,000 + (20,000 if shifted else 0)`; the run was resumed after an execution timeout, retaining seven completed checkpoints. No coefficients were adjusted using this holdout. The gate was **FAIL, 9/12**: mixed three-player Sombra (+0.075), shifted four-player steals (−0.072), shifted five-player steals (−0.094). `results/action_calibration/heldout_score.csv`, `heldout_policy.csv`, and `heldout_gates.csv` contain complete *summaries*; raw individual stage predictions for the first seven checkpointed arms were not retained and must be regenerated if required. The `stage_count=17807` in `heldout_decision.json` sums all checkpointed arms; do not confuse this with the partial raw export.
3. A second development cycle was opened explicitly because transfer across table size failed. **6,600** fresh, in-policy games were generated (1,100 for each combination n=3/4/5 × mixed/shifted), with base start `4,100,000 + n*100,000 + (20,000 if shifted else 0)`. A fixed ridge penalty of 20 was applied to six public size-by-action log-odds adjustments. The held-out 3-million-series observations were not used as fit labels. A separate 3,000-game development screen used the corresponding `4,900,000` base. Ten of twelve point errors in this screen were within ±7 points; this was an exploratory screen, not a validation claim.
4. The **final untouched** holdout for version 3 consisted of 1,300 independently seeded, full games for each n × population combination: **7,800 games** with base start `6,000,000 + n*100,000 + (20,000 if shifted else 0)`. It evaluated only the frozen size-aware model as the *acting policy*, and scored that model against the previous opponent model on identical pre-block events. Six complete raw per-stage prediction files are available as `results/action_calibration/final_stages_{n}_{population}.csv`. No hyperparameter was adjusted after inspecting these files. Gate: **FAIL, 11/12**, sole failure noted above.

The gate was set before each holdout: at least 150 blocking stages per action stratum, **absolute prediction-minus-observation gap ≤0.07**, and **Brier score no worse than the `opponent` estimator by >0.01 on identical stages**. A pointwise criterion across 12 noisy independent strata is stringent, but it was not relaxed post hoc. CIs in the results are game-clustered bootstrap intervals (not independent-stage intervals); they quantify stochastic simulation uncertainty, not epistemic model uncertainty or external validity.

## Final size-aware action-level validation, natural-play blocking stages

| Players | Mixture | Action | Stages | Gap (new) | Gap (old opponent) | Δ Brier (new − old) | Gate |
|--:|---|---|--:|--:|--:|--:|---|
| 3 | mixed | steal | 699 | +0.007 | +0.087 | −0.0074 | pass |
| 3 | mixed | Sombra | 322 | +0.006 | −0.040 | −0.0037 | pass |
| 3 | shifted | steal | 500 | −0.066 | +0.009 | +0.0043 | pass |
| 3 | shifted | Sombra | 395 | **−0.095** | −0.144 | −0.0155 | **FAIL** |
| 4 | mixed | steal | 861 | +0.055 | +0.090 | −0.0046 | pass |
| 4 | mixed | Sombra | 374 | +0.018 | −0.065 | −0.0037 | pass |
| 4 | shifted | steal | 957 | −0.041 | −0.021 | +0.0013 | pass |
| 4 | shifted | Sombra | 406 | −0.038 | −0.127 | −0.0156 | pass |
| 5 | mixed | steal | 1174 | +0.040 | +0.042 | −0.0026 | pass |
| 5 | mixed | Sombra | 596 | +0.030 | −0.033 | +0.0006 | pass |
| 5 | shifted | steal | 1136 | −0.055 | −0.064 | +0.0006 | pass |
| 5 | shifted | Sombra | 579 | −0.022 | −0.105 | −0.0186 | pass |

The 7,999 reached blocking stages across the six final arms yield **pooled, descriptive Brier scores 0.1832 (new) and 0.1874 (old)**. The difference is a stage-weighted summary, not a predeclared pooled-significance test. Action-specific calibration must never be inferred from aggregate performance alone. The largest remaining bias's 95% game-clustered CI [−0.142, −0.052] excludes zero.

## Reproducibility, dependencies and tests

- `experiments/action_calibration_common.py` handles policy-matched simulations, deterministic pre-offer scoring, penalized fitting, clustered resampling, and per-game denominators.
- `13_fit_action_calibration.py` fits four offsets on fresh four-player samples; `14_validate_action_calibration.py` retains the first failed 12-stratum holdout (with checkpoint/resume support).
- `15_fit_size_calibration.py` fits six size-by-action offsets on fresh 3/4/5-player development samples; `16_validate_size_calibration.py` retains the **one-time** frozen final validation (complete raw predictions saved per arm); `17_summarise_action_calibration.py` displays both holdouts without reruns.
- `results/action_calibration/frozen_size_fit.json` contains all coefficients and their fingerprint. Do not overwrite it with fitted coefficients from holdout samples.
- `results/action_calibration/logs/` records the rejected full-mechanistic development attempt and the final development and holdout runs. Earlier reported calibration rounds remain in separate prior audit documents.
- Tests: **60 passed** in Python 3.13.5, including reconstructed original upstream functional tests and 36 focused regression tests. The reconstructed `tests/test_engine.py` is verification-only and was **not included in the Git patch** because that file already exists in the remote repository.
- The code uses the existing simulation-only Python dependencies (`numpy`, `pandas`, `scipy` for earlier experiments, `pytest` for tests). No external human observations or labels were used.

## Remaining scientific issue and recommendation

The unresolved error is not a missing code path. It is **public-belief misspecification under endogenously selected targets and mixed private strategy policies**. The current game supplies limited public evidence early enough for a player to infer whether a particular opponent is likely to protect or bluff. A more complex learned forecast could overfit the simulator's own archetype and action-selection rules, particularly after multiple adaptive calibration cycles. Do not keep retuning fixed tolerances until a holdout happens to pass.

For the paper, the clean strategy is to **declare a small sensitivity comparison between the `empirical`, `opponent`, and size-aware `opponent_action` policies**, preserving the historical experiments as diagnostic baselines. Report whether opportunity suppression, deterrence, and the direction of selection depend on the forecasting policy; do not state an unconditional reward-driven evolutionary prediction unless it is stable across these models. The analytical volunteer/inspection reductions and ODD specification should proceed. Separately, the rules marked ⚠ in `docs/rules_assumptions.md` still require author confirmation.

**No Experiments 2–4 replacement run was launched; no live GitHub branch or public release was created.**
