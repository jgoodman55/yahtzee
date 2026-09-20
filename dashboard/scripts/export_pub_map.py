#!/usr/bin/env python3
"""Export confirmed pubs from mart_pub_locations for the Leaflet map.

Reads the pipeline DuckDB file (yahtzee.duckdb at the repo root) and writes:

  dashboard/pub_map/pubs.geojson   GeoJSON FeatureCollection
  dashboard/pub_map/pubs.js        same data as window.PUB_MAP_DATA (file:// safe)

Popup notes and optional seed photos come from seed_pubs.csv (joined here).
Borough is not exported — the map assigns it client-side from lat/lng +
vendored ONS GeoJSON.

Photo preview is seed-only:

  seed_pubs.csv ``photo_url`` / ``image_url`` (manual; often a vendored
  JPEG under dashboard/pub_map/photos/)

There is no live Google Places photo fetch and no API key. Pins without a
seed photo still export; the map shows **No photo yet**.

Run after `bruin run` whenever seed_pubs / raw_pub_visits / geocoding change:

  python3 dashboard/scripts/export_pub_map.py
  python3 dashboard/scripts/export_pub_map.py --db /path/to/yahtzee.duckdb

Requires: pip install duckdb
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.parse import quote_plus

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "yahtzee.duckdb"
OUT_DIR = REPO_ROOT / "dashboard" / "pub_map"
SEED_PUBS = REPO_ROOT / "assets" / "seeds" / "seed_pubs.csv"
LONDON_CENTER = (-0.1278, 51.5074)

OPTIONAL_PHOTO_KEYS = (
    "photo_url",
    "photo_source",
    "photo_attribution",
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
            "mart_pub_locations is missing — run `bruin run` first."
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


def maps_search_url(pub: dict) -> str:
    name = (pub.get("name") or "pub").strip()
    lat = pub.get("lat")
    lng = pub.get("lng")
    query = name
    if lat is not None and lng is not None:
        query = f"{name} {lat},{lng}"
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query)


def attach_photos(
    pubs: list[dict],
    *,
    seed_fields: dict[str, dict[str, str]] | None = None,
) -> dict:
    """Fill photo_url / maps_url from seed_pubs only. Never raises."""
    fields = seed_fields if seed_fields is not None else load_seed_popup_fields()
    stats = {"seed": 0, "none": 0}
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
        else:
            stats["none"] += 1
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
    return (
        f"Photos: {stats['seed']} seed, {stats['none']} none "
        "(seed_pubs.csv / vendored dashboard/pub_map/photos/ only)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"DuckDB path (default: {DEFAULT_DB})",
    )
    args = parser.parse_args()

    con = _connect(args.db)
    try:
        pubs = load_confirmed_pubs(con)
    finally:
        con.close()

    attach_seed_notes(pubs)
    photo_stats = attach_photos(pubs)
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
