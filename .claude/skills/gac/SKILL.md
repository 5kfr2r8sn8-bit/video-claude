---
name: gac
description: "GAC - make 'gaya nota' tip videos (frosted glass note card over B-roll, no talking needed; triggers on 'gaya nota', 'video nota', 'buat nota') and edit a Public Gold dealer's raw talking-head phone video into a clean TikTok/Reels video: transcribes the Malay speech itself (Whisper), cuts silences, adds a hook cover, sentence captions, big words, info cards, counters, checklists, phone mockups, product photos and B-roll, then a CTA, all in the dealer's own colour and font, and checks every frame against the TikTok safe zone before delivering. Works in claude.ai chat and in Claude Code. Use whenever a Public Gold dealer uploads a video (MOV/MP4) and asks to edit it, add sari kata/captions, hook, effects or anything TikTok/Reels, or says 'GAC', even if they don't name the skill."
---

# GAC: edit video dealer Public Gold

**Aturan untuk SEMUA video (edit biasa dan gaya Nota), tanpa kecuali:**
1. **Plan dulu** → tunggu jawapan "ok" atau pembetulan.
2. **Preview** (`--preview 8`, hantar videonya + gambar frame) → tunggu "ok" atau pembetulan.
3. Baru **render penuh**, semak, kemudian hantar.
Never skip a step, even when the request looks simple or they say "terus buat": a short plan and a
preview cost seconds; a wrong full render costs minutes and their trust.

The participant is a Public Gold dealer, often new to editing and to Claude. Talk in casual,
friendly Malay with short sentences and no jargon (say "semakan", not "QA"; "sari kata", not
"subtitles"). The only thing they must give is the video. Everything else is optional and has
a fallback, so never block on missing material.

Scripts live in `scripts/` and always run through `scripts/run.sh`, which installs what it
needs the first time (claude.ai sandbox: pip; Mac: a private venv with its own ffmpeg).

```bash
R=<this skill dir>/scripts/run.sh
bash $R analyze.py VIDEO /tmp/an                      # size, duration, pauses, /tmp/an/sheet.jpg (1 frame/s)
bash $R transcribe.py VIDEO /tmp/v --profile P.json   # -> /tmp/v.srt + /tmp/v.words.json (word times)
bash $R srt.py /tmp/v.srt                             # numbered lines with times, for planning
bash $R build.py timeline.json OUT.mp4 --preview 8    # quick check of the first 8 s
bash $R build.py timeline.json OUT.mp4                # full render + frame sheet + safe-zone check
```

Paths: in claude.ai, uploads are in `/mnt/user-data/uploads/`, finished files go to
`/mnt/user-data/outputs/` (then share them with the user). Work in `/tmp/gac/`. In Claude Code,
keep everything in the user's own video folder and never overwrite their files.

## 1. Profil (once per participant)
Look for `gac_profile.json` (uploads, the working folder, or `~/.config/gac/profile.json`).
If there is none, ask these in ONE short message, with defaults so they can just say "ok":
1. Nama + ID dealer (shown only if they want it on screen)
2. Warna utama: emas, biru, hijau, marun, ungu, putih, or a hex code (default emas)
3. Font: Montserrat (default, tegas), Jakarta (moden), Inter (kemas)
4. Penutup (CTA): `komen` (e.g. "Komen EMAS"), `whatsapp` (asks for the number), `pinned`
   ("Rujuk pinned video saya"), or their own sentence
5. Perkataan khas Whisper should know: team name (e.g. G100), mentor's name, product names
Save it like this, and in claude.ai give the file back as an output with one line:
"Simpan fail ni. Lain kali upload sekali dengan video, tak payah jawab lagi."
```json
{"nama": "Aina", "id_dealer": "PG0xxxxx", "warna": "biru", "font": "montserrat",
 "cta": {"jenis": "komen", "teks": "Komen EMAS untuk info"},
 "perkataan": ["G100", "Tuan Shafie"], "betulkan": {"cloud": "Claude"}}
```
`betulkan` is filled over time: when the participant corrects a word Whisper keeps getting
wrong, add it so it is fixed automatically next time. The accent colour is applied
everywhere by the build (`"gold"`/`"yellow"` in a timeline both mean the profile colour).

## 2. Faham video
Run `analyze.py` and view `sheet.jpg`. Note faces, anything burned in (CapCut captions, name,
logo) and where the speaker holds products. Burned-in captions → do NOT add sari kata, keep
zoom ≤ 1.10, and keep cards out of that band.

## 3. Transcribe
If the participant gave an SRT (CapCut export), use it. Otherwise run `transcribe.py` with the
profile (it adds their words to Whisper's vocabulary and applies their `betulkan`). First run
in a chat downloads the model (~1.6 GB, about 10 s) and then takes roughly a third of the video
length. Fix obvious mishearings yourself from context (e.g. "Public Go" → "Public Gold").

## 4. Plan, then wait
Show ONE message with:
- the transcript as numbered lines (the `unsure` words in **bold**, ask them to check),
- 2–3 hook options (short, from their own words, one key word in the accent colour),
- a table of suggested visuals, one row per key idea:

| Masa | Ayat | Cadangan | Kalau ada, lebih cantik |
|---|---|---|---|
| 0:05 | "buka akaun GAP" | 📱 Mockup telefon | Screenshot app GAP. Tiada → kad teks |
| 0:12 | "RM100 sebulan" | 🔢 Kaunter RM0 → RM100 | — |
| 0:18 | "dapat 1 gram" | 🪙 Gambar produk | Gambar dinar 1g. Tiada → kad teks/ikon |

- **Efek pilihan** (always include this section, even if you suggest none), in three short groups,
  one line each, so they see everything GAC can do:
  - Efek GAC: Glass Type, Chart Grow, Checklist, Zoom Cut, Phone Mockup, Pull Back Reveal, Digital Zoom (`"effects"`)
  - Peralihan: flash, whip, koyak kertas (`"fx"`: flash / whip / tear)
  - Penekanan: freeze frame dengan tulisan besar, glow di tepi skrin, babak ✗/✓ compare (`freeze` segment, `"fx": glow`, compare scene)
  Mark the 1–3 you recommend for this video with the sentence and time they would sit on, and ask
  which ones they want. If they ask "efek apa ada?", show this list.
- the ending (their profile CTA).

Then stop and wait for "ok" or changes. Material is always optional: if they say "takpe,
teruskan", use the fallback. Suggest material in a way that teaches ("Kalau ada screenshot app
GAP, video nampak lebih real").

How to choose visuals (aim for one every 4–8 s, face visible in between):
- number they say (RM, gram, tahun, %) → `counter`
- list of 2–4 points ("pertama… kedua…") → `checklist`, one tick per spoken point
- one strong word or phrase → `bigword` (max 3–4 per video)
- "X vs Y", before/after → `compare` scene
- app, website, screenshot → `screen` scene (phone mockup) with their screenshot or recording
- product named (dinar, goldbar, GAP) → their photo as `image`, or a `card`
- extra clips they upload → B-roll `screen` scene with `"frame": "full"` (1–3 s, voice keeps playing)
- price trend → `chart` only with numbers or a chart they give; always show its source

Optional effects (top-level `"effects"`, same original times, drawn on the video itself under
the captions; captions hide under the panels). Offer them in the plan as "efek pilihan":
- `glass`: frosted glass panel, the text types itself ("Glass Type")
- `chart`: bars grow + a line draws (decorative unless they give `values`)
- `checklist`: card whose boxes tick one by one (`at` = the spoken time of each item)
- `zoomcut`: 3–4 quick zoom cuts on the face (`zooms`)
- `phone`: phone slides in with their screenshot (`image`) or a short list
- `pullback`: the video shrinks and turns out to be playing inside an app window (`window`, `title`, `items`, `percent`)
- `digitalzoom`: slow smooth zoom to the face (`to`)
Give each effect at least ~1.5 s; keep 1–2 effects per 15 s so the face stays the focus.

## 5. Build
Colour: keep the phone's **original colours** (no `"look"`, the default). iPhone HDR is converted
automatically so it never looks washed out. Only if they ask, offer `"look": "premium"` (neutral,
a bit richer) or `"bright"` (dim indoor footage); never warm/yellow the picture on your own.
Write `timeline.json` (format: `references/timeline.md`), with `"profile"` pointing at the
profile file. Rules that make it look professional:
- **Cut only in real silence.** Use the word times; build.py warns `cut ... is not in a real
  pause`, fix every one. Drop long pauses (> ~0.35 s), false starts and fillers (aa, emm).
  Alternate zoom 1.0 and 1.05–1.10 between segments.
- **Hook = cover.** `"type": "title", "cover": true` so it is fully visible on frame 1; above
  the head, never on a face.
- **Sari kata**: `"subtitles": {"words": "v.words.json", "srt": "v.srt", "emphasis": [...]}`.
  One sentence per caption, split evenly, no one-word leftovers. A whole sentence's captions
  hide while a big word, card or scene that says the same thing is on screen.
- **Visual on the word.** Each element starts on the spoken word (use word times), not before.
- Keep within 2–3 colours: white, the profile colour, red only for warnings, green only for ✓.
- Never put on screen a number, price or claim the participant did not say or give.
- Sound: big words get a soft ding, cards a pop, counters ticks (built in, no music).
- End with their CTA (`cta` element, or `"style": "minimal"` with `"icon": "comment"`).

## 6. Semak sebelum hantar (always)
1. Always render `--preview 8` first and SEND that preview to them (plus the frames sheet it
   prints). Wait for "ok" or changes before the full render; a full render takes minutes, a
   preview seconds.
2. After the full render, view the frame sheet it prints (`*_frames.jpg`: 1 frame/s with red
   lines at y 220 / 1500 and cyan lines at x 120 / 960). Check every tile: text inside the
   lines, no text on a face, no caption under a big word, hook visible on frame 1.
3. Read the build output: `"safe_zone": "BERSIH"` is required. `WARNING safe zone ...` names
   the times; move or shrink that element and render again. Also fix every
   `WARNING caption too wide` / `cut ... not in a real pause`.
4. For long or heavily cut videos, re-transcribe the final and compare with the plan (catches
   doubled or missing words).
Only then deliver: the video plus a short Malay list of what was added and 1–2 things to check.
Always hand the finished video over as a file they can download (in claude.ai: save it to
/mnt/user-data/outputs and present it). Rendering in a chat is slow: after the preview is approved,
do ONE full render; if a check fails, fix and render once more at most, then deliver and say
honestly what is still not perfect. Never end a reply with "belum sempat semak".

## Gaya Nota (no talking needed)
For tips and step-by-step posts: a see-through glass note card over their own B-roll (a scenic clip
or a photo) so the scenery still shows, a title, steps that appear one by one with a marker on each
step name, and a closing line. No CTA pill and no sound effects by default (they add music on
TikTok); add them only if asked (`"show_pill": true`, `"sfx": true`). They only give a B-roll and the
text (or a topic: then draft the steps with them; never invent numbers they did not give).
Optional voice-over or a music file they own (`"audio"`).
Ask in the plan which look they want (defaults in brackets), so every participant's notes differ:
- Font tajuk: Playfair (serif, default) / Montserrat / Jakarta / Inter → `"font_tajuk"`
- Font teks: Montserrat (default) / Jakarta / Inter → `"font_teks"`
- Warna kad: krim (default) / putih / hitam / kelabu / any hex → `"warna_kad"`
- Warna huruf: auto (dark on light cards, white on dark cards) / hitam / putih / hex → `"warna_huruf"`
- Kelutsinaran kad: `"tint"` 0.30 default (lower = more scenery, higher = easier to read)
The marker on step names uses their profile colour.
Always in this order, waiting for their answer at each step:
1. **Plan**: show the title, every step (exact text), the closing line, the look choices above, which
   B-roll you will use, their colour, and the length (about 3 s per step + 9 s). Ask "ok?".
2. **Preview**: render `--preview 8`, send it with one still frame of the full card (the
   frames sheet it prints), ask for changes.
3. **Full render** only after they say ok, then the usual checks.
```bash
bash $R nota.py nota.json OUT.mp4 --preview 8     # spec format is at the top of scripts/nota.py
```
Steps appear every ~3.2 s unless given times; fonts shrink automatically so the card fits the safe
zone. Use `**bold**` for the key number. Check the frame sheet it prints before delivering.

## Had (say so when relevant)
- In chat: keep videos short (≤ 2 minutes) and 1080p; 4K or long videos may fail to upload or
  render slowly. Rendering takes about 1–2 minutes per 30 s.
- Whisper can mishear names and slang; that is why the transcript is shown first.
- No background removal, green screen, AI images or stock footage. Visuals come from their
  own photos, screenshots and clips, plus the cards, icons, counters and charts drawn here.
