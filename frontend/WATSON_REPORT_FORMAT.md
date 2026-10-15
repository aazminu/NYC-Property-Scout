# Watson Report JSON Structure

## Expected JSON Format from Watson

```json
{
  "property": {
    "address": "190 Beach 69th St, Arverne, NY",
    "building_name": "The Tides At Arverne By The Sea",
    "beds": 1.0,
    "baths": null,
    "sqft": null,
    "zillow_url": "https://www.zillow.com/apartments/arverne-ny/the-tides-at-arverne-by-the-sea/ChWHPZ/"
  },
  "scores": {
    "overall": 7.5,
    "quality": 15,
    "financial": 0
  },
  "quality_audit": {
    "score": 15,
    "recent_issues": [
      {
        "type": "Noise – Street/Sidewalk",
        "details": "multiple incidents Dec 2025 – Jan 2026"
      },
      {
        "type": "Noise – Commercial",
        "details": "multiple incidents Nov 2025 – Dec 2025"
      },
      {
        "type": "Snow or Ice",
        "details": "complaints in Jan 2026"
      }
    ],
    "scouts_note": "The property experienced frequent noise complaints (both street/sidewalk and commercial) over the past 90 days, resulting in significant deductions. Two snow/ice complaints also contributed."
  },
  "financial_audit": {
    "score": 0,
    "city_market_value": 3368000,
    "annual_tax": 2140182,
    "risk_factors": [
      "High assessed value relative to market value may indicate over-assessment"
    ]
  },
  "recommendation": {
    "level": "High Risk",
    "reason": "The low transparency scores and notable tax-assessment discrepancy suggest caution"
  },
  "sources": "NYC Open Data (erm2-nwe9 & 8y4t-faws)"
}
```

## How to Parse from Markdown

The Watson response comes as markdown text. The ScoreCard component will:
1. Try to parse JSON if wrapped in ```json blocks
2. Fall back to regex extraction for markdown format
3. Display structured UI based on parsed data
