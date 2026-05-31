"""
Zone Engine — divides the game world into city territories.

Each city in the blend gets a zone center and radius.
Buildings and streets are then assigned to zones via weighted Voronoi influence.
"""
import math
from typing import List, Tuple


def compute_zones(normalized: List[Tuple[str, float]], map_size: float) -> list:
    """
    Place zone centers at equal angular intervals around the map origin.
    Higher-weight cities get zones closer to the centre and with larger radii.

    Returns a list of zone dicts ready for JSON serialisation.
    """
    n = len(normalized)
    zones = []

    for i, (city_name, weight) in enumerate(normalized):
        # Angular offset so first zone sits at NW rather than due East
        angle  = (2 * math.pi * i / n) - math.pi / 5
        # Higher weight → closer to centre
        spread = map_size * 0.36 * (1.1 - weight * 0.55)
        cx     = math.cos(angle) * spread
        cz     = math.sin(angle) * spread
        # Zone radius: proportional to weight, capped at 65 % of map half-extent
        radius = map_size * 0.42 * weight + map_size * 0.14
        radius = min(radius, map_size * 0.65)

        zones.append({
            "city":   city_name,
            "weight": round(weight, 4),
            "cx":     round(cx, 2),
            "cz":     round(cz, 2),
            "radius": round(radius, 2),
        })

    return zones


def assign_city(x: float, z: float, zones: list, softness: float = 0.3) -> str:
    """
    Return the dominant city name for a game-world position.

    softness = 0.0 → hard Voronoi (pure distance)
    softness = 1.0 → fully weight-blended (ignores distance)

    The formula blends distance-based and weight-based influence:
        score = (1 - softness) / dist  +  softness * weight
    """
    if not zones:
        return "Tokyo"

    scores = []
    for zone in zones:
        dx   = x - zone["cx"]
        dz   = z - zone["cz"]
        dist = math.sqrt(dx * dx + dz * dz) + 1e-6
        score = (1.0 - softness) / dist + softness * zone["weight"]
        scores.append(score)

    return zones[scores.index(max(scores))]["city"]
