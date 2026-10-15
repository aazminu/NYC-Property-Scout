"""Unit tests for NYC-Property-Scout BBL normalization, auditing, spatial comps, and valuation."""

from pathlib import Path
import pytest
from utilities.property_analytics import (
    audit_property_records,
    coerce_numeric,
    compute_investment_metrics,
    decompose_bbl,
    filter_property_records,
    find_spatial_comps,
    haversine_km,
    normalize_bbl,
)
from utilities.cli import main as cli_main


def test_normalize_and_decompose_bbl():
    assert normalize_bbl("1008350041") == "1008350041"
    assert normalize_bbl(1008350041) == "1008350041"
    assert normalize_bbl("1008350041.0") == "1008350041"
    assert normalize_bbl("1-835-41") == "1008350041"
    assert normalize_bbl("Manhattan-835-41") == "1008350041"
    assert normalize_bbl("Brooklyn/1234/56") == "3012340056"
    assert normalize_bbl("835-41", default_borough="Queens") == "4008350041"

    # Invalid BBLs (borough 0 or 6, block 0, lot 0, empty)
    assert normalize_bbl("0008350041") is None
    assert normalize_bbl("6008350041") is None
    assert normalize_bbl("1000000041") is None
    assert normalize_bbl("1008350000") is None
    assert normalize_bbl(None) is None
    assert normalize_bbl("N/A") is None

    info = decompose_bbl("3-1234-56")
    assert info == {
        "bbl": "3012340056",
        "borough_code": 3,
        "borough_name": "Brooklyn",
        "block": 1234,
        "lot": 56,
    }


def test_coerce_numeric_and_filter_property_records():
    assert coerce_numeric("$1,250,000") == 1250000.0
    assert coerce_numeric("3,450.50") == 3450.5
    assert coerce_numeric(None) is None
    assert coerce_numeric("N/A") is None

    sample = [
        {"zpid": 1, "price": "$3,200", "beds": "2", "address": "120 E 34th St, Manhattan, NY", "bbl": "1008890020"},
        {"zpid": 2, "price": None, "beds": 2, "address": "500 W 43rd St, Manhattan, NY", "bbl": "1010720001"},
        {"zpid": 3, "price": 4800, "beds": 2.0, "address": "43-12 Hunter St, Long Island City, NY", "bbl": "4004260015"},
        {"zpid": 4, "price": "N/A", "beds": 2, "address": "Brooklyn, NY", "bbl": "3010000001"},
        {"only_one_key": 1},
    ]

    # Filtering by min_price excludes None and "N/A" prices instead of letting them slip through
    res_min = filter_property_records(sample, min_price=3000, max_price=4000, beds=2)
    assert len(res_min) == 1
    assert res_min[0]["zpid"] == 1

    # Filtering by borough="Queens" matches Long Island City via BBL prefix 4
    res_queens = filter_property_records(sample, borough="Queens")
    assert len(res_queens) == 1
    assert res_queens[0]["zpid"] == 3


def test_audit_property_records_detects_mismatches_duplicates_and_outliers():
    records = [
        {"zpid": "100", "price": 500000, "sqft": 500, "address": "10 Main St, Manhattan, NY", "bbl": "1001000001"},
        {"zpid": "101", "price": 520000, "sqft": 510, "address": "12 Main St, Manhattan, NY", "bbl": "1001000002"},
        {"zpid": "102", "price": 490000, "sqft": 495, "address": "14 Main St, Manhattan, NY", "bbl": "1001000003"},
        {"zpid": "103", "price": 510000, "sqft": 505, "address": "16 Main St, Manhattan, NY", "bbl": "1001000004"},
        {"zpid": "100", "price": 9500000, "sqft": 500, "address": "99 Broadway, Brooklyn, NY", "bbl": "1002000005"},
        {"zpid": "104", "price": 400000, "sqft": 400, "address": "Queens, NY", "bbl": "INVALID-BBL"},
    ]
    report = audit_property_records(records, mad_threshold=3.0)
    assert report["total_valid_records"] == 6
    assert report["invalid_bbl_count"] == 1
    assert report["duplicate_zpids"] == ["100"]
    assert len(report["borough_mismatches"]) == 1
    assert report["borough_mismatches"][0]["address_borough"] == "Brooklyn"
    assert report["borough_mismatches"][0]["bbl_borough"] == "Manhattan"
    assert len(report["ppsf_outliers"]) == 1
    assert report["ppsf_outliers"][0]["id"] == "100"


def test_spatial_haversine_and_comps():
    # Distance between Midtown Manhattan and LIC Queens is ~3-4 km
    d = haversine_km(40.7549, -73.9840, 40.7447, -73.9485)
    assert 2.5 < d < 4.5

    subject = {"zpid": "s1", "latitude": 40.7500, "longitude": -73.9900, "beds": 2, "sqft": 900, "price": 4200}
    candidates = [
        {"zpid": "c1", "latitude": 40.7510, "longitude": -73.9890, "beds": 2, "sqft": 920, "price": 4300},
        {"zpid": "c2", "latitude": 40.7550, "longitude": -73.9800, "beds": 3, "sqft": 1400, "price": 6200},
        {"zpid": "far", "latitude": 40.6500, "longitude": -73.9500, "beds": 2, "sqft": 900, "price": 3100},
    ]
    comps = find_spatial_comps(subject, candidates, max_radius_km=2.0, top_k=5)
    assert len(comps) == 2
    assert comps[0]["zpid"] == "c1"
    assert comps[0]["similarity_score"] > comps[1]["similarity_score"]


def test_compute_investment_metrics_and_cli():
    metrics = compute_investment_metrics(
        purchase_price=800000,
        monthly_rent=5500,
        annual_property_tax=7200,
        monthly_common_charges=500,
        vacancy_rate=0.05,
        down_payment_pct=0.25,
        annual_interest_rate=0.06,
        loan_term_years=30,
    )
    assert metrics["gross_annual_rent"] == 66000.0
    assert metrics["noi"] > 40000.0
    assert 5.0 < metrics["cap_rate_pct"] < 8.0
    assert metrics["price_to_rent_ratio"] == round(800000 / 66000, 2)

    with pytest.raises(ValueError):
        compute_investment_metrics(purchase_price=0, monthly_rent=3000)

    assert cli_main(["bbl", "Manhattan-835-41"]) == 0
    assert cli_main(["valuate", "--price", "900000", "--rent", "5200"]) == 0

    data_file = Path(__file__).resolve().parent.parent / "data" / "nyc_both_20260131_161453_bbl.json"
    if data_file.exists():
        assert cli_main(["audit", "--file", str(data_file)]) == 0
