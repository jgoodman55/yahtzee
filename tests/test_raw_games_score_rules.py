"""Score-rule audit for assets/seeds/raw_games.csv.

Mirrors assets/audit/raw_games_score_rules.sql so leftover OCR/typos can
be listed without a DuckDB run. `bruin run --workers 1` fails on
violations that are not in known_score_rule_violations.csv. Failures are
Jordan's review queue — not a prompt to re-read every sheet.

    python tests/test_raw_games_score_rules.py
    pytest tests/test_raw_games_score_rules.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW_GAMES = REPO / "assets" / "seeds" / "raw_games.csv"
KNOWN = REPO / "assets" / "seeds" / "known_score_rule_violations.csv"

FACE = {
    "ones": (1, 5),
    "twos": (2, 10),
    "threes": (3, 15),
    "fours": (4, 20),
    "fives": (5, 25),
    "sixes": (6, 30),
}
FIXED = {
    "full_house": (frozenset({0, 25}), "full_house must be 0 or 25"),
    "small_straight": (frozenset({0, 30}), "small_straight must be 0 or 30"),
    "large_straight": (frozenset({0, 40}), "large_straight must be 0 or 40"),
    "yahtzee": (frozenset({0, 50}), "yahtzee must be 0 or 50"),
    "upper_bonus": (frozenset({0, 35}), "upper_bonus must be 0 or 35"),
}


def _row_key(game_seq: int, player: str, category: str, score: int, rule: str):
    return (game_seq, player, category, score, rule)


def scan_violations(path: Path = RAW_GAMES) -> list[tuple]:
    found = []
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            game_seq = int(r["game_seq"])
            player = r["player"].strip().lower()
            category = r["category"].strip().lower()
            score = int(r["score"])
            if category in FIXED:
                allowed, rule = FIXED[category]
                if score not in allowed:
                    found.append(_row_key(game_seq, player, category, score, rule))
            elif category == "chance" and score == 0:
                found.append(
                    _row_key(game_seq, player, category, score, "chance must never be 0")
                )
            elif category in FACE:
                face, hi = FACE[category]
                if score % face != 0 or score < 0 or score > hi:
                    found.append(
                        _row_key(
                            game_seq,
                            player,
                            category,
                            score,
                            f"{category} must be a multiple of {face} in 0..{hi}",
                        )
                    )
    return found


def load_known(path: Path = KNOWN) -> set[tuple]:
    with path.open(newline="") as f:
        return {
            _row_key(
                int(r["game_seq"]),
                r["player"].strip().lower(),
                r["category"].strip().lower(),
                int(r["score"]),
                r["rule"],
            )
            for r in csv.DictReader(f)
        }


def format_rows(rows: list[tuple] | set[tuple]) -> str:
    """CSV dump (header + rows) for the same five review-queue fields."""
    lines = ["game_seq,player,category,score,rule"]
    for game_seq, player, category, score, rule in sorted(rows):
        lines.append(f"{game_seq},{player},{category},{score},{rule}")
    return "\n".join(lines)


def format_review_queue(rows: list[tuple] | set[tuple], *, heading: str) -> str:
    """Jordan review queue: one labeled (game_seq, player, category, score, rule)."""
    lines = [heading]
    if not rows:
        lines.append("  (none)")
        return "\n".join(lines)
    for game_seq, player, category, score, rule in sorted(rows):
        lines.append(
            f"  (game_seq={game_seq}, player={player}, category={category}, "
            f"score={score}, rule={rule})"
        )
    return "\n".join(lines)


def test_review_queue_message_lists_tuple_fields():
    text = format_review_queue(
        [(12, "erin", "full_house", 20, "full_house must be 0 or 25")],
        heading="Jordan review queue — check these boxes on the photo:",
    )
    assert "(game_seq=12, player=erin, category=full_house, score=20, rule=full_house must be 0 or 25)" in text


def test_no_new_score_rule_violations():
    found = set(scan_violations())
    known = load_known()
    unexpected = found - known
    missing = known - found
    assert not unexpected, format_review_queue(
        unexpected,
        heading=(
            "Jordan review queue — new impossible boxes "
            "(not in known_score_rule_violations.csv):"
        ),
    )
    assert not missing, format_review_queue(
        missing,
        heading=(
            "Documented leftovers no longer violate — delete them from "
            "known_score_rule_violations.csv:"
        ),
    )


def main() -> int:
    found = scan_violations()
    known = load_known()
    unexpected = set(found) - known
    missing = known - set(found)
    print(f"{len(found)} score-rule violation(s) in {RAW_GAMES.relative_to(REPO)}")
    print(format_rows(found))
    if unexpected:
        print()
        print(
            format_review_queue(
                unexpected,
                heading=(
                    "Jordan review queue — NEW impossible boxes "
                    "(not in known_score_rule_violations.csv):"
                ),
            )
        )
    if missing:
        print()
        print(
            format_review_queue(
                missing,
                heading="STALE known rows (no longer violate):",
            )
        )
    if unexpected or missing:
        return 1
    if found:
        print(
            f"\nAll {len(found)} leftover(s) match known_score_rule_violations.csv."
        )
    else:
        print("\nNo score-rule leftovers. violation_count = 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
