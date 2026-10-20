"""Load, validate and clean the raw listing CSV before training (BLUEPRINT Part E, steps 1–5).

Nothing is dropped silently: every excluded or flagged row is listed, with its
reason, in the data-quality report. The generator's `injected_anomaly` column is
never used for cleaning decisions or as a feature; it is only used afterwards to
check how well the detectors found the problems that were planted on purpose.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from app.core.config import get_settings
from app.ml.features import count_amenities
from app.models.enums import (AreaUnit, ConversionStatus, LandClassification, LayoutApprovalStatus,
                              ListingStatus, PropertyType, RoadAccess)
from app.services.area_units import to_sqft
from app.services.geo import haversine_km

REQUIRED_COLUMNS = ["source_record_id", "property_type", "land_classification", "conversion_status",
                    "layout_approval_status", "city", "locality", "latitude", "longitude", "area_value",
                    "area_unit", "road_access", "road_frontage_ft", "is_corner_plot", "asking_price_inr",
                    "amenities", "listing_status", "plot_width_ft", "plot_length_ft"]

ENUM_COLUMNS = {
    "property_type": PropertyType, "land_classification": LandClassification,
    "conversion_status": ConversionStatus, "layout_approval_status": LayoutApprovalStatus,
    "area_unit": AreaUnit, "road_access": RoadAccess, "listing_status": ListingStatus,
}

# Listings an admin rejected (or a seller withdrew) are not treated as valid asking prices.
EXCLUDED_STATUSES = {"rejected", "archived"}

NEAR_DUP_AREA_TOL = 0.02
NEAR_DUP_PRICE_TOL = 0.02
NEAR_DUP_DISTANCE_KM = 0.1
DIMENSION_TOL = 0.10
IQR_FLAG = 1.5         # outside 1.5 x IQR of the residual: flagged and kept
EXTREME_RATIO = 5.0    # price per sq ft over 5x or under 1/5 of similar listings: typo-like, excluded
                       # from training (listed by ID in the report). Smaller deviations cannot be told
                       # apart from a genuine premium or discount, so they stay in.


@dataclass
class CleaningResult:
    clean: pd.DataFrame                      # rows used for training
    flagged: pd.DataFrame                    # row id, issue, action
    raw_rows: int
    dataset_sha256: str
    missing: pd.DataFrame                    # per-column missing counts in the raw file
    notes: list[str] = field(default_factory=list)


class SchemaError(ValueError):
    pass


def file_sha256(path: Path | list[Path]) -> str:
    paths = path if isinstance(path, list) else [path]
    if len(paths) == 1:
        return hashlib.sha256(paths[0].read_bytes()).hexdigest()
    # Several files (synthetic + real): hash of the per-file hashes, in the order given.
    return hashlib.sha256("".join(file_sha256(p) for p in paths).encode()).hexdigest()


def load_raw(path: Path | list[Path]) -> pd.DataFrame:
    """Read one raw CSV, or several with the same core columns (e.g. synthetic + real listings).
    Columns only some files have are filled with empty strings for the others."""
    paths = path if isinstance(path, list) else [path]
    df = pd.concat([pd.read_csv(p, dtype=str, keep_default_na=False) for p in paths],
                   ignore_index=True).fillna("")
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise SchemaError(f"CSV is missing required columns: {', '.join(missing_cols)}")
    return df


def _flag(rows: list, rid: str, issue: str, action: str) -> None:
    rows.append({"source_record_id": rid, "issue": issue, "action": action})


def validate_and_normalise(df: pd.DataFrame, flags: list) -> pd.DataFrame:
    """Type and enum checks, unit normalisation, range checks. Invalid rows are excluded."""
    s = get_settings()
    out = []
    for _, r in df.iterrows():
        rid = r["source_record_id"]
        bad = [c for c, enum in ENUM_COLUMNS.items() if r[c] not in {m.value for m in enum}]
        if bad:
            _flag(flags, rid, f"invalid value in {', '.join(bad)}", "excluded")
            continue
        try:
            price = float(r["asking_price_inr"])
            area_sqft = float(to_sqft(r["area_value"], r["area_unit"]))
        except (ValueError, ArithmeticError):
            _flag(flags, rid, "price or area is not a positive number", "excluded")
            continue
        if not price > 0:
            _flag(flags, rid, "price is not a positive number", "excluded")
            continue
        rec = r.to_dict()
        rec["asking_price_inr"] = price
        rec["normalized_area_sqft"] = area_sqft
        for c in ("latitude", "longitude", "road_frontage_ft", "plot_width_ft", "plot_length_ft"):
            rec[c] = float(r[c]) if r[c] != "" else math.nan
        lat, lng = rec["latitude"], rec["longitude"]
        if not (math.isnan(lat) or math.isnan(lng)) and not (
                s.geo_lat_min <= lat <= s.geo_lat_max and s.geo_lng_min <= lng <= s.geo_lng_max):
            _flag(flags, rid, "coordinates outside Karnataka", "coordinates treated as missing")
            rec["latitude"] = rec["longitude"] = math.nan
        rec["amenity_count"] = count_amenities(r["amenities"])
        out.append(rec)
    return pd.DataFrame(out)


def consistency_checks(df: pd.DataFrame, flags: list) -> None:
    """Flag (but keep) records whose declared fields contradict each other."""
    for _, r in df.iterrows():
        rid = r["source_record_id"]
        w, l = r["plot_width_ft"], r["plot_length_ft"]
        if not (math.isnan(w) or math.isnan(l)):
            dims = w * l
            if abs(dims - r["normalized_area_sqft"]) / r["normalized_area_sqft"] > DIMENSION_TOL:
                _flag(flags, rid, f"width × length ({dims:,.0f} sq ft) differs from stated area "
                                  f"({r['normalized_area_sqft']:,.0f} sq ft) by more than 10%",
                      "kept (stated area used)")
        if r["land_classification"] == "agricultural" and r["conversion_status"] == "converted_claimed":
            _flag(flags, rid, "classified agricultural but conversion claimed", "kept")
        if r["property_type"] == "agricultural_land" and r["land_classification"].startswith("non_agricultural"):
            _flag(flags, rid, "agricultural land type with non-agricultural classification", "kept")
        if r["road_access"] == "unknown":
            _flag(flags, rid, "road access unknown", "kept (imputed, indicator added)")


def near_duplicate_groups(df: pd.DataFrame) -> pd.Series:
    """Union-find over pairs with the same locality and type, area and price within 2%,
    and coordinates within 100 m. Returns a group id per row (the first record id in the group)."""
    ids = list(df["source_record_id"])
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for _, g in df.groupby(["locality", "property_type"]):
        rows = g.to_dict("records")
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                a, b = rows[i], rows[j]
                if abs(a["normalized_area_sqft"] - b["normalized_area_sqft"]) > NEAR_DUP_AREA_TOL * a["normalized_area_sqft"]:
                    continue
                if abs(a["asking_price_inr"] - b["asking_price_inr"]) > NEAR_DUP_PRICE_TOL * a["asking_price_inr"]:
                    continue
                coords = [a["latitude"], a["longitude"], b["latitude"], b["longitude"]]
                if not any(math.isnan(c) for c in coords) and haversine_km(*coords) > NEAR_DUP_DISTANCE_KM:
                    continue
                ra, rb = find(a["source_record_id"]), find(b["source_record_id"])
                if ra != rb:
                    parent[max(ra, rb)] = min(ra, rb)
    return pd.Series([find(i) for i in ids], index=df.index, name="dup_group_id")


def price_outliers(df: pd.DataFrame) -> pd.Series:
    """Residual of log(price per sq ft) against the median of similar listings (same
    locality and type, or same type when fewer than 3), scored with the IQR rule.
    Returns 0 (normal), 1 (flag) or 2 (extreme: more than 5x away from similar listings) per row."""
    lp = np.log(df["asking_price_inr"] / df["normalized_area_sqft"])
    grp = df.groupby(["locality", "property_type"])["source_record_id"].transform("count")
    med_lt = lp.groupby([df["locality"], df["property_type"]]).transform("median")
    med_t = lp.groupby(df["property_type"]).transform("median")
    resid = lp - np.where(grp >= 3, med_lt, med_t)
    q1, q3 = resid.quantile(0.25), resid.quantile(0.75)
    iqr = q3 - q1
    level = pd.Series(0, index=df.index)
    level[(resid < q1 - IQR_FLAG * iqr) | (resid > q3 + IQR_FLAG * iqr)] = 1
    level[resid.abs() > math.log(EXTREME_RATIO)] = 2
    return level


def clean(path: Path | list[Path]) -> CleaningResult:
    raw = load_raw(path)
    flags: list[dict] = []
    missing = pd.DataFrame({
        "missing": (raw == "").sum(),
        "share": ((raw == "").sum() / len(raw)).round(3),
    }).query("missing > 0").drop(index=["injected_anomaly"], errors="ignore")

    exact = raw.drop(columns=["source_record_id", "injected_anomaly"], errors="ignore").duplicated()
    for rid in raw.loc[exact, "source_record_id"]:
        _flag(flags, rid, "exact duplicate of an earlier row", "excluded")
    df = validate_and_normalise(raw[~exact], flags)

    status_excl = df["listing_status"].isin(EXCLUDED_STATUSES)
    for _, r in df[status_excl].iterrows():
        _flag(flags, r["source_record_id"], f"listing status '{r['listing_status']}'", "excluded")
    df = df[~status_excl].reset_index(drop=True)

    consistency_checks(df, flags)

    df["dup_group_id"] = near_duplicate_groups(df)
    is_extra_copy = df.duplicated("dup_group_id", keep="first")
    for _, r in df[is_extra_copy].iterrows():
        _flag(flags, r["source_record_id"], f"near-duplicate of {r['dup_group_id']}", "excluded (one copy kept)")
    df = df[~is_extra_copy].reset_index(drop=True)

    level = price_outliers(df)
    for i, r in df[level > 0].iterrows():
        extreme = level[i] == 2
        ppsf = r["asking_price_inr"] / r["normalized_area_sqft"]
        _flag(flags, r["source_record_id"],
              f"{'extreme' if extreme else 'possible'} price outlier (₹{ppsf:,.0f}/sq ft vs similar listings)",
              "excluded from training" if extreme else "kept")
    df = df[level < 2].reset_index(drop=True)

    return CleaningResult(clean=df, flagged=pd.DataFrame(flags, columns=["source_record_id", "issue", "action"]),
                          raw_rows=len(raw), dataset_sha256=file_sha256(path), missing=missing)


def detection_check(raw: pd.DataFrame, flagged: pd.DataFrame) -> pd.DataFrame:
    """How many of the generator's deliberately injected problems the detectors found.
    Only meaningful for synthetic data (genuine data has no such column)."""
    if "injected_anomaly" not in raw.columns:
        return pd.DataFrame()
    if "is_synthetic" in raw.columns:
        raw = raw[raw["is_synthetic"].str.lower() == "true"]
    planted = raw[raw["injected_anomaly"] != ""][["source_record_id", "injected_anomaly"]].copy()
    planted["kind"] = planted["injected_anomaly"].str.replace(r"near_duplicate_of:.*", "near_duplicate", regex=True)
    planted["kind"] = planted["kind"].str.replace(r"price_outlier_x.*", "price_outlier", regex=True)
    found = set(flagged["source_record_id"])
    # A near-duplicate counts as found if either copy was flagged as part of the group.
    issue_text = flagged.groupby("source_record_id")["issue"].apply(" | ".join).to_dict()

    def detected(row):
        if row["kind"] == "near_duplicate":
            return "near-duplicate" in issue_text.get(row["source_record_id"], "")
        if row["kind"] == "price_outlier":
            return "price outlier" in issue_text.get(row["source_record_id"], "")
        if row["kind"] == "dimension_mismatch":
            return "width × length" in issue_text.get(row["source_record_id"], "")
        if row["kind"] == "road_access_removed":
            return "road access unknown" in issue_text.get(row["source_record_id"], "")
        return row["source_record_id"] in found

    planted["detected"] = planted.apply(detected, axis=1)
    return planted.groupby("kind")["detected"].agg(planted="count", detected="sum").reset_index()
