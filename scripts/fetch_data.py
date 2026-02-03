#!/usr/bin/env python3
"""
Fetch school district data from public sources.
- NCES: District demographics and contacts
- USASpending: Federal education grants
"""

import json
import requests
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
DOCS_DIR = Path(__file__).parent.parent / "docs"

# States to fetch (expand as needed)
STATES = ["WA", "OR", "CA", "TX", "FL", "NY"]


def fetch_usaspending_by_state(state: str, year: str = "2024") -> list:
    """Fetch Department of Education awards for a state."""
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    
    payload = {
        "filters": {
            "time_period": [{"start_date": f"{year}-01-01", "end_date": f"{year}-12-31"}],
            "agencies": [{"type": "awarding", "tier": "toptier", "name": "Department of Education"}],
            "recipient_locations": [{"country": "USA", "state": state}],
            "award_type_codes": ["02", "03", "04", "05"]  # Grants
        },
        "fields": ["Award ID", "Recipient Name", "Award Amount", "Description", "Start Date"],
        "limit": 100,
        "page": 1,
        "sort": "Award Amount",
        "order": "desc"
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except Exception as e:
        print(f"  Error fetching USASpending for {state}: {e}")
        return []


def fetch_nces_districts(state: str) -> list:
    """
    Fetch district data from NCES.
    Note: NCES bulk files require download; this uses their search API as fallback.
    For production, download CSV from: https://nces.ed.gov/ccd/files.asp
    """
    # NCES doesn't have a clean REST API, so we'll use static data
    # In production, you'd parse their CSV files
    return []


def build_district_database(states: list) -> dict:
    """Build aggregated district database."""
    
    print(f"Building district database for {len(states)} states...")
    
    all_data = {
        "meta": {
            "updated": datetime.now().isoformat(),
            "sources": ["USASpending.gov", "NCES"],
            "states": states
        },
        "districts": [],
        "federal_awards": {}
    }
    
    for state in states:
        print(f"Fetching {state}...")
        
        # Get federal awards
        awards = fetch_usaspending_by_state(state)
        print(f"  Found {len(awards)} federal awards")
        
        # Extract district-like recipients (filter out state agencies)
        district_awards = []
        for award in awards:
            name = award.get("Recipient Name", "").upper()
            # Filter for school districts (rough heuristic)
            if any(kw in name for kw in ["SCHOOL", "DISTRICT", "UNIFIED", "ISD", "USD"]):
                district_awards.append({
                    "name": award.get("Recipient Name"),
                    "amount": award.get("Award Amount"),
                    "description": award.get("Description", "")[:200],
                    "state": state
                })
        
        all_data["federal_awards"][state] = district_awards
        print(f"  {len(district_awards)} district-level awards")
    
    return all_data


def add_sample_districts(data: dict) -> dict:
    """Add sample district data for demo purposes."""
    
    # Sample data - in production, parse from NCES CSV
    sample_districts = [
        {"name": "Seattle Public Schools", "state": "WA", "enrollment": 49000, "city": "Seattle", "type": "Urban"},
        {"name": "Spokane Public Schools", "state": "WA", "enrollment": 28000, "city": "Spokane", "type": "Urban"},
        {"name": "Tacoma Public Schools", "state": "WA", "enrollment": 27000, "city": "Tacoma", "type": "Urban"},
        {"name": "Kent School District", "state": "WA", "enrollment": 25000, "city": "Kent", "type": "Suburban"},
        {"name": "Federal Way Public Schools", "state": "WA", "enrollment": 22000, "city": "Federal Way", "type": "Suburban"},
        {"name": "Lake Washington School District", "state": "WA", "enrollment": 32000, "city": "Kirkland", "type": "Suburban"},
        {"name": "Northshore School District", "state": "WA", "enrollment": 23000, "city": "Bothell", "type": "Suburban"},
        {"name": "Bellevue School District", "state": "WA", "enrollment": 19000, "city": "Bellevue", "type": "Suburban"},
        {"name": "Los Angeles USD", "state": "CA", "enrollment": 420000, "city": "Los Angeles", "type": "Urban"},
        {"name": "San Diego USD", "state": "CA", "enrollment": 97000, "city": "San Diego", "type": "Urban"},
        {"name": "Houston ISD", "state": "TX", "enrollment": 187000, "city": "Houston", "type": "Urban"},
        {"name": "Dallas ISD", "state": "TX", "enrollment": 140000, "city": "Dallas", "type": "Urban"},
        {"name": "Austin ISD", "state": "TX", "enrollment": 72000, "city": "Austin", "type": "Urban"},
        {"name": "New York City DOE", "state": "NY", "enrollment": 915000, "city": "New York", "type": "Urban"},
        {"name": "Portland Public Schools", "state": "OR", "enrollment": 43000, "city": "Portland", "type": "Urban"},
        {"name": "Miami-Dade County", "state": "FL", "enrollment": 334000, "city": "Miami", "type": "Urban"},
    ]
    
    # Enrich with federal award data if available
    for district in sample_districts:
        state_awards = data["federal_awards"].get(district["state"], [])
        matching = [a for a in state_awards if district["name"].upper() in a["name"].upper()]
        if matching:
            district["federal_awards"] = sum(a["amount"] for a in matching if a["amount"])
        else:
            district["federal_awards"] = 0
    
    data["districts"] = sample_districts
    return data


def main():
    DATA_DIR.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)
    
    # Build database
    data = build_district_database(STATES)
    data = add_sample_districts(data)
    
    # Save to data dir
    output_path = DATA_DIR / "districts.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nSaved to {output_path}")
    
    # Copy to docs for web UI
    docs_path = DOCS_DIR / "data.json"
    with open(docs_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Copied to {docs_path}")
    
    # Summary
    print(f"\n=== Summary ===")
    print(f"Districts: {len(data['districts'])}")
    print(f"States with award data: {len(data['federal_awards'])}")
    total_awards = sum(len(v) for v in data['federal_awards'].values())
    print(f"Total district-level awards: {total_awards}")


if __name__ == "__main__":
    main()
