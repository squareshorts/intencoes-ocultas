# Rule assumptions used by the model

The rulebook (`README.md`) leaves some situations open. The simulator needs
each one resolved. Every assumption below is a field of `RuleConfig` in
`src/intencoes/rules.py`, so alternatives can be tested as robustness checks.
**Items marked ⚠ need confirmation from the game's author.**

| # | Situation | Assumption (default) | Config field |
|---|---|---|---|
| A1 ⚠ | Win condition | Last player with ≥1 active influence wins. Observers do not win. Games reaching `max_turns` are recorded as draws. | `max_turns` |
| A2 | Claimant shows the claimed card when challenged | Card goes back into the deck, deck is shuffled, a replacement is drawn (as in the rulebook's example) | `swap_on_proven_claim` |
| A3 ⚠ | Observers | Cannot challenge, block or intervene; "palpites" are informal and have no effect on play | — |
| A4 ⚠ | Sombra cost when the attack fails | 3 coins are paid on declaration and not refunded, whether blocked or lost to a challenge | `assassin_refund_on_failed_challenge` |
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
