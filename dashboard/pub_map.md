# Pub map

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
| Leaflet / MapLibre / MapKit HTML | No | `text` is Markdown only (no `<iframe>` / `<script>`). |
| TSX custom React map | No | TSX is compiled in Go (`goja`) and flattened to the same widget model as YAML. It is not a runtime React tree. |
| Vega-Lite lon/lat | Yes (fallback) | Projected pin plot only. DAC rejects remote tile/GeoJSON `data.url`. |
| Standalone Leaflet page next to DAC | **Yes** | `dashboard/pub_map.html` — this is the primary map. |

This is **not Apple MapKit** (that needs an Apple token and still cannot live
inside DAC). Leaflet + OSM is the closest practical equivalent: pan/zoom,
visit-sized bubbles, name + visit popups.

## Interactive map (primary)

`dashboard/pub_map.html` loads confirmed rows from `mart_pub_locations`
(`pub_map/pubs.js`, regenerated from DuckDB). Circle radius scales with
`visit_count`. Default center is London. Default basemap is free
[OpenStreetMap](https://www.openstreetmap.org/copyright) raster tiles —
**no API key and no signup**.

### Optional nicer tiles (not required)

Append `?maptiler=YOUR_KEY` to the map URL to use MapTiler Streets. Jordan
does **not** need this for the default path. Do not commit a key.

### Regenerate data after `bruin run`

```bash
# from repo root, after marts are built
python3 dashboard/scripts/export_pub_map.py
# optional: python3 dashboard/scripts/export_pub_map.py --db /path/to/yahtzee.duckdb
```

Writes `dashboard/pub_map/pubs.geojson` and `dashboard/pub_map/pubs.js`.
`pubs.js` is what the HTML loads so the map also works as a local `file://`
page (no CORS fetch).

`visit_count` is the number of `raw_pub_visits` rows per merchant (summed
when proximity-dedup collapses venues). It is not a game-to-pub join.

### Open / serve

```bash
# 1) Double-click / open in a browser (file://). OSM tiles still load.
open dashboard/pub_map.html   # macOS; or just open the file

# 2) Tiny static server (needed for the DAC Markdown link on :8765)
python3 -m http.server 8765 --directory dashboard
# then http://localhost:8765/pub_map.html

# 3) DAC itself (widgets only — it will not serve pub_map.html)
dac serve --dir dashboard --open
# Pubs tab → "Open the interactive Leaflet map"
```

`dac serve` does not publish extra HTML. Keep the sidecar on port 8765 if you
want the dashboard link to work, or open the file directly.

### `dac build` static export

```bash
dac build --dir dashboard --dashboard "Yahtzee Head-to-Head" --output build
cp dashboard/pub_map.html build/
cp -R dashboard/pub_map build/pub_map
```

DAC's build output is only `index.html` + hashed assets. Copy the map files
next to it so a relative `pub_map.html` link works on the same static host.
The baked Vega plot remains the in-dashboard fallback.

## Prototype (this repo)

`yahtzee.yml` is one dashboard with two tabs:

- **Head-to-head** — games, commentary, totals spot-check
- **Pubs** — link to the Leaflet map, Vega-Lite fallback, **All venues** table
