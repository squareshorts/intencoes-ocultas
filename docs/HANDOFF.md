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
> **Open work, in priority order (also tracked in `docs/paper_outline.md`):**
> 1. **Calibrate attackers' P(blocked).**
>    - Exp 2–4 were rerun with the block-aware model (results in `results/`, summaries via `experiments/summarise.py`). Intervention nearly vanished (0.01/game), because attackers assume every eligible blocker-holder always intervenes; only 8% of attacks are actually blocked.
>    - Fix: add public counters of intervention opportunities and interventions to `View`, and scale the interventor term in `HeuristicAgent._p_blocked` by the Laplace rate (as `_bluff_score` does for challenges).
>    - Re-gate (bluffers invade non-sceptics; sceptics resist), check calibration (predicted vs actual block rate), then rerun exp 2–4 (≈2.7 h).
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

_Last updated: 2026-10-19, exp 2–4 rerun done; P(blocked) miscalibration found._
