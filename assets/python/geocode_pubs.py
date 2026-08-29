"""@bruin
name: mart_pub_locations
type: python
depends:
  - raw_pub_visits
  - seed_pubs
materialization:
  type: table
@bruin"""

# Resolves each distinct merchant name in raw_pub_visits to a confirmed pub
# location, in priority order:
#   1. seed_pubs.csv        (manual, free, highest trust)
#   2. OpenStreetMap Nominatim (free, no key)
#   3. Google Places Text Search (needs GOOGLE_PLACES_API_KEY, small free tier)
#   4. unresolved            (flagged for you to review and add to the seed)
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

# Nominatim's usage policy requires a real identifying User-Agent and max 1 req/sec.
HEADERS = {"User-Agent": "yahtzee-analytics-personal-project (contact: you@example.com)"}

PUB_OSM_CLASSES = {"pub", "bar", "biergarten"}
PUB_GOOGLE_TYPES = {"bar", "night_club"}  # Google has no distinct "pub" type


def try_seed(merchant: str, seed_df: pd.DataFrame):
    match = seed_df[seed_df["merchant_name_raw"] == merchant]
    if not match.empty and pd.notna(match.iloc[0]["lat"]):
        row = match.iloc[0]
        return {
            "pub_name": row["pub_name"],
            "lat": row["lat"],
            "lng": row["lng"],
            "source": "seed",
            "is_confirmed_pub": True,
        }
    return None


def try_nominatim(merchant: str):
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
    if not GOOGLE_API_KEY:
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


def main():
    visits = query("select distinct merchant_name_raw from raw_pub_visits")
    seed = query("select * from seed_pubs")

    resolved = [resolve_merchant(m, seed) for m in visits["merchant_name_raw"]]
    result_df = pd.DataFrame(resolved)

    unresolved_count = (result_df["source"] == "unresolved").sum()
    if unresolved_count:
        print(
            f"{unresolved_count} venue(s) unresolved — review them and add rows "
            "to assets/seeds/seed_pubs.csv, then re-run."
        )

    return result_df


# Bruin python assets: the last expression / a `df`-returning main() pattern
# materializes the table. If your installed Bruin version expects an explicit
# global instead, assign it directly: df = main()
df = main()
