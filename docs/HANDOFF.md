# Handoff prompt (paste into a fresh agent session)

> You are continuing a modeling paper on the bluffing card game **Intenções Ocultas** (a Coup-like game with a novel rewarded third-party "Intervenção" rule).
> The repo is `C:\work\intencoes-ocultas`, mirrored privately at github.com/squareshorts/intencoes-ocultas, branch `main`. Author: Antonio Pereira (UFPA).
> **Target:** paper 1 is model-only, for *Journal of the Royal Society Interface* (APC covered by the CAPES–Royal Society agreement). A protocol for human data comes later, for paper 2.
>
> **Read first, in this order:**
> 1. `README.md` — the rulebook, in Portuguese.
> 2. `docs/rules_assumptions.md` — how ambiguous rules are resolved. ⚠ items are still unconfirmed; the author said to proceed with the defaults.
> 3. `docs/paper_outline.md` — hypotheses H1–H5, findings so far, and the status checklist. **This is the source of truth for what is done.**
> 4. `literature/review.md` and `literature/references.bib` — 72 references, DOIs verified. Never add a reference without verifying it.
>
> **Code (Python 3.13):**
> - Environment: `.venv` (create with `py -3.13 -m venv .venv`, then `pip install numpy pandas scipy matplotlib pytest`). Run the tests with `.venv/Scripts/python.exe -m pytest -q`.
> - `src/intencoes/rules.py` — `RuleConfig`, where every assumption is a field.
> - `src/intencoes/engine.py` — the game engine. It checks invariants: coins and cards are conserved.
> - `src/intencoes/agents.py` — `HeuristicAgent` with `Params`: bluff, block_bluff, intervene, intervene_bluff, challenge_threshold θ, stake_bonus. Scepticism is card counting via `p_holds`.
> - `src/intencoes/sim.py` — batch runner; `stats.py` — paired bootstrap with common random numbers; `evolution.py` — Wright–Fisher co-evolution; `egta.py` — 9 archetypes, payoff tables, α-Rank, replicator dynamics.
> - `experiments/01`–`04` produce `results/exp*.csv`. Raw per-game data goes in `results/raw/` (gitignored and regenerable).
> - Windows: anything that uses `ProcessPoolExecutor` must run as a script file, not via stdin. Runs take minutes, so launch them in the background.
>
> **Open work, in priority order (see `docs/endogenous_opportunities_2026_10_19.md`):**
> 1. **Action-specific public blocking calibration tested to completion; strict gate NOT met.**
>    Read `docs/action_specific_calibration_2026_10_19.md`. The first four-player-trained
>    model passed 9/12 independent in-policy action strata. The final public
>    table-size model passed 11/12 on **7,800 completely new full games**;
>    remaining error was **n=3, shifted, Sombra: −9.5 pp**, 95% game-clustered
>    CI [−14.2, −5.2] pp. Improved Brier scores do not make that conditional
>    forecast calibrated. Do NOT retrofit the gate, leak simulator policy
>    labels or hidden cards, or replace historical Experiments 2–4. The new
>    predictor is opt-in via `Params.block_prediction="opponent_action"` plus
>    coefficients in `results/action_calibration/frozen_size_fit.json`; the
>    default is still `empirical`. Stop the ad-hoc forecast-tuning loop and
>    move to a *predeclared, affordable* sensitivity experiment comparing
>    baseline opponent, empirical and frozen size-aware policies, together
>    with analytic volunteer/inspection reductions. Label any selection
>    findings policy-conditional. `experiments/17_summarise_action_calibration.py`
>    prints the already completed holdouts without regenerating them.
> 2. Token economy: launch runs in the background, read only compact summaries (write a `summarise.py`, ≤30 lines per experiment), and never print raw logs or full payoff matrices.
> 3. Moran/Fermi finite-population dynamics with a selection-strength sweep.
> 4. Analytic sub-models (volunteer's dilemma, inspection game) as validation.
> 5. Figures, ODD protocol, Sobol sensitivity analysis, and a CFR benchmark on a reduced 3-player game.
> 6. Draft the manuscript in Interface format. Then propose a human-data protocol for paper 2.
>
> **Ground rules:**
> - Report failures honestly.
> - Commit with clear messages that end with the Co-Authored-By line.
> - Do not confuse this project with the user's SMR/EEG repos in `C:\work`.
> - Before outward-facing actions (new repos, making anything public), confirm with the user.

_Last updated: 2026-10-19, endogenous-policy calibration and controlled opportunity gate;
see docs/endogenous_opportunities_2026_10_19.md._

_Last updated: 2026-10-19, independent size-aware action calibration validation, strict gate 11/12 FAIL._

## 2026-10-19 — rare-bluffer invasion experiment (frozen policy sensitivity)

See `docs/bluff_invasion_2026_10_19.md` for all estimates, seed counts, exact Holm-adjusted tests, and limitations; reproducibility scripts are `experiments/19_bluff_invasion.py` and `experiments/20_summarise_bluff_invasion.py`. The primary strict-coupling four-player experiment found a +5.04 to +6.92 percentage-point win advantage at low scepticism across the empirical/opponent/action-specific blocking forecasts, with 2,500 paired seeds per condition. Three-player results were positive; five-player advantages were small and inconclusive. Moderate-scepticism effects were close to zero; at high scepticism no false action was selected under this heuristic. Original noncoupled results are retained separately because RNG consumption while considering a rejected bluff can confound outcomes. This is a rare-mutant win-rate sensitivity screen, not finite-population evolution or proof of invasion/fixation. The previous forecast calibration failure and unresolved rule assumptions remain open. Do not replace the original Experiments 2–4 CSVs. Next: frequency-dependent mutant composition, and separately controlled intervention reward/exposure.

## Official rule confirmation (20 October 2026)

The project author approved three previously flagged rule interpretations. A1: the last player with at least one active influence wins; A3: eliminated Observers may comment but cannot perform formal challenges, actions, blocks or interventions; A4: Sombra pays three coins on declaration, without refund if the attack fails. The reference engine and prior results already implement these rules. The 400-turn draw is a simulator-only safety cutoff. The failed-action-challenge refund toggle was examined solely as a counterfactual sensitivity. The rulebook, `docs/rules_assumptions.md`, manuscript and supplementary methods were updated without recalibrating agents or replacing any existing results.
