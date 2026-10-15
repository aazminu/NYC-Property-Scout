import json
import re
from pathlib import Path

# Path to the JSON file
json_file = Path("data/nyc_both_20260131_161453_bbl.json")

# Read the JSON data
print(f"Reading {json_file}...")
with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total properties: {len(data)}")

# Counter for updates
updated_count = 0
missing_zpid_count = 0

# Pattern to extract zpid from URL
# Matches patterns like: /31552954_zpid/ or building codes like /Cknr6R/
zpid_pattern = re.compile(r"/(\d+)_zpid/?")  # Numeric zpid: /31552954_zpid/
building_code_pattern = re.compile(
    r"/([A-Za-z0-9]{6,})/?$"
)  # Building codes: /Cknr6R/ or /ChWHPZ/

# Process each property
for property_data in data:
    zpid = property_data.get("zpid")
    url = property_data.get("url", "")

    # Check if zpid is missing or "N/A"
    if not zpid or zpid == "N/A" or zpid == "":
        missing_zpid_count += 1

        # Try to extract zpid from URL
        if url:
            # First try numeric zpid pattern
            match = zpid_pattern.search(url)
            if match:
                extracted_zpid = match.group(1)
                property_data["zpid"] = extracted_zpid
                updated_count += 1
                print(
                    f"Updated: {property_data.get('address', 'Unknown')} -> zpid: {extracted_zpid}"
                )
            else:
                # Try building code pattern
                match = building_code_pattern.search(url)
                if match:
                    building_code = match.group(1)
                    property_data["zpid"] = building_code
                    updated_count += 1
                    print(
                        f"Updated: {property_data.get('address', 'Unknown')} -> zpid: {building_code}"
                    )

print(f"\nSummary:")
print(f"Properties with missing zpid: {missing_zpid_count}")
print(f"Properties updated with extracted zpid: {updated_count}")
print(f"Properties still missing zpid: {missing_zpid_count - updated_count}")

# Create backup
backup_file = json_file.with_suffix(".json.backup")
print(f"\nCreating backup at {backup_file}...")
with open(backup_file, "w", encoding="utf-8") as f:
    json.dump(data, f)

# Save the updated data
print(f"Saving updated data to {json_file}...")
with open(json_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✅ Done!")
