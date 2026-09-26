"""Sheet locations join seed_pubs on the canonical pub name.

    python tests/test_game_locations.py
    pytest tests/test_game_locations.py
"""

from __future__ import annotations

import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOCATIONS = REPO / "assets" / "seeds" / "seed_game_locations.csv"
PUBS = REPO / "assets" / "seeds" / "seed_pubs.csv"
GAMES = REPO / "assets" / "seeds" / "raw_games.csv"


def _rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_logged_pubs_use_canonical_seed_names():
    pubs = {row["pub_name"] for row in _rows(PUBS)}
    locations = _rows(LOCATIONS)
    assert locations
    for row in locations:
        assert row["pub_name"] in pubs, row
        assert row["sheet_label"]


def test_img_2922_locations_and_blank_earlier_games():
    by_seq = {int(row["game_seq"]): row for row in _rows(LOCATIONS)}
    assert by_seq[112]["pub_name"] == "The Butcher's Hook"
    assert by_seq[113]["pub_name"] == "The Queen's Arms"
    assert by_seq[114]["pub_name"] == "The Queen's Arms"
    assert "Pimlico" not in by_seq[113]["pub_name"]
    game_seqs = {int(row["game_seq"]) for row in _rows(GAMES)}
    assert max(game_seqs) == 114
    # Games through the first new sheet have no written location.
    assert not any(seq <= 111 for seq in by_seq)
