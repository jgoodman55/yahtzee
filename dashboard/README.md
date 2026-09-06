# Yahtzee DAC dashboard

One DAC dashboard with two tabs: **Head-to-head** (record, streaks, commentary,
totals spot-check) and **Pubs** (Vega-Lite lon/lat pins + venue table). Pubs
are not joined to games. See `pub_map.md` for why Leaflet cannot live inside
DAC 0.15.

Queries run against the pipeline DuckDB file (`yahtzee.duckdb` at the repo root)
via the read-only `local_duckdb` connection in `.bruin.yml`. The pipeline writes
through `duckdb-default` (same file, writable, one asset at a time).

Walkthrough screenshots: [`docs/screenshots/`](docs/screenshots/).

## Prerequisites

From the repo root:

```shell
# Bruin + DAC CLIs (https://getbruin.com/docs/dac/getting-started/quickstart.html)
# curl -LsSf https://getbruin.com/install/cli | sh
# curl -LsSf https://getbruin.com/install/dac | sh

cp -n ../.bruin.yml.example ../.bruin.yml   # if .bruin.yml is missing
pip install -r ../assets/python/requirements.txt
OFFLINE_TEST=1 bruin run                    # builds marts into yahtzee.duckdb
```

`dac` walks upward from this directory to find the repo-root `.bruin.yml`.

## Commands

```shell
dac validate --dir .
dac validate --dir . --with-database
dac check --dir .
dac serve --dir . --open
```

The dashboard is served at `http://localhost:8321`.

## Connection

This project uses two DuckDB connections to the same `yahtzee.duckdb` file:

- `duckdb-default` — writable, `max_concurrent_assets: 1`, used by `bruin run`
- `local_duckdb` — `read_only: true`, used by this dashboard so widgets can
  query in parallel without DuckDB file-lock errors

The empty `data/dac-demo.duckdb` leftover from `dac init` is unused.
