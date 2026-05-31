"""
Terrain Engine — computes blended terrain parameters for the Three.js scene.

Tokyo/NY/Paris/London are flat urban cores (low amplitude).
Istanbul is hilly (medium-high amplitude, mid frequency).
Dubai is desert with subtle dune undulations (medium amplitude, low frequency).

The Three.js renderer uses multi-octave sin/cos noise driven by these params.
"""

# Real-world terrain character per city
_PROFILES = {
    "Tokyo":    {"amp": 0.55, "freq": 0.042},
    "İstanbul": {"amp": 4.40, "freq": 0.058},
    "Paris":    {"amp": 0.40, "freq": 0.030},
    "New York": {"amp": 0.45, "freq": 0.045},
    "Dubai":    {"amp": 2.10, "freq": 0.022},
    "Londra":   {"amp": 0.65, "freq": 0.038},
}

_DEFAULT = {"amp": 1.0, "freq": 0.040}


def compute_terrain(normalized: list) -> dict:
    """
    Weighted blend of city terrain profiles.

    Returns:
        amplitude : peak terrain height in game units
        frequency : spatial frequency of hills/dunes
        enabled   : True when amplitude is visually meaningful (> 1.2)
    """
    amp  = sum(_PROFILES.get(c, _DEFAULT)["amp"]  * w for c, w in normalized)
    freq = sum(_PROFILES.get(c, _DEFAULT)["freq"] * w for c, w in normalized)

    return {
        "amplitude": round(amp,  3),
        "frequency": round(freq, 4),
        "enabled":   amp > 1.2,
    }
