# Yahtzee DAC dashboard

One DAC app, seven tabs that go simple → deep. Dark theme (`yahtzee-dark`):
Erin is electric pink (`#FF2D92`), Jordan is electric blue (`#2D9CFF`).

| Tab | What’s on it |
|---|---|
| **Overview** | Headline KPIs: games, wins, high scores (`recorded_total`), Erin/Jordan/combined yahtzees, upper bonuses, multi-yahtzee player-games, streaks. Big numbers are Erin pink (`#FF2D92`), Jordan blue (`#2D9CFF`), or white for combined totals. |
| **Races** | Cumulative wins, cumulative yahtzees, yahtzees-per-game + cumulative multi-yahtzee games (`game_seq` on x) |
| **Zeros** | Zeros per game (bonuses excluded), lower-section miss rates (FH / SS / LS / Yahtzee), category table |
| **Strategy** | Player-blind exclusive-feature swing bars, miss × consolation rescue matrix, exclusive Yahtzee holder-won vs upset (Erin alone / Jordan alone). Oak/chance stay off this tab. Cohort notes: [`../assets/marts/strategy.md`](../assets/marts/strategy.md). |
| **Deep cuts** | Lifetime points, rates, upper avg dice count (ones–sixes, 0–5) vs lower sum-box avg points (3oak / 4oak / chance), win margins and `recorded_total` distributions split by player, closest/blowouts, commentary, clickable scorecard links. KPI figures use the same pink / blue / white Vega-Lite marks as Overview. |
| **Scorecards** | Sidecar link + sample composite + catalog. Photo \| seed card (Chance before Yahtzee). See [`scorecards.md`](scorecards.md). |
| **Pubs** | Link to the standalone Leaflet map + venue table. Not joined to games. |

Queries hit DuckDB marts (`mart_headline_kpis`, `mart_player_kpis`,
`mart_game_trends`, `mart_category_stats`, `mart_strategy_swing` /
`mart_strategy_rescue` / `mart_yz_matchup`, plus `mart_head_to_head` /
`mart_pub_locations`).

DAC 0.15 cannot embed Leaflet/MapKit. The real map is `pub_map.html` (OSM
tiles, no API key). See `pub_map.md` for regenerate / serve / `dac build`.

Queries run against the pipeline DuckDB file (`yahtzee.duckdb` at the repo root)
via the read-only `local_duckdb` connection in `.bruin.yml`. The pipeline writes
through `duckdb-default` (same file, writable, one asset at a time).

Walkthrough screenshots: [`docs/screenshots/`](docs/screenshots/). Strategy tab
captures: `strategy_swing_factors.png`, `strategy_rescue_matrix.png`,
`strategy_yz_matchup_stacked.png`.

## Prerequisites

From the repo root:

```shell
# Bruin + DAC CLIs (https://getbruin.com/docs/dac/getting-started/quickstart.html)
# curl -LsSf https://getbruin.com/install/cli | sh
# curl -LsSf https://getbruin.com/install/dac | sh

cp -n ../.bruin.yml.example ../.bruin.yml   # if .bruin.yml is missing
pip install -r ../assets/python/requirements.txt
OFFLINE_TEST=1 bruin run --workers 1        # builds marts into yahtzee.duckdb
```

`dac` walks upward from this directory to find the repo-root `.bruin.yml`.

## Commands

```shell
dac validate --dir .
dac validate --dir . --with-database
dac check --dir .
dac serve --dir . --template yahtzee-dark --open
```

`--template yahtzee-dark` loads `themes/yahtzee-dark.yml` (extends `bruin-dark`,
pink/blue chart tokens). The viewer still has a light/dark toggle; start from
dark.

The dashboard is served at `http://localhost:8321`.

## Interactive pub map

After `bruin run`, refresh the GeoJSON the Leaflet page reads:

```shell
python3 scripts/export_pub_map.py
python3 -m http.server 8765 --directory .
# http://localhost:8765/pub_map.html
```

Or open `pub_map.html` as a local file. Optional MapTiler streets:
`?maptiler=YOUR_KEY` — not required.

## Connection

This project uses two DuckDB connections to the same `yahtzee.duckdb` file:

- `duckdb-default` — writable, `max_concurrent_assets: 1`, used by `bruin run`
- `local_duckdb` — `read_only: true`, used by this dashboard so widgets can
  query in parallel without DuckDB file-lock errors

The empty `data/dac-demo.duckdb` leftover from `dac init` is unused.
