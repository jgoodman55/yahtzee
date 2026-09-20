"""Pub map venue photo popups: seed URL / vendored JPEG only.

    python tests/test_pub_map_photos.py
    pytest tests/test_pub_map_photos.py
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXPORT = REPO / "dashboard" / "scripts" / "export_pub_map.py"
MAP_HTML = REPO / "dashboard" / "pub_map.html"
GEOJSON = REPO / "dashboard" / "pub_map" / "pubs.geojson"
SEED = REPO / "assets" / "seeds" / "seed_pubs.csv"
PHOTOS = REPO / "dashboard" / "pub_map" / "photos"
CHURCHILL_JPG = PHOTOS / "churchill_arms.jpg"
CADOGAN_JPG = PHOTOS / "cadogan_arms.jpg"
MARKETPLACE_JPG = PHOTOS / "vauxhall_marketplace.jpg"


def load_export():
    spec = importlib.util.spec_from_file_location("export_pub_map", EXPORT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def sample_pubs():
    return [
        {
            "name": "Churchill Arms",
            "merchant_name_raw": "CHURCHILL ARMS KENSINGTON",
            "lat": 51.5068785,
            "lng": -0.1948694,
            "source": "seed",
            "visit_count": 2,
        },
        {
            "name": "No Photo Arms",
            "merchant_name_raw": "NO PHOTO ARMS",
            "lat": 51.5021332,
            "lng": -0.1196679,
            "source": "seed",
            "visit_count": 1,
        },
    ]


def test_churchill_seed_photo_is_vendored():
    assert CHURCHILL_JPG.exists()
    assert CHURCHILL_JPG.stat().st_size > 1000
    blob = SEED.read_text(encoding="utf-8")
    assert "photo_url" in blob.splitlines()[0]
    assert "pub_map/photos/churchill_arms.jpg" in blob
    assert "CVB / Wikimedia Commons" in blob


def test_jordan_cadogan_and_marketplace_photos_are_vendored():
    assert CADOGAN_JPG.exists()
    assert CADOGAN_JPG.stat().st_size > 1000
    assert MARKETPLACE_JPG.exists()
    assert MARKETPLACE_JPG.stat().st_size > 1000
    with SEED.open(newline="", encoding="utf-8") as fh:
        rows = {row["merchant_name_raw"]: row for row in csv.DictReader(fh)}
    cadogan = rows["CADOGAN ARMS"]
    marketplace = rows["VAUXHALL MARKETPLACE"]
    assert cadogan["photo_url"] == "pub_map/photos/cadogan_arms.jpg"
    assert marketplace["photo_url"] == "pub_map/photos/vauxhall_marketplace.jpg"
    assert "Commons" not in cadogan["photo_attribution"]
    assert "Flickr" not in cadogan["photo_attribution"]
    assert cadogan["photo_attribution"] == "Jordan"
    assert marketplace["photo_attribution"] == "Jordan"


def test_html_popup_is_photo_card():
    html = MAP_HTML.read_text(encoding="utf-8")
    assert "venue-card" in html
    assert "venue-photo" in html
    assert "No photo yet" in html
    assert "Google Maps" in html
    assert "bindVenuePopup" in html
    assert "mouseover" in html
    assert "Photos later" not in html
    assert "isSafePhotoUrl" in html


def test_exporter_is_seed_only_no_live_photo_api():
    exp = load_export()
    src = EXPORT.read_text(encoding="utf-8")
    assert not hasattr(exp, "fetch_google_place_photo")
    assert not hasattr(exp, "load_photo_cache")
    assert "GOOGLE_PLACES" not in src
    assert "OFFLINE_TEST" not in src
    assert "--refresh-photos" not in src


def test_seed_photo_used_missing_seed_stays_empty():
    exp = load_export()
    pubs = sample_pubs()
    stats = exp.attach_photos(pubs)
    churchill = next(p for p in pubs if p["name"] == "Churchill Arms")
    farrier = next(p for p in pubs if p["name"] == "No Photo Arms")
    assert churchill["photo_url"] == "pub_map/photos/churchill_arms.jpg"
    assert churchill["photo_source"] == "seed"
    assert "Wikimedia" in churchill["photo_attribution"]
    assert "photo_url" not in farrier
    assert farrier["maps_url"].startswith("https://www.google.com/maps/search/")
    assert stats["seed"] == 1
    assert stats["none"] == 1


def test_image_url_alias_and_feature_export():
    exp = load_export()
    pubs = [
        {
            "name": "Alias Arms",
            "merchant_name_raw": "ALIAS ARMS",
            "lat": 51.5,
            "lng": -0.1,
            "source": "seed",
            "visit_count": 1,
        }
    ]
    seed_fields = {
        "merchant": {
            "ALIAS ARMS": {
                "note": "1 Test Street",
                "photo_url": "https://example.invalid/alias.jpg",
                "photo_source": "seed",
            }
        },
        "name": {},
    }
    exp.attach_photos(pubs, seed_fields=seed_fields)
    collection = exp.to_feature_collection(pubs)
    props = collection["features"][0]["properties"]
    assert props["photo_url"] == "https://example.invalid/alias.jpg"
    assert props["maps_url"].startswith("https://www.google.com/maps/search/")
    assert collection["metadata"]["photo_count"] == 1
    assert "borough" not in props
    assert "place_id" not in props


def test_load_seed_accepts_image_url_alias(tmp_path, monkeypatch):
    exp = load_export()
    seed = tmp_path / "seed_pubs.csv"
    seed.write_text(
        "merchant_name_raw,pub_name,lat,lng,note,image_url\n"
        "TEST PUB,Test Pub,51.5,-0.1,A note,https://example.invalid/img.jpg\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(exp, "SEED_PUBS", seed)
    fields = exp.load_seed_popup_fields()
    assert fields["merchant"]["TEST PUB"]["photo_url"] == "https://example.invalid/img.jpg"
    assert fields["merchant"]["TEST PUB"]["photo_source"] == "seed"


def test_exported_geojson_has_churchill_photo_and_maps_links():
    data = json.loads(GEOJSON.read_text(encoding="utf-8"))
    features = data["features"]
    by_name = {ft["properties"]["name"]: ft["properties"] for ft in features}
    churchill = by_name["Churchill Arms"]
    cadogan = by_name["Cadogan Arms"]
    marketplace = by_name["Vauxhall Marketplace"]
    assert churchill["photo_url"] == "pub_map/photos/churchill_arms.jpg"
    assert churchill["photo_source"] == "seed"
    assert "maps_url" in churchill
    assert cadogan["photo_url"] == "pub_map/photos/cadogan_arms.jpg"
    assert cadogan["photo_source"] == "seed"
    assert cadogan["photo_attribution"] == "Jordan"
    assert marketplace["photo_url"] == "pub_map/photos/vauxhall_marketplace.jpg"
    assert marketplace["photo_source"] == "seed"
    assert marketplace["photo_attribution"] == "Jordan"
    assert marketplace["maps_url"].startswith("https://www.google.com/maps/search/")
    assert data["metadata"]["photo_count"] == 44
    names_without = {
        ft["properties"]["name"]
        for ft in features
        if not ft["properties"].get("photo_url")
    }
    assert names_without == set()
    gone = {
        "Diogenes the Dog",
        "The Chalk Freehouse",
        "Supercute Taproom",
        "The Thirsty Farrier",
    }
    assert gone.isdisjoint(by_name)


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
