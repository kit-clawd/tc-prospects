#!/usr/bin/env python3
"""
Fetch ALL federal awards (not just education CFDA codes).
"""

import json
import time
import requests

HEADERS = {'Content-Type': 'application/json'}

def load_districts():
    with open('data/districts.json') as f:
        return json.load(f)

def save_districts(data):
    with open('data/districts.json', 'w') as f:
        json.dump(data, f, indent=2)
    with open('docs/data.json', 'w') as f:
        json.dump(data, f, indent=2)

def search_awards(recipient_name):
    """Search for ALL awards to a recipient (2023-2026)."""
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    
    payload = {
        "filters": {
            "recipient_search_text": [recipient_name],
            "time_period": [{"start_date": "2023-01-01", "end_date": "2026-12-31"}],
            "award_type_codes": ["02", "03", "04", "05"],  # All grants
        },
        "fields": ["Award ID", "Recipient Name", "Award Amount", "Description", "Start Date", "CFDA Number"],
        "page": 1,
        "limit": 50,
        "sort": "Award Amount",
        "order": "desc"
    }
    
    try:
        resp = requests.post(url, json=payload, headers=HEADERS, timeout=30)
        if resp.ok:
            return resp.json().get('results', [])
    except Exception as e:
        print(f"    Error: {e}")
    
    return []

def main():
    print("=" * 60)
    print("Fetching ALL federal awards (2023-2026)")
    print("=" * 60)
    
    data = load_districts()
    
    # Focus on large districts (>50k enrollment)
    large_districts = [d for d in data['districts'] if (d.get('enrollment') or 0) >= 50000]
    print(f"\nUpdating {len(large_districts)} large districts...")
    
    for i, district in enumerate(large_districts):
        name = district['name']
        
        # Simplify search term
        search_term = name.replace(' School District', '').replace(' Public Schools', '').replace(' County', '')
        
        print(f"\n[{i+1}/{len(large_districts)}] {name}")
        print(f"  Searching: {search_term}")
        
        results = search_awards(search_term)
        
        if results:
            # Filter to actual matches
            matching = [r for r in results if search_term.lower().split()[0] in (r.get('Recipient Name') or '').lower()]
            
            if matching:
                total = sum(r.get('Award Amount') or 0 for r in matching)
                district['federal_awards'] = total
                district['recent_awards'] = len(matching)
                district['award_details'] = []
                
                for r in matching[:10]:  # Top 10
                    district['award_details'].append({
                        'amount': r.get('Award Amount') or 0,
                        'description': (r.get('Description') or '')[:200],
                        'program': r.get('CFDA Number') or '',
                        'start_date': r.get('Start Date') or '',
                        'year': '2023-2026'
                    })
                
                print(f"  ✓ {len(matching)} awards, ${total:,.0f}")
            else:
                print(f"  No matching awards")
        else:
            print(f"  No results")
        
        time.sleep(0.5)
    
    save_districts(data)
    print("\n" + "=" * 60)
    print("Done!")

if __name__ == '__main__':
    main()
