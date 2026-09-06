# Scorecard ingest

Real Yahtzee games replace the 3-game demo seed in `assets/seeds/raw_games.csv`.

## Source

- Google Drive folder: https://drive.google.com/drive/folders/1nSooXGB5YhYIaP43eBJdxjCR3NHSZxEo
- Folder id: `1nSooXGB5YhYIaP43eBJdxjCR3NHSZxEo`
- 34 HEIC sheets: `IMG_2885` through `IMG_2918`
- Filename ascending = game order
- Each sheet is a standard Hasbro card: up to 3 Erin/Jordan games (`E J` column pairs, left to right)

## Numbering

- `game_seq` is continuous **1–102**
- Mapping of sequence → photo → column group is in `assets/seeds/sheet_game_crosswalk.csv`
- `IMG_2890` game 3 is included as `game_seq` **18** (Erin recorded_total **173**, Jordan **224**). Later sheets continue at 19.

## Seed files

| File | Role |
|---|---|
| `assets/seeds/raw_games.csv` | Category scores: `game_seq,player,category,score,recorded_total` (15 categories × 2 players × 102 games = 3060 data rows). Players are `jordan` / `erin`. |
| `assets/seeds/sheet_game_crosswalk.csv` | Photo provenance for each `game_seq` |
| `assets/seeds/extraction_flags.md` | Cells / games that needed a human call during extraction |

`recorded_total` is repeated on all 15 category rows for that `(game_seq, player)`. After Jordan's category review it was set to `sum(score)` for every player-game (0 remaining mismatches). `fact_games.totals_match` still compares computed vs recorded as a spot-check. Historical card-vs-sum notes stay in `extraction_flags.md`.

## Pipeline

Seeds feed `stg_games` → `fact_games` (computed vs recorded totals) → `int_win_loss` / `int_commentary` → `mart_head_to_head`. After replacing `raw_games.csv`:

```bash
cp -n .bruin.yml.example .bruin.yml
OFFLINE_TEST=1 bruin run --workers 1
```
