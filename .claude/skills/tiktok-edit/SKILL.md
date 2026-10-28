---
name: tiktok-edit
description: Edit video TikTok (9:16) daripada rakaman mentah — potong jeda senyap, sari kata automatik (Bahasa Melayu lalai) dan tajuk hook di bahagian atas, kemudian simpan ke folder final/. Guna bila pengguna minta edit, potong, letak sari kata/caption/subtitle atau hook pada video TikTok/Reels/Shorts.
---

# Edit video TikTok

Skrip: `.claude/skills/tiktok-edit/scripts/tiktok_edit.py` (jalankan dengan `.venv/bin/python` dari akar repo).
Semua ayat kepada pengguna dalam Bahasa Melayu.

## 0. Persediaan (sekali setiap sesi baharu)

```bash
[ -x .venv/bin/python ] || (python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt)
.claude/skills/tiktok-edit/scripts/setup_models.sh small   # langkau sendiri jika model sudah ada
```

Model Whisper diambil dari GitHub Releases (sherpa-onnx) kerana Hugging Face disekat dalam
persekitaran ini. Jika muat turun gagal, beritahu pengguna hos yang disekat — jangan teka sari kata.

## 1. Cari video

Video mentah dalam `rakaman/`. Jika tiada, video mungkin dalam GitHub Release — muat turun aset
release ke `rakaman/`. Jika ada lebih dari satu video dan pengguna tidak sebut yang mana, tanya.

## 2. Prepare — potong senyap, 9:16, transkrip

```bash
.venv/bin/python .claude/skills/tiktok-edit/scripts/tiktok_edit.py prepare rakaman/<video>.mp4
```

Hasil dalam `build/<nama>/`: `cut.mp4`, `subs.srt`, `meta.json`.

Pilihan berguna:
- `--fit blur` untuk video landskap/produk yang tidak patut dipotong tepi (lalai `crop` memenuhkan skrin).
- `--silence-db -40` jika suara perlahan tetapi terpotong; `-30` jika bunyi latar bising tidak dipotong.
- `--min-silence 0.5` / `--pad 0.12` untuk potongan yang kurang agresif.
- `--lang en` (atau `id`, dsb.) jika video bukan Bahasa Melayu. `--no-subs` jika tidak mahu sari kata.

## 3. Semak sari kata (WAJIB)

Baca `build/<nama>/subs.srt` dan betulkan teks terus dalam fail itu:
- ejaan Bahasa Melayu, nama jenama/produk, singkatan, perkataan yang Whisper salah dengar;
- buang perkataan pengisi yang mengganggu (emm, aaa) jika ia muncul;
- **jangan ubah cap masa**, dan kekalkan setiap baris pendek (≈ 3 perkataan).

Jika ada perkataan yang tidak pasti, senaraikan kepada pengguna dan bukan meneka.

## 4. Tajuk hook

Guna teks hook yang pengguna beri. Jika tiada, cadangkan 3 pilihan berdasarkan transkrip
(pendek, ≤ 8 perkataan, timbulkan rasa ingin tahu atau manfaat jelas) dan minta pengguna pilih.

## 5. Render ke final/

```bash
.venv/bin/python .claude/skills/tiktok-edit/scripts/tiktok_edit.py render build/<nama> --hook "Teks hook"
```

- Lalai: hook dipapar sepanjang video. `--hook-secs 3` untuk 3 saat pertama sahaja.
- `--upper` untuk sari kata huruf besar; `--out final/nama.mp4` untuk nama fail lain.
- Hasil: `final/<nama>_tiktok.mp4` (1080×1920, H.264, audio −14 LUFS).

## 6. Semak hasil

Ambil satu bingkai dan lihat sendiri sebelum lapor siap:

```bash
ffmpeg -v error -y -ss 2 -i final/<nama>_tiktok.mp4 -frames:v 1 -vf scale=540:-1 build/<nama>/semak.png
```

Pastikan hook tidak menutup muka/produk dan sari kata boleh dibaca. Lapor kepada pengguna:
tempoh asal → tempoh akhir, berapa saat senyap dibuang, dan pembetulan sari kata yang dibuat.

Fail dalam `final/` dan `build/` tidak masuk git (lihat `.gitignore`); untuk serah video kepada
pengguna, muat naik sebagai aset GitHub Release atau hantar fail terus.
