#!/usr/bin/env python3
"""Build per-game photo + seed scorecard pages.

Reads `raw_games.csv` + `sheet_game_crosswalk.csv` (and mart_game_trends when
the DuckDB file exists) and writes:

  dashboard/scorecards/games.js     window.SCORECARD_DATA (file:// safe)
  dashboard/scorecards/samples/*.png  optional photo|seed composites

HTML (`index.html`, `viewer.html`) is hand-written and reads games.js.

Photos (optional, often too large for git):
  dashboard/scorecards/photos/IMG_####.jpg|.jpeg|.png|.webp|.HEIC
  dashboard/scorecards/samples/photos/IMG_####.jpg   (committed samples)

Refresh after `bruin run` or seed edits:

  python3 dashboard/scripts/export_scorecards.py
  python3 dashboard/scripts/export_scorecards.py --png-samples 1,47,100

Then serve beside DAC:

  python3 -m http.server 8765 --directory dashboard
  # http://localhost:8765/scorecards/viewer.html?game=12
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "yahtzee.duckdb"
OUT_DIR = REPO_ROOT / "dashboard" / "scorecards"
PHOTOS_DIR = OUT_DIR / "photos"
SAMPLE_PHOTOS = OUT_DIR / "samples" / "photos"
SAMPLE_DIR = OUT_DIR / "samples"
GAMES_CSV = REPO_ROOT / "assets" / "seeds" / "raw_games.csv"
CROSSWALK_CSV = REPO_ROOT / "assets" / "seeds" / "sheet_game_crosswalk.csv"

ERIN = "#FF2D92"
JORDAN = "#2D9CFF"
BG = "#0A0C10"
SURFACE = "#12171F"

# Physical Hasbro order — Chance before Yahtzee (see ingestion/scorecard_format.md).
UPPER = [
    ("ones", "Aces"),
    ("twos", "Twos"),
    ("threes", "Threes"),
    ("fours", "Fours"),
    ("fives", "Fives"),
    ("sixes", "Sixes"),
    ("upper_bonus", "Bonus"),
]
LOWER = [
    ("three_of_a_kind", "3 of a Kind"),
    ("four_of_a_kind", "4 of a Kind"),
    ("full_house", "Full House"),
    ("small_straight", "Small Straight"),
    ("large_straight", "Large Straight"),
    ("chance", "Chance"),
    ("yahtzee", "Yahtzee"),
    ("yahtzee_bonus", "Yahtzee Bonus"),
]
ALL_CATS = [k for k, _ in UPPER + LOWER]


def _connect(db_path: Path):
    try:
        import duckdb
    except ImportError:
        return None
    if not db_path.exists():
        return None
    return duckdb.connect(str(db_path), read_only=True)


def load_crosswalk() -> dict[int, dict]:
    rows = {}
    with CROSSWALK_CSV.open(newline="", encoding="utf-8") as fh:
        for rec in csv.DictReader(fh):
            seq = int(rec["game_seq"])
            rows[seq] = {
                "game_seq": seq,
                "sheet": rec["sheet"].strip(),
                "game_on_sheet": int(rec["game_on_sheet"]),
            }
    return rows


def load_scores() -> dict[tuple[int, str], dict[str, int]]:
    out: dict[tuple[int, str], dict[str, int]] = defaultdict(dict)
    recorded: dict[tuple[int, str], int] = {}
    with GAMES_CSV.open(newline="", encoding="utf-8") as fh:
        for rec in csv.DictReader(fh):
            key = (int(rec["game_seq"]), rec["player"].strip().lower())
            out[key][rec["category"].strip()] = int(rec["score"])
            recorded[key] = int(rec["recorded_total"])
    for key, scores in out.items():
        scores["_recorded"] = recorded[key]
    return out


def load_trends(db_path: Path) -> dict[int, dict]:
    con = _connect(db_path)
    if con is None:
        return {}
    try:
        cols = {
            r[0]
            for r in con.execute(
                "select lower(column_name) from information_schema.columns "
                "where lower(table_name) = 'mart_game_trends'"
            ).fetchall()
        }
        if not cols:
            return {}
        erin_c = (
            "erin_computed_total"
            if "erin_computed_total" in cols
            else "erin_total"
        )
        jordan_c = (
            "jordan_computed_total"
            if "jordan_computed_total" in cols
            else "jordan_total"
        )
        rows = con.execute(
            f"""
            select game_seq, winner, margin, {erin_c}, {jordan_c}
            from mart_game_trends
            order by game_seq
            """
        ).fetchall()
        return {
            int(seq): {
                "winner": winner,
                "margin": int(margin),
                "erin_computed": int(erin_t),
                "jordan_computed": int(jordan_t),
            }
            for seq, winner, margin, erin_t, jordan_t in rows
        }
    finally:
        con.close()


def resolve_photo(sheet: str) -> str | None:
    stems = [sheet, sheet.lower(), sheet.upper()]
    exts = (".jpg", ".jpeg", ".png", ".webp", ".HEIC", ".heic")
    search_dirs = (PHOTOS_DIR, SAMPLE_PHOTOS)
    for directory in search_dirs:
        if not directory.exists():
            continue
        for stem in stems:
            for ext in exts:
                path = directory / f"{stem}{ext}"
                if path.exists():
                    return str(path.relative_to(OUT_DIR)).replace("\\", "/")
    return None


def player_box(scores: dict[str, int]) -> dict:
    cats = {k: int(scores.get(k, 0)) for k in ALL_CATS}
    computed = sum(cats.values())
    return {
        "scores": cats,
        "recorded_total": int(scores.get("_recorded", computed)),
        "computed_total": computed,
    }


def build_games(db_path: Path) -> list[dict]:
    crosswalk = load_crosswalk()
    scores = load_scores()
    trends = load_trends(db_path)
    games = []
    for seq in sorted(crosswalk):
        cw = crosswalk[seq]
        erin = player_box(scores.get((seq, "erin"), {}))
        jordan = player_box(scores.get((seq, "jordan"), {}))
        trend = trends.get(seq)
        if trend:
            winner = trend["winner"]
            margin = trend["margin"]
            erin["computed_total"] = trend["erin_computed"]
            jordan["computed_total"] = trend["jordan_computed"]
        else:
            if erin["computed_total"] > jordan["computed_total"]:
                winner = "erin"
            elif jordan["computed_total"] > erin["computed_total"]:
                winner = "jordan"
            else:
                winner = "tie"
            margin = abs(erin["computed_total"] - jordan["computed_total"])
        games.append(
            {
                "game_seq": seq,
                "sheet": cw["sheet"],
                "game_on_sheet": cw["game_on_sheet"],
                "winner": winner,
                "margin": margin,
                "erin": erin,
                "jordan": jordan,
                "photo": resolve_photo(cw["sheet"]),
            }
        )
    return games


def write_games_js(games: list[dict]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lower_order": [k for k, _ in LOWER],
        "games": games,
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    path = OUT_DIR / "games.js"
    path.write_text(
        "// Generated by dashboard/scripts/export_scorecards.py — do not edit.\n"
        "window.SCORECARD_DATA = " + text + ";\n",
        encoding="utf-8",
    )
    return path


def _try_import_pil():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:
        pass
    return Image, ImageDraw, ImageFont


def _font(size: int, bold: bool = False):
    from PIL import ImageFont

    names = (
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _open_photo(rel: str | None):
    Image, _, _ = _try_import_pil()
    if Image is None or not rel:
        return None
    path = OUT_DIR / rel
    if not path.exists():
        return None
    return Image.open(path).convert("RGB")


def render_composite_png(game: dict, sheet_games: list[dict], dest: Path) -> None:
    """Photo (or placeholder) | seed-rendered sheet. Chance before Yahtzee."""
    mods = _try_import_pil()
    if mods is None:
        raise SystemExit("Pillow is required for --png-samples (pip install pillow)")
    Image, ImageDraw, _ImageFont = mods

    row_h = 22
    labels = (
        [("hdr", "Number Combos")]
        + [("box", lab) for _, lab in UPPER]
        + [("sum", "Upper total")]
        + [("hdr", "Special Combos")]
        + [("box", lab) for _, lab in LOWER]
        + [("sum", "Lower total")]
        + [("sum", "Grand total")]
    )
    cat_w = 132
    col_w = 54
    n_cols = len(sheet_games) * 2
    card_w = cat_w + n_cols * col_w + 16
    card_h = 70 + row_h * len(labels) + 16
    pad = 16
    header_h = 52

    photo = _open_photo(game.get("photo"))
    photo_w = 520
    if photo is not None:
        ratio = photo_w / photo.width
        photo = photo.resize((photo_w, max(1, int(photo.height * ratio))), Image.Resampling.LANCZOS)
        photo_h = photo.height
    else:
        photo_h = card_h

    width = pad + photo_w + pad + card_w + pad
    height = header_h + pad + max(photo_h, card_h) + pad
    im = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(im)
    title_f = _font(22, bold=True)
    small_f = _font(13)
    box_f = _font(12)
    label_f = _font(12, bold=True)

    title = f"Game {game['game_seq']}  ·  {game['sheet']} game {game['game_on_sheet']}"
    draw.text((pad, 14), title, fill="#F3F6FA", font=title_f)
    draw.text(
        (pad, 40),
        f"winner {game['winner']}   margin {game['margin']}   "
        f"Erin {game['erin']['recorded_total']} / Jordan {game['jordan']['recorded_total']}",
        fill="#A8B3C5",
        font=small_f,
    )

    photo_x, photo_y = pad, header_h + 8
    if photo is not None:
        im.paste(photo, (photo_x, photo_y))
    else:
        draw.rectangle(
            [photo_x, photo_y, photo_x + photo_w, photo_y + photo_h],
            fill=SURFACE,
            outline="#2A3344",
        )
        draw.text(
            (photo_x + 24, photo_y + 40),
            f"No local photo for {game['sheet']}",
            fill="#A8B3C5",
            font=small_f,
        )

    card_x = photo_x + photo_w + pad
    card_y = photo_y
    draw.rectangle(
        [card_x, card_y, card_x + card_w, card_y + card_h],
        fill="#161C26",
        outline="#2A3344",
    )

    def _score(g, player, kind, lab):
        scores = g[player]["scores"]
        if kind == "hdr":
            return ""
        if lab == "Upper total":
            return sum(scores[k] for k, _ in UPPER)
        if lab == "Lower total":
            return sum(scores[k] for k, _ in LOWER)
        if lab == "Grand total":
            return g[player]["computed_total"]
        key = next(k for k, name in UPPER + LOWER if name == lab)
        return scores[key]

    y = card_y + 8
    # header row
    draw.text((card_x + 8, y), "Game", fill="#A8B3C5", font=label_f)
    for i, g in enumerate(sheet_games):
        mark = " ▸" if g["game_seq"] == game["game_seq"] else ""
        draw.text(
            (card_x + cat_w + i * 2 * col_w + 8, y),
            f"#{g['game_seq']}{mark}",
            fill="#F3F6FA",
            font=label_f,
        )
    y += row_h
    draw.text((card_x + 8, y), "Player", fill="#A8B3C5", font=label_f)
    for i, _g in enumerate(sheet_games):
        draw.text((card_x + cat_w + i * 2 * col_w + 4, y), "Erin", fill=ERIN, font=label_f)
        draw.text(
            (card_x + cat_w + i * 2 * col_w + col_w + 4, y),
            "Jordan",
            fill=JORDAN,
            font=label_f,
        )
    y += row_h

    for kind, lab in labels:
        if kind == "sum":
            draw.rectangle(
                [card_x + 1, y - 1, card_x + card_w - 1, y + row_h - 2],
                fill="#1A2130",
            )
        draw.text((card_x + 8, y + 3), lab, fill="#A8B3C5", font=label_f)
        for i, g in enumerate(sheet_games):
            ev, jv = _score(g, "erin", kind, lab), _score(g, "jordan", kind, lab)
            ex = card_x + cat_w + i * 2 * col_w + 10
            jx = ex + col_w
            if g["game_seq"] == game["game_seq"]:
                draw.rectangle(
                    [ex - 8, y - 1, jx + col_w - 12, y + row_h - 2],
                    fill="#1E2430",
                )
            draw.text((ex, y + 3), str(ev), fill="#FF7AB8", font=box_f)
            draw.text((jx, y + 3), str(jv), fill="#7ABBFF", font=box_f)
        y += row_h

    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, optimize=True)


def chrome_screenshot(game_seq: int, dest: Path) -> bool:
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not chrome:
        return False
    url = (OUT_DIR / "viewer.html").resolve().as_uri() + f"?game={game_seq}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-sandbox",
        f"--window-size=1500,1100",
        f"--screenshot={dest}",
        url,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    return dest.exists()


def write_sample_pngs(games: list[dict], seqs: list[int], engine: str) -> list[Path]:
    by_seq = {g["game_seq"]: g for g in games}
    written = []
    for seq in seqs:
        game = by_seq.get(seq)
        if game is None:
            print(f"skip sample game {seq}: not in seed")
            continue
        sheet_games = [g for g in games if g["sheet"] == game["sheet"]]
        dest = SAMPLE_DIR / f"game_{seq}.png"
        used = None
        if engine in ("chrome", "auto") and chrome_screenshot(seq, dest):
            used = "chrome"
        if used is None and engine in ("pillow", "auto"):
            render_composite_png(game, sheet_games, dest)
            used = "pillow"
        if used is None:
            raise SystemExit(f"Could not render sample for game {seq} (engine={engine})")
        written.append(dest)
        print(f"  sample game {seq}: {dest.relative_to(REPO_ROOT)} ({used})")
    return written


def parse_seqs(raw: str) -> list[int]:
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--png-samples",
        default="",
        help="Comma-separated game_seq values to write under samples/ (e.g. 1,47,100)",
    )
    parser.add_argument(
        "--png-engine",
        choices=("auto", "chrome", "pillow"),
        default="auto",
        help="How to render --png-samples (default: chrome if present, else Pillow)",
    )
    args = parser.parse_args()

    if not GAMES_CSV.exists() or not CROSSWALK_CSV.exists():
        raise SystemExit("raw_games.csv / sheet_game_crosswalk.csv missing")

    # Sanity: Chance must precede Yahtzee on the rendered card.
    lower_keys = [k for k, _ in LOWER]
    if lower_keys.index("chance") > lower_keys.index("yahtzee"):
        raise SystemExit("LOWER category order must put chance before yahtzee")

    games = build_games(args.db)
    js_path = write_games_js(games)
    with_photo = sum(1 for g in games if g["photo"])
    print(
        f"Wrote {len(games)} games → {js_path.relative_to(REPO_ROOT)} "
        f"({with_photo} with a local photo)"
    )
    if args.png_samples:
        write_sample_pngs(games, parse_seqs(args.png_samples), args.png_engine)


if __name__ == "__main__":
    main()
