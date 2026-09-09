# Scorecards (photo | seed)

Jordan validated the seed by putting the **original sheet photo** next to a
**digitized scorecard** (Chance before Yahtzee; Erin pink / Jordan blue).
DAC 0.15 cannot host that comparison inside a table cell.

## What DAC 0.15 can do

Checked against [widgets](https://getbruin.com/docs/dac/dashboards/widgets.html)
and the table renderer (`TableWidget` has labels / number / format — no
markdown, no `href` on cells):

| Approach | Works in DAC 0.15? | Notes |
|---|---|---|
| Markdown links in **text** widgets | Yes | Same as the Pubs Leaflet link |
| `image` widget (`src` URL) | Yes | Static URL; no Jinja on `src` |
| Filters (`select` / `text`) | Yes | Dashboard-wide — would clutter Overview |
| Table cell markdown / `<a>` | No | Cells are formatted text only |
| Vega-Lite `href` on a text mark | Yes (used here) | Clickable “Game N” lists on Deep cuts |
| Arbitrary HTML / iframe in a widget | No | Same limit as the pub map |
| Sidecar static HTML next to `dac serve` | **Yes** | This page — port 8765 |

## Refresh after `bruin run`

```bash
# from repo root
python3 dashboard/scripts/export_scorecards.py
python3 dashboard/scripts/export_scorecards.py --png-samples 1,47,100
```

Writes `dashboard/scorecards/games.js` (and optional PNG composites). The
viewer and index are static HTML.

```bash
python3 -m http.server 8765 --directory dashboard
# http://localhost:8765/scorecards/index.html
# http://localhost:8765/scorecards/viewer.html?game=12
```

`dac serve` does **not** publish these files. Keep the sidecar on 8765 so
dashboard Markdown / Vega-Lite links work, or open the HTML directly
(`file://` works — `games.js` is inlined like `pub_map/pubs.js`).

## Photos from Drive

Full HEIC sheets are large and stay out of git (`dashboard/scorecards/photos/`).

1. Download `IMG_2885`–`IMG_2918` from
   https://drive.google.com/drive/folders/1nSooXGB5YhYIaP43eBJdxjCR3NHSZxEo
2. Drop `IMG_####.HEIC` or `.jpg` into `dashboard/scorecards/photos/`
3. Re-run `export_scorecards.py`

This repo ships a few downscaled sample JPGs under
`dashboard/scorecards/samples/photos/` plus PNG composites for games 1, 47,
and 100 so the Scorecards tab image and the viewer work without Drive.

Crosswalk: `assets/seeds/sheet_game_crosswalk.csv` (`game_seq` → sheet +
`game_on_sheet`).
