# Pustaka kesan video GAC (20 kesan)

Semua kesan diletak di `"effects"` dalam timeline: `{"type": ..., "t": [mula, tamat], ...}` (masa video asal).
Kod: `scripts/effects.py` (asal) + `scripts/effects2.py` (baharu). Bunyi dipasang automatik.

## Peraturan zon (WAJIB, semua kesan)
- **Muka mesti bersih.** Tiada tulisan, ikon, serpihan atau panel di atas muka (atas rambut hingga dagu).
  Overlay hanya di **jalur atas kepala** (y 250 hingga atas rambut) atau **bawah dagu** (dagu hingga y 1470).
- **Zon UI TikTok:** tiada tulisan di atas y 220, di bawah y 1500, atau di kanan x 960 (y 700-1500).
- Kesan seluruh skrin (zoom, dolly, latar) tidak menutup muka; muka kekal seperti asal.
- Animasi yang bergerak melalui zon UI: guna versi statik (cth `coinstack` `"drop": 0`).
- Sari kata disembunyikan sendiri semasa panel / senarai dipapar (panel sudah menyebut isi yang sama).
- 1-2 kesan setiap 15 s; setiap kesan ≥ 1.5 s.

## Senarai
| # | Nama | `type` | Kunci | Bila guna |
|---|---|---|---|---|
| 1 | Orbit | `orbit` | `items` [..], `speed` | perkataan/ciri mengelilingi anda (sisi jauh di belakang anda) |
| 2 | Chat Takeover | `chat` | `messages` [[teks, "l"/"r"], ..], `gap` | soalan pelanggan / testimoni chat |
| 3 | Frame Escape | `frame_escape` | – | video jadi bingkai, anda keluar dari bingkai |
| 4 | Snap Zoom | `snapzoom` | `to` (1.3) | penekanan pantas pada satu ayat |
| 5 | Checklist Pop | `checklist_pop` | `items`, `at` [masa disebut] | senarai yang melantun masuk |
| 6 | Headline Storm | `headlines` | `headlines` [..] | tajuk berita (hanya yang disebut/diberi) |
| 7 | Zoom Portal | `portal` | `image` (pilihan) | portal bulat terbuka di belakang anda |
| 8 | Growth Curve | `growth` | `values`, `label`, `source` | graf naik (nombor peserta sahaja, nyatakan sumber) |
| 9 | Studio Reveal | `studio` | – | latar jadi studio gelap, lampu sorot menyala |
| 10 | B-roll Overlay | `broll` | `image`, `pos` top/bottom | gambar/klip peserta dalam kad |
| 11 | Paper Cutout | `paper` | – | anda jadi potongan kertas atas kertas kraf |
| 12 | Dolly Zoom | `dolly` | `amount` (0.35) | kesan vertigo: latar menjauh, anda kekal |
| 13 | Magazine Cover | `magazine` | `title`, `issue`, `lines` | kulit majalah, masthead di belakang kepala |
| 14 | Liquid Glass | `liquid` | `text`, `size` | pil kaca cecair bawah dagu |
| 15 | Zoom Through Cut | `zoomthrough` | – (letak `t` merentasi potongan) | peralihan meluru masuk/keluar |
| 16 | Green Screen | `greenscreen` | `image` atau `color` | tukar latar untuk satu bahagian (seluruh video: `scripts/bgswap.py`) |
| 17 | Frame Break | `frame_break` | – | macam Frame Escape + serpihan kaca (tak lalu muka) |
| 18 | Digital Zoom | `digitalzoom` | `to` | zoom perlahan ke muka |
| 19 | Phone Mockup | `phone` | `image` atau `title`+`items` | telefon slaid masuk |
| 20 | Checklist | `checklist` | `title`, `items`, `at` | kad senarai bertanda |

Lain-lain yang sedia ada: `glass` (Glass Type), `chart` (Chart Grow), `zoomcut`, `pullback`.

## Contoh
```json
"effects": [
  {"type": "snapzoom", "t": [5.7, 6.6]},
  {"type": "checklist_pop", "t": [14.2, 27.0], "items": ["Cari circle", "Peruntuk duit"], "at": [14.2, 20.2]},
  {"type": "growth", "t": [28.6, 32.0], "values": [1, 2, 3, 5], "label": "Simpanan emas"},
  {"type": "chat", "t": [38.8, 43.0], "messages": [["Nak set auto debit", "l"], ["DM saya!", "r"]]}
]
```
Kesan yang perlukan topeng orang (orbit, frame_*, portal, studio, paper, dolly, magazine, greenscreen)
lebih perlahan dirender (±0.5-1 s sebingkai).
