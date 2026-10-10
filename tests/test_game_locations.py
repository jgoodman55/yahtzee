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
    assert max(game_seqs) == 123
    # Games through the first new sheet have no written location.
    assert not any(seq <= 111 for seq in by_seq)


def test_img_2923_queens_arms_and_munkbron():
    by_seq = {int(row["game_seq"]): row for row in _rows(LOCATIONS)}
    assert by_seq[115]["pub_name"] == "The Queen's Arms"
    assert by_seq[115]["sheet_label"] == "Queen's Arms - 2"
    assert by_seq[116]["pub_name"] == "The Queen's Arms"
    assert by_seq[116]["sheet_label"] == "Queen's Arms - 2"
    assert by_seq[117]["pub_name"] == "Munkbron"
    assert by_seq[117]["sheet_label"] == "Sweden - Munkbron - 1"
    pubs = {row["pub_name"]: row for row in _rows(PUBS)}
    munkbron = pubs["Munkbron"]
    assert munkbron["merchant_name_raw"] == "MUNKBRON STOCKHOLM"
    assert munkbron["lat"] == "59.3244808"
    assert munkbron["lng"] == "18.0674809"
    assert "Munkbron Bryggeri & Ölhall" in munkbron["note"]
    assert "Lilla Nygatan" in munkbron["note"]
    assert "Stockholm" in munkbron["note"]
    assert munkbron["photo_url"] == "pub_map/photos/munkbron.jpg"
    assert munkbron["photo_attribution"] == "Jordan"


def test_img_2924_munkbron_and_atlas():
    by_seq = {int(row["game_seq"]): row for row in _rows(LOCATIONS)}
    assert by_seq[118]["pub_name"] == "Munkbron"
    assert by_seq[118]["sheet_label"] == "Munkbron - 2"
    assert by_seq[119]["pub_name"] == "Munkbron"
    assert by_seq[119]["sheet_label"] == "Munkbron - 2"
    assert by_seq[120]["pub_name"] == "The Atlas"
    assert by_seq[120]["sheet_label"] == "Atlas - 1"
    atlas = {row["pub_name"]: row for row in _rows(PUBS)}["The Atlas"]
    assert atlas["merchant_name_raw"] == "THE ATLAS FULHAM"
    assert atlas["lat"] == "51.4862159"
    assert atlas["lng"] == "-0.1961560"
    assert "16 Seagrave Road" in atlas["note"]
    assert "Fulham" in atlas["note"]
    assert "SW6 1RX" in atlas["note"]
    assert "Logged from a scorecard header, not a Chase visit" in atlas["note"]
    assert atlas["photo_url"] == "pub_map/photos/the_atlas.jpg"
    assert "Steve Daniels" in atlas["photo_attribution"]
    assert "CC BY-SA 2.0" in atlas["photo_attribution"]


def test_img_2925_atlas_three_games():
    by_seq = {int(row["game_seq"]): row for row in _rows(LOCATIONS)}
    for seq in (121, 122, 123):
        assert by_seq[seq]["pub_name"] == "The Atlas"
        assert by_seq[seq]["sheet_label"] == "Atlas - 3"
    pubs = {row["pub_name"] for row in _rows(PUBS)}
    assert sum(1 for row in _rows(PUBS) if row["pub_name"] == "The Atlas") == 1
    assert "The Atlas" in pubs
