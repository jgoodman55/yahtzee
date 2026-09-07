"""@bruin
name: mart_pub_locations
connection: duckdb-default
type: python
depends:
  - raw_pub_visits
  - seed_pubs
materialization:
  type: table
@bruin"""

# Resolves each merchant name in raw_pub_visits to a confirmed pub location
# (visit_count is the number of visit-log rows per merchant), in priority order:
#   1. seed_pubs.csv        (manual, free, highest trust)
#   2. OpenStreetMap Nominatim (free, no key)
#   3. Google Places Text Search (needs GOOGLE_PLACES_API_KEY, small free tier)
#   4. unresolved            (flagged for you to review and add to the seed)
#
# Then dedupes across sources by physical proximity: "Anchor Bar" (seed) and
# "Anchor Bankside (South" (a card-statement merchant string) are different
# text but the same building — string similarity alone won't reliably catch
# that (fuzzy name matching is fooled by chain pub naming and abbreviations
# just as easily as it's helped by them). Instead, once each merchant string
# has *coordinates* (from any of the three sources above), venues within
# ~50m of each other are treated as the same physical pub and collapsed to
# one row, keeping the seed's name/coords as authoritative when a seed match
# is involved.
#
# Set OFFLINE_TEST=1 to skip live Nominatim/Google calls entirely (seed
# matches only, everything else marked unresolved) — useful for testing the
# rest of the Bruin pipeline without network access or API keys.
#
# Requires: requests  (add to requirements.txt next to this asset)

import os
import time

import pandas as pd
import requests
from bruin import query

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
GOOGLE_PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")
OFFLINE_TEST = os.environ.get("OFFLINE_TEST") == "1"

# Nominatim's usage policy requires a real identifying User-Agent and max 1 req/sec.
HEADERS = {"User-Agent": "yahtzee-analytics-personal-project (contact: you@example.com)"}

PUB_OSM_CLASSES = {"pub", "bar", "biergarten"}
PUB_GOOGLE_TYPES = {"bar", "night_club"}  # Google has no distinct "pub" type

# ~50m at London's latitude — tight enough not to merge genuinely different
# pubs a couple of blocks apart, loose enough to absorb GPS/geocoding jitter.
DEDUPE_RADIUS_DEGREES = 0.00045


def try_seed(merchant: str, seed_df: pd.DataFrame):
    match = seed_df[seed_df["merchant_name_raw"] == merchant]
    if not match.empty and pd.notna(match.iloc[0]["lat"]):
        row = match.iloc[0]
        return {
            "pub_name": row["pub_name"],
            "lat": float(row["lat"]),
            "lng": float(row["lng"]),
            "source": "seed",
            "is_confirmed_pub": True,
        }
    return None


def try_nominatim(merchant: str):
    if OFFLINE_TEST:
        return None
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": merchant, "format": "jsonv2", "addressdetails": 0, "limit": 1},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        time.sleep(1)  # respect Nominatim's 1 req/sec policy
        if not results:
            return None
        top = results[0]
        if top.get("class") == "amenity" and top.get("type") in PUB_OSM_CLASSES:
            return {
                "pub_name": top.get("display_name", merchant).split(",")[0],
                "lat": float(top["lat"]),
                "lng": float(top["lon"]),
                "source": "osm",
                "is_confirmed_pub": True,
            }
    except requests.RequestException:
        pass
    return None


def try_google_places(merchant: str):
    if OFFLINE_TEST or not GOOGLE_API_KEY:
        return None
    try:
        resp = requests.post(
            GOOGLE_PLACES_URL,
            json={"textQuery": merchant},
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": GOOGLE_API_KEY,
                "X-Goog-FieldMask": "places.displayName,places.location,places.types",
            },
            timeout=10,
        )
        resp.raise_for_status()
        places = resp.json().get("places", [])
        if not places:
            return None
        top = places[0]
        types = set(top.get("types", []))
        if types & PUB_GOOGLE_TYPES:
            return {
                "pub_name": top["displayName"]["text"],
                "lat": top["location"]["latitude"],
                "lng": top["location"]["longitude"],
                "source": "google",
                "is_confirmed_pub": True,
            }
    except requests.RequestException:
        pass
    return None


def resolve_merchant(merchant: str, seed_df: pd.DataFrame) -> dict:
    for resolver in (lambda m: try_seed(m, seed_df), try_nominatim, try_google_places):
        result = resolver(merchant)
        if result:
            result["merchant_name_raw"] = merchant
            return result
    return {
        "merchant_name_raw": merchant,
        "pub_name": None,
        "lat": None,
        "lng": None,
        "source": "unresolved",
        "is_confirmed_pub": False,
    }


def dedupe_by_proximity(df: pd.DataFrame) -> pd.DataFrame:
    """Collapses rows whose coordinates are within DEDUPE_RADIUS_DEGREES of
    each other into a single pub, preferring a seed-sourced row's name/coords
    as the canonical one when a seed match is in the cluster."""
    locatable = df[df["lat"].notna()].copy()
    unresolved = df[df["lat"].isna()].copy()
    if locatable.empty:
        return df

    locatable["lat"] = pd.to_numeric(locatable["lat"], errors="coerce")
    locatable["lng"] = pd.to_numeric(locatable["lng"], errors="coerce")
    locatable = locatable.dropna(subset=["lat", "lng"])
    if locatable.empty:
        return df
    locatable = locatable.sort_values(by="source", key=lambda s: s.map({"seed": 0}).fillna(1))
    clusters = []  # list of dicts: {lat, lng, canonical_row, merged_merchant_names}
    for _, row in locatable.iterrows():
        lat = float(row["lat"])
        lng = float(row["lng"])
        match = next(
            (c for c in clusters
             if abs(c["lat"] - lat) < DEDUPE_RADIUS_DEGREES
             and abs(c["lng"] - lng) < DEDUPE_RADIUS_DEGREES),
            None,
        )
        visit_count = int(row.get("visit_count") or 1)
        if match:
            match["merged_merchant_names"].append(row["merchant_name_raw"])
            match["visit_count"] += visit_count
        else:
            clusters.append({
                "lat": lat, "lng": lng,
                "canonical_row": row,
                "merged_merchant_names": [row["merchant_name_raw"]],
                "visit_count": visit_count,
            })

    deduped_rows = []
    for c in clusters:
        row = c["canonical_row"].copy()
        row["merged_from"] = ", ".join(c["merged_merchant_names"])
        row["visit_count"] = int(c["visit_count"])
        deduped_rows.append(row)

    return pd.concat([pd.DataFrame(deduped_rows), unresolved], ignore_index=True)


def materialize():
    visits = query(
        "select merchant_name_raw, count(*)::integer as visit_count "
        "from raw_pub_visits group by 1"
    )
    seed = query("select * from seed_pubs")

    resolved = []
    for _, visit in visits.iterrows():
        row = resolve_merchant(visit["merchant_name_raw"], seed)
        row["visit_count"] = int(visit["visit_count"])
        resolved.append(row)
    result_df = pd.DataFrame(resolved)
    result_df = dedupe_by_proximity(result_df)
    if "visit_count" in result_df.columns:
        result_df["visit_count"] = (
            result_df["visit_count"].fillna(1).astype(int)
        )

    unresolved_count = (result_df["source"] == "unresolved").sum()
    if unresolved_count:
        print(
            f"{unresolved_count} venue(s) unresolved — review them and add rows "
            "to assets/seeds/seed_pubs.csv, then re-run."
        )
    if OFFLINE_TEST:
        print("OFFLINE_TEST=1 — skipped live geocoding, seed matches only.")

    return result_df
