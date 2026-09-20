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
# (visit_count is unique calendar days per merchant: one visit-log row per
# Transaction Date at that venue, then summed on proximity-dedup).
#
# Locations come from seed_pubs.csv only (lat/lng already in the seed).
# There is no live Nominatim / Google Places lookup and no API key.
# Merchants without a seed match stay unresolved (flagged for review).
#
# Then dedupes by physical proximity: "Anchor Bar" (seed) and
# "Anchor Bankside (South" (a card-statement merchant string) are different
# text but the same building — string similarity alone won't reliably catch
# that (fuzzy name matching is fooled by chain pub naming and abbreviations
# just as easily as it's helped by them). Instead, once each merchant string
# has *coordinates* (from the seed), venues within ~50m of each other are
# treated as the same physical pub and collapsed to one row, keeping the
# seed's name/coords as authoritative. Distinct seed pubs with different
# pub_name values are never collapsed. The Derby and Hanover Arms are the
# identity exception that motivated that rule (~30m neighbors on Kennington
# Park Road).

import pandas as pd

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


def resolve_merchant(merchant: str, seed_df: pd.DataFrame) -> dict:
    result = try_seed(merchant, seed_df)
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


# Identity exception: these seed pub_name values must never share a pin,
# even when their coordinates fall inside DEDUPE_RADIUS_DEGREES.
KEEP_DISTINCT_SEED_PUB_NAMES = frozenset({"The Derby", "The Hanover Arms"})


def _keep_seed_pubs_distinct(canonical, new_row) -> bool:
    """Neighboring but separately seeded pubs must stay on the map.

    Same-name seed aliases (Anchor Bar / ANCHOR BANKSIDE) still merge.
    Different seed pub_name values never merge — including the Derby /
    Hanover Arms pair on Kennington Park Road.
    """
    if canonical.get("source") != "seed" or new_row.get("source") != "seed":
        return False
    left = str(canonical.get("pub_name") or "").strip()
    right = str(new_row.get("pub_name") or "").strip()
    if not left or not right:
        return False
    if frozenset({left, right}) == KEEP_DISTINCT_SEED_PUB_NAMES:
        return True
    return left != right


def dedupe_by_proximity(df: pd.DataFrame) -> pd.DataFrame:
    """Collapses rows whose coordinates are within DEDUPE_RADIUS_DEGREES of
    each other into a single pub, preferring a seed-sourced row's name/coords
    as the canonical one when a seed match is in the cluster.

    Two seed rows with different pub_name values are never merged, so
    neighbors like The Derby and Hanover Arms stay distinct.
    """
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
             and abs(c["lng"] - lng) < DEDUPE_RADIUS_DEGREES
             and not _keep_seed_pubs_distinct(c["canonical_row"], row)),
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
    from bruin import query

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

    unresolved = result_df[result_df["source"] == "unresolved"]
    if not unresolved.empty:
        print(
            f"{len(unresolved)} venue(s) unresolved — review them and add rows "
            "to assets/seeds/seed_pubs.csv, then re-run."
        )
        for name in unresolved["merchant_name_raw"].tolist():
            print(f"  - {name}")

    return result_df
