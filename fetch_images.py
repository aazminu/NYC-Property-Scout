import json
import requests
from bs4 import BeautifulSoup
import re
import time
from random import uniform
from fake_useragent import UserAgent
import os
from datetime import datetime

# Configuration
INPUT_FILE = "data/nyc_both_20260131_161453_bbl.json"
OUTPUT_FILE = "data/nyc_both_20260131_161453_bbl.json"
BACKUP_FILE = f'data/nyc_both_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
SAVE_INTERVAL = 20  # Save progress every 20 properties


def load_data():
    """Load property data from JSON file"""
    with open(INPUT_FILE, "r") as f:
        return json.load(f)


def save_data(data, filepath=OUTPUT_FILE):
    """Save property data to JSON file"""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✓ Data saved to {filepath}")


def extract_image_url(html_content, zpid):
    """Extract the first property image URL from Zillow HTML"""
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Method 1: Look for meta property og:image (Open Graph)
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]

        # Method 2: Look for picture tags with data-testid
        picture = soup.find("picture", {"data-testid": "media-photo"})
        if picture:
            img = picture.find("img")
            if img and img.get("src"):
                return img["src"]

        # Method 3: Find images in carousel or gallery
        img_tags = soup.find_all(
            "img", {"class": re.compile(r"(photo|image|media)", re.I)}
        )
        for img in img_tags:
            src = img.get("src") or img.get("data-src")
            if src and ("photos.zillowstatic.com" in src or "zillow.com" in src):
                # Skip tiny icons/logos
                if "logo" not in src.lower() and "icon" not in src.lower():
                    return src

        # Method 4: Search in script tags for image data
        scripts = soup.find_all("script", type="application/json")
        for script in scripts:
            if script.string and "hiRes" in script.string:
                # Look for high-res image URLs in JSON data
                match = re.search(r'"hiRes":"(https://[^"]+)"', script.string)
                if match:
                    return match.group(1)
                match = re.search(
                    r'"url":"(https://photos\.zillowstatic\.com[^"]+)"', script.string
                )
                if match:
                    return match.group(1)

        print(f"  ⚠ No image found for zpid {zpid}")
        return None

    except Exception as e:
        print(f"  ✗ Error parsing HTML for zpid {zpid}: {e}")
        return None


def fetch_image_url(url, zpid, session, ua):
    """Fetch property page and extract first image URL"""
    try:
        headers = {
            "User-Agent": ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }

        response = session.get(url, headers=headers, timeout=15)

        if response.status_code == 200:
            image_url = extract_image_url(response.text, zpid)
            return image_url
        else:
            print(f"  ✗ HTTP {response.status_code} for zpid {zpid}")
            return None

    except requests.exceptions.Timeout:
        print(f"  ✗ Timeout for zpid {zpid}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Request error for zpid {zpid}: {e}")
        return None


def main():
    print("=" * 60)
    print("Zillow Image Extractor")
    print("=" * 60)

    # Load data
    print(f"\nLoading data from {INPUT_FILE}...")
    properties = load_data()
    print(f"✓ Loaded {len(properties)} properties")

    # Create backup
    print(f"\nCreating backup at {BACKUP_FILE}...")
    save_data(properties, BACKUP_FILE)

    # Filter properties that need images
    properties_needing_images = [
        (idx, prop)
        for idx, prop in enumerate(properties)
        if prop.get("zpid")
        and prop.get("zpid") not in [None, "N/A", ""]
        and not prop.get("image_url")  # Skip if already has image
    ]

    print(f"\n{len(properties_needing_images)} properties need image URLs")

    if not properties_needing_images:
        print("✓ All properties already have images!")
        return

    # Initialize session
    session = requests.Session()
    ua = UserAgent()

    # Process each property
    updated_count = 0
    failed_count = 0

    for count, (idx, prop) in enumerate(properties_needing_images, 1):
        zpid = prop["zpid"]
        url = prop.get("url", "")

        print(f"\n[{count}/{len(properties_needing_images)}] zpid: {zpid}")
        print(f"  URL: {url}")

        if not url:
            print(f"  ✗ No URL available")
            failed_count += 1
            continue

        # Fetch image URL
        image_url = fetch_image_url(url, zpid, session, ua)

        if image_url:
            properties[idx]["image_url"] = image_url
            print(f"  ✓ Image URL: {image_url[:80]}...")
            updated_count += 1
        else:
            properties[idx]["image_url"] = None
            failed_count += 1

        # Save progress periodically
        if count % SAVE_INTERVAL == 0:
            print(f"\n{'='*60}")
            print(f"Progress checkpoint - saving data...")
            save_data(properties)
            print(f"Updated: {updated_count} | Failed: {failed_count}")
            print(f"{'='*60}")

        # Random delay to avoid rate limiting
        if count < len(properties_needing_images):
            delay = uniform(2.0, 5.0)
            print(f"  ⏳ Waiting {delay:.1f}s...")
            time.sleep(delay)

    # Final save
    print(f"\n{'='*60}")
    print("Saving final data...")
    save_data(properties)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total properties processed: {len(properties_needing_images)}")
    print(f"Successfully extracted: {updated_count}")
    print(f"Failed: {failed_count}")
    print(f"Success rate: {(updated_count/len(properties_needing_images)*100):.1f}%")
    print(f"\n✓ Complete! Data saved to {OUTPUT_FILE}")
    print(f"✓ Backup saved to {BACKUP_FILE}")


if __name__ == "__main__":
    main()
