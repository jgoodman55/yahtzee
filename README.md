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
  categories, `chance`, `yahtzee_bonus`) plus `recorded_total`, the grand
  total as written on the card. The same `recorded_total` is repeated on
  all 15 category rows for a `(game_seq, player)` so the spot-check stays
  on one seed file.
- `raw_players.csv` — player dimension source (`player_key`, `display_name`).
- `seed_commentary.csv` — catchphrase bank, categorized (`big_margin`,
  `narrow_margin`, `tie`, `streak`, `no_bonus_either`, `bonus_split`,
  `multi_yahtzee`, `zero_yahtzee`, `totals_mismatch`).
- `raw_pub_visits.csv` / `seed_pubs.csv` — pub geocoding inputs. One visit-log
  row per unique calendar day at a venue (`visit_count` on `mart_pub_locations`
  is that unique-day count per merchant, summed on proximity-dedup). Not
  joined to games. Rebuild Chase days with
  `assets/python/build_pub_visits.py --chase Chase7977_Activity_20260830.csv`.
- `sheet_game_crosswalk.csv` — `game_seq` → Drive sheet `IMG_####` +
  `game_on_sheet` (feeds the Scorecards sidecar).

**Staging → dims/facts → intermediate → marts**
- `stg_games`, `stg_players` — typed/cleaned staging views (`stg_games`
  passes `recorded_total` through).
- `dim_player` — player dimension.
- `fact_games` — grain `game_seq` × `player`: aggregated from category rows,
  joined to `dim_player` (dim left-joined to the aggregate). Computes
  `sum(score)` as `computed_total` and compares it to `recorded_total` for
  a `totals_match` flag — this is the spot-check: if the 15 category scores
  don't sum to the recorded total, it's flagged, not silently trusted
  either way.
- `int_win_loss` — pivots `fact_games` to game grain: winner, margin,
  cumulative wins, streaks.
- `int_commentary` — **Python** asset: deterministically (seeded by
  `game_seq`) samples from `seed_commentary` based on the game's situation.
  Seeded, not truly random, so re-running the pipeline doesn't change the
  jokes each time.
- `mart_head_to_head` — `int_win_loss` joined with `int_commentary` — feeds
  the dashboard commentary table and the animation.
- `mart_player_kpis` / `mart_headline_kpis` / `mart_game_trends` /
  `mart_category_stats` — dashboard marts (lifetime KPIs, race series, zeros
  and category miss rates; upper `avg_dice_count` = score / face). High scores
  use `recorded_total`.
- `int_strategy_features` → `mart_strategy_swing` / `mart_strategy_rescue` /
  `mart_yz_matchup` — player-blind Strategy tab (exclusive-feature holder
  win rates, miss × consolation rescue matrix, exclusive Yahtzee
  holder-won vs upset). Cohort definitions: `assets/marts/strategy.md`.
- `mart_pub_locations` — seed-only pub list (lat/lng from `seed_pubs.csv`,
  proximity-deduped; unresolved merchants flagged) — standalone, not
  joined to games.

## 2. Scorecard ingestion (OCR)

Upload each photographed sheet to **Grok** and have it extract / propose
`raw_games.csv` updates. Layout and handwriting notes live in
`ingestion/scorecard_format.md`. There is no Anthropic or OpenAI
integration; `bruin run` never calls a model.

After patching the seed:

1. `python tests/test_raw_games_score_rules.py` (or `bruin run --workers 1`).
2. **Failures are the review queue** — impossible boxes as
   `(game_seq, player, category, score, rule)`. Check those cells on the
   photo. That is the default alert, not a full-sheet re-read.
3. `known_score_rule_violations.csv` stays empty by policy. Fix the seed;
   do not allowlist OCR noise.
4. Legal-but-wrong scores still need occasional side-by-side on the
   scorecards viewer. They will not fail the rule tests.

Full loop: `docs/scorecard_ingest.md`. `ingestion/scan_scorecard.py` is a
leftover Claude helper and is not part of the pipeline.

## 3. Pub geocoding pipeline

Locations come from `seed_pubs.csv` only (lat/lng already in the seed).
No Nominatim, no Google Places, no API key, no `OFFLINE_TEST` flag.

1. Seed match (`seed_pubs.csv`) — merchant string → seed lat/lng.
2. Unresolved — visit-log merchants with no seed match are printed for
   review; add a seed row (with coords) and re-run. No network.
3. **Proximity dedup**: once a merchant string has coordinates from the
   seed, venues within ~50m of each other are collapsed into one pub.
   This is what actually catches "Anchor Bar" and "Anchor Bankside
   (South" being the same building — string similarity alone is fooled
   too easily by chain naming and abbreviations; matching on the resolved
   coordinates is more reliable than fuzzy-matching the raw text. Distinct
   seed pubs with different `pub_name` values (The Derby and Hanover Arms)
   are not collapsed even when they sit inside that radius.

Popup photos are the same: seed `photo_url` / vendored
`dashboard/pub_map/photos/` only. No live Place Photos.

## 4. Dashboard (Bruin DAC)

Dark-mode DAC app (`dashboard/yahtzee.yml`, theme `yahtzee-dark`): Erin is
electric pink (`#FF2D92`), Jordan is electric blue (`#2D9CFF`). Tabs go
simple → deep:

1. **Overview** — games, wins, high and low scores (`recorded_total`, per player), yahtzees
   (Erin / Jordan / combined), upper bonuses, multi-yahtzee player-games,
   streaks. Big numbers: Erin pink (`#FF2D92`), Jordan blue (`#2D9CFF`),
   combined totals white.
2. **Races** — cumulative wins / yahtzees and multi-yahtzee trend (`game_seq`)
3. **Zeros** — zeros per game (bonuses excluded) and lower-section miss rates
4. **Strategy** — player-blind exclusive-feature swing bars, rescue matrix
   (miss × consolation), exclusive Yahtzee holder-won vs upset (Erin
   alone / Jordan alone). Oak/chance are not on this tab. See
   `assets/marts/strategy.md`.
5. **Deep cuts** — lifetime points, rates, upper dice-count averages
   (ones–sixes on a 0–5 scale) and lower sum-box point averages (3oak / 4oak /
   chance), win margins and `recorded_total` distributions split by player,
   closest/blowouts (colored by winner) and commentary (Erin/Jordan
   `recorded_total` after Winner). KPI figures use the same pink / blue /
   white Vega-Lite marks as Overview, centered in the widget.
6. **Scorecards** — path to side-by-side original photo + seed-rendered card
   (Chance before Yahtzee). DAC 0.15 cannot click table cells; the sidecar
   HTML on port 8765 is the comparison UX (see `dashboard/scorecards.md`).
7. **Pubs** — link to the standalone Leaflet map (not joined to games)

Marts behind the widgets: `mart_headline_kpis`, `mart_player_kpis`,
`mart_game_trends`, `mart_category_stats`, `mart_strategy_swing`,
`mart_strategy_rescue`, `mart_yz_matchup`. Serve with
`dac serve --dir dashboard --template yahtzee-dark`.

Standalone Leaflet map (`dashboard/pub_map.html`) — same-size pint pins
coloured by unique-day visits, plus a London borough choropleth with
drill-down, from `mart_pub_locations`. DAC 0.15 cannot embed Leaflet/MapKit;
the Pubs tab links out to this page. Default tiles are Esri World Light Gray
(no API key). See `dashboard/pub_map.md`.

## 5. Animation

- Cumulative win-count race by `game_seq` (not date), rendered with
  matplotlib `FuncAnimation`, exported to mp4/gif, embedded on its own DAC
  page.
- Captions pulled straight from `int_commentary` — deterministic, not
  generated at render time.

## 6. Hosting

- Local: `bruin run` + DAC dev server, DuckDB file on disk — zero cost.
- VPS: after merge, GitHub Actions SSHs to a small Ubuntu box (~£5/mo) and
  runs Bruin there. Runbook: [`docs/hosting-vps.md`](docs/hosting-vps.md).
  - **PR validation** — [`.github/workflows/scorecard-validation.yml`](.github/workflows/scorecard-validation.yml)
    (impossible scores; no secrets). Grok stays OCR; CI is the alert.
  - **Deploy** — [`.github/workflows/deploy-vps.yml`](.github/workflows/deploy-vps.yml)
    (`push` to `main`, or Actions → Deploy VPS → Run workflow).

## 7. Build order

1. Seeds + `stg_games`/`stg_players` + `dim_player` + `fact_games`
   (get the core stats and spot-check working first)
2. `int_win_loss` + `int_commentary` (cheeky logic)
3. Grok extract + score-rule tests for new scorecards (`docs/scorecard_ingest.md`)
4. Seed-only pub locations + `mart_pub_locations`
5. DAC dashboard pages
6. Animation script
7. Wire everything into `pipeline.yml`, validate, run

See `/assets` for the Bruin pipeline (108 photographed games in
`raw_games.csv`; `recorded_total` was recomputed from category sums after
Jordan's review, and `fact_games.totals_match` remains the spot-check),
`/docs/scorecard_ingest.md` for the Grok + score-rule loop, and
`/visuals` for the animation script.

## 8. Running just the Bruin portion

No API keys. `bruin run` is seed-only: games, commentary, and pub
locations all come from CSVs in `assets/seeds/`. `mart_pub_locations`
never calls Nominatim or Google Places.

The only remaining optional network is **client-side map tiles** when you
open `dashboard/pub_map.html` in a browser (Esri World Light Gray / OSM).
That is Leaflet in the browser, not Bruin.

```bash
cd yahtzee
cp -n .bruin.yml.example .bruin.yml   # local DuckDB connection; no secrets
pip install -r assets/python/requirements.txt

bruin validate          # sanity-checks pipeline.yml + .bruin.yml + asset schemas
bruin run                # runs the full DAG against the scorecard seed in this repo
                         # DuckDB is single-writer; .bruin.yml.example sets
                         # max_concurrent_assets: 1. If a run still hits a file
                         # lock, retry with: bruin run --workers 1
```

`.bruin.yml` is gitignored (Bruin default). This repo ships `.bruin.yml.example`
with a `duckdb-default` connection pointing at `yahtzee.duckdb`. Copy it before
the first `bruin` / `dac` command.

Then serve the dashboard (after `bruin run` has built the marts):

```bash
dac validate --dir dashboard
dac check --dir dashboard
dac serve --dir dashboard --template yahtzee-dark --open

# Interactive pub map + scorecards (not inside DAC — open beside it)
python3 dashboard/scripts/export_pub_map.py
python3 dashboard/scripts/export_scorecards.py
python3 -m http.server 8765 --directory dashboard
# http://localhost:8765/pub_map.html
# http://localhost:8765/scorecards/viewer.html?game=1
```

The dashboard uses the `local_duckdb` connection (same `yahtzee.duckdb` file,
`read_only: true`) so widgets can query in parallel. Stop `dac serve` before
another `bruin run` — DuckDB still cannot mix a writer with open readers.

That builds `stg_*` → `dim_player`/`fact_games` → `int_win_loss` →
`int_commentary` → `mart_head_to_head` plus the dashboard marts
(`mart_player_kpis`, `mart_headline_kpis`, `mart_game_trends`,
`mart_category_stats`, `int_strategy_features` → `mart_strategy_swing` /
`mart_strategy_rescue` / `mart_yz_matchup`), and `mart_pub_locations`
(seed matches only; unresolved merchants are printed). Inspect results
directly:

```bash
duckdb yahtzee.duckdb "select * from mart_head_to_head"
```

`assets/seeds/raw_games.csv` already holds the 108 games from sheets
`IMG_2885`–`IMG_2920`. Re-run after appending more sheets (Grok extract,
then score-rule tests). See `docs/scorecard_ingest.md`.

**Migrating an older two-file seed:** if you still have a separate
`raw_game_totals.csv` (`game_seq,player,recorded_total`), join it onto
`raw_games` on `(game_seq, player)` so every category row gets a
`recorded_total` column, then drop `raw_game_totals.csv` /
`stg_game_totals`. The seed now sets `recorded_total` to
`sum(score)` after Jordan's category review; `fact_games.totals_match`
is still the spot-check if those ever diverge again.

## 9. Score-rule review queue

Impossible category scores (wrong Full House / straight / Yahtzee box,
Chance 0, upper faces that are not `n * face`) fail `bruin run` unless
they are listed in `known_score_rule_violations.csv` (empty by policy).
Those failures are what Jordan checks after a Grok extract — listed as
`(game_seq, player, category, score, rule)`. The same check runs
on PRs that touch seeds / audit / tests
([`.github/workflows/scorecard-validation.yml`](.github/workflows/scorecard-validation.yml)).
Print the same list without Bruin:

```bash
python tests/test_raw_games_score_rules.py
```


