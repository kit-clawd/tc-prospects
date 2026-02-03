#!/usr/bin/env python3
"""
Scrape district staff directories using headless browser.
Handles JS-rendered pages that simple requests can't.
"""

import json
import re
import time
import subprocess
from pathlib import Path

def load_districts():
    with open('data/districts.json') as f:
        return json.load(f)

def save_districts(data):
    with open('data/districts.json', 'w') as f:
        json.dump(data, f, indent=2)
    with open('docs/data.json', 'w') as f:
        json.dump(data, f, indent=2)

def extract_contacts_from_text(text):
    """Extract contact info from page text."""
    contacts = []
    
    # Common title patterns
    title_patterns = [
        (r'(?:chief\s+)?technology\s+(?:officer|director)', 'Technology Director'),
        (r'(?:chief\s+)?information\s+(?:officer|director)', 'Chief Information Officer'),
        (r'(?:chief\s+)?academic\s+(?:officer|director)', 'Chief Academic Officer'),
        (r'curriculum\s+(?:director|coordinator)', 'Curriculum Director'),
        (r'(?:assistant|associate)\s+superintendent', 'Assistant Superintendent'),
        (r'director\s+of\s+(?:technology|it|information)', 'Director of Technology'),
        (r'director\s+of\s+(?:curriculum|instruction)', 'Director of Curriculum'),
        (r'(?:it|tech)\s+director', 'IT Director'),
    ]
    
    # Find emails
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text.lower())
    
    # Find names near titles
    for pattern, title in title_patterns:
        matches = list(re.finditer(pattern, text.lower()))
        for match in matches:
            # Look for name nearby (within 200 chars before or after)
            start = max(0, match.start() - 200)
            end = min(len(text), match.end() + 200)
            context = text[start:end]
            
            # Look for name pattern
            name_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)', context)
            if name_match:
                name = name_match.group(1)
                # Find email in context
                email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', context.lower())
                email = email_match.group(0) if email_match else None
                
                contacts.append({
                    'name': name,
                    'title': title,
                    'email': email,
                    'source': 'Website scrape'
                })
    
    return contacts

def scrape_district_with_browser(district_name, website):
    """Use clawdbot browser to scrape a district's staff directory."""
    if not website:
        return []
    
    # Common staff directory paths
    paths = [
        '/about/leadership',
        '/about/administration',
        '/our-district/leadership',
        '/district/administration', 
        '/about-us/leadership',
        '/departments',
        '/staff-directory',
        '/administration',
        '/leadership',
        '/contact-us',
    ]
    
    all_contacts = []
    
    for path in paths[:3]:  # Try first 3 paths to save time
        url = website.rstrip('/') + path
        print(f"    Trying {path}...", end=' ', flush=True)
        
        try:
            # Use clawdbot browser snapshot
            result = subprocess.run(
                ['clawdbot', 'browser', 'snapshot', '--target-url', url, 
                 '--profile', 'clawd', '--timeout-ms', '15000', '--max-chars', '50000'],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                text = result.stdout
                contacts = extract_contacts_from_text(text)
                if contacts:
                    print(f"Found {len(contacts)} contacts!")
                    all_contacts.extend(contacts)
                    break  # Got contacts, stop trying paths
                else:
                    print("No contacts found")
            else:
                print("Failed")
        except Exception as e:
            print(f"Error: {e}")
    
    # Deduplicate by name
    seen = set()
    unique = []
    for c in all_contacts:
        if c['name'] not in seen:
            seen.add(c['name'])
            unique.append(c)
    
    return unique

def main():
    print("=" * 60)
    print("Staff Directory Scraper (Browser-based)")
    print("=" * 60)
    
    data = load_districts()
    
    # Focus on districts that:
    # 1. Have a website
    # 2. Have enrollment > 10000 (worth the effort)
    # 3. Don't already have tech director contacts
    
    districts_to_scrape = []
    for d in data['districts']:
        if not d.get('website'):
            continue
        if (d.get('enrollment') or 0) < 10000:
            continue
        
        # Check if already has tech director
        has_tech = any(
            'tech' in (c.get('title') or '').lower() or 
            'cio' in (c.get('title') or '').lower() or
            'cto' in (c.get('title') or '').lower()
            for c in d.get('contacts', [])
        )
        if not has_tech:
            districts_to_scrape.append(d)
    
    print(f"\nFound {len(districts_to_scrape)} districts to scrape (>10k enrollment, no tech director)")
    print("=" * 60)
    
    updated = 0
    for i, district in enumerate(districts_to_scrape[:20]):  # Limit to 20 for now
        name = district['name']
        website = district['website']
        
        print(f"\n[{i+1}/{min(20, len(districts_to_scrape))}] {name}")
        print(f"    Website: {website}")
        
        contacts = scrape_district_with_browser(name, website)
        
        if contacts:
            if 'contacts' not in district:
                district['contacts'] = []
            
            # Add new contacts (avoid duplicates)
            existing_names = {c.get('name') for c in district['contacts']}
            for c in contacts:
                if c['name'] not in existing_names:
                    district['contacts'].append(c)
                    print(f"    ✓ Added: {c['name']} ({c['title']})")
                    updated += 1
        
        time.sleep(1)  # Be polite
    
    save_districts(data)
    
    print("\n" + "=" * 60)
    print(f"Done! Added {updated} new contacts")
    print("=" * 60)

if __name__ == '__main__':
    main()
