# 🌆 HARMAN — City Blend Engine

**Gerçek dünya şehirlerini harmanlayarak oynanabilir 3D oyun haritaları üret.**

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Deneyin-e94560?style=for-the-badge)](https://harman.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red.svg)](https://streamlit.io)
[![Three.js](https://img.shields.io/badge/Three.js-r128-green.svg)](https://threejs.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🎮 **[→ Hemen Dene: harman.streamlit.app](https://harman.streamlit.app)**

---

## ✨ Özellikler

- **6 Şehir** — Tokyo · İstanbul · Paris · New York · Dubai · Londra
- **OSM Gerçek Veri** — OpenStreetMap'ten gerçek bina ölçüleri, sokak ağı, landmark'lar
- **Zone Bazlı Harmanlama** — Voronoi bölgeleri, Voronoi yumuşaklık kontrolü
- **4 Mevsim** — Yaz · İlkbahar · Sonbahar · Kış (kar, çimen, kuru yaprak)
- **Procedural Dokular** — Tuğla · Kireçtaşı · Cam panel · Beton (canvas tabanlı, harici dosya yok)
- **Landmark Sistemi** — Gerçek OSM POI'lar + sponsor billboard sistemi
- **Çarpışma Tespiti** — AABB + slide-along-wall
- **FBX Karakter** — Kendi modelini yükle, animasyonlar desteklenir
- **Claude AI** — Doğal dil ile şehir tanımı, dünya loru, sponsor önerisi
- **Ağaçlar & Nehir** — Zone'a özgü ağaç türleri, animasyonlu su

---

## 🚀 Kurulum

```bash
# 1. Repoyu klonla
git clone https://github.com/KULLANICI/harman.git
cd harman

# 2. Bağımlılıkları kur
pip install -r requirements.txt

# 3. Uygulamayı başlat
streamlit run app.py
```

> **Not:** OSM verisi ilk çalıştırmada otomatik indirilir ve `data/cache/` klasörüne kaydedilir.

---

## ⚙️ Yapılandırma

### Claude AI (opsiyonel)
`.streamlit/secrets.toml` dosyası oluştur:
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

Ya da uygulama içinde sidebar'dan API key girilebilir.

---

## 📁 Proje Yapısı

```
harman/
├── app.py                  # Ana Streamlit uygulaması
├── requirements.txt        # Python bağımlılıkları
├── data/
│   ├── osm_fetcher.py      # OpenStreetMap veri çekici
│   ├── landmark_fetcher.py # POI / landmark verisi
│   └── cache/              # OSM önbelleği (git'e dahil değil)
├── engine/
│   ├── blend_engine.py     # Şehir harmanlama motoru
│   ├── zone_engine.py      # Voronoi bölge sistemi
│   ├── terrain_engine.py   # Arazi parametreleri
│   └── landmark_engine.py  # Landmark yerleştirme
└── ai/
    └── harman_ai.py        # Claude API entegrasyonu
```

---

## 🗺️ Sprint Yol Haritası

| Sprint | İçerik | Durum |
|--------|--------|-------|
| 1 | UI + Şehir Seçimi + Three.js Temel | ✅ |
| 2 | OSM Gerçek Veri + Procedural Dokular | ✅ |
| 3 | Zone Motoru + Sokaklar + Arazi | ✅ |
| 4 | Landmark + Sponsor Sistemi | ✅ |
| 5 | Claude AI Entegrasyonu | ✅ |
| 6 | FBX Karakter + Animasyon | ✅ |
| 7 | Mevsim + Atmosfer + Çarpışma | ✅ |
| 8 | GLB Export | 🔜 |
| 9 | Gece/Gündüz Döngüsü | 🔜 |
| 10 | Sponsor Dashboard | 🔜 |

---

## 🛠️ Geliştirilen Teknolojiler

- **Frontend:** Three.js r128, Streamlit
- **Backend:** Python, OSMnx, GeoPandas
- **AI:** Anthropic Claude API (claude-opus-4-8)
- **Veri:** OpenStreetMap, Overpass API

---

## 📄 Lisans

MIT License — Detaylar için [LICENSE](LICENSE) dosyasına bakın.
