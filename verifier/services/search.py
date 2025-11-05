from duckduckgo_search import DDGS
from urllib.parse import urlparse
import re
import requests

EXCLUDED_DOMAINS = {
	'facebook.com', 'm.facebook.com', 'twitter.com', 'x.com', 'instagram.com',
	'yelp.com', 'yellowpages.com', 'healthgrades.com', 'linkedin.com',
	'bing.com', 'google.com', 'maps.google.com', 'mapquest.com', 'apple.com',
}

KNOWN_BRAND_DOMAINS = {
	'walgreens': 'https://www.walgreens.com',
	'cvs': 'https://www.cvs.com',
	'rite aid': 'https://www.riteaid.com',
	'apollo pharmacy': 'https://www.apollopharmacy.in',
	'apollopharmacy': 'https://www.apollopharmacy.in',
}


def _normalize_name(name: str) -> str:
	s = name.lower().strip()
	s = re.sub(r"[^a-z0-9\s]", "", s)
	s = re.sub(r"\s+", " ", s)
	return s


def _probe_url(url: str) -> bool:
	try:
		r = requests.head(url, timeout=8, allow_redirects=True)
		return r.status_code < 400
	except Exception:
		return False


def _guess_official_url(pharmacy_name: str) -> str | None:
	n = _normalize_name(pharmacy_name)
	# Direct brand map first
	for k, v in KNOWN_BRAND_DOMAINS.items():
		if k in n:
			if _probe_url(v):
				return v
	# Try normalized domain guesses
	token = n.replace(' ', '')
	for domain in (f"https://www.{token}.com", f"https://{token}.com", f"https://www.{token}.in", f"https://{token}.in"):
		if _probe_url(domain):
			return domain
	return None


def find_official_url(pharmacy_name: str, address: str | None = None):
	query = pharmacy_name
	if address:
		query = f"{pharmacy_name} {address}"
	name_l = pharmacy_name.lower()
	# Basic brand/region bias
	if 'apollo' in name_l:
		region = 'in-en'
	else:
		region = 'us-en'

	results = []
	try:
		with DDGS() as ddgs:
			results = ddgs.text(query, region=region, max_results=15)
	except Exception as e:
		print(f"[DuckDuckGo] search error: {e}")
		results = []

	best_url = None
	best_score = -1
	for r in results or []:
		url = r.get('href') or r.get('url') or ''
		if not url:
			continue
		parsed = urlparse(url)
		domain = parsed.netloc.lower().split(':')[0]
		if any(ex in domain for ex in EXCLUDED_DOMAINS):
			continue
		score = 0
		title = (r.get('title') or '').lower()
		snippet = (r.get('body') or '').lower()
		if name_l in title:
			score += 3
		if name_l in snippet:
			score += 1
		# Prefer simple domains (likely official sites)
		if domain.count('.') <= 2:
			score += 1
		# Brand bias: URLs having the brand name in domain (e.g., apollopharmacy.in)
		brand_tokens = set(name_l.split()) | {name_l + 's'}
		if any(token in domain for token in brand_tokens):
			score += 2
		if score > best_score:
			best_score = score
			best_url = url

	if best_url:
		return best_url
	# Fallback if search failed or yielded nothing
	return _guess_official_url(pharmacy_name)