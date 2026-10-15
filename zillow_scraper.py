#!/usr/bin/env python3
"""
Zillow NYC Scraper
==================
Scrapes rental and for-sale listings from Zillow for New York City.

Usage:
    python zillow_scraper.py --type rent --pages 2
    python zillow_scraper.py --type sale --pages 2
    python zillow_scraper.py --type both --pages 2
"""

import argparse
import json
import os
import random
import re
import time
from datetime import datetime
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


class ZillowScraper:
    """Scraper for Zillow NYC listings with anti-detection measures."""

    BASE_URL = "https://www.zillow.com"

    # NYC search URLs
    RENT_URL = "https://www.zillow.com/new-york-ny/rentals"
    SALE_URL = "https://www.zillow.com/new-york-ny"

    def __init__(self, delay_range: tuple = (3, 7)):
        """
        Initialize the scraper.

        Args:
            delay_range: Tuple of (min, max) seconds to wait between requests
        """
        self.delay_range = delay_range
        self.ua = UserAgent()
        self.session = requests.Session()
        self.data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(self.data_dir, exist_ok=True)

    def _get_headers(self) -> dict:
        """Generate realistic browser headers with rotating user-agent."""
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    def _random_delay(self):
        """Add random delay between requests to avoid detection."""
        delay = random.uniform(*self.delay_range)
        print(f"  Waiting {delay:.1f} seconds...")
        time.sleep(delay)

    def _extract_json_data(self, html: str) -> Optional[dict]:
        """
        Extract JSON data embedded in the page.
        Zillow embeds property data in script tags.
        """
        soup = BeautifulSoup(html, "lxml")

        # Look for the main data script
        scripts = soup.find_all("script", {"type": "application/json"})
        for script in scripts:
            try:
                data = json.loads(script.string)
                if "cat1" in str(data) or "listResults" in str(data):
                    return data
            except (json.JSONDecodeError, TypeError):
                continue

        # Alternative: Look for __NEXT_DATA__ script
        next_data = soup.find("script", {"id": "__NEXT_DATA__"})
        if next_data:
            try:
                return json.loads(next_data.string)
            except (json.JSONDecodeError, TypeError):
                pass

        return None

    def _parse_listings_from_json(self, json_data: dict, listing_type: str) -> list:
        """
        Parse listings from Zillow's JSON data structure.

        Args:
            json_data: Raw JSON data from the page
            listing_type: Either 'rent' or 'sale'
        """
        listings = []

        # Navigate through potential JSON structures
        try:
            # Try different JSON paths that Zillow uses
            search_results = None

            # Path 1: props -> pageProps -> searchPageState
            if "props" in json_data:
                page_props = json_data.get("props", {}).get("pageProps", {})
                search_state = page_props.get("searchPageState", {})
                cat1 = search_state.get("cat1", {})
                search_results = cat1.get("searchResults", {}).get("listResults", [])

            # Path 2: Direct searchResults
            if not search_results and "searchResults" in json_data:
                search_results = json_data.get("searchResults", {}).get(
                    "listResults", []
                )

            # Path 3: cat1 -> searchResults
            if not search_results and "cat1" in json_data:
                search_results = (
                    json_data.get("cat1", {})
                    .get("searchResults", {})
                    .get("listResults", [])
                )

            if not search_results:
                print("  Warning: Could not find listing data in JSON")
                return listings

            for item in search_results:
                # Check if this is a multi-unit building
                units = item.get("units", [])
                if units:
                    # Extract each unit as a separate listing
                    base_address = item.get("address", "")
                    building_name = item.get("buildingName", "")
                    lat_long = item.get("latLong", {})
                    base_url = item.get("detailUrl", "")
                    if base_url and not base_url.startswith("http"):
                        base_url = self.BASE_URL + base_url

                    # Get building photo
                    building_photo = item.get("imgSrc", "N/A")
                    
                    for unit in units:
                        unit_listing = self._parse_unit(
                            unit,
                            base_address,
                            building_name,
                            lat_long,
                            base_url,
                            listing_type,
                            building_photo,
                        )
                        if unit_listing:
                            listings.append(unit_listing)
                else:
                    # Single property listing
                    listing = self._parse_single_listing(item, listing_type)
                    if listing:
                        listings.append(listing)

        except Exception as e:
            print(f"  Error parsing JSON: {e}")

        return listings

    def _parse_unit(
        self,
        unit: dict,
        base_address: str,
        building_name: str,
        lat_long: dict,
        base_url: str,
        listing_type: str,
        photo_url: str = "N/A",
    ) -> Optional[dict]:
        """Parse a single unit from a multi-unit building."""
        try:
            # Price
            price = unit.get("price", "N/A")
            if isinstance(price, str):
                price = (
                    price.replace("$", "")
                    .replace(",", "")
                    .replace("+", "")
                    .replace("/mo", "")
                    .strip()
                )

            # Unit details
            beds = unit.get("beds", "N/A")
            baths = unit.get("baths", "N/A")
            sqft = unit.get("sqft", "N/A")

            return {
                "address": base_address,
                "building_name": building_name,
                "price": price,
                "beds": beds,
                "baths": baths,
                "sqft": sqft,
                "property_type": "MULTI_UNIT",
                "status": "For Rent" if listing_type == "rent" else "For Sale",
                "latitude": lat_long.get("latitude", "N/A"),
                "longitude": lat_long.get("longitude", "N/A"),
                "zpid": "N/A",
                "url": base_url,
                "photo_url": photo_url,
                "listing_type": listing_type,
                "scraped_at": datetime.now().isoformat(),
            }
        except Exception as e:
            print(f"  Error parsing unit: {e}")
            return None

    def _parse_single_listing(self, item: dict, listing_type: str) -> Optional[dict]:
        """Parse a single listing item."""
        try:
            # Zillow often nests data under hdpData.homeInfo
            hdp_data = item.get("hdpData", {})
            home_info = hdp_data.get("homeInfo", {})

            # Extract address - check multiple paths
            address = (
                item.get("address")
                or item.get("addressStreet")
                or home_info.get("streetAddress", "")
                + ", "
                + home_info.get("city", "")
                + ", "
                + home_info.get("state", "")
                or "N/A"
            )

            # Price handling - check multiple paths
            price = (
                item.get("price")
                or item.get("unformattedPrice")
                or home_info.get("price")
                or "N/A"
            )
            if isinstance(price, str):
                price = (
                    price.replace("$", "")
                    .replace(",", "")
                    .replace("+", "")
                    .replace("/mo", "")
                    .strip()
                )

            # Property details - check multiple paths
            beds = item.get("beds") or home_info.get("bedrooms") or "N/A"
            baths = item.get("baths") or home_info.get("bathrooms") or "N/A"
            sqft = (
                item.get("area")
                or item.get("livingArea")
                or home_info.get("livingArea")
                or "N/A"
            )

            # Property type
            property_type = (
                item.get("propertyType")
                or item.get("homeType")
                or home_info.get("homeType")
                or "N/A"
            )

            # Listing URL
            detail_url = item.get("detailUrl", "")
            if detail_url and not detail_url.startswith("http"):
                detail_url = self.BASE_URL + detail_url

            # Status text
            status = item.get("statusText", item.get("statusType", ""))

            # Lat/Long - check multiple paths
            lat_long = item.get("latLong", {})
            lat = lat_long.get("latitude") or home_info.get("latitude") or "N/A"
            lng = lat_long.get("longitude") or home_info.get("longitude") or "N/A"

            # Additional useful fields
            zpid = item.get("zpid") or home_info.get("zpid") or "N/A"
            
            # Photo URL - check multiple paths
            photo_url = (
                item.get("imgSrc")
                or item.get("mediumImageLink")
                or home_info.get("hiResLink")
                or "N/A"
            )
            # Also try to get carousel photos if available
            carousel = item.get("carouselPhotos", [])
            if carousel and isinstance(carousel, list) and len(carousel) > 0:
                photo_url = carousel[0].get("url", photo_url)

            return {
                "address": address,
                "price": price,
                "beds": beds,
                "baths": baths,
                "sqft": sqft,
                "property_type": property_type,
                "status": status,
                "latitude": lat,
                "longitude": lng,
                "zpid": zpid,
                "url": detail_url,
                "photo_url": photo_url,
                "listing_type": listing_type,
                "scraped_at": datetime.now().isoformat(),
            }
        except Exception as e:
            print(f"  Error parsing listing: {e}")
            return None

    def _parse_listings_from_html(self, html: str, listing_type: str) -> list:
        """
        Fallback: Parse listings directly from HTML if JSON fails.
        """
        listings = []
        soup = BeautifulSoup(html, "lxml")

        # Find listing cards
        cards = soup.find_all("article", {"data-test": "property-card"})
        if not cards:
            cards = soup.find_all(
                "div", class_=re.compile(r"ListItem|property-card|StyledPropertyCard")
            )

        for card in cards:
            try:
                # Address
                address_elem = card.find("address") or card.find(
                    attrs={"data-test": "property-card-addr"}
                )
                address = address_elem.get_text(strip=True) if address_elem else "N/A"

                # Price
                price_elem = card.find(
                    attrs={"data-test": "property-card-price"}
                ) or card.find(class_=re.compile(r"Price"))
                price = price_elem.get_text(strip=True) if price_elem else "N/A"
                price = (
                    price.replace("$", "")
                    .replace(",", "")
                    .replace("+", "")
                    .replace("/mo", "")
                    .strip()
                )

                # Details (beds, baths, sqft)
                details_elem = card.find_all("li") or card.find_all("b")
                beds, baths, sqft = "N/A", "N/A", "N/A"

                for detail in details_elem:
                    text = detail.get_text(strip=True).lower()
                    if "bd" in text or "bed" in text:
                        beds = re.search(r"(\d+)", text)
                        beds = beds.group(1) if beds else "N/A"
                    elif "ba" in text:
                        baths = re.search(r"([\d.]+)", text)
                        baths = baths.group(1) if baths else "N/A"
                    elif "sqft" in text or "sq" in text:
                        sqft = re.search(r"([\d,]+)", text)
                        sqft = sqft.group(1).replace(",", "") if sqft else "N/A"

                # URL
                link = card.find("a", href=True)
                url = link["href"] if link else ""
                if url and not url.startswith("http"):
                    url = self.BASE_URL + url

                # Photo URL
                img = card.find("img", src=True)
                photo_url = img["src"] if img else "N/A"

                listings.append(
                    {
                        "address": address,
                        "price": price,
                        "beds": beds,
                        "baths": baths,
                        "sqft": sqft,
                        "property_type": "N/A",
                        "status": "N/A",
                        "latitude": "N/A",
                        "longitude": "N/A",
                        "url": url,
                        "photo_url": photo_url,
                        "listing_type": listing_type,
                        "scraped_at": datetime.now().isoformat(),
                    }
                )
            except Exception as e:
                print(f"  Error parsing card: {e}")
                continue

        return listings

    def scrape_page(self, url: str, listing_type: str) -> list:
        """
        Scrape a single page of listings.

        Args:
            url: URL to scrape
            listing_type: 'rent' or 'sale'

        Returns:
            List of listing dictionaries
        """
        print(f"  Fetching: {url}")

        try:
            response = self.session.get(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()

            # Try JSON extraction first
            json_data = self._extract_json_data(response.text)
            if json_data:
                listings = self._parse_listings_from_json(json_data, listing_type)
                if listings:
                    print(f"  Found {len(listings)} listings from JSON")
                    return listings

            # Fallback to HTML parsing
            listings = self._parse_listings_from_html(response.text, listing_type)
            print(f"  Found {len(listings)} listings from HTML")
            return listings

        except requests.exceptions.RequestException as e:
            print(f"  Request error: {e}")
            return []

    def scrape(self, listing_type: str = "rent", num_pages: int = 1) -> pd.DataFrame:
        """
        Scrape multiple pages of listings.

        Args:
            listing_type: 'rent', 'sale', or 'both'
            num_pages: Number of pages to scrape

        Returns:
            DataFrame with all listings
        """
        all_listings = []

        types_to_scrape = []
        if listing_type in ("rent", "both"):
            types_to_scrape.append(("rent", self.RENT_URL))
        if listing_type in ("sale", "both"):
            types_to_scrape.append(("sale", self.SALE_URL))

        for ltype, base_url in types_to_scrape:
            print(f"\n{'='*50}")
            print(f"Scraping NYC {ltype.upper()} listings...")
            print(f"{'='*50}")

            for page in range(1, num_pages + 1):
                print(f"\nPage {page}/{num_pages}:")

                # Construct page URL
                # if page == 1:
                #     url = base_url + "/"
                # else:
                url = f"{base_url}/{page}_p/"

                listings = self.scrape_page(url, ltype)
                all_listings.extend(listings)

                # Random delay between pages
                if page < num_pages:
                    self._random_delay()

        # Convert to DataFrame
        df = pd.DataFrame(all_listings)

        # Remove duplicates based on URL
        if not df.empty and "url" in df.columns:
            df = df.drop_duplicates(subset=["url"], keep="first")

        return df

    def save_data(self, df: pd.DataFrame, listing_type: str, format: str = "csv"):
        """
        Save scraped data to file.

        Args:
            df: DataFrame with listings
            listing_type: 'rent', 'sale', or 'both'
            format: 'csv' or 'json'
        """
        if df.empty:
            print("\nNo data to save.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "csv":
            filename = f"nyc_{listing_type}_{timestamp}.csv"
            filepath = os.path.join(self.data_dir, filename)
            df.to_csv(filepath, index=False)
        else:
            filename = f"nyc_{listing_type}_{timestamp}.json"
            filepath = os.path.join(self.data_dir, filename)
            df.to_json(filepath, orient="records", indent=2)

        print(f"\nData saved to: {filepath}")
        print(f"Total listings: {len(df)}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Zillow NYC listings for rent and sale properties."
    )
    parser.add_argument(
        "--type",
        choices=["rent", "sale", "both"],
        default="both",
        help="Type of listings to scrape (default: both)",
    )
    parser.add_argument(
        "--pages", type=int, default=2, help="Number of pages to scrape (default: 2)"
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Output format (default: csv)",
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=3.0,
        help="Minimum delay between requests in seconds (default: 3)",
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=7.0,
        help="Maximum delay between requests in seconds (default: 7)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Zillow NYC Scraper")
    print("=" * 60)
    print(f"Listing type: {args.type}")
    print(f"Pages to scrape: {args.pages}")
    print(f"Output format: {args.format}")
    print(f"Delay range: {args.delay_min}-{args.delay_max} seconds")
    print("=" * 60)

    scraper = ZillowScraper(delay_range=(args.delay_min, args.delay_max))
    df = scraper.scrape(listing_type=args.type, num_pages=args.pages)

    if not df.empty:
        # Preview data
        print("\n" + "=" * 60)
        print("Preview of scraped data:")
        print("=" * 60)
        print(
            df[["address", "price", "beds", "baths", "listing_type"]]
            .head(10)
            .to_string()
        )

        # Save data
        scraper.save_data(df, args.type, args.format)
    else:
        print("\nNo listings were scraped. This could be due to:")
        print("  - Anti-bot protection blocking requests")
        print("  - Changed page structure")
        print("  - Network issues")
        print("\nTry again later or use a proxy/VPN.")


if __name__ == "__main__":
    main()
