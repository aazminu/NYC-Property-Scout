#!/usr/bin/env python3
"""
BBL Enrichment Script
=====================
Enriches Zillow scraped data with NYC BBL (Borough-Block-Lot).

IMPORTANT: To get BBL data, you need to register (free) at:
https://api-portal.nyc.gov/signup

Then get your subscription key from:
https://api-portal.nyc.gov/docs/services/geoclient/operations/geoclient

Usage:
    # With .env file containing NYC_GEOCLIENT_KEY
    python bbl_enricher.py data/nyc_rent.csv
    
    # Or specify key directly
    python bbl_enricher.py data/nyc_rent.csv --api-key YOUR_SUBSCRIPTION_KEY
"""

import argparse
import os
import re
import time
from typing import Optional, Dict

import pandas as pd
import requests

# Load .env file with custom parser (handles colon format)
def load_env_file():
    """Load .env file, supporting both = and : delimiters."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Support both KEY=value and KEY : value formats
                    if ":" in line:
                        key, value = line.split(":", 1)
                    elif "=" in line:
                        key, value = line.split("=", 1)
                    else:
                        continue
                    key = key.strip().replace("-", "_")  # Normalize key
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value

load_env_file()


class BBLEnricher:
    """Enriches NYC addresses with Borough-Block-Lot data."""
    
    # NYC Geoclient API v2 (requires free registration)
    GEOCLIENT_URL = "https://api.nyc.gov/geoclient/v2/address.json"
    
    # Borough name to code mapping
    BOROUGH_CODES = {
        "MANHATTAN": "1", "MN": "1", "NEW YORK": "1",
        "BRONX": "2", "BX": "2",
        "BROOKLYN": "3", "BK": "3", "KINGS": "3",
        "QUEENS": "4", "QN": "4",
        "STATEN ISLAND": "5", "SI": "5", "RICHMOND": "5"
    }
    
    # Neighborhood to borough mapping
    NEIGHBORHOODS = {
        "manhattan": "MANHATTAN", "harlem": "MANHATTAN", "tribeca": "MANHATTAN",
        "soho": "MANHATTAN", "chelsea": "MANHATTAN", "midtown": "MANHATTAN",
        "brooklyn": "BROOKLYN", "williamsburg": "BROOKLYN", "bushwick": "BROOKLYN",
        "dumbo": "BROOKLYN", "park slope": "BROOKLYN", "bed-stuy": "BROOKLYN",
        "queens": "QUEENS", "astoria": "QUEENS", "flushing": "QUEENS",
        "jamaica": "QUEENS", "long island city": "QUEENS", "rego park": "QUEENS",
        "arverne": "QUEENS", "far rockaway": "QUEENS", "whitestone": "QUEENS",
        "kew gardens": "QUEENS", "south richmond hill": "QUEENS",
        "bronx": "BRONX", "riverdale": "BRONX", "fordham": "BRONX",
        "staten island": "STATEN ISLAND", "new york": "MANHATTAN"
    }
    
    def __init__(self, api_key: str = None):
        """
        Initialize BBL enricher.
        
        Args:
            api_key: NYC Geoclient subscription key (Ocp-Apim-Subscription-Key)
        """
        self.api_key = api_key or os.environ.get("PRIMARY_KEY") or os.environ.get("NYC_GEOCLIENT_KEY")
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                "Ocp-Apim-Subscription-Key": self.api_key
            })
    
    def parse_address(self, full_address: str) -> Dict[str, str]:
        """Parse a full address into components."""
        address = full_address.strip()
        parts = address.split(",")
        
        if len(parts) < 2:
            return {}
        
        street_part = parts[0].strip()
        city_part = parts[1].strip() if len(parts) > 1 else ""
        
        # Handle unit numbers in the street part
        # Remove "APT X", "Unit X", "#X", etc.
        street_part = re.sub(r'\s+(APT|UNIT|#|FLOOR|FL)\s*\S*', '', street_part, flags=re.IGNORECASE)
        
        # Extract house number and street name
        match = re.match(r'^(\d+[-\d/]*)\s+(.+)$', street_part)
        if not match:
            return {}
        
        house_number = match.group(1)
        street_name = match.group(2)
        
        # Determine borough
        borough = None
        city_lower = city_part.lower()
        
        for boro_name in self.BOROUGH_CODES:
            if boro_name.lower() in city_lower:
                borough = boro_name
                break
        
        if not borough:
            for neighborhood, boro in self.NEIGHBORHOODS.items():
                if neighborhood in city_lower:
                    borough = boro
                    break
        
        # Extract zip code if present
        zip_match = re.search(r'\b(\d{5})\b', address)
        zip_code = zip_match.group(1) if zip_match else None
        
        return {
            "house_number": house_number,
            "street_name": street_name,
            "borough": borough or "MANHATTAN",
            "zip_code": zip_code
        }
    
    def get_bbl_from_geoclient(self, address: str) -> Optional[Dict]:
        """
        Get BBL using NYC Geoclient API v2.
        Requires free registration at https://api-portal.nyc.gov/signup
        """
        if not self.api_key:
            return None
        
        parsed = self.parse_address(address)
        if not parsed or not parsed.get("house_number") or not parsed.get("street_name"):
            return None
        
        try:
            response = self.session.get(
                self.GEOCLIENT_URL,
                params={
                    "houseNumber": parsed["house_number"],
                    "street": parsed["street_name"],
                    "borough": parsed["borough"]
                },
                timeout=10
            )
            
            if response.status_code == 401:
                if not hasattr(self, '_auth_error_shown'):
                    print("\n⚠️  API key is not yet activated!")
                    print("   NYC API subscriptions may take a few hours to approve.")
                    print("   Check your subscription status at: https://api-portal.nyc.gov/")
                    self._auth_error_shown = True
                return None
            
            response.raise_for_status()
            data = response.json()
            
            result = data.get("address", {})
            
            if result.get("bbl"):
                return {
                    "bbl": result.get("bbl"),
                    "borough_code": result.get("bblBoroughCode"),
                    "block": result.get("bblTaxBlock"),
                    "lot": result.get("bblTaxLot"),
                    "borough_name": result.get("firstBoroughName"),
                    "building_class": result.get("buildingClassificationCode"),
                    "bin": result.get("buildingIdentificationNumber"),
                    "census_tract": result.get("censusTract2020")
                }
            
            return None
            
        except Exception as e:
            return None
    
    def enrich_dataframe(self, df: pd.DataFrame, address_column: str = "address",
                         delay: float = 0.3) -> pd.DataFrame:
        """
        Enrich a DataFrame with BBL data.
        """
        # Add new columns
        new_columns = ["bbl", "borough_code", "block", "lot", "borough_name", 
                       "building_class", "bin", "census_tract"]
        for col in new_columns:
            if col not in df.columns:
                df[col] = None
        
        total = len(df)
        successful = 0
        
        print(f"\nEnriching {total} addresses with BBL data...")
        print("=" * 60)
        
        for idx, row in df.iterrows():
            if idx % 10 == 0:
                print(f"  Processing {idx + 1}/{total}...")
            
            address = row.get(address_column)
            if pd.isna(address):
                continue
            
            bbl_data = self.get_bbl_from_geoclient(str(address))
            
            if bbl_data:
                for col in new_columns:
                    if col in bbl_data:
                        df.at[idx, col] = bbl_data.get(col)
                successful += 1
            
            time.sleep(delay)
        
        print(f"\n✓ Successfully enriched {successful}/{total} addresses with BBL data")
        
        return df


def enrich_with_pluto(df: pd.DataFrame, pluto_file: str) -> pd.DataFrame:
    """
    Enrich data by joining with downloaded PLUTO file.
    Download PLUTO from: https://www.nyc.gov/site/planning/data-maps/open-data/dwn-pluto-mappluto.page
    """
    print(f"Loading PLUTO file: {pluto_file}")
    pluto = pd.read_csv(pluto_file, dtype=str)
    
    # Create address key for joining
    # This is a simplified approach - real matching would need fuzzy matching
    print("Note: Local PLUTO matching requires manual address normalization")
    print("For best results, use the Geoclient API")
    
    return df


def main():
    parser = argparse.ArgumentParser(
        description="Enrich Zillow scraped data with NYC BBL (Borough-Block-Lot).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Using .env file with PRIMARY-KEY:
    python bbl_enricher.py data/nyc_rent.csv
    
    # Or specify key directly:
    python bbl_enricher.py data/nyc_rent.csv --api-key YOUR_SUBSCRIPTION_KEY
    
    # Register for free at: https://api-portal.nyc.gov/signup
"""
    )
    parser.add_argument("input_file", help="Path to CSV file with scraped data")
    parser.add_argument("--output", help="Output file path (default: adds _with_bbl suffix)")
    parser.add_argument("--api-key", help="NYC Geoclient subscription key")
    parser.add_argument("--delay", type=float, default=0.3, 
                        help="Delay between API calls in seconds (default: 0.3)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: File not found: {args.input_file}")
        return
    
    print("=" * 60)
    print("BBL Enricher - NYC Borough-Block-Lot Lookup")
    print("=" * 60)
    
    # Get API key from args or environment
    api_key = args.api_key or os.environ.get("PRIMARY_KEY") or os.environ.get("NYC_GEOCLIENT_KEY")
    
    if not api_key:
        print("\n⚠️  No API key found!")
        print("\nTo get BBL data, you need to:")
        print("1. Register (free) at: https://api-portal.nyc.gov/signup")
        print("2. Subscribe to the Geoclient API")
        print("3. Add PRIMARY-KEY to your .env file, or use --api-key")
        return
    
    print(f"✓ API key loaded")
    
    df = pd.read_csv(args.input_file)
    print(f"Loaded {len(df)} records from {args.input_file}")
    
    enricher = BBLEnricher(api_key=api_key)
    df = enricher.enrich_dataframe(df, delay=args.delay)
    
    # Save output
    if args.output:
        output_path = args.output
    else:
        base, ext = os.path.splitext(args.input_file)
        output_path = f"{base}_with_bbl{ext}"
    
    df.to_csv(output_path, index=False)
    print(f"\n✓ Saved enriched data to: {output_path}")
    
    # Show sample
    cols = ["address", "bbl", "block", "lot"]
    sample = df[cols].dropna(subset=["bbl"]).head(5)
    if not sample.empty:
        print("\nSample enriched data:")
        print("-" * 60)
        print(sample.to_string())


if __name__ == "__main__":
    main()

