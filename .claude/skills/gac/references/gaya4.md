# Gaya 4 = "Gaya Kelas Emas" (skrin kecil + frame info, sebelah-menyebelah, ada pergerakan)

Nama dipilih pengguna: **Gaya Kelas Emas**. Istilah umum: split-screen explainer / picture-in-picture.

Gaya kegemaran pengguna (Rakaman7, 2026-11-03): "saya suka sangat, tak perlu fokus muka kita penuh satu skrin".
Skrip: `scripts/sebelah_hf.py` (HyperFrames). Contoh lengkap: `references/sebelah_contoh.json` (`build/hf/r7lr/spec.json`).

## Rupa
1. **Mula skrin penuh** (±0–6 s): penceramah penuh skrin + kad hook kaca hitam emas di atas kepala.
2. **Video mengecil (animasi 0.9 s)** ke **petak kiri** (9:16, bingkai emas, bucu bulat), **frame tulisan masuk dari kanan**.
3. Frame kanan (kaca hitam, tepi emas): tag emas "SEBAB n / N" + titik kemajuan, tajuk serif dengan kata kunci emas,
   poin ✓ / ✗ / • muncul satu-satu ikut sebutan (cth Sebab 7: ✅ Beli ✅ Simpan ✅ Jual ✅ Keluarkan emas fizikal).
4. **Pergerakan sepanjang video:** petak kiri "pop" setiap bahagian baru, video zoom perlahan dalam petak, frame kanan slaid masuk.
5. **B-roll dalam petak kiri** (suara terus berjalan): klip video (`"video"`), gambar (`"img"`), gambar penuh tanpa potong
   (`"fit": "contain"`, latar kabur), `"pos"` untuk anjak potongan.
6. Sari kata frasa di bawah dua-dua petak (tak tutup muka), kata kunci emas. Latar: video sendiri dikaburkan + sinar emas.
7. Penutup: logo Public Gold + butang emas (cth "📌 Rujuk video pin", "Isi borang sign up ↓").

## Peraturan
- Semua dalam zon selamat TikTok: x 130–950, y 236–1340 (telefon tinggi potong tepi, caption TikTok tutup bawah ±1360).
- Tiada tulisan atas produk; tiada rambut/aurat wanita dalam B-roll; muka tak ditutup.
- "Lighting HD" bila diminta: `hqdn3d,eq=gamma=1.10:brightness=0.025:contrast=1.06:saturation=1.06,curves,unsharp`.
- Video panjang: potong segmen satu-satu (`build/rakaman7/cut_seg.py`) — filter_complex sekali gus kehabisan memori.
- Pembetulan kecil pada satu bahagian: render bahagian itu sahaja (duration pendek, aset dikongsi) dan sambung dengan
  video penuh (ambil audio dari video penuh). Jangan jana `sfx.wav` dalam folder yang berkongsi aset (ia ditimpa).
- **Latar putih kosong** (pengguna, Rakaman8: "cuba warna putih, tak nak bercorak"): `"bg": "white"` dalam spec
  (atau mana-mana warna CSS). Panel tulisan & kotak sari kata kekal gelap supaya kontras. Contoh: `build/hf/r8/spec.json`.
- Bahan pengguna terbaik (Rakaman8): klip selfie angkat 1 kg sebelah tangan (hook skrin penuh, perlahankan `setpts=1.36*PTS`
  supaya jongkong kekal dalam bingkai) + klip angkat jongkong dari dulang merah; gambar rumah untuk ayat "rumah banglo".
- **Ilustrasi dalam petak kiri** (pengguna, Rakaman8: "nak ilustrasi banyak ditayang, bukan video saya bercakap"):
  broll `{"t":[a,b],"illus":{...}}` dengan `kind`:
  - `bars`: `title`, `bars` `[[label, nilai, teks]]`, `note`;
  - `count`: `title`, `prefix`, `to`, `sub`, `note`;
  - `icon`: `icon` `shield|house`, `title`, `tags` `[["x"|"", teks]]`; "x" = coret.

  Isi setiap jurang bercakap > 2 s dengan gambar / klip / ilustrasi. Tandakan "Anggaran" pada angka sendiri.
