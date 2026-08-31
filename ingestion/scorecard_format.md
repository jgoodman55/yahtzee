# Scorecard format reference

Refer to the layout below when converting Yahtzee scorecard images to CSVs.

## Physical layout

- Standard Hasbro Yahtzee score sheet, one sheet = up to **3 games**.
- Player columns run left to right, headed by single-letter initials:
  `E J E J E J` (Erin, Jordan, repeated once per game). Not every sheet has
  all 3 games filled in — trailing columns may be blank.
- The sheet is split into two physical sections (upper "Number Combos" and
  lower "Special Combos"), each with its own subtotal row, plus a final
  "Grand Total" row at the very bottom of the lower section.

## Row order (top to bottom)

**Number Combos** (upper section)
1. Aces (add up all 1s)
2. Twos
3. Threes
4. Fours
5. Fives
6. Sixes
7. Bonus — 35 if the six rows above sum to 63+, otherwise blank/zero
8. **Total of this section** (upper subtotal)

**Special Combos** (lower section)

9. Three of a Kind (sum of all 5 dice)
10. Four of a Kind (sum of all 5 dice)
11. Full House (fixed 25)
12. Small Straight (fixed 30)
13. Large Straight (fixed 40)
14. Chance (sum of all 5 dice)
15. Yahtzee (fixed 50, or 0)
16. Yahtzee Bonus (checked or X'd boxes, 100 each — count checked or X'd boxes, not a written number)
17. **Total of this section** (lower subtotal)
18. **Grand Total** (upper subtotal + lower subtotal)

## Handwriting notation quirks and how to modestly validate

- A **slash (`/`) or short dash** in the Bonus row means "not earned" —
  read this as `0`, not as a digit or a blank/missing value.
- Corrections: values are sometimes crossed out and rewritten nearby — use
  the final (not-crossed-out) value.
- Digits that commonly get confused in this handwriting: `1` vs `7`, `0`
  vs `6`, `8` vs `0`. When genuinely unsure, flag the cell rather than
  guess — the subtotal and grand total rows can often disambiguate a
  single uncertain upper-section cell, but not with full certainty, so
  don't silently "correct" toward whatever makes the arithmetic work.
  Furthermore, disambiguation is possible for the Aces, Twos, Threes, Fours, Fives, and Sixes by considering that each of those boxes must be divisible by itself. For example, the Fives can never be 16, it would more likely be 15. Additionally, the fixed boxes: Small Straight, Large Straight, and Yahtzee can only ever be their designated value else 0. Moreover, any box where the totals are added (Aces, Twos, Threes, Fours, Fives, Sixes, Three of a Kind, Four of a Kind, and Chance) must be <= 30.

## Worked example

| Category | Erin | Jordan |
|---|---|---|
| Aces | 1 | 0 |
| Twos | 6 | 4 |
| Threes | 9 | 0 |
| Fours | 16 | 16 |
| Fives | 16 | 15 |
| Sixes | 18 | 18 |
| Bonus | 35 | 0 (written as `/`) |
| **Upper subtotal** | **100** | **53** |
| Three of a Kind | 21 | 16 |
| Four of a Kind | 18 | 10 |
| Full House | 25 | 25 |
| Small Straight | 30 | 30 |
| Large Straight | 40 | 40 |
| Chance | 8 | 21 |
| Yahtzee | 50 | 0 |
| Yahtzee Bonus | 0 | 0 |
| **Lower subtotal** | **192** | **142** |
| **Grand Total** | **292** | **195** |

Note: Erin's six upper-section digits summed to 66 in this example, one
more than the 65 implied by the recorded subtotal (100 − 35 bonus) — a
real instance of the kind of single-cell ambiguity the spot-check is
meant to catch. The spot check should catch that Erin's Fives have 16, which is not divisible by 5, so the cell should've actually been 15.
