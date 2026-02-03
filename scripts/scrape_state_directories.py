#!/usr/bin/env python3
"""
Scrape state education directories for district staff contacts.
These are official sources with structured data.
"""

import json
import re
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def load_districts():
    with open('data/districts.json') as f:
        return json.load(f)

def save_districts(data):
    with open('data/districts.json', 'w') as f:
        json.dump(data, f, indent=2)
    with open('docs/data.json', 'w') as f:
        json.dump(data, f, indent=2)

def scrape_wa_k12_directory():
    """
    Washington K12 data portal has district directory.
    """
    print("Scraping Washington directory...")
    contacts = {}
    
    # Try OSPI report card - has superintendent names
    districts = [
        ('Seattle School District No. 1', '103300'),
        ('Spokane School District 81', '105000'),
        ('Tacoma School District 10', '102700'),
    ]
    
    for name, code in districts:
        url = f"https://washingtonstatereportcard.ospi.k12.wa.us/ReportCard/ViewSchoolOrDistrict/{code}"
        print(f"  Checking {name}...")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.ok:
                # Look for superintendent info
                soup = BeautifulSoup(resp.text, 'html.parser')
                text = soup.get_text()
                if 'superintendent' in text.lower():
                    print(f"    Has superintendent data")
        except Exception as e:
            print(f"    Error: {e}")
        time.sleep(1)
    
    return contacts

def scrape_texas_tea():
    """
    Texas Education Agency has district directory.
    https://tea.texas.gov/texas-schools/general-information/school-district-locator
    """
    print("\nScraping Texas TEA directory...")
    
    # TEA has AskTED database
    # https://tealprod.tea.state.tx.us/Tea.AskTed.Web/Forms/Home.aspx
    url = "https://tealprod.tea.state.tx.us/Tea.AskTed.Web/Forms/Home.aspx"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"  TEA AskTED status: {resp.status_code}")
        if resp.ok:
            soup = BeautifulSoup(resp.text, 'html.parser')
            forms = soup.find_all('form')
            print(f"  Found {len(forms)} forms")
    except Exception as e:
        print(f"  Error: {e}")

def scrape_ca_cde():
    """
    California CDE school directory.
    https://www.cde.ca.gov/SchoolDirectory/
    """
    print("\nScraping California CDE directory...")
    
    # CDE has downloadable text files
    # https://www.cde.ca.gov/ds/si/ds/pubschls.asp - public schools
    url = "https://www.cde.ca.gov/ds/si/ds/pubschls.asp"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.ok:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Look for download links
            links = soup.find_all('a', href=True)
            download_links = [l for l in links if 'download' in l.text.lower() or '.txt' in l['href'].lower()]
            print(f"  Found {len(download_links)} download links")
            for link in download_links[:3]:
                print(f"    {link.text.strip()}: {link['href']}")
    except Exception as e:
        print(f"  Error: {e}")

def scrape_fl_fldoe():
    """
    Florida DOE school directory.
    """
    print("\nScraping Florida FLDOE directory...")
    
    url = "https://www.fldoe.org/accountability/data-sys/school-dis-data/superintendents.stml"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.ok:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # This page lists all FL superintendents!
            tables = soup.find_all('table')
            print(f"  Found {len(tables)} tables")
            
            if tables:
                rows = tables[0].find_all('tr')
                print(f"  Found {len(rows)} rows in first table")
                
                contacts = []
                for row in rows[1:]:  # Skip header
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        district = cells[0].get_text().strip()
                        supt = cells[1].get_text().strip() if len(cells) > 1 else ''
                        email_cell = cells[2] if len(cells) > 2 else None
                        
                        # Extract email from link
                        email = None
                        if email_cell:
                            link = email_cell.find('a', href=True)
                            if link and 'mailto:' in link['href']:
                                email = link['href'].replace('mailto:', '')
                        
                        if district and supt:
                            contacts.append({
                                'district': district,
                                'name': supt,
                                'email': email
                            })
                
                print(f"  Extracted {len(contacts)} FL superintendents!")
                return contacts
    except Exception as e:
        print(f"  Error: {e}")
    
    return []

def main():
    print("=" * 60)
    print("State Directory Scraper")
    print("=" * 60)
    
    # Florida has the best superintendent list
    fl_contacts = scrape_fl_fldoe()
    
    if fl_contacts:
        print(f"\nUpdating Florida districts with {len(fl_contacts)} superintendents...")
        
        data = load_districts()
        updated = 0
        
        for contact in fl_contacts:
            # Find matching district
            for d in data['districts']:
                if d['state'] != 'FL':
                    continue
                
                # Match by name (fuzzy)
                district_name = d['name'].lower()
                contact_district = contact['district'].lower()
                
                if (contact_district in district_name or 
                    district_name in contact_district or
                    contact_district.split()[0] in district_name):
                    
                    # Check if already has superintendent
                    has_supt = any(c.get('title') == 'Superintendent' for c in d.get('contacts', []))
                    
                    if not has_supt and contact.get('name'):
                        if 'contacts' not in d:
                            d['contacts'] = []
                        
                        d['contacts'].insert(0, {
                            'name': contact['name'],
                            'title': 'Superintendent',
                            'email': contact.get('email'),
                            'source': 'Florida DOE'
                        })
                        print(f"  ✓ {d['name']}: {contact['name']}")
                        updated += 1
                    break
        
        save_districts(data)
        print(f"\nUpdated {updated} Florida districts")
    
    # Try other states
    scrape_wa_k12_directory()
    scrape_texas_tea()
    scrape_ca_cde()
    
    print("\n" + "=" * 60)
    print("Done!")

if __name__ == '__main__':
    main()
