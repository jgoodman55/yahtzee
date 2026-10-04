"""High and low scores are per-player extremes of recorded_total.

High score is max(recorded_total) for that player. Low score is
min(recorded_total), the same single-player grain. When several games share
the extreme, the scorecard game is the earliest game_seq — the same secondary
key as the closest-game and blowout lists.

    python tests/test_score_extremes.py
    pytest tests/test_score_extremes.py
"""

from __future__ import annotations

import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW_GAMES = REPO / "assets" / "seeds" / "raw_games.csv"
PLAYER_KPIS = REPO / "assets" / "marts" / "mart_player_kpis.sql"
DASHBOARD = REPO / "dashboard" / "yahtzee.yml"

# Current seed. A new card that sets a record updates these on purpose.
EXPECTED = {
    "erin": {"high": (106, 505), "low": (29, 125)},
    "jordan": {"high": (100, 509), "low": (49, 135)},
}


def extremes(rows: list[tuple[str, int, int]]) -> dict[str, dict[str, tuple[int, int]]]:
    """Return {player: {high: (game_seq, total), low: (game_seq, total)}}.

    Tie-break is earliest game_seq, matching score_ranks in mart_player_kpis.
    """
    by_player: dict[str, list[tuple[int, int]]] = {}
    for player, game_seq, total in rows:
        by_player.setdefault(player, []).append((game_seq, total))

    out: dict[str, dict[str, tuple[int, int]]] = {}
    for player, games in by_player.items():
        high_total = max(total for _, total in games)
        low_total = min(total for _, total in games)
        high_game = min(game_seq for game_seq, total in games if total == high_total)
        low_game = min(game_seq for game_seq, total in games if total == low_total)
        out[player] = {
            "high": (high_game, high_total),
            "low": (low_game, low_total),
        }
    return out


def seed_player_games() -> list[tuple[str, int, int]]:
    """One recorded_total per (player, game_seq). The seed repeats it on every box."""
    seen: dict[tuple[str, int], int] = {}
    with RAW_GAMES.open(newline="") as f:
        for row in csv.DictReader(f):
            key = (row["player"].strip().lower(), int(row["game_seq"]))
            total = int(row["recorded_total"])
            previous = seen.get(key)
            if previous is not None and previous != total:
                raise AssertionError(f"recorded_total disagrees inside {key}: {previous} vs {total}")
            seen[key] = total
    return [(player, game_seq, total) for (player, game_seq), total in seen.items()]


def test_tie_break_picks_earliest_game_seq():
    picked = extremes(
        [
            ("erin", 2, 100),
            ("erin", 1, 100),
            ("erin", 4, 50),
            ("erin", 3, 50),
            ("jordan", 9, 80),
            ("jordan", 8, 70),
        ]
    )
    assert picked["erin"]["high"] == (1, 100)
    assert picked["erin"]["low"] == (3, 50)
    assert picked["jordan"]["high"] == (9, 80)
    assert picked["jordan"]["low"] == (8, 70)


def test_seed_extremes_match_recorded_total():
    picked = extremes(seed_player_games())
    assert picked == EXPECTED
    # Lowest single-player total in the seed, same definition as the Overview widget.
    lowest = min(
        (total, player, game_seq)
        for player, sides in picked.items()
        for game_seq, total in [sides["low"]]
    )
    assert lowest == (125, "erin", 29)


def test_mart_ranks_high_and_low_the_same_way():
    sql = PLAYER_KPIS.read_text()
    assert "order by recorded_total desc, game_seq asc" in sql
    assert "order by recorded_total asc, game_seq asc" in sql
    assert "as low_score" in sql
    assert "as high_score" in sql


def test_overview_places_low_score_beside_high_score():
    """High and low sit in one Top-tab row, each tile showing both players."""
    dashboard = DASHBOARD.read_text()
    high = dashboard.index("name: High score")
    low = dashboard.index("name: Low score")
    assert high < low
    between = dashboard[high:low]
    assert "\n  - tab:" not in between
    for field in (
        "erin_high_score",
        "jordan_high_score",
        "erin_low_score",
        "jordan_low_score",
        "erin_high_score_url",
        "jordan_high_score_url",
        "erin_low_score_url",
        "jordan_low_score_url",
    ):
        assert f"field: {field}" in dashboard
    assert "target: _blank" in dashboard


def test_top_tab_shows_streak_from_headline():
    """Current run and longest run sit on Top. Score keeps its race companion.

    Numbers come from mart_headline_kpis (already on the headline query).
    No extra mart. The row height stays a quoted string so phone cards
    do not collapse.
    """
    dashboard = DASHBOARD.read_text()
    top, rest = dashboard.split("  - tab: Score\n", 1)
    assert "name: Streak\n" in top
    assert top.index("name: Streak") < top.index("name: Wins")
    streak = top[top.index("name: Streak"): top.index("name: Wins")]
    assert "col: 3" in streak
    assert "query: headline" in streak
    for field in (
        "erin_current_streak",
        "jordan_current_streak",
        "erin_longest_streak",
        "jordan_longest_streak",
    ):
        assert f"field: {field}" in streak or f"datum.{field}" in streak
    row = top[top.rindex("  - tab: Top\n", 0, top.index("name: Streak")): top.index("name: Streak")]
    assert 'height: "188"' in row
    assert "height: 188\n" not in row
    score = rest.split("  - tab: Roll\n", 1)[0]
    assert "name: Streaks" in score


def _jpeg_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    i = 2
    while i < len(data) - 9:
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            height = int.from_bytes(data[i + 5 : i + 7], "big")
            width = int.from_bytes(data[i + 7 : i + 9], "big")
            return width, height
        if marker == 0xD8 or marker == 0x01 or 0xD0 <= marker <= 0xD9:
            i += 2
            continue
        length = int.from_bytes(data[i + 2 : i + 4], "big")
        i += 2 + length
    raise AssertionError(f"no JPEG size in {path}")


def test_top_tab_links_the_pub_map():
    """A preview of the borough map sits above the streak row.

    The picture links to the map page. Scorecard links stay on the Game
    tab. The Pub tab keeps its own map link. No fixed row height, so the
    banner is not clipped and a numeric height cannot crush the card.
    """
    dashboard = DASHBOARD.read_text()
    assert "name: Yahtzee Head-to-Head\n" in dashboard[:200]
    top, rest = dashboard.split("  - tab: Score\n", 1)
    landing = top[top.index("name: Pub map"): top.index("name: Streak")]
    assert "See where we've played" not in landing
    assert "Open the scorecards" not in landing
    assert "[![Pub map](/pub_map/preview.svg)](/pub_map.html)" in landing
    assert "scorecards" not in landing.lower()
    assert "col: 12" in landing[:250]
    row = top[top.rindex("  - tab: Top\n", 0, top.index("name: Pub map")): top.index("name: Pub map")]
    assert "height:" not in row
    pub_map = Path(__file__).resolve().parents[1] / "dashboard" / "pub_map"
    preview = pub_map / "preview.jpg"
    assert preview.is_file()
    assert preview.stat().st_size < 200_000
    width, height = _jpeg_size(preview)
    aspect = width / height
    assert 2.3 <= aspect <= 3.0, aspect
    svg = (pub_map / "preview.svg").read_text()
    assert "Pub map" in svg
    assert "chip-phone" in svg
    assert svg.count("data:image/jpeg;base64,") == 1
    game = rest.split("  - tab: Game\n", 1)[1].split("  - tab: Pub\n", 1)[0]
    assert "[browse every scorecard](/scorecards/index.html)" in game
    pub = rest.split("  - tab: Pub\n", 1)[1]
    assert "[Open the map](/pub_map.html)" in pub


if __name__ == "__main__":
    test_tie_break_picks_earliest_game_seq()
    test_seed_extremes_match_recorded_total()
    test_mart_ranks_high_and_low_the_same_way()
    test_overview_places_low_score_beside_high_score()
    test_top_tab_shows_streak_from_headline()
    test_top_tab_links_the_pub_map()
    print("test_score_extremes: ok")
