#!/usr/bin/env python3
"""
Scrape district websites for contact information.
Looks for staff directories, admin contacts, tech directors, etc.
"""

import json
import re
import time
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent.parent / "data"
DOCS_DIR = Path(__file__).parent.parent / "docs"

# Contact titles we're looking for
TARGET_TITLES = [
    "superintendent",
    "assistant superintendent", 
    "deputy superintendent",
    "chief technology officer",
    "cto",
    "chief information officer",
    "cio",
    "technology director",
    "director of technology",
    "it director",
    "director of information",
    "instructional technology",
    "digital learning",
    "curriculum director",
    "director of curriculum",
    "academic officer",
    "chief academic",
    "purchasing director",
    "procurement",
    "business manager",
    "chief financial",
    "cfo",
    "chief operating",
    "coo",
]

# Email regex
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

# Phone regex (US format)
PHONE_PATTERN = re.compile(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')

# Name pattern - looks like "First Last" or "First M. Last"
NAME_PATTERN = re.compile(r'^[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)?$')


def get_session():
    """Create a requests session with appropriate headers."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    return session


def fetch_page(session, url, timeout=15):
    """Fetch a page and return BeautifulSoup object."""
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, 'html.parser')
    except:
        return None


def find_staff_pages(session, base_url):
    """Find staff directory and about/leadership pages."""
    pages = []
    soup = fetch_page(session, base_url)
    if not soup:
        return pages
    
    # Keywords that suggest staff/leadership pages
    keywords = ['staff', 'directory', 'leadership', 'administration', 'cabinet', 
                'team', 'about', 'contact', 'superintendent', 'board']
    
    seen_urls = set()
    for link in soup.find_all('a', href=True):
        href = link.get('href', '').lower()
        text = link.get_text().lower()
        
        if any(kw in href or kw in text for kw in keywords):
            full_url = urljoin(base_url, link['href'])
            # Stay on same domain
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                if full_url not in seen_urls:
                    seen_urls.add(full_url)
                    pages.append(full_url)
    
    # Also try common patterns
    common = ['/staff', '/directory', '/administration', '/leadership', 
              '/about/leadership', '/about/administration', '/contact']
    for path in common:
        url = urljoin(base_url, path)
        if url not in seen_urls:
            pages.append(url)
    
    return pages[:10]  # Limit to 10 pages


def looks_like_name(text):
    """Check if text looks like a person's name."""
    if not text or len(text) < 4 or len(text) > 50:
        return False
    
    # Must have at least 2 words
    words = text.strip().split()
    if len(words) < 2 or len(words) > 5:
        return False
    
    # Common non-name words
    bad_words = ['the', 'our', 'meet', 'contact', 'about', 'office', 'department',
                 'district', 'school', 'public', 'services', 'board', 'click',
                 'view', 'read', 'more', 'home', 'page', 'menu', 'search',
                 'phone', 'email', 'fax', 'address', 'location']
    if any(w.lower() in bad_words for w in words):
        return False
    
    # First word should start with capital
    if not words[0][0].isupper():
        return False
    
    # Check against name pattern
    if NAME_PATTERN.match(text.strip()):
        return True
    
    return False


def extract_contacts_strict(soup, url):
    """Extract contacts with strict quality checks - must have email."""
    contacts = []
    page_text = soup.get_text()
    
    # Find all emails on page
    all_emails = EMAIL_PATTERN.findall(page_text)
    
    # Filter out generic emails
    generic_prefixes = ['info@', 'contact@', 'support@', 'admin@', 'webmaster@', 
                        'noreply@', 'help@', 'office@', 'communications@', 'hr@']
    person_emails = [e for e in all_emails 
                     if not any(e.lower().startswith(g) for g in generic_prefixes)]
    
    if not person_emails:
        return contacts
    
    # For each email, try to find associated name and title
    for email in set(person_emails):
        # Find elements containing this email
        email_elements = soup.find_all(string=re.compile(re.escape(email)))
        
        for elem in email_elements:
            # Look in parent containers for name/title
            parent = elem.find_parent(['div', 'li', 'tr', 'td', 'article', 'section', 'p'])
            if not parent:
                continue
            
            parent_text = parent.get_text()
            
            # Find title match
            matched_title = None
            for title in TARGET_TITLES:
                if title in parent_text.lower():
                    matched_title = title
                    break
            
            # Find name - look in headings, bold, strong, links
            name = None
            for tag in parent.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b']):
                tag_text = tag.get_text().strip()
                if looks_like_name(tag_text):
                    name = tag_text
                    break
            
            # If no name found in markup, try to extract from text near email
            if not name:
                lines = parent_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if looks_like_name(line):
                        name = line
                        break
            
            # Find phone
            phones = PHONE_PATTERN.findall(parent_text)
            phone = phones[0] if phones else None
            
            # Only add if we have a name
            if name:
                contacts.append({
                    'name': name,
                    'email': email,
                    'title': matched_title.title() if matched_title else None,
                    'phone': phone,
                })
                break  # Only add once per email
    
    # Dedupe
    seen = set()
    unique = []
    for c in contacts:
        key = c['email'].lower()
        if key not in seen:
            seen.add(key)
            unique.append(c)
    
    return unique


def scrape_district(district, session):
    """Scrape contacts for a single district."""
    website = district.get('website')
    if not website:
        return None
    
    if not website.startswith('http'):
        website = 'https://' + website
    
    result = {
        'district': district['name'],
        'website': website,
        'contacts': [],
        'pages_checked': 0,
    }
    
    try:
        # Find staff/directory pages
        pages_to_check = find_staff_pages(session, website)
        pages_to_check.insert(0, website)  # Include homepage
        
        all_contacts = []
        seen_emails = set()
        
        for page_url in pages_to_check[:8]:  # Check up to 8 pages
            result['pages_checked'] += 1
            soup = fetch_page(session, page_url)
            if not soup:
                continue
            
            page_contacts = extract_contacts_strict(soup, page_url)
            for c in page_contacts:
                if c['email'].lower() not in seen_emails:
                    seen_emails.add(c['email'].lower())
                    all_contacts.append(c)
            
            time.sleep(0.5)  # Be polite
        
        result['contacts'] = all_contacts
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def load_districts():
    """Load district data with known websites."""
    known_websites = {
        "Seattle Public Schools": "https://www.seattleschools.org",
        "Spokane Public Schools": "https://www.spokaneschools.org",
        "Tacoma Public Schools": "https://www.tacomaschools.org",
        "Kent School District": "https://www.kent.k12.wa.us",
        "Federal Way Public Schools": "https://www.fwps.org",
        "Lake Washington School District": "https://www.lwsd.org",
        "Northshore School District": "https://www.nsd.org",
        "Bellevue School District": "https://bsd405.org",
        "Los Angeles Unified School District": "https://www.lausd.org",
        "San Diego Unified School District": "https://www.sandiegounified.org",
        "Houston Independent School District": "https://www.houstonisd.org",
        "Dallas Independent School District": "https://www.dallasisd.org",
        "Austin Independent School District": "https://www.austinisd.org",
        "Portland Public Schools": "https://www.pps.net",
        "Miami-Dade County Public Schools": "https://www.dadeschools.net",
        "Hillsborough County Public Schools": "https://www.hillsboroughschools.org",
        "Orange County Public Schools": "https://www.ocps.net",
        "New York City Department of Education": "https://www.schools.nyc.gov",
    }
    
    data_path = DATA_DIR / "districts.json"
    with open(data_path) as f:
        data = json.load(f)
    
    for district in data['districts']:
        if district['name'] in known_websites:
            district['website'] = known_websites[district['name']]
    
    return data


def main():
    import sys
    print("Loading district data...", flush=True)
    data = load_districts()
    
    # Only scrape districts with websites
    districts_with_sites = [d for d in data['districts'] if d.get('website')]
    print(f"Scraping {len(districts_with_sites)} districts with known websites...", flush=True)
    
    session = get_session()
    
    for i, district in enumerate(districts_with_sites):
        print(f"  [{i+1}/{len(districts_with_sites)}] {district['name']}...", end=" ", flush=True)
        result = scrape_district(district, session)
        
        if result:
            district['contacts'] = result['contacts']
            print(f"found {len(result['contacts'])} contacts ({result['pages_checked']} pages)", flush=True)
        else:
            print("skipped", flush=True)
        
        time.sleep(1)
    
    # Save
    output_path = DATA_DIR / "districts.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nSaved to {output_path}", flush=True)
    
    docs_path = DOCS_DIR / "data.json"
    with open(docs_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Copied to {docs_path}", flush=True)
    
    # Summary
    total_contacts = sum(len(d.get('contacts', [])) for d in data['districts'])
    districts_with_contacts = sum(1 for d in data['districts'] if d.get('contacts'))
    print(f"\n=== Summary ===", flush=True)
    print(f"Districts scraped: {len(districts_with_sites)}", flush=True)
    print(f"Districts with contacts: {districts_with_contacts}", flush=True)
    print(f"Total contacts found: {total_contacts}", flush=True)


if __name__ == "__main__":
    main()
