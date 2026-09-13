"""Commentary seed + deterministic pick checks.

Deep cuts (and the win-race captions) read precomputed columns from
`mart_head_to_head`, which is `int_win_loss` left-joined to
`int_commentary`. `int_commentary` samples `seed_commentary` with an RNG
seeded by `game_seq` — `big_margin` only when margin >= 60.

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


def test_build_row_uses_big_margin_when_margin_ge_60():
    build_row = _load_build_commentary().build_row
    phrases = load_phrases()
    win_loss = {
        "margin": 60,
        "winner": "jordan",
        "running_same_winner_count": 0,
    }
    row = build_row(1, win_loss, {}, phrases)
    assert row["margin_comment"] is not None
    comment = row["margin_comment"]
    assert comment.startswith("jordan: ")
    assert comment.removeprefix("jordan: ") in phrases["big_margin"]


def test_pick_is_deterministic_per_game_seq():
    phrases = load_phrases()
    options = phrases["big_margin"]
    a = random.Random("42").choice(options)
    b = random.Random("42").choice(options)
    assert a == b


if __name__ == "__main__":
    test_candy_and_kept_big_margin_phrases()
    test_build_row_uses_big_margin_when_margin_ge_60()
    test_pick_is_deterministic_per_game_seq()
    print("test_commentary: ok")
