"""
Harman AI — Claude API integration.

Three entry points:
  parse_blend_prompt   : natural language → city blend parameters
  generate_world_lore  : blend config     → cinematic world description (Turkish)
  suggest_sponsors     : landmark list    → brand sponsor suggestions

All functions use claude-opus-4-8 with prompt caching on the static system prompt.
"""
import json
import re

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

MODEL = "claude-opus-4-8"

# Available city names for validation
_CITIES = {"Tokyo", "İstanbul", "Paris", "New York", "Dubai", "Londra"}

# ── SYSTEM PROMPTS (cached — never include dynamic data here) ─────────────────

_BLEND_SYSTEM = """\
Sen "Harman" adlı 3B oyun haritası motorunun şehir harmanlama asistanısın.
Kullanıcının serbest metin açıklamasından harita parametrelerini çıkarıyorsun.

Kullanılabilir şehirler ve karakterleri:
- Tokyo: neon, yoğun, çok katlı, gece hayatı, fütüristik Asya
- İstanbul: tarihi, kubbeli, organik sokaklar, tepelik, Doğu-Batı sentezi
- Paris: zarif, Haussmann blokları, geniş bulvarlar, krem rengi binalar
- New York: gökdelen, art deco, Manhattan ızgarası, beton orman
- Dubai: cam, ultra modern, seyrek yapı, lüks, çöl zemini
- Londra: Viktoryen, kırmızı tuğla, sisli, tarihi, parklar

Sadece JSON döndür, başka hiçbir metin veya açıklama ekleme:
{
  "cities": [{"name": "ŞehirAdı", "weight": 0.X}, ...],
  "mood": "kısa ruh hali (3-5 kelime)",
  "weather": "Açık|Puslu|Yoğun Sis",
  "density": 20-140,
  "description": "Bu hayali şehrin 2 cümlelik Türkçe tasviri (max 50 kelime)"
}
Kurallar: 2-4 şehir seç; ağırlıklar toplamı 1.0 olmalı; ruh haline en uygun şehirleri seç.\
"""

_LORE_SYSTEM = """\
Sen sinematik bir oyun dünyası yazarısın.
Sana verilecek şehir karışımı için kısa ama güçlü bir Türkçe dünya tasviri yaz.
Kurallar:
- 3-4 cümle, kesinlikle 80 kelimeyi geçme
- Oyun worldbuilding tarzında yaz (neo-noir / cyberpunk / fantastik gerçekçilik)
- Mimari, ışık, sokak dokusu ve atmosfer detayı ver
- Sadece tasviri yaz — giriş/açıklama/başlık ekleme\
"""

_SPONSOR_SYSTEM = """\
Sen oyun içi reklam stratejisti ve pazarlama danışmanısın.
Verilen şehir kombinasyonu ve landmark listesi için uygun marka önerileri sun.
Her landmark için tek bir gerçek veya hayali marka öner.
Sadece JSON array döndür, başka hiçbir metin ekleme:
[{"landmark": "landmark adı", "brand": "Marka", "color": "#RRGGBB", "reason": "kısa gerekçe"}]
Renk, markanın kurumsal rengine yakın olsun. En fazla 8 öneri döndür.\
"""


# ── PUBLIC API ─────────────────────────────────────────────────────────────────

def parse_blend_prompt(user_text: str, api_key: str) -> dict:
    """
    Parse a natural language city description into blend parameters.
    Returns dict with: cities, mood, weather, density, description
    Empty dict on failure.
    """
    if not HAS_ANTHROPIC or not api_key:
        return {"error": "anthropic kütüphanesi yüklü değil veya API key eksik"}

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=MODEL,
            max_tokens=600,
            system=[{
                "type": "text",
                "text": _BLEND_SYSTEM,
                "cache_control": {"type": "ephemeral"},   # cache static system prompt
            }],
            messages=[{"role": "user", "content": user_text}],
        )
        raw = resp.content[0].text.strip()
        data = _extract_json(raw, "{")
        if not data:
            return {"error": "JSON ayrıştırma başarısız", "raw": raw[:200]}

        # Normalize + validate city names
        cities = []
        for c in data.get("cities", []):
            name = _normalize_city(c.get("name", ""))
            if name in _CITIES:
                cities.append({"name": name, "weight": float(c.get("weight", 0.5))})
        if not cities:
            return {"error": "Geçerli şehir bulunamadı", "raw": raw[:200]}

        # Normalize weights to sum 1.0
        total = sum(c["weight"] for c in cities) or 1.0
        for c in cities:
            c["weight"] = round(c["weight"] / total, 4)

        data["cities"] = cities
        return data

    except anthropic.AuthenticationError:
        return {"error": "Geçersiz API key — lütfen kontrol edin"}
    except Exception as exc:
        return {"error": str(exc)}


def generate_world_lore(cities_info: list, api_key: str) -> str:
    """
    Generate a cinematic Turkish worldbuilding description for the blended city.
    cities_info: [{"name": str, "weight": float}, ...]
    """
    if not HAS_ANTHROPIC or not api_key:
        return ""

    city_str = ", ".join(
        f"{c['name']} (%{int(c['weight'] * 100)})" for c in cities_info
    )
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=MODEL,
            max_tokens=280,
            system=[{
                "type": "text",
                "text": _LORE_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": f"Şehir karışımı: {city_str}"}],
        )
        return resp.content[0].text.strip()

    except Exception as exc:
        return f"Lore üretilemedi: {exc}"


def suggest_sponsors(landmarks: list, cities: list, api_key: str) -> list:
    """
    Suggest brand sponsors for a list of landmarks.
    Returns [{"landmark", "brand", "color", "reason"}, ...]
    """
    if not HAS_ANTHROPIC or not api_key or not landmarks:
        return []

    city_names = ", ".join(c["name"] for c in cities)
    lm_list    = "\n".join(
        f"- {lm['name']} ({lm.get('type','attraction')}, {lm.get('city','')})"
        for lm in landmarks[:12]
    )
    prompt = f"Şehirler: {city_names}\n\nLandmark'lar:\n{lm_list}"

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=MODEL,
            max_tokens=700,
            system=[{
                "type": "text",
                "text": _SPONSOR_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        arr = _extract_json(raw, "[")
        return arr if isinstance(arr, list) else []

    except Exception:
        return []


# ── INTERNAL ──────────────────────────────────────────────────────────────────

def _extract_json(text: str, start_char: str):
    """Extract first JSON object or array from a string."""
    end_char = "}" if start_char == "{" else "]"
    idx = text.find(start_char)
    if idx == -1:
        return None
    depth, in_str, esc = 0, False, False
    for i, ch in enumerate(text[idx:], idx):
        if esc:
            esc = False; continue
        if ch == "\\":
            esc = True; continue
        if ch == '"':
            in_str = not in_str; continue
        if in_str:
            continue
        if ch == start_char:
            depth += 1
        elif ch == end_char:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[idx:i+1])
                except json.JSONDecodeError:
                    return None
    return None


def _normalize_city(name: str) -> str:
    mapping = {
        "istanbul": "İstanbul",
        "i̇stanbul": "İstanbul",
        "istanbul": "İstanbul",
        "london": "Londra",
        "londra": "Londra",
        "paris": "Paris",
        "new york": "New York",
        "newyork": "New York",
        "new_york": "New York",
        "tokyo": "Tokyo",
        "dubai": "Dubai",
    }
    return mapping.get(name.lower().strip(), name.strip())
