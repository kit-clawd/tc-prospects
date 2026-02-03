#!/usr/bin/env python3
"""
Fetch school district data from public sources.
- NCES: District demographics and contacts
- USASpending: Federal education grants with program details
"""

import json
import requests
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
DOCS_DIR = Path(__file__).parent.parent / "docs"

# States to fetch (expand as needed)
STATES = ["WA", "OR", "CA", "TX", "FL", "NY"]

# CFDA program codes for education grants
CFDA_PROGRAMS = {
    "84.010": "Title I - Improving Basic Programs",
    "84.011": "Title I - Migrant Education",
    "84.013": "Title I - Program for Neglected Children",
    "84.027": "IDEA - Special Education Grants",
    "84.173": "IDEA - Preschool Grants",
    "84.196": "Education for Homeless Children",
    "84.287": "21st Century Community Learning",
    "84.318": "Education Technology State Grants",
    "84.365": "English Language Acquisition",
    "84.366": "Mathematics and Science Partnerships",
    "84.367": "Supporting Effective Instruction",
    "84.369": "Grants for State Assessments",
    "84.424": "Student Support and Academic Enrichment",
}


def fetch_usaspending_detailed(state: str, years: list = None) -> list:
    """Fetch Department of Education awards with full details."""
    if years is None:
        years = ["2024", "2025", "2026"]
    
    all_awards = []
    
    for year in years:
        url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
        
        payload = {
            "filters": {
                "time_period": [{"start_date": f"{year}-01-01", "end_date": f"{year}-12-31"}],
                "agencies": [{"type": "awarding", "tier": "toptier", "name": "Department of Education"}],
                "recipient_locations": [{"country": "USA", "state": state}],
                "award_type_codes": ["02", "03", "04", "05"]  # Grants
            },
            "fields": [
                "Award ID", 
                "Recipient Name", 
                "Award Amount", 
                "Description",
                "Start Date",
                "End Date",
                "Awarding Agency",
                "CFDA Number"
            ],
            "limit": 100,
            "page": 1,
            "sort": "Award Amount",
            "order": "desc"
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            for r in results:
                r["fetch_year"] = year
            all_awards.extend(results)
        except Exception as e:
            print(f"  Error fetching {state} {year}: {e}")
    
    return all_awards


def parse_cfda(cfda_str: str) -> dict:
    """Parse CFDA number and return program info."""
    if not cfda_str:
        return {"code": None, "program": "Unknown"}
    
    # CFDA format is usually "84.010" or similar
    code = cfda_str.split()[0] if cfda_str else None
    program = CFDA_PROGRAMS.get(code, cfda_str)
    
    return {"code": code, "program": program}


def is_school_district(name: str) -> bool:
    """Check if recipient name looks like a school district."""
    if not name:
        return False
    name_upper = name.upper()
    keywords = ["SCHOOL", "DISTRICT", "UNIFIED", "ISD", "USD", "EDUCATION", "LEARNING"]
    exclude = ["UNIVERSITY", "COLLEGE", "SUPERINTENDENT OF PUBLIC"]
    
    if any(ex in name_upper for ex in exclude):
        return False
    return any(kw in name_upper for kw in keywords)


def build_district_database(states: list) -> dict:
    """Build aggregated district database with award details."""
    
    print(f"Building district database for {len(states)} states...")
    
    all_data = {
        "meta": {
            "updated": datetime.now().isoformat(),
            "sources": ["USASpending.gov", "NCES"],
            "states": states
        },
        "districts": [],
        "awards_by_district": {}
    }
    
    for state in states:
        print(f"Fetching {state}...")
        
        # Get detailed federal awards
        awards = fetch_usaspending_detailed(state)
        print(f"  Found {len(awards)} total awards")
        
        # Group by district
        district_awards = {}
        for award in awards:
            name = award.get("Recipient Name", "")
            if not is_school_district(name):
                continue
            
            # Normalize district name
            district_key = name.upper().strip()
            
            if district_key not in district_awards:
                district_awards[district_key] = {
                    "name": name,
                    "state": state,
                    "awards": [],
                    "total_amount": 0,
                    "title_i_amount": 0,
                    "recent_awards": 0  # Awards in last 12 months
                }
            
            cfda_info = parse_cfda(award.get("CFDA Number"))
            amount = award.get("Award Amount") or 0
            start_date = award.get("Start Date", "")
            
            award_record = {
                "amount": amount,
                "description": (award.get("Description") or "")[:200],
                "cfda_code": cfda_info["code"],
                "program": cfda_info["program"],
                "start_date": start_date,
                "year": award.get("fetch_year")
            }
            
            district_awards[district_key]["awards"].append(award_record)
            district_awards[district_key]["total_amount"] += amount
            
            # Track Title I specifically
            if cfda_info["code"] and cfda_info["code"].startswith("84.01"):
                district_awards[district_key]["title_i_amount"] += amount
            
            # Track recent awards (2025-2026)
            if award.get("fetch_year") in ["2025", "2026"]:
                district_awards[district_key]["recent_awards"] += 1
        
        all_data["awards_by_district"][state] = district_awards
        print(f"  {len(district_awards)} school districts found")
    
    return all_data


def add_sample_districts(data: dict) -> dict:
    """Add sample district data and merge with award data."""
    
    # Sample districts with enrollment data
    sample_districts = [
        {"name": "Seattle Public Schools", "state": "WA", "enrollment": 49000, "city": "Seattle", "type": "Urban"},
        {"name": "Spokane Public Schools", "state": "WA", "enrollment": 28000, "city": "Spokane", "type": "Urban"},
        {"name": "Tacoma Public Schools", "state": "WA", "enrollment": 27000, "city": "Tacoma", "type": "Urban"},
        {"name": "Kent School District", "state": "WA", "enrollment": 25000, "city": "Kent", "type": "Suburban"},
        {"name": "Federal Way Public Schools", "state": "WA", "enrollment": 22000, "city": "Federal Way", "type": "Suburban"},
        {"name": "Lake Washington School District", "state": "WA", "enrollment": 32000, "city": "Kirkland", "type": "Suburban"},
        {"name": "Northshore School District", "state": "WA", "enrollment": 23000, "city": "Bothell", "type": "Suburban"},
        {"name": "Bellevue School District", "state": "WA", "enrollment": 19000, "city": "Bellevue", "type": "Suburban"},
        {"name": "Los Angeles Unified School District", "state": "CA", "enrollment": 420000, "city": "Los Angeles", "type": "Urban"},
        {"name": "San Diego Unified School District", "state": "CA", "enrollment": 97000, "city": "San Diego", "type": "Urban"},
        {"name": "Houston Independent School District", "state": "TX", "enrollment": 187000, "city": "Houston", "type": "Urban"},
        {"name": "Dallas Independent School District", "state": "TX", "enrollment": 140000, "city": "Dallas", "type": "Urban"},
        {"name": "Austin Independent School District", "state": "TX", "enrollment": 72000, "city": "Austin", "type": "Urban"},
        {"name": "New York City Department of Education", "state": "NY", "enrollment": 915000, "city": "New York", "type": "Urban"},
        {"name": "Portland Public Schools", "state": "OR", "enrollment": 43000, "city": "Portland", "type": "Urban"},
        {"name": "Miami-Dade County Public Schools", "state": "FL", "enrollment": 334000, "city": "Miami", "type": "Urban"},
        {"name": "Hillsborough County Public Schools", "state": "FL", "enrollment": 217000, "city": "Tampa", "type": "Urban"},
        {"name": "Orange County Public Schools", "state": "FL", "enrollment": 206000, "city": "Orlando", "type": "Urban"},
    ]
    
    # Merge with award data
    for district in sample_districts:
        state_awards = data["awards_by_district"].get(district["state"], {})
        
        # Try to match by name
        matched = None
        district_name_upper = district["name"].upper()
        for key, award_data in state_awards.items():
            if district_name_upper in key or key in district_name_upper:
                matched = award_data
                break
        
        if matched:
            district["federal_awards"] = matched["total_amount"]
            district["title_i"] = matched["title_i_amount"]
            district["recent_awards"] = matched["recent_awards"]
            district["award_details"] = matched["awards"][:10]  # Top 10 awards
        else:
            district["federal_awards"] = 0
            district["title_i"] = 0
            district["recent_awards"] = 0
            district["award_details"] = []
    
    # Also add districts we found in USASpending that aren't in our sample
    for state, state_awards in data["awards_by_district"].items():
        for key, award_data in state_awards.items():
            # Check if already in sample
            exists = any(
                d["name"].upper() in key or key in d["name"].upper() 
                for d in sample_districts
            )
            if not exists and award_data["total_amount"] > 1000000:  # Only add if >$1M
                sample_districts.append({
                    "name": award_data["name"],
                    "state": state,
                    "enrollment": None,  # Unknown
                    "city": None,
                    "type": None,
                    "federal_awards": award_data["total_amount"],
                    "title_i": award_data["title_i_amount"],
                    "recent_awards": award_data["recent_awards"],
                    "award_details": award_data["awards"][:10]
                })
    
    data["districts"] = sample_districts
    return data


def main():
    DATA_DIR.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)
    
    # Build database
    data = build_district_database(STATES)
    data = add_sample_districts(data)
    
    # Remove raw awards_by_district to keep file smaller
    del data["awards_by_district"]
    
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
    districts_with_awards = sum(1 for d in data['districts'] if d.get('federal_awards', 0) > 0)
    print(f"Districts with federal awards: {districts_with_awards}")
    districts_with_title_i = sum(1 for d in data['districts'] if d.get('title_i', 0) > 0)
    print(f"Districts with Title I: {districts_with_title_i}")


if __name__ == "__main__":
    main()
