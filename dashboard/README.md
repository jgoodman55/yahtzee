# Yahtzee DAC dashboard

Head-to-head record, streaks, commentary, and a totals spot-check widget.
Queries run against the pipeline DuckDB file (`yahtzee.duckdb` at the repo root)
via the `duckdb-default` connection in `.bruin.yml`.

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

This project uses `duckdb-default` (same name as `pipeline.yml`), not the
`local_duckdb` / `data/dac-demo.duckdb` names from `dac init`. The demo DuckDB
file is unused leftover from scaffolding.
