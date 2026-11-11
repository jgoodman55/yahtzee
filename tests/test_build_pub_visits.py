"""Scoresheet days union with Chase days and do not double-count.

    python tests/test_build_pub_visits.py
    pytest tests/test_build_pub_visits.py
"""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "assets" / "python" / "build_pub_visits.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_pub_visits", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_anchor_scoresheet_day_unions_and_does_not_double():
    mod = _load()
    played = {date(2026, 10, 11), date(2026, 10, 31)}
    assert mod.SCORESHEET_DATED_DAYS["ANCHOR BANKSIDE"] == played
    assert "ANCHOR BANKSIDE" not in mod.SCORESHEET_ONE_VISIT
    chase = {date(2026, 7, 1), date(2026, 8, 9)}
    assert played.isdisjoint(chase)
    combined = mod.combined_days("ANCHOR BANKSIDE", chase)
    assert combined == chase | played
    assert mod.visit_row_count("ANCHOR BANKSIDE", combined) == 4
    already = chase | played
    assert mod.combined_days("ANCHOR BANKSIDE", already) == already
    assert mod.visit_row_count("ANCHOR BANKSIDE", already) == 4


def test_three_johns_scoresheet_day_unions_and_does_not_double():
    mod = _load()
    played = {date(2026, 10, 31), mod.SHEET_2929_DATE}
    assert mod.SCORESHEET_DATED_DAYS["THREE JOHNS"] == played
    assert "THREE JOHNS" not in mod.SCORESHEET_ONE_VISIT
    chase = {date(2026, 8, 1)}
    combined = mod.combined_days("THREE JOHNS", chase)
    assert combined == chase | played
    assert mod.visit_row_count("THREE JOHNS", combined) == 3
    already = chase | played
    assert mod.combined_days("THREE JOHNS", already) == already
    assert mod.visit_row_count("THREE JOHNS", already) == 3


def test_img_2929_placeholder_date_is_one_day_for_both_venues():
    mod = _load()
    assert mod.SHEET_2929_DATE == date(2026, 11, 11)
    assert mod.SCORESHEET_DATED_DAYS["SAN SEBASTIAN"] == {mod.SHEET_2929_DATE}
    assert mod.SHEET_2929_DATE in mod.SCORESHEET_DATED_DAYS["THREE JOHNS"]
    assert mod.visit_row_count(
        "SAN SEBASTIAN", mod.combined_days("SAN SEBASTIAN", set())
    ) == 1
    already = {mod.SHEET_2929_DATE}
    assert mod.combined_days("SAN SEBASTIAN", already) == already
    assert mod.visit_row_count("SAN SEBASTIAN", already) == 1


def test_scoresheet_only_venues_stay_one_row_when_chase_is_empty():
    mod = _load()
    for merchant in (
        "BUTCHERS HOOK",
        "QUEENS ARMS PIMLICO",
        "MUNKBRON STOCKHOLM",
        "THE ATLAS FULHAM",
        "LEICESTER ARMS SOHO",
    ):
        assert merchant in mod.SCORESHEET_ONE_VISIT
        assert merchant not in mod.SCORESHEET_DATED_DAYS
        assert mod.combined_days(merchant, set()) == set()
