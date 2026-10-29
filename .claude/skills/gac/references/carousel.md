# Carousel remake (slaid gambar)

Untuk bila peserta beri carousel orang lain sebagai contoh dan minta "ikut sebijik, tukar gambar saya".
Skrip: `scripts/carousel.py`. Contoh pelan lengkap (12 slaid "Cara Daftar Akaun Emas", diluluskan
2026-10-29): `references/carousel_contoh.json`.

## Apa yang skrip buat
Reka bentuk contoh (tajuk emas, kad screenshot, panel, tangan emas) dikekalkan. Ia:
- buang orang dalam contoh dan isi tempatnya, letak gambar peserta sebagai sticker (outline putih);
- tukar data dealer lain (nama, PG Code, cawangan, nombor transaksi) kepada data peserta, font Open Sans macam app;
- buang UI TikTok (butang kanan, bar carian, avatar, titik carousel, tandatangan);
- lukis semula lencana nombor langkah (1..n, susunan betul);
- pilihan: tukar latar ke gambar peserta sendiri (`bg`), alih panel ke tepi (`shift`).

Tiada AI penjana gambar. Hanya gambar peserta sendiri, latar yang peserta beri, dan reka bentuk contoh.
Contoh milik dealer lain: ingatkan peserta minta izin pembuat asal, dan jangan sekali-kali tinggalkan
nama / PG Code / tandatangan orang lain.

## Folder kerja (`build/<nama>/`)
```
ref/00.jpg ..   slaid contoh, ikut susunan
me/01.jpg ..    gambar peserta (cut-out me/cut_NN.png dibuat automatik kali pertama)
bg/*.jpg        latar pilihan peserta
slides.json     pelan setiap slaid
```
`.venv/bin/python .claude/skills/gac/scripts/carousel.py build/<nama> [00 03 ...]` -> `build/<nama>/out/*.jpg`.
Perlu `opencv-contrib-python-headless onnxruntime` dalam .venv dan model `~/.cache/gac/models/u2net_human_seg.onnx`
(dimuat turun sendiri oleh poster.py).

## slides.json: kunci setiap slaid
| Kunci | Maksud |
|---|---|
| `person_region` [x0,y0,x1,y1] | kawasan orang dalam contoh (dibuang) |
| `me` | `{"n": "04", "height": 1000, "bottom": 1950, "right": 400, "dx": 0, "flip": false, "border": 10}` gambar peserta. `right` = tepi kanan sticker; `border` 5 bila ada celah sempit (bawah ketiak) |
| `ui` / `ui_fine` / `ui_icons` / `ui_rows` / `dots` | buang UI: kotak licin / Telea halus / piksel ikon putih sahaja / isi baris demi baris / bulatan titik `[cx,cy,r]` |
| `rows_fill` true | isi lubang orang baris demi baris (elak bayang bila ramai orang dibuang) |
| `protect` | kotak yang tidak boleh disentuh oleh pengisian (kad) |
| `text` | `{"box", "text", "font": os/osb/lib/libi, "size", "x", "y", "color", "max_w", "flat"}` ganti teks |
| `headline` | `{"box", "text", "size"}` tulis semula sebaris tajuk serif emas 3D |
| `gold` | nilai emas besar dalam panel navy (cth PG Code) |
| `clear` | kosongkan kotak sebelum `gold` |
| `badge` | `[cx, cy, r, "4"]` lencana syiling nombor |
| `mirror` / `copy` / `rowfill` | baiki bingkai kad: cermin tepi bertentangan / salin tampalan (plain, flipv, tile) / isi warna dari kiri |
| `front` | kotak yang ditampal semula di atas sticker (panel di depan orang) |
| `bg` | fail latar dalam `bg/`; `score` kotak tajuk (piksel emas/putih dikekalkan), `solid` kotak kad/panel bucu bulat, `bg_dark` gelapkan lagi, `shift` alih `solid` ke kanan (px) |

## Aliran kerja
1. Semak semua slaid contoh, senaraikan data orang lain yang mesti ditukar. Minta data peserta yang tiada.
2. Padankan gambar ikut arah tangan / pandangan (tangan menunjuk ke kad; pandangan ke arah luar slaid).
   Elak gambar dengan orang lain / kanak-kanak.
3. Ukur kotak dengan grid (crop + garis setiap 50 px), bina `slides.json`, jalankan, lihat setiap slaid.
4. Cut-out bermasalah (dinding sama warna tudung, celah bawah ketiak): lukis poligon manual pada
   `me/cut_NN.png` (lihat helaian grid gambar asal pada offset bbox), kemudian `border` 5.
5. Hantar semua slaid + zip. Ingatkan: baki/harga/dakwaan dari contoh asal mesti disahkan peserta.
