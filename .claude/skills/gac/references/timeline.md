# timeline.json format

All times are ORIGINAL video times in seconds (as seen in the raw upload,
the contact sheet and the SRT). build.py maps them onto the cut video.

`"canvas"`: "auto" (default, follows the source), "portrait" (1080x1920) or "landscape" (1920x1080).
Default y positions below are for portrait and scale automatically for landscape;
give explicit `x`/`y` in canvas pixels when you need precise placement.

```json
{
  "video": "/mnt/user-data/uploads/clip.mov",
  "profile": "/mnt/user-data/uploads/gac_profile.json",
  "enhance": true,
  "auto_sfx": true,
  "sfx_gain_db": -14,
  "segments": [
    [0.95, 4.45, 1.0],
    [4.45, 8.20, 1.10],
    {"freeze": 16.6, "dur": 1.0, "text": "PELUANG!", "color": "yellow", "zoom": 1.1, "outline": false},
    [16.33, 20.46, 1.10]
  ],
  "subtitles": {"script": "words of the exact script with *key* words starred", "max_words": 5, "y": 1460},
  "elements": [ ... ],
  "fx": {"tear": [13.25], "whip": [8.55], "flash": [4.45], "glow": [[16.33, 20.46, "green"]]},
  "sfx": [[12.0, "coin"]]
}
```

## segments
`[start, end, zoom]` keeps that part of the source. Drop pauses/stumbles by leaving
gaps. Alternate zoom 1.0 and 1.08–1.12 between segments for the punch-in feel.
If the video has burned-in captions, keep zoom ≤ 1.10 (captions scale with zoom).

A 4th item shows the Iman document during that segment (see iman-style.md):
`[a, b, zoom, "doc"]` floats it over the untouched video; `[a, b, zoom, "split"]` crops the
face to one side and shows the paper panel on the other. Crops always follow the
detected face and never stretch the picture.

`{"freeze": t, ...}` inserts a still of time t (silent, with impact sfx), darkened, with
big text (`"text_y"` moves the text; use it to keep a burned-in name visible). `"outline": true` tries a body cut-out + white outline + text-behind-subject
using OpenCV GrabCut. It only works on plain, uncluttered backgrounds and is often
rough: check the frame and turn it off if edges look bad.

## subtitles (only when the video has NO burned-in captions)
Best: `{"words": "video.whisper.words.json", "srt": "capcut.srt", "emphasis": ["emas", "GAP"], "fix": {"kat": "kan"}, "drop": ["aa"]}`
uses Whisper's per-word timing (from `transcribe.py`) grouped by SRT line, so a caption never runs across two sentences
(without `"srt"`, it breaks at punctuation and capitalised sentence starters). Each sentence is split evenly by `max_words`.
Words cut away or under a motion scene are skipped. `DEBUG_SUBS=1` prints the captions.
Next best: `{"srt": "path/to/file.srt", "max_words": 4, "y": 1640}` uses each SRT line's own timing.
To clean fillers or fix spelling, use `"lines": [[start, end, "text with *key* words"], ...]` instead
(copy times from `srt.py`). Subtitles are hidden automatically while the document is shown.
Needs the user's exact script. Words are spread over detected speech by duration, so
timing is approximate (±0.5 s). Current word turns yellow; `*word*` is always big yellow.
Omit this key entirely when captions are already burned in.

## elements
Common keys: `type`, `t: [start, end]`, optional `x`, `y` (centre, px), `sfx` (name or false),
`pop` (false = no pop-in).

| type | keys | default y | auto sfx |
|---|---|---|---|
| title | `"cover": true` = fully visible from frame 1 with no pop-in (the user uses the hook as the TikTok/Reels cover; put it above the head, y ~325). `lines`: [[["TEXT","white"],["WORD","red"]], ...], `size`(116), `glow`, `style`:"clean" (Iman: no outline, soft shadow, size 96) | 330 | whoosh |
| bigword | `text`, `color`, `size`(150) | 1200 | impact |
| card | `text`, `icon`(check/cross/up/down/calendar/phone/warning), `color`, `sub`, `sub_color` | 1230 | pop |
| chart | `title`, `sub`, `dir` up/down (decorative line, not real data) | 1170 | whoosh |
| checklist | `items` [..], `icon` check/cross, `gap`(0.9 s) | 1170 | pop each |
| counter | `to`, `from`, `prefix`, `suffix`, `decimals`, `label`, `count_time` | 1170 | tick |
| image | `path`, `width`(620) floating card with white frame | 760 | whoosh |
| lowerthird | `name`, `title`, `color` | 1240 | whoosh |
| cta | `text` gold pill with dark text (`"color": "green"` for the old WhatsApp-green pill) | 1235 | coin |
| disclaimer | `text` small yellow box | 300 | click |

Colours: white, yellow, green, red, gold, or [r,g,b]. Keep to 2–3 per video.

## doc
Iman-style document, see `iman-style.md`: `{"icons": "ikon", "size": 50, "blocks": [...]}`.

## layout (portrait 1080×1920)
- Title / disclaimer: top band y 200–420 (above the head).
- Face: roughly y 300–1000. Do not park cards here for more than ~1 s.
- Cards, charts, counters, checklists: chest band y 1050–1330.
- Captions/subtitles: y 1350–1600. Keep cards out of this band.
- Images: y 600–900 for short moments only (they cover the face).

## fx
- `tear`: torn-paper wipe centred on that time (use on a cut).
- `whip`: 4-frame horizontal motion blur on a cut.
- `flash`: 2-frame white flash.
- `glow`: soft coloured edge glow for a range.

### chart scene (real price line, animated)
`{"type":"chart","backdrop":"video","dim":0,"data":"/abs/path/data.json","year0":2016,"window":[4,6.6],
"zoom_to":[0,10],"zoom_at":..,"draw_at":..,"draw_time":2.2,"source":"Data: goldprice.org (RM/oz)",
"lines":[{"at":..,"parts":[["Dalam ","white"],["10 TAHUN","gold"]],"size":96,"until_at":..}]}`
Only from a chart the user supplies: digitise its line into `[[years_from_year0, value], ...]` (pick the
line colour's pixels, map axis pixels to values) and always show the source. No y-axis numbers are drawn.
A window of ~2.5 years shows "naik & turun"; the full window shows the long-term trend.

### Backdrop options for scenes
`"backdrop":"video"` + `"dim"`: 0.5 = Gaku video (bokeh + 50% black); 0 = Gaku bokeh (blur only; scene
text gets a soft dark halo automatically). `"hold"` works on bokeh scenes too (freezes the blurred frame).
cta `"style":"minimal"` takes `"icon":"comment"` (speech bubble, "komen di bawah"), `"heart"` ("tekan like") or `"none"` (text-only info pill, e.g. "± RM600 / gram (anggaran hari ini)").

### swap scene (product ladder, one at a time)
`{"type":"swap","backdrop":"video","dim":0,"h":520,"y":0.42,"items":[{"at":45.3,"image":"produk/goldbar_5g.png","label":"5G"}, ...]}`
Each product replaces the previous in place (0.25 s cross-fade) with a big gold gram label under it. Use when the
speaker lists sizes (5g → 10g → 20g → 50g → 100g): similar-looking products need the label, and a grid makes them tiny.
Put each `at` on the spoken word. Show a big target (1kg) on its own in a separate hero scene.

### promo scene (event poster)
`{"type":"promo","backdrop":"video","dim":0.45,"poster":"posterX.jpg","poster_at":..,"hold":2.2,"poster_w":650,"top":250,
 "date":{"at":..,"text":"SABTU 17 OKT 2026 · 9:30 PAGI – 12:30 TGH"},"venue":{"at":..,"text":"..."},
 "pill":{"at":..,"text":"www.contoh.my"},"tag":{"at":..,"text":"TERHAD KEPADA 200 PAX"}}`
Poster with a gold rim, then gold caps date, white venue (2 lines max), big gold pill with dark text, spaced gold caps tag.
Everything fits x 120..960, y 230..1490 (it warns if not). Only use details printed on the poster or spoken.
Opening with several people (kids, couple): opening spec `"multi_person": true`. Separate hook clips: concat hook + main into one source first.


## Scenes (full-screen motion, voice keeps playing)
Mark a segment `[a, b, 1.0, "scene:NAME"]` and describe it under `"scenes": {"NAME": {...}}`.
Every `at` inside a scene is an ORIGINAL video time. Captions hide during scenes. Add
`"backdrop": "video", "dim": 0.5` to show the speaker's own video blurred behind the scene
(nicer than plain dark). Keep scenes 2–4 s with face segments between them.
Icons: names from the participant's `ikon/` folder, else the bundled ones in `assets/ikon/`
(`betul`, `pangkah`, `syiling`, `hadiah`, `jam`, `bulan`, `glob`); a missing icon draws a dot.

```json
"segments": [[0.0, 4.2, 1.0], [4.2, 8.0, 1.0, "scene:app"], [8.0, 12.5, 1.06], [12.5, 16.0, 1.0, "scene:vs"]],
"scenes": {
  "app":   {"type": "screen", "image": "/mnt/user-data/uploads/gap.png", "phone_at": 4.3,
            "lines": [{"at": 4.6, "parts": [["Akaun ", "white"], ["GAP", "gold"]], "size": 84}]},
  "broll": {"type": "screen", "video": "/mnt/user-data/uploads/kedai.mp4", "start": 0, "frame": "full"},
  "vs":    {"type": "compare", "title": {"at": 12.6, "parts": [["Simpan ", "white"], ["emas", "gold"]]},
            "rows": [{"at": 13.4, "icon": "pangkah", "text": "Duit habis"}, {"at": 14.6, "icon": "betul", "text": "Nilai kekal"}]},
  "rm":    {"type": "counter", "title": {"at": 20.1, "parts": [["Serendah", "white"]]}, "icon": "syiling",
            "at": 20.4, "to": 100, "prefix": "RM", "sub": {"at": 21.5, "parts": [["sebulan", "white"]]}},
  "hero":  {"type": "hero", "icon": "/mnt/user-data/uploads/dinar.png", "icon_at": 25.1,
            "lines": [{"at": 25.3, "parts": [["Dinar ", "white"], ["1 gram", "gold"]]}]}
}
```
- `screen`: phone mockup of a screenshot (`image`) or screen recording (`video`, `start`);
  `"frame": "full"` = vertical B-roll filling the screen, `"frame": "card"` = landscape clip in a rounded card.
- `compare` rows slide in on their `at`; `counter` counts up to `to`; `hero` = one big image + lines.


## effects (optional, drawn under captions)
```json
"effects": [
  {"type": "glass", "t": [9.1, 12.0], "text": "Glass Type", "y": 1150},
  {"type": "chart", "t": [28.4, 30.0], "title": "Simpanan", "values": [1, 2, 3, 5, 8]},
  {"type": "checklist", "t": [37.9, 41.0], "title": "Syarat", "items": ["A", "B", "C"], "at": [38.2, 39.4, 40.5]},
  {"type": "zoomcut", "t": [29.8, 31.3], "zooms": [1.0, 1.22, 1.45, 1.0]},
  {"type": "phone", "t": [48.2, 50.0], "image": "gap.png"},
  {"type": "pullback", "t": [23.0, 25.3], "window": "video.mp4", "title": "Langkah", "items": ["Rakam", "Edit"], "percent": 62},
  {"type": "digitalzoom", "t": [49.8, 51.0], "to": 1.3}
]
```
Times are original video times; an effect may span several segments. Panels (glass, chart,
checklist, phone, pullback) hide the captions while they show; zooms keep the captions sharp
because they act on the video only. Colours follow the profile accent.

## Gaya 1 elements (scripts/gaya.py, see gaya1.md)
| type | keys | default y |
|---|---|---|
| hook2 | `kicker` [[word, t], ...], `big`, `size`(230), `ink` light/dark, `behind`(true) | on the head top (auto, person mask) |
| bigword + `"style": "gaya1"` | `text`, `size`(210), `behind`(true) - viewfinder corners, then 2-frame fade | on the head top (auto) |
| pill | `parts` [[text, "n" or "i"(italic serif)], ...] | 1300 |
| uipanel | `title` + `typed` / `items` + `select` [[t, index]] / `rows` [[label, value]] | 1250 |
| cta + `"style": "button"` | `text` (orange pill) | 1420 |
Top level: `"chapters": [[t, "step 1 / 3"], ...]`, `"chapters_total"`, `"chapters_end"`; `"look": "warm"`; `"zoom_anchor": 0.78` (row of the frame kept fixed when a segment zooms, e.g. a burned-in caption band);
`"subtitles": {"style": "type", "italic": [...]}` (letter-by-letter captions, rise above panels/pills).
