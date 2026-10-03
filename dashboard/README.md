# Yahtzee DAC dashboard

One DAC app, six short tabs. Dark theme (`yahtzee-dark`):
Erin is `#FF2D92`, Jordan is `#2D9CFF`.
Grey (`#6D7889`) is a coin-flip line, an upset, or a sample under 5 games.

The dashboard name stays `Yahtzee Head-to-Head`, so `/d/Yahtzee%20Head-to-Head`
does not move.

| Tab | What’s on it |
|---|---|
| **Top** | Erin-vs-Jordan comparisons: current win streak (longest run in small type), wins, average, median, high and low score (click opens that game), Yahtzees, and the solo-Yahtzee win rate. |
| **Score** | Streaks next to the wins race, separate Erin and Jordan histograms for margins and totals, sum-box averages. |
| **Roll** | Per-game rate, Yahtzee count distribution, cumulative races, the solo-Yahtzee matchup, scratch rates (including four of a kind), scratches as a percent of games. |
| **Odds** | Upper bonus as a percent with the count, upper average, dice-per-face with value labels, swing bars ordered by win rate, rescue matrix. Plain labels. |
| **Game** | Commentary (newest first, comment up front), clickable closest games and blowouts, a sample card, the full game list. |
| **Pub** | Link to the Leaflet map, win rate by location with n on the label, games table, venue list. |

DAC’s tab buttons use 16px of padding on each side, so at 390px only about
23 letters fit across six tabs. The longer names (Overview, Yahtzees,
Strategy) push Games and Pubs off the bar with no scroll hint, so the
labels are the short plain words above.

## Methodology

Wins, margins, and the winner compare `computed_total` from `int_win_loss`
(the sum of the 15 boxes). High scores, low scores, lifetime points, and
averages use `recorded_total`, the grand total written on the card. A tie
for high or low uses the earliest `game_seq`.

Yahtzees are the 50-point box plus `yahtzee_bonus / 100`. A multi-Yahtzee
game has two or more. The upper bonus is 35 points once ones through sixes
reach 63, which is 3 dice on every face. That 3-dice line is the par mark
on the upper-dice chart.

Strategy rates are player-blind: exactly one of Erin or Jordan has the
feature, and the rate is how often that holder won. They are associated
with winning, not a cause. Cells and bars with fewer than 5 games are
faded or grey. Cohort keys in the marts stay snake_case and abbreviated;
the dashboard relabels them. Definitions:
[`assets/marts/strategy.md`](../assets/marts/strategy.md).

DAC 0.21.0 cannot make a table cell a link, so game tables show the game
number. Clickable lists are Vega-Lite `href` marks with
`usermeta.embedOptions.loader.target: _blank`, root-relative
(`/scorecards/viewer.html?game=N`). Widget `height` values are quoted
strings (`"168"`). A bare number becomes inline CSS that crushes stacked
cards below 640px.

## Runbook

These notes used to sit on the dashboard. The live site does not render
this file.

On [yahtzee.jginfo.xyz](https://yahtzee.jginfo.xyz), Caddy serves
`/scorecards` and `/pub_map.html` from `dashboard/` on disk and
reverse-proxies everything else to `dac serve` on 127.0.0.1:8321. Ports
8321 and 8765 are not public. There is no `http.server` sidecar. The
Caddyfile is in [`../docs/hosting-vps.md`](../docs/hosting-vps.md).

`dac serve` does not publish the scorecard viewer or the map. Locally, put
Caddy in front of it, or open `pub_map.html` directly (`file://` works for
that page on its own).

After `bruin run`:

```shell
python3 scripts/export_scorecards.py
python3 scripts/export_pub_map.py
```

Full-resolution Drive HEICs stay out of git. Copy `IMG_####.jpg` or `.HEIC`
into `scorecards/photos/` (see [`../docs/scorecard_ingest.md`](../docs/scorecard_ingest.md))
and re-run the scorecard export. Photo-vs-seed layout: [`scorecards.md`](scorecards.md).
Map layers: [`pub_map.md`](pub_map.md).

Queries hit DuckDB marts (`mart_headline_kpis`, `mart_player_kpis`,
`mart_game_trends`, `mart_category_stats`, `mart_strategy_swing` /
`mart_strategy_rescue` / `mart_yz_matchup`, plus `mart_head_to_head` /
`mart_pub_locations`).

DAC 0.21.0 cannot embed Leaflet/MapKit. The real map is `pub_map.html` (Esri
World Light Gray tiles, no API key): Boroughs / Pubs layers, pint pins
coloured by unique-day visits. See `pub_map.md` for regenerate / serve /
`dac build`.

Queries run against the pipeline DuckDB file (`yahtzee.duckdb` at the repo root)
via the read-only `local_duckdb` connection in `.bruin.yml`. The pipeline writes
through `duckdb-default` (same file, writable, one asset at a time).

Walkthrough screenshots: [`docs/screenshots/`](docs/screenshots/). Strategy tab
captures: `strategy_swing_factors.png`, `strategy_rescue_matrix.png`,
`strategy_yz_holder_won_vs_upset.png`.

## Prerequisites

From the repo root:

```shell
# Bruin + DAC CLIs (https://getbruin.com/docs/dac/getting-started/quickstart.html)
# curl -LsSf https://getbruin.com/install/cli | sh
# DAC pinned to 0.21.0 (same release as the VPS — docs/hosting-vps.md)
# curl -LsSf https://getbruin.com/install/dac | sh -s -- v0.21.0

cp -n ../.bruin.yml.example ../.bruin.yml   # if .bruin.yml is missing
pip install -r ../assets/python/requirements.txt
bruin run --workers 1                       # builds marts into yahtzee.duckdb
```

`dac` walks upward from this directory to find the repo-root `.bruin.yml`.

## Commands

```shell
dac validate --dir dashboard
dac validate --dir dashboard --with-database
dac check --dir dashboard --config /c/Users/jorda/yahtzee/yahtzee/.bruin.yml
dac serve --dir dashboard --template yahtzee-dark --open --config /c/Users/jorda/yahtzee/yahtzee/.bruin.yml
```

`--template yahtzee-dark` loads `themes/yahtzee-dark.yml` (extends `bruin-dark`,
Erin and Jordan chart tokens). The viewer still has a light/dark toggle; start from
dark.

The dashboard is served at `http://localhost:8321`.

## Interactive pub map

After `bruin run`, refresh the GeoJSON the Leaflet page reads:

```shell
python3 scripts/export_pub_map.py
```

On [yahtzee.jginfo.xyz](https://yahtzee.jginfo.xyz), Caddy serves
`/pub_map.html` and `/scorecards` from this directory. `dac serve` does not
publish them, and ports 8321 and 8765 are not open on the droplet.

To click those links on a laptop, run `dac serve` on 127.0.0.1:8321 and the
local Caddyfile in [`../docs/hosting-vps.md`](../docs/hosting-vps.md) so
root-relative paths resolve (`http://127.0.0.1:8080/pub_map.html`). Opening
`pub_map.html` as a local file still works. Optional MapTiler streets:
`?maptiler=YOUR_KEY` — not required.

## Connection

This project uses two DuckDB connections to the same `yahtzee.duckdb` file:

- `duckdb-default` — writable, `max_concurrent_assets: 1`, used by `bruin run`
- `local_duckdb` — `read_only: true`, used by this dashboard so widgets can
  query in parallel without DuckDB file-lock errors

The empty `data/dac-demo.duckdb` leftover from `dac init` is unused.
