import streamlit as st
import streamlit.components.v1 as components
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data.osm_fetcher import HAS_OSM, is_cached, is_street_cached, clear_cache
from data.landmark_fetcher import is_landmark_cached
from engine.blend_engine import build_blended_map
from engine.landmark_engine import sponsor_key
from ai.harman_ai import (
    parse_blend_prompt, generate_world_lore, suggest_sponsors, HAS_ANTHROPIC
)

st.set_page_config(layout="wide", page_title="Harman — City Blend Engine", page_icon="🌆")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600&display=swap');

.stApp { background: #07070f; color: #e0e0e0; }

.harman-header {
    background: linear-gradient(135deg,#0d0d1a 0%,#111128 50%,#0d0d1a 100%);
    border:1px solid #e94560; border-radius:14px;
    padding:24px 32px; margin-bottom:18px; position:relative; overflow:hidden;
}
.harman-header::before {
    content:''; position:absolute; top:-50%; left:-50%; width:200%; height:200%;
    background:radial-gradient(ellipse at center,rgba(233,69,96,.06) 0%,transparent 60%);
    pointer-events:none;
}
.harman-title {
    font-family:'Orbitron',monospace; font-weight:900; font-size:3em; letter-spacing:8px;
    background:linear-gradient(90deg,#e94560 0%,#00d4ff 50%,#e94560 100%);
    background-size:200% auto;
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    margin:0; animation:shine 4s linear infinite;
}
@keyframes shine { to { background-position:200% center; } }
.harman-sub { color:#555; font-family:'Inter',sans-serif; font-size:.88em;
              letter-spacing:3px; margin:6px 0 0 2px; text-transform:uppercase; }

.blend-bar { height:10px; border-radius:5px; display:flex; overflow:hidden;
             background:#111; border:1px solid #1a1a2e; }
.blend-segment { height:100%; transition:width .6s cubic-bezier(.4,0,.2,1); }

.city-pill {
    display:inline-flex; align-items:center; gap:6px; border-radius:20px;
    padding:5px 14px; font-size:.82em; font-family:'Inter',sans-serif;
    font-weight:600; margin:3px 4px 3px 0; border:1px solid; letter-spacing:.5px;
}
.dna-panel {
    background:rgba(255,255,255,.03); border:1px solid #1a1a2e;
    border-radius:10px; padding:12px 16px; margin-top:12px;
    display:flex; flex-wrap:wrap; gap:8px; align-items:center;
}
.dna-tag {
    background:rgba(233,69,96,.12); border:1px solid rgba(233,69,96,.3);
    color:#e94560; border-radius:12px; padding:3px 10px;
    font-size:.78em; font-family:'Inter',sans-serif;
}
.stat-card {
    background:rgba(255,255,255,.03); border:1px solid #1a1a2e;
    border-radius:10px; padding:14px 18px; margin-top:14px;
}
.stat-label { color:#444; font-size:.75em; font-family:'Inter',sans-serif;
              letter-spacing:2px; text-transform:uppercase; margin-bottom:4px; }
.stat-value { color:#e0e0e0; font-size:1.05em; font-family:'Inter',sans-serif; font-weight:600; }
.stat-sub   { color:#555; font-size:.8em; font-family:'Inter',sans-serif; margin-top:2px; }

.cache-dot { display:inline-block; width:7px; height:7px;
             border-radius:50%; margin-right:5px; vertical-align:middle; }
.placeholder-box {
    background:linear-gradient(135deg,#0a0a18,#0f0f22); border:2px dashed #1e1e3a;
    border-radius:10px; height:560px; display:flex; flex-direction:column;
    align-items:center; justify-content:center;
}
[data-testid="stSidebar"] {
    background:rgba(7,7,15,.98) !important; border-right:1px solid #1a1a2e !important;
}
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    color:#e94560 !important; font-family:'Orbitron',monospace !important; letter-spacing:2px;
}
.stButton > button {
    background:linear-gradient(90deg,#e94560,#c62a47) !important;
    color:white !important; border:none !important; border-radius:8px !important;
    font-weight:700 !important; letter-spacing:3px !important; padding:14px !important;
    font-family:'Orbitron',monospace !important; font-size:.85em !important;
    box-shadow:0 4px 20px rgba(233,69,96,.3) !important;
}
.stButton > button:hover {
    transform:translateY(-2px) !important;
    box-shadow:0 8px 30px rgba(233,69,96,.5) !important;
}
div[data-baseweb="select"] > div { background:#0f0f1a !important; border-color:#1e1e3a !important; }
</style>
""", unsafe_allow_html=True)

# ── CITY DNA ──────────────────────────────────────────────────────────────────
CITIES = {
    "Tokyo":    {"emoji":"🗼","color":"#e94560","fog":.022,
                 "tags":["Neon","Yoğun","Çok Katlı","Izgara","Gece Şehri"],
                 "landmark":"Tokyo Kulesi","lm_type":"tokyo_tower",
                 "palette":{"sky":[15,15,35],"ground":[18,22,45],"building_main":[20,55,100],
                             "building_alt":[233,69,96],"landmark":[255,60,60],
                             "neon":[0,212,255],"roof":[10,10,30]}},
    "İstanbul": {"emoji":"🕌","color":"#d4af37","fog":.014,
                 "tags":["Tarihi","Kubbeli","Organik","Tepelik","Kültürel"],
                 "landmark":"Ayasofya","lm_type":"hagia_sophia",
                 "palette":{"sky":[44,24,16],"ground":[130,95,18],"building_main":[196,163,90],
                             "building_alt":[139,46,46],"landmark":[212,175,55],
                             "neon":[255,140,66],"roof":[90,55,18]}},
    "Paris":    {"emoji":"🗼","color":"#4a8fd4","fog":.010,
                 "tags":["Haussmann","Tek Tip","Geniş Bulvar","Zarif","Krem Rengi"],
                 "landmark":"Eyfel Kulesi","lm_type":"eiffel",
                 "palette":{"sky":[90,115,165],"ground":[155,135,108],"building_main":[210,198,165],
                             "building_alt":[138,112,82],"landmark":[180,148,10],
                             "neon":[255,210,0],"roof":[75,75,88]}},
    "New York": {"emoji":"🗽","color":"#8888aa","fog":.016,
                 "tags":["Gökdelen","Art Deco","Manhattan","Beton","Izgara"],
                 "landmark":"Empire State","lm_type":"empire_state",
                 "palette":{"sky":[25,25,28],"ground":[42,42,48],"building_main":[68,68,80],
                             "building_alt":[105,105,118],"landmark":[255,165,0],
                             "neon":[255,255,0],"roof":[45,45,52]}},
    "Dubai":    {"emoji":"🏙️","color":"#00d4ff","fog":.005,
                 "tags":["Cam","Ultra Modern","Seyrek","Lüks","Çöl"],
                 "landmark":"Burj Khalifa","lm_type":"burj_khalifa",
                 "palette":{"sky":[130,200,235],"ground":[190,155,88],"building_main":[195,228,242],
                             "building_alt":[238,238,255],"landmark":[255,215,0],
                             "neon":[0,255,240],"roof":[175,210,232]}},
    "Londra":   {"emoji":"🎡","color":"#dc143c","fog":.030,
                 "tags":["Viktoryen","Kırmızı Tuğla","Sisli","Tarihi","Parklar"],
                 "landmark":"Big Ben","lm_type":"big_ben",
                 "palette":{"sky":[108,122,140],"ground":[80,102,45],"building_main":[136,112,83],
                             "building_alt":[175,33,33],"landmark":[220,20,60],
                             "neon":[255,69,0],"roof":[75,65,55]}},
}

def blend_rgb(pairs):
    return [int(sum(c[i]*w for c,w in pairs)) for i in range(3)]

def rgb_js(a): return f"0x{a[0]:02x}{a[1]:02x}{a[2]:02x}"

def collect_tags(normalized):
    seen, out = set(), []
    for name, _ in normalized:
        for t in CITIES[name]["tags"]:
            if t not in seen: seen.add(t); out.append(t)
    return out[:8]

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:16px 0 22px 0;'>
        <div style='font-family:Orbitron,monospace;font-size:1.9em;font-weight:900;
                    letter-spacing:6px;color:#e94560;'>HARMAN</div>
        <div style='color:#333;font-size:.75em;letter-spacing:3px;margin-top:4px;'>
            CITY BLEND ENGINE v5.0
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("### 🌍 ŞEHİR SEÇİMİ")
    city_names = list(CITIES.keys())

    c1 = st.selectbox("Şehir 1", city_names, index=0, key="c1")
    w1 = st.slider("w1", 0, 100, 50, key="w1", label_visibility="collapsed")
    c2 = st.selectbox("Şehir 2", city_names, index=1, key="c2")
    w2 = st.slider("w2", 0, 100, 50, key="w2", label_visibility="collapsed")

    use3 = st.checkbox("➕ 3. Şehir", key="u3")
    c3, w3 = None, 0
    if use3:
        c3 = st.selectbox("Şehir 3", city_names, index=2, key="c3")
        w3 = st.slider("w3", 0, 100, 33, key="w3", label_visibility="collapsed")

    use4 = st.checkbox("➕ 4. Şehir", key="u4")
    c4, w4 = None, 0
    if use4:
        c4 = st.selectbox("Şehir 4", city_names, index=3, key="c4")
        w4 = st.slider("w4", 0, 100, 25, key="w4", label_visibility="collapsed")

    raw = [(c1,w1),(c2,w2)]
    if use3 and c3: raw.append((c3,w3))
    if use4 and c4: raw.append((c4,w4))
    total_w = sum(w for _,w in raw) or 1
    normalized = [(c, w/total_w) for c,w in raw]

    # Phase 5: override with AI blend if active
    if st.session_state.get("use_ai_blend") and st.session_state.get("ai_blend"):
        ab = st.session_state.ai_blend
        normalized = [(c["name"], c["weight"]) for c in ab["cities"] if c["name"] in CITIES]

    st.divider()
    st.markdown("### 🗄️ VERİ KAYNAĞI")
    for cname, _ in normalized:
        b_ok = is_cached(cname)
        s_ok = is_street_cached(cname)
        b_col = "#00d4ff" if b_ok else "#333"
        s_col = "#00d4ff" if s_ok else "#333"
        st.markdown(
            f"<span style='font-size:.8em;color:#666;font-family:Inter,sans-serif;'>"
            f"{CITIES[cname]['emoji']} {cname} &nbsp;"
            f"<span class='cache-dot' style='background:{b_col};'></span>binalar "
            f"<span class='cache-dot' style='background:{s_col};'></span>sokaklar</span>",
            unsafe_allow_html=True,
        )

    data_mode = st.radio("Mod", ["🌐 OSM Gerçek Veri","⚙️ Prosedürel"],
                         key="data_mode")
    use_osm = data_mode.startswith("🌐")

    if use_osm and not HAS_OSM:
        st.warning("⚠️ `osmnx` yüklü değil.\n```\npip install osmnx\n```")

    if st.button("🗑️ Önbelleği Temizle", key="clr"):
        for cname, _ in normalized: clear_cache(cname)
        st.rerun()

    st.divider()
    st.markdown("### ⚙️ HARİTA AYARLARI")
    density   = st.slider("Bina Yoğunluğu",  20, 140, 70)
    map_size  = st.slider("Harita Çapı",      100, 400, 220)
    show_lm   = st.toggle("Landmark'ları Göster", value=True)
    weather   = st.select_slider("Hava", ["Açık","Puslu","Yoğun Sis"])
    cam_mode  = st.radio("Kamera", ["3. Şahıs","Serbest Uçuş"], horizontal=True)

    st.divider()
    st.markdown("### 👤 KARAKTER MODELİ")
    fbx_file = st.file_uploader(
        "FBX Karakter Yükle", type=["fbx"], key="fbx_uploader",
        help="FBX formatında karakter — animasyonlar otomatik algılanır",
    )
    if fbx_file is not None:
        import base64 as _b64
        fbx_bytes = fbx_file.read()
        size_kb   = len(fbx_bytes) // 1024
        if size_kb > 20_000:
            st.warning("⚠️ Dosya 20MB üzeri — yavaş yüklenebilir")
        st.session_state.fbx_b64  = _b64.b64encode(fbx_bytes).decode()
        st.session_state.fbx_name = fbx_file.name
        st.success(f"✅ {fbx_file.name} ({size_kb} KB)")
    if st.session_state.get("fbx_b64"):
        st.markdown(
            "<span style='color:#00d4ff;font-size:.78em;font-family:Inter,sans-serif;'>"
            "⚡ Otomatik ölçeklendirme aktif — karakter ~2.2 birime sığdırılır</span>",
            unsafe_allow_html=True,
        )
        char_scale = st.slider(
            "Ölçek Çarpanı", 0.1, 4.0, 1.0, step=0.05, format="%.2f", key="char_scale",
            help="1.0 = otomatik (2.2 birim yükseklik) · 0.5 = yarı boy · 2.0 = çift"
        )
        char_cam_h = st.slider("Kamera Yüksekliği", 2, 25, 9, key="char_cam_h")
        if st.button("🗑️ FBX'i Kaldır", key="rm_fbx"):
            del st.session_state.fbx_b64
            st.rerun()
    else:
        char_scale = 1.0
        char_cam_h = 7

    st.divider()
    st.markdown("### 🌦️ SPRİNT 1 — MEVSİM & ATMOSFER")
    season = st.selectbox(
        "Mevsim",
        ["Yaz", "İlkbahar", "Sonbahar", "Kış"],
        index=0, key="season",
    )
    # Season-specific extra options
    if season == "Kış":
        snow_density = st.slider("Kar Yoğunluğu", 500, 5000, 2500, step=500, key="snow_d")
    else:
        snow_density = 0
    show_sun_disk = st.toggle("Güneş Diski", value=True, key="sun_disk",
                              help="Gökyüzünde güneş ışıması")

    st.divider()
    st.markdown("### 🏛️ SPRİNT 4 — ÇARPIŞMA TESPİTİ")
    enable_collision = st.toggle(
        "Binalara Çarpma", value=True, key="coll",
        help="AABB collision + slide-along-wall — binalar ve landmark'lar engel"
    )
    st.markdown(
        "<span style='color:#666;font-size:.78em;font-family:Inter,sans-serif;'>"
        "Aktifken binalara çarpılır, duvara kayarak geçiş sağlanır.</span>",
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown("### 🌿 SPRİNT 3 — DOĞA ELEMANLARI")
    tree_count = st.slider("Ağaç Sayısı", 0, 240, 70, step=10, key="tree_count")
    show_river = st.toggle("Nehir", value=True, key="show_river",
                           help="Kıvrımlı CatmullRom nehir + animasyonlu su dokusu")

    st.divider()
    st.markdown("### 🗺️ FAZ 3 — BÖLGE & ARAZİ")
    zone_mode = st.toggle("Bölge Bazlı Yerleşim", value=True, key="zm",
                          help="Açık: harita şehir bölgelerine ayrılır. Kapalı: rastgele harmanlama.")
    softness  = st.slider("Bölge Sınırı Yumuşaklığı", 0.0, 1.0, 0.32, step=0.04, key="soft",
                          help="0 = keskin Voronoi, 1 = tamamen bulanık") if zone_mode else 0.32
    show_zones   = st.toggle("Bölge Overlayı",  value=True,  key="szn")
    show_streets = st.toggle("Sokak Ağı",        value=True,  key="sst")
    show_terrain = st.toggle("Arazi Yüksekliği", value=True,  key="ste")

    st.divider()
    st.markdown("### 🏷️ FAZ 4 — LANDMARK SPONSORLARI")

    # Session state init
    if "sponsors" not in st.session_state:
        st.session_state.sponsors = {}
    if "lm_list" not in st.session_state:
        st.session_state.lm_list = {}

    lm_list = st.session_state.lm_list
    sponsors = st.session_state.sponsors

    if not lm_list:
        st.markdown(
            "<span style='color:#333;font-size:.8em;font-family:Inter,sans-serif;'>"
            "Önce HARMANLA'ya basın — landmark listesi yüklenecek.</span>",
            unsafe_allow_html=True,
        )
    else:
        sponsored_count = sum(1 for v in sponsors.values() if v.get("brand","").strip())
        st.markdown(
            f"<span style='color:#00d4ff;font-size:.82em;font-family:Inter,sans-serif;'>"
            f"✅ {sponsored_count} aktif sponsor</span>",
            unsafe_allow_html=True,
        )
        for city_name, lms in lm_list.items():
            color = CITIES[city_name]["color"]
            st.markdown(
                f"<div style='color:{color};font-size:.82em;font-weight:600;"
                f"font-family:Inter,sans-serif;margin:8px 0 4px 0;'>"
                f"{CITIES[city_name]['emoji']} {city_name}</div>",
                unsafe_allow_html=True,
            )
            for lm_idx, lm in enumerate(lms[:10]):
                key = sponsor_key(city_name, lm["name"])
                # Widget key includes index to avoid duplicates when name prefixes collide
                wkey = f"{key}_{lm_idx}"
                is_sp = key in sponsors and bool(sponsors[key].get("brand","").strip())
                badge = "🟢" if is_sp else "⚪"
                with st.expander(f"{badge} {lm['name'][:28]}", expanded=False):
                    brand = st.text_input(
                        "Marka / Sponsor",
                        value=sponsors.get(key, {}).get("brand",""),
                        key=f"br_{wkey}",
                        placeholder="örn: Nike, Toyota…",
                    )
                    col_color = st.color_picker(
                        "Marka Rengi",
                        value=sponsors.get(key, {}).get("color","#e94560"),
                        key=f"clr_{wkey}",
                    )
                    if brand.strip():
                        sponsors[key] = {"brand": brand.strip(), "color": col_color}
                    else:
                        sponsors.pop(key, None)

    st.divider()
    st.markdown("### 🤖 FAZ 5 — HARMAN AI")

    # Session state
    if "api_key" not in st.session_state:
        st.session_state.api_key = ""
    if "ai_blend" not in st.session_state:
        st.session_state.ai_blend = None
    if "world_lore" not in st.session_state:
        st.session_state.world_lore = ""
    if "ai_sponsor_suggestions" not in st.session_state:
        st.session_state.ai_sponsor_suggestions = []

    # API Key
    try:
        _ak = st.secrets["ANTHROPIC_API_KEY"]
        st.markdown(
            "<span style='color:#00d4ff;font-size:.8em;font-family:Inter,sans-serif;'>"
            "✅ API key: secrets'ten yüklendi</span>",
            unsafe_allow_html=True,
        )
    except Exception:
        _ak = st.text_input(
            "Claude API Key",
            type="password",
            value=st.session_state.api_key,
            key="ak_input",
            placeholder="sk-ant-api03-…",
        )
        st.session_state.api_key = _ak

    api_key = _ak

    if not HAS_ANTHROPIC:
        st.warning("⚠️ `anthropic` kütüphanesi yüklü değil.\n```\npip install anthropic\n```")

    ai_mode = st.toggle("AI Modu Aktif", value=False, key="ai_mode_toggle",
                        disabled=not (HAS_ANTHROPIC and bool(api_key)),
                        help="Doğal dil ile şehir tanımı yap, AI harmanı oluştursun")

    st.divider()
    gen_btn = st.button("🗺️  HARMANLA", use_container_width=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class='harman-header'>
    <div class='harman-title'>HARMAN</div>
    <div class='harman-sub'>Dünya Şehirlerinden Oyun Haritası Üret &nbsp;·&nbsp;
        City Blend Engine &nbsp;·&nbsp; v5.0 AI + Landmarks + Zones + Streets</div>
</div>""", unsafe_allow_html=True)

bar_seg  = "".join(f'<div class="blend-segment" style="width:{w*100:.1f}%;background:{CITIES[c]["color"]};"></div>' for c,w in normalized)
pills    = "".join(f'<span class="city-pill" style="border-color:{CITIES[c]["color"]};color:{CITIES[c]["color"]};">{CITIES[c]["emoji"]} {c}&nbsp;<b>{w*100:.0f}%</b></span>' for c,w in normalized)
tags_html= "".join(f'<span class="dna-tag">{t}</span>' for t in collect_tags(normalized))

st.markdown(f"""
<div style='margin-bottom:16px;'>
    <div class='blend-bar'>{bar_seg}</div>
    <div style='margin-top:10px;'>{pills}</div>
</div>
<div class='dna-panel'>
    <span style='color:#333;font-size:.78em;font-family:Inter,sans-serif;margin-right:4px;'>DNA:</span>
    {tags_html}
</div>""", unsafe_allow_html=True)
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# ── PHASE 5 — AI BLEND PANEL ─────────────────────────────────────────────────
if st.session_state.get("ai_mode_toggle") and HAS_ANTHROPIC and st.session_state.get("api_key") or \
   st.session_state.get("api_key") and HAS_ANTHROPIC:

    with st.expander("🤖 HARMAN AI — Doğal Dil ile Harita Tanımla", expanded=st.session_state.get("ai_mode_toggle", False)):
        st.markdown(
            "<div style='color:#666;font-size:.82em;font-family:Inter,sans-serif;margin-bottom:8px;'>"
            "Haritanı Türkçe veya İngilizce tanımla — AI şehirleri ve oranları belirlesin.</div>",
            unsafe_allow_html=True,
        )
        # Example prompts
        EXAMPLES = [
            "Neon ışıklı gece şehri, Tokyo yoğunluğu ve İstanbul tarihi dokusu",
            "Sisli tarihi Avrupa, Viktoryen ve Haussmann mimarisinin kesişimi",
            "Fütüristik çöl metropolü, cam gökdelenler ve lüks seyreklisi",
        ]
        ex_cols = st.columns(3)
        for i, ex in enumerate(EXAMPLES):
            with ex_cols[i]:
                if st.button(f"💡 Örnek {i+1}", key=f"ex{i}", help=ex, use_container_width=True):
                    st.session_state.ai_prompt_val = ex

        ai_prompt = st.text_area(
            "Harita tasviri",
            value=st.session_state.get("ai_prompt_val", ""),
            placeholder=EXAMPLES[0],
            key="ai_prompt",
            height=90,
            label_visibility="collapsed",
        )

        ai_gen = st.button("🤖 AI İLE OLUŞTUR", use_container_width=True, key="ai_gen_btn",
                           disabled=not ai_prompt.strip())

        if ai_gen and ai_prompt.strip():
            with st.spinner("Claude analiz ediyor…"):
                result = parse_blend_prompt(ai_prompt.strip(), st.session_state.api_key)
            if "error" in result:
                st.error(f"Hata: {result['error']}")
            else:
                st.session_state.ai_blend = result
                st.success("✅ AI harmanı hazır — aşağıda önizleyin ve haritayı oluşturun.")

        # Show AI blend preview
        if st.session_state.ai_blend and "cities" in st.session_state.ai_blend:
            ab = st.session_state.ai_blend
            pills_ai = "".join(
                f'<span class="city-pill" style="border-color:{CITIES.get(c["name"],{}).get("color","#888")};"'
                f' style="color:{CITIES.get(c["name"],{}).get("color","#888")};">'
                f'{CITIES.get(c["name"],{}).get("emoji","🌆")} {c["name"]} <b>{int(c["weight"]*100)}%</b></span>'
                for c in ab["cities"] if c["name"] in CITIES
            )
            bar_ai = "".join(
                f'<div class="blend-segment" style="width:{c["weight"]*100:.1f}%;background:{CITIES.get(c["name"],{}).get("color","#888")};"></div>'
                for c in ab["cities"] if c["name"] in CITIES
            )
            st.markdown(f"""
            <div style='background:rgba(0,212,255,.06);border:1px solid rgba(0,212,255,.3);
                        border-radius:10px;padding:14px 18px;margin-top:8px;'>
                <div style='color:#00d4ff;font-size:.75em;letter-spacing:2px;
                            font-family:Orbitron,monospace;margin-bottom:8px;'>🤖 AI ÖNERİSİ</div>
                <div class='blend-bar' style='margin-bottom:10px;'>{bar_ai}</div>
                <div>{pills_ai}</div>
                <div style='color:#888;font-size:.8em;font-family:Inter,sans-serif;
                            margin-top:10px;font-style:italic;'>"{ab.get("description","")}"</div>
                <div style='color:#555;font-size:.75em;font-family:Inter,sans-serif;margin-top:6px;'>
                    Hava: {ab.get("weather","Açık")} &nbsp;·&nbsp;
                    Yoğunluk: {ab.get("density", 70)} &nbsp;·&nbsp;
                    Ruh hali: {ab.get("mood","")}
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_apply, col_clear = st.columns([3, 1])
            with col_apply:
                if st.button("✅ Bu Haritayı Oluştur", key="apply_ai", use_container_width=True):
                    st.session_state.use_ai_blend = True
                    st.rerun()
            with col_clear:
                if st.button("✕ Temizle", key="clear_ai", use_container_width=True):
                    st.session_state.ai_blend = None
                    st.session_state.use_ai_blend = False
                    st.rerun()

# ── CONFIG BUILDER ────────────────────────────────────────────────────────────
def _build_config(normalized, density, map_size, show_lm, weather, cam_mode,
                  buildings=None, streets=None, zones=None, terrain=None,
                  landmarks=None):
    fog_mult = {"Açık":1.0,"Puslu":2.8,"Yoğun Sis":6.0}[weather]
    bsky = blend_rgb([(CITIES[c]["palette"]["sky"],   w) for c,w in normalized])
    bgnd = blend_rgb([(CITIES[c]["palette"]["ground"],w) for c,w in normalized])
    bfog = sum(CITIES[c]["fog"]*w for c,w in normalized) * fog_mult

    cities_js = [{
        "name":    name,
        "weight":  weight,
        "lm_type": CITIES[name]["lm_type"],
        "lm_name": CITIES[name]["landmark"],
        "color":   CITIES[name]["color"],
        "palette": {k: rgb_js(v) for k,v in CITIES[name]["palette"].items()},
    } for name, weight in normalized]

    zones_js = [{
        "city":   z["city"],
        "weight": z["weight"],
        "cx":     z["cx"],
        "cz":     z["cz"],
        "radius": z["radius"],
        "color":  CITIES[z["city"]]["color"],
    } for z in (zones or [])]

    return {
        "cities":        cities_js,
        "density":       density,
        "mapSize":       map_size,
        "showLandmarks": show_lm,
        "fogDensity":    round(bfog, 5),
        "skyHex":        rgb_js(bsky),
        "groundHex":     rgb_js(bgnd),
        "freeCamera":    cam_mode == "Serbest Uçuş",
        "useOSM":        buildings is not None,
        "buildings":     buildings or [],
        "streets":       streets   or [],
        "zones":         zones_js,
        "terrain":       terrain   or {"amplitude":0, "frequency":0.04, "enabled":False},
        "showZones":     show_zones,
        "showStreets":   show_streets,
        "showTerrain":   show_terrain,
        "landmarks":     landmarks or [],
        "fbxCharacter":  st.session_state.get("fbx_b64", ""),
        "charScale":     st.session_state.get("char_scale", 0.02),
        "charCamH":      st.session_state.get("char_cam_h", 7),
        # Sprint 1
        "season":        st.session_state.get("season", "Yaz"),
        "snowDensity":   st.session_state.get("snow_d", 0),
        "showSunDisk":   st.session_state.get("sun_disk", True),
        # Sprint 3
        "treeCount":     st.session_state.get("tree_count", 70),
        "showRiver":     st.session_state.get("show_river", True),
        # Sprint 4
        "enableCollision": st.session_state.get("coll", True),
    }

# ── HTML GENERATOR ────────────────────────────────────────────────────────────
def generate_html(cfg: dict) -> str:
    cfg_json = json.dumps(cfg)

    js = r"""
const HARMAN = """ + cfg_json + r""";

// ── UTILITIES ────────────────────────────────────────────────────────────────
function C(h) { return new THREE.Color(h); }
function C3(h) {
    const s = String(h);
    return s.startsWith('0x') || s.startsWith('0X')
        ? new THREE.Color(parseInt(s, 16))
        : new THREE.Color(s);
}

// ═══════════════════════════════════════════════════════════════════════════
// SPRINT 4 — ÇARPIŞMA TESPİTİ (AABB + Slide-Along-Wall)
// ═══════════════════════════════════════════════════════════════════════════

const colliders = [];   // {minX, maxX, minZ, maxZ, cx, cz}

function addCollider(group, margin) {
    if (!HARMAN.enableCollision) return;
    const m = margin !== undefined ? margin : 0.45;
    try {
        const box = new THREE.Box3().setFromObject(group);
        if (box.isEmpty() ||
            (box.max.x - box.min.x) < 0.2 ||
            (box.max.z - box.min.z) < 0.2) return;
        colliders.push({
            minX: box.min.x - m,
            maxX: box.max.x + m,
            minZ: box.min.z - m,
            maxZ: box.max.z + m,
            cx:   (box.min.x + box.max.x) * 0.5,
            cz:   (box.min.z + box.max.z) * 0.5,
        });
    } catch(e) {}   // Box3 hataları sessizce geç
}

function checkCollision(nx, nz) {
    if (!HARMAN.enableCollision || colliders.length === 0) return false;
    const R = 0.60;   // oyuncu yarıçapı
    for (const col of colliders) {
        // Uzak collider'ları erken at — performans
        if (Math.abs(col.cx - nx) > 32 || Math.abs(col.cz - nz) > 32) continue;
        if (nx > col.minX - R && nx < col.maxX + R &&
            nz > col.minZ - R && nz < col.maxZ + R) return true;
    }
    return false;
}

function pickCity() {
    const r = Math.random(); let acc = 0;
    for (const c of HARMAN.cities) { acc += c.weight; if (r <= acc) return c; }
    return HARMAN.cities[HARMAN.cities.length-1];
}
// Belirtilen dünya koordinatı için en yakın şehri zone ağırlıklarına göre döndür
function cityForPos(px, pz) {
    if (!HARMAN.zones || HARMAN.zones.length === 0) return pickCity().name;
    let best = HARMAN.zones[0], minScore = Infinity;
    for (const zone of HARMAN.zones) {
        const dist = Math.hypot(px - zone.cx, pz - zone.cz);
        const score = dist / (zone.weight + 0.01);
        if (score < minScore) { minScore = score; best = zone; }
    }
    return best.city;
}

// ═══════════════════════════════════════════════════════════════════════════
// SPRINT 1 — MEVSIM & ATMOSFER SİSTEMİ
// ═══════════════════════════════════════════════════════════════════════════

const SEASON_CFG = {
    'Yaz': {
        skyTop:'#082558', skyMid:'#164882', skyBot:'#2a6898',
        sunColor:0xfff5cc, sunInt:1.15, sunPos:[80,110,55],
        fillColor:0x88aeff, fillInt:0.25,
        hemSky:0x88bbdd, hemGnd:0x446633, hemInt:0.38,
        fogMult:0.65, fogHex:'#2a6898',
        groundTint:'#7a8a60',
        exposure:0.88, snow:false,
    },
    'İlkbahar': {
        skyTop:'#1a5898', skyMid:'#4a96cc', skyBot:'#a8d8ee',
        sunColor:0xfff8e0, sunInt:0.98, sunPos:[70,85,60],
        fillColor:0x99ccff, fillInt:0.22,
        hemSky:0xaaccee, hemGnd:0x557744, hemInt:0.36,
        fogMult:0.78, fogHex:'#a8d8ee',
        groundTint:'#6a8055',
        exposure:0.85, snow:false,
    },
    'Sonbahar': {
        skyTop:'#4a4828', skyMid:'#9a7a38', skyBot:'#c4a060',
        sunColor:0xffcc80, sunInt:0.82, sunPos:[95,58,70],
        fillColor:0xddaa88, fillInt:0.20,
        hemSky:0xaa8844, hemGnd:0x664422, hemInt:0.32,
        fogMult:1.10, fogHex:'#b8985a',
        groundTint:'#7a5a30',
        exposure:0.80, snow:false,
    },
    'Kış': {
        skyTop:'#1c2c3a', skyMid:'#4a6888', skyBot:'#9ab8cc',
        sunColor:0xc8deff, sunInt:0.58, sunPos:[105,42,75],
        fillColor:0x99aabb, fillInt:0.18,
        hemSky:0x8899aa, hemGnd:0xddeeff, hemInt:0.28,
        fogMult:1.55, fogHex:'#aabbcc',
        groundTint:'#ccd8e0',
        exposure:0.75, snow:true,
    },
};
const SC = SEASON_CFG[HARMAN.season] || SEASON_CFG['Yaz'];

// ═══════════════════════════════════════════════════════════════════════════
// SPRINT 3 — DOĞA ELEMANLARI: AĞAÇ & NEHİR KONFIG
// Not: Mevsim/şehir anahtarları ASCII formatında — Unicode parse sorunları önlenir
// ═══════════════════════════════════════════════════════════════════════════

// Mevsim adlarını ASCII anahtara çevir (JSON unicode decode sonrası eşleştirme için)
function _seasonKey(s) {
    if (s === 'Yaz')      return 'summer';
    if (s === 'Sonbahar') return 'autumn';
    if (s === 'Kis' || s.indexOf('K') === 0 && s.length <= 4) return 'winter';
    return 'spring';  // Ilkbahar fallback
}

const TREE_COLORS = {
    'Tokyo':    { summer:'#2a7e30', spring:'#f0a0c0', autumn:'#cc5520', winter:'#3a2818' },
    'Istanbul': { summer:'#1a6828', spring:'#3a9045', autumn:'#8a6025', winter:'#2a1a12' },
    'Paris':    { summer:'#3a8830', spring:'#5aaa42', autumn:'#b87828', winter:'#281a10' },
    'NewYork':  { summer:'#286e22', spring:'#48983a', autumn:'#c04a18', winter:'#201008' },
    'Dubai':    { summer:'#2a7020', spring:'#2a7020', autumn:'#2a7020', winter:'#2a7020' },
    'Londra':   { summer:'#256a1e', spring:'#3a8c2e', autumn:'#9a6a20', winter:'#1e1208' },
};

// City adını ASCII anahtara normalize et
function _cityKey(c) {
    if (c.indexOf('stanbul') >= 0) return 'Istanbul';
    if (c.indexOf('New') >= 0)     return 'NewYork';
    return c;
}

// ═══════════════════════════════════════════════════════════════════════════
// SPRINT 2 — PROCEDURAL TEXTURE SYSTEM
// Canvas-tabanlı; harici dosya yok. Her doku bir kez üretilir ve TEXCACHE'e
// alınır. Malzeme önbelleği (MATCACHE) draw call'ları drastik azaltır.
// ═══════════════════════════════════════════════════════════════════════════

const TEXCACHE = {};
const MATCACHE = {};

/* Ortak canvas-texture fabrikası */
function _tex(key, drawFn, rX, rY, S=512) {
    if (TEXCACHE[key]) return TEXCACHE[key];
    const cv = document.createElement('canvas');
    cv.width = cv.height = S;
    drawFn(cv.getContext('2d'), S);
    const t = new THREE.CanvasTexture(cv);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(rX, rY);
    TEXCACHE[key] = t;
    return t;
}

/* Hex → RGB [0-255]
   Handles both Three.js "0xRRGGBB" palette format AND CSS "#RRGGBB" format */
function _rgb(hex) {
    const n = parseInt(String(hex).replace(/^0x|^#/, ''), 16);
    if (isNaN(n)) return [128, 128, 128];
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

// ── YAPI DOKU FONKSİYONLARI ───────────────────────────────────────────────

function txBrick(hex, aged=false) {
    const [r,g,b]=_rgb(hex); const d=aged?0.70:1;
    return _tex(`br_${hex}_${aged}`, (ctx,S)=>{
        // Koyu harç — AC hissi için yüksek kontrast
        const mr=Math.max(0,Math.round(r*d*0.38)), mg=Math.max(0,Math.round(g*d*0.35)), mb=Math.max(0,Math.round(b*d*0.32));
        ctx.fillStyle=`rgb(${mr},${mg},${mb})`; ctx.fillRect(0,0,S,S);
        const BW=60, BH=26;  // Daha büyük tuğla = uzaktan görünür
        for(let row=0;row<S/BH+2;row++){
            const off=(row%2)*(BW/2);
            for(let col=-1;col<S/BW+2;col++){
                const v=(Math.random()-0.5)*44;
                const cr=Math.min(255,Math.max(0,Math.round(r*d+v)));
                const cg=Math.min(255,Math.max(0,Math.round(g*d+v*0.85-5)));
                const cb=Math.min(255,Math.max(0,Math.round(b*d+v*0.65-10)));
                ctx.fillStyle=`rgb(${cr},${cg},${cb})`;
                ctx.fillRect(col*BW+off+2.5, row*BH+2.5, BW-5, BH-5);
                // 3D kenar gölgesi
                ctx.fillStyle='rgba(0,0,0,0.22)';
                ctx.fillRect(col*BW+off+2.5, row*BH+2.5, BW-5, 4);
                ctx.fillRect(col*BW+off+2.5, row*BH+2.5, 4, BH-5);
                // Highlight
                ctx.fillStyle='rgba(255,255,255,0.12)';
                ctx.fillRect(col*BW+off+BW-8, row*BH+2.5, 4, BH-5);
                ctx.fillRect(col*BW+off+2.5, row*BH+BH-8, BW-5, 4);
            }
        }
    }, 2, 6);
}

function txLimestone(hex) {
    const [r,g,b]=_rgb(hex);
    return _tex(`ls_${hex}`, (ctx,S)=>{
        ctx.fillStyle=`rgb(${r},${g},${b})`; ctx.fillRect(0,0,S,S);
        // Taş yüzey dokusu — yüksek kontrastlı
        for(let i=0;i<1400;i++){
            const sh=(Math.random()-0.5)*24;
            ctx.fillStyle=`rgba(${sh>0?255:0},${sh>0?255:0},${sh>0?255:0},${Math.abs(sh)*0.010})`;
            ctx.fillRect(Math.random()*S,Math.random()*S,1+Math.random()*4,1+Math.random()*3);
        }
        // Kalın ashlar derz çizgileri — AC taş bloğu hissi
        const BH=46, jointCol=`rgba(${Math.max(0,r-70)},${Math.max(0,g-65)},${Math.max(0,b-58)},0.72)`;
        ctx.strokeStyle=jointCol; ctx.lineWidth=3.5;
        for(let y=BH;y<S;y+=BH){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(S,y);ctx.stroke();}
        ctx.lineWidth=2.5;
        for(let row=0;row<S/BH+1;row++){const off=(row%2)*95;
            for(let x=off;x<S+95;x+=190){ctx.beginPath();ctx.moveTo(x,row*BH);ctx.lineTo(x,(row+1)*BH);ctx.stroke();}}
        // Dip yıpranma — eskimiş görünüm
        const grad=ctx.createLinearGradient(0,S*0.75,0,S);
        grad.addColorStop(0,'rgba(0,0,0,0)'); grad.addColorStop(1,'rgba(0,0,0,0.20)');
        ctx.fillStyle=grad; ctx.fillRect(0,0,S,S);
    }, 2, 4);
}

function txGlass(hex) {
    const [r,g,b]=_rgb(hex);
    return _tex(`gl_${hex}`, (ctx,S)=>{
        ctx.fillStyle=`rgb(${r},${g},${b})`; ctx.fillRect(0,0,S,S);
        const PW=36, PH=52;
        ctx.strokeStyle='rgba(255,255,255,0.18)'; ctx.lineWidth=2.5;
        for(let x=0;x<=S;x+=PW){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,S);ctx.stroke();}
        for(let y=0;y<=S;y+=PH){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(S,y);ctx.stroke();}
        // Panel yansımaları
        for(let x=2;x<S;x+=PW) for(let y=2;y<S;y+=PH){
            const gr=ctx.createLinearGradient(x,y,x+PW,y+PH);
            gr.addColorStop(0,'rgba(255,255,255,0.18)');
            gr.addColorStop(0.45,'rgba(255,255,255,0.03)');
            gr.addColorStop(1,'rgba(0,0,0,0.07)');
            ctx.fillStyle=gr; ctx.fillRect(x+1,y+1,PW-3,PH-3);
        }
        // Ara sıra koyu yansıma bandı
        for(let i=0;i<3;i++){ctx.fillStyle='rgba(0,0,0,0.06)';ctx.fillRect(0,Math.random()*S,S,8+Math.random()*14);}
    }, 2, 6);
}

function txConcrete(hex) {
    const [r,g,b]=_rgb(hex);
    return _tex(`cn_${hex}`, (ctx,S)=>{
        ctx.fillStyle=`rgb(${r},${g},${b})`; ctx.fillRect(0,0,S,S);
        // Yoğun beton dokusu
        for(let i=0;i<3500;i++){
            const sh=(Math.random()-0.5)*28;
            ctx.fillStyle=`rgba(${sh>0?255:0},${sh>0?255:0},${sh>0?255:0},${Math.abs(sh)*0.0055})`;
            ctx.fillRect(Math.random()*S,Math.random()*S,1+Math.random()*3,1+Math.random()*5);
        }
        // Belirgin panel çizgileri
        ctx.strokeStyle='rgba(0,0,0,0.12)'; ctx.lineWidth=1.5;
        for(let y=85;y<S;y+=85){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(S,y);ctx.stroke();}
        // Form bağlantı delikleri
        ctx.fillStyle='rgba(0,0,0,0.18)';
        for(let x=90;x<S;x+=130) for(let y=85;y<S;y+=85){ctx.beginPath();ctx.arc(x,y,3,0,Math.PI*2);ctx.fill();}
        // Alt yıpranma
        const gr=ctx.createLinearGradient(0,S*0.8,0,S);
        gr.addColorStop(0,'rgba(0,0,0,0)'); gr.addColorStop(1,'rgba(0,0,0,0.15)');
        ctx.fillStyle=gr; ctx.fillRect(0,0,S,S);
    }, 2, 4);
}

// ── ZEMİN DOKU FONKSİYONLARI ─────────────────────────────────────────────

function txCobble() {
    return _tex('cobble', (ctx, S) => {
        // Koyu derzler arası zemin
        ctx.fillStyle = '#202025'; ctx.fillRect(0, 0, S, S);
        for (let i = 0; i < 200; i++) {
            const x = Math.random()*S, y = Math.random()*S;
            const w = 16+Math.random()*24, h = 11+Math.random()*17;
            // Taşlar daha parlak (78-140) → görünür olsun
            const v = 78 + Math.floor(Math.random()*62);
            ctx.fillStyle = `rgb(${v},${v-4},${v-9})`;
            ctx.beginPath(); ctx.ellipse(x,y,w/2,h/2,Math.random()*Math.PI,0,Math.PI*2); ctx.fill();
            ctx.strokeStyle = 'rgba(0,0,0,0.55)'; ctx.lineWidth = 1.8; ctx.stroke();
            ctx.strokeStyle = 'rgba(255,255,255,0.10)'; ctx.lineWidth = 0.8; ctx.stroke();
        }
    }, 1, 1);
}

function txAsphalt() {
    return _tex('asphalt',(ctx,S)=>{
        ctx.fillStyle='#18181e'; ctx.fillRect(0,0,S,S);
        for(let i=0;i<1100;i++){
            const v=18+Math.random()*22;
            ctx.fillStyle=`rgb(${v},${v},${v+3})`;
            ctx.beginPath(); ctx.arc(Math.random()*S,Math.random()*S,0.7+Math.random()*2.3,0,Math.PI*2); ctx.fill();
        }
    }, 1, 1);
}

function txSnowGnd() {
    return _tex('snowgnd_v2', (ctx, S) => {
        // Kar beyazı zemin
        ctx.fillStyle = '#ddeaf5'; ctx.fillRect(0, 0, S, S);
        // Kar yüzeyi — yumuşak dalgalı tümsekler
        for (let i = 0; i < 500; i++) {
            const v = 216 + Math.floor(Math.random()*38);
            ctx.fillStyle = `rgb(${v}, ${v+1}, ${v+8})`;
            ctx.beginPath();
            ctx.ellipse(Math.random()*S, Math.random()*S,
                5+Math.random()*22, 2+Math.random()*10,
                Math.random()*Math.PI, 0, Math.PI*2);
            ctx.fill();
        }
        // Kar gölge izleri (mavi tona)
        for (let i = 0; i < 120; i++) {
            ctx.fillStyle = `rgba(90, 125, 175, ${0.07+Math.random()*0.09})`;
            ctx.beginPath();
            ctx.ellipse(Math.random()*S, Math.random()*S,
                6+Math.random()*18, 3+Math.random()*9,
                Math.random()*Math.PI, 0, Math.PI*2);
            ctx.fill();
        }
        // İnce çatlak izler
        ctx.strokeStyle = 'rgba(160,190,220,0.18)'; ctx.lineWidth = 0.7;
        for (let i = 0; i < 30; i++) {
            const x=Math.random()*S, y=Math.random()*S;
            ctx.beginPath(); ctx.moveTo(x,y);
            ctx.lineTo(x+Math.random()*40-20, y+Math.random()*40-20);
            ctx.stroke();
        }
    }, 1, 1);
}

function txGrass() {
    return _tex('grass_v2', (ctx, S) => {
        // Taze toprak zemini
        ctx.fillStyle = '#2a5018'; ctx.fillRect(0, 0, S, S);
        // Yoğun çimen — farklı uzunluk ve açılarda
        for (let i = 0; i < 2200; i++) {
            const x = Math.random()*S, y = Math.random()*S;
            const h = 3 + Math.random()*9;
            const lean = Math.random()*4 - 2;
            const g = 55 + Math.floor(Math.random()*55);
            ctx.strokeStyle = `rgb(20, ${g}, 15)`;
            ctx.lineWidth = 0.9;
            ctx.beginPath();
            ctx.moveTo(x, y + h);
            ctx.quadraticCurveTo(x + lean, y + h*0.4, x + lean*1.5, y);
            ctx.stroke();
        }
        // Toprak yamalar
        for (let i = 0; i < 40; i++) {
            const x=Math.random()*S, y=Math.random()*S;
            ctx.fillStyle = `rgba(70,45,15,${0.12+Math.random()*0.18})`;
            ctx.beginPath();
            ctx.ellipse(x,y,10+Math.random()*20,5+Math.random()*12,Math.random()*Math.PI,0,Math.PI*2);
            ctx.fill();
        }
        // Taş parçaları
        for (let i = 0; i < 30; i++) {
            const v = 55+Math.floor(Math.random()*35);
            ctx.fillStyle = `rgb(${v},${v-3},${v-8})`;
            ctx.beginPath();
            ctx.ellipse(Math.random()*S,Math.random()*S,3+Math.random()*7,2+Math.random()*4,Math.random()*Math.PI,0,Math.PI*2);
            ctx.fill();
        }
    }, 1, 1);
}

function txAutumnGnd() {
    return _tex('autumn_v2', (ctx, S) => {
        // Kuru toprak zemini
        ctx.fillStyle = '#5a3415'; ctx.fillRect(0, 0, S, S);
        // Kuru toprak dokusu
        for (let i = 0; i < 1200; i++) {
            const v = 58+Math.floor(Math.random()*38);
            ctx.fillStyle = `rgb(${v}, ${v-12}, ${v-28})`;
            ctx.fillRect(Math.random()*S, Math.random()*S, 1+Math.random()*4, 1+Math.random()*3);
        }
        // Kuru yapraklar — oval şekiller
        for (let i = 0; i < 180; i++) {
            const x=Math.random()*S, y=Math.random()*S;
            const w=6+Math.random()*18, h=4+Math.random()*9;
            const hue=12+Math.floor(Math.random()*38);  // turuncu-kahverengi-kırmızı
            const lig=22+Math.floor(Math.random()*28);
            ctx.fillStyle = `hsl(${hue},55%,${lig}%)`;
            ctx.save();
            ctx.translate(x,y); ctx.rotate(Math.random()*Math.PI);
            ctx.beginPath(); ctx.ellipse(0,0,w/2,h/2,0,0,Math.PI*2); ctx.fill();
            ctx.restore();
        }
        // Kuru dal parçaları
        ctx.strokeStyle = 'rgba(40,20,5,0.55)'; ctx.lineWidth = 1;
        for (let i = 0; i < 35; i++) {
            const x=Math.random()*S, y=Math.random()*S;
            ctx.beginPath(); ctx.moveTo(x,y);
            ctx.lineTo(x+Math.random()*30-15, y+Math.random()*30-15);
            ctx.stroke();
        }
        // Küçük taş ve toprak parçaları
        for (let i = 0; i < 60; i++) {
            const v=40+Math.floor(Math.random()*30);
            ctx.fillStyle=`rgb(${v},${v-8},${v-18})`;
            ctx.beginPath();
            ctx.ellipse(Math.random()*S,Math.random()*S,2+Math.random()*5,1+Math.random()*3,Math.random()*Math.PI,0,Math.PI*2);
            ctx.fill();
        }
    }, 1, 1);
}

function getGroundTex(mapSize) {
    const sk = _seasonKey(HARMAN.season);
    let t, rep;
    if (sk === 'winter') {
        t = txSnowGnd();
        rep = Math.round(mapSize * 0.04);   // kar — büyük yumuşak tümsekler
    } else if (sk === 'spring') {
        t = txGrass();
        rep = Math.round(mapSize * 0.08);   // çimen — sık tekrar, doğal görünüm
    } else if (sk === 'autumn') {
        t = txAutumnGnd();
        rep = Math.round(mapSize * 0.06);   // kuru yapraklar — orta yoğunluk
    } else {
        t = txCobble();
        rep = Math.round(mapSize * 0.055);  // yaz kaldırımı — görünür taşlar
    }
    t.repeat.set(Math.max(6, rep), Math.max(6, rep));
    return t;
}

// ── YAPI MALZEME FABRİKASI (önbellekli) ──────────────────────────────────
function getBldMat(city, type, pal) {
    const k=`${city}__${type.slice(0,12)}__${pal.building_main}`;
    if(MATCACHE[k]) return MATCACHE[k];

    const isGlass    = ['office','commercial','retail','hotel','supermarket'].some(t=>type.includes(t));
    const isHistoric = ['church','cathedral','mosque','temple','chapel','shrine'].some(t=>type.includes(t));
    const isIndustry = ['industrial','warehouse','factory','storage'].some(t=>type.includes(t));

    // color:0xffffff — nötr çarpan, doku kendi rengini gösterir
    let mat;
    if(city==='Dubai' || ((city==='Tokyo'||city==='New York') && isGlass)) {
        mat = new THREE.MeshStandardMaterial({map:txGlass(pal.building_alt),color:0xffffff,metalness:.68,roughness:.15});
    } else if(city==='Tokyo' && !isGlass) {
        mat = new THREE.MeshStandardMaterial({map:txConcrete(pal.building_main),color:0xffffff,metalness:.30,roughness:.60});
    } else if(city==='Paris') {
        mat = new THREE.MeshStandardMaterial({map:txLimestone(pal.building_main),color:0xffffff,roughness:.84});
    } else if(city==='Istanbul' || city==='İstanbul') {
        mat = new THREE.MeshStandardMaterial({map: isHistoric ? txLimestone(pal.landmark) : txBrick(pal.building_main),color:0xffffff,roughness:.88});
    } else if(city==='Londra') {
        mat = new THREE.MeshStandardMaterial({map:txBrick(pal.building_alt,true),color:0xffffff,roughness:.91});
    } else if(city==='New York') {
        mat = type.includes('apart')||type.includes('resid')
            ? new THREE.MeshStandardMaterial({map:txBrick(pal.building_main),color:0xffffff,roughness:.88})
            : new THREE.MeshStandardMaterial({map:txConcrete(pal.building_main),color:0xffffff,metalness:.28,roughness:.72});
    } else if(isGlass) {
        mat = new THREE.MeshStandardMaterial({map:txGlass(pal.building_main),color:0xffffff,metalness:.65,roughness:.18});
    } else if(isIndustry) {
        mat = new THREE.MeshStandardMaterial({map:txConcrete(pal.roof),color:0xffffff,roughness:.92});
    } else {
        mat = new THREE.MeshStandardMaterial({map:txConcrete(pal.building_main),color:0xffffff,roughness:.82});
    }
    MATCACHE[k]=mat;
    return mat;
}

// ── Yol materyali fabrikası ────────────────────────────────────────────────
function getRoadMat(type) {
    const k = 'road_' + type;
    if (MATCACHE[k]) return MATCACHE[k];
    const t = txAsphalt(); t.repeat.set(1, 1);
    const m = new THREE.MeshStandardMaterial({map: t, roughness: .96, metalness: 0});
    MATCACHE[k] = m;
    return m;
}

// ═══════════════════════════════════════════════════════════════════════════
// SPRINT 3 — AĞAÇ JENERATÖRÜ
// 6 şehir tipi × 4 mevsim: kış=çıplak dal, yaz=yapraklı öbek, ilkbahar=çiçek
// ═══════════════════════════════════════════════════════════════════════════

function createTree(px, pz, city) {
    const g  = new THREE.Group();
    const sk = _seasonKey(HARMAN.season);
    const ck = _cityKey(city);
    const leafCol = new THREE.Color(
        (TREE_COLORS[ck] || TREE_COLORS['Londra'])[sk] || '#2a7830'
    );
    const isWinter = sk === 'winter' && ck !== 'Dubai';
    const sc = 0.78 + Math.random() * 0.52;
    const trunkH = (2.0 + Math.random() * 1.6) * sc;

    // Gövde
    const trunk = new THREE.Mesh(
        new THREE.CylinderGeometry(0.10*sc, 0.20*sc, trunkH, 7),
        new THREE.MeshStandardMaterial({color:0x5c3a1e, roughness:.96})
    );
    trunk.position.y = trunkH / 2;
    trunk.castShadow = true;
    g.add(trunk);

    const leafMat = new THREE.MeshStandardMaterial({color:leafCol, roughness:.88});

    if (!isWinter) {
        if (ck === 'Istanbul') {
            // Selvi — ince koni
            const cone = new THREE.Mesh(
                new THREE.ConeGeometry(0.65*sc, 5.2*sc, 8), leafMat);
            cone.position.y = trunkH + 2.6*sc;
            cone.castShadow = true;
            g.add(cone);
        } else if (ck === 'Dubai') {
            // Palmiye — fan yapraklar
            for (let i = 0; i < 6; i++) {
                const a = (i/6)*Math.PI*2;
                const fr = new THREE.Mesh(
                    new THREE.ConeGeometry(0.12*sc, 2.0*sc, 4),
                    new THREE.MeshStandardMaterial({color:0x2a6a18, roughness:.85})
                );
                fr.position.set(Math.cos(a)*0.35*sc, trunkH+0.5, Math.sin(a)*0.35*sc);
                fr.rotation.z = Math.cos(a)*0.7;
                fr.rotation.x = Math.sin(a)*0.7;
                g.add(fr);
            }
        } else {
            // Geniş taçlı ağaç — 3 küre öbek
            const offsets = [
                [0,        trunkH+1.65*sc, 0,         1.52*sc],
                [-0.70*sc, trunkH+1.05*sc, 0.20*sc,  1.00*sc],
                [ 0.70*sc, trunkH+1.05*sc,-0.20*sc,  0.96*sc],
            ];
            for (const [ox,oy,oz,r] of offsets) {
                const s = new THREE.Mesh(
                    new THREE.SphereGeometry(r, 7, 6), leafMat);
                s.position.set(ox, oy, oz);
                s.castShadow = true;
                g.add(s);
            }
        }
    } else {
        // Kış — çıplak dal
        const brMat = new THREE.MeshStandardMaterial({color:0x2a1a0a, roughness:.96});
        for (let i = 0; i < 5; i++) {
            const a = (i/5)*Math.PI*2;
            const br = new THREE.Mesh(
                new THREE.CylinderGeometry(0.03*sc, 0.07*sc, 1.5*sc, 5), brMat);
            br.position.set(
                Math.cos(a)*0.26*sc, (trunkH+0.75)*sc, Math.sin(a)*0.26*sc);
            br.rotation.z = Math.cos(a)*0.65;
            br.rotation.x = Math.sin(a)*0.65;
            g.add(br);
        }
    }

    g.position.set(px, 0, pz);
    g.rotation.y = Math.random() * Math.PI * 2;
    scene.add(g);
}

// ═══════════════════════════════════════════════════════════════════════════
// SPRINT 3 — NEHİR (CatmullRom şerit + animasyonlu su)
// ═══════════════════════════════════════════════════════════════════════════

function createRiver(mapSize, season) {
    const sk = _seasonKey(season);
    const waterHex = sk === 'winter' ? 0x1e3a50 : 0x0a3060;  // koyu, yüksek kontrast

    // Kıvrımlı nehir yolu — haritanın tam ortasından geçir
    const pts = [];
    for (let i = 0; i <= 9; i++) {
        const t = i / 9;
        // Genlik azaltıldı + faz kaydırıldı → nehir oyuncunun ÖNÜNDEN geçiyor
        pts.push(new THREE.Vector3(
            Math.sin(t * Math.PI * 1.8) * mapSize * 0.20,
            0.15,
            (t - 0.5) * mapSize * 1.75
        ));
    }
    const curve = new THREE.CatmullRomCurve3(pts);

    // Ribbon geometrisi — DoubleSide ile her açıdan görünür
    const NUM = 90, W = 14;  // daha geniş = daha görünür
    const vArr = [], uvArr = [], idx = [];
    for (let i = 0; i <= NUM; i++) {
        const t  = i / NUM;
        const pt = curve.getPoint(t);
        const tn = curve.getTangent(t);
        // XZ düzleminde dik vektör
        const rx = tn.z, rz = -tn.x;
        const len = Math.sqrt(rx*rx + rz*rz) || 1;
        const nx = rx/len * W/2, nz = rz/len * W/2;
        vArr.push(pt.x-nx, 0.15, pt.z-nz,
                  pt.x+nx, 0.15, pt.z+nz);
        uvArr.push(0, t*10, 1, t*10);
        if (i < NUM) {
            const b = i*2;
            // Her iki winding — DoubleSide + explicit her iki yüz
            idx.push(b,b+2,b+1, b+1,b+2,b+3);
        }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(vArr), 3));
    geo.setAttribute('uv',       new THREE.BufferAttribute(new Float32Array(uvArr), 2));
    geo.setIndex(idx);
    geo.computeVertexNormals();

    // Saf su materyali — canvas texture yok, metalness/roughness ile yansıma
    const waterMat = new THREE.MeshStandardMaterial({
        color:       waterHex,
        metalness:   0.45,
        roughness:   0.04,
        transparent: true,
        opacity:     0.88,
        side:        THREE.DoubleSide,
    });
    scene.add(new THREE.Mesh(geo, waterMat));
    return waterMat;
}

// ── SCENE ────────────────────────────────────────────────────────────────────
const scene = new THREE.Scene();
scene.background = new THREE.Color(SC.skyBot);
// Doğrusal sis: yakın nesneler net, uzak nesneler soluklaşır — AC tarzı atmosfer
const _fogC = new THREE.Color(SC.fogHex);
_fogC.multiplyScalar(0.50);
const _fogNear = HARMAN.mapSize * 0.55;
const _fogFar  = HARMAN.mapSize * 1.90 * SC.fogMult;
scene.fog = new THREE.Fog(_fogC, _fogNear, _fogFar);

const W = 1280, H = 520;
const camera   = new THREE.PerspectiveCamera(60, W/H, 0.1, 2500);
const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setSize(W, H);
renderer.shadowMap.enabled  = true;
renderer.shadowMap.type     = THREE.PCFSoftShadowMap;
renderer.toneMapping         = THREE.ReinhardToneMapping;   // ACESFilmic doku detayını yutuyordu
renderer.toneMappingExposure = SC.exposure * 0.82;
document.body.appendChild(renderer.domElement);

// ── SKY SPHERE (gradient) ─────────────────────────────────────────────────
(function buildSky(){
    const gc = document.createElement('canvas');
    gc.width = 1; gc.height = 512;
    const gx = gc.getContext('2d');
    const gg = gx.createLinearGradient(0,0,0,512);
    gg.addColorStop(0,   SC.skyTop);
    gg.addColorStop(0.45,SC.skyMid);
    gg.addColorStop(1,   SC.skyBot);
    gx.fillStyle=gg; gx.fillRect(0,0,1,512);
    const st = new THREE.CanvasTexture(gc);
    const sg = new THREE.SphereGeometry(900,24,12);
    sg.scale(-1,1,1);
    scene.add(new THREE.Mesh(sg,
        new THREE.MeshBasicMaterial({map:st,side:THREE.BackSide,depthWrite:false})));
})();

// ── SUN DISK (görsel) ──────────────────────────────────────────────────────
if (HARMAN.showSunDisk) {
    const sdMat = new THREE.SpriteMaterial({
        color: new THREE.Color(SC.sunColor),
        transparent:true, opacity:0.85, depthWrite:false,
        blending:THREE.AdditiveBlending,
    });
    const sd = new THREE.Sprite(sdMat);
    const sp = SC.sunPos;
    sd.position.set(sp[0]*6, sp[1]*6, -sp[2]*5);
    sd.scale.set(140, 140, 1);
    scene.add(sd);
    // Glow halo
    const glMat = new THREE.SpriteMaterial({
        color: new THREE.Color(SC.sunColor),
        transparent:true, opacity:0.20, depthWrite:false,
        blending:THREE.AdditiveBlending,
    });
    const gl = new THREE.Sprite(glMat);
    gl.position.copy(sd.position);
    gl.scale.set(320, 320, 1);
    scene.add(gl);
}

// ── LIGHTS — Düşük ambient = koyu gölgeler, güçlü güneş = doku detayı ────
scene.add(new THREE.AmbientLight(0xffffff, 0.10));   // çok düşük — gölgeler koyu kalır
const sun = new THREE.DirectionalLight(SC.sunColor, SC.sunInt * 1.25);
sun.position.set(...SC.sunPos);
sun.castShadow = true;
sun.shadow.mapSize.setScalar(2048);
sun.shadow.camera.near   = 1;
sun.shadow.camera.far    = 500;
sun.shadow.camera.left   = -HARMAN.mapSize;
sun.shadow.camera.right  =  HARMAN.mapSize;
sun.shadow.camera.top    =  HARMAN.mapSize;
sun.shadow.camera.bottom = -HARMAN.mapSize;
sun.shadow.bias = -0.0003;
scene.add(sun);
// Hafif dolgu ışığı — gölgelerde detay kalsın
scene.add(new THREE.HemisphereLight(SC.hemSky, SC.hemGnd, SC.hemInt * 0.15));
const fill = new THREE.DirectionalLight(SC.fillColor, SC.fillInt * 0.40);
fill.position.set(-60,40,-80);
scene.add(fill);

// ═══════════════════════════════════════════════════════════════════════════
// PHASE 3 — TERRAIN
// Multi-octave sin/cos noise; no external lib needed.
// ═══════════════════════════════════════════════════════════════════════════
function applyTerrain(geo, cfg) {
    if (!cfg.enabled) return;
    const pos = geo.attributes.position;
    const {amplitude:amp, frequency:freq} = cfg;
    for (let i = 0; i < pos.count; i++) {
        const x = pos.getX(i), z = pos.getZ(i);
        const h = amp * (
            Math.sin(x*freq)          * Math.cos(z*freq*1.30)         * 1.00 +
            Math.sin(x*freq*2.2+1.8)  * Math.cos(z*freq*1.9 +0.70)   * 0.38 +
            Math.sin(x*freq*4.1+2.3)  * Math.cos(z*freq*3.7 +1.40)   * 0.18 +
            Math.sin(x*freq*8.3+3.5)  * Math.cos(z*freq*7.1 +2.20)   * 0.08
        );
        pos.setY(i, Math.max(-0.8, h));
    }
    pos.needsUpdate = true;
    geo.computeVertexNormals();
}

// Ground — create with terrain if enabled
const gndGeo = HARMAN.showTerrain && HARMAN.terrain.enabled
    ? (() => {
        const g = new THREE.PlaneGeometry(HARMAN.mapSize*2.4, HARMAN.mapSize*2.4, 90, 90);
        applyTerrain(g, HARMAN.terrain);
        return g;
      })()
    : new THREE.PlaneGeometry(HARMAN.mapSize*2.4, HARMAN.mapSize*2.4);

// Zemin: mevsime göre solid renk — canvas doku yerine güvenilir yöntem
// Zemin mevsim renk paleti (MeshBasicMaterial → ışıktan bağımsız, her zaman görünür)
function _gndBaseColor() {
    const sk = _seasonKey(HARMAN.season);
    if (sk === 'winter')  return 0xd0dde5;   // karlı beyaz-gri
    if (sk === 'spring')  return 0x3a5225;   // parlak yeşil
    if (sk === 'autumn')  return 0x5a3a18;   // kuru yaprak kahvesi
    return 0x2e2d28;                          // yaz — koyu gri asfalt/kaldırım
}

const gndTex = getGroundTex(HARMAN.mapSize);

// MeshBasicMaterial: ışıktan bağımsız. color=0xffffff → doku tam parlaklıkta
// Eski: color*texture çarpımı ≈ siyah → fog rengi görünüyordu (floating hissi)
const gndMat = new THREE.MeshBasicMaterial({
    map:   gndTex,
    color: 0xffffff,   // nötr — cobblestone taşları kendi gri renginde görünür
});

const gnd      = new THREE.Mesh(gndGeo, gndMat);
gnd.rotation.x = -Math.PI/2;
scene.add(gnd);

// Zemin üstüne ince shadow catcher — binaların gölgeleri zeminde görünsün
const shadowMat = new THREE.ShadowMaterial({ opacity: 0.28 });
const shadowGnd = new THREE.Mesh(
    new THREE.PlaneGeometry(HARMAN.mapSize*2.4, HARMAN.mapSize*2.4),
    shadowMat
);
shadowGnd.rotation.x = -Math.PI/2;
shadowGnd.position.y  = 0.01;
shadowGnd.receiveShadow = true;
scene.add(shadowGnd);

// GridHelper kaldırıldı — zemin kılavuz çizgileri "test sahnesi" hissi veriyordu

// ── KAR PARÇACIKLARİ (Kış mevsimine özel) ────────────────────────────────
let snowPts = null;
if (SC.snow && HARMAN.snowDensity > 0) {
    const COUNT = HARMAN.snowDensity;
    const snowGeo = new THREE.BufferGeometry();
    const pos = new Float32Array(COUNT * 3);
    const half = HARMAN.mapSize * 1.1;
    for (let i = 0; i < COUNT; i++) {
        pos[i*3]   = (Math.random()-0.5) * half * 2;
        pos[i*3+1] = Math.random() * 65;
        pos[i*3+2] = (Math.random()-0.5) * half * 2;
    }
    snowGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    snowPts = new THREE.Points(snowGeo,
        new THREE.PointsMaterial({
            color:0xeef4ff, size:0.28,
            transparent:true, opacity:0.82,
            depthWrite:false,
            blending:THREE.NormalBlending,
        })
    );
    scene.add(snowPts);
}

// ═══════════════════════════════════════════════════════════════════════════
// PHASE 3 — ZONE OVERLAYS
// ═══════════════════════════════════════════════════════════════════════════
const PALS = {};
for (const c of HARMAN.cities) PALS[c.name] = c.palette;

if (HARMAN.showZones && HARMAN.zones.length > 0) {
    for (const zone of HARMAN.zones) {
        const pal = PALS[zone.city];
        if (!pal) continue;

        // Subtle ground tint matching city ground colour
        const tintMat = new THREE.MeshStandardMaterial({
            color:C(pal.ground), transparent:true, opacity:.20,
            roughness:1.0, depthWrite:false
        });
        const tint = new THREE.Mesh(new THREE.CircleGeometry(zone.radius, 52), tintMat);
        tint.rotation.x = -Math.PI/2;
        tint.position.set(zone.cx, 0.008, zone.cz);
        scene.add(tint);

        // Neon border ring
        const ringMat = new THREE.MeshBasicMaterial({
            color:C(pal.neon), transparent:true, opacity:.18,
            side:THREE.DoubleSide, depthWrite:false
        });
        const ring = new THREE.Mesh(
            new THREE.RingGeometry(zone.radius-.55, zone.radius+.55, 64), ringMat
        );
        ring.rotation.x = -Math.PI/2;
        ring.position.set(zone.cx, 0.012, zone.cz);
        scene.add(ring);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PHASE 3 — STREET NETWORK
// ═══════════════════════════════════════════════════════════════════════════
if (HARMAN.showStreets && HARMAN.streets.length > 0) {
    // Sprint 2: textured road materials (önbellekli)
    const roadMats = {
        motorway:    getRoadMat('motorway'),
        trunk:       getRoadMat('trunk'),
        primary:     getRoadMat('primary'),
        secondary:   getRoadMat('secondary'),
        tertiary:    getRoadMat('tertiary'),
        residential: getRoadMat('residential'),
        _def:        getRoadMat('default'),
    };

    let segCount = 0;
    const SEG_LIMIT = 2800;

    for (const st of HARMAN.streets) {
        if (segCount >= SEG_LIMIT) break;
        const mat  = roadMats[st.type] || roadMats._def;
        const path = st.path;

        for (let i = 0; i < path.length-1 && segCount < SEG_LIMIT; i++) {
            const [x1,z1] = path[i], [x2,z2] = path[i+1];
            const dx = x2-x1, dz = z2-z1;
            const len = Math.sqrt(dx*dx + dz*dz);
            if (len < 0.15 || len > 90) continue;

            const seg = new THREE.Mesh(new THREE.BoxGeometry(st.width, 0.06, len), mat);
            seg.position.set((x1+x2)/2, 0.03, (z1+z2)/2);
            seg.rotation.y = Math.atan2(dx, dz);
            seg.receiveShadow = true;
            scene.add(seg);
            segCount++;
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PHASE 2 — OSM BUILDING RENDERER
// ═══════════════════════════════════════════════════════════════════════════
function createOSMBuilding(b) {
    const g   = new THREE.Group();
    const pal = PALS[b.city] || PALS[HARMAN.cities[0].name];

    // Sprint 2: procedural texture material (önbellekli)
    // Not: isHistoric/isGlass/isIndustry switch bloğu için de gerekli
    const isGlass    = ['office','commercial','retail','hotel','supermarket'].some(t=>b.type.includes(t)) || b.city==='Dubai';
    const isHistoric = ['church','cathedral','mosque','temple','chapel','shrine'].some(t=>b.type.includes(t));
    const mat = getBldMat(b.city, b.type, pal);
    const box = new THREE.Mesh(new THREE.BoxGeometry(b.w,b.h,b.d), mat);
    box.position.y=b.h/2; box.castShadow=true; box.receiveShadow=true;
    g.add(box);

    switch(b.city) {
        case 'Tokyo':
            if(b.h>8  && Math.random()>.42) _neonSign(g,b.w,b.h,b.d,pal);
            if(b.h>14 && Math.random()>.60) _rooftopUnit(g,b.w,b.h,b.d,pal);
            if(b.h>20 && Math.random()>.65) _ledStrip(g,b.w,b.h,b.d,pal);
            break;
        case 'İstanbul':
            if(isHistoric)                           _dome(g,b.w,b.h,b.d,pal);
            else if(b.h<10 && Math.random()>.50)     _pointedRoof(g,b.w,b.h,b.d,pal);
            break;
        case 'Paris':
            if(b.h<15) _mansard(g,b.w,b.h,b.d,pal);
            _cornice(g,b.w,b.h,b.d,pal);
            break;
        case 'New York':
            if(b.h>22 && Math.random()>.50) _waterTower(g,b.w,b.h,b.d);
            if(b.h>28)                      _setback(g,b.w,b.h,b.d,mat);
            break;
        case 'Dubai':
            _goldTrim(g,b.w,b.h,b.d,pal);
            if(b.h>25) _glassFin(g,b.w,b.h,b.d,pal);
            break;
        case 'Londra':
            if(Math.random()>.48) _chimneys(g,b.w,b.h,b.d);
            break;
    }
    g.position.set(b.x,0,b.z);
    g.rotation.y=(Math.random()-.5)*.22;
    scene.add(g);
    addCollider(g);   // Sprint 4
}

// Detail helpers
function _neonSign(g,w,h,d,p){const m=new THREE.MeshStandardMaterial({color:C(p.neon),emissive:C(p.neon),emissiveIntensity:1.5});const s=new THREE.Mesh(new THREE.BoxGeometry(w*.65,.62,.12),m);s.position.set(0,1.5+Math.random()*(h-3),d/2+.07);g.add(s);}
function _ledStrip(g,w,h,d,p){const m=new THREE.MeshStandardMaterial({color:C(p.building_alt),emissive:C(p.building_alt),emissiveIntensity:.9});const s=new THREE.Mesh(new THREE.BoxGeometry(.12,h*.55,.12),m);s.position.set(w/2+.07,h*.28,0);g.add(s);}
function _rooftopUnit(g,w,h,d,p){const m=new THREE.MeshStandardMaterial({color:C(p.roof)});const r=new THREE.Mesh(new THREE.BoxGeometry(w*.38,1.1,d*.38),m);r.position.y=h+.55;g.add(r);}
function _dome(g,w,h,d,p){const m=new THREE.MeshStandardMaterial({color:C(p.landmark),metalness:.28,roughness:.5});const r=Math.min(w,d)*.42;const dome=new THREE.Mesh(new THREE.SphereGeometry(r,14,10,0,Math.PI*2,0,Math.PI/2),m);dome.position.y=h;g.add(dome);}
function _pointedRoof(g,w,h,d,p){const m=new THREE.MeshStandardMaterial({color:C(p.roof),roughness:.85});const r=new THREE.Mesh(new THREE.CylinderGeometry(0,Math.min(w,d)*.52,h*.22,4),m);r.position.y=h+h*.11;r.rotation.y=Math.PI/4;g.add(r);}
function _mansard(g,w,h,d,p){const m=new THREE.MeshStandardMaterial({color:C(p.roof),metalness:.25});const r=new THREE.Mesh(new THREE.CylinderGeometry(0,w*.56,h*.20,4),m);r.position.y=h+h*.10;r.rotation.y=Math.PI/4;g.add(r);}
function _cornice(g,w,h,d,p){const m=new THREE.MeshStandardMaterial({color:C(p.building_alt)});const c=new THREE.Mesh(new THREE.BoxGeometry(w+.28,.20,d+.28),m);c.position.y=h;g.add(c);}
function _waterTower(g,w,h,d){const wm=new THREE.MeshStandardMaterial({color:0x8b6914}),rm=new THREE.MeshStandardMaterial({color:0x555555});const bx=(Math.random()-.5)*w*.55,bz=(Math.random()-.5)*d*.55;const tk=new THREE.Mesh(new THREE.CylinderGeometry(.6,.6,1.4,8),wm);tk.position.set(bx,h+1.4,bz);const rp=new THREE.Mesh(new THREE.ConeGeometry(.68,.85,8),rm);rp.position.set(bx,h+2.6,bz);g.add(tk,rp);}
function _setback(g,w,h,d,mat){const b2=new THREE.Mesh(new THREE.BoxGeometry(w*.7,h*.32,d*.7),mat);b2.position.y=h+h*.16;g.add(b2);}
function _goldTrim(g,w,h,d,p){const m=new THREE.MeshStandardMaterial({color:C(p.landmark),metalness:.85,roughness:.14});const t=new THREE.Mesh(new THREE.BoxGeometry(w+.14,.16,d+.14),m);t.position.y=h;const b=new THREE.Mesh(new THREE.BoxGeometry(w+.20,.32,d+.20),m);b.position.y=.16;g.add(t,b);}
function _glassFin(g,w,h,d,p){const m=new THREE.MeshStandardMaterial({color:C(p.building_main),metalness:.9,roughness:.05});const f=new THREE.Mesh(new THREE.BoxGeometry(.14,h*.6,d*.9),m);f.position.set(w/2+.08,h*.2,0);g.add(f);}
function _chimneys(g,w,h,d){const m=new THREE.MeshStandardMaterial({color:0x444444});for(let i=0;i<2;i++){const ch=new THREE.Mesh(new THREE.CylinderGeometry(.13,.17,1.3),m);ch.position.set((i-.5)*w*.48,h+.65,(Math.random()-.5)*d*.4);g.add(ch);}}

// ═══════════════════════════════════════════════════════════════════════════
// PHASE 1 — PROCEDURAL BUILDERS (fallback)
// ═══════════════════════════════════════════════════════════════════════════
function buildTokyo(x,z,pal){const g=new THREE.Group(),h=3+Math.random()*35,w=1.2+Math.random()*2.2;const m=h>12?new THREE.MeshStandardMaterial({map:txGlass(pal.building_alt),metalness:.6,roughness:.18}):new THREE.MeshStandardMaterial({map:txConcrete(pal.building_main),metalness:.3,roughness:.6});const bld=new THREE.Mesh(new THREE.BoxGeometry(w,h,w),m);bld.position.y=h/2;bld.castShadow=true;g.add(bld);if(Math.random()>.45)_neonSign(g,w,h,w,pal);const rm=new THREE.MeshStandardMaterial({color:C(pal.roof)});const rt=new THREE.Mesh(new THREE.BoxGeometry(w*.5,1,w*.5),rm);rt.position.y=h+.5;g.add(rt);g.position.set(x,0,z);scene.add(g);addCollider(g);}
function buildIstanbul(x,z,pal){const g=new THREE.Group(),t=Math.random();const sm=new THREE.MeshStandardMaterial({map:txBrick(pal.building_main),roughness:.88});const dm=new THREE.MeshStandardMaterial({map:txLimestone(pal.landmark),roughness:.5,metalness:.2});if(t>.72){const sh=new THREE.Mesh(new THREE.CylinderGeometry(.28,.38,11,10),sm);sh.position.y=5.5;const bl=new THREE.Mesh(new THREE.CylinderGeometry(.65,.65,.35,12),sm);bl.position.y=8.5;const cp=new THREE.Mesh(new THREE.ConeGeometry(.55,2.8,10),dm);cp.position.y=12.4;g.add(sh,bl,cp);}else if(t>.35){const bh=2.5+Math.random()*5,bw=3+Math.random()*2.5;const base=new THREE.Mesh(new THREE.BoxGeometry(bw,bh,bw*.85),sm);base.position.y=bh/2;base.castShadow=true;const dome=new THREE.Mesh(new THREE.SphereGeometry(bw*.48,14,10,0,Math.PI*2,0,Math.PI/2),dm);dome.position.y=bh;g.add(base,dome);}else{const bh=2.5+Math.random()*4.5,bw=2.8+Math.random()*2;const bld=new THREE.Mesh(new THREE.BoxGeometry(bw,bh,2.8),sm);bld.position.y=bh/2;bld.castShadow=true;const rf=new THREE.Mesh(new THREE.CylinderGeometry(0,bw*.65,bh*.3,4),new THREE.MeshStandardMaterial({color:C(pal.roof)}));rf.position.y=bh+bh*.15;rf.rotation.y=Math.PI/4;g.add(bld,rf);}g.position.set(x,0,z);scene.add(g);addCollider(g);}
function buildParis(x,z,pal){const g=new THREE.Group(),floors=5+Math.floor(Math.random()*3),h=floors*1.25,w=3.8+Math.random()*2;const bld=new THREE.Mesh(new THREE.BoxGeometry(w,h,w*.72),new THREE.MeshStandardMaterial({map:txLimestone(pal.building_main),roughness:.82}));bld.position.y=h/2;bld.castShadow=true;const msd=new THREE.Mesh(new THREE.CylinderGeometry(0,w*.62,h*.22,4),new THREE.MeshStandardMaterial({color:C(pal.roof),metalness:.3}));msd.position.y=h+h*.11;msd.rotation.y=Math.PI/4;const cor=new THREE.Mesh(new THREE.BoxGeometry(w+.28,.22,w*.72+.28),new THREE.MeshStandardMaterial({color:C(pal.building_alt)}));cor.position.y=h;g.add(bld,msd,cor);g.position.set(x,0,z);scene.add(g);addCollider(g);}
function buildNewYork(x,z,pal){const g=new THREE.Group(),t=Math.random();const cm=new THREE.MeshStandardMaterial({map:txConcrete(pal.building_main),metalness:.28,roughness:.70});if(t>.55){const bw=4+Math.random()*3.5,bh=8+Math.random()*20;let y=0;for(const[sw,sh]of[[bw,bh],[bw*.72,bh*.48],[bw*.45,bh*.28],[bw*.28,bh*.18]]){const b=new THREE.Mesh(new THREE.BoxGeometry(sw,sh,sw),cm);b.position.y=y+sh/2;b.castShadow=true;g.add(b);y+=sh;}const sp=new THREE.Mesh(new THREE.CylinderGeometry(.08,.22,bh*.28),new THREE.MeshStandardMaterial({color:0xbbbbbb,metalness:.9}));sp.position.y=y+bh*.14;g.add(sp);}else if(t>.28){const h=18+Math.random()*55,w=1.8+Math.random()*2.5;const b=new THREE.Mesh(new THREE.BoxGeometry(w,h,w),new THREE.MeshStandardMaterial({color:C(pal.building_alt),metalness:.7,roughness:.15}));b.position.y=h/2;b.castShadow=true;g.add(b);}else{const h=4.5+Math.random()*3,w=5+Math.random();const b=new THREE.Mesh(new THREE.BoxGeometry(w,h,3.8),new THREE.MeshStandardMaterial({color:0x7a3b1e}));b.position.y=h/2;b.castShadow=true;g.add(b);}g.position.set(x,0,z);scene.add(g);addCollider(g);}
function buildDubai(x,z,pal){const g=new THREE.Group(),t=Math.random();const gm=new THREE.MeshStandardMaterial({map:txGlass(pal.building_main),metalness:.90,roughness:.05});if(t>.48){const h=28+Math.random()*85,w=1.8+Math.random()*1.5;const b=new THREE.Mesh(new THREE.BoxGeometry(w,h,w),gm);b.position.y=h/2;b.castShadow=true;const cp=new THREE.Mesh(new THREE.CylinderGeometry(0,w*.55,h*.12,4),gm);cp.position.y=h+h*.06;g.add(b,cp);}else if(t>.22){const h=22+Math.random()*60;const b=new THREE.Mesh(new THREE.CylinderGeometry(.6,2.5,h,8),gm);b.position.y=h/2;b.castShadow=true;g.add(b);}else{const h=2.8+Math.random()*2;const b=new THREE.Mesh(new THREE.BoxGeometry(6.5,h,5.5),new THREE.MeshStandardMaterial({color:0xf5f0e0,roughness:.7}));b.position.y=h/2;b.castShadow=true;const rf=new THREE.Mesh(new THREE.BoxGeometry(7,.28,6),new THREE.MeshStandardMaterial({color:C(pal.landmark),metalness:.5}));rf.position.y=h+.14;g.add(b,rf);}g.position.set(x,0,z);scene.add(g);addCollider(g);}
function buildLondra(x,z,pal){const g=new THREE.Group(),t=Math.random();if(t>.65){const h=14+Math.random()*32;const b=new THREE.Mesh(new THREE.CylinderGeometry(.25,2.2,h,4),new THREE.MeshStandardMaterial({map:txGlass(pal.building_alt),metalness:.65,roughness:.12}));b.position.y=h/2;b.castShadow=true;g.add(b);}else{const h=4+Math.random()*5.5,w=4+Math.random()*2;const b=new THREE.Mesh(new THREE.BoxGeometry(w,h,3.5),new THREE.MeshStandardMaterial({map:txBrick(pal.building_main,true),roughness:.91}));b.position.y=h/2;b.castShadow=true;const cm=new THREE.MeshStandardMaterial({color:0x444444});for(let i=0;i<2;i++){const ch=new THREE.Mesh(new THREE.CylinderGeometry(.14,.18,1.4),cm);ch.position.set((i-.5)*.9,h+.7,0);g.add(ch);}g.add(b);}g.position.set(x,0,z);scene.add(g);addCollider(g);}
const BUILDERS={Tokyo:buildTokyo,"İstanbul":buildIstanbul,Paris:buildParis,"New York":buildNewYork,Dubai:buildDubai,Londra:buildLondra};

// ── BUILDING DISPATCH ─────────────────────────────────────────────────────────
if (HARMAN.useOSM && HARMAN.buildings.length > 0) {
    for (const b of HARMAN.buildings) createOSMBuilding(b);
} else {
    const half = HARMAN.mapSize;
    for (let i = 0; i < HARMAN.density; i++) {
        const city = pickCity(), builder = BUILDERS[city.name];
        if (!builder) continue;
        let x=(Math.random()-.5)*half*1.8, z=(Math.random()-.5)*half*1.8;
        if(Math.abs(x)<10&&Math.abs(z)<10) x+=18;
        builder(x, z, city.palette);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PHASE 4 — DATA-DRIVEN LANDMARK SYSTEM + SPONSOR BILLBOARDS + RADAR
// ═══════════════════════════════════════════════════════════════════════════

const landmarkObjects = [];   // for animation + proximity checks

// ── Type-specific 3D models ───────────────────────────────────────────────
function _lmTower(g, pal, h) {
    const m = new THREE.MeshStandardMaterial({color:C3(pal.landmark),metalness:.5});
    const tw = new THREE.Mesh(new THREE.CylinderGeometry(.3,h*.12,h,8),m); tw.position.y=h/2; g.add(tw);
    const dk = new THREE.Mesh(new THREE.CylinderGeometry(h*.18,h*.18,1.4,8),m); dk.position.y=h*.6; g.add(dk);
    const sp = new THREE.Mesh(new THREE.CylinderGeometry(.06,.06,h*.28),new THREE.MeshStandardMaterial({color:0xffffff,metalness:.9})); sp.position.y=h+h*.14; g.add(sp);
}
function _lmReligious(g, pal, h) {
    const sm = new THREE.MeshStandardMaterial({color:C3(pal.building_main),roughness:.85});
    const dm = new THREE.MeshStandardMaterial({color:C3(pal.landmark),metalness:.25});
    const base = new THREE.Mesh(new THREE.BoxGeometry(h*.8,h*.5,h*.65),sm); base.position.y=h*.25; g.add(base);
    const dome = new THREE.Mesh(new THREE.SphereGeometry(h*.32,14,10,0,Math.PI*2,0,Math.PI/2),dm); dome.position.y=h*.5; g.add(dome);
    const minH = h*.9;
    for(const[mx,mz]of[[h*.45,h*.45],[-h*.45,h*.45],[h*.45,-h*.45],[-h*.45,-h*.45]]){
        const sh=new THREE.Mesh(new THREE.CylinderGeometry(.28,.35,minH,8),sm); sh.position.set(mx,minH/2,mz);
        const cp=new THREE.Mesh(new THREE.ConeGeometry(.55,2.2,8),dm); cp.position.set(mx,minH+1.1,mz);
        g.add(sh,cp);
    }
}
function _lmCastle(g, pal, h) {
    const m = new THREE.MeshStandardMaterial({color:C3(pal.building_alt),roughness:.9});
    const base = new THREE.Mesh(new THREE.BoxGeometry(h*.8,h*.45,h*.65),m); base.position.y=h*.22; g.add(base);
    for(const[ox,oz]of[[h*.35,h*.28],[-h*.35,h*.28],[h*.35,-h*.28],[-h*.35,-h*.28]]){
        const tw=new THREE.Mesh(new THREE.CylinderGeometry(h*.1,h*.12,h,8),m); tw.position.set(ox,h/2,oz);
        const bt=new THREE.Mesh(new THREE.CylinderGeometry(h*.14,h*.14,.8,8),m); bt.position.set(ox,h+.4,oz);
        g.add(tw,bt);
    }
}
function _lmMonument(g, pal, h) {
    const m = new THREE.MeshStandardMaterial({color:C3(pal.landmark),metalness:.2,roughness:.8});
    const ob = new THREE.Mesh(new THREE.CylinderGeometry(.5,h*.15,h,4),m); ob.position.y=h/2; ob.rotation.y=Math.PI/4; g.add(ob);
    const base = new THREE.Mesh(new THREE.BoxGeometry(h*.3,h*.12,h*.3),m); base.position.y=h*.06; g.add(base);
}
function _lmMuseum(g, pal, h) {
    const m = new THREE.MeshStandardMaterial({color:C(pal.building_main),roughness:.85});
    const b = new THREE.Mesh(new THREE.BoxGeometry(h*.9,h*.55,h*.65),m); b.position.y=h*.27; g.add(b);
    const roof = new THREE.Mesh(new THREE.CylinderGeometry(0,h*.52,h*.22,4),m); roof.position.y=h*.55+h*.11; roof.rotation.y=Math.PI/4; g.add(roof);
    for(let i=0;i<4;i++){const cl=new THREE.Mesh(new THREE.CylinderGeometry(.18,.22,h*.55,8),m); cl.position.set((i-1.5)*h*.22,h*.27,h*.32+.1); g.add(cl);}
}
function _lmDefault(g, pal, h) {
    // Obelisk / anıt — genel landmark için evrensel form
    const stoneMat = new THREE.MeshStandardMaterial({color:C3(pal.building_main), roughness:.85});
    const accentMat= new THREE.MeshStandardMaterial({color:C3(pal.landmark), metalness:.35, roughness:.55});
    // Geniş kaide
    const base = new THREE.Mesh(new THREE.BoxGeometry(h*.55,h*.1,h*.55), stoneMat);
    base.position.y = h*.05; g.add(base);
    // Ana gövde (4 köşeli kule)
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(h*.09, h*.15, h*.72, 4), stoneMat);
    shaft.position.y = h*.41; shaft.rotation.y = Math.PI/4; g.add(shaft);
    // Piramit tepe
    const tip = new THREE.Mesh(new THREE.ConeGeometry(h*.1, h*.25, 4), accentMat);
    tip.position.y = h*.89; tip.rotation.y = Math.PI/4; g.add(tip);
}

// ── Sponsor billboard ─────────────────────────────────────────────────────
function _addSponsorBillboard(g, name, color, h) {
    const sc = new THREE.Color(color);
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(.12,.12,4.5),new THREE.MeshStandardMaterial({color:0x333333})); pole.position.y=h+2.5; g.add(pole);
    const back = new THREE.Mesh(new THREE.BoxGeometry(8,2.8,.35),new THREE.MeshStandardMaterial({color:0x0a0a14})); back.position.y=h+5.4; g.add(back);
    const bandMat = new THREE.MeshStandardMaterial({color:sc,emissive:sc,emissiveIntensity:.8});
    const band = new THREE.Mesh(new THREE.BoxGeometry(8.2,.45,.18),bandMat); band.position.set(0,h+4.05,.18); g.add(band);
    const topBand = new THREE.Mesh(new THREE.BoxGeometry(8.2,.45,.18),bandMat); topBand.position.set(0,h+6.75,.18); g.add(topBand);
    const light = new THREE.PointLight(color, 2.0, 35); light.position.y=h+5; g.add(light);
    // Ground glow ring
    const glowMat = new THREE.MeshBasicMaterial({color:sc,transparent:true,opacity:.18,side:THREE.DoubleSide,depthWrite:false});
    const glow = new THREE.Mesh(new THREE.CircleGeometry(6,32),glowMat); glow.rotation.x=-Math.PI/2; glow.position.y=.02; g.add(glow);
    g.userData.sponsorBand  = band;
    g.userData.sponsorBand2 = topBand;
    g.userData.sponsorLight = light;
    g.userData.sponsorColor = sc;
}

// ── Main landmark factory ─────────────────────────────────────────────────
function createGameLandmark(lm) {
    if (!HARMAN.showLandmarks) return;
    const g   = new THREE.Group();
    const pal = PALS[lm.city] || PALS[HARMAN.cities[0].name];
    const h   = lm.h || 12;

    switch(lm.type) {
        case 'tower':     _lmTower(g, pal, h);     break;
        case 'religious': _lmReligious(g, pal, h); break;
        case 'castle':    _lmCastle(g, pal, h);    break;
        case 'monument':  _lmMonument(g, pal, h);  break;
        case 'museum': case 'gallery': _lmMuseum(g, pal, h); break;
        default:          _lmDefault(g, pal, h);   break;
    }

    if (lm.sponsored && lm.sponsorName) {
        _addSponsorBillboard(g, lm.sponsorName, lm.sponsorColor, h);
    }

    g.position.set(lm.x, 0, lm.z);
    g.userData = lm;
    scene.add(g);
    addCollider(g, 0.8);   // landmark'lar için biraz daha geniş buffer
    landmarkObjects.push(g);
}

// ── Sprint 3: AĞAÇ & NEHİR — try/catch ile güvenli başlatma ────────────────
let riverMat = null;
try {
    if (HARMAN.treeCount > 0) {
        const half    = HARMAN.mapSize * 0.90;
        const spawn   = 12;
        const placed  = [];
        const MIN_SEP = 3.5;

        for (let i = 0; i < HARMAN.treeCount; i++) {
            let tx, tz, ok = false;
            for (let attempt = 0; attempt < 25; attempt++) {
                const rr  = half * (0.15 + Math.pow(Math.random(), 0.6) * 0.85);
                const ang = Math.random() * Math.PI * 2;
                tx = Math.cos(ang) * rr;
                tz = Math.sin(ang) * rr;
                if (Math.abs(tx) < spawn && Math.abs(tz) < spawn) continue;
                if (placed.every(p => Math.hypot(tx-p[0], tz-p[1]) > MIN_SEP)) {
                    ok = true; break;
                }
            }
            if (!ok) continue;
            placed.push([tx, tz]);
            createTree(tx, tz, cityForPos(tx, tz));
        }
    }

    if (HARMAN.showRiver) {
        riverMat = createRiver(HARMAN.mapSize, HARMAN.season);
    }
} catch(e) {
    console.error('Sprint3 init error:', e);
    const hud = document.getElementById('hud');
    if (hud) hud.innerHTML +=
        '<br><span style="color:orange;font-size:10px;">S3 err: ' + e.message + '</span>';
}

// Build landmarks from Phase 4 real data
if (HARMAN.landmarks && HARMAN.landmarks.length > 0) {
    for (const lm of HARMAN.landmarks) createGameLandmark(lm);
} else if (HARMAN.showLandmarks) {
    // Fallback: iconic placeholders per city
    let angle=0; const step=(Math.PI*2)/HARMAN.cities.length;
    for (const city of HARMAN.cities) {
        if(city.weight>0.08){
            const dist=28+(1-city.weight)*48;
            const fx=Math.cos(angle)*dist, fz=Math.sin(angle)*dist;
            const fakeLm={x:fx,z:fz,name:city.lm_name,type:'tower',city:city.name,h:28,sponsored:false};
            createGameLandmark(fakeLm);
        }
        angle+=step;
    }
}

// ── Landmark radar (canvas 2D) ────────────────────────────────────────────
const radarCanvas = document.getElementById('radar');
const rCtx = radarCanvas ? radarCanvas.getContext('2d') : null;

function drawRadar() {
    if (!rCtx) return;
    const S=80;
    rCtx.clearRect(0,0,S,S);
    // BG circle
    rCtx.beginPath(); rCtx.arc(S/2,S/2,S/2-2,0,Math.PI*2);
    rCtx.fillStyle='rgba(7,7,15,.88)'; rCtx.fill();
    rCtx.strokeStyle='#e94560'; rCtx.lineWidth=1; rCtx.stroke();
    // Player dot
    rCtx.beginPath(); rCtx.arc(S/2,S/2,4,0,Math.PI*2);
    rCtx.fillStyle='#e94560'; rCtx.fill();
    // Landmark dots
    for(const obj of landmarkObjects){
        const dx=obj.position.x-player.position.x;
        const dz=obj.position.z-player.position.z;
        const dist=Math.sqrt(dx*dx+dz*dz);
        if(dist>180) continue;
        const ang=Math.atan2(dx,dz)-playerAngle;
        const rd=Math.min(dist/180*(S/2-8),S/2-8);
        const rx=S/2+Math.sin(ang)*rd, ry=S/2-Math.cos(ang)*rd;
        rCtx.beginPath();
        rCtx.arc(rx,ry,obj.userData.sponsored?4.5:2.5,0,Math.PI*2);
        rCtx.fillStyle=obj.userData.sponsored?(obj.userData.sponsorColor||'#e94560'):'#888';
        rCtx.fill();
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// CHARACTER — varsayılan blok karakter (FBX yokken veya yüklenirken)
// ═══════════════════════════════════════════════════════════════════════════
const player=new THREE.Group();
const legMat=new THREE.MeshStandardMaterial({color:0x111111});
const leftLeg=new THREE.Mesh(new THREE.BoxGeometry(.22,.85,.22),legMat); leftLeg.position.set(-.2,.42,0);
const rightLeg=new THREE.Mesh(new THREE.BoxGeometry(.22,.85,.22),legMat); rightLeg.position.set(.2,.42,0);
const skirt=new THREE.Mesh(new THREE.BoxGeometry(.72,.42,.52),new THREE.MeshStandardMaterial({color:0x222222})); skirt.position.y=1.02;
const torso=new THREE.Mesh(new THREE.BoxGeometry(.62,.82,.42),new THREE.MeshStandardMaterial({color:0xe94560})); torso.position.y=1.65;
const armMat=new THREE.MeshStandardMaterial({color:0xe94560});
const leftArm=new THREE.Mesh(new THREE.BoxGeometry(.19,.72,.19),armMat); leftArm.position.set(-.46,1.65,0);
const rightArm=new THREE.Mesh(new THREE.BoxGeometry(.19,.72,.19),armMat); rightArm.position.set(.46,1.65,0);
const head=new THREE.Mesh(new THREE.BoxGeometry(.42,.42,.42),new THREE.MeshStandardMaterial({color:0xffdbac})); head.position.y=2.22;
const hairMat=new THREE.MeshStandardMaterial({color:0x00f3ff,roughness:.4});
const hairTop=new THREE.Mesh(new THREE.BoxGeometry(.50,.16,.50),hairMat); hairTop.position.set(0,2.42,0);
const hairBack=new THREE.Mesh(new THREE.BoxGeometry(.50,.42,.16),hairMat); hairBack.position.set(0,2.18,-.22);
player.add(leftLeg,rightLeg,skirt,torso,leftArm,rightArm,head,hairTop,hairBack);
scene.add(player);

// ═══════════════════════════════════════════════════════════════════════════
// FBX CHARACTER LOADER
// ═══════════════════════════════════════════════════════════════════════════
let fbxModel  = null;   // loaded FBX root
let mixer     = null;   // AnimationMixer
let walkClip  = null;   // walk/run action
let idleClip  = null;   // idle/stand action
let activeClip= null;   // currently playing clip
const clock   = new THREE.Clock();

function switchAnim(newClip) {
    if (!mixer || !newClip || activeClip === newClip) return;
    if (activeClip) { activeClip.fadeOut(0.2); }
    newClip.reset().fadeIn(0.2).play();
    activeClip = newClip;
}

function initFBXAnimations(fbx) {
    if (!fbx.animations || fbx.animations.length === 0) return;
    mixer = new THREE.AnimationMixer(fbx);
    for (const clip of fbx.animations) {
        const n = clip.name.toLowerCase();
        if (!idleClip && (n.includes('idle') || n.includes('stand') || n.includes('tpose'))) {
            idleClip = mixer.clipAction(clip);
        }
        if (!walkClip && (n.includes('walk') || n.includes('run') || n.includes('move'))) {
            walkClip = mixer.clipAction(clip);
        }
    }
    // Fallbacks: assign by index if names didn't match
    if (!idleClip) idleClip = mixer.clipAction(fbx.animations[0]);
    if (!walkClip && fbx.animations.length > 1) walkClip = mixer.clipAction(fbx.animations[1]);
    // Start idle
    if (idleClip) { idleClip.play(); activeClip = idleClip; }
}

if (HARMAN.fbxCharacter) {
    // Decode base64 → ArrayBuffer → Blob → ObjectURL
    const b64    = HARMAN.fbxCharacter;
    const binary = atob(b64);
    const bytes  = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const blob   = new Blob([bytes.buffer], {type:'application/octet-stream'});
    const objURL = URL.createObjectURL(blob);

    const loader = new THREE.FBXLoader();
    loader.load(
        objURL,
        (fbx) => {
            // ── Auto-scale: fit to TARGET_HEIGHT game units, then apply user multiplier ──
            const TARGET_HEIGHT = 2.2;   // approximate human height in game units
            fbx.scale.setScalar(1);      // reset before measuring
            const bbox0 = new THREE.Box3().setFromObject(fbx);
            const modelH = bbox0.getSize(new THREE.Vector3()).y;
            const autoScale = (modelH > 0.001) ? (TARGET_HEIGHT / modelH) : 0.01;
            fbx.scale.setScalar(autoScale * HARMAN.charScale);  // charScale = multiplier

            // ── Ground alignment: push feet to y = 0 ──
            const bbox1 = new THREE.Box3().setFromObject(fbx);
            fbx.position.y = -bbox1.min.y;

            // ── Spawn at player position ──
            fbx.position.x = player.position.x;
            fbx.position.z = player.position.z;
            fbx.rotation.copy(player.rotation);

            // ── Shadows ──
            fbx.traverse(child => {
                if (child.isMesh) { child.castShadow = true; child.receiveShadow = true; }
            });

            fbxModel = fbx;
            scene.add(fbxModel);
            player.visible = false;
            initFBXAnimations(fbx);
            URL.revokeObjectURL(objURL);

            const hud = document.getElementById('hud');
            if (hud) hud.style.borderColor = '#00d4ff';
            console.log(`FBX yüklendi — modelH:${modelH.toFixed(2)} autoScale:${autoScale.toFixed(4)} final:${(autoScale*HARMAN.charScale).toFixed(4)}`);
        },
        (xhr) => {
            if (xhr.total) {
                const pct = Math.round(xhr.loaded / xhr.total * 100);
                const hud = document.getElementById('hud');
                if (hud) hud.title = `FBX yükleniyor: %${pct}`;
            }
        },
        (err) => console.error('FBX yüklenemedi:', err)
    );
}

// ── INPUT & RENDER LOOP ───────────────────────────────────────────────────────
let mF=false,mB=false,mL=false,mR=false,playerAngle=0;
const SPEED=0.12, TURN=0.042;   // yürüme hızı: ~7 birim/sn (gerçekçi)
let walkCycle = 0;               // mesafeye bağlı adım animasyonu
document.addEventListener('keydown',e=>{if(e.key==='w'||e.key==='W')mF=true;if(e.key==='s'||e.key==='S')mB=true;if(e.key==='a'||e.key==='A')mL=true;if(e.key==='d'||e.key==='D')mR=true;});
document.addEventListener('keyup',e=>{if(e.key==='w'||e.key==='W')mF=false;if(e.key==='s'||e.key==='S')mB=false;if(e.key==='a'||e.key==='A')mL=false;if(e.key==='d'||e.key==='D')mR=false;});

const zoneEl = document.getElementById('zone-indicator');

function animate(){
    requestAnimationFrame(animate);
    const delta = clock.getDelta();

    // Update FBX animation mixer
    if (mixer) mixer.update(delta);

    // Active character: FBX if loaded, otherwise default player
    const char = fbxModel || player;

    if(mL)playerAngle+=TURN; if(mR)playerAngle-=TURN;
    char.rotation.y = playerAngle;

    let wlk=false;
    if (mF || mB) {
        const s = mF ? SPEED : -SPEED;
        const nx = char.position.x - Math.sin(playerAngle) * s;
        const nz = char.position.z - Math.cos(playerAngle) * s;

        if (!checkCollision(nx, nz)) {
            // Serbest hareket
            char.position.x = nx;
            char.position.z = nz;
        } else if (!checkCollision(nx, char.position.z)) {
            // Z duvarı — X'te kayarak geç
            char.position.x = nx;
        } else if (!checkCollision(char.position.x, nz)) {
            // X duvarı — Z'de kayarak geç
            char.position.z = nz;
        }
        // Her iki eksen de bloke: tamamen dur
        wlk = true;
    }

    // FBX animation switching
    if (fbxModel && mixer) {
        if (wlk)  switchAnim(walkClip || idleClip);
        else      switchAnim(idleClip || walkClip);
    } else if (!fbxModel) {
        if (wlk) {
            // Mesafeye bağlı adım — 0.48 rad/frame = ~13 kare/döngü = gerçekçi yürüyüş
            walkCycle += SPEED * 4.0;
            leftLeg.rotation.x  =  Math.sin(walkCycle) * 0.68;
            rightLeg.rotation.x = -Math.sin(walkCycle) * 0.68;
            leftArm.rotation.x  = -Math.sin(walkCycle) * 0.52;
            rightArm.rotation.x  =  Math.sin(walkCycle) * 0.52;
            // Hafif gövde sallama — gerçekçi yürüyüş hissi
            torso.rotation.z     =  Math.sin(walkCycle * 0.5) * 0.04;
        } else {
            // Durduğunda yumuşak dönüş — sert sıfırlama yok
            leftLeg.rotation.x  *= 0.80;
            rightLeg.rotation.x *= 0.80;
            leftArm.rotation.x  *= 0.80;
            rightArm.rotation.x *= 0.80;
            torso.rotation.z    *= 0.80;
        }
    }

    const half=HARMAN.mapSize*1.05;
    char.position.x=Math.max(-half,Math.min(half,char.position.x));
    char.position.z=Math.max(-half,Math.min(half,char.position.z));
    char.position.y=0;   // zemine kilitle — havada uçma yok

    // Keep default player in sync (for fallback)
    if (fbxModel) { player.position.copy(char.position); player.rotation.copy(char.rotation); }

    if(!HARMAN.freeCamera){
        const cd=15, ch=HARMAN.charCamH;
        camera.position.x=char.position.x+Math.sin(playerAngle)*cd;
        camera.position.z=char.position.z+Math.cos(playerAngle)*cd;
        camera.position.y=char.position.y+ch;
        camera.lookAt(char.position.x, char.position.y+1.7, char.position.z);
    }
    // Zone indicator
    if(zoneEl && HARMAN.zones.length>0){
        let near=HARMAN.zones[0],minD=Infinity;
        for(const z of HARMAN.zones){const d=Math.hypot(player.position.x-z.cx,player.position.z-z.cz);if(d<minD){minD=d;near=z;}}
        zoneEl.textContent=`📍 ${near.city}`;
        zoneEl.style.color=near.color||'#e94560';
    }

    // ── Phase 4: Sponsor animations + proximity popup + radar ──────────────
    const t4=Date.now()*.001;
    let nearSp=null, nearSpDist=Infinity;
    for(const obj of landmarkObjects){
        // Animate sponsor effects
        if(obj.userData.sponsorBand){
            const ei=.45+.38*Math.sin(t4*2.2);
            obj.userData.sponsorBand.material.emissiveIntensity=ei;
            if(obj.userData.sponsorBand2) obj.userData.sponsorBand2.material.emissiveIntensity=ei;
            if(obj.userData.sponsorLight) obj.userData.sponsorLight.intensity=1.2+.9*Math.sin(t4*2.8);
        }
        // Proximity check for sponsored landmarks
        if(obj.userData.sponsored){
            const d=Math.hypot(player.position.x-obj.position.x, player.position.z-obj.position.z);
            if(d<22 && d<nearSpDist){ nearSpDist=d; nearSp=obj; }
        }
    }
    // Proximity popup
    const popup=document.getElementById('sp-popup');
    if(popup){
        if(nearSp){
            popup.style.display='block';
            const sc=nearSp.userData.sponsorColor||'#e94560';
            popup.style.borderColor=sc;
            document.getElementById('sp-lm-name').textContent=nearSp.userData.name||'';
            document.getElementById('sp-brand').textContent='🏷️ '+nearSp.userData.sponsorName;
            document.getElementById('sp-brand').style.color=sc;
        } else { popup.style.display='none'; }
    }
    // Radar redraw every 3rd frame
    if(Math.round(t4*60)%3===0) drawRadar();

    // ── Sprint 3: Nehir su animasyonu (UV kayması) ───────────────────────
    if (riverMat && riverMat.map) {
        riverMat.map.offset.y = (riverMat.map.offset.y - 0.0022) % 1;
        riverMat.map.needsUpdate = true;
    }

    // ── Sprint 1: Kar animasyonu ──────────────────────────────────────────
    if (snowPts) {
        const sp = snowPts.geometry.attributes.position.array;
        const t  = Date.now() * 0.0004;
        const half2 = HARMAN.mapSize * 1.1;
        for (let i = 0; i < sp.length; i += 3) {
            sp[i+1] -= 0.055 + (i % 7) * 0.003;          // farklı hızda düşüş
            sp[i]   += Math.sin(t + i * 0.5) * 0.012;     // hafif sallanma
            sp[i+2] += Math.cos(t + i * 0.3) * 0.008;
            if (sp[i+1] < -1) {                             // üstten yeniden başlat
                sp[i]   = (Math.random()-0.5) * half2 * 2;
                sp[i+1] = 60;
                sp[i+2] = (Math.random()-0.5) * half2 * 2;
            }
        }
        snowPts.geometry.attributes.position.needsUpdate = true;
    }

    renderer.render(scene,camera);
}
animate();

// No resize needed — fixed 1280×520 canvas
"""

    lm_rows = ""
    if cfg["showLandmarks"]:
        lm_rows = "".join(
            f"📍 {CITIES[c['name']]['emoji']} {CITIES[c['name']]['landmark']}<br>"
            for c in cfg["cities"] if c["weight"] > 0.08
        )

    bld_count  = len(cfg["buildings"])
    st_count   = len(cfg["streets"])
    mode_label = "🌐 OSM" if cfg["useOSM"] else "⚙️ Prosedürel"

    lm_count   = len(cfg.get("landmarks", []))
    sp_count   = sum(1 for l in cfg.get("landmarks",[]) if l.get("sponsored"))

    return f"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/fflate@0.6.9/umd/index.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/FBXLoader.js"></script>
<style>
  html,body{{margin:0;padding:0;background:#07070f;overflow:hidden;}}
  canvas{{display:block;border-radius:10px;border:1px solid #1a1a2e;}}
  #hud{{position:fixed;top:12px;left:12px;color:#ccc;font-family:Inter,sans-serif;
        background:rgba(7,7,15,.90);padding:11px 15px;border-radius:8px;font-size:12px;
        pointer-events:none;border:1px solid #e94560;line-height:1.9;z-index:10;}}
  #hud b{{color:#e94560;}} #zone-indicator{{font-size:1.05em;font-weight:600;}}
  #lm{{position:fixed;bottom:12px;right:100px;color:#aaa;font-family:Inter,sans-serif;
       background:rgba(7,7,15,.82);padding:9px 13px;border-radius:8px;font-size:10px;
       pointer-events:none;border:1px solid #1a1a2e;line-height:1.9;z-index:10;}}
  #stats{{position:fixed;bottom:12px;left:12px;color:#555;font-family:Inter,sans-serif;
          background:rgba(7,7,15,.75);padding:7px 12px;border-radius:8px;font-size:10px;
          pointer-events:none;line-height:1.7;z-index:10;}}
  /* Radar */
  #radar{{position:fixed;bottom:12px;right:12px;z-index:10;border-radius:50%;
          border:1px solid #e94560;opacity:.88;}}
  /* Proximity popup */
  #sp-popup{{display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);
             background:rgba(7,7,15,.92);border:1px solid #e94560;border-radius:12px;
             padding:14px 20px;z-index:20;text-align:center;pointer-events:none;
             font-family:Inter,sans-serif;min-width:200px;}}
  #sp-lm-name{{color:#ccc;font-size:.9em;margin-bottom:5px;}}
  #sp-brand{{font-size:1.2em;font-weight:700;letter-spacing:2px;}}
  #sp-ad-label{{color:#444;font-size:.72em;margin-top:4px;letter-spacing:1px;}}
</style>
</head>
<body>
<div id="hud"><b>HARMAN</b> v5.0<br><b>W/S</b>&nbsp;İleri/Geri&nbsp;&nbsp;<b>A/D</b>&nbsp;Dön<br><span id="zone-indicator"></span></div>
<div id="lm">{lm_rows}</div>
<div id="stats">{mode_label} · {bld_count} bina · {lm_count} lm · <span style="color:#00d4ff">{sp_count} sponsor</span></div>
<canvas id="radar" width="80" height="80"></canvas>
<div id="sp-popup">
  <div id="sp-lm-name"></div>
  <div id="sp-brand"></div>
  <div id="sp-ad-label">SPONSORED LANDMARK</div>
</div>
<script>{js}</script>
</body>
</html>"""


# ── MAIN RENDER ───────────────────────────────────────────────────────────────
if gen_btn:
    if use_osm and HAS_OSM:
        with st.status("🌍 Harman v4.0 — Şehirler yükleniyor…", expanded=True) as status:
            def push(msg): status.write(msg)

            result = build_blended_map(
                normalized,
                density     = density,
                map_size    = map_size,
                zone_mode   = zone_mode,
                softness    = softness,
                show_streets= show_streets,
                sponsors    = dict(st.session_state.get("sponsors", {})),
                progress_cb = push,
            )
            # Store landmark list for sponsor UI
            st.session_state.lm_list = result.get("lm_pools", {})

            lm_count = len(result.get("landmarks", []))
            sp_count = sum(1 for l in result.get("landmarks",[]) if l.get("sponsored"))
            status.update(
                label=f"✅ Harita hazır — {result['total']} bina · {lm_count} landmark · {sp_count} sponsor",
                state="complete", expanded=False,
            )

        cfg  = _build_config(
            normalized, density, map_size, show_lm, weather, cam_mode,
            buildings=result["buildings"],
            streets  =result["streets"],
            zones    =result["zones"],
            terrain  =result["terrain"] if show_terrain else None,
            landmarks=result.get("landmarks", []),
        )
        html = generate_html(cfg)
        components.html(html, width=1280, height=540, scrolling=False)

        # Stats panel
        cols = st.columns(len(normalized) + 1)
        with cols[0]:
            st.markdown(
                f"<div class='stat-card'>"
                f"<div class='stat-label'>Toplam</div>"
                f"<div class='stat-value'>{result['total']} bina</div>"
                f"<div class='stat-sub'>{len(result['streets'])} sokak seg.</div>"
                f"<div class='stat-sub'>{lm_count} landmark · <b style='color:#00d4ff'>{sp_count} sponsor</b></div>"
                f"<div class='stat-sub'>🌐 OSM · {'Bölge' if zone_mode else 'Karma'} mod</div>"
                f"</div>", unsafe_allow_html=True
            )
        for idx, (cname, weight) in enumerate(normalized):
            stats  = result["city_stats"].get(cname, {})
            placed = result["sources"].get(cname, 0)
            color  = CITIES[cname]["color"]
            with cols[idx+1]:
                st.markdown(
                    f"<div class='stat-card'>"
                    f"<div class='stat-label' style='color:{color};'>{CITIES[cname]['emoji']} {cname}</div>"
                    f"<div class='stat-value'>{placed} bina</div>"
                    f"<div class='stat-sub'>Pool: {stats.get('total','—')} &nbsp;|&nbsp; "
                    f"ort.yük: {stats.get('avg_height','—')} birim</div>"
                    f"</div>", unsafe_allow_html=True
                )

        # ── Phase 5: World Lore + AI Sponsor Suggestions ────────────────────
        _ak = st.session_state.get("api_key","")
        if HAS_ANTHROPIC and _ak:
            lore_col, sp_col = st.columns([3, 1])
            with lore_col:
                if st.button("✨ Dünya Loru Üret", key="gen_lore", use_container_width=True):
                    with st.spinner("Claude dünya tarihi yazıyor…"):
                        lore = generate_world_lore(
                            [{"name": c, "weight": w} for c, w in normalized], _ak
                        )
                    st.session_state.world_lore = lore
            with sp_col:
                if st.button("🏷️ Sponsor Öner", key="ai_sp_btn", use_container_width=True,
                             disabled=not result.get("landmarks")):
                    with st.spinner("Claude sponsor öneriyor…"):
                        sugs = suggest_sponsors(
                            result.get("landmarks", []),
                            [{"name": c} for c, _ in normalized],
                            _ak,
                        )
                    st.session_state.ai_sponsor_suggestions = sugs

            if st.session_state.get("world_lore"):
                st.markdown(
                    f"<div style='background:rgba(233,69,96,.06);border:1px solid rgba(233,69,96,.3);"
                    f"border-radius:10px;padding:16px 20px;margin-top:8px;'>"
                    f"<div style='color:#e94560;font-size:.75em;letter-spacing:2px;"
                    f"font-family:Orbitron,monospace;margin-bottom:8px;'>✨ DÜNYA LORU</div>"
                    f"<div style='color:#ccc;font-family:Inter,sans-serif;font-size:.95em;"
                    f"line-height:1.65;font-style:italic;'>\"{st.session_state.world_lore}\"</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            if st.session_state.get("ai_sponsor_suggestions"):
                st.markdown(
                    "<div style='color:#d4af37;font-size:.75em;letter-spacing:2px;"
                    "font-family:Orbitron,monospace;margin:14px 0 8px 0;'>🤖 AI SPONSOR ÖNERİLERİ</div>",
                    unsafe_allow_html=True,
                )
                sp_cols = st.columns(min(4, len(st.session_state.ai_sponsor_suggestions)))
                for i, sug in enumerate(st.session_state.ai_sponsor_suggestions[:4]):
                    with sp_cols[i % len(sp_cols)]:
                        color = sug.get("color","#e94560")
                        st.markdown(
                            f"<div style='background:rgba(255,255,255,.03);border:1px solid {color}33;"
                            f"border-radius:8px;padding:10px 12px;'>"
                            f"<div style='color:{color};font-size:.8em;font-weight:600;"
                            f"font-family:Inter,sans-serif;'>{sug.get('brand','')}</div>"
                            f"<div style='color:#666;font-size:.72em;font-family:Inter,sans-serif;"
                            f"margin-top:3px;'>{sug.get('landmark','')[:25]}</div>"
                            f"<div style='color:#444;font-size:.7em;font-family:Inter,sans-serif;"
                            f"margin-top:4px;font-style:italic;'>{sug.get('reason','')}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

    else:
        if use_osm and not HAS_OSM:
            st.warning("osmnx yüklü değil — prosedürel moda geçildi. `pip install osmnx`")
        with st.spinner("Şehirler harmanlanıyor…"):
            cfg  = _build_config(normalized, density, map_size, show_lm, weather, cam_mode)
            html = generate_html(cfg)
        components.html(html, width=1280, height=540, scrolling=False)

else:
    mode_hint = "🌐 OSM Gerçek Veri" if use_osm else "⚙️ Prosedürel"
    st.markdown(f"""
    <div class='placeholder-box'>
        <div style='font-size:4em;opacity:.35;margin-bottom:16px;'>🌆</div>
        <div style='color:#333;font-size:1.05em;letter-spacing:2px;font-family:Inter,sans-serif;opacity:.6;'>
            Şehirleri seç ve HARMANLA'ya bas
        </div>
        <div style='color:#222;font-size:.82em;margin-top:10px;font-family:Inter,sans-serif;'>
            {mode_hint} &nbsp;·&nbsp; {'Bölge Modu' if zone_mode else 'Karma Mod'}
        </div>
    </div>""", unsafe_allow_html=True)
