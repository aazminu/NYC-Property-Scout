"""
BBL Code Matcher Utility

Matches property addresses from rental listings JSON files with BBL codes
using NYC GeoSearch API (free, no API key required).
"""

import json
import time
import requests
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import quote
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BBLMatcher:
    """Match property addresses with BBL codes using NYC GeoSearch API."""

    def __init__(self, rate_limit_delay: float = 0.5):
        """
        Initialize BBL matcher with NYC GeoSearch API.

        Args:
            rate_limit_delay: Delay between API calls in seconds (default 0.5s)
        """
        self.api_base_url = "https://geosearch.planninglabs.nyc/v2/search"
        self.rate_limit_delay = rate_limit_delay
        self.cache: Dict[str, Optional[str]] = {}
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "NYC-Rent-Scraper-BBL-Matcher/1.0"})

    def _clean_address(self, address: str) -> str:
        """Clean address for API call."""
        if not address or address == "N/A":
            return ""

        # Remove extra whitespace
        cleaned = " ".join(address.split())
        return cleaned.strip()

    def find_bbl_by_geosearch(self, address: str) -> Optional[str]:
        """
        Find BBL code using NYC GeoSearch API.

        Args:
            address: Property address to geocode

        Returns:
            BBL code if found, None otherwise
        """
        if not address or address == "N/A":
            return None

        # Check cache first
        if address in self.cache:
            return self.cache[address]

        cleaned_address = self._clean_address(address)
        if not cleaned_address:
            return None

        try:
            # Call NYC GeoSearch API
            url = f"{self.api_base_url}?text={quote(cleaned_address)}"

            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Extract BBL from response
            if data.get("features") and len(data["features"]) > 0:
                feature = data["features"][0]
                properties = feature.get("properties", {})

                # BBL can be in different locations
                bbl = properties.get("addendum", {}).get("pad", {}).get("bbl")

                if not bbl:
                    # Try alternative locations
                    bbl = properties.get("pad_bbl") or properties.get("bbl")

                if bbl:
                    self.cache[address] = bbl
                    logger.debug(f"✓ GeoSearch: {address} -> BBL {bbl}")
                    return bbl

            # No BBL found
            self.cache[address] = None
            logger.debug(f"✗ GeoSearch: No BBL found for {address}")
            return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"API error for {address}: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.warning(f"Parse error for {address}: {e}")
            return None
        finally:
            # Rate limiting
            time.sleep(self.rate_limit_delay)

    def enrich_json_with_bbl(
        self, input_json_path: str, output_json_path: Optional[str] = None
    ) -> Dict:
        """Add BBL codes to rental listings JSON file using NYC GeoSearch API."""
        input_path = Path(input_json_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Input JSON not found at {input_json_path}")

        # Default output path
        if output_json_path is None:
            output_json_path = str(input_path.parent / f"{input_path.stem}_bbl.json")

        # Load JSON data
        with open(input_path, "r", encoding="utf-8") as f:
            listings = json.load(f)

        # Statistics
        stats = {
            "total_listings": 0,
            "with_address": 0,
            "bbl_matched": 0,
            "bbl_not_matched": 0,
            "invalid_records": 0,
        }

        logger.info(f"Starting BBL lookup for {len(listings)} listings...")
        logger.info(f"Rate limit: {self.rate_limit_delay}s between requests")
        logger.info(
            f"Estimated time: {len(listings) * self.rate_limit_delay / 60:.1f} minutes\n"
        )

        # Process each listing
        for idx, listing in enumerate(listings):
            if not isinstance(listing, dict) or len(listing) <= 1:
                stats["invalid_records"] += 1
                continue

            stats["total_listings"] += 1

            address = listing.get("address")

            if address and address != "N/A":
                stats["with_address"] += 1

                # Find BBL using GeoSearch API
                bbl = self.find_bbl_by_geosearch(address)

                if bbl:
                    listing["bbl"] = bbl
                    stats["bbl_matched"] += 1

                    # Progress reporting every 100 listings
                    if (idx + 1) % 100 == 0:
                        match_rate = (
                            stats["bbl_matched"] / stats["with_address"]
                        ) * 100
                        logger.info(
                            f"Progress: {idx + 1}/{len(listings)} | Match rate: {match_rate:.1f}%"
                        )
                else:
                    listing["bbl"] = None
                    stats["bbl_not_matched"] += 1
            else:
                listing["bbl"] = None
                stats["bbl_not_matched"] += 1

        # Save enriched data
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(listings, f, indent=2, ensure_ascii=False)

        # Log statistics
        logger.info(f"\n=== BBL Enrichment Statistics ===")
        logger.info(f"Total valid listings: {stats['total_listings']}")
        logger.info(f"Listings with address: {stats['with_address']}")
        logger.info(f"")
        logger.info(f"BBL codes matched: {stats['bbl_matched']}")
        logger.info(f"BBL codes not matched: {stats['bbl_not_matched']}")
        logger.info(f"Invalid records skipped: {stats['invalid_records']}")

        if stats["total_listings"] > 0:
            match_rate = (stats["bbl_matched"] / stats["total_listings"]) * 100
            logger.info(f"")
            logger.info(f"Overall match rate: {match_rate:.1f}%")

        logger.info(f"\nEnriched data saved to: {output_json_path}")

        return stats


def main():
    """Main function for standalone script usage."""
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python utilities/bbl_matcher.py <input_json_path> [output_json_path]"
        )
        print("\nExample:")
        print("  python utilities/bbl_matcher.py data/nyc_both_20260131_161453.json")
        print(
            "  python utilities/bbl_matcher.py data/nyc_both_20260131_161453.json data/enriched.json"
        )
        print("\nUses NYC GeoSearch API (free, no API key required)")
        sys.exit(1)

    input_json = sys.argv[1]
    output_json = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        matcher = BBLMatcher()
        stats = matcher.enrich_json_with_bbl(input_json, output_json)

        return 0
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
