#!/usr/bin/env python3
"""
Fetch RECENT federal awards (2024-2025) from USASpending API.
"""

import json
import time
import requests
from datetime import datetime, timedelta

HEADERS = {'Content-Type': 'application/json'}

def load_districts():
    with open('data/districts.json') as f:
        return json.load(f)

def save_districts(data):
    with open('data/districts.json', 'w') as f:
        json.dump(data, f, indent=2)
    with open('docs/data.json', 'w') as f:
        json.dump(data, f, indent=2)

def search_recent_awards(recipient_name, state):
    """
    Search USASpending for recent awards (last 2 years).
    """
    # Use the spending_by_award endpoint with date filters
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    
    # Search for awards from 2024-2025
    payload = {
        "filters": {
            "recipient_search_text": [recipient_name],
            "time_period": [
                {
                    "start_date": "2024-01-01",
                    "end_date": "2026-12-31"
                }
            ],
            "award_type_codes": ["02", "03", "04", "05"],  # Grants
        },
        "fields": [
            "Award ID",
            "Recipient Name", 
            "Award Amount",
            "Total Outlays",
            "Description",
            "Start Date",
            "End Date",
            "Awarding Agency",
            "CFDA Number"
        ],
        "page": 1,
        "limit": 20,
        "sort": "Award Amount",
        "order": "desc"
    }
    
    try:
        resp = requests.post(url, json=payload, headers=HEADERS, timeout=30)
        if resp.ok:
            data = resp.json()
            results = data.get('results', [])
            return results
    except Exception as e:
        print(f"    Error: {e}")
    
    return []

def search_by_cfda(cfda_codes, state):
    """
    Search by CFDA program codes (education-specific).
    """
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    
    payload = {
        "filters": {
            "program_numbers": cfda_codes,
            "recipient_locations": [{"country": "USA", "state": state}],
            "time_period": [
                {
                    "start_date": "2024-01-01",
                    "end_date": "2026-12-31"
                }
            ],
            "award_type_codes": ["02", "03", "04", "05"],
        },
        "fields": [
            "Award ID",
            "Recipient Name",
            "Award Amount", 
            "Description",
            "Start Date",
            "Awarding Agency",
            "CFDA Number"
        ],
        "page": 1,
        "limit": 50,
        "sort": "Award Amount",
        "order": "desc"
    }
    
    try:
        resp = requests.post(url, json=payload, headers=HEADERS, timeout=30)
        if resp.ok:
            data = resp.json()
            return data.get('results', [])
    except Exception as e:
        print(f"  Error searching CFDA: {e}")
    
    return []

def main():
    print("=" * 60)
    print("Fetching RECENT federal awards (2024-2026)")
    print("=" * 60)
    
    # Education CFDA codes
    edu_cfda = [
        "84.010",  # Title I
        "84.027",  # IDEA Special Ed
        "84.367",  # Supporting Effective Instruction
        "84.425",  # ESSER (COVID relief)
        "84.184",  # Safe and Drug-Free Schools
        "84.287",  # 21st Century Community Learning
        "84.424",  # GEER Fund
    ]
    
    data = load_districts()
    states = list(set(d['state'] for d in data['districts']))
    
    print(f"\nSearching for recent education grants in {len(states)} states...")
    
    all_recent = []
    
    for state in states:
        print(f"\n{state}:")
        results = search_by_cfda(edu_cfda, state)
        
        if results:
            # Filter for school districts
            district_awards = [r for r in results if any(kw in (r.get('Recipient Name') or '').lower() 
                for kw in ['school', 'district', 'unified', 'isd', 'public schools'])]
            
            print(f"  Found {len(district_awards)} school district awards")
            
            for award in district_awards[:5]:
                print(f"    ${award.get('Award Amount', 0):,.0f} - {award.get('Recipient Name', '')[:40]}")
                print(f"      {award.get('Description', '')[:60]}...")
                print(f"      Date: {award.get('Start Date', 'N/A')}")
            
            all_recent.extend(district_awards)
        else:
            print(f"  No recent awards found")
        
        time.sleep(0.5)
    
    print(f"\n\nTotal recent awards found: {len(all_recent)}")
    
    # Now update our district data
    if all_recent:
        print("\nUpdating district data with recent awards...")
        updated = 0
        
        for district in data['districts']:
            d_name = district['name'].lower()
            d_state = district['state']
            
            # Find matching awards
            matching = [a for a in all_recent 
                if d_state in str(a) and 
                any(word in (a.get('Recipient Name') or '').lower() for word in d_name.split()[:2])]
            
            if matching:
                # Update award details
                district['award_details'] = []
                district['recent_awards'] = len(matching)
                total = 0
                
                for award in matching[:5]:
                    amount = award.get('Award Amount', 0) or 0
                    total += amount
                    district['award_details'].append({
                        'amount': amount,
                        'description': award.get('Description', ''),
                        'program': award.get('CFDA Number', ''),
                        'start_date': award.get('Start Date', ''),
                        'year': '2024-2025'
                    })
                
                district['federal_awards'] = total
                print(f"  {district['name']}: {len(matching)} awards, ${total:,.0f}")
                updated += 1
        
        save_districts(data)
        print(f"\nUpdated {updated} districts with recent award data")

if __name__ == '__main__':
    main()
