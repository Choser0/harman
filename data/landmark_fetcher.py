"""
Landmark Fetcher — real named POIs from OpenStreetMap.

Queries tourism + historic tags around each city centre, returns the top
named attractions with their game-space offset from city centre.
Results are disk-cached separately from buildings/streets.
"""
import json
import math
import random
from pathlib import Path

try:
    import osmnx as ox
    HAS_OSM = True
except ImportError:
    HAS_OSM = False

from data.osm_fetcher import CITY_CENTERS, CACHE_DIR, FETCH_RADIUS, XZ_SCALE

MAX_LANDMARKS = 18   # per city

# Height estimates by landmark type (game units)
_TYPE_HEIGHT = {
    "tower":      lambda: random.uniform(18, 38),
    "religious":  lambda: random.uniform(10, 22),
    "castle":     lambda: random.uniform(12, 20),
    "monument":   lambda: random.uniform(7,  16),
    "museum":     lambda: random.uniform(6,  12),
    "gallery":    lambda: random.uniform(5,  10),
    "ruins":      lambda: random.uniform(4,   9),
    "viewpoint":  lambda: random.uniform(5,  10),
    "attraction": lambda: random.uniform(6,  14),
}


# ── PUBLIC ────────────────────────────────────────────────────────────────────

def fetch_landmark_data(city_name: str, progress_cb=None) -> dict:
    """Fetch and cache real named POIs for a city."""
    if not HAS_OSM:
        return {"city": city_name, "landmarks": []}

    cache_path = _cache_path(city_name)
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if progress_cb:
                n = len(data.get("landmarks", []))
                progress_cb(f"🏛️  {city_name}: landmark'lar önbellekten ({n} adet)")
            return data
        except Exception:
            cache_path.unlink(missing_ok=True)

    if progress_cb:
        progress_cb(f"🏛️  {city_name}: landmark'lar indiriliyor…")

    lat, lon = CITY_CENTERS[city_name]
    try:
        ox.settings.log_console = False
        gdf = ox.features_from_point(
            (lat, lon),
            tags={"tourism": True, "historic": True, "man_made": "tower"},
            dist=FETCH_RADIUS,
        )

        landmarks = []
        seen_names = set()

        for _, row in gdf.iterrows():
            try:
                name = (
                    row.get("name:en")
                    or row.get("name")
                    or row.get("name:tr")
                )
                if not name or str(name) in ("nan", "None", ""):
                    continue
                name = str(name).strip()
                if name in seen_names or len(name) < 3:
                    continue
                seen_names.add(name)

                centroid = row.geometry.centroid
                gx, gz = _latlng_game(centroid.y, centroid.x, lat, lon)

                lm_type = _classify(row)
                h = round(_TYPE_HEIGHT.get(lm_type, _TYPE_HEIGHT["attraction"])(), 2)

                landmarks.append({
                    "name": name,
                    "type": lm_type,
                    "gx":   round(gx, 2),
                    "gz":   round(gz, 2),
                    "h":    h,
                })
            except Exception:
                continue

        # Sort by centrality (closest to city centre = most prominent)
        landmarks.sort(key=lambda l: math.hypot(l["gx"], l["gz"]))
        landmarks = landmarks[:MAX_LANDMARKS]

        data = {"city": city_name, "landmarks": landmarks}
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        if progress_cb:
            progress_cb(f"✅ {city_name}: {len(landmarks)} landmark hazır")
        return data

    except Exception as exc:
        if progress_cb:
            progress_cb(f"⚠️  {city_name}: landmark hatası — atlanıyor ({exc})")
        return {"city": city_name, "landmarks": [], "error": str(exc)}


def is_landmark_cached(city_name: str) -> bool:
    return _cache_path(city_name).exists()


# ── INTERNAL ──────────────────────────────────────────────────────────────────

def _cache_path(city_name: str) -> Path:
    safe = city_name.replace("İ", "I").replace(" ", "_")
    return CACHE_DIR / f"{safe}_{FETCH_RADIUS}m_landmarks.json"


def _latlng_game(lat, lon, ref_lat, ref_lon):
    R = 6_371_000
    gx =  math.radians(lon - ref_lon) * R * math.cos(math.radians(ref_lat)) * XZ_SCALE
    gz = -math.radians(lat - ref_lat) * R * XZ_SCALE
    return gx, gz


def _classify(row) -> str:
    man_made = str(row.get("man_made", "")).lower()
    tourism  = str(row.get("tourism",  "")).lower()
    historic = str(row.get("historic", "")).lower()
    building = str(row.get("building", "")).lower()
    amenity  = str(row.get("amenity",  "")).lower()

    if man_made in ("tower", "lighthouse", "windmill"):       return "tower"
    if building in ("cathedral","mosque","temple","church",
                    "synagogue","shrine"):                     return "religious"
    if amenity == "place_of_worship":                         return "religious"
    if historic == "castle":                                  return "castle"
    if historic in ("monument", "memorial", "column"):        return "monument"
    if tourism  == "museum":                                  return "museum"
    if tourism  == "gallery":                                  return "gallery"
    if historic == "ruins":                                   return "ruins"
    if tourism  == "viewpoint":                               return "viewpoint"
    return "attraction"
