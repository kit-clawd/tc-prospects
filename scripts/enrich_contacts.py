#!/usr/bin/env python3
"""
Enrich district data with superintendent names from Ballotpedia
and email patterns from district websites.
"""

import json
import re
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import quote

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

STATE_NAMES = {
    'WA': 'Washington',
    'OR': 'Oregon', 
    'CA': 'California',
    'TX': 'Texas',
    'FL': 'Florida',
    'NY': 'New_York'
}

def load_districts():
    """Load current district data."""
    with open('data/districts.json') as f:
        return json.load(f)

def save_districts(data):
    """Save district data."""
    with open('data/districts.json', 'w') as f:
        json.dump(data, f, indent=2)
    # Also update docs
    with open('docs/data.json', 'w') as f:
        json.dump(data, f, indent=2)

def get_ballotpedia_superintendent(district_name, state):
    """
    Get superintendent name from Ballotpedia.
    """
    # Convert district name to Ballotpedia URL format
    # "Seattle Public Schools" -> "Seattle_Public_Schools,_Washington"
    
    bp_name = district_name.replace(' ', '_')
    state_name = STATE_NAMES.get(state, state)
    
    # Try common URL patterns
    urls_to_try = [
        f"https://ballotpedia.org/{bp_name},_{state_name}",
        f"https://ballotpedia.org/{bp_name}",
        f"https://ballotpedia.org/{bp_name.replace('_School_District', '')}_School_District,_{state_name}",
    ]
    
    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.ok and 'does not have' not in resp.text:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Look for superintendent in infobox
                infobox = soup.find('table', class_='infobox')
                if infobox:
                    for row in infobox.find_all('tr'):
                        cells = row.find_all(['th', 'td'])
                        if len(cells) >= 2:
                            label = cells[0].get_text().strip().lower()
                            if 'superintendent' in label:
                                name = cells[1].get_text().strip()
                                # Clean up the name
                                name = re.sub(r'\[.*?\]', '', name).strip()
                                if name and len(name) > 2:
                                    return name
                
                # Also check page text
                text = soup.get_text()
                match = re.search(r'superintendent[:\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)', text, re.IGNORECASE)
                if match:
                    return match.group(1)
                    
        except Exception as e:
            pass
    
    return None

def guess_email(name, domain):
    """
    Guess email based on common patterns.
    Returns list of possible emails to try.
    """
    if not name or not domain:
        return []
    
    parts = name.lower().split()
    if len(parts) < 2:
        return []
    
    first = parts[0].replace('.', '')
    last = parts[-1]
    first_initial = first[0] if first else ''
    
    patterns = [
        f"{first}.{last}@{domain}",
        f"{first_initial}{last}@{domain}",
        f"{first}{last}@{domain}",
        f"{first}_{last}@{domain}",
        f"{last}.{first}@{domain}",
        f"superintendent@{domain}",
    ]
    
    return patterns

def extract_domain(website):
    """Extract domain from website URL for email guessing."""
    if not website:
        return None
    match = re.search(r'https?://(?:www\.)?([^/]+)', website)
    if match:
        domain = match.group(1)
        # Convert web domain to email domain (common patterns)
        # seattleschools.org -> seattleschools.org
        # www.spokaneschools.org -> spokaneschools.org
        return domain
    return None

def get_email_pattern_from_website(website):
    """
    Try to find email pattern from district website staff pages.
    """
    if not website:
        return None, None
    
    # Common staff directory paths
    paths = [
        '/about/leadership',
        '/about/administration', 
        '/our-district/leadership',
        '/district/administration',
        '/contact',
        '/about-us/leadership',
        '/departments',
    ]
    
    domain = extract_domain(website)
    
    for path in paths:
        url = website.rstrip('/') + path
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.ok:
                # Look for email addresses
                emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', resp.text)
                if emails:
                    # Find the domain pattern
                    district_emails = [e for e in emails if domain and domain.split('.')[0] in e.lower()]
                    if district_emails:
                        # Extract pattern from first email
                        sample = district_emails[0]
                        return sample, domain
        except:
            pass
    
    return None, domain

def main():
    print("=" * 60)
    print("Contact Enrichment - Superintendent Finder")
    print("=" * 60)
    
    data = load_districts()
    districts = data['districts']
    
    updated = 0
    
    for i, district in enumerate(districts):
        name = district['name']
        state = district['state']
        
        # Skip if already has superintendent contact
        existing_contacts = district.get('contacts', [])
        has_supt = any('superintendent' in (c.get('title') or '').lower() for c in existing_contacts)
        
        if has_supt:
            print(f"[{i+1}/{len(districts)}] {name}: Already has superintendent")
            continue
        
        print(f"[{i+1}/{len(districts)}] {name} ({state})...", end=' ', flush=True)
        
        # Get superintendent from Ballotpedia
        supt_name = get_ballotpedia_superintendent(name, state)
        
        if supt_name:
            print(f"Found: {supt_name}", end=' ')
            
            # Try to get email pattern
            website = district.get('website')
            domain = extract_domain(website)
            
            if domain:
                # Generate likely email
                emails = guess_email(supt_name, domain)
                likely_email = emails[0] if emails else None
            else:
                likely_email = None
            
            # Add contact
            contact = {
                'name': supt_name,
                'title': 'Superintendent',
                'email': likely_email,
                'email_guessed': True,
                'phone': None,
                'source': 'Ballotpedia'
            }
            
            if 'contacts' not in district:
                district['contacts'] = []
            
            district['contacts'].insert(0, contact)
            updated += 1
            print(f"(email: {likely_email})")
        else:
            print("Not found")
        
        # Be polite
        time.sleep(1.5)
        
        # Save progress every 10
        if (i + 1) % 10 == 0:
            save_districts(data)
            print(f"  [Saved progress: {updated} updated]")
    
    # Final save
    save_districts(data)
    
    print("\n" + "=" * 60)
    print(f"Done! Updated {updated} districts with superintendent info")
    print("=" * 60)

if __name__ == '__main__':
    main()
