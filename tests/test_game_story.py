"""What decided each game, from the boxes alone.

    python tests/test_game_story.py
    pytest tests/test_game_story.py
"""

from __future__ import annotations

import csv
import importlib.util
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "assets" / "python" / "build_game_story.py"
GAMES = REPO / "assets" / "seeds" / "raw_games.csv"
GAMES_JS = REPO / "dashboard" / "scorecards" / "games.js"

FORBIDDEN = re.compile(
    r"\b(chase|pipeline|seed|merchant|scratch|3oak|4oak|jargon|bank)\b",
    re.IGNORECASE,
)


def _load():
    spec = importlib.util.spec_from_file_location("build_game_story", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]


def _scores() -> dict[int, dict[str, dict[str, int]]]:
    out: dict[int, dict[str, dict[str, int]]] = {}
    with GAMES.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            seq = int(row["game_seq"])
            player = row["player"].strip().lower()
            slot = out.setdefault(seq, {"erin": {}, "jordan": {}})
            slot[player][row["category"].strip().lower()] = int(row["score"])
    return out


def _zeros(**overrides: int) -> dict[str, int]:
    scores = {key: 0 for key in _load()._BOXES}
    scores.update(overrides)
    return scores


def _assert_plain(story: str) -> None:
    assert story.strip()
    assert 1 <= len(_sentences(story)) <= 2
    assert FORBIDDEN.search(story) is None
    assert re.search(r"\b(erin|jordan)\b", story) is None
    assert re.search(r"yahtzee", story) is None
    assert "  " not in story


def test_yahtzee_loses_to_straights():
    story = _load().game_story(
        _zeros(
            ones=3,
            twos=6,
            threes=9,
            fours=12,
            fives=15,
            sixes=18,
            upper_bonus=35,
            three_of_a_kind=15,
            chance=20,
            yahtzee=50,
        ),
        _zeros(
            ones=2,
            twos=4,
            threes=6,
            fours=8,
            fives=10,
            sixes=12,
            three_of_a_kind=21,
            four_of_a_kind=24,
            full_house=25,
            small_straight=30,
            large_straight=40,
            chance=18,
        ),
    )
    assert story == (
        "Erin rolled a Yahtzee (+50) but missed large straight, small straight "
        "and full house, while Jordan's large straight (+40), small straight (+30) "
        "and full house (+25) outweighed it."
    )
    _assert_plain(story)


def test_identical_tie():
    scores = _zeros(yahtzee=50, large_straight=40, chance=20)
    story = _load().game_story(scores, dict(scores))
    assert story == "They finished level, box for box."
    _assert_plain(story)


def test_tie_names_the_widest_split():
    story = _load().game_story(
        _zeros(yahtzee=50, chance=10),
        _zeros(large_straight=40, chance=20),
    )
    assert story == (
        "They finished level. The widest split was Erin's Yahtzee (+50) "
        "against Jordan's large straight (+40)."
    )
    _assert_plain(story)


def test_blowout_says_never_close():
    story = _load().game_story(
        _zeros(chance=10),
        _zeros(
            ones=4,
            twos=8,
            threes=12,
            fours=16,
            fives=20,
            sixes=24,
            upper_bonus=35,
            three_of_a_kind=20,
            four_of_a_kind=24,
            full_house=25,
            small_straight=30,
            large_straight=40,
            chance=15,
            yahtzee=50,
        ),
    )
    assert story.startswith("Never close: ")
    assert "Jordan's Yahtzee (+50)" in story
    assert "large straight (+40)" in story
    assert "Erin missed" in story
    assert story.count(".") == 2
    _assert_plain(story)


def test_story_is_deterministic():
    module = _load()
    erin = _zeros(yahtzee=50, chance=22, sixes=18)
    jordan = _zeros(large_straight=40, full_house=25, chance=18, sixes=24)
    assert module.game_story(erin, jordan) == module.game_story(dict(erin), dict(jordan))


def test_kinds_merge_when_both_are_swings():
    story = _load().game_story(
        _zeros(yahtzee=50, chance=18),
        _zeros(three_of_a_kind=21, four_of_a_kind=26, chance=20, sixes=18),
    )
    assert "big three and four of a kind (+47)" in story
    assert "outweighed it" in story
    _assert_plain(story)


def test_every_real_game_has_a_short_story():
    module = _load()
    scores = _scores()
    assert set(scores) == set(range(1, 130))
    for seq, players in scores.items():
        first = module.game_story(players["erin"], players["jordan"])
        second = module.game_story(players["erin"], players["jordan"])
        assert first == second, seq
        _assert_plain(first)


def test_story_sits_beside_commentary_and_on_the_viewer():
    mart = (REPO / "assets" / "marts" / "mart_head_to_head.sql").read_text()
    assert "int_game_story" in mart
    assert "s.story" in mart
    dashboard = (REPO / "dashboard" / "yahtzee.yml").read_text()
    assert "h.story" in dashboard
    assert "What decided it" in dashboard
    viewer = (REPO / "dashboard" / "scorecards" / "viewer.html").read_text()
    assert 'id="story"' in viewer
    assert "game.story" in viewer
    assert 'id="replay"' in viewer
    assert "replay.js" in viewer
    assert "Seed-rendered" not in viewer
    css = (REPO / "dashboard" / "scorecards" / "scorecards.css").read_text()
    assert ".story" in css
    assert "prefers-reduced-motion" in css
    script = (REPO / "dashboard" / "pub_map" / "newtab.js").read_text()
    assert 'indexOf("DECIDED")' in script
    assert "Watch replay" in script
    export = (REPO / "dashboard" / "scripts" / "export_scorecards.py").read_text()
    assert "game_story" in export
    assert "story_focus" in export
    replay = (REPO / "dashboard" / "scorecards" / "replay.js").read_text()
    assert "buildTimeline" in replay
    assert "prefers-reduced-motion" in replay
    assert "function mount" in replay


def test_replay_timeline_matches_game_128():
    subprocess.check_call(["node", str(REPO / "tests" / "test_replay_timeline.js")])


def test_story_focus_names_the_boxes_in_the_sentence():
    module = _load()
    focus = module.story_focus(
        _zeros(
            ones=3,
            twos=6,
            threes=9,
            fours=12,
            fives=15,
            sixes=18,
            upper_bonus=35,
            three_of_a_kind=15,
            chance=20,
            yahtzee=50,
        ),
        _zeros(
            ones=2,
            twos=4,
            threes=6,
            fours=8,
            fives=10,
            sixes=12,
            three_of_a_kind=21,
            four_of_a_kind=24,
            full_house=25,
            small_straight=30,
            large_straight=40,
            chance=18,
        ),
    )
    assert focus == ["full_house", "small_straight", "large_straight", "yahtzee"]


def test_game_128_focus_is_yahtzee_against_the_straight():
    module = _load()
    players = _scores()[128]
    focus = module.story_focus(players["erin"], players["jordan"])
    assert focus == ["upper_bonus", "four_of_a_kind", "large_straight", "yahtzee"]
    story = module.game_story(players["erin"], players["jordan"])
    assert "Yahtzee" in story
    assert "large straight" in story
    assert "upper bonus" in story


def test_identical_tie_has_no_focus_boxes():
    module = _load()
    scores = _zeros(yahtzee=50, large_straight=40, chance=20)
    assert module.story_focus(scores, dict(scores)) == []


def test_games_js_embeds_the_same_story():
    module = _load()
    text = GAMES_JS.read_text(encoding="utf-8")
    payload = json.loads(text.split("=", 1)[1].rstrip().rstrip(";"))
    scores = _scores()
    game = next(row for row in payload["games"] if row["game_seq"] == 129)
    assert game["story"] == module.game_story(scores[129]["erin"], scores[129]["jordan"])
    assert all(row.get("story") for row in payload["games"])
    game_128 = next(row for row in payload["games"] if row["game_seq"] == 128)
    assert game_128["focus"] == module.story_focus(scores[128]["erin"], scores[128]["jordan"])
