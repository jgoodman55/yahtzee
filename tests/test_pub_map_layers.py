"""Pub map Layer A (borough choropleth) + Layer B (pint pins).

    python tests/test_pub_map_layers.py
    pytest tests/test_pub_map_layers.py
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GEOJSON = REPO / "dashboard" / "pub_map" / "pubs.geojson"
BOROUGHS = REPO / "dashboard" / "pub_map" / "london_boroughs.geojson"
BOROUGHS_JS = REPO / "dashboard" / "pub_map" / "london_boroughs.js"
MAP_HTML = REPO / "dashboard" / "pub_map.html"
EXPORT = REPO / "dashboard" / "scripts" / "export_pub_map.py"

OUTSIDE = "Outside London"
SNAP_DEG = 0.01
LONDON_BOROUGHS = {
    "Barking and Dagenham",
    "Barnet",
    "Bexley",
    "Brent",
    "Bromley",
    "Camden",
    "City of London",
    "Croydon",
    "Ealing",
    "Enfield",
    "Greenwich",
    "Hackney",
    "Hammersmith and Fulham",
    "Haringey",
    "Harrow",
    "Havering",
    "Hillingdon",
    "Hounslow",
    "Islington",
    "Kensington and Chelsea",
    "Kingston upon Thames",
    "Lambeth",
    "Lewisham",
    "Merton",
    "Newham",
    "Redbridge",
    "Richmond upon Thames",
    "Southwark",
    "Sutton",
    "Tower Hamlets",
    "Waltham Forest",
    "Wandsworth",
    "Westminster",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def point_in_ring(lng: float, lat: float, ring: list) -> bool:
    inside = False
    j = len(ring) - 1
    for i, (xi, yi) in enumerate(ring):
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lng < (xj - xi) * (lat - yi) / (
            (yj - yi) or 1e-12
        ) + xi:
            inside = not inside
        j = i
    return inside


def point_in_geom(lng: float, lat: float, geom: dict) -> bool:
    coords = geom.get("coordinates") or []
    polys = [coords] if geom.get("type") == "Polygon" else coords
    for poly in polys:
        if not poly:
            continue
        if point_in_ring(lng, lat, poly[0]) and not any(
            point_in_ring(lng, lat, hole) for hole in poly[1:]
        ):
            return True
    return False


def flatten_coords(node):
    if not node:
        return
    if isinstance(node[0], (int, float)):
        yield node
        return
    for child in node:
        yield from flatten_coords(child)


def min_vertex_dist(lng: float, lat: float, geom: dict) -> float:
    best = math.inf
    for x, y in flatten_coords(geom.get("coordinates")):
        d = (x - lng) ** 2 + (y - lat) ** 2
        if d < best:
            best = d
    return math.sqrt(best)


def bbox(features: list[dict]) -> tuple[float, float, float, float]:
    xs, ys = [], []
    for ft in features:
        for x, y in flatten_coords(ft["geometry"]["coordinates"]):
            xs.append(x)
            ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def assign_borough(lng: float, lat: float, boroughs: list[dict]) -> str:
    for ft in boroughs:
        if point_in_geom(lng, lat, ft["geometry"]):
            return ft["properties"]["name"]
    min_x, min_y, max_x, max_y = bbox(boroughs)
    if not (min_x <= lng <= max_x and min_y <= lat <= max_y):
        return OUTSIDE
    best_name = OUTSIDE
    best = SNAP_DEG
    for ft in boroughs:
        d = min_vertex_dist(lng, lat, ft["geometry"])
        if d < best:
            best = d
            best_name = ft["properties"]["name"]
    return best_name


def test_vendored_london_boroughs():
    data = load_json(BOROUGHS)
    assert data["type"] == "FeatureCollection"
    names = {ft["properties"]["name"] for ft in data["features"]}
    assert names == LONDON_BOROUGHS
    assert len(data["features"]) == 33
    js = BOROUGHS_JS.read_text(encoding="utf-8")
    assert "window.LONDON_BOROUGHS" in js
    assert "OGL" in js or "ONS" in js


def test_html_layers_and_pint_svg():
    html = MAP_HTML.read_text(encoding="utf-8")
    assert "circleMarker" not in html
    assert "L.divIcon" in html
    assert 'className: "pint-pin"' in html
    assert "<svg" in html
    assert "🍺" not in html
    assert 'id="btn-boroughs"' in html
    assert 'id="btn-pubs"' in html
    assert "BEER_STOPS" in html
    assert "assignBorough" in html
    assert "pub_map/london_boroughs.js" in html
    assert "is-count" not in html
    assert "NAME_ZOOM" not in html
    assert "BOROUGH_STOPS" not in html
    assert "displayBoroughName" in html
    assert "is-hidden" in html
    assert "resolveBoroughLabelCollisions" in html
    assert "venue-card" in html
    assert "No photo yet" in html
    assert "bindVenuePopup" in html
    assert "keepInView: false" in html
    assert "keepInView: true" not in html
    assert ".leaflet-popup-pane { pointer-events: none; }" in html
    assert "Photos later" not in html


def test_export_script_joins_notes_not_borough():
    src = EXPORT.read_text(encoding="utf-8")
    assert "attach_seed_notes" in src
    assert "attach_photos" in src
    assert "seed_pubs.csv" in src
    assert "client-side" in src


def test_pubs_export_includes_notes():
    features = load_json(GEOJSON)["features"]
    with_notes = [ft for ft in features if ft["properties"].get("note")]
    assert len(with_notes) == len(features)
    derby = next(ft for ft in features if ft["properties"]["name"] == "The Derby")
    assert "Kennington Park Rd" in derby["properties"]["note"]
    assert "borough" not in derby["properties"]


def test_point_in_polygon_assignments():
    boroughs = load_json(BOROUGHS)["features"]
    pubs = load_json(GEOJSON)["features"]
    expected = {
        "Anchor Bar": "Southwark",
        "The Ship": "Southwark",
        "The Monument": "City of London",
        "Nancy Spains": "City of London",
        "The Three Johns": "Islington",
        "Churchill Arms": "Kensington and Chelsea",
        "Gordon's Wine Bar": "Westminster",
        "The Spaniards Inn": "Barnet",
        "White Horse Peckham": "Southwark",
        "The Derby": "Lambeth",
        "The Bear Inn": OUTSIDE,
        "The Crown": OUTSIDE,
        "Tamesis Dock": "Lambeth",
    }
    got = {}
    for ft in pubs:
        lng, lat = ft["geometry"]["coordinates"]
        got[ft["properties"]["name"]] = assign_borough(lng, lat, boroughs)
    for name, borough in expected.items():
        assert got[name] == borough, (name, got[name], borough)


def test_borough_visit_totals_sum_unique_days():
    boroughs = load_json(BOROUGHS)["features"]
    pubs = load_json(GEOJSON)["features"]
    totals = defaultdict(int)
    for ft in pubs:
        lng, lat = ft["geometry"]["coordinates"]
        name = assign_borough(lng, lat, boroughs)
        totals[name] += int(ft["properties"]["visit_count"] or 1)
    assert totals[OUTSIDE] >= 2  # Oxford Crown + Bear Inn
    assert totals["Southwark"] > 0
    assert totals["Lambeth"] > 0
    assert sum(totals.values()) == sum(
        int(ft["properties"]["visit_count"] or 1) for ft in pubs
    )


if __name__ == "__main__":
    for fn in (
        test_vendored_london_boroughs,
        test_html_layers_and_pint_svg,
        test_export_script_joins_notes_not_borough,
        test_pubs_export_includes_notes,
        test_point_in_polygon_assignments,
        test_borough_visit_totals_sum_unique_days,
    ):
        fn()
        print("ok", fn.__name__)
    print("ok")
