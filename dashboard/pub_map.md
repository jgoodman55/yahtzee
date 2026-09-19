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
inside DAC). Leaflet + a light Esri gray canvas is the closest practical
equivalent: pan/zoom, borough choropleth, pint pins, name + visit popups.

## Interactive map (primary)

`dashboard/pub_map.html` loads confirmed rows from `mart_pub_locations`
(`pub_map/pubs.js`, regenerated from DuckDB). Two layers:

| Layer | Default | What you see |
|---|---|---|
| **Pubs** (Layer B) | Yes (`#pubs`) | Same-size SVG pint-glass pins (~16×20px, not emoji). Fill colour ramps pale lager → deep stout/amber by unique-day `visit_count`. |
| **Boroughs** (Layer A) | `#boroughs` | Choropleth of London boroughs labelled with unique-day visit totals. Click a borough (or a row in the list) to switch to Pubs, filtered and zoomed to that borough’s pins. |

Toggle **Boroughs / Pubs** in the header. A crumb **← Boroughs** appears after drill-down. Photo popups are still future work; hover/click shows name, unique-day visits, and the seed address/note when present.

Default overview fits **Greater London** so the pint field stays readable. Oxford pubs are listed as **Outside London** on the borough view (and as ordinary pins if you zoom/pan out).

Default basemap is
[Esri World Light Gray](https://www.esri.com/) canvas tiles (base + labels) —
**no API key and no signup**. (CartoDB Positron is the usual keyless light
style, but those tiles now watermark without a Carto key.)

### Borough boundaries (source + attribution)

Vendored at `dashboard/pub_map/london_boroughs.geojson` (and `london_boroughs.js`
for `file://`).

- **Dataset:** [ONS Local Authority Districts (May 2024) Boundaries UK BGC](https://geoportal.statistics.gov.uk/) — generalised 20 m, clipped to Mean High Water.
- **Filter:** `LAD24CD LIKE 'E09%'` (32 London boroughs + City of London).
- **Service used to download:** ArcGIS FeatureServer `Local_Authority_Districts_May_2024_Boundaries_UK_BGC` (`outSR=4326`).
- **Processing:** coordinates rounded to 5 decimal places (~1 m) to keep the file small. Properties kept: `name`, `lad24cd`.
- **Licence:** [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
- **Copyright:** Contains OS data © Crown copyright and database right 2024. Contains National Statistics data © Crown copyright and database right 2024.

The map does **not** add a `borough` column to `mart_pub_locations`. Assignment is
client-side: ray-casting point-in-polygon, then (only for points inside the
Greater London bbox that miss a polygon — e.g. Tamesis Dock on the Thames)
snap to the nearest borough within ~1 km. Oxford stays **Outside London**.

### Optional nicer tiles (not required)

Append `?maptiler=YOUR_KEY` to the map URL to use MapTiler Streets. Jordan
does **not** need this for the default path. Do not commit a key.

### Regenerate data after `bruin run`

```bash
# from repo root, after marts are built
# optional: rebuild unique-day visits from the Chase export (not in git)
# python3 assets/python/build_pub_visits.py --chase Chase7977_Activity_20260830.csv
python3 dashboard/scripts/export_pub_map.py
# optional: python3 dashboard/scripts/export_pub_map.py --db /path/to/yahtzee.duckdb
```

Writes `dashboard/pub_map/pubs.geojson` and `dashboard/pub_map/pubs.js`.
`pubs.js` is what the HTML loads so the map also works as a local `file://`
page (no CORS fetch). Seed `note` (address / Jordan pin comment) is joined in
the exporter from `assets/seeds/seed_pubs.csv` — not a mart column.

`visit_count` is **unique calendar days** at that pin: one `raw_pub_visits`
row per merchant × Transaction Date (summed when proximity-dedup collapses
venues). Same-day Chase sales at the same location are one visit. It is not
a game-to-pub join.

Chase statement merchants classified `likely_pub=yes` (Jordan 2026-09-14)
are in `seed_pubs.csv` / `raw_pub_visits.csv`. Excluded: Thomas Cubitt,
Hung Drawn & Quartered, Bar Crispin, Guinness Open Gate Brewery, Hector’s,
The Buccaneer (didn’t play there), Walrus / Walrus & Carpenter (didn’t
play there), FCB Paddington (coffee, not a pub).
The Derby and Hanover Arms stay as separate pins (~30m neighbors; identity
exception in proximity dedupe). Beehive is exactly 1 visit (Jordan override).
Spaniards Inn is the OSM pub amenity on Spaniards Road, not the bus stop.
ANCHOR BANKSIDE maps to the existing Anchor Bar seed (alias row, same
coords). Rebuild visit rows with `assets/python/build_pub_visits.py --chase
Chase7977_Activity_20260830.csv` (unique days from `Sale` rows; the Chase
file is not committed). Kept sample rows: Crown Tavern (2), THE RED LION
LDN, and DOG N BONE PH LONDON. The original three sample ANCHOR BAR rows
were replaced by Chase Bankside days so visit_count is statement-based, not
mixed demo+Chase.

**MC and Sons** (both seed pins kept): Southwark (`MC AND SONS`) statement
days 2026-08-09, 2026-07-25, 2026-07-18 → **3** visits; Vauxhall
(`MC AND SONS VAUXHALL`) days 2026-08-20, 2026-08-19, 2026-07-30 → **3**
visits.

**Vauxhall Marketplace** (one pin at 7 S Lambeth Pl; statement strings like
`TST-Unit … Vauxhall MP` / `TST-MarketPlace - Vaux`) is **3** unique days
(2026-08-24, 2026-08-20, 2026-08-06). Unresolved merchants stay in the
visit log without invented coordinates.

### Open / serve

```bash
# 1) Double-click / open in a browser (file://). Esri light-gray tiles still load.
open dashboard/pub_map.html   # macOS; or just open the file

# 2) Tiny static server (needed for the DAC Markdown link on :8765)
python3 -m http.server 8765 --directory dashboard
# then http://localhost:8765/pub_map.html
# Layers: http://localhost:8765/pub_map.html#pubs
#         http://localhost:8765/pub_map.html#boroughs
# Drill:  http://localhost:8765/pub_map.html#borough=Southwark

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

`yahtzee.yml` is one dashboard with five tabs (Overview → Races → Zeros →
Deep cuts → **Pubs**). The Pubs tab is a link to this Leaflet page plus the
venue table — DAC still cannot embed the map.
