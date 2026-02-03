#!/usr/bin/env python3
"""
Get superintendent/contact data from reliable public sources.
"""

import json
import re
import csv
import io
import time
import requests
from pathlib import Path

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

TARGET_STATES = ['WA', 'OR', 'CA', 'TX', 'FL', 'NY']

def get_nces_directory():
    """
    NCES ELSI exports include superintendent names.
    We'll use their table generator API.
    """
    print("Fetching NCES district directory data...")
    
    # NCES has a public API for school search
    # https://nces.ed.gov/ccd/schoolsearch/
    
    results = {}
    
    for state in TARGET_STATES:
        print(f"  Searching {state}...")
        try:
            # Use their search API
            url = f"https://nces.ed.gov/ccd/schoolsearch/school_list.asp"
            params = {
                'Search': 1,
                'State': state,
                'SchoolType': 1,  # Regular schools
                'SpecificSchlTypes': 'all',
                'IncGrade': '-1',
                'LoGrade': '-1',
                'HiGrade': '-1'
            }
            
            # Actually let's try a direct approach - download their files
            # CCD LEA (district) file has superintendent
            
        except Exception as e:
            print(f"    Error: {e}")
        
        time.sleep(0.5)
    
    return results

def scrape_ospi_directory():
    """
    Scrape Washington OSPI EDS Directory directly.
    """
    print("\nScraping OSPI Directory (Washington)...")
    
    contacts = {}
    base_url = "https://eds.ospi.k12.wa.us"
    
    # Get the search page
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        # First, get the page to capture any needed tokens
        resp = session.get(f"{base_url}/DirectoryEDS.aspx", timeout=30)
        
        # Look for district links in the page
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find all links that might be district pages
        links = soup.find_all('a', href=True)
        district_links = [l for l in links if 'District' in l.text or 'School' in l.text]
        print(f"  Found {len(district_links)} potential district links")
        
        # Look for a district list/search
        forms = soup.find_all('form')
        print(f"  Found {len(forms)} forms")
        
        # Check for select dropdowns (often have district lists)
        selects = soup.find_all('select')
        for sel in selects:
            name = sel.get('name', sel.get('id', 'unnamed'))
            opts = sel.find_all('option')
            print(f"  Select '{name}': {len(opts)} options")
            if len(opts) > 0 and len(opts) < 20:
                print(f"    Options: {[o.text for o in opts[:5]]}")
                
    except Exception as e:
        print(f"  Error: {e}")
    
    return contacts

def scrape_greatschools():
    """
    GreatSchools has district profiles with superintendent names.
    """
    print("\nChecking GreatSchools for superintendent data...")
    
    # They have a structured URL pattern
    # https://www.greatschools.org/washington/seattle/Seattle-Public-Schools/
    
    test_districts = [
        ('WA', 'seattle', 'Seattle-Public-Schools'),
        ('WA', 'tacoma', 'Tacoma-Public-Schools'),
    ]
    
    for state, city, district in test_districts:
        url = f"https://www.greatschools.org/{state.lower()}/{city}/{district}/"
        print(f"  Checking {district}...")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.ok:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Look for superintendent info
                text = soup.get_text()
                if 'superintendent' in text.lower():
                    # Find the context
                    lines = [l.strip() for l in text.split('\n') if 'superintendent' in l.lower()]
                    for line in lines[:3]:
                        print(f"    Found: {line[:100]}")
        except Exception as e:
            print(f"    Error: {e}")
        
        time.sleep(1)

def scrape_ballotpedia():
    """
    Ballotpedia has school board and superintendent info.
    """
    print("\nChecking Ballotpedia for superintendent data...")
    
    # Example: https://ballotpedia.org/Seattle_Public_Schools,_Washington
    districts = [
        "Seattle_Public_Schools,_Washington",
        "Los_Angeles_Unified_School_District,_California",
    ]
    
    for district in districts:
        url = f"https://ballotpedia.org/{district}"
        print(f"  Checking {district.split(',')[0]}...")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.ok:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Look for superintendent in infobox
                infobox = soup.find('table', class_='infobox')
                if infobox:
                    rows = infobox.find_all('tr')
                    for row in rows:
                        text = row.get_text()
                        if 'superintendent' in text.lower():
                            print(f"    {text.strip()[:80]}")
        except Exception as e:
            print(f"    Error: {e}")
        
        time.sleep(1)

def try_direct_state_files():
    """
    Try to find direct data file downloads from state DOEs.
    """
    print("\nLooking for state data file downloads...")
    
    state_files = {
        'WA': [
            # OSPI Report Card Data
            'https://washingtonstatereportcard.ospi.k12.wa.us/ReportCard/ViewSchoolOrDistrict/103300',
            # OSPI Data Files
            'https://www.k12.wa.us/data-reporting/data-portal',
        ],
        'OR': [
            # ODE Directory
            'https://www.oregon.gov/ode/schools-and-districts/Pages/School-Directory.aspx',
        ],
        'CA': [
            # CDE Public Schools
            'https://www.cde.ca.gov/ds/si/ds/pubschls.asp',
        ],
    }
    
    # California has direct download files
    print("  Checking California CDE public school file...")
    try:
        # They have a text file download
        url = "https://www.cde.ca.gov/schooldirectory/report?rid=dl1"
        resp = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
        print(f"    Status: {resp.status_code}, Content-Type: {resp.headers.get('content-type', 'unknown')}")
    except Exception as e:
        print(f"    Error: {e}")

def main():
    print("=" * 60)
    print("Superintendent Contact Finder")
    print("=" * 60)
    
    # Try multiple approaches
    scrape_ospi_directory()
    scrape_ballotpedia()
    try_direct_state_files()
    
    print("\n" + "=" * 60)
    print("Summary: Best data sources identified")
    print("=" * 60)

if __name__ == '__main__':
    main()
