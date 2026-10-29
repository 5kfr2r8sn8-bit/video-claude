# Gaya 2: "Panel kaca cerita atas kepala" (frosted glass storytelling, tutorial teknologi)

Dianalisis daripada video rujukan TikTok yang dimuat naik pengguna pada 2026-10-29
(79 s, 576×1024, 30 fps, 74 s kandungan + 4 s kad akhir TikTok). Ukuran ditukar ke 1080×1920 (×1.875).
Bingkai rujukan tidak disimpan dalam repo (video milik orang lain); hanya teknik dan ukuran.

Rasa keseluruhan: SATU panel kaca kabur (frosted glass) sentiasa terapung di ATAS KEPALA, dan
kandungannya bertukar ikut ayat (nombor, ikon, carta, harga, butang). Muka dan badan tidak pernah
ditutup. Kemas, premium, macam UI app (iOS widget) atas video sebenar.

---

## 1. Saat pertama (bingkai 0–29)
| Bingkai | Apa berlaku |
|---|---|
| 0 | Video sahaja, penceramah sudah bercakap. Tiada teks. |
| 1–2 | **Panel kaca kosong muncul** di atas kepala (fade + sedikit membesar). Bentuk: segi empat bucu bulat ±40 px, isi kabur, tepi nipis cerah. |
| 3–11 | **Nombor "2026" bergulir masuk digit demi digit** (gaya slot/odometer): setiap digit muncul dari bawah, kelihatan separuh, kemudian tegak. ±1 digit setiap 2 bingkai, kiri ke kanan. |
| 12–29 | "2026" tetap. **Percikan cahaya kecil** (bintik putih/emas) mula naik di sekitar panel (bingkai 18+). |
| ±1.0 s | Baris kecil huruf jarak luas "THE YEAR OF" muncul, kemudian "AGENTIC **AI**" besar (kata kunci warna oren-emas). |

Pengajaran: hook bermula dengan **satu nombor besar yang bergulir** dalam panel kaca. Mata terus ke
atas kepala, muka kekal jelas.

## 2. Rentak & potongan
- Jump cut setiap **±2.5 s** (30 potongan dalam 74 s), satu take.
- Zoom bergilir: tengah dekat (dada ke atas) ↔ sedikit jauh (separuh badan).
- Jeda dipotong ketat (median 70 ms).
- Tiada sari kata penuh! Hanya **kata kunci / label** dalam panel. (Teks = ringkasan visual, bukan transkrip.)

## 3. Panel kaca dan kandungannya
**Panel:** lebar ±88% skrin (x 70–1010), tinggi ikut kandungan (±200–420 px), di y ±60–520
(jalur atas kepala; di 1080×1920 letak y ≥ 250 untuk zon UI). Isi: kabur kuat latar belakang
(blur ±25) + tint coklat keemasan (#8D674D, alpha ±0.55), tepi 2 px putih 25%, bayang lembut.
Panel KEKAL sepanjang bahagian; hanya kandungan bertukar dengan cross-fade 4–6 bingkai.

| Jenis kandungan | Contoh rujukan | Cara keluar |
|---|---|---|
| **Nombor bergulir** | "2026", "2024", counter "0 → 24 JAM" | digit demi digit dari bawah (odometer) |
| **Tajuk + label kecil** | "THE YEAR OF / AGENTIC **AI**" | label huruf kecil jarak luas dulu, tajuk besar pop |
| **Teks amaran** | "KETINGGALAN" merah + percikan bunga api | pop + gegar kecil, kilauan merah |
| **Ikon + label** | robot, "Your AI intern" + bulatan kiraan | ikon pop (skala 0.6→1), teks fade |
| **Pil tag mengelilingi ikon** | Emails / Tasks / Research / Code | pil muncul satu-satu di sekeliling |
| **Tanda ✓ + ayat** | "✓ Let it do the work" | tick hijau + teks taip |
| **Carta lengkung** | "LEARNING CURVE", Day 1 → Trained | garis melukis sendiri, titik bergerak, label pil |
| **Baris ikon app** | ChatGPT / Claude / DeepSeek | kad ikon bucu bulat muncul satu-satu kiri→kanan |
| **Harga** | "RM??" → cop **"MURAH!"** hijau senget | cop hentak (skala 1.4→1, putaran −8°), bingkai neon hijau |
| **Senarai setup + harga** | Cloud server RM40/year, AI model RM10 | baris slaid masuk, harga berguling |
| **Formula** | robot + brain = ~RM0 /month | kad muncul satu-satu, "=" kemudian, nombor bergulir |
| **Awan tag** | "Macam-macam!" + Research / Emails / Coding... | tajuk pop, tag muncul berderet |
| **CTA** | "🔗 Check out my bio" + anak panah ↑ ke atas | pil pop, anak panah melantun ke arah nama akaun |
| **Pilihan A atau B** | Desktop *or* VPS (dua kad sebelah-menyebelah) | kad kiri dulu, "or", kad kanan |

**Peralihan imbas kembali (flashback):** "3 YEARS AGO ◀◀ 2023": video jadi **jalur filem**
(lubang sprocket kiri & kanan), warna **sepia/merah hangat** + kebocoran cahaya, garis imbasan, kemudian
**kilat putih penuh** (2–3 bingkai) kembali ke masa kini. Tempoh ±3 s.

## 4. Font
| Peranan | Rujukan (anggaran) | Guna dalam GAC |
|---|---|---|
| Nombor & tajuk | Sans geometri sangat tebal (SF Pro Display Heavy) | **Inter Black** / Montserrat ExtraBold |
| Label kecil | Sans huruf besar, jarak luas (tracking +20%) | Montserrat SemiBold, tracking luas |
| Teks pil / butang | Sans Semibold putih | Plus Jakarta Bold |
| Kod / nota kecil | Monospace | JetBrains Mono |

## 5. Warna
| Peranan | Nilai |
|---|---|
| Tint panel kaca | **#8D674D** (coklat keemasan), alpha ±0.55 |
| Teks utama | putih |
| Kata kunci | oren-emas (±#F5A623) |
| Amaran | merah (KETINGGALAN) |
| Positif / murah | hijau neon **#46B58C** |
| Video | gred hangat semula jadi (lampu kuning siling), tidak diubah |

## 6. Bunyi
- **Muzik latar perlahan** sepanjang video (nada rendah berterusan dalam spektrum), suara jelas di atas.
- Kekuatan −19 LUFS, LRA 9.6 (lebih dinamik daripada Gaya 1).
- **Sting/riser** pada hook (0–3 s) dan semasa flashback (±10 s): harmonik tinggi muncul.
- Bunyi kecil "pop / tick" bila kandungan panel bertukar (anggaran; perlahan).

## 7. Peraturan zon (WAJIB, sama macam semua gaya)
Panel hanya di jalur atas kepala (y 250 hingga atas rambut − 20). Kalau ruang atas kepala terlalu
sempit, kecilkan panel; jangan sekali-kali turunkan ke muka. CTA anak panah ↑ juga dalam jalur itu.

## 8. Yang GAC sudah ada vs perlu dibina
Ada: panel kaca kabur (`effects.frosted`), nombor bergulir (`counter`), carta (`growth`), pil,
ikon pop, tanda ✓, cop (`mword`), kilat putih (`fx.flash`), muzik? (tiada, peserta tambah sendiri di TikTok).
Perlu dibina sebelum Gaya 2 boleh ditiru penuh:
1. **Panel kaca tetap atas kepala** yang kandungannya bertukar ikut masa (satu elemen `glasspanel` dengan `scenes`).
2. **Nombor odometer** digit demi digit.
3. **Cop "MURAH!"** neon senget yang menghentak.
4. **Baris kad ikon** dan **formula A + B = C**.
5. **Peralihan flashback jalur filem** + sepia + kilat putih.
6. Percikan cahaya kecil di sekitar panel.
Bila peserta minta "gaya 2", tunjuk senarai ini dalam plan dan bina dulu jika setuju.
