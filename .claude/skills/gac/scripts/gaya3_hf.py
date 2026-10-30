#!/usr/bin/env python3
"""Gaya 3 (references/gaya3.md) as a HyperFrames composition: black-glass cards with gold edges above the
head, serif titles with a gold keyword, phrase captions (gold keyword) in a dark frosted box, full-screen
B-roll cutaways on a dark gold-ray background.

Usage: python3 gaya3_hf.py spec.json PROJECT_DIR      (then: npx hyperframes render -o out.mp4 in PROJECT_DIR)
spec = {
  "video": "assets/cut.mp4", "duration": 97.2,
  "band": {"top": 225, "bottom": 405},        # card band above the head (never over the face)
  "captions": {"words": "words.json", "y": 1428, "h": 140, "keys": ["emas", "boros"], "fix": {"bocu": "bocor"}},
  "scenes": [ {"t": [a, b], "kind": ..., ...}, ... ],   # times on the cut video
  "sfx_gain_db": -11, "music_db": -12
}
Card kinds (one card at a time, centred in the band; *word* = gold):
  title    {"label": "TIPS SIMPAN EMAS", "title": "Simpan Emas, *Kawal Boros*"}     serif title, words reveal
  big      {"label": "BERPOTENSI", "text": "INFLASI", "sub": "lindungi nilai"}       big gold word
  chips    {"label": "...", "items": [["v"|"x"|"", "text"], ...], "at": [..], "row": false}  dark pills with tick/cross
  gold     {"label": "MULA SERENDAH", "items": [["1 gram", "EMAS 999.9"], "atau", ["RM100", "SAHAJA"]], "at": [..]}
  bars     {"text": "KONSISTEN", "sub": "Kumpul gram emas setiap bulan"}            growing bar chart
  warn     {"text": "Duit mudah bocor?", "icon": "hourglass"}                        red warning pill
  cta      {"label": "MULAKAN SIMPANAN EMAS", "title": "bersama *Public Gold*", "pills": ["Isi borang sign up"], "at": [..]}
B-roll (full screen, voice keeps playing):
  counter  {"label": "...", "from": 1, "to": 1000, "unit": "g", "sub": "1 KILOGRAM", "at": t, "dur": 1.6}   number rolls up
  broll    {"video": "assets/clip.mp4" (optional, real B-roll), "img_w": 640, "frame": false,
            "images": ["assets/x.jpg", ...], "at": [..], "pill": "Akaun GAP", "pill_at": t,
            "logo": "assets/pg_logo.png", "logo_at": t, "tag": "Serendah RM100", "tag_at": t, "layout": "row"|"one"}
"""
import json, os, sys, html, re

def e(x): return html.escape(str(x))
def gold_words(t):   # *word* -> gold span
    return re.sub(r'\*(.+?)\*', r'<b class="g">\1</b>', e(t))

def phrases(words, fix, maxc=26, gap=0.3):
    out, cur = [], []
    for i, w in enumerate(words):
        txt = w['w']
        for a, b in fix.items(): txt = re.sub(rf'\b{re.escape(a)}', b, txt)
        cur.append((txt, w['s'], w['e']))
        nxt = words[i + 1] if i + 1 < len(words) else None
        n = len(' '.join(c[0] for c in cur))
        if nxt is None or txt[-1:] in ',.?!' or nxt['s'] - w['e'] > gap or n > maxc:
            out.append(cur); cur = []
    res = []
    for k, p in enumerate(out):
        a = p[0][1]; b = out[k + 1][0][1] if k + 1 < len(out) else p[-1][2] + 0.4
        if b - p[-1][2] > 0.7: b = p[-1][2] + 0.5          # long pause: caption leaves
        res.append((a, b, ' '.join(c[0] for c in p)))
    return res

def mark_key(text, keys):   # first whole-word key found -> gold
    for k in keys:
        m = re.search(rf'(?<![\w-]){re.escape(k)}(?![\w-])', text, re.I)
        if m: return e(text[:m.start()]) + f'<b class="g">{e(m.group(0))}</b>' + e(text[m.end():])
    return e(text)

ICON = {'v': '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="#46D18C" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        'x': '<svg width="28" height="28" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="#FF5A5A" stroke-width="3.2" stroke-linecap="round"/></svg>',
        'hourglass': '<svg width="34" height="34" viewBox="0 0 24 24"><path d="M6 3h12M6 21h12M7 3c0 5 10 5 10 9s-10 4-10 9M17 3c0 5-10 5-10 9s10 4 10 9" fill="none" stroke="#F2C14E" stroke-width="2.2" stroke-linecap="round"/></svg>',
        'down': '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M12 4v15M6 13l6 6 6-6" fill="none" stroke="#2a1600" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        'doc': '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M6 3h9l4 4v14H6z M9 11h7M9 15h7" fill="none" stroke="#2a1600" stroke-width="2.2" stroke-linejoin="round"/></svg>'}

def card_html(i, s):
    k = s['kind']; sid = f'c{i}'
    lbl = f'<div class="lbl">{e(s["label"])}</div>' if s.get('label') else ''
    if k == 'title':
        t, gold = [], False
        for w in s['title'].split(' '):   # *several words* stay gold across the word split
            m = re.match(r'^(\*?)(.*?)(\*?)([,.!?]*)$', w)   # "*Bajet*," -> gold "Bajet,"
            st, w, en = bool(m.group(1)), m.group(2) + m.group(4), bool(m.group(3)); gold = gold or st
            t.append(f'<span class="w{" g" if gold else ""}">{e(w)}</span>'); gold = gold and not en
        t = ' '.join(t)
        body = f'{lbl}<div class="serif" style="font-size:{s.get("size", 72)}px">{t}</div>' + (f'<div class="sub">{gold_words(s["sub"])}</div>' if s.get('sub') else '')
    elif k == 'big':
        body = f'{lbl}<div class="bigg" style="font-size:{min(110, int(900 / max(1, len(s["text"]))) )}px">{e(s["text"])}</div>' + (f'<div class="sub">{gold_words(s["sub"])}</div>' if s.get('sub') else '')
    elif k == 'chips':
        items = ''.join(f'<div class="chip ch{j} {m}">{ICON.get(m, "")}<span>{gold_words(t)}</span></div>' for j, (m, t) in enumerate(s['items']))
        body = f'{lbl}<div class="chips{" row" if s.get("row") else ""}">{items}</div>'
        return f'<div class="card bare" id="{sid}">{body}</div>'          # chips float without a card
    elif k == 'gold':
        parts = ''
        for j, it in enumerate(s['items']):
            if isinstance(it, str): parts += f'<div class="atau g{j}">{e(it)}</div>'
            else: parts += f'<div class="gcard g{j}"><b>{e(it[0])}</b>' + (f'<small>{e(it[1])}</small>' if len(it) > 1 and it[1] else '') + '</div>'
        body = (f'<div class="lblpill">{e(s["label"])}</div>' if s.get('label') else '') + f'<div class="grow">{parts}</div>'
        return f'<div class="card bare" id="{sid}">{body}</div>'
    elif k == 'bars':
        bars = ''.join(f'<i class="bar b{j}" style="height:{14 + j * 9}px"></i>' for j in range(7))
        body = f'<div class="bigg" style="font-size:66px">{e(s["text"])}</div><div class="sub">{gold_words(s.get("sub", ""))}</div><div class="bars">{bars}</div>'
    elif k == 'warn':
        body = f'<div class="warn">{ICON.get(s.get("icon", "hourglass"), "")}<span>{e(s["text"])}</span></div>'
        return f'<div class="card bare" id="{sid}">{body}</div>'
    elif k == 'cta':
        pills = ''.join(f'<div class="gpill p{j}">{ICON["doc"]}<span>{e(p)}</span>{ICON["down"]}</div>' for j, p in enumerate(s.get('pills', [])))
        body = f'<div class="card in">{lbl}<div class="serif" style="font-size:56px">{gold_words(s["title"])}</div></div><div class="pills">{pills}</div>'
        return f'<div class="card bare" id="{sid}">{body}</div>'
    elif k == 'counter':
        body = (f'{lbl}<div class="bigg cnt"><span id="n{i}">{s.get("from", 0):,}</span><small>{e(s.get("unit", ""))}</small></div>'
                + (f'<div class="cntsub">{e(s["sub"])}</div>' if s.get('sub') else ''))
    elif k == 'broll':
        return ''
    else:
        raise SystemExit(f'unknown kind {k}')
    return f'<div class="card" id="{sid}">{body}</div>'

def broll_html(i, s):
    st = f' style="width:{int(s["img_w"])}px"' if s.get('img_w') else ''
    imgs = ''.join(f'<img class="bi i{j}{"" if s.get("frame", True) else " free"}" src="{e(src)}"{st}/>' for j, src in enumerate(s.get('images', [])))
    extra = ''
    if s.get('logo'): extra += f'<div class="blogo"><img src="{e(s["logo"])}"/></div>'
    if s.get('pill'): extra += f'<div class="bpill">{e(s["pill"])}</div>'
    if s.get('tag'): extra += f'<div class="btag">{e(s["tag"])}</div>'
    if s.get('video'):   # real B-roll clip underneath (root-level <video>): only a soft shade + labels here
        return f'<div class="broll vb" id="b{i}"><div class="bimgs {s.get("layout", "one")}">{imgs}</div>{extra}</div>'
    return f'<div class="broll" id="b{i}"><div class="rays"></div><div class="bimgs {s.get("layout", "one")}">{imgs}</div>{extra}</div>'

def card_js(i, s):
    a, b = s['t']; k = s['kind']; L = []
    if k == 'broll':
        sid = f'#b{i}'
        L.append(f'tl.fromTo("{sid}", {{opacity: 0}}, {{opacity: 1, duration: 0.2}}, {a});')
        L.append(f'tl.to("{sid}", {{opacity: 0, duration: 0.2}}, {b - 0.2});')
        if s.get('video'):
            L.append(f'tl.fromTo("#bv{i}", {{opacity: 0, scale: 1.04}}, {{opacity: 1, scale: 1, duration: 0.25}}, {a}); tl.to("#bv{i}", {{opacity: 0, duration: 0.2}}, {b - 0.2});')
        else:
            L.append(f'tl.fromTo("{sid} .rays", {{rotation: 0}}, {{rotation: 14, duration: {b - a:.2f}, ease: "none"}}, {a});')
        at = s.get('at') or [a + 0.1 + j * 0.35 for j in range(len(s.get('images', [])))]
        for j, t0 in enumerate(at):
            L.append(f'tl.fromTo("{sid} .i{j}", {{opacity: 0, y: 60, scale: 0.85, rotation: {(-4 if j % 2 == 0 else 4)}}}, {{opacity: 1, y: 0, scale: 1, rotation: {(-2 if j % 2 == 0 else 2)}, duration: 0.45, ease: "back.out(1.6)"}}, {t0});')
        L.append(f'tl.fromTo("{sid} .bimgs", {{scale: 1}}, {{scale: 1.06, duration: {b - a:.2f}, ease: "none"}}, {a});')
        for cls, key in (('.blogo', 'logo_at'), ('.bpill', 'pill_at'), ('.btag', 'tag_at')):
            if s.get(key) is not None:
                L.append(f'tl.fromTo("{sid} {cls}", {{opacity: 0, scale: 0.6}}, {{opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2.5)"}}, {s[key]});')
        return '\n      '.join(L)
    sid = f'#c{i}'
    L.append(f'tl.fromTo("{sid}", {{opacity: 0, scale: 0.94, y: 10}}, {{opacity: 1, scale: 1, y: 0, duration: 0.25, ease: "power2.out"}}, {a});')
    L.append(f'tl.to("{sid}", {{opacity: 0, y: -8, duration: 0.18}}, {b - 0.18});')
    if k == 'title':
        n = len(s['title'].split(' '))
        L.append(f'tl.fromTo("{sid} .w", {{opacity: 0, y: 14, filter: "blur(6px)"}}, {{opacity: 1, y: 0, filter: "blur(0px)", duration: 0.3, stagger: 0.12}}, {a + 0.15});')
        if s.get('sub'): L.append(f'tl.fromTo("{sid} .sub", {{opacity: 0}}, {{opacity: 1, duration: 0.3}}, {s.get("sub_at", a + 0.3 + n * 0.12)});')
    elif k == 'counter':
        t0 = s.get('at', a + 0.3); dur = s.get('dur', 1.6)
        L.append(f'const o{i} = {{v: {s.get("from", 0)}}}; tl.to(o{i}, {{v: {s["to"]}, duration: {dur}, ease: "power2.inOut", onUpdate: () => {{ document.getElementById("n{i}").textContent = Math.round(o{i}.v).toLocaleString("en-US"); }}}}, {t0});')
        L.append(f'tl.fromTo("{sid} .cnt", {{scale: 1}}, {{scale: 1.12, duration: 0.15, yoyo: true, repeat: 1}}, {t0 + dur});')
        if s.get('sub'): L.append(f'tl.fromTo("{sid} .cntsub", {{opacity: 0, scale: 0.6}}, {{opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2.5)"}}, {s.get("sub_at", t0 + dur)});')
    elif k in ('big', 'bars'):
        L.append(f'tl.fromTo("{sid} .bigg", {{scale: 1.35, opacity: 0}}, {{scale: 1, opacity: 1, duration: 0.3, ease: "back.out(2)"}}, {a + 0.05});')
        L.append(f'tl.fromTo("{sid} .sub", {{opacity: 0, y: 8}}, {{opacity: 1, y: 0, duration: 0.3}}, {s.get("sub_at", a + 0.4)});')
        if k == 'bars':
            L.append(f'tl.fromTo("{sid} .bar", {{scaleY: 0}}, {{scaleY: 1, duration: 0.3, stagger: 0.18, ease: "back.out(2)"}}, {a + 0.6});')
    elif k in ('chips', 'gold'):
        at = s.get('at') or []
        n = len(s['items'])
        for j in range(n):
            t0 = at[j] if j < len(at) else a + 0.2 + j * 0.35
            cls = 'ch' if k == 'chips' else 'g'
            L.append(f'tl.fromTo("{sid} .{cls}{j}", {{opacity: 0, scale: 0.6, y: 12}}, {{opacity: 1, scale: 1, y: 0, duration: 0.28, ease: "back.out(2.4)"}}, {t0});')
    elif k == 'warn':
        L.append(f'tl.fromTo("{sid} .warn", {{x: 0}}, {{x: 7, duration: 0.05, repeat: 5, yoyo: true}}, {a + 0.3});')
    elif k == 'cta':
        for j in range(len(s.get('pills', []))):
            t0 = (s.get('at') or [a + 0.6])[j] if j < len(s.get('at') or [a + 0.6]) else a + 0.6 + j * 0.4
            L.append(f'tl.fromTo("{sid} .p{j}", {{opacity: 0, scale: 0.6}}, {{opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2.5)"}}, {t0});')
            L.append(f'tl.to("{sid} .p{j}", {{y: -6, duration: 0.45, repeat: 5, yoyo: true, ease: "sine.inOut"}}, {t0 + 0.4});')
    return '\n      '.join(L)

def sfx_events(sc):
    ev = []
    for i, s in enumerate(sc):
        a, b = s['t']; k = s['kind']; at = s.get('at') or []
        if i == 0: ev.append((a + 0.1, 'shimmer', -2))
        if k == 'broll':
            ev += [(a, 'whoosh', 0), (a + 0.05, 'boom', -6)]
            ev += [(t, 'pop', -2) for t in at]
            for key in ('logo_at', 'pill_at', 'tag_at'):
                if s.get(key) is not None: ev.append((s[key], 'shimmer' if key != 'tag_at' else 'coin', -3))
            continue
        ev.append((a - 0.05, 'swoosh', -4))
        if k == 'title': ev += [(a + 0.15 + j * 0.12, 'tick', -10) for j in range(min(8, len(s['title'].split(' '))))]
        elif k == 'big': ev += [(a + 0.05, 'hit', 0), (a + 0.35, 'shimmer', -4)]
        elif k == 'bars': ev += [(a + 0.05, 'hit', -1)] + [(a + 0.6 + j * 0.18, 'tick', -6) for j in range(7)] + [(a + 1.9, 'coin', -4)]
        elif k in ('chips', 'gold'): ev += [(at[j] if j < len(at) else a + 0.2 + j * 0.35, 'pop', 0) for j in range(len(s['items']))]
        elif k == 'warn': ev += [(a + 0.05, 'alarm', -6)]
        elif k == 'counter':
            t0 = s.get('at', a + 0.3); dur = s.get('dur', 1.6)
            ev += [(t0 + j * dur / 10, 'tick', -7) for j in range(10)] + [(t0 + dur, 'coin', -1), (s.get('sub_at', t0 + dur) + 0.05, 'shimmer', -4)]
        elif k == 'cta': ev += [(a, 'swell', -3)] + [(t, 'coin', -2) for t in (s.get('at') or [a + 0.6])]
    return ev

def build(spec, out):
    D = spec['duration']; B = spec.get('band', {}); top, bot = B.get('top', 225), B.get('bottom', 405)
    sc = spec['scenes']; C = spec.get('captions', {})
    cards = '\n        '.join(card_html(i, s) for i, s in enumerate(sc) if s['kind'] != 'broll')
    brolls = '\n        '.join(broll_html(i, s) for i, s in enumerate(sc) if s['kind'] == 'broll')
    bvids = '\n      '.join(f'<video id="bv{i}" class="clip bvid" src="{e(s["video"])}" data-start="{s["t"][0]:.2f}" data-duration="{s["t"][1] - s["t"][0]:.2f}" data-track-index="{3 + i}" muted playsinline></video>'
                            for i, s in enumerate(sc) if s['kind'] == 'broll' and s.get('video'))
    js = '\n      '.join(card_js(i, s) for i, s in enumerate(sc))
    cap_html, cap_js = '', []
    if C.get('words'):
        words = json.load(open(os.path.join(out, C['words'])))
        for j, (a, b, t) in enumerate(phrases(words, C.get('fix', {}))):
            if a >= D: continue
            cap_html += f'<div class="cap" id="k{j}"><span>{mark_key(t, C.get("keys", []))}</span></div>'
            cap_js.append(f'tl.fromTo("#k{j}", {{opacity: 0, y: 10, scale: 0.96}}, {{opacity: 1, y: 0, scale: 1, duration: 0.12, ease: "power2.out"}}, {a:.2f}); tl.to("#k{j}", {{opacity: 0, duration: 0.06}}, {min(b, D) - 0.06:.2f});')
    cy, ch = C.get('y', 1428), C.get('h', 140)
    doc = f'''<!doctype html>
<html lang="ms">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="assets/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Mont"; src: url("assets/Montserrat.ttf"); font-weight: 100 900; }}
      @font-face {{ font-family: "Play"; src: url("assets/PlayfairDisplay.ttf"); font-weight: 400 900; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: 1080px; height: 1920px; font-family: "Mont", sans-serif; color: #fff; }}
      #vid {{ position: absolute; inset: 0; width: 1080px; height: 1920px; object-fit: cover; }}
      #layer {{ position: absolute; inset: 0; }}
      .g {{ color: #F2C14E; font-weight: inherit; }}
      .card {{ position: absolute; left: 50%; top: {(top + bot) / 2}px; transform: translate(-50%, -50%); opacity: 0; max-width: 940px; width: max-content;
              padding: 18px 44px 20px; border-radius: 22px; text-align: center;
              background: linear-gradient(180deg, rgba(34,27,18,.9), rgba(12,10,8,.92)); border: 1.5px solid rgba(220,176,86,.6);
              box-shadow: 0 12px 34px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,230,170,.18); }}
      .card.bare {{ background: none; border: none; box-shadow: none; padding: 0; display: flex; flex-direction: column; align-items: center; gap: 12px; }}
      .card.bare > .lbl {{ background: rgba(16,13,10,.88); padding: 8px 24px; border-radius: 30px; margin: 0; }}
      .card.in {{ position: static; transform: none; opacity: 1; }}
      .lbl {{ font-size: 26px; font-weight: 700; letter-spacing: .3em; color: #E7B958; text-transform: uppercase; margin-bottom: 6px; }}
      .serif {{ font-family: "Play", serif; font-weight: 700; line-height: 1.12; }} .serif .w {{ display: inline-block; }}
      .sub {{ font-size: 32px; font-weight: 600; opacity: .95; margin-top: 6px; }}
      .bigg {{ font-weight: 900; line-height: 1; letter-spacing: .01em;
              background: linear-gradient(180deg, #FFEDB0, #F2C14E 50%, #C68E1E); -webkit-background-clip: text; background-clip: text; color: transparent;
              filter: drop-shadow(0 3px 6px rgba(0,0,0,.4)); }}
      .chips {{ display: flex; flex-direction: column; align-items: center; gap: 12px; }} .chips.row {{ flex-direction: row; }}
      .chip {{ white-space: nowrap; display: flex; align-items: center; gap: 12px; font-size: 40px; font-weight: 700; padding: 10px 28px 10px 20px; border-radius: 40px;
              background: rgba(16,13,10,.86); border: 2px solid rgba(255,255,255,.18); box-shadow: 0 8px 22px rgba(0,0,0,.4); }}
      .chip.v {{ border-color: rgba(70,209,140,.75); }} .chip.x {{ border-color: rgba(255,90,90,.7); }} .chip.x span {{ text-decoration: line-through; text-decoration-color: rgba(255,90,90,.9); }}
      .lblpill {{ font-size: 26px; font-weight: 800; letter-spacing: .26em; color: #F2C14E; padding: 8px 26px; border-radius: 30px; background: rgba(16,13,10,.88); }}
      .grow {{ display: flex; align-items: center; gap: 18px; }}
      .gcard {{ display: flex; flex-direction: column; align-items: center; padding: 12px 30px; border-radius: 20px; color: #2a1600;
               background: linear-gradient(180deg, #FFE7A0, #F2C14E 55%, #D49B2A); box-shadow: 0 10px 24px rgba(0,0,0,.4), inset 0 2px 0 rgba(255,255,255,.6); }}
      .gcard b {{ font-size: 54px; font-weight: 900; line-height: 1.05; }} .gcard small {{ font-size: 22px; font-weight: 800; letter-spacing: .14em; }}
      .atau {{ font-family: "Play", serif; font-style: italic; font-size: 34px; color: #fff; text-shadow: 0 2px 8px rgba(0,0,0,.6); }}
      .bars {{ display: flex; align-items: flex-end; gap: 8px; height: 70px; margin-top: 8px; justify-content: center; }}
      .bar {{ display: block; width: 26px; border-radius: 5px; background: linear-gradient(180deg, #FFE7A0, #D49B2A); transform-origin: bottom; }}
      .warn {{ display: flex; align-items: center; gap: 14px; font-size: 52px; font-weight: 800; padding: 14px 34px; border-radius: 22px; color: #FF6464;
              background: rgba(16,13,10,.9); border: 2px solid rgba(220,176,86,.55); box-shadow: 0 10px 26px rgba(0,0,0,.45); }}
      .pills {{ display: flex; gap: 16px; }}
      .gpill {{ display: flex; align-items: center; gap: 10px; font-size: 42px; font-weight: 800; color: #2a1600; padding: 10px 26px; border-radius: 40px;
               background: linear-gradient(180deg, #FFE7A0, #F2C14E 60%, #D49B2A); box-shadow: 0 8px 20px rgba(0,0,0,.4); }}
      #capbox {{ position: absolute; left: 50px; right: 50px; top: {cy}px; height: {ch}px; border-radius: 26px;
                backdrop-filter: blur(20px); background: rgba(22,18,14,.62); box-shadow: 0 8px 26px rgba(0,0,0,.3); }}
      .cap {{ position: absolute; left: 70px; right: 70px; top: {cy}px; height: {ch}px; display: flex; align-items: center; justify-content: center; text-align: center;
             font-size: 54px; font-weight: 800; line-height: 1.15; opacity: 0; text-shadow: 0 3px 10px rgba(0,0,0,.5); }}
      .broll {{ position: absolute; inset: 0; opacity: 0; overflow: hidden; background: radial-gradient(circle at 50% 42%, #3d2c12 0%, #160f07 55%, #070504 100%); }}
      .rays {{ position: absolute; left: -50%; top: -30%; width: 200%; height: 160%;
              background: repeating-conic-gradient(from 0deg at 50% 45%, rgba(255,200,90,.07) 0deg 5deg, rgba(0,0,0,0) 5deg 13deg); }}
      .bimgs {{ position: absolute; left: 0; right: 0; top: 520px; display: flex; justify-content: center; align-items: center; gap: 26px; }}
      .bimgs.one {{ top: 560px; }}
      .bi {{ border-radius: 28px; border: 5px solid rgba(255,255,255,.9); box-shadow: 0 24px 60px rgba(0,0,0,.6); object-fit: cover; }}
      .bvid {{ position: absolute; inset: 0; width: 1080px; height: 1920px; object-fit: cover; opacity: 0; }}
      .broll.vb {{ background: linear-gradient(180deg, rgba(0,0,0,.35), rgba(0,0,0,0) 30%, rgba(0,0,0,0) 62%, rgba(0,0,0,.45)); }}
      .bi.free {{ border: none; border-radius: 0; box-shadow: none; filter: drop-shadow(0 26px 50px rgba(0,0,0,.6)); }}
      .cnt {{ font-size: 104px; display: flex; align-items: baseline; justify-content: center; gap: 8px; }} .cnt small {{ font-size: 54px; }}
      .cntsub {{ display: inline-block; font-size: 26px; font-weight: 900; letter-spacing: .12em; color: #2a1600; padding: 6px 18px; border-radius: 12px; margin-top: 6px;
                background: linear-gradient(180deg, #FFE7A0, #F2C14E 60%, #D49B2A); }}
      .bimgs.one .bi {{ width: 900px; }} .bimgs.row .bi {{ height: 470px; max-width: 320px; }}
      .blogo {{ position: absolute; left: 50%; top: 330px; transform: translateX(-50%); background: #fff; border-radius: 22px; padding: 12px 30px; box-shadow: 0 10px 30px rgba(0,0,0,.5); }}
      .blogo img {{ height: 80px; display: block; }}
      .bpill {{ position: absolute; left: 50%; top: 1130px; transform: translateX(-50%); font-size: 40px; font-weight: 800; color: #2a1600; padding: 12px 34px; border-radius: 40px; white-space: nowrap;
               background: linear-gradient(180deg, #FFE7A0, #F2C14E 60%, #D49B2A); box-shadow: 0 10px 26px rgba(0,0,0,.5); }}
      .btag {{ position: absolute; left: 50%; top: 1240px; transform: translateX(-50%); font-size: 44px; font-weight: 900; color: #F2C14E; padding: 10px 30px; border-radius: 18px; white-space: nowrap;
              background: rgba(16,13,10,.9); border: 2px solid rgba(220,176,86,.7); }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{D:.3f}" data-width="1080" data-height="1920">
      <video id="vid" class="clip" src="{spec["video"]}" data-start="0" data-duration="{D:.3f}" data-track-index="0" data-has-audio="true"></video>
      {bvids}
      <audio id="sfx" class="clip" src="assets/sfx.wav" data-start="0" data-duration="{D:.3f}" data-track-index="1"></audio>
      <div id="layer" class="clip" data-start="0" data-duration="{D:.3f}" data-track-index="2">
        {brolls}
        <div id="capbox"></div>
        {cap_html}
        {cards}
      </div>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      {js}
      {chr(10).join("      " + x for x in cap_js)}
      tl.set({{}}, {{}}, {D:.3f});
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
'''
    os.makedirs(os.path.join(out, 'assets'), exist_ok=True)
    open(os.path.join(out, 'index.html'), 'w').write(doc)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import sfx
    sfx.render_track(sorted(sfx_events(sc)), D, os.path.join(out, 'assets', 'sfx.wav'), spec.get('sfx_gain_db', -11), spec.get('music_db'))

if __name__ == '__main__':
    build(json.load(open(sys.argv[1])), sys.argv[2])
    print('ok', sys.argv[2])
