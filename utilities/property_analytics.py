"""
NYC Property Scout - Canonical BBL Normalization, Data Quality Discrepancy Auditor,
Spatial Haversine Comparable Matcher, and Cap-Rate / NOI Investment Valuation Engine.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

BOROUGH_CODE_TO_NAME: Dict[int, str] = {
    1: "Manhattan",
    2: "Bronx",
    3: "Brooklyn",
    4: "Queens",
    5: "Staten Island",
}

BOROUGH_NAME_TO_CODE: Dict[str, int] = {
    "manhattan": 1,
    "new york": 1,
    "ny": 1,
    "mn": 1,
    "bronx": 2,
    "the bronx": 2,
    "bx": 2,
    "brooklyn": 3,
    "kings": 3,
    "bk": 3,
    "queens": 4,
    "qn": 4,
    "long island city": 4,
    "astoria": 4,
    "flushing": 4,
    "staten island": 5,
    "richmond": 5,
    "si": 5,
}


def coerce_numeric(value: Any) -> Optional[float]:
    """Coerce currency/formatted strings or numbers into a finite float."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, str):
        cleaned = re.sub(r"[^0-9.\-]", "", value.replace(",", "").strip())
        if not cleaned or cleaned in ("-", ".", "-."):
            return None
        try:
            num = float(cleaned)
            return num if math.isfinite(num) else None
        except ValueError:
            return None
    return None


def normalize_bbl(raw_bbl: Any, default_borough: Optional[str] = None) -> Optional[str]:
    """
    Normalize a raw NYC Borough-Block-Lot (BBL) identifier into a canonical 10-digit string:
    1-digit Borough (1..5) + 5-digit zero-padded Block + 4-digit zero-padded Lot.
    Supports:
    - 10-digit integers/strings: "1008350041"
    - Hyphenated/slashed strings: "1-835-41", "Manhattan-835-41", "3/01234/0056"
    """
    if raw_bbl is None or isinstance(raw_bbl, bool):
        return None

    s = str(raw_bbl).strip()
    if not s or s.lower() in ("none", "null", "n/a", "nan"):
        return None

    # Handle float strings like "1008350041.0"
    if re.fullmatch(r"\d{10}\.0+", s):
        s = s.split(".")[0]

    if re.fullmatch(r"\d{10}", s):
        b_code = int(s[0])
        block = int(s[1:6])
        lot = int(s[6:10])
        if b_code in BOROUGH_CODE_TO_NAME and block > 0 and lot > 0:
            return f"{b_code}{block:05d}{lot:04d}"
        return None

    parts = [p.strip() for p in re.split(r"[\-/:,\s]+", s) if p.strip()]
    if len(parts) == 3:
        b_part, blk_part, lot_part = parts
        b_code: Optional[int] = None
        if b_part.isdigit():
            b_code = int(b_part)
        else:
            b_code = BOROUGH_NAME_TO_CODE.get(b_part.lower())

        if b_code in BOROUGH_CODE_TO_NAME and blk_part.isdigit() and lot_part.isdigit():
            block = int(blk_part)
            lot = int(lot_part)
            if 0 < block <= 99999 and 0 < lot <= 9999:
                return f"{b_code}{block:05d}{lot:04d}"

    elif len(parts) == 2 and default_borough:
        b_code = BOROUGH_NAME_TO_CODE.get(default_borough.strip().lower())
        blk_part, lot_part = parts
        if b_code in BOROUGH_CODE_TO_NAME and blk_part.isdigit() and lot_part.isdigit():
            block = int(blk_part)
            lot = int(lot_part)
            if 0 < block <= 99999 and 0 < lot <= 9999:
                return f"{b_code}{block:05d}{lot:04d}"

    return None


def decompose_bbl(bbl: Any) -> Optional[Dict[str, Any]]:
    """Decompose a valid BBL into borough code, borough name, block, and lot."""
    norm = normalize_bbl(bbl)
    if not norm:
        return None
    b_code = int(norm[0])
    return {
        "bbl": norm,
        "borough_code": b_code,
        "borough_name": BOROUGH_CODE_TO_NAME[b_code],
        "block": int(norm[1:6]),
        "lot": int(norm[6:10]),
    }


def infer_borough_from_address(address: str) -> Optional[int]:
    """Infer NYC borough code (1..5) from an address string."""
    if not address or not isinstance(address, str):
        return None
    lower = address.lower()
    for token, code in [
        ("manhattan", 1),
        ("bronx", 2),
        ("brooklyn", 3),
        ("queens", 4),
        ("long island city", 4),
        ("astoria", 4),
        ("flushing", 4),
        ("forest hills", 4),
        ("jamaica", 4),
        ("staten island", 5),
        ("new york, ny", 1),
    ]:
        if token in lower:
            return code
    return None


def filter_property_records(
    properties: List[Any],
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    beds: Optional[int] = None,
    borough: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Safely filter property records with numeric coercion for price/beds and
    canonical borough matching (either via BBL prefix or address).
    """
    filtered: List[Dict[str, Any]] = []
    target_b_code = BOROUGH_NAME_TO_CODE.get(borough.strip().lower()) if borough else None

    for prop in properties:
        if not isinstance(prop, dict) or len(prop) <= 1:
            continue

        price = coerce_numeric(prop.get("price"))
        if min_price is not None:
            if price is None or price <= 0 or price < min_price:
                continue
        if max_price is not None:
            if price is None or price <= 0 or price > max_price:
                continue

        if beds is not None:
            prop_beds = coerce_numeric(prop.get("beds"))
            if prop_beds is None or int(round(prop_beds)) != int(beds):
                continue

        if borough:
            address = str(prop.get("address") or "").lower()
            bbl_info = decompose_bbl(prop.get("bbl"))
            bbl_match = (
                target_b_code is not None
                and bbl_info is not None
                and bbl_info["borough_code"] == target_b_code
            )
            addr_match = borough.strip().lower() in address
            if not (bbl_match or addr_match):
                continue

        filtered.append(prop)

    return filtered


def audit_property_records(records: List[Any], mad_threshold: float = 3.5) -> Dict[str, Any]:
    """
    Audit a NYC property dataset for schema completeness, invalid BBL codes,
    duplicate ZPIDs, borough-vs-BBL mismatches, and MAD price-per-sqft outliers.
    """
    valid_records = [r for r in (records or []) if isinstance(r, dict) and len(r) > 1]
    seen_zpids = set()
    duplicate_zpids: List[str] = []
    missing_bbl_count = 0
    invalid_bbl_count = 0
    borough_mismatches: List[Dict[str, Any]] = []
    ppsf_entries: List[Tuple[str, float]] = []

    for idx, rec in enumerate(valid_records):
        rec_id = str(rec.get("zpid") or rec.get("id") or f"row-{idx}")
        if rec.get("zpid") is not None:
            z = str(rec.get("zpid"))
            if z in seen_zpids:
                duplicate_zpids.append(z)
            seen_zpids.add(z)

        raw_bbl = rec.get("bbl")
        if raw_bbl is None or str(raw_bbl).strip() == "":
            missing_bbl_count += 1
        else:
            norm = normalize_bbl(raw_bbl)
            if norm is None:
                invalid_bbl_count += 1
            else:
                addr_b = infer_borough_from_address(str(rec.get("address") or ""))
                bbl_b = int(norm[0])
                if addr_b is not None and addr_b != bbl_b:
                    borough_mismatches.append(
                        {
                            "id": rec_id,
                            "address": rec.get("address"),
                            "bbl": norm,
                            "address_borough": BOROUGH_CODE_TO_NAME[addr_b],
                            "bbl_borough": BOROUGH_CODE_TO_NAME[bbl_b],
                        }
                    )

        price = coerce_numeric(rec.get("price"))
        sqft = coerce_numeric(rec.get("sqft") or rec.get("livingArea"))
        if price and price > 0 and sqft and sqft >= 150:
            ppsf_entries.append((rec_id, price / sqft))

    # Robust MAD outlier detection on price-per-sqft
    ppsf_outliers: List[Dict[str, Any]] = []
    median_ppsf: Optional[float] = None
    if ppsf_entries:
        vals = sorted(v for _, v in ppsf_entries)
        mid = len(vals) // 2
        median_ppsf = (vals[mid - 1] + vals[mid]) / 2.0 if len(vals) % 2 == 0 else vals[mid]
        abs_devs = sorted(abs(v - median_ppsf) for v in vals)
        mad = (abs_devs[mid - 1] + abs_devs[mid]) / 2.0 if len(abs_devs) % 2 == 0 else abs_devs[mid]
        sigma = mad * 1.4826
        if sigma > 1e-6:
            for rec_id, ppsf in ppsf_entries:
                z = abs(ppsf - median_ppsf) / sigma
                if z >= mad_threshold:
                    ppsf_outliers.append(
                        {
                            "id": rec_id,
                            "ppsf": round(ppsf, 2),
                            "mad_zscore": round(z, 3),
                        }
                    )

    total = len(valid_records)
    valid_bbl_count = total - missing_bbl_count - invalid_bbl_count
    bbl_coverage_pct = round((valid_bbl_count / total) * 100.0, 2) if total > 0 else 0.0

    return {
        "total_valid_records": total,
        "skipped_empty_records": len(records or []) - total,
        "valid_bbl_count": valid_bbl_count,
        "missing_bbl_count": missing_bbl_count,
        "invalid_bbl_count": invalid_bbl_count,
        "bbl_coverage_pct": bbl_coverage_pct,
        "duplicate_zpids": duplicate_zpids,
        "borough_mismatches": borough_mismatches,
        "median_ppsf": round(median_ppsf, 2) if median_ppsf is not None else None,
        "ppsf_outliers": ppsf_outliers,
    }


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance in kilometers between two WGS84 coordinates."""
    r = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def find_spatial_comps(
    subject: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    max_radius_km: float = 2.5,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Find top-K comparable properties within max_radius_km weighted by spatial and bedroom proximity."""
    s_lat = coerce_numeric(subject.get("latitude") or subject.get("lat"))
    s_lon = coerce_numeric(subject.get("longitude") or subject.get("lng") or subject.get("lon"))
    if s_lat is None or s_lon is None:
        return []

    s_beds = coerce_numeric(subject.get("beds"))
    s_sqft = coerce_numeric(subject.get("sqft"))
    s_id = str(subject.get("zpid") or subject.get("bbl") or "")

    scored: List[Dict[str, Any]] = []
    for cand in candidates:
        if not isinstance(cand, dict):
            continue
        c_id = str(cand.get("zpid") or cand.get("bbl") or "")
        if s_id and c_id == s_id:
            continue

        c_lat = coerce_numeric(cand.get("latitude") or cand.get("lat"))
        c_lon = coerce_numeric(cand.get("longitude") or cand.get("lng") or cand.get("lon"))
        c_price = coerce_numeric(cand.get("price"))
        if c_lat is None or c_lon is None or c_price is None or c_price <= 0:
            continue

        dist_km = haversine_km(s_lat, s_lon, c_lat, c_lon)
        if dist_km > max_radius_km:
            continue

        bed_penalty = 0.0
        c_beds = coerce_numeric(cand.get("beds"))
        if s_beds is not None and c_beds is not None:
            bed_penalty = abs(s_beds - c_beds) * 0.25

        sqft_penalty = 0.0
        c_sqft = coerce_numeric(cand.get("sqft"))
        if s_sqft and s_sqft > 0 and c_sqft and c_sqft > 0:
            sqft_penalty = abs(s_sqft - c_sqft) / s_sqft

        similarity = 1.0 / (1.0 + dist_km + bed_penalty + sqft_penalty)
        scored.append(
            {
                **cand,
                "distance_km": round(dist_km, 4),
                "similarity_score": round(similarity, 4),
            }
        )

    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    return scored[:top_k]


def compute_investment_metrics(
    purchase_price: float,
    monthly_rent: float,
    annual_property_tax: Optional[float] = None,
    monthly_common_charges: float = 0.0,
    vacancy_rate: float = 0.05,
    maintenance_pct_of_rent: float = 0.08,
    down_payment_pct: float = 0.20,
    annual_interest_rate: float = 0.065,
    loan_term_years: int = 30,
) -> Dict[str, float]:
    """
    Calculate NYC residential investment metrics:
    Gross Rental Yield, Net Operating Income (NOI), Cap Rate, Annual Debt Service,
    Cash-on-Cash Return, and Price-to-Rent Ratio.
    """
    if purchase_price <= 0 or monthly_rent < 0:
        raise ValueError("purchase_price must be > 0 and monthly_rent must be >= 0")

    gross_annual_rent = monthly_rent * 12.0
    effective_gross_income = gross_annual_rent * (1.0 - max(0.0, min(1.0, vacancy_rate)))

    est_tax = (
        annual_property_tax
        if annual_property_tax is not None and annual_property_tax >= 0
        else purchase_price * 0.0115
    )
    annual_common = max(0.0, monthly_common_charges) * 12.0
    annual_maintenance = gross_annual_rent * max(0.0, maintenance_pct_of_rent)
    operating_expenses = est_tax + annual_common + annual_maintenance

    noi = effective_gross_income - operating_expenses
    gross_yield_pct = (gross_annual_rent / purchase_price) * 100.0
    cap_rate_pct = (noi / purchase_price) * 100.0

    # Mortgage amortization
    down_payment = purchase_price * max(0.01, min(1.0, down_payment_pct))
    loan_principal = max(0.0, purchase_price - down_payment)
    n_months = max(1, loan_term_years * 12)
    r_month = max(0.0, annual_interest_rate) / 12.0

    if loan_principal == 0:
        monthly_debt = 0.0
    elif r_month == 0:
        monthly_debt = loan_principal / n_months
    else:
        factor = (1.0 + r_month) ** n_months
        monthly_debt = loan_principal * (r_month * factor) / (factor - 1.0)

    annual_debt_service = monthly_debt * 12.0
    annual_cash_flow = noi - annual_debt_service
    closing_costs = purchase_price * 0.03
    total_cash_invested = down_payment + closing_costs
    cash_on_cash_pct = (annual_cash_flow / total_cash_invested) * 100.0 if total_cash_invested > 0 else 0.0
    price_to_rent_ratio = purchase_price / gross_annual_rent if gross_annual_rent > 0 else float("inf")

    return {
        "gross_annual_rent": round(gross_annual_rent, 2),
        "effective_gross_income": round(effective_gross_income, 2),
        "operating_expenses": round(operating_expenses, 2),
        "noi": round(noi, 2),
        "gross_yield_pct": round(gross_yield_pct, 2),
        "cap_rate_pct": round(cap_rate_pct, 2),
        "annual_debt_service": round(annual_debt_service, 2),
        "annual_cash_flow": round(annual_cash_flow, 2),
        "cash_on_cash_pct": round(cash_on_cash_pct, 2),
        "price_to_rent_ratio": round(price_to_rent_ratio, 2),
    }
