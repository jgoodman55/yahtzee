"""Grounding checks for Strategy marts (n=120 seed, 0 ties).

Run after `bruin run --workers 1`:

    python tests/test_strategy_marts.py
    pytest tests/test_strategy_marts.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "yahtzee.duckdb"


def _connect():
    import duckdb

    if not DB.exists():
        raise SystemExit(f"missing {DB}; run bruin first")
    return duckdb.connect(str(DB), read_only=True)


def test_swing_grounding():
    con = _connect()
    rows = {
        r[0]: (r[1], r[2])
        for r in con.execute(
            "select feature, holder_wins, n from mart_strategy_swing"
        ).fetchall()
    }
    assert rows["Yahtzee = 50"] == (54, 64)
    assert rows["Upper bonus (35)"] == (49, 58)
    assert rows["Large straight = 40"] == (29, 39)
    assert rows["Large straight = 0"] == (10, 39)
    assert rows["Small straight = 0"][1] < 10


def test_rescue_ls_yz_grounding():
    con = _connect()
    wins, n = con.execute(
        """
        select sum(focal_wins), sum(n)
        from mart_strategy_rescue
        where miss = 'Large straight = 0'
          and consolation in ('Has Yahtzee', 'Has both')
        """
    ).fetchone()
    assert (wins, n) == (13, 24)


def test_yz_matchup_exclusive_holders():
    con = _connect()
    rows = {
        r[0]: (r[1], r[2], r[3])
        for r in con.execute(
            """
            select holder, holder_wins, holder_losses, n_holder
            from mart_yz_matchup
            group by 1, 2, 3, 4
            """
        ).fetchall()
    }
    assert rows["Erin"] == (29, 8, 37)
    assert rows["Jordan"] == (25, 2, 27)
    wins, n = con.execute(
        """
        select sum(n) filter (where outcome = 'Holder won'), sum(n)
        from mart_yz_matchup
        """
    ).fetchone()
    assert (wins, n) == (54, 64)


if __name__ == "__main__":
    test_swing_grounding()
    test_rescue_ls_yz_grounding()
    test_yz_matchup_exclusive_holders()
    print("strategy mart grounding ok")
    sys.exit(0)
