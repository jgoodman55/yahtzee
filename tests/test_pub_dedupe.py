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


def test_geocode_is_seed_only_no_live_apis():
    geo = load_geocode()
    src = GEOCODE.read_text(encoding="utf-8")
    assert not hasattr(geo, "try_nominatim")
    assert not hasattr(geo, "try_google_places")
    assert not hasattr(geo, "OFFLINE_TEST")
    assert not hasattr(geo, "GOOGLE_API_KEY")
    assert "nominatim.openstreetmap.org" not in src
    assert "GOOGLE_PLACES" not in src
    assert "OFFLINE_TEST" not in src


def test_resolve_merchant_uses_seed_coords():
    geo = load_geocode()
    seed = pd.DataFrame(
        [
            {
                "merchant_name_raw": "THE DERBY",
                "pub_name": "The Derby",
                "lat": 51.4811678,
                "lng": -0.1132925,
            }
        ]
    )
    hit = geo.resolve_merchant("THE DERBY", seed)
    assert hit["source"] == "seed"
    assert hit["pub_name"] == "The Derby"
    assert hit["lat"] == 51.4811678
    assert hit["is_confirmed_pub"] is True


def test_unresolved_when_no_seed_match():
    geo = load_geocode()
    seed = pd.DataFrame(
        columns=["merchant_name_raw", "pub_name", "lat", "lng"]
    )
    miss = geo.resolve_merchant("UNKNOWN TAPROOM LTD", seed)
    assert miss["source"] == "unresolved"
    assert miss["lat"] is None
    assert miss["lng"] is None
    assert miss["is_confirmed_pub"] is False
    assert miss["merchant_name_raw"] == "UNKNOWN TAPROOM LTD"


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
    test_geocode_is_seed_only_no_live_apis()
    test_resolve_merchant_uses_seed_coords()
    test_unresolved_when_no_seed_match()
    test_derby_and_hanover_stay_distinct()
    test_same_named_seed_aliases_still_merge()
    print("ok")
