"""Commentary seed + one-comment checks.

The Game tab reads one `comment` from `mart_head_to_head`.
`int_commentary` samples `seed_commentary` with an RNG seeded by
`game_seq`, then keeps the most savage applicable type. `big_margin`
only when margin >= 60.

    python tests/test_commentary.py
    pytest tests/test_commentary.py
"""

from __future__ import annotations

import csv
import importlib.util
import random
import sys
from collections import defaultdict
from pathlib import Path
from types import ModuleType

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "assets" / "seeds" / "seed_commentary.csv"
GAMES = REPO / "assets" / "seeds" / "raw_games.csv"
BUILD_COMMENTARY = REPO / "assets" / "python" / "build_commentary.py"

CANDY = "like taking candy from a stupid baby"
KEPT_BIG_MARGIN = (
    "absolute domination, not even close",
    "one-sided. someone brought their A-game",
    "the scoreboard is basically a mercy rule at this point",
)


def load_phrases() -> dict[str, list[str]]:
    by_cat: dict[str, list[str]] = defaultdict(list)
    with SEED.open(newline="") as f:
        for row in csv.DictReader(f):
            by_cat[row["category"]].append(row["phrase"])
    return dict(by_cat)


def test_candy_and_kept_big_margin_phrases():
    phrases = load_phrases()
    big = phrases["big_margin"]
    assert CANDY in big
    for kept in KEPT_BIG_MARGIN:
        assert kept in big
    assert len(big) >= 8


def _load_build_commentary():
    bruin = ModuleType("bruin")
    bruin.query = lambda *a, **k: None
    sys.modules.setdefault("bruin", bruin)
    spec = importlib.util.spec_from_file_location("build_commentary", BUILD_COMMENTARY)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _phrase_category(comment: str, phrases: dict[str, list[str]]) -> str:
    body = comment
    for prefix in ("jordan: ", "erin: "):
        if body.startswith(prefix):
            body = body.removeprefix(prefix)
            break
    hits = [cat for cat, options in phrases.items() if body in options]
    assert len(hits) == 1, (comment, hits)
    return hits[0]


def _applicable_kinds(win_loss: dict, jordan: dict, erin: dict) -> list[str]:
    kinds = []
    margin = win_loss["margin"]
    winner = win_loss["winner"]
    if winner == "tie":
        kinds.append("tie")
    elif margin >= 60:
        kinds.append("big_margin")
    elif margin <= 5:
        kinds.append("narrow_margin")
    if win_loss["running_same_winner_count"] >= 3:
        kinds.append("streak")
    yahtzees_j = jordan.get("total_yahtzees", 0)
    yahtzees_e = erin.get("total_yahtzees", 0)
    if yahtzees_j >= 2 or yahtzees_e >= 2:
        kinds.append("multi_yahtzee")
    elif yahtzees_j == 0 and yahtzees_e == 0:
        kinds.append("zero_yahtzee")
    bonus_j = bool(jordan.get("upper_bonus_hit", False))
    bonus_e = bool(erin.get("upper_bonus_hit", False))
    if not bonus_j and not bonus_e:
        kinds.append("no_bonus_either")
    elif bonus_j != bonus_e:
        kinds.append("bonus_split")
    kinds.append("ordinary")
    return kinds


def _best_kind(kinds: list[str], rank: tuple[str, ...]) -> str:
    order = {kind: i for i, kind in enumerate(rank)}
    return min(kinds, key=lambda kind: order[kind])


def _facts(seq: int, jordan: dict, erin: dict) -> dict:
    return {(seq, "jordan"): jordan, (seq, "erin"): erin}


def test_blowout_beats_showoff_bonus_and_streak():
    mod = _load_build_commentary()
    phrases = load_phrases()
    win_loss = {"margin": 198, "winner": "jordan", "running_same_winner_count": 5}
    facts = _facts(
        118,
        {"total_yahtzees": 2, "upper_bonus_hit": True},
        {"total_yahtzees": 0, "upper_bonus_hit": False},
    )
    row = mod.build_row(118, win_loss, facts, phrases)
    assert _phrase_category(row["comment"], phrases) == "big_margin"
    assert row["comment"].startswith("jordan: ")
    assert " · " not in row["comment"]


def test_missed_bonus_beats_a_hot_streak():
    mod = _load_build_commentary()
    phrases = load_phrases()
    win_loss = {"margin": 11, "winner": "erin", "running_same_winner_count": 4}
    facts = _facts(
        120,
        {"total_yahtzees": 1, "upper_bonus_hit": False},
        {"total_yahtzees": 0, "upper_bonus_hit": False},
    )
    row = mod.build_row(120, win_loss, facts, phrases)
    assert _phrase_category(row["comment"], phrases) == "no_bonus_either"
    assert not row["comment"].startswith("erin: ")


def test_quiet_game_uses_the_ordinary_line():
    mod = _load_build_commentary()
    phrases = load_phrases()
    win_loss = {"margin": 20, "winner": "erin", "running_same_winner_count": 0}
    facts = _facts(
        4,
        {"total_yahtzees": 1, "upper_bonus_hit": True},
        {"total_yahtzees": 1, "upper_bonus_hit": True},
    )
    row = mod.build_row(4, win_loss, facts, phrases)
    assert _phrase_category(row["comment"], phrases) == "ordinary"


def test_rank_list_beats_insertion_order():
    mod = _load_build_commentary()
    chosen = mod.savage_comment(
        [
            ("streak", "erin: on a genuine heater right now"),
            ("no_bonus_either", "nobody hit the upper bonus — the 1s and 2s strategy is not working"),
        ]
    )
    assert chosen.startswith("nobody hit the upper bonus")
    assert mod.SAVAGERY_RANK[0] == "big_margin"
    assert mod.SAVAGERY_RANK.index("no_bonus_either") < mod.SAVAGERY_RANK.index("streak")
    assert mod.SAVAGERY_RANK[-1] == "ordinary"


def _seed_games() -> list[tuple[int, dict, dict, dict]]:
    boxes: dict[int, dict[str, dict[str, int]]] = defaultdict(dict)
    with GAMES.open(newline="") as handle:
        for row in csv.DictReader(handle):
            boxes[int(row["game_seq"])].setdefault(row["player"], {})[row["category"]] = int(row["score"])

    def total(seq: int, player: str) -> int:
        return sum(boxes[seq][player].values())

    def yahtzees(seq: int, player: str) -> int:
        natural = 1 if boxes[seq][player].get("yahtzee", 0) > 0 else 0
        bonus = boxes[seq][player].get("yahtzee_bonus", 0) // 100
        return natural + bonus

    situations = []
    running = 0
    previous = None
    for seq in sorted(boxes):
        jordan_total = total(seq, "jordan")
        erin_total = total(seq, "erin")
        if jordan_total > erin_total:
            winner = "jordan"
        elif erin_total > jordan_total:
            winner = "erin"
        else:
            winner = "tie"
        if previous is not None and winner == previous:
            running += 1
        previous = winner
        win_loss = {
            "margin": abs(jordan_total - erin_total),
            "winner": winner,
            "running_same_winner_count": running,
        }
        jordan = {
            "total_yahtzees": yahtzees(seq, "jordan"),
            "upper_bonus_hit": boxes[seq]["jordan"].get("upper_bonus", 0) > 0,
        }
        erin = {
            "total_yahtzees": yahtzees(seq, "erin"),
            "upper_bonus_hit": boxes[seq]["erin"].get("upper_bonus", 0) > 0,
        }
        situations.append((seq, win_loss, jordan, erin))
    return situations


def test_every_game_has_one_deterministic_comment():
    mod = _load_build_commentary()
    phrases = load_phrases()
    situations = _seed_games()
    assert len(situations) == 123
    for seq, win_loss, jordan, erin in situations:
        facts = _facts(seq, jordan, erin)
        first = mod.build_row(seq, win_loss, facts, phrases)
        second = mod.build_row(seq, win_loss, facts, phrases)
        assert first == second
        assert list(first) == ["game_seq", "comment"]
        comment = first["comment"]
        assert isinstance(comment, str) and comment.strip()
        assert " · " not in comment
        kind = _phrase_category(comment, phrases)
        assert kind == _best_kind(_applicable_kinds(win_loss, jordan, erin), mod.SAVAGERY_RANK)


def test_pick_is_deterministic_per_game_seq():
    phrases = load_phrases()
    options = phrases["big_margin"]
    a = random.Random("42").choice(options)
    b = random.Random("42").choice(options)
    assert a == b


if __name__ == "__main__":
    test_candy_and_kept_big_margin_phrases()
    test_blowout_beats_showoff_bonus_and_streak()
    test_missed_bonus_beats_a_hot_streak()
    test_quiet_game_uses_the_ordinary_line()
    test_rank_list_beats_insertion_order()
    test_every_game_has_one_deterministic_comment()
    test_pick_is_deterministic_per_game_seq()
    print("test_commentary: ok")
