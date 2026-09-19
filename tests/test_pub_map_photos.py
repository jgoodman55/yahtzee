"""Pub map venue photo popups: seed URL, Google cache, offline fallback.

    python tests/test_pub_map_photos.py
    pytest tests/test_pub_map_photos.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXPORT = REPO / "dashboard" / "scripts" / "export_pub_map.py"
MAP_HTML = REPO / "dashboard" / "pub_map.html"
GEOJSON = REPO / "dashboard" / "pub_map" / "pubs.geojson"
SEED = REPO / "assets" / "seeds" / "seed_pubs.csv"
CHURCHILL_JPG = REPO / "dashboard" / "pub_map" / "photos" / "churchill_arms.jpg"


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
            "name": "The Thirsty Farrier",
            "merchant_name_raw": "THE THIRSTY FARRIER S",
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


def test_seed_photo_beats_cache_and_google(tmp_path):
    exp = load_export()
    cache_path = tmp_path / "pub_photos.json"
    calls = []

    def fake_google(pub, api_key):
        calls.append(pub["name"])
        return {
            "status": "ok",
            "photo_url": "https://example.invalid/google.jpg",
            "photo_source": "google",
            "fetched_at": "2026-09-19T00:00:00Z",
        }

    pubs = sample_pubs()
    stats = exp.attach_photos(
        pubs,
        cache_path=cache_path,
        refresh=False,
        offline=False,
        api_key="fake-key",
        sleep_s=0,
        fetch_google=fake_google,
    )
    churchill = next(p for p in pubs if p["name"] == "Churchill Arms")
    farrier = next(p for p in pubs if p["name"] == "The Thirsty Farrier")
    assert churchill["photo_url"] == "pub_map/photos/churchill_arms.jpg"
    assert churchill["photo_source"] == "seed"
    assert "Wikimedia" in churchill["photo_attribution"]
    assert farrier["photo_url"] == "https://example.invalid/google.jpg"
    assert farrier["photo_source"] == "google"
    assert farrier["maps_url"].startswith("https://www.google.com/maps/search/")
    assert stats["seed"] == 1
    assert stats["google"] == 1
    assert calls == ["The Thirsty Farrier"]


def test_cache_hit_skips_live_fetch(tmp_path):
    exp = load_export()
    pubs = [
        {
            "name": "The Thirsty Farrier",
            "merchant_name_raw": "THE THIRSTY FARRIER S",
            "lat": 51.5021332,
            "lng": -0.1196679,
            "source": "seed",
            "visit_count": 1,
        }
    ]
    key = exp.photo_cache_key(pubs[0])
    cache_path = tmp_path / "pub_photos.json"
    cache_path.write_text(
        json.dumps(
            {
                "version": 1,
                "photos": {
                    key: {
                        "status": "ok",
                        "photo_url": "https://example.invalid/cached.jpg",
                        "photo_source": "google",
                        "photo_attribution": "Cached Photog",
                        "place_id": "ChIJ-test",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    calls = []
    stats = exp.attach_photos(
        pubs,
        cache_path=cache_path,
        refresh=False,
        offline=False,
        api_key="fake-key",
        sleep_s=0,
        fetch_google=lambda pub, key: calls.append(pub["name"]),
        seed_fields={"merchant": {}, "name": {}},
    )
    assert calls == []
    assert pubs[0]["photo_url"] == "https://example.invalid/cached.jpg"
    assert pubs[0]["place_id"] == "ChIJ-test"
    assert stats["cache"] == 1
    assert stats["google"] == 0


def test_offline_and_missing_key_skip_live_fetch(tmp_path):
    exp = load_export()
    calls = []

    def fake_google(pub, api_key):
        calls.append(api_key)
        return {"status": "ok", "photo_url": "https://example.invalid/nope.jpg"}

    pubs = [
        {
            "name": "The Thirsty Farrier",
            "merchant_name_raw": "THE THIRSTY FARRIER S",
            "lat": 51.5021332,
            "lng": -0.1196679,
            "source": "seed",
            "visit_count": 1,
        }
    ]
    seed_fields = {"merchant": {}, "name": {}}
    exp.attach_photos(
        pubs,
        cache_path=tmp_path / "a.json",
        offline=True,
        api_key="fake-key",
        sleep_s=0,
        fetch_google=fake_google,
        seed_fields=seed_fields,
    )
    exp.attach_photos(
        list(pubs),
        cache_path=tmp_path / "b.json",
        offline=False,
        api_key="",
        sleep_s=0,
        fetch_google=fake_google,
        seed_fields=seed_fields,
    )
    assert calls == []
    assert "photo_url" not in pubs[0]


def test_negative_cache_not_retried(tmp_path):
    exp = load_export()
    pubs = [
        {
            "name": "The Thirsty Farrier",
            "merchant_name_raw": "THE THIRSTY FARRIER S",
            "lat": 51.5021332,
            "lng": -0.1196679,
            "source": "seed",
            "visit_count": 1,
        }
    ]
    key = exp.photo_cache_key(pubs[0])
    cache_path = tmp_path / "pub_photos.json"
    cache_path.write_text(
        json.dumps(
            {
                "version": 1,
                "photos": {key: {"status": "miss", "reason": "no_photos"}},
            }
        ),
        encoding="utf-8",
    )
    calls = []
    stats = exp.attach_photos(
        pubs,
        cache_path=cache_path,
        refresh=False,
        offline=False,
        api_key="fake-key",
        sleep_s=0,
        fetch_google=lambda pub, key: calls.append("x") or {"status": "ok"},
        seed_fields={"merchant": {}, "name": {}},
    )
    assert calls == []
    assert stats["none"] == 1


def test_refresh_photos_bypasses_cache(tmp_path):
    exp = load_export()
    pubs = [
        {
            "name": "The Thirsty Farrier",
            "merchant_name_raw": "THE THIRSTY FARRIER S",
            "lat": 51.5021332,
            "lng": -0.1196679,
            "source": "seed",
            "visit_count": 1,
        }
    ]
    key = exp.photo_cache_key(pubs[0])
    cache_path = tmp_path / "pub_photos.json"
    cache_path.write_text(
        json.dumps(
            {
                "version": 1,
                "photos": {
                    key: {
                        "status": "ok",
                        "photo_url": "https://example.invalid/old.jpg",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    stats = exp.attach_photos(
        pubs,
        cache_path=cache_path,
        refresh=True,
        offline=False,
        api_key="fake-key",
        sleep_s=0,
        fetch_google=lambda pub, key: {
            "status": "ok",
            "photo_url": "https://example.invalid/new.jpg",
            "photo_source": "google",
        },
        seed_fields={"merchant": {}, "name": {}},
    )
    assert pubs[0]["photo_url"] == "https://example.invalid/new.jpg"
    assert stats["google"] == 1
    saved = json.loads(cache_path.read_text(encoding="utf-8"))
    assert saved["photos"][key]["photo_url"] == "https://example.invalid/new.jpg"


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
    # Simulate image_url already normalized by load_seed_popup_fields.
    exp.attach_photos(
        pubs,
        cache_path=None,
        offline=True,
        api_key="",
        sleep_s=0,
        fetch_google=lambda *_: None,
        seed_fields=seed_fields,
    )
    collection = exp.to_feature_collection(pubs)
    props = collection["features"][0]["properties"]
    assert props["photo_url"] == "https://example.invalid/alias.jpg"
    assert props["maps_url"].startswith("https://www.google.com/maps/search/")
    assert collection["metadata"]["photo_count"] == 1
    assert "borough" not in props


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
    churchill = next(ft for ft in features if ft["properties"]["name"] == "Churchill Arms")
    farrier = next(
        ft for ft in features if ft["properties"]["name"] == "The Thirsty Farrier"
    )
    assert churchill["properties"]["photo_url"] == "pub_map/photos/churchill_arms.jpg"
    assert churchill["properties"]["photo_source"] == "seed"
    assert "maps_url" in churchill["properties"]
    assert "photo_url" not in farrier["properties"]
    assert farrier["properties"]["maps_url"].startswith(
        "https://www.google.com/maps/search/"
    )
    assert data["metadata"]["photo_count"] >= 1


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
