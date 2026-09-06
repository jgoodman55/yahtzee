# Pub map — inside the same DAC dashboard

Venues stay **standalone** from games. We only kept `game_seq`, not dates, so
there is no reliable game-to-pub join. Do not invent one.

## What DAC 0.15 can (and cannot) do

Checked against [DAC widgets](https://getbruin.com/docs/dac/dashboards/widgets.html),
[TSX](https://getbruin.com/docs/dac/dashboards/tsx.html),
[layout/tabs](https://getbruin.com/docs/dac/dashboards/layout.html), and
[dac import](https://getbruin.com/docs/dac/commands/import.html) (`map` cards
from Metabase are converted to **tables**).

| Approach | Works in DAC 0.15? | Notes |
|---|---|---|
| Native map widget | No | Widget types are `metric`, `chart`, `table`, `text`, `image`, `divider`. No `map`. |
| Leaflet / MapLibre HTML | No | `text` is Markdown only (no `<iframe>` / `<script>`). |
| TSX custom React map | No | TSX is compiled in Go (`goja`) and flattened to the same widget model as YAML. It is not a runtime React tree. |
| `image` of a static map | Yes, but stale | URL-only; not query-backed. |
| Vega-Lite lon/lat | **Yes** | `chart: vega-lite` with `longitude` / `latitude` encodings. DAC injects SQL results as the `dac` dataset. Remote `data.url` (OSM tiles, GeoJSON basemaps) is rejected, so this is a projected pin plot, not a tiled street map. |
| Table of venues | Yes | Always available, including unresolved rows with no coordinates. |

## Prototype (this repo)

`yahtzee.yml` is one dashboard with two tabs:

- **Head-to-head** — games, commentary, totals spot-check
- **Pubs** — Vega-Lite pins from `mart_pub_locations` (confirmed rows only) plus an **All venues** table

```bash
dac serve --dir dashboard --open
# open Yahtzee Head-to-Head → Pubs
```

If you later need a real tiled OSM map, host a tiny static `pub_map.html`
*next to* the DAC site (or wait for a native DAC map widget). Do not join it
to `mart_head_to_head`.
