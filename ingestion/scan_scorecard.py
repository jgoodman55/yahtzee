"""
Reads photographed Yahtzee scorecards (handwritten — see
scorecard_format.md for the physical layout and known notation quirks)
using a vision-capable Claude model, spot-checks the arithmetic, and
writes clean results to the pipeline's seed CSVs.

Each photographed sheet can hold up to 3 games. Game numbering comes
from the filename, not from guessing — name files like:

    scorecard_games_1_to_3.jpg      (3 games, game_seq 1, 2, 3)
    scorecard_games_4_to_6.jpg      (3 games, game_seq 4, 5, 6)
    scorecard_games_7_to_8.jpg      (only 2 games filled in on that sheet)

The number of games extracted from the image must match the count implied
by the filename (end - start + 1) or the whole file is flagged for
review rather than guessed at.

Usage:
    export ANTHROPIC_API_KEY=...
    python scan_scorecard.py --dir /path/to/photos
    python scan_scorecard.py --image scorecard_games_1_to_3.jpg

Nothing is written to the real seed files for a game with a totals
mismatch or any model-flagged uncertain cell — those get dumped to a
<filename>.review.json next to the image instead, for manual review.
Silently trusting either the arithmetic or the handwriting would hide
real data-entry mistakes rather than catch them.
"""

import argparse
import base64
import csv
import json
import re
import sys
from pathlib import Path

import anthropic

SEEDS_DIR = Path(__file__).parent.parent / "assets" / "seeds"
RAW_GAMES_CSV = SEEDS_DIR / "raw_games.csv"
RAW_TOTALS_CSV = SEEDS_DIR / "raw_game_totals.csv"
FORMAT_DOC = Path(__file__).parent / "scorecard_format.md"

CATEGORIES = [
    "ones", "twos", "threes", "fours", "fives", "sixes", "upper_bonus",
    "three_of_a_kind", "four_of_a_kind", "full_house", "small_straight",
    "large_straight", "yahtzee", "chance", "yahtzee_bonus",
]

FILENAME_RANGE_RE = re.compile(r"(\d+)_to_(\d+)")


def build_prompt(expected_game_count: int) -> str:
    format_doc = FORMAT_DOC.read_text() if FORMAT_DOC.exists() else ""
    return f"""\
This is a photo of a handwritten Yahtzee scorecard sheet. It should
contain {expected_game_count} game(s), in left-to-right column order
(players are "jordan" and "erin" for each game — the sheet's column
headers use initials J and E).

Reference on the physical layout and known notation quirks for this
scorecard, follow it carefully:

---
{format_doc}
---

Extract every category for both players, for every game on the sheet.
For any cell you're not confident about (illegible, ambiguous
crossing-out, smudged, or an arithmetic check that doesn't resolve
cleanly), include its category name in that player's
"uncertain_categories" list instead of guessing.

Respond with ONLY this JSON structure, no other text — a list with
exactly {expected_game_count} entries, one per game, left to right:
[
  {{
    "jordan": {{"ones": 0, "twos": 0, ..., "yahtzee_bonus": 0,
                "recorded_total": 0, "uncertain_categories": []}},
    "erin": {{"ones": 0, "twos": 0, ..., "yahtzee_bonus": 0,
              "recorded_total": 0, "uncertain_categories": []}}
  }},
  ...
]
"""


def encode_image(path: Path) -> tuple[str, str]:
    media_type = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".heic": "image/heic",
    }.get(path.suffix.lower(), "image/jpeg")
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return data, media_type


def parse_filename_range(path: Path) -> tuple[int, int]:
    match = FILENAME_RANGE_RE.search(path.stem)
    if not match:
        raise ValueError(
            f"Can't find a '<start>_to_<end>' pattern in filename '{path.name}'. "
            "Rename it like 'scorecard_games_1_to_3.jpg'."
        )
    start, end = int(match.group(1)), int(match.group(2))
    if end < start:
        raise ValueError(f"'{path.name}': end ({end}) is before start ({start}).")
    return start, end


def extract_scorecard(image_path: Path, expected_game_count: int) -> list[dict]:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    data, media_type = encode_image(image_path)

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=3000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}},
                {"type": "text", "text": build_prompt(expected_game_count)},
            ],
        }],
    )
    text = response.content[0].text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def spot_check(player: str, values: dict) -> list[str]:
    problems = []
    if values.get("uncertain_categories"):
        problems.append(f"{player}: OCR flagged uncertain cells: {values['uncertain_categories']}")
    computed = sum(values.get(c, 0) for c in CATEGORIES)
    recorded = values.get("recorded_total", 0)
    if computed != recorded:
        problems.append(
            f"{player}: computed sum {computed} != recorded total {recorded} "
            f"(diff {computed - recorded:+d})"
        )
    return problems


def process_image(image_path: Path) -> tuple[list[dict], list[str], int, int]:
    """Returns (clean_games, problems, start_seq, end_seq). clean_games is
    empty if anything on the sheet had a problem — the whole sheet is
    all-or-nothing so game_seq numbering never gets out of sync."""
    start, end = parse_filename_range(image_path)
    expected_count = end - start + 1

    print(f"  Extracting {image_path.name} (expecting {expected_count} game(s)) ...")
    games = extract_scorecard(image_path, expected_count)

    problems = []
    if len(games) != expected_count:
        problems.append(
            f"filename implies {expected_count} game(s) but extraction returned {len(games)}"
        )

    for i, game in enumerate(games):
        for player in ("jordan", "erin"):
            problems += [f"game {start + i}: {p}" for p in spot_check(player, game[player])]

    return (games if not problems else []), problems, start, end


def write_to_seeds(game_seq: int, game: dict):
    with open(RAW_GAMES_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        for player in ("jordan", "erin"):
            for category in CATEGORIES:
                writer.writerow([game_seq, player, category, game[player][category]])

    with open(RAW_TOTALS_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        for player in ("jordan", "erin"):
            writer.writerow([game_seq, player, game[player]["recorded_total"]])


def main():
    parser = argparse.ArgumentParser()
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--image", type=Path, help="a single scorecard photo")
    src.add_argument("--dir", type=Path, help="a directory of scorecard photos")
    args = parser.parse_args()

    images = sorted(args.dir.glob("scorecard_games_*")) if args.dir else [args.image]
    if not images:
        print(f"No files matching 'scorecard_games_*' found in {args.dir}")
        sys.exit(1)

    any_failures = False
    for image_path in images:
        try:
            clean_games, problems, start, end = process_image(image_path)
        except ValueError as e:
            print(f"  SKIPPED {image_path.name}: {e}")
            any_failures = True
            continue

        if problems:
            review_path = image_path.with_suffix(".review.json")
            review_path.write_text(json.dumps({"problems": problems}, indent=2))
            print(f"  NOT written — {image_path.name} has issues, see {review_path.name}:")
            for p in problems:
                print(f"    - {p}")
            any_failures = True
            continue

        for i, game in enumerate(clean_games):
            write_to_seeds(start + i, game)
        print(f"  Wrote games {start}-{end} from {image_path.name} — all totals checked out clean.")

    if any_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
