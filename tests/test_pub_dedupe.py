"""Proximity dedupe keeps neighboring but distinct seed pubs separate.

    python tests/test_pub_dedupe.py
    pytest tests/test_pub_dedupe.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
GEOCODE = REPO / "assets" / "python" / "geocode_pubs.py"


def load_geocode():
    spec = importlib.util.spec_from_file_location("geocode_pubs", GEOCODE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_derby_and_hanover_stay_distinct():
    geo = load_geocode()
    df = pd.DataFrame(
        [
            {
                "merchant_name_raw": "THE DERBY",
                "pub_name": "The Derby",
                "lat": 51.4811678,
                "lng": -0.1132925,
                "source": "seed",
                "is_confirmed_pub": True,
                "visit_count": 6,
            },
            {
                "merchant_name_raw": "THE HANOVER ARMS",
                "pub_name": "The Hanover Arms",
                "lat": 51.4813791,
                "lng": -0.1130873,
                "source": "seed",
                "is_confirmed_pub": True,
                "visit_count": 1,
            },
        ]
    )
    out = geo.dedupe_by_proximity(df)
    names = set(out["pub_name"])
    assert names == {"The Derby", "The Hanover Arms"}
    assert int(out.loc[out["pub_name"] == "The Derby", "visit_count"].iloc[0]) == 6
    assert int(out.loc[out["pub_name"] == "The Hanover Arms", "visit_count"].iloc[0]) == 1


def test_same_named_seed_aliases_still_merge():
    geo = load_geocode()
    df = pd.DataFrame(
        [
            {
                "merchant_name_raw": "ANCHOR BANKSIDE",
                "pub_name": "Anchor Bar",
                "lat": 51.5073,
                "lng": -0.0931,
                "source": "seed",
                "is_confirmed_pub": True,
                "visit_count": 8,
            },
            {
                "merchant_name_raw": "ANCHOR BAR",
                "pub_name": "Anchor Bar",
                "lat": 51.5073,
                "lng": -0.0931,
                "source": "seed",
                "is_confirmed_pub": True,
                "visit_count": 1,
            },
        ]
    )
    out = geo.dedupe_by_proximity(df)
    assert len(out) == 1
    assert int(out.iloc[0]["visit_count"]) == 9
    merged = str(out.iloc[0]["merged_from"])
    assert "ANCHOR BANKSIDE" in merged
    assert "ANCHOR BAR" in merged


if __name__ == "__main__":
    test_derby_and_hanover_stay_distinct()
    test_same_named_seed_aliases_still_merge()
    print("ok")
