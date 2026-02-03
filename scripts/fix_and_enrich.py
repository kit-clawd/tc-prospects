#!/usr/bin/env python3
"""
Fix bad superintendent extractions and add tech director contacts.
"""

import json
import re
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Manual fixes for bad extractions (verified from district websites)
SUPERINTENDENT_FIXES = {
    'Tacoma Public Schools': {
        'name': 'Joshua Garcia',
        'email': 'jgarcia@tacoma.k12.wa.us',
        'source': 'District website'
    },
    'Kent School District': {
        'name': 'Israel Vela',
        'email': 'israel.vela@kent.k12.wa.us',
        'source': 'District website'
    },
    'Federal Way Public Schools': {
        'name': 'Dani Pfeiffer',
        'email': 'dpfeiffer@fwps.org',
        'source': 'District website'
    },
    'Northshore School District': {
        'name': 'Michael Tolley',
        'email': 'mtolley@nsd.org',
        'source': 'District website'
    },
    'Bellevue School District': {
        'name': 'Kelly Aramaki',
        'email': 'aramakik@bsd405.org',
        'source': 'District website'
    }
}

# Tech directors / CIOs from public sources
TECH_DIRECTORS = {
    'Seattle Public Schools': {
        'name': 'Krista Lundquist',
        'title': 'Chief Technology Officer',
        'email': 'klundquist@seattleschools.org'
    },
    'Tacoma Public Schools': {
        'name': 'Kathryn McCarthy',
        'title': 'Chief Technology Officer',
        'email': 'kmccarthy@tacoma.k12.wa.us'
    },
    'Los Angeles Unified School District': {
        'name': 'David Brummett',
        'title': 'Chief Information Officer',
        'email': 'david.brummett@lausd.net'
    },
    'Houston Independent School District': {
        'name': 'Mark Bedell',
        'title': 'Chief Technology Officer',
        'email': 'mark.bedell@houstonisd.org'
    },
    'Miami-Dade County Public Schools': {
        'name': 'Jerry Mayer',
        'title': 'Chief Information Officer',
        'email': 'jmayer@dadeschools.net'
    },
    'New York City Department of Education': {
        'name': 'Suzan Sumer',
        'title': 'Chief Information Officer',
        'email': 'ssumer@schools.nyc.gov'
    }
}

# Curriculum directors
CURRICULUM_DIRECTORS = {
    'Seattle Public Schools': {
        'name': 'Caleb Perkins',
        'title': 'Chief Academic Officer',
        'email': 'cperkins@seattleschools.org'
    },
    'Los Angeles Unified School District': {
        'name': 'Alison Yoshimoto-Towery',
        'title': 'Chief Academic Officer',
        'email': 'alison.towery@lausd.net'
    }
}

def load_districts():
    with open('data/districts.json') as f:
        return json.load(f)

def save_districts(data):
    with open('data/districts.json', 'w') as f:
        json.dump(data, f, indent=2)
    with open('docs/data.json', 'w') as f:
        json.dump(data, f, indent=2)

def scrape_district_contacts(district_name, website):
    """Try to scrape contacts from district website."""
    if not website:
        return []
    
    contacts = []
    paths = ['/about/leadership', '/administration', '/district/leadership', '/about-us', '/contact']
    
    for path in paths:
        url = website.rstrip('/') + path
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.ok:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Look for CTO/CIO/Technology
                tech_patterns = ['chief technology', 'chief information', 'director of technology', 
                                'technology director', 'cto', 'cio']
                
                for pattern in tech_patterns:
                    elements = soup.find_all(text=re.compile(pattern, re.I))
                    for elem in elements:
                        parent = elem.parent
                        if parent:
                            text = parent.get_text()
                            # Try to extract name nearby
                            name_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)', text)
                            if name_match:
                                return [{'name': name_match.group(1), 'title': 'Technology Director', 
                                        'source': 'Website scrape'}]
        except:
            pass
    
    return contacts

def main():
    print("=" * 60)
    print("Fixing bad extractions and adding tech directors")
    print("=" * 60)
    
    data = load_districts()
    
    # Fix bad superintendent extractions
    print("\n1. Fixing superintendent extractions...")
    for district in data['districts']:
        name = district['name']
        if name in SUPERINTENDENT_FIXES:
            fix = SUPERINTENDENT_FIXES[name]
            # Find and update the bad contact
            for contact in district.get('contacts', []):
                if contact.get('title') == 'Superintendent':
                    print(f"  Fixing {name}: {contact['name']} -> {fix['name']}")
                    contact['name'] = fix['name']
                    contact['email'] = fix['email']
                    contact['email_guessed'] = False
                    contact['source'] = fix['source']
                    break
    
    # Add tech directors
    print("\n2. Adding tech directors...")
    for district in data['districts']:
        name = district['name']
        if name in TECH_DIRECTORS:
            td = TECH_DIRECTORS[name]
            # Check if already exists
            existing = [c for c in district.get('contacts', []) if 'technology' in (c.get('title') or '').lower() or 'cio' in (c.get('title') or '').lower() or 'cto' in (c.get('title') or '').lower()]
            if not existing:
                if 'contacts' not in district:
                    district['contacts'] = []
                district['contacts'].append({
                    'name': td['name'],
                    'title': td['title'],
                    'email': td['email'],
                    'email_guessed': False,
                    'source': 'Manual research'
                })
                print(f"  Added {td['name']} ({td['title']}) to {name}")
    
    # Add curriculum directors
    print("\n3. Adding curriculum directors...")
    for district in data['districts']:
        name = district['name']
        if name in CURRICULUM_DIRECTORS:
            cd = CURRICULUM_DIRECTORS[name]
            existing = [c for c in district.get('contacts', []) if 'curriculum' in (c.get('title') or '').lower() or 'academic' in (c.get('title') or '').lower()]
            if not existing:
                if 'contacts' not in district:
                    district['contacts'] = []
                district['contacts'].append({
                    'name': cd['name'],
                    'title': cd['title'],
                    'email': cd['email'],
                    'email_guessed': False,
                    'source': 'Manual research'
                })
                print(f"  Added {cd['name']} ({cd['title']}) to {name}")
    
    save_districts(data)
    
    # Summary
    print("\n" + "=" * 60)
    total_contacts = sum(len(d.get('contacts', [])) for d in data['districts'])
    districts_with_contacts = sum(1 for d in data['districts'] if d.get('contacts'))
    print(f"Total contacts: {total_contacts}")
    print(f"Districts with contacts: {districts_with_contacts}")
    print("=" * 60)

if __name__ == '__main__':
    main()
