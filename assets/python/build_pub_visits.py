#!/usr/bin/env python3
"""Rebuild assets/seeds/raw_pub_visits.csv from a Chase activity export.

visit_count downstream is the number of visit-log rows per merchant. This
script writes **one row per unique Transaction Date per venue**, so multiple
Chase sales on the same calendar day at the same pin count as one visit.

The Chase CSV is not committed (personal statement). Jordan classified
likely_pub=yes merchants on 2026-09-14; this mapping follows that include
list plus later address/naming overrides and the Vauxhall Marketplace
addendum. Excluded: Thomas Cubitt, Hung Drawn & Quartered, Bar Crispin,
Guinness Open Gate Brewery, Hector's, The Buccaneer (didn't play there),
Walrus / Walrus & Carpenter (didn't play there), FCB Paddington (coffee,
not a pub), Diogenes the Dog, The Chalk Freehouse, Supercute Taproom,
The Thirsty Farrier (didn't play there), The Pig and Butcher (didn't play
there).

  python3 assets/python/build_pub_visits.py \\
      --chase /path/to/Chase7977_Activity_20260830.csv
"""

from __future__ import annotations

import argparse
import csv
import html
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_PUBS = REPO_ROOT / "assets" / "seeds" / "seed_pubs.csv"
OUT_VISITS = REPO_ROOT / "assets" / "seeds" / "raw_pub_visits.csv"

# Demo / pre-Chase sample rows kept in the visit log (no statement dates).
KEPT_SAMPLE_ROWS = [
    "THE RED LION LDN",
    "DOG N BONE PH LONDON",
    "CROWN TAVERN EC1",
    "CROWN TAVERN EC1",
]

# In visits but not seed_pubs (logged, unresolved coords).
EXTRA_INCLUDED = [
    "GREENE KING",
    "FORTUNE OF WAR",
    "MAD DOG BREWERY",
    "BEBEME WINE BAR",
]

EXCLUDED_SUBSTR = (
    "THOMAS CUBITT",
    "HUNG DRAWN AND QUARTERED",
    "BAR CRISPIN",
    "GUINNESS OPEN GATE",
    "HECTOR'S",
    "HECTORS",
    "THE BUCCANEER",
    "WALRUS AND CARPENTER",
    "WALRUS",
    "FCB PADDINGTON",
    "DIOGENES",
    "CHALK FREE",
    "SUPERCUTE",
    "THIRSTY FARRIER",
    "PIG AND BUTCHER",
)

# Jordan visit-count overrides applied after unique-day counts.
VISIT_COUNT_OVERRIDES = {
    "BEEHIVE": 1,  # 2026-09-15: exactly 1 visit (Chase has 2 unique days)
}

PROCESSOR_PREFIXES = (
    r"^SQ\s*\*",
    r"^SUMUP\s*\*",
    r"^ZETTLE_\*",
    r"^ZETTLE\*",
    r"^DINES\*",
    r"^CLR\*",
    r"^TST-",
    r"^TST\s+",
)

# Truncated / processor-mangled descriptions that do not prefix-match a key.
SPECIAL_PATTERNS = (
    (re.compile(r"UNIT\s+\d+\s+VAUXHALL\s*M|MARKETPLACE\s*-\s*VAUX"), "VAUXHALL MARKETPLACE"),
    (re.compile(r"^FLORENCE\s*\(BRIXTON\)"), "FLORENCE BRIXTON"),
)


def normalize_description(desc: str) -> str:
    d = html.unescape(desc).upper()
    d = d.replace("&", "AND")
    d = d.replace("\u2019", "'").replace("`", "'")
    for pat in PROCESSOR_PREFIXES:
        d = re.sub(pat, "", d)
    return re.sub(r"\s+", " ", d).strip()


def load_merchant_keys() -> list[str]:
    keys: list[str] = []
    with SEED_PUBS.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name = row["merchant_name_raw"].strip()
            if name and name != "ANCHOR BAR":
                keys.append(name)
    keys.extend(EXTRA_INCLUDED)
    # Longest first so MC AND SONS VAUXHALL wins over MC AND SONS.
    return sorted(dict.fromkeys(keys), key=lambda k: -len(k))


def match_merchant(normalized: str, keys: list[str]) -> str | None:
    if any(ex in normalized for ex in EXCLUDED_SUBSTR):
        return None
    for pat, key in SPECIAL_PATTERNS:
        if pat.search(normalized):
            return key
    for key in keys:
        kn = key.upper().replace("&", "AND")
        if normalized == kn:
            return key
        if normalized.startswith(kn + " ") or normalized.startswith(kn + "("):
            return key
        if kn.startswith(normalized) and len(normalized) >= 12:
            return key
    return None


def unique_days_by_merchant(chase_path: Path, keys: list[str]) -> dict[str, set]:
    by_merchant: dict[str, set] = defaultdict(set)
    with chase_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if (row.get("Type") or "").strip() != "Sale":
                continue
            merchant = match_merchant(normalize_description(row["Description"]), keys)
            if not merchant:
                continue
            day = datetime.strptime(row["Transaction Date"], "%m/%d/%Y").date()
            by_merchant[merchant].add(day)
    return by_merchant


def merchant_order() -> list[str]:
    """Stable order: seed_pubs (skip ANCHOR BAR), then extra unresolved keys."""
    order: list[str] = []
    with SEED_PUBS.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name = row["merchant_name_raw"].strip()
            if name and name != "ANCHOR BAR":
                order.append(name)
    for name in EXTRA_INCLUDED:
        if name not in order:
            order.append(name)
    return order


def visit_row_count(merchant: str, days: set) -> int:
    if merchant in VISIT_COUNT_OVERRIDES:
        return VISIT_COUNT_OVERRIDES[merchant]
    return len(days)


def write_visits(by_merchant: dict[str, set]) -> list[str]:
    rows = ["merchant_name_raw", *KEPT_SAMPLE_ROWS]
    for merchant in merchant_order():
        n = visit_row_count(merchant, by_merchant.get(merchant, set()))
        rows.extend([merchant] * n)
    unexpected = sorted(set(by_merchant) - set(merchant_order()))
    for merchant in unexpected:
        n = visit_row_count(merchant, by_merchant[merchant])
        rows.extend([merchant] * n)
    OUT_VISITS.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--chase",
        type=Path,
        required=True,
        help="Chase activity CSV (Transaction Date, Description, Type, …)",
    )
    args = parser.parse_args()
    if not args.chase.exists():
        raise SystemExit(f"Chase CSV not found: {args.chase}")

    keys = load_merchant_keys()
    by_merchant = unique_days_by_merchant(args.chase, keys)
    write_visits(by_merchant)

    chase_days = sum(
        visit_row_count(merchant, days) for merchant, days in by_merchant.items()
    )
    print(f"Wrote {OUT_VISITS.relative_to(REPO_ROOT)}")
    print(f"  unique venue-days from Chase (after overrides): {chase_days}")
    print(f"  kept sample rows: {len(KEPT_SAMPLE_ROWS)}")
    print(f"  total visit-log rows: {chase_days + len(KEPT_SAMPLE_ROWS)}")
    for merchant in (
        "MC AND SONS",
        "MC AND SONS VAUXHALL",
        "VAUXHALL MARKETPLACE",
        "ANCHOR BANKSIDE",
        "THE BLACK DOG VAUX",
        "CROWN 052892",
        "MONUMENT",
        "BEEHIVE",
    ):
        days = sorted(by_merchant.get(merchant, set()))
        n = visit_row_count(merchant, by_merchant.get(merchant, set()))
        note = ""
        if merchant in VISIT_COUNT_OVERRIDES:
            note = f" (override {VISIT_COUNT_OVERRIDES[merchant]}; Chase days {len(days)})"
        print(f"  {merchant}: {n} visit row(s){note} {[str(d) for d in days]}")


if __name__ == "__main__":
    main()
