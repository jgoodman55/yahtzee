"""Jordan 2026-09-15 pub-map pin list, grounded in seed / visits / Leaflet export.

    python tests/test_pub_map_jordan_pins.py
    pytest tests/test_pub_map_jordan_pins.py
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "assets" / "seeds" / "seed_pubs.csv"
VISITS = REPO / "assets" / "seeds" / "raw_pub_visits.csv"
GEOJSON = REPO / "dashboard" / "pub_map" / "pubs.geojson"
MAP_HTML = REPO / "dashboard" / "pub_map.html"

REMOVED = (
    "THE BUCCANEER",
    "FCB PADDINGTON",
    "The Buccaneer",
    "FCB Paddington",
    "WALRUS",
    "WALRUS AND CARPENTER",
    "The Walrus & Carpenter",
    "The Walrus",
    "DIOGENES THE DOG L",
    "THE CHALK FREE HOUSE L",
    "SUPERCUTE TAPROOM",
    "THE THIRSTY FARRIER S",
    "Diogenes the Dog",
    "The Chalk Freehouse",
    "Supercute Taproom",
    "The Thirsty Farrier",
    "PIG AND BUTCHER",
    "Pig and Butcher",
)


def load_seed() -> dict[str, dict]:
    with SEED.open(newline="", encoding="utf-8") as fh:
        return {row["merchant_name_raw"]: row for row in csv.DictReader(fh)}


def load_visits() -> Counter:
    with VISITS.open(newline="", encoding="utf-8") as fh:
        return Counter(row["merchant_name_raw"] for row in csv.DictReader(fh))


def load_features() -> list[dict]:
    data = json.loads(GEOJSON.read_text(encoding="utf-8"))
    return data["features"]


def by_name(features: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for feat in features:
        grouped.setdefault(feat["properties"]["name"], []).append(feat)
    return grouped


def test_seed_jordan_addresses_and_names():
    seed = load_seed()
    cases = {
        "WHITE HORSE": ("White Horse Peckham", "20-222 Peckham Rye"),
        "THE SHIP": ("The Ship", "68 Borough Rd"),
        "THE DERBY": ("The Derby", "336 Kennington Park Rd"),
        "THE HANOVER ARMS": ("The Hanover Arms", "326 Kennington Park Rd"),
        "DUKE OF WELLINGTON": ("Duke of Wellington", "63 Eaton Terrace"),
        "THE DUCHY": ("The Duchy Arms", "63 Sancroft St"),
        "SPANIARDS": ("The Spaniards Inn", "Spaniards Rd"),
        "ANGLESEA ARMS": ("Anglesea Arms", "15 Selwood Terrace"),
        "GERMAN KRAFT MM": ("Mercato Metropolitano", "42 Newington Causeway"),
        "CROWN 052892": ("The Crown", "59a Cornmarket St"),
        "MONUMENT": ("The Monument", "18 Fish St Hill"),
        "BEEHIVE": ("The Beehive", "51 Durham St"),
    }
    for merchant, (pub_name, address) in cases.items():
        row = seed[merchant]
        assert row["pub_name"] == pub_name, merchant
        assert address in row["note"], (merchant, row["note"])
        assert row["lat"] and row["lng"]


def test_derby_and_hanover_are_separate_pins():
    seed = load_seed()
    grouped = by_name(load_features())
    derby = seed["THE DERBY"]
    hanover = seed["THE HANOVER ARMS"]
    assert derby["pub_name"] != hanover["pub_name"]
    assert (derby["lat"], derby["lng"]) != (hanover["lat"], hanover["lng"])
    assert len(grouped["The Derby"]) == 1
    assert len(grouped["The Hanover Arms"]) == 1
    d_feat = grouped["The Derby"][0]
    h_feat = grouped["The Hanover Arms"][0]
    assert d_feat["geometry"]["coordinates"] != h_feat["geometry"]["coordinates"]
    assert d_feat["properties"]["visit_count"] == 6
    assert h_feat["properties"]["visit_count"] == 1


def test_walrus_and_walrus_carpenter_are_gone():
    seed = load_seed()
    visits = load_visits()
    grouped = by_name(load_features())
    blob = GEOJSON.read_text(encoding="utf-8")
    for merchant in ("WALRUS", "WALRUS AND CARPENTER"):
        assert merchant not in seed
        assert visits[merchant] == 0
    assert "The Walrus & Carpenter" not in grouped
    assert "The Walrus" not in grouped
    assert "WALRUS" not in blob
    assert "Walrus" not in blob


def test_removals_are_gone():
    seed = load_seed()
    visits = load_visits()
    blob = GEOJSON.read_text(encoding="utf-8")
    for name in REMOVED:
        assert name not in seed
        assert visits[name] == 0
        assert name not in blob


def test_added_crown_monument_beehive():
    seed = load_seed()
    visits = load_visits()
    grouped = by_name(load_features())
    assert seed["CROWN 052892"]["pub_name"] == "The Crown"
    assert visits["CROWN 052892"] == 1
    assert len(grouped["The Crown"]) == 1
    assert grouped["The Crown"][0]["properties"]["visit_count"] == 1

    assert seed["MONUMENT"]["pub_name"] == "The Monument"
    assert visits["MONUMENT"] == 2
    assert grouped["The Monument"][0]["properties"]["visit_count"] == 2

    assert seed["BEEHIVE"]["pub_name"] == "The Beehive"
    assert visits["BEEHIVE"] == 1
    assert grouped["The Beehive"][0]["properties"]["visit_count"] == 1


def test_mc_and_marketplace_are_day_deduped():
    visits = load_visits()
    grouped = by_name(load_features())
    assert visits["MC AND SONS"] == 3
    assert visits["MC AND SONS VAUXHALL"] == 3
    assert visits["VAUXHALL MARKETPLACE"] == 3
    assert grouped["MC and Sons Southwark"][0]["properties"]["visit_count"] == 3
    assert grouped["MC and Sons Vauxhall"][0]["properties"]["visit_count"] == 3
    assert grouped["Vauxhall Marketplace"][0]["properties"]["visit_count"] == 3


def test_spaniards_pin_is_the_pub_amenity_not_the_bus_stop():
    seed = load_seed()
    grouped = by_name(load_features())
    lat = float(seed["SPANIARDS"]["lat"])
    lng = float(seed["SPANIARDS"]["lng"])
    # OSM amenity=pub (not the inn-named bus stop at 51.5702319, -0.1737169).
    assert abs(lat - 51.5698601) < 1e-6
    assert abs(lng - (-0.1740839)) < 1e-6
    coords = grouped["The Spaniards Inn"][0]["geometry"]["coordinates"]
    assert abs(coords[1] - lat) < 1e-6
    assert abs(coords[0] - lng) < 1e-6


def test_ship_is_borough_road_not_gate_st():
    seed = load_seed()
    grouped = by_name(load_features())
    row = seed["THE SHIP"]
    assert row["pub_name"] == "The Ship"
    assert "68 Borough Rd" in row["note"]
    assert "SE1 1DX" in row["note"]
    assert "Gate St" not in row["note"]
    lat = float(row["lat"])
    lng = float(row["lng"])
    # 68 Borough Rd, London SE1 1DX (public GPS for that address, not Gate St).
    assert abs(lat - 51.4992665) < 1e-6
    assert abs(lng - (-0.0969249)) < 1e-6
    feat = grouped["The Ship"][0]
    coords = feat["geometry"]["coordinates"]
    assert abs(coords[1] - lat) < 1e-6
    assert abs(coords[0] - lng) < 1e-6
    blob = GEOJSON.read_text(encoding="utf-8")
    assert "Gate St" not in blob
    assert "Pig and Butcher" not in blob
    assert "PIG AND BUTCHER" not in blob


def test_map_uses_pint_pins_and_esri_basemap():
    html = MAP_HTML.read_text(encoding="utf-8")
    assert "circleMarker" not in html
    assert "pint-pin" in html
    assert "pale lager" in html.lower() or "pale → stout" in html or "pale lager" in html
    assert 'id="btn-boroughs"' in html
    assert 'id="btn-pubs"' in html
    assert "pub_map/london_boroughs.js" in html
    assert "World_Light_Gray_Base" in html
    assert "World_Light_Gray_Reference" in html
    assert "keepInView: false" in html
    assert "keepInView: true" not in html


def test_confirmed_pin_count():
    features = load_features()
    names = [f["properties"]["name"] for f in features]
    assert len(features) == 45
    assert "The Butcher's Hook" in names
    assert "The Queen's Arms" in names
    hook = next(f for f in features if f["properties"]["name"] == "The Butcher's Hook")
    queens = next(f for f in features if f["properties"]["name"] == "The Queen's Arms")
    assert hook["properties"]["visit_count"] == 0
    assert hook["properties"]["games_played"] == 1
    assert hook["properties"]["erin_wins"] == 1
    assert "Fulham Road" in hook["properties"]["note"]
    assert queens["properties"]["visit_count"] == 0
    assert queens["properties"]["games_played"] == 2
    assert queens["properties"]["jordan_wins"] == 2
    assert "Warwick Way" in queens["properties"]["note"]
    assert "The Walrus & Carpenter" not in names
    assert "The Buccaneer" not in names
    assert "German Kraft" not in names
    assert "Diogenes the Dog" not in names
    assert "The Chalk Freehouse" not in names
    assert "Supercute Taproom" not in names
    assert "The Thirsty Farrier" not in names
    assert "Pig and Butcher" not in names
    assert "The Ship" in names


if __name__ == "__main__":
    for fn in (
        test_seed_jordan_addresses_and_names,
        test_derby_and_hanover_are_separate_pins,
        test_walrus_and_walrus_carpenter_are_gone,
        test_removals_are_gone,
        test_added_crown_monument_beehive,
        test_mc_and_marketplace_are_day_deduped,
        test_spaniards_pin_is_the_pub_amenity_not_the_bus_stop,
        test_ship_is_borough_road_not_gate_st,
        test_map_uses_pint_pins_and_esri_basemap,
        test_confirmed_pin_count,
    ):
        fn()
        print("ok", fn.__name__)
    print("ok")
