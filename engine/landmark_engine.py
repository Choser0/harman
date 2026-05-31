"""
Landmark Engine — places real OSM landmarks within city zones,
injects sponsor data, returns a JSON-ready list for Three.js.
"""
import math

_OSM_GAME_RADIUS = 650 * 0.15   # 97.5 game units (same as blend_engine)
MAX_PER_ZONE     = 12


def place_landmarks(zones: list, lm_pools: dict, sponsors: dict) -> list:
    """
    For each zone, translate that city's OSM landmark offsets into world
    coordinates scaled to fit within the zone radius.

    sponsors : { "CityName_LandmarkPrefix": {"brand": str, "color": str} }
    """
    result = []

    for zone in zones:
        city = zone["city"]
        pool = lm_pools.get(city, [])
        if not pool:
            continue

        scale    = zone["radius"] / _OSM_GAME_RADIUS
        clip_r_sq = (zone["radius"] * 1.25) ** 2

        for lm in pool[:MAX_PER_ZONE]:
            nx = zone["cx"] + lm["gx"] * scale
            nz = zone["cz"] + lm["gz"] * scale

            # Clip to zone
            if (nx - zone["cx"])**2 + (nz - zone["cz"])**2 > clip_r_sq:
                continue

            # Sponsor lookup — key = "City_first20chars"
            key    = _sponsor_key(city, lm["name"])
            sp     = sponsors.get(key, {})
            active = bool(sp.get("brand", "").strip())

            result.append({
                "x":           round(nx, 2),
                "z":           round(nz, 2),
                "name":        lm["name"],
                "type":        lm["type"],
                "city":        city,
                "h":           lm["h"],
                "sponsored":   active,
                "sponsorName": sp.get("brand", ""),
                "sponsorColor": sp.get("color", "#e94560"),
            })

    return result


def sponsor_key(city: str, landmark_name: str) -> str:
    return _sponsor_key(city, landmark_name)


def _sponsor_key(city: str, name: str) -> str:
    return f"{city}_{name[:20]}"
