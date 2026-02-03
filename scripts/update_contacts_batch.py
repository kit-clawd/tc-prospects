#!/usr/bin/env python3
"""
Update contacts with verified data from web scraping.
"""

import json

def load_districts():
    with open('data/districts.json') as f:
        return json.load(f)

def save_districts(data):
    with open('data/districts.json', 'w') as f:
        json.dump(data, f, indent=2)
    with open('docs/data.json', 'w') as f:
        json.dump(data, f, indent=2)

# Verified contacts from web scraping
NEW_CONTACTS = {
    'Seattle Public Schools': [
        {'name': 'Ben Shuldiner', 'title': 'Superintendent', 'email': 'bshuldiner@seattleschools.org', 'source': 'District website'},
        {'name': 'Carlos Del Valle', 'title': 'Assistant Superintendent of Technology', 'email': 'cdelvalle@seattleschools.org', 'source': 'District website'},
        {'name': 'Fred Podesta', 'title': 'Chief Operations Officer', 'email': 'fpodesta@seattleschools.org', 'source': 'District website'},
        {'name': 'Bev Redmond', 'title': 'Chief of Staff', 'email': 'bredmond@seattleschools.org', 'source': 'District website'},
        {'name': 'Dr. Kurt Buttleman', 'title': 'Assistant Superintendent of Finance', 'email': 'kbuttleman@seattleschools.org', 'source': 'District website'},
    ],
}

# Updates to existing contacts (name changes, etc.)
UPDATES = {
    'Seattle Public Schools': {
        'old_superintendent': 'Brent Jones',
        'new_superintendent': 'Ben Shuldiner',
    }
}

def main():
    print("=" * 60)
    print("Updating contacts with verified data")
    print("=" * 60)
    
    data = load_districts()
    updated_count = 0
    
    for district in data['districts']:
        name = district['name']
        
        # Check if we have new contacts for this district
        if name in NEW_CONTACTS:
            print(f"\n{name}:")
            
            if 'contacts' not in district:
                district['contacts'] = []
            
            existing_names = {c.get('name') for c in district['contacts']}
            
            for new_contact in NEW_CONTACTS[name]:
                # Check if we need to update existing or add new
                if new_contact['name'] in existing_names:
                    # Update existing
                    for c in district['contacts']:
                        if c.get('name') == new_contact['name']:
                            c.update(new_contact)
                            print(f"  Updated: {new_contact['name']}")
                            updated_count += 1
                else:
                    # Check if this replaces an old contact (e.g., new superintendent)
                    if name in UPDATES and new_contact['title'] == 'Superintendent':
                        old_name = UPDATES[name].get('old_superintendent')
                        for c in district['contacts']:
                            if c.get('name') == old_name:
                                print(f"  Replacing {old_name} with {new_contact['name']}")
                                c.update(new_contact)
                                updated_count += 1
                                break
                        else:
                            district['contacts'].append(new_contact)
                            print(f"  Added: {new_contact['name']} ({new_contact['title']})")
                            updated_count += 1
                    else:
                        district['contacts'].append(new_contact)
                        print(f"  Added: {new_contact['name']} ({new_contact['title']})")
                        updated_count += 1
    
    save_districts(data)
    
    print("\n" + "=" * 60)
    print(f"Updated {updated_count} contacts")
    print("=" * 60)

if __name__ == '__main__':
    main()
