# Scorecard ingest

Real Yahtzee games replace the 3-game demo seed in `assets/seeds/raw_games.csv`.

## Source

- Google Drive folder: https://drive.google.com/drive/folders/1nSooXGB5YhYIaP43eBJdxjCR3NHSZxEo
- Folder id: `1nSooXGB5YhYIaP43eBJdxjCR3NHSZxEo`
- 36 sheets: `IMG_2885` through `IMG_2920` (Drive still has 2885–2918; 2919–2920 are the two new photos)
- Filename ascending = game order
- Each sheet is a standard Hasbro card: up to 3 Erin/Jordan games (`E J` column pairs, left to right)

## Numbering

- `game_seq` is continuous **1–108**
- Mapping of sequence → photo → column group is in `assets/seeds/sheet_game_crosswalk.csv`
- `IMG_2890` game 3 is included as `game_seq` **18** (Erin recorded_total **173**, Jordan **224**). Later sheets continue at 19.

## Seed files

| File | Role |
|---|---|
| `assets/seeds/raw_games.csv` | Category scores: `game_seq,player,category,score,recorded_total` (15 categories × 2 players × 108 games = 3240 data rows). Players are `jordan` / `erin`. |
| `assets/seeds/sheet_game_crosswalk.csv` | Photo provenance for each `game_seq` |
| `assets/seeds/extraction_flags.md` | Cells / games that needed a human call during extraction |
| `assets/seeds/known_score_rule_violations.csv` | Leftover impossible scores still under photo review (allowlist for `raw_games_score_rules`) |

`recorded_total` is repeated on all 15 category rows for that `(game_seq, player)`. After Jordan's category review it was set to `sum(score)` for every player-game (0 remaining mismatches). `fact_games.totals_match` still compares computed vs recorded as a spot-check. Historical card-vs-sum notes stay in `extraction_flags.md`.

## Score-rule quality

`raw_games` plus `assets/audit/raw_games_score_rules.sql` flag impossible box values (OCR / spreadsheet typos):

- `full_house` ∈ {0, 25}, `small_straight` ∈ {0, 30}, `large_straight` ∈ {0, 40}, `yahtzee` ∈ {0, 50}
- `chance` must never be 0
- Upper faces: `ones`–`sixes` must be `n * face` for `n` in 0..5
- `upper_bonus` ∈ {0, 35}

Most of these rules hard-fail on the `raw_games` seed. Leftovers stay in
`known_score_rule_violations.csv` (currently empty).
`raw_games_score_rules` fails `OFFLINE_TEST=1 bruin run --workers 1` when a
violation is not on that allowlist. List leftovers without Bruin:

```bash
python tests/test_raw_games_score_rules.py
# or: pytest tests/test_raw_games_score_rules.py
```

## Side-by-side scorecards (dashboard)

After `bruin run`, refresh the photo | seed-card pages:

```bash
python3 dashboard/scripts/export_scorecards.py
python3 dashboard/scripts/export_scorecards.py --png-samples 1,47,100
python3 -m http.server 8765 --directory dashboard
# http://localhost:8765/scorecards/viewer.html?game=1
```

Drop Drive originals into `dashboard/scorecards/photos/` as `IMG_2885.HEIC`
(or `.jpg`). Those files are gitignored. A few downscaled sample JPGs ship
under `dashboard/scorecards/samples/photos/`. Details: `dashboard/scorecards.md`.

## Pipeline

Seeds feed `stg_games` → `fact_games` (computed vs recorded totals) → `int_win_loss` / `int_commentary` → `mart_head_to_head`. After replacing `raw_games.csv`:

```bash
cp -n .bruin.yml.example .bruin.yml
OFFLINE_TEST=1 bruin run --workers 1
```
