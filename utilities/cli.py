"""CLI entrypoint for NYC-Property-Scout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from utilities.property_analytics import (
    audit_property_records,
    compute_investment_metrics,
    decompose_bbl,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nyc-property-scout", description="NYC Property Scout analytics CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_bbl = sub.add_parser("bbl", help="Normalize and decompose a NYC Borough-Block-Lot identifier")
    p_bbl.add_argument("raw_bbl", help="Raw BBL string or integer (e.g., 'Manhattan-835-41' or '1008350041')")

    p_val = sub.add_parser("valuate", help="Compute NYC property cap-rate, NOI, and cash-on-cash return")
    p_val.add_argument("--price", type=float, required=True, help="Purchase price in USD")
    p_val.add_argument("--rent", type=float, required=True, help="Monthly rent in USD")
    p_val.add_argument("--common", type=float, default=450.0, help="Monthly common charges / HOA")

    p_aud = sub.add_parser("audit", help="Run data quality & BBL discrepancy audit on property JSON")
    p_aud.add_argument(
        "--file",
        default=str(Path(__file__).resolve().parent.parent / "data" / "nyc_both_20260131_161453_bbl.json"),
        help="Path to property JSON file",
    )

    args = parser.parse_args(argv)
    if args.cmd == "bbl":
        res = decompose_bbl(args.raw_bbl)
        print(json.dumps(res, indent=2))
        return 0 if res else 1
    elif args.cmd == "valuate":
        metrics = compute_investment_metrics(
            purchase_price=args.price,
            monthly_rent=args.rent,
            monthly_common_charges=args.common,
        )
        print(json.dumps(metrics, indent=2))
        return 0
    elif args.cmd == "audit":
        with open(args.file, "r", encoding="utf-8") as f:
            data = json.load(f)
        report = audit_property_records(data)
        print(json.dumps(report, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
