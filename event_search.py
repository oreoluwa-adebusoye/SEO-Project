import os, requests

TM_BASE = "https://app.ticketmaster.com/discovery/v2/events.json"
TM_KEY = os.getenv("TICKETMASTER_API_KEY")

def search_ticketmaster(keyword="tech", city="New York", size=20, radius_miles=25, lat=None, lon=None):
    if not TM_KEY:
        raise RuntimeError("Missing TICKETMASTER_API_KEY")

    params = {
        "apikey": TM_KEY,
        "size": size,
        "radius": radius_miles,
        "sort": "date,asc",
        "countryCode": "US",
    }
    if keyword:
        params["keyword"] = keyword
    if lat and lon:
        params["latlong"] = f"{lat},{lon}"
    elif city:
        params["city"] = city

    r = requests.get(TM_BASE, params=params, timeout=12)
    r.raise_for_status()
    items = r.json().get("_embedded", {}).get("events", [])

    events = []
    for e in items:
        venue = (e.get("_embedded", {}).get("venues", [{}])[0]) if e.get("_embedded") else {}

        # pick a wide image (16:9) with decent width; fall back to first
        img = None
        imgs = e.get("images", []) or []
        wide = [i for i in imgs if i.get("ratio") in ("16_9", "3_2")]
        if wide:
            img = max(wide, key=lambda i: i.get("width", 0)).get("url")
        elif imgs:
            img = imgs[0].get("url")

        events.append({
            "id": e.get("id"),
            "name": e.get("name"),
            "url": e.get("url"),
            "description": e.get("info") or e.get("pleaseNote"),
            "start": (e.get("dates", {}).get("start", {}).get("dateTime")),
            "venue": venue.get("name"),
            "city": (venue.get("city", {}) or {}).get("name"),
            "image_url": img,  # <-- new
        })
    return events
