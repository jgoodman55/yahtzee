"""Grounding checks for Strategy marts (n=108 seed, 0 ties).

Run after `OFFLINE_TEST=1 bruin run --workers 1`:

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
    assert rows["Yahtzee = 50"] == (47, 56)
    assert rows["Upper bonus (35)"] == (48, 56)
    assert rows["Large straight = 40"] == (27, 36)
    assert rows["Large straight = 0"] == (9, 36)
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
    assert (wins, n) == (12, 22)


def test_yz_matchup_buckets():
    con = _connect()
    rows = {
        r[0]: r[1]
        for r in con.execute(
            "select yz_matchup, n_bucket from mart_yz_matchup group by 1, 2"
        ).fetchall()
    }
    assert rows == {"none": 32, "one": 56, "both": 20}
    holder, n = con.execute(
        """
        select holder_wins, n_bucket
        from mart_yz_matchup
        where yz_matchup = 'one'
        limit 1
        """
    ).fetchone()
    assert (holder, n) == (47, 56)


if __name__ == "__main__":
    test_swing_grounding()
    test_rescue_ls_yz_grounding()
    test_yz_matchup_buckets()
    print("strategy mart grounding ok")
    sys.exit(0)
