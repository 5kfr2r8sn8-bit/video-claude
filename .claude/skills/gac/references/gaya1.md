# Gaya 1: "Tutorial motion-UI" (bersih, hangat, teks bertaip, kata kunci biru)

Dianalisis daripada video rujukan TikTok (84 s, 576×1024, 30 fps) yang pengguna muat naik pada
2026-10-28. Semua ukuran di bawah sudah ditukar ke kanvas GAC **1080×1920** (×1.875).
Bingkai rujukan tidak disimpan dalam repo (video milik orang lain); hanya ukuran dan teknik.

Rasa keseluruhan: macam tutorial produk teknologi. Bersih, banyak ruang, teks kecil dan tajam,
satu warna aksen (biru), grafik "app UI" gelap yang muncul dari bawah, tiada muzik, rentak laju.

---

## 1. Saat pertama (bingkai 0–29)

| Bingkai | Apa berlaku |
|---|---|
| 0 | **Semua teks hook sudah ada pada bingkai pertama** (jadi cover). Tiada fade-in, tiada logo intro. Penceramah sudah bercakap pada bingkai 0 (tiada senyap di awal). |
| 0 | Susun atur hook 2 tingkat di atas kepala: **baris kecil** `ramai gila orang` (kiri) + `edit pakai` (kanan), dan di bawahnya **satu perkataan gergasi** `✳ Claude`. |
| 0 | Perkataan gergasi berada **di belakang kepala**: topi penceramah menutup sebahagian huruf "au". Ini teknik *text-behind-subject*. |
| 0–19 | Baris kecil berwarna kelabu pudar (≈ #A8A29E). |
| 20 | Perkataan `ramai gila orang` bertukar hitam penuh **tepat bila disebut** (karaoke kelabu → hitam, tukar serta-merta, tiada animasi). `edit pakai` kekal kelabu sehingga disebut. |
| 0–29 | Kamera statik, tiada zoom, tiada kesan bunyi. Tiada pergerakan grafik langsung dalam 1 saat pertama. Yang bergerak cuma penceramah dan warna perkataan. |
| ±2.5 s | Potongan pertama (jump cut), dan hook hilang serta-merta (potong keras, tiada fade). |

Pengajaran: saat pertama sengaja **senyap secara visual**. Hook besar + bersih + suara terus
masuk. Mata penonton terus baca hook sambil dengar ayat yang sama.

## 2. Rentak & potongan

- **59 potongan dalam 84 s**, iaitu satu potongan setiap **±1.4 s**. Semua jump cut dalam satu take yang sama.
- Jeda antara ayat dipotong sangat ketat: purata **50 ms**, paling panjang **110 ms**. Hampir tiada nafas.
- Zoom bertukar setiap potongan antara **3 aras**: lebar (badan penuh, ≈1.0), sederhana (≈1.15), dekat (≈1.3, dada ke atas).
- Struktur: Hook (0–2.5 s) → masalah (2.5–8 s) → **step 1/5 … 5/5** → **bonus** → CTA (±80 s).

## 3. Teks dan cara ia keluar

| Elemen | Rupa | Masuk | Keluar | Kedudukan (1080×1920) |
|---|---|---|---|---|
| **Sari kata** | Sentence case (huruf kecil biasa), putih #EEEDEE, tebal (Bold 700), **tiada outline**, bayang sangat lembut. Ayat pendek 2–5 perkataan. | **Taip huruf demi huruf** (≈2 huruf/bingkai ≈ 60 huruf/s), bermula pada perkataan yang disebut. | Hilang serta-merta bila ayat seterusnya mula (potong keras). | Tengah dada, y ≈ 1030–1100. Bila ada panel, betul-betul di atas panel. Kadang-kadang di atas kepala, y ≈ 215–300. |
| **Kata kunci** dalam sari kata | Perkataan sama, warna **biru #4F74E3**. Satu kata kunci setiap ayat. | Ikut taipan. | Ikut sari kata. | Dalam baris. |
| **Kata italik serif** | Satu perkataan "emosi" dalam **serif italik** biru lembut #708BE2 (cth *lawa-lawa*, *edit*, *Pro*). Diletak senget ke kanan/bawah baris utama. | Fade-in ±4 bingkai, selepas baris utama siap ditaip. | Ikut sari kata. | Offset +40 px ke bawah dari baris. |
| **Perkataan gergasi** | Huruf kecil, **Black/Heavy 900**, ±190 px, hitam #0E0E11 atau biru #4C7BFD. Contoh: `install`, `wajib`. | **Bucu viewfinder** (4 sudut "⌜ ⌝", nipis, putih) muncul ±6 bingkai dulu, kemudian perkataan **fade-in 2 bingkai**. | Fade-out ±5 bingkai. | Di atas kepala, y ≈ 230–330, **di belakang kepala**. |
| **Tag bab** `step 1 / 5` | Font mono kecil (±22 px), kotak gelap #242424 bucu bulat 6 px; nombor semasa biru. Kemudian `bonus · usage`. | Muncul serta-merta pada awal bab. | Kekal sepanjang bab. | Kiri atas, x ≈ 68, y ≈ 285. |
| **Bar kemajuan** | Garis nipis 3 px merentas atas: bahagian siap biru #4779FE, baki kelabu nipis. | Bertambah ikut bab. | Kekal. | y ≈ 255, x 50–1030. |
| **Panel "app" gelap** | Tetingkap gelap #262623, bucu bulat ±28 px, bayang lembut. Isi: senarai folder dengan baris terpilih biru, kotak prompt (teks **ditaip** dengan kursor `|`), "Plan usage" dengan bar kemajuan, harga ($20 / RM99) di kanan dalam biru. | **Slaid naik dari bawah** ±4 bingkai (ease-out), tanpa lantunan. | Slaid turun / fade ±4 bingkai. | Separuh bawah, y ≈ 1160–1520, lebar ±88% skrin. |
| **Pil putih condong** | Kad putih bucu bulat, **senget −3°**, teks hitam tebal + satu kata italik serif biru (cth "Code = pandai *edit*", "Siap dalam 20–30 minit"). Bayang lembut. | Slaid naik ±40 px + fade-in, ±5 bingkai. | Fade. | Paras peha/bawah, y ≈ 1250–1350. |
| **Kad notifikasi CTA** | Pil gelap dengan avatar kecil, teks biru ditaip ("Dah try, siap!"), kemudian kad "Share link, biar aku tengok" + nama fail mono. | Taip; tukar kad dengan **cross-fade 3 bingkai**. | — | Bawah, y ≈ 1350–1450. |
| **Butang CTA** | Pil **oren #FE5934**, teks putih tebal "Share hasil kau". | Fade/pop kecil. | Kekal hingga habis. | Bawah tengah, y ≈ 1480. |
| **Ikon/logo kecil** | Kad logo gelap kecil (cth "HyperFrames free") di kiri atas. | Pop kecil. | Fade. | Kiri atas di bawah tag bab. |

Prinsip: **satu idea, satu grafik**. Panel muncul hanya bila diterangkan, dan sari kata naik
ke atas panel supaya tak bertindih.

## 4. Font

| Peranan | Rujukan (anggaran) | Guna dalam GAC |
|---|---|---|
| Sari kata, pil, panel | Sans geometri moden, Bold | **Plus Jakarta Sans Bold** (`assets/fonts/PlusJakartaSans.ttf`) |
| Perkataan gergasi / hook | Grotesk sangat tebal, huruf kecil | **Inter Black** (`assets/fonts/Inter.ttf`, berat 900) |
| Kata italik | Serif italik halus (gaya Instrument Serif Italic) | **Belum ada dalam skill.** Perlu tambah font serif italik |
| Tag bab, nama fail | Monospace | JetBrains Mono (sistem) |

## 5. Warna

| Peranan | Hex |
|---|---|
| Aksen utama (kata kunci, perkataan gergasi, bar) | **#4C7BFD** (julat #4779FE – #4F74E3) |
| Italik serif | #708BE2 |
| Teks putih | #EEEDEE |
| Teks gelap / perkataan gergasi hitam | #0E0E11 |
| Panel & tag | #262623 / #242424 |
| Logo asterisk (jenama) | #D9765A |
| Butang CTA | **#FE5934** |

**Gred video**: hangat dan lembut. Purata RGB ±180/155/138 (merah melebihi biru ±40), ketepuan
rendah (±0.25), hitam penuh (p1 ≈ 1) tetapi putih tidak dipotong (p99 ≈ 225–228, highlight
lembut). Rasa "krim/peach". Jangan tambah kontras kuat.

## 6. Bunyi

- **Tiada muzik latar.** Antara ayat, bunyi jatuh hampir senyap (±−46 dB).
- Suara dibersihkan kuat: spektrum ada takuk tetap pada ±5–6 kHz dan ±9 kHz (kesan *noise reduction/enhance*).
- Dimampatkan kuat: **−14.5 LUFS, LRA 2.4 LU, puncak −1 dB**. Suara rata dan dekat.
- Kesan bunyi: **sangat sedikit dan halus**. Contoh yang jelas: "tik" nada tinggi (±11–12 kHz) sejurus sebelum pil muncul (±63.6 s). Tiada whoosh/ding besar yang ketara. *(Keyakinan sederhana: kesan bunyi yang sangat perlahan mungkin terlepas.)*

## 7. Resipi dalam GAC

Semua ciri Gaya 1 kini disokong oleh `scripts/gaya.py` (dipanggil oleh build.py).

Profil gaya: salin profil peserta, tukar dua nilai sahaja (nama/CTA/perkataan kekal milik peserta):
```json
{"warna": "#4C7BFD", "font": "jakarta"}
```
Timeline (semua masa = masa video asal, seperti biasa):
```json
{
  "profile": "profile_gaya1.json",
  "look": "warm",
  "auto_sfx": true,
  "subtitles": {"words": "v.words.json", "style": "type", "y": 1300, "max_words": 4,
                "emphasis": ["satu kata kunci setiap ayat"], "italic": ["perkataan emosi"]},
  "segments": "potong setiap jeda > 0.12 s, tinggal ±0.05 s; zoom bergilir 1.0 / 1.15 / 1.3",
  "chapters": [[4.0, "step 1 / 3"], [25.0, "step 2 / 3"], [60.0, "step 3 / 3"], [90.0, "bonus · tips"]],
  "chapters_total": 4,
  "elements": [
    {"type": "hook2", "cover": true, "t": [0, 3.8], "kicker": [["Ramai", 0.08], ["orang", 0.8], ["ingat", 0.98]], "big": "untung?"},
    {"type": "bigword", "style": "gaya1", "t": [10.8, 12.3], "text": "boros"},
    {"type": "uipanel", "t": [16.0, 23.6], "title": "Bila duit dalam akaun",
     "items": ["Nampak barang cantik", "Ada promosi", "Ada duit lebih"], "select": [[16.0, 0], [18.4, 1], [20.4, 2]]},
    {"type": "uipanel", "t": [40, 44], "title": "Akaun GAP", "rows": [["Pembelian minimum", "RM100"]]},
    {"type": "uipanel", "t": [50, 56], "title": "Nota", "typed": "Teks ini ditaip huruf demi huruf"},
    {"type": "pill", "t": [26.0, 29.0], "parts": [["Siap dalam ", "n"], ["20–30 minit", "i"]]},
    {"type": "cta", "style": "button", "t": [140, 151], "text": "Isi borang di bawah"}
  ]
}
```
Nota:
- `hook2.kicker`: senarai `[perkataan, masa disebut]` (ambil dari `v.words.json`). Perkataan bertukar
  dari pudar ke penuh tepat pada masanya. `"ink": "dark"` untuk latar cerah (teks hitam macam rujukan).
- `hook2` dan `bigword` gaya1 diletak **di belakang kepala secara automatik** (`"behind": true` lalai):
  topeng orang (U²-Net human seg, ±176 MB, dimuat turun sekali ke `~/.cache/gac/models/`) mencari
  atas kepala dan perkataan bertindih ±38% tingginya. Beri `"y"` untuk kedudukan sendiri,
  `"behind": false` untuk di depan.
- Sari kata `"style": "type"` naik sendiri ke atas panel/pil yang sedang dipapar.
- Kesan bunyi: `tick` halus untuk perkataan gergasi/panel/pil, `click` untuk butang. Hook tiada bunyi.
- Panel maksimum 820 px lebar (dalam zon selamat x 130–950).
- Kata kunci dalam `uipanel.items` mengikut masa `select` (masa asal).

## 8. Had yang masih ada
- Kad notifikasi CTA bertaip ("Dah try, siap!") dan kad logo kecil belum dibuat: guna `uipanel` dengan `typed`.
- Kata italik dalam sari kata diletak dalam baris (rujukan kadang-kadang letak senget di bawah baris).
- Topeng orang dibuat setiap bingkai hanya semasa elemen "behind" dipapar. Tangan yang naik ke atas
  kepala juga akan menutup teks (sama macam rujukan).
- Gred `warm` dibuat untuk footage biasa. Footage yang sudah kuning akan jadi lebih kuning, jadi semak bingkai.
