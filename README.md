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
  is that unique-day count per merchant, summed on proximity-dedup). Chase
  visits are not inferred from games. Rebuild Chase days with
  `assets/python/build_pub_visits.py --chase Chase7977_Activity_20260830.csv`.
- `seed_game_locations.csv` — optional location per `game_seq`
  (`pub_name` matches `seed_pubs.pub_name`, plus the handwritten
  `sheet_label`). Taken from the top of the sheet: `<pub> - <number of
  games>`, in column order. Games with no row are Unknown.
  `mart_location_stats` is games and win rate by that pub.
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
  proximity-deduped; unresolved merchants flagged). Statement visits stay
  separate from games. `mart_location_stats` joins `seed_game_locations`
  to those canonical pub names.

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
`#FF2D92`, Jordan is `#2D9CFF`. Grey is a coin-flip line or a sample under
5 games. The name stays `Yahtzee Head-to-Head`. Six tabs, short enough to
fit a 390px screen (DAC pads each tab by 16px a side):

1. **Top** — a pub-map link first, then paired comparisons: current win
   streak (longest run in small type), wins, average, median, high, low,
   Yahtzees, and the solo-Yahtzee win rate.
2. **Score** — streaks, cumulative wins, margin and total distributions,
   sum-box averages.
3. **Roll** — distribution, cumulative races, solo-Yahtzee matchup,
   scratch rates (four of a kind included).
4. **Odds** — upper section (bonus, average, dice vs par), swing bars,
   rescue matrix. See `assets/marts/strategy.md`.
5. **Game** — commentary (newest first), scorecard links, full game list.
6. **Pub** — win rate by location (n on the label) and the Leaflet map.

Marts behind the widgets: `mart_headline_kpis`, `mart_player_kpis`,
`mart_game_trends`, `mart_category_stats`, `mart_strategy_swing`,
`mart_strategy_rescue`, `mart_yz_matchup`. Serve with
`dac serve --dir dashboard --template yahtzee-dark`.

Standalone Leaflet map (`dashboard/pub_map.html`) — opens on the London
borough choropleth, with same-size pint pins one toggle away, from
`mart_pub_locations`. DAC 0.21.0 cannot embed Leaflet/MapKit; the Top tab
shows a preview image that opens this page, and the Pub tab links out too.
Default tiles are Esri World Light Gray (no API key). See `dashboard/pub_map.md`.

## 5. Animation

- Cumulative win-count race by `game_seq` (not date), rendered with
  matplotlib `FuncAnimation`, exported to mp4/gif, embedded on its own DAC
  page.
- Captions pulled straight from `int_commentary` — deterministic, not
  generated at render time.

## 6. Hosting

- Local: `bruin run` + DAC dev server, DuckDB file on disk — zero cost.
- VPS: [https://yahtzee.jginfo.xyz](https://yahtzee.jginfo.xyz) on a DigitalOcean
  Ubuntu droplet. Caddy serves `/pub_map.html`, `/pub_map/*`, `/scorecards`,
  and `/scorecards/*` from `dashboard/` and reverse-proxies everything else
  to `dac serve` on 127.0.0.1:8321. Ports 8321 and 8765 are not public.
  Runbook: [`docs/hosting-vps.md`](docs/hosting-vps.md).
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

See `/assets` for the Bruin pipeline (120 photographed games in
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
# DAC is pinned to 0.21.0 so the laptop and the VPS match:
# curl -LsSf https://getbruin.com/install/dac | sh -s -- v0.21.0
dac validate --dir dashboard
dac check --dir dashboard
dac serve --dir dashboard --template yahtzee-dark --open

# Interactive pub map + scorecards. Production Caddy serves these from
# dashboard/ at /pub_map.html and /scorecards; dac serve does not publish them.
python3 dashboard/scripts/export_pub_map.py
python3 dashboard/scripts/export_scorecards.py
# Optional, when the Top-tab map picture should change. Needs Chrome.
# Writes preview.jpg and preview.svg. Not part of the droplet rebuild.
# python3 dashboard/scripts/export_map_preview.py

# Locally, serve dashboard/ in front of dac serve so root-relative links
# resolve. The short Caddyfile in docs/hosting-vps.md listens on :8080:
#   http://127.0.0.1:8080/pub_map.html
#   http://127.0.0.1:8080/scorecards/viewer.html?game=1
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

`assets/seeds/raw_games.csv` already holds the 120 games from sheets
`IMG_2885`–`IMG_2924`. Re-run after appending more sheets (Grok extract,
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


