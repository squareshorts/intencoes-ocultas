# Ablation: random bluff target (pre-fix model, commit 0e270d5)

Exp 2–4 outputs from the model in which agents bluffed by claiming a *random*
unheld character, valued actions without accounting for blocks, and had a
fixed stake bonus. Reproduce with `Params(bluff_target="random")`, which
restores that behaviour (for exp 3, also drop `stake_bonus` from `evolution.TRAITS`). Kept as the "bluff target selection" ablation.
