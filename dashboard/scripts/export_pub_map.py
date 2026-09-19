#!/usr/bin/env python3
"""Export confirmed pubs from mart_pub_locations for the Leaflet map.

Reads the pipeline DuckDB file (yahtzee.duckdb at the repo root) and writes:

  dashboard/pub_map/pubs.geojson   GeoJSON FeatureCollection
  dashboard/pub_map/pubs.js        same data as window.PUB_MAP_DATA (file:// safe)

Popup notes and optional seed photos come from seed_pubs.csv (joined here).
Borough is not exported — the map assigns it client-side from lat/lng +
vendored ONS GeoJSON.

Photo preview (highest trust first):

  1. seed_pubs.csv ``photo_url`` / ``image_url`` (manual, no API)
  2. dashboard/pub_map/pub_photos.json cache (previous Google Places hits)
  3. Google Places Text Search + Place Photos when GOOGLE_PLACES_API_KEY is
     set and OFFLINE_TEST is not 1

Run after `bruin run` whenever seed_pubs / raw_pub_visits / geocoding change:

  python3 dashboard/scripts/export_pub_map.py
  python3 dashboard/scripts/export_pub_map.py --db /path/to/yahtzee.duckdb
  OFFLINE_TEST=1 python3 dashboard/scripts/export_pub_map.py   # skip live photos

Requires: pip install duckdb
Live Place Photos also need: pip install requests
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import quote_plus

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "yahtzee.duckdb"
OUT_DIR = REPO_ROOT / "dashboard" / "pub_map"
SEED_PUBS = REPO_ROOT / "assets" / "seeds" / "seed_pubs.csv"
PHOTO_CACHE = OUT_DIR / "pub_photos.json"
LONDON_CENTER = (-0.1278, 51.5074)

GOOGLE_PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_PHOTO_MEDIA = "https://places.googleapis.com/v1/{name}/media"
PHOTO_MAX_WIDTH_PX = 400
GOOGLE_SEARCH_RADIUS_M = 80.0
GOOGLE_SLEEP_S = 0.15

OPTIONAL_PHOTO_KEYS = (
    "photo_url",
    "photo_source",
    "photo_attribution",
    "place_id",
    "maps_url",
)


def _connect(db_path: Path):
    try:
        import duckdb
    except ImportError as exc:
        raise SystemExit(
            "duckdb is required to export the pub map.\n"
            "  pip install duckdb\n"
            "or: pip install -r assets/python/requirements.txt"
        ) from exc
    if not db_path.exists():
        raise SystemExit(f"DuckDB file not found: {db_path}")
    return duckdb.connect(str(db_path), read_only=True)


def _table_columns(con, table: str) -> set[str]:
    rows = con.execute(
        "select lower(column_name) from information_schema.columns "
        "where lower(table_name) = lower(?)",
        [table],
    ).fetchall()
    return {r[0] for r in rows}


def load_confirmed_pubs(con) -> list[dict]:
    cols = _table_columns(con, "mart_pub_locations")
    if not cols:
        raise SystemExit(
            "mart_pub_locations is missing — run `bruin run` first "
            "(OFFLINE_TEST=1 is fine)."
        )

    visit_expr = (
        "coalesce(visit_count, 1)::integer"
        if "visit_count" in cols
        else "1::integer"
    )
    merged_expr = "merged_from" if "merged_from" in cols else "NULL"
    sql = f"""
        select
            coalesce(pub_name, merchant_name_raw) as name,
            merchant_name_raw,
            lat::double as lat,
            lng::double as lng,
            source,
            {visit_expr} as visit_count,
            {merged_expr} as merged_from
        from mart_pub_locations
        where is_confirmed_pub
          and lat is not null
          and lng is not null
        order by visit_count desc, name
    """
    rows = con.execute(sql).fetchdf()
    pubs = []
    for rec in rows.to_dict(orient="records"):
        pubs.append(
            {
                "name": rec["name"],
                "merchant_name_raw": rec["merchant_name_raw"],
                "lat": float(rec["lat"]),
                "lng": float(rec["lng"]),
                "source": rec.get("source"),
                "visit_count": int(rec["visit_count"] or 1),
                "merged_from": rec.get("merged_from"),
            }
        )
    return pubs


def _seed_cell(row: dict, *keys: str) -> str:
    for key in keys:
        value = (row.get(key) or "").strip()
        if value:
            return value
    return ""


def load_seed_popup_fields() -> dict[str, dict[str, str]]:
    """Address/note + optional photo fields from seed_pubs — not mart columns.

    Borough assignment is client-side (lat/lng + vendored ONS GeoJSON), so
    this export stays a thin mart dump plus seed popup extras.
    """
    by_merchant: dict[str, dict[str, str]] = {}
    by_name: dict[str, dict[str, str]] = {}
    if not SEED_PUBS.exists():
        return {"merchant": by_merchant, "name": by_name}
    with SEED_PUBS.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            extra = {}
            note = _seed_cell(row, "note")
            photo = _seed_cell(row, "photo_url", "image_url")
            attribution = _seed_cell(row, "photo_attribution")
            if note:
                extra["note"] = note
            if photo:
                extra["photo_url"] = photo
                extra["photo_source"] = "seed"
            if attribution:
                extra["photo_attribution"] = attribution
            if not extra:
                continue
            merchant = _seed_cell(row, "merchant_name_raw")
            name = _seed_cell(row, "pub_name")
            if merchant:
                by_merchant[merchant] = extra
            if name and name not in by_name:
                by_name[name] = extra
    return {"merchant": by_merchant, "name": by_name}


def load_seed_notes() -> tuple[dict[str, str], dict[str, str]]:
    """Address/note text from seed_pubs — not a mart column."""
    fields = load_seed_popup_fields()
    notes_by_merchant = {
        key: val["note"] for key, val in fields["merchant"].items() if val.get("note")
    }
    notes_by_name = {
        key: val["note"] for key, val in fields["name"].items() if val.get("note")
    }
    return notes_by_merchant, notes_by_name


def _lookup_seed_extra(pub: dict, fields: dict[str, dict[str, str]]) -> dict[str, str]:
    merchant = pub.get("merchant_name_raw") or ""
    name = pub.get("name") or ""
    merged = pub.get("merged_from") or ""
    extra = dict(fields["merchant"].get(merchant) or {})
    if not extra.get("photo_url"):
        for alias in [part.strip() for part in merged.split(",") if part.strip()]:
            alias_extra = fields["merchant"].get(alias) or {}
            if alias_extra.get("photo_url"):
                extra = {**extra, **alias_extra}
                break
    if not extra.get("photo_url"):
        name_extra = fields["name"].get(name) or {}
        extra = {**name_extra, **extra} if extra else dict(name_extra)
    elif not extra.get("note"):
        name_extra = fields["name"].get(name) or {}
        if name_extra.get("note"):
            extra["note"] = name_extra["note"]
    return extra


def attach_seed_notes(pubs: list[dict]) -> None:
    fields = load_seed_popup_fields()
    for pub in pubs:
        extra = _lookup_seed_extra(pub, fields)
        if extra.get("note"):
            pub["note"] = extra["note"]


def photo_cache_key(pub: dict) -> str:
    name = (pub.get("name") or "").strip()
    lat = float(pub["lat"])
    lng = float(pub["lng"])
    return f"{name}|{lat:.5f}|{lng:.5f}"


def maps_search_url(pub: dict) -> str:
    name = (pub.get("name") or "pub").strip()
    lat = pub.get("lat")
    lng = pub.get("lng")
    query = name
    if lat is not None and lng is not None:
        query = f"{name} {lat},{lng}"
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query)


def load_photo_cache(path: Path | None = None) -> dict:
    cache_path = path or PHOTO_CACHE
    if not cache_path.exists():
        return {"version": 1, "photos": {}}
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "photos": {}}
    if not isinstance(data, dict):
        return {"version": 1, "photos": {}}
    photos = data.get("photos")
    if not isinstance(photos, dict):
        photos = {}
    return {"version": 1, "photos": photos}


def save_photo_cache(data: dict, path: Path | None = None) -> Path:
    cache_path = path or PHOTO_CACHE
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "photos": data.get("photos") or {},
    }
    cache_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return cache_path


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _attribution_from_photo(photo: dict) -> str:
    authors = photo.get("authorAttributions") or []
    names = []
    for author in authors:
        label = (author.get("displayName") or "").strip()
        if label:
            names.append(label)
    if names:
        return ", ".join(names)
    return "Google"


def fetch_google_place_photo(pub: dict, api_key: str) -> dict | None:
    """Resolve a Place and return a cacheable photo URI, or None on miss/error.

    Uses Places API (New) Text Search + Place Photos. The photo *name*
    expires and must not be reused; we store the ``photoUri`` (and place id)
    so the static map can show an ``<img>`` without a client-side key.
    Those URIs can themselves go stale — ``--refresh-photos`` re-fetches.
    """
    try:
        import requests
    except ImportError:
        return None

    name = (pub.get("name") or "").strip()
    if not name:
        return None
    lat = float(pub["lat"])
    lng = float(pub["lng"])
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.photos,places.formattedAddress"
        ),
    }
    body = {
        "textQuery": f"{name} pub",
        "maxResultCount": 1,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": GOOGLE_SEARCH_RADIUS_M,
            }
        },
    }
    try:
        resp = requests.post(
            GOOGLE_PLACES_URL, json=body, headers=headers, timeout=10
        )
        resp.raise_for_status()
        places = resp.json().get("places") or []
        if not places:
            return {
                "status": "miss",
                "reason": "no_place",
                "fetched_at": _now_iso(),
            }
        place = places[0]
        photos = place.get("photos") or []
        place_id = place.get("id")
        if not photos:
            return {
                "status": "miss",
                "reason": "no_photos",
                "place_id": place_id,
                "fetched_at": _now_iso(),
            }
        photo = photos[0]
        photo_name = photo.get("name")
        if not photo_name:
            return {
                "status": "miss",
                "reason": "no_photo_name",
                "place_id": place_id,
                "fetched_at": _now_iso(),
            }
        media = requests.get(
            GOOGLE_PHOTO_MEDIA.format(name=photo_name),
            params={
                "maxWidthPx": PHOTO_MAX_WIDTH_PX,
                "skipHttpRedirect": "true",
                "key": api_key,
            },
            timeout=10,
        )
        media.raise_for_status()
        photo_uri = (media.json() or {}).get("photoUri")
        if not photo_uri:
            return {
                "status": "miss",
                "reason": "no_photo_uri",
                "place_id": place_id,
                "fetched_at": _now_iso(),
            }
        return {
            "status": "ok",
            "photo_url": photo_uri,
            "photo_source": "google",
            "photo_attribution": _attribution_from_photo(photo),
            "place_id": place_id,
            "fetched_at": _now_iso(),
        }
    except Exception:
        return {
            "status": "miss",
            "reason": "request_error",
            "fetched_at": _now_iso(),
        }


def attach_photos(
    pubs: list[dict],
    *,
    cache_path: Path | None = None,
    refresh: bool = False,
    offline: bool | None = None,
    api_key: str | None = None,
    sleep_s: float = GOOGLE_SLEEP_S,
    fetch_google: Callable[[dict, str], dict | None] | None = None,
    seed_fields: dict[str, dict[str, str]] | None = None,
) -> dict:
    """Fill photo_url / maps_url on each pub. Never raises; map still works."""
    if offline is None:
        offline = os.environ.get("OFFLINE_TEST") == "1"
    if api_key is None:
        api_key = os.environ.get("GOOGLE_PLACES_API_KEY") or ""
    fetcher = fetch_google or fetch_google_place_photo
    fields = seed_fields if seed_fields is not None else load_seed_popup_fields()
    cache = load_photo_cache(cache_path)
    photos = cache.setdefault("photos", {})
    stats = {
        "seed": 0,
        "cache": 0,
        "google": 0,
        "none": 0,
        "live_skipped": bool(offline or not api_key),
        "offline": bool(offline),
        "has_key": bool(api_key),
    }
    cache_dirty = False
    live_calls = 0

    for pub in pubs:
        pub["maps_url"] = maps_search_url(pub)
        extra = _lookup_seed_extra(pub, fields)
        if extra.get("note") and not pub.get("note"):
            pub["note"] = extra["note"]
        if extra.get("photo_url"):
            pub["photo_url"] = extra["photo_url"]
            pub["photo_source"] = extra.get("photo_source") or "seed"
            if extra.get("photo_attribution"):
                pub["photo_attribution"] = extra["photo_attribution"]
            stats["seed"] += 1
            continue

        key = photo_cache_key(pub)
        cached = photos.get(key) if isinstance(photos.get(key), dict) else None
        usable_cache = (
            cached
            and not refresh
            and cached.get("status") == "ok"
            and cached.get("photo_url")
        )
        if usable_cache:
            pub["photo_url"] = cached["photo_url"]
            pub["photo_source"] = cached.get("photo_source") or "google"
            if cached.get("photo_attribution"):
                pub["photo_attribution"] = cached["photo_attribution"]
            if cached.get("place_id"):
                pub["place_id"] = cached["place_id"]
            stats["cache"] += 1
            continue
        negative_cache = cached and not refresh and cached.get("status") == "miss"
        if negative_cache:
            stats["none"] += 1
            continue

        if offline or not api_key:
            stats["none"] += 1
            continue

        if live_calls:
            time.sleep(sleep_s)
        result = fetcher(pub, api_key) or {
            "status": "miss",
            "reason": "empty",
            "fetched_at": _now_iso(),
        }
        live_calls += 1
        photos[key] = result
        cache_dirty = True
        if result.get("status") == "ok" and result.get("photo_url"):
            pub["photo_url"] = result["photo_url"]
            pub["photo_source"] = result.get("photo_source") or "google"
            if result.get("photo_attribution"):
                pub["photo_attribution"] = result["photo_attribution"]
            if result.get("place_id"):
                pub["place_id"] = result["place_id"]
            stats["google"] += 1
        else:
            stats["none"] += 1

    if cache_dirty:
        save_photo_cache(cache, cache_path)
    return stats


def to_feature_collection(pubs: list[dict]) -> dict:
    features = []
    photo_count = 0
    for pub in pubs:
        props = {
            "name": pub["name"],
            "merchant_name_raw": pub["merchant_name_raw"],
            "source": pub["source"],
            "visit_count": pub["visit_count"],
        }
        if pub.get("note"):
            props["note"] = pub["note"]
        if pub.get("merged_from"):
            props["merged_from"] = pub["merged_from"]
        for key in OPTIONAL_PHOTO_KEYS:
            if pub.get(key):
                props[key] = pub[key]
        if props.get("photo_url"):
            photo_count += 1
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [pub["lng"], pub["lat"]],
                },
                "properties": props,
            }
        )
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "grain": "mart_pub_locations (standalone — not joined to games)",
            "default_center": {"lng": LONDON_CENTER[0], "lat": LONDON_CENTER[1]},
            "confirmed_pub_count": len(features),
            "photo_count": photo_count,
        },
    }


def write_outputs(collection: dict) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    geojson_path = OUT_DIR / "pubs.geojson"
    js_path = OUT_DIR / "pubs.js"
    payload = json.dumps(collection, indent=2, ensure_ascii=False)
    geojson_path.write_text(payload + "\n", encoding="utf-8")
    js_path.write_text(
        "// Generated by dashboard/scripts/export_pub_map.py — do not edit.\n"
        "window.PUB_MAP_DATA = "
        + payload
        + ";\n",
        encoding="utf-8",
    )
    return geojson_path, js_path


def _photo_summary(stats: dict) -> str:
    bits = [
        f"{stats['seed']} seed",
        f"{stats['cache']} cache",
        f"{stats['google']} google",
        f"{stats['none']} none",
    ]
    line = "Photos: " + ", ".join(bits)
    if stats.get("offline"):
        line += " (OFFLINE_TEST=1 — skipped live Place Photos)"
    elif not stats.get("has_key"):
        line += " (no GOOGLE_PLACES_API_KEY — seed/cache only)"
    return line


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"DuckDB path (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "--refresh-photos",
        action="store_true",
        help="Ignore pub_photos.json hits and re-query Google Places (needs a key).",
    )
    args = parser.parse_args()

    con = _connect(args.db)
    try:
        pubs = load_confirmed_pubs(con)
    finally:
        con.close()

    attach_seed_notes(pubs)
    photo_stats = attach_photos(pubs, refresh=args.refresh_photos)
    collection = to_feature_collection(pubs)
    geojson_path, js_path = write_outputs(collection)
    print(
        f"Exported {len(pubs)} confirmed pub(s)\n"
        f"  {geojson_path.relative_to(REPO_ROOT)}\n"
        f"  {js_path.relative_to(REPO_ROOT)}\n"
        f"  {_photo_summary(photo_stats)}"
    )
    if not pubs:
        print("No confirmed pubs with coordinates — add seed_pubs rows and re-run.")


if __name__ == "__main__":
    main()
