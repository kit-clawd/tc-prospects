# TC Prospects

Simple school district prospecting tool. Aggregates free public data sources to identify potential sales opportunities.

## Data Sources

- **NCES** (National Center for Education Statistics) - District demographics, enrollment, contacts
- **USASpending.gov** - Federal education grants by recipient
- **Edunomics Lab** - ESSER spending by district (manual download)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Fetch fresh data
python scripts/fetch_data.py

# Serve the browser UI
python -m http.server 8080 -d docs
# Open http://localhost:8080
```

## Project Structure

```
tc-prospects/
├── scripts/
│   └── fetch_data.py    # Data fetching from APIs
├── data/
│   └── districts.json   # Aggregated district data
├── docs/
│   ├── index.html       # Browse UI
│   └── data.json        # Data for UI (copy of districts.json)
└── README.md
```

## Filtering Ideas

- Large districts (>10k enrollment) not yet customers
- Districts with high federal funding (active buyers)
- Districts in states with curriculum mandates
- Districts whose ESSER funds are expiring (budget pressure)

## Future Enhancements

- [ ] Add competitor tracking (board minutes scraping)
- [ ] Tech director contact enrichment
- [ ] RFP alert monitoring
- [ ] CRM integration
