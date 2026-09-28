# Scorecards (photo | seed)

Jordan validated the seed by putting the **original sheet photo** next to a
**digitized scorecard** (Chance before Yahtzee).
DAC 0.21.0 cannot host that comparison inside a table cell.

## What DAC 0.21.0 can do

Checked against [widgets](https://getbruin.com/docs/dac/dashboards/widgets.html)
and the table renderer (labels / number / format / image thumbnails — no
markdown, no `href` on cells):

| Approach | Works in DAC 0.21.0? | Notes |
|---|---|---|
| Markdown links in **text** widgets | Yes | Same as the Pubs Leaflet link |
| `image` widget | Yes | Data-driven since 0.18. `src`, `alt`, `title`, and `caption` name columns from `sql`, `query`, or inline `data`. A bare URL in `src` fails validation (`one of query, sql, or data is required`). The Scorecards sample uses `data` so the Game 1 composite still renders. |
| Filters (`select` / `text`) | Yes | Dashboard-wide — would clutter Overview |
| Table cell markdown / `<a>` | No | Cells are formatted text or image thumbnails only |
| Vega-Lite `href` on a text mark | Yes (used here) | Clickable “Game N” lists on Deep cuts. Vega-Lite has no `target` encoding; we set `usermeta.embedOptions.loader.target: _blank`. A root-relative `href` (`/scorecards/viewer.html?game=N`) opens the viewer in a **new tab** when DAC honors that target. Image widgets cannot do this. |
| Image widget click / `href` | No | No click target on the image itself. A markdown `caption` column can link out. |
| Arbitrary HTML / iframe in a widget | No | Same limit as the pub map |
| Static HTML beside `dac serve` | **Yes** | Caddy `file_server` for `/scorecards` and `/pub_map.html` from `dashboard/`. DAC does not publish these files. |

## Refresh after `bruin run`

```bash
# from repo root
python3 dashboard/scripts/export_scorecards.py
python3 dashboard/scripts/export_scorecards.py --png-samples 1,47,100
```

Writes `dashboard/scorecards/games.js` (and optional PNG composites). The
viewer and index are static HTML.

On [yahtzee.jginfo.xyz](https://yahtzee.jginfo.xyz), Caddy serves this folder
at `/scorecards` (and `/scorecards/*`). `dac serve` does **not** publish
these files, and there is no `python -m http.server` sidecar.

```text
https://yahtzee.jginfo.xyz/scorecards/index.html
https://yahtzee.jginfo.xyz/scorecards/viewer.html?game=12
```

Locally, put the same routes in front of `dac serve` (Caddyfile in
`docs/hosting-vps.md`) so root-relative dashboard links resolve, or open the
HTML directly (`file://` works — `games.js` is inlined like `pub_map/pubs.js`).

## Photos

Full-resolution HEIC sheets stay out of git (`dashboard/scorecards/photos/`).
Every sheet the crosswalk names (`IMG_2885`–`IMG_2922`) is committed as a
web JPEG under `dashboard/scorecards/samples/photos/` (about 1200×1600,
EXIF/GPS stripped). `resolve_photo` in `export_scorecards.py` checks that
directory before `photos/`, so `games.js` points at the committed files and
the hosted site can show a sheet for every game.

`viewer.html` still tries `photos/` first, so a local full-resolution copy
wins when you have one:

1. Download originals from
   https://drive.google.com/drive/folders/1nSooXGB5YhYIaP43eBJdxjCR3NHSZxEo
2. Drop `IMG_####.HEIC` or `.jpg` into `dashboard/scorecards/photos/`
3. Re-run `export_scorecards.py` (sample JPGs still win in `games.js`)

PNG composites for games 1, 47, and 100 are the Scorecards tab sample.

Crosswalk: `assets/seeds/sheet_game_crosswalk.csv` (`game_seq` → sheet +
`game_on_sheet`).
