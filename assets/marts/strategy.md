# Strategy marts

Player-blind, game-level rates for the DAC **Strategy** tab. All three
marts read `int_strategy_features` (one row per `game_seq`: Erin/Jordan
conversion-box flags + `int_win_loss.winner`).

That intermediate is the layer: swing, rescue, and Yahtzee matchup share
the same exclusive-feature logic. Putting the pivot only in DAC YAML would
duplicate cohort definitions and make the 13/24-style checks harder to
re-run. The dashboard queries are thin `select`s from these marts.

Oak / chance are intentionally absent — weak signals, not strategy.

## `mart_strategy_swing`

Games where **exactly one** player has the binary feature. Rate = that
holder's win rate.

| Feature | Seed (n=126, 0 ties) |
|---|---|
| Yahtzee bonus > 0 | 15/15 = 100% |
| Upper bonus (35) | 52/62 ≈ 84% |
| Yahtzee = 50 | 57/68 ≈ 84% |
| Large straight = 40 | 30/40 = 75% |
| Large straight = 0 | 10/40 = 25% |
| Full house = 0 | 11/26 ≈ 42% |
| Small straight = 0 | 1/4 = 25% — **n < 10, grey on the chart** |

## `mart_strategy_rescue`

**Exclusive combo**, not exclusive-miss-then-split.

A game is in cell *(miss M, consolation C)* when exactly one of Erin/Jordan
has **both** M and C. Cell = that focal player's win rate.

Consolations are mutually exclusive: Has Yahtzee (50, no UB) / Has upper
bonus (35, no YZ) / Has both / Has neither.

Rows: LS=0, SS=0, FH=0, No Yahtzee.

Grounding: exclusive **LS=0 + any Yahtzee** (Has Yahtzee + Has both) =
**13/24 ≈ 54%**. That includes games where both missed LS but only one
also had Yahtzee. The exclusive-miss cut of the same question is 9/20 —
do not quote that as the rescue rate.

## `mart_yz_matchup`

**Exclusive Yahtzee only** — games where exactly one player scored
Yahtzee = 50. None / both are out of this mart.

Grain: holder × outcome. Two bars (Erin alone / Jordan alone), each
stacked **Holder won** vs **Upset** (holder lost). The Strategy chart
Y-axis is that holder's outcome **share (0–100%)**; labels keep raw W/L.
Combined exclusive holder rate is the swing-factor Yahtzee = 50 row
(57/68 ≈ 84%) — not a separate dashboard visual.

| Holder | Seed (n=126, 0 ties) |
|---|---|
| Erin alone | 30W / 9L of 39 ≈ 77% |
| Jordan alone | 27W / 2L of 29 ≈ 93% |
| Combined | 57 / 68 ≈ 84% |
