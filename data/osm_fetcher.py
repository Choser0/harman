"""
OSM Fetcher — real building + street data from OpenStreetMap via OSMnx.
Results are cached to data/cache/ so repeat renders are instant.
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

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Exact city-center coordinates (dense urban core for richest building data)
CITY_CENTERS = {
    "Tokyo":    (35.6938, 139.7034),   # Shinjuku
    "İstanbul": (41.0082, 28.9784),    # Sultanahmet
    "Paris":    (48.8566,  2.3522),    # Île de la Cité
    "New York": (40.7549, -73.9840),   # Midtown Manhattan
    "Dubai":    (25.1972,  55.2744),   # Downtown
    "Londra":   (51.5155,  -0.0922),   # City of London
}

FETCH_RADIUS = 650    # metres around city centre
MAX_BUILDINGS = 220
XZ_SCALE = 0.15       # 1 real metre → 0.15 game units  (650 m ≈ 97 game units)
Y_SCALE  = 0.38       # 1 real metre → 0.38 game units  (100 m tower ≈ 38 units)


# ── PUBLIC API ────────────────────────────────────────────────────────────────

def fetch_city_data(city_name: str, progress_cb=None) -> dict:
    """
    Return building templates for a city.
    Uses disk cache; only hits OSM on first call per city.
    """
    if not HAS_OSM:
        return _osm_missing(city_name)

    cache_path = _cache_path(city_name)
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if progress_cb:
                progress_cb(f"💾 {city_name}: önbellekten yüklendi ({data['stats']['total']} bina)")
            return data
        except Exception:
            cache_path.unlink(missing_ok=True)

    if progress_cb:
        progress_cb(f"🌐 {city_name}: OpenStreetMap'ten indiriliyor…")

    lat, lon = CITY_CENTERS[city_name]
    try:
        ox.settings.log_console = False
        ox.settings.use_cache   = True

        gdf = ox.features_from_point(
            (lat, lon),
            tags={"building": True},
            dist=FETCH_RADIUS,
        )
        gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()

        if progress_cb:
            progress_cb(f"🏗️  {city_name}: {len(gdf)} poligon işleniyor…")

        templates = _extract_templates(gdf, lat)

        if len(templates) > MAX_BUILDINGS:
            templates = random.sample(templates, MAX_BUILDINGS)

        heights = [t["h"] for t in templates] or [10.0]
        stats = {
            "total":      len(templates),
            "avg_height": round(sum(heights) / len(heights), 1),
            "max_height": round(max(heights), 1),
            "radius_m":   FETCH_RADIUS,
        }

        data = {"city": city_name, "building_templates": templates, "stats": stats}
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        if progress_cb:
            progress_cb(f"✅ {city_name}: {len(templates)} bina şablonu hazır")
        return data

    except Exception as exc:
        if progress_cb:
            progress_cb(f"⚠️  {city_name}: OSM hatası — prosedürel fallback ({exc})")
        return {"city": city_name, "building_templates": [], "stats": {}, "error": str(exc)}


def clear_cache(city_name: str = None) -> None:
    if city_name:
        _cache_path(city_name).unlink(missing_ok=True)
    else:
        for f in CACHE_DIR.glob("*.json"):
            f.unlink()


def is_cached(city_name: str) -> bool:
    return _cache_path(city_name).exists()


# ── INTERNAL ──────────────────────────────────────────────────────────────────

def _cache_path(city_name: str) -> Path:
    safe = city_name.replace("İ", "I").replace(" ", "_")
    return CACHE_DIR / f"{safe}_{FETCH_RADIUS}m.json"


def _extract_templates(gdf, ref_lat: float) -> list:
    templates = []
    for _, row in gdf.iterrows():
        try:
            geom = row.geometry
            if geom.geom_type == "MultiPolygon":
                geom = max(geom.geoms, key=lambda g: g.area)

            minx, miny, maxx, maxy = geom.bounds

            # Degrees → metres (approximate equirectangular)
            w_m = abs(maxx - minx) * math.cos(math.radians(ref_lat)) * 111_320
            d_m = abs(maxy - miny) * 110_540

            if w_m < 3 or w_m > 220 or d_m < 3 or d_m > 220:
                continue

            h_m = _estimate_height(row)
            btype = _clean_tag(row.get("building", "yes"))

            templates.append({
                "w":    round(max(1.5, w_m * XZ_SCALE),  2),
                "d":    round(max(1.5, d_m * XZ_SCALE),  2),
                "h":    round(max(2.0, min(h_m * Y_SCALE, 68.0)), 2),
                "type": btype,
            })
        except Exception:
            continue
    return templates


def _estimate_height(row) -> float:
    """Real height in metres from OSM tags, with typed statistical fallback."""
    for tag in ("height", "max_height"):
        try:
            val = row.get(tag)
            if val and str(val) not in ("nan", "None", ""):
                return float(str(val).replace("m", "").replace(" ", ""))
        except Exception:
            pass
    try:
        lvl = row.get("building:levels")
        if lvl and str(lvl) not in ("nan", "None", ""):
            return float(str(lvl).split(";")[0]) * 3.5
    except Exception:
        pass

    btype = _clean_tag(row.get("building", "yes"))
    DEFAULTS = {
        "apartments": 15, "residential": 9, "house": 6, "detached": 6,
        "semi_detached": 7, "terrace": 7, "bungalow": 3, "cabin": 4,
        "commercial": 16, "retail": 5, "supermarket": 6,
        "office": 24, "industrial": 9, "warehouse": 8, "factory": 10,
        "church": 18, "cathedral": 30, "mosque": 22, "temple": 16,
        "school": 9, "university": 14, "hospital": 18, "government": 16,
        "hotel": 26, "dormitory": 12, "civic": 14,
        "yes": 10, "building": 10,
    }
    base = DEFAULTS.get(btype, 10)
    return base * random.uniform(0.72, 1.32)


def _clean_tag(val) -> str:
    if isinstance(val, list):
        val = val[0]
    s = str(val).lower().strip()
    return s if s not in ("nan", "none", "") else "yes"


def _osm_missing(city_name: str) -> dict:
    return {
        "city": city_name,
        "building_templates": [],
        "stats": {},
        "error": "osmnx not installed — run: pip install osmnx",
    }


# ── PHASE 3: STREET NETWORK ───────────────────────────────────────────────────

MAX_STREETS = 350   # per city, sorted by road importance

def fetch_street_data(city_name: str, progress_cb=None) -> dict:
    """
    Fetch and cache the drive-network edges for a city.
    Returns street segments normalised to game coordinates (relative to city centre).
    """
    if not HAS_OSM:
        return {"city": city_name, "street_segments": []}

    cache_path = _street_cache_path(city_name)
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if progress_cb:
                n = len(data.get("street_segments", []))
                progress_cb(f"🛣️  {city_name}: sokaklar önbellekten ({n} segment)")
            return data
        except Exception:
            cache_path.unlink(missing_ok=True)

    if progress_cb:
        progress_cb(f"🛣️  {city_name}: sokak ağı indiriliyor…")

    lat, lon = CITY_CENTERS[city_name]
    try:
        ox.settings.log_console = False
        G = ox.graph_from_point((lat, lon), dist=FETCH_RADIUS, network_type="drive")
        _, edges = ox.graph_to_gdfs(G)

        segments = []
        for _, edge in edges.iterrows():
            try:
                coords = list(edge.geometry.coords)   # (lon, lat) tuples from Shapely
                path   = []
                for (elon, elat) in coords:
                    gx, gz = _latlon_to_game(elat, elon, lat, lon)
                    path.append([round(gx, 2), round(gz, 2)])

                hw = edge.get("highway", "residential")
                if isinstance(hw, list):
                    hw = hw[0]
                hw = str(hw)

                segments.append({
                    "path":  path,
                    "width": _road_width(hw),
                    "type":  hw,
                })
            except Exception:
                continue

        # Keep most important roads first
        segments.sort(key=lambda s: -s["width"])
        segments = segments[:MAX_STREETS]

        data = {"city": city_name, "street_segments": segments}
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        if progress_cb:
            progress_cb(f"✅ {city_name}: {len(segments)} sokak segmenti hazır")
        return data

    except Exception as exc:
        if progress_cb:
            progress_cb(f"⚠️  {city_name}: sokak hatası — atlanıyor ({exc})")
        return {"city": city_name, "street_segments": [], "error": str(exc)}


def is_street_cached(city_name: str) -> bool:
    return _street_cache_path(city_name).exists()


def _street_cache_path(city_name: str) -> Path:
    safe = city_name.replace("İ", "I").replace(" ", "_")
    return CACHE_DIR / f"{safe}_{FETCH_RADIUS}m_streets.json"


def _latlon_to_game(lat: float, lon: float, ref_lat: float, ref_lon: float):
    """
    Convert a lat/lon to game (x, z) relative to a reference point.
    East  → +x,  North → −z  (Three.js convention: camera looks into −z).
    """
    R      = 6_371_000
    game_x =  math.radians(lon - ref_lon) * R * math.cos(math.radians(ref_lat)) * XZ_SCALE
    game_z = -math.radians(lat - ref_lat) * R * XZ_SCALE
    return game_x, game_z


def _road_width(hw_type: str) -> float:
    WIDTHS = {
        "motorway": 4.5, "motorway_link": 3.0,
        "trunk": 4.0,    "trunk_link": 2.5,
        "primary": 3.2,  "primary_link": 2.0,
        "secondary": 2.5,"secondary_link": 1.8,
        "tertiary": 2.0, "tertiary_link": 1.5,
        "residential": 1.5, "living_street": 1.2,
        "service": 1.0,  "unclassified": 1.4,
        "pedestrian": 0.9,
    }
    return WIDTHS.get(hw_type, 1.4)
