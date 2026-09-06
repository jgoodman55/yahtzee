# Yahtzee scorecard extraction flags

Source: Drive folder IMG_2885→IMG_2918 (102 games from 34 sheets, including IMG_2890 game 3 as `game_seq` 18).

## part1_flags.md

# part1_flags.md — ambiguous / unusual cells

## IMG_2885
- game 1, erin, upper section: category sum is 52 but written upper total is 42; grand total 191 = 42+149 (intentional arithmetic mismatch).
- game 1, erin, recorded_total: 191 does not equal full category sum 201 (uses written upper 42).
- game 2, erin, yahtzee_bonus: "200" written in bonus score box (actually lower-section subtotal); no bonus checkboxes filled → scored 0.
- game 3, erin, upper_bonus: 35 written despite upper category sum 55 (<63 threshold).
- game 3, erin, yahtzee_bonus: "100" appears in/near bonus score area; no checkboxes filled → scored 0; grand total 279 excludes it.
- game 3, jordan, upper_bonus: messy scribbles (49/44 crossed out, 39 nearby); scored 0 to match math (49+145=194).

## IMG_2886
- game 1 column order: labeled J, E (Jordan left of pair) then E, J / E, J.
- game 1, erin, threes: written as circle/slash → 0.
- game 3, erin & jordan, large_straight: circled zeros → 0.
- game 3, jordan, four_of_a_kind: slash/circle → 0.

## IMG_2887
- game 2, erin, chance: written 50 (above normal max 30).
- game 2, erin, yahtzee: written 26 over a slash (nonstandard; not 0 or 50).
- game 2, erin, upper total: written 101 vs category+bonus sum 101 with threes=6 (OK); if threes were 9 would be 104.
- game 3, erin, fives: written 12 (not a multiple of 5).
- game 3, erin, sixes: written 15 (not a multiple of 6).
- game 3, erin, yahtzee: written 20 (nonstandard).
- game 3, erin, chance: written 50.

## IMG_2888
- (none major; all three games complete and math-consistent)

## IMG_2889
- game 1, erin, full_house: 25 written over another value.
- game 2, erin, fours: 12 written over a scribble.
- game 2, jordan, chance: 21 written over crossed-out 20.
- game 2, jordan, recorded_total: written 208 but category sum 209 (60+149).
- game 3, jordan, recorded_total: 155; upper category sum 55 vs any scribbled upper subtotal.

## IMG_2890
- game 1, erin, four_of_a_kind: 18 written over earlier 22.
- game 2, jordan, upper total: 58 crossed out, replaced with 61 (matches category sum).
- game 3, erin & jordan: unfinished — no grand totals written; columns skipped.
- game 3, jordan, yahtzee: would have been 20 (nonstandard) if included.
- game 3, jordan, chance: would have been 50 if included.

## IMG_2891
- game 2, jordan, upper section: category sum 48 but written upper total 58; grand total 178 uses 58+120.
- game 3, erin, fours: 16 (confirmed); upper cats 67 + bonus 35 = 102 written upper total.
- game 3, erin, upper_bonus: 35 written with slash through it; included because upper total 102 requires +35.

## IMG_2892
- game 2, erin, large_straight: 40 has a diagonal line through it but lower total 183 requires 40.
- game 2, erin, recorded_total: 240 vs category sum 239 (off by 1).
- game 2, jordan, four_of_a_kind: written 13.
- game 2, jordan, recorded_total: 193 uses written lower subtotal 131 (cats sum to 130).

## IMG_2893
- game 1, erin, yahtzee_bonus: mark resembling "10" in score box; no checkboxes → 0; total 208 confirms.
- game 1, jordan, recorded_total: 231; category sum 241 (written upper 99 / lower ~130 used in their arithmetic).
- game 1, jordan, lower total: handwriting ambiguous (130 vs 132).
- game 3, erin & jordan, upper_bonus: slash → 0.


## part2_flags.md

# part2 extraction flags

## Ambiguous / unusual cells

| sheet | game | player | category | note |
|-------|------|--------|----------|------|
| IMG_2894 | 2 | erin | yahtzee | Written as 25 (non-standard; usually 0 or 50). Category sum matches recorded_total 125. |
| IMG_2894 | 3 | erin | chance | Heavy scribble/overwrite; read as 11 (needed for total 184). |
| IMG_2894 | 3 | jordan | yahtzee_bonus | One bonus checkbox marked (arrow); scored 100. Lower section total 297 includes bonus. |
| IMG_2894 | 1 | jordan | fours | Earlier scribble; final value 12 (upper total 106 = 0+6+9+12+20+24+35). |
| IMG_2896 | 2 | erin | upper_bonus | "16" crossed out, replaced with 35. |
| IMG_2896 | 2 | erin | yahtzee_bonus | Two bonus checkmarks → 200. Category sum 459 vs written grand total 456 (intentional mismatch; use written 456). |
| IMG_2896 | 2 | erin | recorded_total | Written upper total 99 (101 crossed out) + written lower 357 = 456; category lower sums to 360. |
| IMG_2896 | 3 | erin | upper_bonus | Checkmark present but upper total 59 < 63; scored 0. |
| IMG_2896 | 3 | jordan | fives | Handwriting ambiguous (could look like 40); upper total 99 requires 10. |
| IMG_2897 | 1 | jordan | yahtzee | Written as 21 (non-standard). Matches lower total 98 with large_straight=0. |
| IMG_2897 | 1 | jordan | large_straight | 40 heavily scribbled out; treated as 0. |
| IMG_2898 | 1 | erin | yahtzee_bonus | Slash in first bonus checkbox but not added to totals; scored 0. |
| IMG_2898 | 2 | erin | recorded_total | Category sum 225 vs written grand total 226 (off by 1). |
| IMG_2899 | 1 | erin | four_of_a_kind | Low score 13 (unusual but clearly written); sum matches 301. |
| IMG_2899 | 1 | jordan | four_of_a_kind | Read as 8; category sum 303 vs written grand total 302 (off by 1). |
| IMG_2899 | 1 | jordan | yahtzee_bonus | One X in bonus box → 100. |
| IMG_2899 | 3 | jordan | ones | Upper categories sum 60 vs written upper total 61; grand total written 152. |
| IMG_2900 | 2 | erin | recorded_total | Prior total crossed out in box; final grand total 264 written below. |
| IMG_2900 | 3 | erin | four_of_a_kind | Ambiguous handwriting; used 19 so lower section sums to 143 with three_of_a_kind=18. |
| IMG_2901 | 3 | erin | large_straight | 40 has a vertical mark through it but lower total 112 requires 40. |

## Sheets with fewer than 3 games
None — all 9 sheets (IMG_2894–IMG_2902) have 3 complete games.


## part3_flags.md

# part3 extraction flags

Sheets: IMG_2903–IMG_2911 (9 sheets, 27 games × 2 players).

- **IMG_2904** game 1 / erin / `four_of_a_kind`: Initial OCR read 25; sum only matches recorded_total 238 with 29. Using 29.
- **IMG_2904** game 2 / jordan / `threes`: Messy/overwritten; inferred 9 from upper section total 58.
- **IMG_2904** game 3 / jordan / `recorded_total`: Final digits faint; category sum confirms 200.
- **IMG_2905** game 2 / erin / `fives`: Smudged/faint; written upper total 50 implies fives=5.
- **IMG_2905** game 2 / erin / `three_of_a_kind`: Smudged game-2 column; read as 25 (with chance 22) to match lower total 146 / grand 196.
- **IMG_2905** game 2 / erin / `chance`: Smudged; read as 22 together with 3oak=25 to match written lower total 146.
- **IMG_2905** game 2 / jordan / `sixes`: Smudged/rewritten; read as 18.
- **IMG_2905** game 2 / jordan / `recorded_total`: Smudged; read as 268 (105+163).
- **IMG_2906** game 1 / erin / `ones`: Attached OCR said 2; column re-read shows 1 (upper written 99 = 1+8+6+16+15+18+35).
- **IMG_2906** game 2 / jordan / `fours`: Attached OCR said 10; re-read shows 16 (needed for grand total 330).
- **IMG_2906** game 2 / jordan / `yahtzee_bonus`: One X checkbox → 100.
- **IMG_2906** game 3 / jordan / `player`: Header may look like I; treated as jordan.
- **IMG_2906** game 3 / jordan / `recorded_total`: Category sum 227 vs written grand total 228.
- **IMG_2907** game 2 / jordan / `full_house`: Messy; read as 25.
- **IMG_2907** game 3 / erin / `recorded_total`: Category sum 162 vs written grand total 160; written upper total 56 vs category sum 58.
- **IMG_2907** game 3 / jordan / `fours`: Written 15 (not a multiple of 4); kept as written.
- **IMG_2907** game 3 / jordan / `fives`: Re-read as 16 (attached OCR said 10); with yahtzee 50 matches upper 99 + lower 155 = 254.
- **IMG_2908** game 1 / jordan / `sixes`: 18 scribbled toward 15; upper total 57 confirms 18.
- **IMG_2908** game 2 / erin / `four_of_a_kind`: Re-read as 26 (earlier OCR 20) to match recorded_total 156.
- **IMG_2908** game 3 / erin / `ones`: Ambiguous 1 vs 3; using 1 (upper total context 46).
- **IMG_2908** game 3 / erin / `recorded_total`: Grand total re-read as 198; category sum 186 (lower written 150 vs category sum 140).
- **IMG_2908** game 3 / jordan / `twos`: Messy handwriting; read as 2.
- **IMG_2909** game 1 / erin / `yahtzee_bonus`: Mark in bonus area but yahtzee=0 and total excludes 100; score 0.
- **IMG_2909** game 2 / erin / `upper section`: Written upper total 101 vs category+bonus sum 95.
- **IMG_2909** game 3 / jordan / `upper_bonus`: 49 written then crossed out; treating as 0.
- **IMG_2910** game 1 / erin / `three_of_a_kind`: Scribble under 14; final value 14.
- **IMG_2910** game 3 / erin / `small_straight`: Written 20 (non-standard; usual is 30). Category sum 161 vs recorded_total 171.
- **IMG_2910** game 3 / jordan / `yahtzee_bonus`: One X → 100.
- **IMG_2911** game 1 / erin / `full_house`: 25 written over earlier 0.
- **IMG_2911** game 3 / jordan / `threes`: Re-read as 9 (earlier OCR 7); matches upper total 58 and recorded_total 198.
- **IMG_2911** game 3 / jordan / `player`: Header looks like I; treated as jordan.

## Category sum vs recorded_total (recomputed after Jordan review)

The notes below record what was written on the cards. The seed now uses
`recorded_total = sum(score)` for every `(game_seq, player)` so
`fact_games.totals_match` is true for all 204 player-games.

Recomputed recorded_totals: (1,erin)=201; (14,jordan)=209; (20,jordan)=168;
(23,erin)=239; (23,jordan)=192; (25,jordan)=241; (35,erin)=454;
(41,erin)=225; (43,jordan)=303; (45,jordan)=151; (66,jordan)=227;
(69,erin)=162; (72,erin)=186; (74,erin)=274; (78,erin)=161;
(82,jordan)=399; (83,erin)=245.

Category-score corrections in the same pass: game 33 jordan rebuilt
(duplicate `fours` / missing `fives` → fives=15); (35,erin,chance) 28→23;
(68,jordan,yahtzee) 50→0; (101,jordan,fives) 24→25.

Historical written-vs-sum notes (superseded by the recomputed totals):

- **IMG_2906** game 3 / jordan: written 228, category sum 227
- **IMG_2907** game 3 / erin: written 160, category sum 162
- **IMG_2908** game 3 / erin: written 198, category sum 186
- **IMG_2909** game 2 / erin: written 280, category sum 274
- **IMG_2910** game 3 / erin: written 171, category sum 161


## part4_flags.md

# part4_flags.md — ambiguous / unusual cells

## IMG_2912
- game 1, jordan, yahtzee_bonus: one tick/slash in first bonus checkbox → scored 100; written grand total 249 excludes yahtzee 50 and this bonus (98+151).
- game 1, jordan, recorded_total: 249 vs category sum 399 (yahtzee + bonus not added into written total).
- game 1, jordan, large_straight: 40 written over a prior entry.
- game 2, erin, recorded_total: written 295 vs category sum 245 (delta +50); used written 295.
- game 2, jordan, yahtzee_bonus: one X in first checkbox → 100.
- game 3, jordan, ones: loopy digit; upper math (total 100 with bonus 35) requires 0.

## IMG_2913
- game 1, erin, upper_bonus: "59" written in bonus box (upper-section sum 1+4+9+12+15+18); not a real bonus → scored 0; "total of this section" has slash.
- game 1, erin, yahtzee_bonus: one X → 100.
- game 1, jordan, yahtzee_bonus: one X → 100 (math for grand total 392); some reads suggested a second mark.
- game 3, erin, full_house: 25 written over a prior 0/smudge.
- game 3, erin, yahtzee: slash/dot → 0.
- game 3, jordan, yahtzee_bonus: one X → 100.

## IMG_2914
- game 1, erin, upper_bonus: slash → 0.
- game 1, erin, fours: written 4 (not a multiple of 4).
- game 2, jordan, upper_bonus: "47" written in bonus box (upper sum 1+4+9+12+15+6); not a real bonus → scored 0; section total slash; grand total 161 excludes 47.
- game 3, erin, yahtzee: 0 with diagonal line → 0.

## IMG_2915
- game 2, erin, fours: written 8 (not a multiple of 4); fits upper total 59.
- game 3, jordan, twos: written 8.
- game 3, jordan, large_straight: 40 scribbled out with 24 written beside it; column math for recorded_total 387 requires 24 (not 40).
- game 3, jordan, yahtzee_bonus: one X → 100.
- game 3, jordan, recorded_total: 387 (category sum with LS=24 and bonus 100).

## IMG_2916
- game 2, erin, twos: 8 appears written over a 6.
- game 3, erin, yahtzee: 50 with messy flourish on the 5.
- game 3, jordan, recorded_total: 260 in the total box; margin note "-20" / "203" below (likely unrelated correction for another column) — used 260.

## IMG_2917
- game 1, jordan, recorded_total: handwriting can look like 145; category sum and clearer reading → 195.
- game 1, jordan, fours: written 16.
- game 1, erin, fives: read as 15 (fits total 292); could be 16 (±1 vs total).
- game 3, jordan, upper_bonus: dash → 0.

## IMG_2918
- game 1, jordan, yahtzee_bonus: two X marks → 200; recorded_total 509 (=100 upper + 209 lower + 200).
- game 1, jordan, full_house: 25 written over a correction/scribble.
- game 2, erin, yahtzee_bonus: one mark → 100.
- game 2, jordan, yahtzee_bonus: one mark → 100.
- game 3, erin, threes: digit ambiguous (6 vs 9); upper total 59 requires threes=6 (with sixes=18).
- game 3, erin, sixes: 18 (needed for upper 59).

## IMG_2890 game 3 (added)
- Previously skipped (no written grand totals). Jordan confirmed totals **E 173 / J 174**.
- Categories summed to those totals; Jordan yahtzee=20 chance=50 (nonstandard); Erin four_of_a_kind 27; totals E173/J224.
- Inserted as game_on_sheet 3 → continuous game_seq between prior IMG_2890 games and IMG_2891.

- Corrected Jordan recorded_total to **224** (yahtzee 20 + chance 50).
