from django.shortcuts import render
from django.conf import settings
from .forms import PharmacyForm
from .services.search import find_official_url
from .services.scrape import scrape_addresses_from_site, scrape_addresses_with_crawl
from .services.geocode import geocode_address, geocode_all, search_place, pick_nearest, geocode_best, extract_city_hint, address_is_city_like, distance_km
from .services.classify import classify_result, is_insured_brand
from .services.streetview import find_nearest_streetview
from .services.places import find_best_storefront, nearby_brand_storefront


def home(request):
	form = PharmacyForm()
	return render(request, 'verifier/home.html', { 'form': form })


def verify(request):
	result = None
	context = {}
	if request.method == 'POST':
		form = PharmacyForm(request.POST)
		if form.is_valid():
			pharmacy_name = form.cleaned_data['pharmacy_name']
			pbm_name = form.cleaned_data['pbm_name']
			input_address = form.cleaned_data['address']

			# Find official URL via DuckDuckGo (defensive)
			official_url = None
			try:
				official_url = find_official_url(pharmacy_name, input_address or None)
			except Exception as e:
				print(f"[verify] find_official_url error: {e}")

			# Try scraping addresses from official site (may return multiple branches)
			scraped_addresses = []
			if official_url:
				try:
					scraped_addresses = scrape_addresses_from_site(official_url, max_candidates=5)
				except Exception as e:
					print(f"[verify] scrape_addresses_from_site error: {e}")
					scraped_addresses = []
				if len(scraped_addresses) < 3:
					try:
						extra = scrape_addresses_with_crawl(official_url, max_pages=6, max_candidates=10)
						for a in extra:
							if a not in scraped_addresses:
								scraped_addresses.append(a)
					except Exception as e:
						print(f"[verify] scrape_addresses_with_crawl error: {e}")

			# If an input city/state hint exists, prefer scraped addresses containing that hint
			city_hint = extract_city_hint(input_address) if input_address else None
			if city_hint:
				city_tokens = [t.strip().lower() for t in city_hint.split(',') if t.strip()]
				filtered = []
				for addr in scraped_addresses:
					addr_l = (addr or '').lower()
					if any(tok and tok in addr_l for tok in city_tokens):
						filtered.append(addr)
				if filtered:
					scraped_addresses = filtered
			scraped_address = scraped_addresses[0] if scraped_addresses else None

			# Geocode input and scraped addresses
			input_coords = geocode_best(input_address) if input_address else None
			scraped_coords = None
			scraped_coords_list = []
			if scraped_addresses:
				# Geocode multiple scraped candidates
				for a in scraped_addresses:
					c = geocode_address(a)
					if c:
						scraped_coords_list.append(c)
				scraped_coords = scraped_coords_list[0] if scraped_coords_list else None

			# Build scraped address match list for console + UI
			scraped_matches = []
			for idx, addr in enumerate(scraped_addresses):
				coord = scraped_coords_list[idx] if idx < len(scraped_coords_list) else None
				is_match = False
				dist_val = None
				if input_coords and coord:
					try:
						dist_val = distance_km(input_coords, coord)
						is_match = dist_val is not None and dist_val <= 1.0
					except Exception:
						is_match = False
				scraped_matches.append({
					'address': addr,
					'coords': coord,
					'is_match': is_match,
					'distance_km': round(dist_val, 3) if dist_val is not None else None,
				})

			if scraped_matches:
				print("[Scraped Addresses]")
				for it in scraped_matches:
					print(f" - {it['address']} | match={it['is_match']} | dist_km={it['distance_km']}")

			# Fallback: geocode by pharmacy name query
			name_query = pharmacy_name if not city_hint else f"{pharmacy_name} {city_hint}"
			# Get multiple name-based candidates and pick nearest when input provided
			name_coords = search_place(name_query)
			name_coords_list = geocode_all(name_query, limit=5)

			# Places API: try to get the exact storefront for chains
			places_coords = None
			places_name = None
			places_addr = None
			if pharmacy_name and input_address and settings.MAPS_API_KEY:
				best_store = find_best_storefront(pharmacy_name, input_address)
				if best_store:
					places_coords = (best_store[0], best_store[1])
					places_name = best_store[2]
					places_addr = best_store[3]
				if not places_coords and is_insured_brand(pharmacy_name) and input_coords:
					nb = nearby_brand_storefront(input_coords[0], input_coords[1], pharmacy_name)
					if nb:
						places_coords = (nb[0], nb[1])
						places_name = nb[2]
						places_addr = nb[3]

			# If input address exists, pick nearest among scraped/name candidates
			best_candidate = scraped_coords or name_coords
			if input_coords:
				candidates = []
				if scraped_coords_list:
					candidates.extend(scraped_coords_list)
				if name_coords_list:
					candidates.extend(name_coords_list)
				if places_coords:
					candidates.append(places_coords)
				nearest = pick_nearest(input_coords, candidates)
				if nearest:
					best_candidate = nearest
				elif not best_candidate:
					# Fallback to input coords if no other candidates
					best_candidate = input_coords

			found_any_location = bool(best_candidate or input_coords)

			# Street View: find nearest outdoor panorama around best_candidate
			streetview_info = None
			if best_candidate and settings.MAPS_API_KEY:
				streetview_info = find_nearest_streetview(best_candidate[0], best_candidate[1])

			pano_found = bool(streetview_info and streetview_info.get('status') == 'OK')
			storefront_found = bool(places_coords)
			city_like = address_is_city_like(input_address) if input_address else False
			classification = classify_result(
				input_coords,
				best_candidate,
				found_any_location,
				pano_found=pano_found,
				storefront_found=storefront_found,
				city_like_input=city_like,
			)

			context = {
				'form': form,
				'classification': classification,
				'official_url': official_url,
				'scraped_address': places_addr or scraped_address,
				'scraped_matches': scraped_matches,
				'input_address': input_address,
				'coords': best_candidate,
				'streetview': streetview_info,
				'pharmacy_name': places_name or pharmacy_name,
				'pbm_name': pbm_name,
			}
			return render(request, 'verifier/result.html', context)
	else:
		form = PharmacyForm()
	context['form'] = form
	return render(request, 'verifier/home.html', context)