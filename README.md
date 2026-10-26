# 💊 Pharmacy Fraud Detection

A Django web app that checks whether a pharmacy is genuine. Enter a pharmacy's name, and
optionally its PBM and address. The app looks for the pharmacy's real-world presence
online and on the map, then classifies it as **Found**, **Not Found** or **Fraud Pharmacy**.

## How it works

```text
Pharmacy name (+ optional address)
        │
        ▼
1. Find the official website        (DuckDuckGo search + URL probing)
        │
        ▼
2. Scrape addresses from the site   (BeautifulSoup, light crawling)
        │
        ▼
3. Geocode the addresses            (Nominatim / Google geocoding)
        │
        ▼
4. Confirm the storefront           (Google Places text search + Street View metadata)
        │
        ▼
5. Classify                         Found · Not Found · Fraud Pharmacy
```

### Classification rules
- **Found**: a storefront was located through Google Places, or an outdoor Street View
  panorama exists at the location, or the scraped address matches the input address.
- **Fraud Pharmacy**: the address you entered is more than **1 km** from where the pharmacy
  actually is (or more than 10 km when only a city was entered).
- **Not Found**: no location could be found for the pharmacy at all.

## Tech stack

| Area | Technology |
|---|---|
| Web framework | Django |
| Search | duckduckgo-search |
| Scraping | requests, BeautifulSoup |
| Geocoding & distance | geopy (Nominatim, geodesic distance) |
| Maps | Google Places API, Street View Metadata API |

## Getting started

### Prerequisites
- Python 3.10+
- A Google Maps Platform API key with the **Places API**, **Geocoding API** and
  **Street View Static API** enabled

### 1. Install dependencies
```bash
pip install django requests beautifulsoup4 geopy duckduckgo-search python-dotenv
```

### 2. Set environment variables
```bash
export MAPS_API_KEY=your_google_maps_api_key
export SECRET_KEY=your_django_secret_key
export DEBUG=True
```

### 3. Run the app
```bash
python manage.py migrate
python manage.py runserver
```
Open http://127.0.0.1:8000 and enter a pharmacy to verify.

## Project structure

```text
pharmacy-fraud-detection/
├── pharmacy_verifier/       # Django project settings and URLs
├── verifier/
│   ├── forms.py             # Pharmacy name, PBM and address form
│   ├── views.py             # Runs the verification pipeline
│   └── services/
│       ├── search.py        # Finds the official website
│       ├── scrape.py        # Extracts addresses from the site
│       ├── geocode.py       # Geocoding and distance helpers
│       ├── places.py        # Google Places storefront lookup
│       ├── streetview.py    # Street View panorama check
│       └── classify.py      # Found / Not Found / Fraud decision
└── templates/verifier/      # Home and result pages
```
