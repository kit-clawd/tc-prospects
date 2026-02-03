#!/usr/bin/env python3
"""
Enrich EdClub competitor data by matching subdomains to districts.
"""

import json
import re
from pathlib import Path
from difflib import SequenceMatcher

DATA_DIR = Path(__file__).parent.parent / "data"

def normalize_name(name: str) -> str:
    """Normalize district/school name for matching."""
    name = name.lower()
    # Remove common suffixes
    for suffix in ['school district', 'unified school district', 'public schools', 
                   'city schools', 'county schools', 'independent school district',
                   'isd', 'usd', 'sd', 'ps', 'unified', 'schools', 'school', 'district',
                   'elementary', 'middle', 'high', 'academy', 'k-12', 'k12']:
        name = re.sub(rf'\b{suffix}\b', '', name)
    # Remove punctuation and extra spaces
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, a, b).ratio()

def match_subdomain_to_district(subdomain: str, districts: list) -> dict | None:
    """Try to match a subdomain to a district."""
    # Clean subdomain (remove .typingclub.com)
    name = subdomain.replace('.typingclub.com', '')
    name_normalized = normalize_name(name.replace('-', ' '))
    
    best_match = None
    best_score = 0.0
    
    for district in districts:
        district_name = district['name']
        district_normalized = normalize_name(district_name)
        
        # Direct substring match
        if name_normalized in district_normalized or district_normalized in name_normalized:
            score = 0.9
        else:
            score = similarity(name_normalized, district_normalized)
        
        # Boost if city matches
        city = (district.get('city') or '').lower()
        if city and city in name_normalized:
            score += 0.2
            
        if score > best_score and score > 0.5:
            best_score = score
            best_match = {
                'district': district['name'],
                'state': district['state'],
                'enrollment': district.get('enrollment', 0),
                'confidence': round(score, 2)
            }
    
    return best_match

def main():
    # Load EdClub subdomains
    with open(DATA_DIR / "edclub_subdomains.txt") as f:
        subdomains = [line.strip() for line in f if line.strip()]
    
    # Load districts
    with open(DATA_DIR / "districts.json") as f:
        data = json.load(f)
        districts = data.get('districts', data) if isinstance(data, dict) else data
    
    print(f"Loaded {len(subdomains)} EdClub subdomains")
    print(f"Loaded {len(districts)} districts")
    
    # Match subdomains to districts
    competitors = []
    matched_districts = set()
    
    for subdomain in subdomains:
        match = match_subdomain_to_district(subdomain, districts)
        entry = {
            'subdomain': subdomain,
            'name': subdomain.replace('.typingclub.com', '').replace('-', ' ').title(),
            'match': match
        }
        competitors.append(entry)
        if match:
            matched_districts.add(match['district'])
    
    # Add competitor status to districts
    for district in districts:
        district['uses_edclub'] = district['name'] in matched_districts
    
    # Stats
    high_confidence = sum(1 for c in competitors if c['match'] and c['match']['confidence'] >= 0.7)
    medium_confidence = sum(1 for c in competitors if c['match'] and 0.5 <= c['match']['confidence'] < 0.7)
    unmatched = sum(1 for c in competitors if not c['match'])
    
    print(f"\nMatching Results:")
    print(f"  High confidence (>=0.7): {high_confidence}")
    print(f"  Medium confidence (0.5-0.7): {medium_confidence}")
    print(f"  Unmatched: {unmatched}")
    print(f"  Districts using EdClub: {len(matched_districts)}")
    
    # Save enriched data
    output = {
        'meta': {
            'total_subdomains': len(subdomains),
            'matched': len(subdomains) - unmatched,
            'unmatched': unmatched,
            'districts_using_edclub': len(matched_districts)
        },
        'competitors': competitors
    }
    
    with open(DATA_DIR / "edclub_enriched.json", 'w') as f:
        json.dump(output, f, indent=2)
    
    # Update districts with competitor flag
    districts_output = {
        'meta': data.get('meta', {}),
        'districts': districts
    }
    districts_output['meta']['edclub_enrichment'] = True
    
    with open(DATA_DIR / "districts.json", 'w') as f:
        json.dump(districts_output, f, indent=2)
    
    print(f"\nSaved: data/edclub_enriched.json")
    print(f"Updated: data/districts.json (added uses_edclub flag)")

if __name__ == "__main__":
    main()
