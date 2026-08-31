# Yahtzee Analytics — Project Outline

A local-first analytics engineering project: our Yahtzee scorecards, modeled
with Bruin (SQL + Python assets) on DuckDB, served as a Bruin
dashboard-as-code (DAC) site, with a standalone map of pubs played at and an
animated win-history chart with commentary.

## 1. Data model

Grain: sequence-ordered (`game_seq`), not date-ordered — no reliable dates.

**Raw (seeds)**
- `raw_games.csv` — one row per `game_seq` × `player` × `category` (all 15
  scorecard boxes: the 6 upper categories, `upper_bonus`, the 7 lower
  categories, `chance`, `yahtzee_bonus`) — the full scorecard, not just totals.
- `raw_game_totals.csv` — the grand total as literally written on the card,
  per `game_seq` × `player` — kept separate from the category rows so it can
  be used as an independent spot-check.
- `raw_players.csv` — player dimension source (`player_key`, `display_name`).
- `seed_commentary.csv` — catchphrase bank, categorized (`big_margin`,
  `narrow_margin`, `tie`, `streak`, `no_bonus_either`, `bonus_split`,
  `multi_yahtzee`, `zero_yahtzee`, `totals_mismatch`).
- `raw_pub_visits.csv` / `seed_pubs.csv` — pub geocoding inputs (unchanged).

**Staging → dims/facts → intermediate → marts**
- `stg_games`, `stg_game_totals`, `stg_players` — typed/cleaned staging views.
- `dim_player` — player dimension.
- `fact_games` — grain `game_seq` × `player`: aggregated from category rows,
  joined to `dim_player` (dim left-joined to the aggregate) and to
  `stg_game_totals` for a `totals_match` flag — this is the spot-check: if
  the 15 category scores don't sum to the recorded total, it's flagged, not
  silently trusted either way.
- `int_win_loss` — pivots `fact_games` to game grain: winner, margin,
  cumulative wins, streaks.
- `int_commentary` — **Python** asset: deterministically (seeded by
  `game_seq`) samples from `seed_commentary` based on the game's situation.
  Seeded, not truly random, so re-running the pipeline doesn't change the
  jokes each time.
- `mart_head_to_head` — `int_win_loss` joined with `int_commentary` — feeds
  the dashboard and the animation.
- `mart_pub_locations` — geocoded, deduped pub list (seed → Nominatim →
  Google Places → unresolved) — standalone, not joined to games.

## 2. Scorecard ingestion (OCR)

`ingestion/scan_scorecard.py` — a human-in-the-loop helper (not a Bruin
asset), run manually before `bruin run`. Each photographed sheet holds up
to 3 games; `ingestion/scorecard_format.md` documents the physical layout
and handwriting quirks (edit that file as you learn more about your own
handwriting patterns — the script reads it as part of the extraction
prompt, so corrections there improve future scans too).

1. Name files like `scorecard_games_1_to_3.jpg` — the number range in the
   filename drives `game_seq` numbering, not guesswork.
2. Sends the photo to a vision-capable Claude model — not classical OCR
   (pytesseract etc.), which is unreliable on handwriting, especially with
   crossed-out corrections.
3. The model returns structured JSON per game: all 15 categories per
   player, the recorded total, and any cells it's genuinely unsure about.
4. **Spot-check before writing anything**: sums the 15 category values per
   player and compares to the recorded total, and checks the extracted game
   count matches the filename's range. Any mismatch, or any flagged
   uncertain cell, stops the write for that whole sheet — the extraction is
   dumped to a `*.review.json` file for you to check by eye instead of
   silently trusting either the arithmetic or the handwriting.
5. Only a clean sheet gets appended to `raw_games.csv` / `raw_game_totals.csv`.

Batch mode: `python scan_scorecard.py --dir /path/to/photos` processes every
`scorecard_games_*` file in a folder in one run.

**Getting an API key**, if you want to run this script yourself: sign up at
console.anthropic.com, add billing (pay-as-you-go, no subscription), and
generate a key under "API Keys" — image requests to Claude cost a small
fraction of a cent each at this volume. Set it as `ANTHROPIC_API_KEY` in
your environment before running the script.

**Or skip the script entirely**: since you're already talking to Claude in
a chat interface with vision built in, you can just upload scorecard photos
directly in conversation and ask Claude to extract and spot-check them the
same way — no key, no script, no local setup. That's the better option for
occasional/small batches; the standalone script is worth it once you want
this to run unattended as part of a repeatable pipeline.

## 3. Pub geocoding pipeline

1. Seed match (`seed_pubs.csv`) — free, no API call, highest trust.
2. OpenStreetMap Nominatim — free, no key, decent baseline.
3. Google Places Text Search — fallback for fuzzy/abbreviated merchant names,
   small free tier.
4. Unresolved — flagged for manual review, feeds back into the seed file.
5. **Proximity dedup**: once a merchant string has coordinates (from any
   source above), venues within ~50m of each other are collapsed into one
   pub. This is what actually catches "Anchor Bar" and "Anchor Bankside
   (South" being the same building — string similarity alone is fooled
   too easily by chain naming and abbreviations; matching on the resolved
   coordinates is more reliable than fuzzy-matching the raw text.

Set `OFFLINE_TEST=1` to skip both live geocoding APIs entirely (seed
matches only) — useful for testing the rest of the pipeline with no
network access or API keys.

## 4. Dashboard (Bruin DAC)

- Head-to-head record, average score, category breakdown, streaks, and a
  data-quality widget surfacing any `totals_match = false` rows — built as
  Bruin DAC pages querying the marts directly.
- Standalone map page (pub pins, sized by visit count) — embedded as a custom
  HTML/JS component since DAC doesn't have a native map widget.

## 5. Animation

- Cumulative win-count race by `game_seq` (not date), rendered with
  matplotlib `FuncAnimation`, exported to mp4/gif, embedded on its own DAC
  page.
- Captions pulled straight from `int_commentary` — deterministic, not
  generated at render time.

## 6. Hosting

- Local: `bruin run` + DAC dev server, DuckDB file on disk — zero cost.
- Optional: small VPS ($5–6/mo) to serve the built DAC site + animation file
  if you want to share it.

## 7. Build order

1. Seeds + `stg_games`/`stg_game_totals`/`stg_players` + `dim_player` +
   `fact_games` (get the core stats and spot-check working first)
2. `int_win_loss` + `int_commentary` (cheeky logic)
3. `ingestion/scan_scorecard.py` for scanning real scorecards
4. Pub geocoding pipeline + `mart_pub_locations`
5. DAC dashboard pages
6. Animation script
7. Wire everything into `pipeline.yml`, validate, run

See `/assets` for the Bruin pipeline (verified against the sample data with
DuckDB — the full staging → fact → mart chain runs and the spot-check
correctly flags an intentionally-seeded totals mismatch in the sample data),
`/ingestion` for the OCR helper, and `/visuals` for the animation script.

## 8. Running just the Bruin portion

You don't need an Anthropic or Google API key to run the core pipeline —
only `assets/python/geocode_pubs.py` (pub geocoding) makes live network
calls, and everything else runs entirely off the seed CSVs already in
`assets/seeds/`.

```bash
cd yahtzee
pip install -r assets/python/requirements.txt

bruin validate          # sanity-checks pipeline.yml + .bruin.yml + asset schemas
bruin run                # runs the full DAG against the sample data in this repo
```

That builds `stg_*` → `dim_player`/`fact_games` → `int_win_loss` →
`int_commentary` → `mart_head_to_head`, plus `mart_pub_locations` (which will
attempt live geocoding unless you set `OFFLINE_TEST=1` — see below). Inspect
results directly:

```bash
duckdb yahtzee.duckdb "select * from mart_head_to_head"
```

Once you're happy with it, swap the sample rows in `assets/seeds/raw_games.csv`
and `raw_game_totals.csv` for your real scorecards (via `ingestion/scan_scorecard.py`
or by hand) and re-run.

## 9. Testing without any API keys

Set `OFFLINE_TEST=1` before running to make `mart_pub_locations` skip both
Nominatim and Google Places entirely — it'll resolve only what's in
`seed_pubs.csv` and mark everything else `unresolved`, with no network calls
and no keys required:

```bash
OFFLINE_TEST=1 bruin run
```

This is enough to validate the whole pipeline structure, the spot-check
logic, and the commentary model end to end — the OCR ingestion script is the
only piece that genuinely needs an API key, and it's a separate manual step
outside `bruin run` (see the OCR section above and the README note on
getting a key).


