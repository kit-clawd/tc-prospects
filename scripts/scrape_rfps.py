#!/usr/bin/env python3
"""
Scrape state procurement sites for education RFPs.
These are gold for sales teams - active buying signals.
"""

import json
import re
import time
from datetime import datetime, timedelta
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

def scrape_wa_webs():
    """
    Washington WEBS (Washington Electronic Business Solution)
    https://pr-webs-vendor.des.wa.gov/
    """
    print("Scraping Washington WEBS procurement...")
    rfps = []
    
    # Search for education-related bids
    # The public search is at https://pr-webs-vendor.des.wa.gov/
    url = "https://pr-webs-vendor.des.wa.gov/Search.aspx"
    
    try:
        session = requests.Session()
        resp = session.get("https://pr-webs-vendor.des.wa.gov/", headers=HEADERS, timeout=15)
        print(f"  WEBS homepage: {resp.status_code}")
        
        # Try the bid search
        search_url = "https://fortress.wa.gov/ga/webs/bidcalendar.aspx"
        resp = session.get(search_url, headers=HEADERS, timeout=15)
        if resp.ok:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Look for education/school keywords in active bids
            text = soup.get_text().lower()
            edu_keywords = ['school', 'education', 'district', 'curriculum', 'typing', 'k-12', 'student']
            
            for kw in edu_keywords:
                if kw in text:
                    print(f"    Found '{kw}' mentions in bid calendar")
            
            # Extract bid items
            tables = soup.find_all('table')
            print(f"  Found {len(tables)} tables")
            
    except Exception as e:
        print(f"  Error: {e}")
    
    return rfps

def scrape_tx_comptroller():
    """
    Texas Comptroller procurement
    https://comptroller.texas.gov/purchasing/
    """
    print("\nScraping Texas Comptroller procurement...")
    
    # Texas smartbuy
    url = "https://www.txsmartbuy.com/esbdSearch"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"  TxSmartBuy: {resp.status_code}")
        
        if resp.ok:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Look for search functionality
            forms = soup.find_all('form')
            print(f"  Found {len(forms)} forms")
            
    except Exception as e:
        print(f"  Error: {e}")

def scrape_ca_caleprocure():
    """
    California Cal eProcure
    https://caleprocure.ca.gov/
    """
    print("\nScraping California CaleProcure...")
    
    url = "https://caleprocure.ca.gov/pages/PublicSearch/supplier-702702702702-publicSearch.xhtml"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        print(f"  CaleProcure: {resp.status_code}")
        
    except Exception as e:
        print(f"  Error: {e}")

def scrape_govwin():
    """
    Check GovWin IQ for education contracts (public preview).
    """
    print("\nChecking GovWin education contracts...")
    
    # GovWin has some public data
    url = "https://iq.govwin.com/neo/marketAnalysis/view/Education/8"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"  GovWin status: {resp.status_code}")
        
    except Exception as e:
        print(f"  Error: {e}")

def scrape_bidnet():
    """
    BidNet Direct - aggregates government RFPs.
    Free search available.
    """
    print("\nScraping BidNet for education bids...")
    
    # Public search
    url = "https://www.bidnetdirect.com/search"
    params = {
        'q': 'typing curriculum software school district',
        'filterRegion': 'US',
    }
    
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        print(f"  BidNet search: {resp.status_code}")
        
        if resp.ok:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Look for bid listings
            results = soup.find_all(['article', 'div'], class_=re.compile(r'bid|result|listing', re.I))
            print(f"  Found {len(results)} potential bid elements")
            
            # Try to find bid titles
            links = soup.find_all('a', href=True)
            bid_links = [l for l in links if '/bid/' in l['href'].lower() or '/opportunity/' in l['href'].lower()]
            print(f"  Found {len(bid_links)} bid links")
            
            for link in bid_links[:5]:
                print(f"    - {link.get_text().strip()[:60]}")
                
    except Exception as e:
        print(f"  Error: {e}")

def scrape_publicsurplus():
    """
    PublicSurplus and other edu-focused RFP aggregators.
    """
    print("\nChecking education procurement aggregators...")
    
    # EdWeek marketplace
    url = "https://marketbrief.edweek.org/"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"  EdWeek MarketBrief: {resp.status_code}")
        
    except Exception as e:
        print(f"  Error: {e}")

def main():
    print("=" * 60)
    print("RFP / Procurement Scraper - Buying Signals")
    print("=" * 60)
    
    # Try various procurement sources
    scrape_wa_webs()
    scrape_tx_comptroller()
    scrape_ca_caleprocure()
    scrape_bidnet()
    scrape_publicsurplus()
    
    print("\n" + "=" * 60)
    print("Summary: State procurement sites require login/session for full access.")
    print("Best free options:")
    print("  - BidNet Direct (free search)")
    print("  - GovWin IQ (limited free)")
    print("  - State-specific portals (varies)")
    print("=" * 60)

if __name__ == '__main__':
    main()
