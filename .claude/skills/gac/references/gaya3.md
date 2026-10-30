# Gaya 3: "Kad kaca hitam emas + sari kata frasa" (premium, gaya bilik pameran emas)

Dianalisis daripada video rujukan yang dimuat naik pengguna pada 2026-10-30 (61.5 s, 576×1024, 30 fps,
−14.7 LUFS, LRA 3). Ukuran ditukar ke 1080×1920 (×1.875). Video rujukan tidak disimpan dalam repo.

Rasa keseluruhan: mewah, gelap + emas. SATU kad kaca hitam bertepi emas di atas kepala, kandungan bertukar
ikut ayat. Sari kata frasa pendek di paras dada, kata kunci emas. Selingan B-roll penuh skrin
(telefon app GAP / jongkong emas) atas latar gelap bersinar emas.

## 1. Saat pertama
| Masa | Apa berlaku |
|---|---|
| 0.0–0.1 s | Video sahaja, penceramah sudah bercakap (tiada intro). |
| 0.1–0.3 s | Kad kaca hitam kosong fade masuk di atas kepala. |
| 0.3–0.5 s | Label kecil emas jarak luas "TIPS SIMPAN EMAS" muncul. |
| 0.5–1.0 s | Tajuk serif muncul **perkataan demi perkataan** (fade + blur hilang): "Simpan Emas Ikut **Bajet**, Bukan Ikut Harga". Kata kunci emas. |
| 0.2 s+ | Sari kata frasa pertama "Untuk mula simpan emas," muncul di paras dada. |

## 2. Rentak
- Tiada jump-cut zoom: bingkai sama sepanjang video. Variasi datang daripada kad yang bertukar dan selingan B-roll.
- Kad bertukar setiap ±3–6 s. B-roll 3–6 s setiap satu (app telefon, jongkong emas), suara terus berjalan.

## 3. Elemen
| Jenis | Rujukan | Cara keluar |
|---|---|---|
| Kad tajuk | label emas kecil + tajuk serif (Playfair) putih, kata kunci emas | perkataan demi perkataan |
| Kad besar | "GAP" emas gradien tebal + "Gold Accumulation Program" | pop skala |
| Cip ✓ / ✗ | pil hitam, tepi hijau ✓ "Ikut bajet anda", tepi merah ✗ (coret) "Ikut harga pasaran" | satu-satu ikut sebutan |
| Kad emas | pil label "MULA SERENDAH" + kad emas "1 gram / EMAS 999.9" *atau* "RM100 / SAHAJA" | satu-satu |
| Kad bar | "KONSISTEN" + "Kumpul gram emas setiap bulan" + carta bar naik | bar tumbuh satu-satu |
| Kaunter | "7 g → 98 g → 299 g → 1,000 g / 1 KILOGRAM" atas B-roll jongkong | nombor bergulir |
| Amaran | pil "⏳ Tunggu harga terendah?" → "Terlepas peluang!" merah | tukar teks, gegar |
| Penutup | "Mula Hari Ini" serif emas + "walaupun bajet kecil"; "MULAKAN SIMPANAN EMAS / bersama **Public Gold**" + pil emas "Isi borang ↓" "Link di bio" | pop |
| B-roll | telefon app GAP atas latar gelap dengan sinar emas berputar, zoom perlahan; label pil emas "Direkod dalam akaun GAP" | zoom, pil pop |

## 4. Font & warna
- Tajuk: **Playfair Display Bold** (serif). Label/sari kata/pil: **Montserrat** ExtraBold.
- Emas #F2C14E (gradien #FFE7A0 → #F2C14E → #D49B2A), kad hitam rgba(12–34,10–27,8–18,.9), tepi emas.
- Sari kata: putih 54 px, kata kunci emas, kotak gelap separa lutsinar.
- Video: warna asal (tiada gred).

## 5. Bunyi
Suara padat (LRA 3), muzik latar lembut, bunyi kecil bila kad/cip muncul.

## 6. Zon (WAJIB)
Kad di jalur atas kepala (y 225 hingga atas rambut − 20). Sari kata di paras dada (y ±1430). Muka tidak ditutup.

## 7. Cara buat (HyperFrames) — `scripts/gaya3_hf.py`
1. Potong jeda/ulangan tanpa zoom, tanpa gred (`build/rakaman4/cut3.py` sebagai contoh) → `PROJECT/assets/cut.mp4`.
2. Transkrip video yang dipotong → `PROJECT/words.json` (betulkan perkataan salah dengar terus dalam fail).
3. `spec.json`: `band` (atas kepala), `captions` (`y`, `h`, `keys` kata kunci emas), `scenes`
   (title / big / chips / gold / bars / warn / cta / broll). Lihat docstring skrip.
4. Salin ke `PROJECT/assets/`: gsap.min.js, Montserrat.ttf, PlayfairDisplay.ttf (assets/fonts), gambar produk,
   `assets/ikon/akaun_gap.jpg`, `assets/ikon/public_gold_logo.png`.
5. `python3 scripts/gaya3_hf.py spec.json PROJECT` → lint → snapshot → render → encode telefon (lihat gaya2.md).
- Video yang sudah ada **sari kata tertanam**: letak kotak sari kata (`captions.y/h`) betul-betul atas sari
  kata lama; kotak kabur (backdrop blur 20) + gelap .62 menyembunyikannya. (Rakaman4: y 1428, h 140.)
- Contoh lengkap: Rakaman4 (`build/hf/r4g3/spec.json`).
