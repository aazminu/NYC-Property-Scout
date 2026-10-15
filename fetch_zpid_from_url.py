import json
import re
import time
import random
import requests
from pathlib import Path
from fake_useragent import UserAgent

# Path to the JSON file
json_file = Path("data/nyc_both_20260131_161453_bbl.json")

# Read the JSON data
print(f"Reading {json_file}...")
with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total properties: {len(data)}")

# Setup user agent and session for persistent connection
ua = UserAgent()
session = requests.Session()

# Counter for updates
updated_count = 0
missing_zpid_count = 0
failed_count = 0

# Pattern to extract zpid from HTML
# Zillow often has zpid in various places: data attributes, JSON-LD, or script tags
zpid_patterns = [
    re.compile(r'"zpid":"?(\d+)"?'),
    re.compile(r'"zpid":(\d+)'),
    re.compile(r'data-zpid="(\d+)"'),
    re.compile(r'zpid["\']?\s*[:=]\s*["\']?(\d+)'),
]

# Process each property
for i, property_data in enumerate(data):
    zpid = property_data.get("zpid")
    url = property_data.get("url", "")
    address = property_data.get("address", "Unknown")

    # Check if zpid is missing or "N/A"
    if not zpid or zpid == "N/A" or zpid == "":
        missing_zpid_count += 1

        if not url:
            print(f"[{i+1}/{len(data)}] No URL for {address}")
            failed_count += 1
            continue

        print(f"[{i+1}/{len(data)}] Fetching {address}...")

        try:
            # Make request with realistic browser headers
            headers = {
                "User-Agent": ua.random,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "max-age=0",
                "DNT": "1",
            }

            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            html_content = response.text

            # Try each pattern
            found_zpid = None
            for pattern in zpid_patterns:
                matches = pattern.findall(html_content)
                if matches:
                    found_zpid = matches[0]
                    break

            if found_zpid:
                property_data["zpid"] = found_zpid
                updated_count += 1
                print(f"  ✓ Found zpid: {found_zpid}")
            else:
                print(f"  ✗ Could not find zpid in page")
                failed_count += 1

            # Randomized rate limiting - wait between 2-5 seconds
            delay = random.uniform(2.0, 5.0)
            print(f"  ⏱ Waiting {delay:.1f}s...")
            time.sleep(delay)

        except requests.exceptions.RequestException as e:
            print(f"  ✗ Error fetching page: {e}")
            failed_count += 1
            # Wait longer on errors with randomization
            error_delay = random.uniform(5.0, 10.0)
            print(f"  ⏱ Waiting {error_delay:.1f}s after error...")
            time.sleep(error_delay)

        # Save progress every 20 updates
        if updated_count > 0 and updated_count % 20 == 0:
            print(f"\n💾 Saving progress... ({updated_count} updated so far)")
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\n{'='*60}")
print(f"Summary:")
print(f"Properties with missing zpid: {missing_zpid_count}")
print(f"Properties updated with extracted zpid: {updated_count}")
print(f"Properties that failed: {failed_count}")
print(f"{'='*60}")

# Create backup
backup_file = json_file.with_suffix(".json.backup")
print(f"\nCreating backup at {backup_file}...")
with open(backup_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)

# Save the updated data
print(f"Saving final data to {json_file}...")
with open(json_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✅ Done!")
