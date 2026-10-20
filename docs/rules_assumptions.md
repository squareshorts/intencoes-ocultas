# Rule assumptions used by the model

The rulebook (`README.md`) and the simulator use the rules below. **A1, A3,
and A4 were expressly approved as the study's official rule interpretation on
20 October 2026** and incorporated into the rulebook. No approval from an
independent publisher or third-party designer is implied. Remaining rows
document rulebook details and explicit simulation conventions. Where a
`RuleConfig` option exists, it can be varied in a sensitivity analysis.

| # | Situation | Assumption (default) | Config field |
|---|---|---|---|
| A1 (confirmed) | Win condition | Last player with ≥1 active influence wins. Observers do not win. Reaching `max_turns` produces a **simulation-only** draw, not a second physical-game victory rule. | `max_turns` (simulation cutoff only) |
| A2 | Claimant shows the claimed card when challenged | Card goes back into the deck, deck is shuffled, a replacement is drawn (as in the rulebook's example) | `swap_on_proven_claim` |
| A3 (confirmed) | Observers | Players with no active influences can comment on bluffs but cannot take game actions, formally challenge, block or intervene. Informal comments have no mechanical effect. | — |
| A4 (confirmed) | Sombra cost when the attack fails | Three coins are paid on declaration and never refunded if the action is challenged, blocked or otherwise fails. | `assassin_refund_on_failed_challenge` (counterfactual sensitivity only) |
| A5 | Comerciante steals from a player with <2 coins | Takes what the target has | — |
| A6 | Who may block Ajuda Externa | Any active player other than the actor (the action has no target); first volunteer clockwise from the actor | — |
| A7 | Several players want to challenge | First willing player clockwise from the claimant resolves the challenge | — |
| A8 | Intervention order | Target decides first. If the target does not block, other active players (excluding the actor) are asked clockwise from the target; the first to accept is the sole interventor | `intervention_enabled` |
| A9 | Intervention reward | +1 coin from the treasury if the interventor's block stands (not exposed by a challenge) | `intervention_reward` |
| A10 | Treasury | Finite: 24 coins + 6 gold × 5 = 54. Payouts are capped by what remains | `treasury` |
| A11 | Golpe Direto obligation | At ≥10 coins at turn start the only legal action is Golpe Direto | `forced_coup_threshold` |
| A12 | Embaixador exchange | Draw 2, keep as many as the player's active influences, return the rest, shuffle | — |
| A13 | Rulebook term "Cobrança" | Read as the Comerciante's steal; "Ataque" read as the Sombra's action | — |
| A14 | Double loss | A Sombra target who wrongly challenges or bluff-blocks can lose two influences in one turn (as in Coup) | — |

**Implementation and sensitivity:** The standard `RuleConfig` retains
`assassin_refund_on_failed_challenge=False`, which implements A4. Enabling it
for a separate experiment changes only a failed Sombra *action-claim challenge*;
it is not a complete alternative rule in which blocked attacks are refunded.
The 400-turn stop and draw designation are a finite-computation safeguard,
not an official game rule. The experimental results were generated under
the now-confirmed standard choices and therefore require no re-estimation
solely because of this clarification.
