"""
Blend Engine — builds the final map data from real OSM city pools.

Phase 2: weighted random building placement
Phase 3: zone-aware building placement + OSM street network per zone
"""
import random
import math

from data.osm_fetcher import fetch_city_data, fetch_street_data
from data.landmark_fetcher import fetch_landmark_data
from engine.zone_engine import compute_zones, assign_city
from engine.terrain_engine import compute_terrain
from engine.landmark_engine import place_landmarks

# Game radius covered by one city's OSM fetch (FETCH_RADIUS * XZ_SCALE)
_OSM_GAME_RADIUS = 650 * 0.15   # ≈ 97.5 game units


def build_blended_map(
    normalized:    list,
    density:       int,
    map_size:      float,
    zone_mode:     bool  = True,
    softness:      float = 0.32,
    show_streets:  bool  = True,
    sponsors:      dict  = None,
    progress_cb           = None,
) -> dict:
    """
    Parameters
    ----------
    normalized    : [(city_name, weight), ...]  weights sum to 1.0
    density       : target building count
    map_size      : half-extent of game world (game units)
    zone_mode     : True → zone-Voronoi assignment, False → global weighted random
    softness      : 0 = hard zone edges, 1 = fully blended borders
    show_streets  : whether to fetch and blend street networks
    progress_cb   : optional callable(str) for streaming status updates

    Returns
    -------
    dict with keys: buildings, streets, zones, terrain, city_stats, sources, total
    """
    sponsors = sponsors or {}

    # ── 1. Fetch building + street + landmark pools ──────────────────────────
    bld_pools    = {}
    street_pools = {}
    lm_pools     = {}
    city_stats   = {}

    for city_name, _ in normalized:
        data = fetch_city_data(city_name, progress_cb=progress_cb)
        bld_pools[city_name]  = data.get("building_templates", [])
        city_stats[city_name] = data.get("stats", {})

    if show_streets:
        for city_name, _ in normalized:
            sdata = fetch_street_data(city_name, progress_cb=progress_cb)
            street_pools[city_name] = sdata.get("street_segments", [])

    for city_name, _ in normalized:
        ldata = fetch_landmark_data(city_name, progress_cb=progress_cb)
        lm_pools[city_name] = ldata.get("landmarks", [])

    if progress_cb:
        progress_cb("🔀 Şehir bölgeleri hesaplanıyor…")

    # ── 2. Compute zones & terrain ───────────────────────────────────────────
    zones   = compute_zones(normalized, map_size)
    terrain = compute_terrain(normalized)

    # ── 3. Place buildings ───────────────────────────────────────────────────
    if progress_cb:
        progress_cb("🏙️  Binalar yerleştiriliyor…")

    buildings = []
    occupied  = []
    half      = map_size * 0.88
    sources   = {c: 0 for c, _ in normalized}

    for _ in range(density):
        x, z = _place(half, occupied)
        occupied.append((x, z))

        if zone_mode:
            city_name = assign_city(x, z, zones, softness)
        else:
            city_name = _weighted_pick(normalized)

        pool     = bld_pools.get(city_name, [])
        template = random.choice(pool) if pool else _synthetic(city_name)
        sources[city_name] = sources.get(city_name, 0) + 1

        buildings.append({
            "x":    round(x, 2),
            "z":    round(z, 2),
            "w":    template["w"],
            "d":    template["d"],
            "h":    template["h"],
            "type": template["type"],
            "city": city_name,
        })

    # ── 4. Build street network ───────────────────────────────────────────────
    streets = _blend_streets(zones, street_pools) if show_streets else []

    # ── 5. Place landmarks with sponsor data ─────────────────────────────────
    if progress_cb:
        progress_cb("🏛️  Landmark'lar yerleştiriliyor…")
    landmarks = place_landmarks(zones, lm_pools, sponsors)

    return {
        "buildings":  buildings,
        "streets":    streets,
        "zones":      zones,
        "terrain":    terrain,
        "landmarks":  landmarks,
        "lm_pools":   lm_pools,        # raw pools so UI can list them
        "city_stats": city_stats,
        "sources":    sources,
        "total":      len(buildings),
    }


# ── INTERNAL ──────────────────────────────────────────────────────────────────

def _blend_streets(zones: list, street_pools: dict,
                   max_per_zone: int = 90) -> list:
    """
    For each zone, translate that city's OSM street segments to be centred on
    the zone origin and scaled to fit within the zone radius.
    """
    all_streets = []
    for zone in zones:
        city  = zone["city"]
        segs  = street_pools.get(city, [])
        if not segs:
            continue

        # Prioritise major roads; take at most max_per_zone
        sorted_segs = sorted(segs, key=lambda s: -s["width"])
        sample      = sorted_segs[:max_per_zone]

        scale     = zone["radius"] / _OSM_GAME_RADIUS
        clip_r_sq = (zone["radius"] * 1.15) ** 2

        for seg in sample:
            new_path = []
            clipped  = False
            for (sx, sz) in seg["path"]:
                nx = zone["cx"] + sx * scale
                nz = zone["cz"] + sz * scale
                if (nx - zone["cx"])**2 + (nz - zone["cz"])**2 > clip_r_sq:
                    clipped = True
                    break
                new_path.append([round(nx, 2), round(nz, 2)])

            if not clipped and len(new_path) >= 2:
                all_streets.append({
                    "path":  new_path,
                    "width": round(max(0.6, seg["width"] * scale), 2),
                    "type":  seg["type"],
                    "city":  city,
                })

    return all_streets


def _weighted_pick(normalized: list) -> str:
    r = random.random()
    acc = 0.0
    for name, w in normalized:
        acc += w
        if r <= acc:
            return name
    return normalized[-1][0]


def _place(half: float, occupied: list,
           min_sep: float = 2.8) -> tuple:
    """Return a non-overlapping position outside the spawn zone."""
    spawn = 11.0
    recent = occupied[-80:]

    for _ in range(80):
        x = random.uniform(-half, half)
        z = random.uniform(-half, half)
        if abs(x) < spawn and abs(z) < spawn:
            continue
        if all(math.hypot(x - ox, z - oz) > min_sep for ox, oz in recent):
            return x, z

    for _ in range(200):
        x = random.uniform(-half, half)
        z = random.uniform(-half, half)
        if abs(x) > spawn or abs(z) > spawn:
            return x, z
    return random.uniform(-half, half), random.uniform(-half, half)


# Statistical fallback when OSM pool is empty
_SYNTHETIC_POOL = {
    "Tokyo":    [{"w":2.0,"d":2.2,"h":22.0,"type":"office"},
                 {"w":3.0,"d":3.5,"h":10.0,"type":"apartments"},
                 {"w":1.8,"d":1.8,"h":35.0,"type":"commercial"}],
    "İstanbul": [{"w":4.5,"d":3.8,"h": 7.5,"type":"apartments"},
                 {"w":5.0,"d":5.0,"h": 6.0,"type":"residential"},
                 {"w":8.0,"d":8.0,"h":12.0,"type":"mosque"}],
    "Paris":    [{"w":5.5,"d":4.0,"h": 9.5,"type":"apartments"},
                 {"w":6.0,"d":4.5,"h": 8.5,"type":"residential"},
                 {"w":4.0,"d":3.5,"h":10.0,"type":"commercial"}],
    "New York": [{"w":4.0,"d":4.0,"h":40.0,"type":"office"},
                 {"w":5.5,"d":5.5,"h":15.0,"type":"apartments"},
                 {"w":3.5,"d":3.5,"h": 6.0,"type":"residential"}],
    "Dubai":    [{"w":3.0,"d":3.0,"h":55.0,"type":"office"},
                 {"w":2.5,"d":2.5,"h":38.0,"type":"hotel"},
                 {"w":7.0,"d":6.0,"h": 4.5,"type":"residential"}],
    "Londra":   [{"w":5.0,"d":4.0,"h": 7.5,"type":"residential"},
                 {"w":4.5,"d":3.5,"h": 6.0,"type":"terrace"},
                 {"w":3.5,"d":3.5,"h":22.0,"type":"office"}],
}

def _synthetic(city_name: str) -> dict:
    opts = _SYNTHETIC_POOL.get(city_name, [{"w":3.0,"d":3.0,"h":10.0,"type":"yes"}])
    t = random.choice(opts).copy()
    t["h"] = round(t["h"] * random.uniform(0.75, 1.35), 2)
    t["w"] = round(t["w"] * random.uniform(0.85, 1.20), 2)
    t["d"] = round(t["d"] * random.uniform(0.85, 1.20), 2)
    return t
