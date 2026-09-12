# Strategy marts

Player-blind, game-level rates for the DAC **Strategy** tab. All three
marts read `int_strategy_features` (one row per `game_seq`: Erin/Jordan
conversion-box flags + `int_win_loss.winner`).

That intermediate is the layer: swing, rescue, and Yahtzee matchup share
the same exclusive-feature logic. Putting the pivot only in DAC YAML would
duplicate cohort definitions and make the 12/22-style checks harder to
re-run. The dashboard queries are thin `select`s from these marts.

Oak / chance are intentionally absent — weak signals, not strategy.

## `mart_strategy_swing`

Games where **exactly one** player has the binary feature. Rate = that
holder's win rate.

| Feature | Seed (n=108, 0 ties) |
|---|---|
| Yahtzee bonus > 0 | 12/12 = 100% (small n) |
| Upper bonus (35) | 48/56 ≈ 86% |
| Yahtzee = 50 | 47/56 ≈ 84% |
| Large straight = 40 | 27/36 = 75% |
| Large straight = 0 | 9/36 = 25% |
| Full house = 0 | 9/21 ≈ 43% |
| Small straight = 0 | 1/4 = 25% — **n < 10, grey on the chart** |

## `mart_strategy_rescue`

**Exclusive combo**, not exclusive-miss-then-split.

A game is in cell *(miss M, consolation C)* when exactly one of Erin/Jordan
has **both** M and C. Cell = that focal player's win rate.

Consolations are mutually exclusive: Has Yahtzee (50, no UB) / Has upper
bonus (35, no YZ) / Has both / Has neither.

Rows: LS=0, SS=0, FH=0, No Yahtzee.

Grounding: exclusive **LS=0 + any Yahtzee** (Has Yahtzee + Has both) =
**12/22 ≈ 55%**. That includes games where both missed LS but only one
also had Yahtzee. The exclusive-miss cut of the same question is 8/18 —
do not quote that as the rescue rate.

## `mart_yz_matchup`

Buckets of games by how many players scored Yahtzee=50: **none / one /
both** (seed ≈ 32 / 56 / 20). Stacked by **winner** (Erin vs Jordan).
`holder_win_rate` is filled only on the `one` bucket (~84%).
