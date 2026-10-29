#!/usr/bin/env python3
"""Gaya 2 (references/gaya2.md) as a HyperFrames composition.

Usage: python3 gaya2_hf.py spec.json PROJECT_DIR
Writes PROJECT_DIR/index.html (+ assets/sfx.wav). Render with:  npx hyperframes render -o out.mp4  (in PROJECT_DIR)

spec = {
  "video": "assets/cut.mp4", "duration": 40.7,
  "panel": {"top": 250, "bottom": 550},           # band above the head (never over the face)
  "scenes": [ {"t": [start, end], "kind": ..., ...}, ... ],   # times on the CUT video
  "flashback": [[start, end, "3 YEARS AGO", "2023"]],          # optional film-strip flashback
  "sfx_gain_db": -14,
  "sfx": "rich" | "minimal",   # rich (default): a sound on every change / item, see rich_sfx()
  "cuts": [6.1, 12.4],         # optional jump-cut times (cut video) for a light whoosh
  "music_db": -30              # optional soft synthesised music bed under the voice
}
Scene kinds (all drawn inside ONE frosted panel above the head; the content cross-fades):
  odometer  {"label": "THE YEAR OF", "text": "2026", "sub": "AGENTIC", "key": "AI"}   characters roll in one by one
  warning   {"text": "KETINGGALAN", "sub": "LEFT BEHIND"}                               red, pops + sparks
  steps     {"num": "1", "text": "Cari circle", "tags": ["Simpan", "Melabur"]}          number badge + tag pills
  check     {"text": "Let it do the work", "sub": "..."}                                green tick + text
  icons     {"label": "THE BRAIN", "items": [["ChatGPT", "chat"], ...]}                  icon cards one by one
  formula   {"items": [["Auto debit", "repeat"], ["Setiap bulan", "calendar"]], "result": "Konsisten", "result_sub": "simpan emas"}
  stamp     {"before": "RM??", "text": "MURAH!"}                                        neon stamp slams in
  tags      {"title": "Macam-macam!", "items": [...]}                                    tag cloud
  cta       {"text": "DM saya", "sub": "cara set auto debit", "arrow": "up"|"none"}
  photo     {"label": "AKAUN EMAS GAP", "items": [["assets/x.jpg", ""]], "img_h": 280}   own photos / app screenshot cards
  any scene + {"logo": "assets/pg_logo.png", "logo_at": 46.94}   brand logo pill pops in (with shine) when the name is said
"""
import json, os, sys, html

ICONS = {   # simple inline SVG glyphs (no emoji fonts needed)
    'chat': '<circle cx="24" cy="22" r="14" fill="none" stroke="#fff" stroke-width="3"/><path d="M14 34 l-4 8 l10 -5" fill="#fff"/>',
    'repeat': '<path d="M12 20 a12 12 0 0 1 22 -4" fill="none" stroke="#fff" stroke-width="3.5"/><path d="M36 10 l-1 8 l-8 -2" fill="none" stroke="#fff" stroke-width="3.5"/><path d="M36 28 a12 12 0 0 1 -22 4" fill="none" stroke="#fff" stroke-width="3.5"/><path d="M12 38 l1 -8 l8 2" fill="none" stroke="#fff" stroke-width="3.5"/>',
    'calendar': '<rect x="8" y="12" width="32" height="28" rx="5" fill="none" stroke="#fff" stroke-width="3"/><line x1="8" y1="20" x2="40" y2="20" stroke="#fff" stroke-width="3"/><line x1="16" y1="8" x2="16" y2="15" stroke="#fff" stroke-width="3"/><line x1="32" y1="8" x2="32" y2="15" stroke="#fff" stroke-width="3"/><circle cx="24" cy="30" r="4" fill="#F5C451"/>',
    'coin': '<circle cx="24" cy="24" r="15" fill="#F5C451" stroke="#B9851C" stroke-width="3"/><text x="24" y="29" font-size="13" font-weight="900" text-anchor="middle" fill="#6b4300">RM</text>',
    'people': '<circle cx="17" cy="18" r="6" fill="#fff"/><circle cx="31" cy="18" r="6" fill="#fff"/><path d="M6 38 a11 10 0 0 1 22 0 z" fill="#fff"/><path d="M20 38 a11 10 0 0 1 22 0 z" fill="#fff" opacity=".8"/>',
    'gold': '<path d="M8 34 l6 -12 h20 l6 12 z" fill="#F5C451" stroke="#B9851C" stroke-width="2.5"/><path d="M16 22 l4 -8 h8 l4 8" fill="#FFE08A" stroke="#B9851C" stroke-width="2.5"/>',
    'check': '<circle cx="24" cy="24" r="16" fill="#46B58C"/><path d="M16 24 l6 6 l11 -12" fill="none" stroke="#fff" stroke-width="4"/>',
    'robot': '<rect x="10" y="14" width="28" height="22" rx="7" fill="#fff"/><circle cx="19" cy="25" r="3.5" fill="#2b2b2b"/><circle cx="29" cy="25" r="3.5" fill="#2b2b2b"/><line x1="24" y1="8" x2="24" y2="14" stroke="#fff" stroke-width="3"/>',
}
def icon(name, size=48):
    return f'<svg viewBox="0 0 48 48" width="{size}" height="{size}">{ICONS.get(name, ICONS["coin"])}</svg>'

ROLL = 'ABCDEFGHJKLMNPRSTUVWXYZ0123456789'
def odo_chars(text, sid):
    out = []
    for i, ch in enumerate(text):
        if ch == ' ': out.append('<span class="sp"> </span>'); continue
        k = (i * 7 + len(text)) % len(ROLL)
        seq = [ROLL[(k + j * 5) % len(ROLL)] for j in range(5)] + [ch]
        col = ''.join(f'<span>{html.escape(c)}</span>' for c in seq)
        out.append(f'<span class="odo"><span class="w">{html.escape(ch)}</span><span class="strip" id="{sid}c{i}">{col}</span></span>')
    return ''.join(out)

def scene_html(i, s):
    k = s['kind']; sid = f's{i}'; e = html.escape
    if k == 'odometer':
        fs = min(124, int(1500 / max(1, len(s['text']))))   # long words shrink to fit the panel
        glints = ''.join(f'<i class="glint" style="left:{8 + (j * 23) % 84}%;top:{20 + (j * 37) % 60}%"></i>' for j in range(8))
        body = (f'<div class="lbl">{e(s.get("label", ""))}</div><div class="big" style="font-size:{fs}px">{odo_chars(s["text"], sid)}</div>{glints}'
                + (f'<div class="sub2">{e(s.get("sub", ""))} <b>{e(s.get("key", ""))}</b></div>' if s.get('sub') or s.get('key') else ''))
    elif k == 'warning':
        sparks = ''.join(f'<i class="spark" style="left:{30 + (j * 37) % 40}%;top:{55 + (j * 13) % 30}%"></i>' for j in range(10))
        body = f'<div class="big red">{e(s["text"])}</div><div class="lbl red2">{e(s.get("sub", ""))}</div>{sparks}'
    elif k == 'steps':
        tags = ''.join(f'<span class="tag t{j}">{e(t)}</span>' for j, t in enumerate(s.get('tags', [])))
        body = f'<div class="row"><div class="badge">{e(s["num"])}</div><div class="mid">{e(s["text"])}</div></div><div class="tags">{tags}</div>'
    elif k == 'check':
        body = f'<div class="row">{icon("check", 64)}<div class="mid">{e(s["text"])}</div></div>' + (f'<div class="lbl">{e(s.get("sub", ""))}</div>' if s.get('sub') else '')
    elif k == 'icons':
        cards = ''.join(f'<div class="card c{j}">{icon(ic, 64)}<div>{e(n)}</div></div>' for j, (n, ic) in enumerate(s['items']))
        body = f'<div class="lbl">{e(s.get("label", ""))}</div><div class="cards">{cards}</div>'
    elif k == 'formula':
        it = s['items']; cards = ''
        for j, (n, ic) in enumerate(it):
            cards += f'<div class="card c{j}">{icon(ic, 60)}<div>{e(n)}</div></div>' + (f'<div class="op o{j}">+</div>' if j < len(it) - 1 else '')
        cards += f'<div class="op o{len(it) - 1}">=</div><div class="card res">{icon("check", 60)}<div><b>{e(s["result"])}</b></div><small>{e(s.get("result_sub", ""))}</small></div>'
        body = f'<div class="cards">{cards}</div>'
    elif k == 'stamp':
        bill = ''
        if s.get('bill'):   # cartoon banknote (an illustration, never a real currency image)
            bill = (f'<svg class="bill" viewBox="0 0 300 140" width="290" height="135"><rect x="2" y="2" width="296" height="136" rx="14" fill="#B9A6E8" stroke="#6E5AB8" stroke-width="4"/>'
                    f'<rect x="14" y="14" width="272" height="112" rx="8" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="2" stroke-dasharray="6 5"/>'
                    f'<g transform="translate(70 72)" fill="#E8584A">' + ''.join(f'<ellipse rx="13" ry="22" transform="rotate({r}) translate(0 -18)"/>' for r in range(0, 360, 72)) + '<circle r="7" fill="#FFD27A"/></g>'
                    f'<text x="200" y="88" font-size="52" font-weight="900" text-anchor="middle" fill="#3E2F86" font-family="Inter">{e(s["bill"])}</text></svg>')
        if bill:   # note on the left, stamp beside it (never on top of each other)
            body = f'<div class="billrow">{bill}<div class="stamp inl">{e(s["text"])}</div></div>'
        else:
            body = f'<div class="big dim">{e(s.get("before", ""))}</div><div class="stamp">{e(s["text"])}</div>'
    elif k == 'photo':   # participant's own product photos in rounded cards
        st = f' style="height:{int(s["img_h"])}px"' if s.get('img_h') else ''   # one big screenshot: taller card
        cards = ''.join(f'<div class="ph p{j}"><img src="{e(src)}"{st}/>' + (f'<div>{e(cap)}</div>' if cap else '') + '</div>' for j, (src, cap) in enumerate(s['items']))
        lbl = f'<div class="lbl">{e(s.get("label", ""))}</div>' if s.get('label') else ''
        if s.get('logo'): lbl = f'<div class="hdr">{logo_html(s)}{lbl}</div>'   # logo + label share one row
        body = lbl + f'<div class="phs">{cards}</div>'
    elif k == 'tags':
        tags = ''.join(f'<span class="tag t{j}">{e(t)}</span>' for j, t in enumerate(s['items']))
        body = f'<div class="pilltitle">{e(s["title"])}</div><div class="tags wrap">{tags}</div>'
    elif k == 'cta':
        arrow = '<div class="arrow">&#8593;</div>' if s.get('arrow', 'none') == 'up' else ''
        body = f'{arrow}<div class="ctapill">{icon("chat", 46)}<span>{e(s["text"])}</span></div>' + (f'<div class="lbl">{e(s.get("sub", ""))}</div>' if s.get('sub') else '')
    else:
        raise SystemExit(f'unknown scene kind {k}')
    if s.get('note'): body += f'<div class="note">{e(s["note"])}</div>'   # small disclaimer line
    if s.get('logo') and k != 'photo': body = logo_html(s) + body
    return f'<div class="scene{" withlogo" if s.get("logo") else ""}" id="{sid}">{body}</div>'

def logo_html(s):
    """Brand logo pill (e.g. Public Gold) shown when the speaker says the name: "logo": src, "logo_at": time."""
    return f'<div class="pglogo"><img src="{html.escape(s["logo"])}"/><span class="shine"></span></div>'

def scene_js(i, s):
    sid = f'#s{i}'; a, b = s['t']; k = s['kind']; L = []
    L.append(f'tl.fromTo("{sid}", {{opacity: 0, y: 14, scale: 0.97}}, {{opacity: 1, y: 0, scale: 1, duration: 0.18, ease: "power2.out"}}, {a});')
    L.append(f'tl.to("{sid}", {{opacity: 0, y: -10, duration: 0.15, ease: "power1.in"}}, {max(a + 0.2, b - 0.15)});')
    if s.get('logo'):
        tg = s.get('logo_at', a + 0.05)
        L.append(f'tl.fromTo("{sid} .pglogo", {{opacity: 0, scale: 0.6}}, {{opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2.5)"}}, {tg});')
        L.append(f'tl.fromTo("{sid} .shine", {{xPercent: -150}}, {{xPercent: 450, duration: 0.7, ease: "power2.inOut"}}, {tg + 0.3});')
    if k == 'odometer':
        n = len(s['text'])
        for c in range(n):
            if s['text'][c] == ' ': continue
            L.append(f'tl.fromTo("{sid}c{c}", {{yPercent: 0}}, {{yPercent: -500/6, duration: 0.28, ease: "power3.out"}}, {a + 0.08 + c * 0.07});')
        L.append(f'tl.fromTo("{sid} .lbl", {{opacity: 0}}, {{opacity: 1, duration: 0.2}}, {a + 0.15 + n * 0.07});')
        L.append(f'tl.fromTo("{sid} .glint", {{opacity: 0, y: 10}}, {{opacity: 0.9, y: -40, duration: 1.2, stagger: 0.12, ease: "sine.out"}}, {a + 0.4});')
        L.append(f'tl.to("{sid} .glint", {{opacity: 0, duration: 0.4, stagger: 0.12}}, {a + 1.4});')
        if s.get('sub') or s.get('key'): L.append(f'tl.fromTo("{sid} .sub2", {{opacity: 0, y: 10}}, {{opacity: 1, y: 0, duration: 0.25, ease: "back.out(2)"}}, {a + 0.3 + n * 0.07});')
    elif k == 'warning':
        L.append(f'tl.fromTo("{sid} .big", {{scale: 1.5}}, {{scale: 1, duration: 0.25, ease: "back.out(3)"}}, {a});')
        L.append(f'tl.to("{sid} .big", {{x: 6, duration: 0.04, repeat: 5, yoyo: true}}, {a + 0.25});')
        L.append(f'tl.fromTo("{sid} .spark", {{opacity: 1, y: 0, scale: 1}}, {{opacity: 0, y: -90, scale: 0.3, duration: 0.8, stagger: 0.05, ease: "power2.out"}}, {a + 0.1});')
    elif k in ('steps', 'tags'):
        if s.get('at'):   # each tag lands on its spoken word
            for j, t0 in enumerate(s['at']):
                L.append(f'tl.fromTo("{sid} .t{j}", {{opacity: 0, scale: 0.6}}, {{opacity: 1, scale: 1, duration: 0.2, ease: "back.out(2.5)"}}, {t0});')
        else:
            L.append(f'tl.fromTo("{sid} .tag", {{opacity: 0, scale: 0.6}}, {{opacity: 1, scale: 1, duration: 0.2, stagger: {s.get("stagger", 0.25)}, ease: "back.out(2.5)"}}, {a + 0.35});')
        if k == 'steps': L.append(f'tl.fromTo("{sid} .badge", {{scale: 0.4, rotation: -30}}, {{scale: 1, rotation: 0, duration: 0.3, ease: "back.out(3)"}}, {a});')
    elif k == 'check':
        L.append(f'tl.fromTo("{sid} svg", {{scale: 0}}, {{scale: 1, duration: 0.3, ease: "back.out(3)"}}, {a + 0.1});')
    elif k in ('icons', 'formula'):
        at = s.get('at')
        for j in range(len(s['items'])):
            t0 = at[j] if at else a + 0.2 + j * 0.45
            L.append(f'tl.fromTo("{sid} .c{j}", {{opacity: 0, scale: 0.5, y: 20}}, {{opacity: 1, scale: 1, y: 0, duration: 0.3, ease: "back.out(2.2)"}}, {t0});')
            L.append(f'tl.fromTo("{sid} .o{j}", {{opacity: 0}}, {{opacity: 1, duration: 0.15}}, {t0 + 0.2});')
        if k == 'formula':
            tr = s.get('result_at', (at[-1] if at else a + 0.2 + (len(s['items']) - 1) * 0.45) + 0.5)
            L.append(f'tl.fromTo("{sid} .res", {{opacity: 0, scale: 0.4}}, {{opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2.5)"}}, {tr});')
    elif k == 'photo':
        at = s.get('at')
        for j in range(len(s['items'])):
            t0 = at[j] if at else a + 0.1 + j * 0.3
            L.append(f'tl.fromTo("{sid} .p{j}", {{opacity: 0, y: 30, rotation: {(-4 if j % 2 == 0 else 4)}, scale: 0.85}}, {{opacity: 1, y: 0, rotation: {(-3 if j % 2 == 0 else 3)}, scale: 1, duration: 0.35, ease: "back.out(1.8)"}}, {t0});')
    elif k == 'stamp':
        if s.get('bill'): L.append(f'tl.fromTo("{sid} .bill", {{opacity: 0, x: -60, rotation: -14}}, {{opacity: 1, x: 0, rotation: -6, duration: 0.3, ease: "back.out(2)"}}, {a});')
        ts = s.get('stamp_at', a + 0.5)
        L.append(f'tl.fromTo("{sid} .stamp", {{opacity: 0, scale: 1.8, rotation: -2}}, {{opacity: 1, scale: 1, rotation: -8, duration: 0.18, ease: "power4.in"}}, {ts});')
        L.append(f'tl.to("{sid} .dim", {{opacity: 0.25, duration: 0.1}}, {ts});')
        L.append(f'tl.fromTo("#panel", {{x: 0}}, {{x: 8, duration: 0.04, repeat: 3, yoyo: true}}, {ts + 0.18});')
    elif k == 'cta':
        if s.get('arrow') == 'up': L.append(f'tl.fromTo("{sid} .arrow", {{y: 0}}, {{y: -16, duration: 0.35, repeat: {int((b - a) / 0.7)}, yoyo: true, ease: "sine.inOut"}}, {a + 0.2});')
        L.append(f'tl.fromTo("{sid} .ctapill", {{scale: 0.6}}, {{scale: 1, duration: 0.3, ease: "back.out(3)"}}, {a});')
    return '\n      '.join(L)

def rich_sfx(sc, spec):
    """Full sound design (default): a swoosh on every panel change, a sound for every item as it lands
    (on the same times as the animation), rolling ticks on odometers, a boom on the hook, gold shimmer
    on gold moments, a soft whoosh on zoom jump cuts ("cuts": [times]). Events: (time, name, extra_db)."""
    ev = []
    for i, s in enumerate(sc):
        a, b = s['t']; k = s['kind']; at = s.get('at') or []
        if s.get('logo'): ev.append((s.get('logo_at', a + 0.05) + 0.05, 'shimmer', -3))
        if i == 0: ev += [(a, 'boom', -1)]
        else: ev += [(a - 0.06, 'swoosh', -5)]
        if k == 'odometer':
            chars = [c for c in range(len(s['text'])) if s['text'][c] != ' ']
            for c in chars[:16]: ev.append((a + 0.08 + c * 0.07, 'tick', -7))
            ev.append((a + 0.36 + len(s['text']) * 0.07, 'shimmer', -3))
        elif k == 'warning': ev += [(a, 'hit', 0), (a + 0.25, 'alarm', -6)]
        elif k in ('steps', 'tags'):
            ev.append((a, 'hit' if k == 'steps' else 'pop', -2))
            n = len(s.get('tags', s.get('items', [])))
            for j in range(n): ev.append((at[j] if j < len(at) else a + 0.35 + j * s.get('stagger', 0.25), 'pop', -2))
        elif k == 'check': ev += [(a + 0.1, 'pop', 0), (a + 0.3, 'coin', -4)]
        elif k in ('icons', 'formula'):
            for j in range(len(s['items'])): ev.append((at[j] if j < len(at) else a + 0.2 + j * 0.45, 'pop', 0))
            if k == 'formula':
                tr = s.get('result_at', (at[-1] if at else a + 0.2 + (len(s['items']) - 1) * 0.45) + 0.5)
                ev += [(tr, 'hit', 0), (tr + 0.15, 'shimmer', -4)]
        elif k == 'photo':
            for j in range(len(s['items'])): ev.append((at[j] if j < len(at) else a + 0.1 + j * 0.3, 'whoosh', -2))
            ev.append(((at[-1] if at else a + 0.1 + (len(s['items']) - 1) * 0.3) + 0.3, 'shimmer', -3))
        elif k == 'stamp':
            ts = s.get('stamp_at', a + 0.5)
            if s.get('bill'): ev.append((a + 0.02, 'whoosh', -2))
            ev += [(ts + 0.15, 'punch', 2), (ts + 0.3, 'coin', -5)]
        elif k == 'cta': ev += [(a, 'swell', -2), (a + 0.05, 'coin', -2), (a + 0.35, 'shimmer', -4)]
    busy = [e[0] for e in ev]
    for t in spec.get('cuts', []):   # zoom jump cuts: a light whoosh, unless something else plays there
        if all(abs(t - u) > 0.45 for u in busy): ev.append((t - 0.05, 'whoosh', -10))
    return ev

SFX_OF = dict(photo='whoosh', odometer='tick', warning='impact', steps='pop', check='pop', icons='pop', formula='pop', stamp='punch', tags='pop', cta='coin')

def build(spec, out_dir):
    D = spec['duration']; P = spec.get('panel', {}); top, bot = P.get('top', 250), P.get('bottom', 550)
    sc = spec['scenes']; win_a = min(s['t'][0] for s in sc); win_b = max(s['t'][1] for s in sc)
    scenes = '\n        '.join(scene_html(i, s) for i, s in enumerate(sc))
    js = '\n      '.join(scene_js(i, s) for i, s in enumerate(sc))
    # panel visible only while a scene is on: show/hide per scene group
    pj, groups = [], []
    for s in sorted(sc, key=lambda x: x['t'][0]):   # back-to-back scenes share one panel appearance
        a, b = s['t']
        if groups and a - groups[-1][1] < 0.6: groups[-1][1] = max(groups[-1][1], b)
        else: groups.append([a, b])
    for a, b in groups:
        pj.append(f'tl.fromTo("#panel", {{opacity: 0, scale: 0.96}}, {{opacity: 1, scale: 1, duration: 0.18, ease: "power2.out", immediateRender: false}}, {max(0, a - 0.12)}); tl.to("#panel", {{opacity: 0, duration: 0.2}}, {b});')
    fb_html, fb_js = '', []
    for j, (a, b, lab, year) in enumerate(spec.get('flashback', [])):
        fb_html += f'<div class="film" id="fb{j}"><div class="sprk l"></div><div class="sprk r"></div><div class="fbpill"><div class="lbl">{html.escape(lab)}</div><div class="big">&#9664;&#9664; {html.escape(year)}</div></div></div><div class="flash" id="fl{j}"></div>'
        fb_js.append(f'tl.fromTo("#fb{j}", {{opacity: 0}}, {{opacity: 1, duration: 0.2}}, {a}); tl.to("#fb{j}", {{opacity: 0, duration: 0.05}}, {b});')
        fb_js.append(f'tl.fromTo("#vid", {{filter: "sepia(0) saturate(1) contrast(1)"}}, {{filter: "sepia(0.75) saturate(1.4) contrast(1.05) hue-rotate(-12deg)", duration: 0.2}}, {a}); tl.to("#vid", {{filter: "sepia(0) saturate(1) contrast(1)", duration: 0.01}}, {b});')
        fb_js.append(f'tl.fromTo("#fl{j}", {{opacity: 0}}, {{opacity: 1, duration: 0.05}}, {b - 0.05}); tl.to("#fl{j}", {{opacity: 0, duration: 0.25}}, {b});')
    H = top; h = bot - top
    doc = f'''<!doctype html>
<html lang="ms" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="assets/gsap.min.js"></script>
    <style>
      :root {{ --tint: rgba(110, 78, 52, 0.62); --key: #F5A623; --ok: #46B58C; --font: "Inter", "Montserrat", sans-serif; }}
      @font-face {{ font-family: "Inter"; src: url("assets/Inter.ttf"); font-weight: 100 900; }}
      @font-face {{ font-family: "Mono"; src: url("assets/JetBrainsMono-Bold.ttf"); }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: 1080px; height: 1920px; font-family: var(--font); color: #fff; }}
      #vid {{ position: absolute; inset: 0; width: 1080px; height: 1920px; object-fit: cover; }}
      #panel {{ position: absolute; left: 70px; width: 880px; top: {H}px; height: {h}px; border-radius: 42px; opacity: 0;
               background: linear-gradient(160deg, rgba(150,112,80,.72), var(--tint) 55%, rgba(80,56,38,.70));
               border: 2px solid rgba(255,255,255,.28); box-shadow: 0 18px 50px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.35);
               backdrop-filter: blur(22px) saturate(1.2); overflow: visible; }}
      #panel::after {{ content: ""; position: absolute; inset: 0; border-radius: 42px; pointer-events: none;
               background: linear-gradient(115deg, rgba(255,255,255,.18), rgba(255,255,255,0) 40%); }}
      .scene {{ position: absolute; inset: 0; opacity: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; text-align: center; padding: 0 40px; }}
      .pglogo {{ position: relative; overflow: hidden; display: inline-flex; background: #fff; border-radius: 18px; padding: 8px 22px; box-shadow: 0 6px 18px rgba(0,0,0,.3); flex: none; }}
      .pglogo img {{ height: 62px; display: block; }}
      .shine {{ position: absolute; top: -20%; left: 0; width: 22%; height: 140%; transform: skewX(-20deg);
               background: linear-gradient(90deg, rgba(255,255,255,0), rgba(255,236,170,.85), rgba(255,255,255,0)); }}
      .hdr {{ display: flex; align-items: center; justify-content: center; gap: 18px; }}
      .withlogo .ph img {{ height: {max(110, h - 196)}px; }}
      .lbl {{ font-size: 26px; letter-spacing: .32em; font-weight: 600; opacity: .9; text-transform: uppercase; }}
      .big {{ font-size: 124px; font-weight: 900; line-height: 1; letter-spacing: -0.02em; display: flex; justify-content: center; text-shadow: 0 6px 24px rgba(0,0,0,.35); }}
      .sub2 {{ font-size: 64px; font-weight: 900; letter-spacing: -0.01em; }} .sub2 b {{ color: var(--key); }}
      .odo {{ display: inline-block; position: relative; height: 1em; overflow: hidden; }} .odo .w {{ visibility: hidden; }}
      .strip {{ position: absolute; left: -20px; right: -20px; top: 0; display: flex; flex-direction: column; align-items: center; }} .strip span {{ height: 1em; line-height: 1em; }}
      .glint {{ position: absolute; width: 8px; height: 8px; border-radius: 50%; background: #FFE3A3; box-shadow: 0 0 10px #FFC761; opacity: 0; }}
      .sp {{ display: inline-block; width: .3em; }}
      .red {{ color: #FF4D4D; font-size: 108px; text-shadow: 0 0 30px rgba(255,60,60,.6); }} .red2 {{ color: #FFB3B3; }}
      .spark {{ position: absolute; width: 10px; height: 10px; border-radius: 50%; background: #FFD27A; box-shadow: 0 0 12px #FFB347; }}
      .row {{ display: flex; align-items: center; gap: 22px; }}
      .badge {{ width: 92px; height: 92px; border-radius: 50%; background: radial-gradient(circle at 35% 30%, #FFE7A0, #E2A93B 70%, #B47A16); color: #2b1a00;
               font-size: 56px; font-weight: 900; display: flex; align-items: center; justify-content: center; box-shadow: 0 6px 18px rgba(0,0,0,.35); }}
      .mid {{ font-size: 66px; font-weight: 800; letter-spacing: -0.01em; }}
      .tags {{ display: flex; gap: 14px; justify-content: center; }} .tags.wrap {{ flex-wrap: wrap; max-width: 800px; }}
      .tag {{ font-size: 32px; font-weight: 700; padding: 10px 24px; border-radius: 40px; background: rgba(255,255,255,.18); border: 1.5px solid rgba(255,255,255,.35); }}
      .cards {{ display: flex; gap: 16px; align-items: center; justify-content: center; }}
      .card {{ min-width: 170px; padding: 16px 18px; border-radius: 26px; background: rgba(255,255,255,.14); border: 1.5px solid rgba(255,255,255,.3);
              display: flex; flex-direction: column; align-items: center; gap: 8px; font-size: 30px; font-weight: 700; }}
      .card small {{ font-size: 22px; opacity: .85; font-weight: 600; }} .card.res {{ background: rgba(70,181,140,.28); border-color: rgba(120,230,180,.7); }}
      .op {{ font-size: 64px; font-weight: 900; opacity: .9; }}
      .dim {{ font-size: 110px; }}
      .stamp {{ position: absolute; font-size: 112px; font-weight: 900; color: #5CF0B0; padding: 6px 34px; border: 8px solid #5CF0B0; border-radius: 22px;
               text-shadow: 0 0 22px rgba(92,240,176,.8); box-shadow: 0 0 30px rgba(92,240,176,.6), inset 0 0 24px rgba(92,240,176,.4); background: rgba(10,40,30,.35); }}
      .pilltitle {{ font-size: 70px; font-weight: 900; padding: 8px 40px; border-radius: 60px; background: rgba(255,255,255,.16); border: 2px solid rgba(255,255,255,.35); }}
      .ctapill {{ display: flex; align-items: center; gap: 18px; font-size: 72px; font-weight: 900; padding: 16px 46px; border-radius: 80px;
                 background: rgba(255,255,255,.18); border: 2px solid rgba(255,255,255,.45); }}
      .arrow {{ font-size: 70px; font-weight: 900; line-height: .8; }}
      .film {{ position: absolute; inset: 0; opacity: 0; pointer-events: none;
              background: radial-gradient(ellipse at 70% 20%, rgba(255,170,90,.35), rgba(0,0,0,0) 55%), repeating-linear-gradient(0deg, rgba(0,0,0,.08) 0 2px, rgba(0,0,0,0) 2px 6px); }}
      .sprk {{ position: absolute; top: 0; bottom: 0; width: 46px; background: #0c0c0c;
              -webkit-mask: repeating-linear-gradient(180deg, #000 0 26px, transparent 26px 50px) right 10px top 0 / 26px 100% no-repeat, linear-gradient(#000,#000); -webkit-mask-composite: xor; }}
      .sprk.l {{ left: 0; }} .sprk.r {{ right: 0; transform: scaleX(-1); }}
      .fbpill {{ position: absolute; left: 50%; top: {H + 20}px; transform: translateX(-50%); padding: 18px 60px; border-radius: 60px;
                background: rgba(40,30,22,.55); border: 2px solid rgba(255,255,255,.3); text-align: center; }}
      .fbpill .big {{ font-size: 84px; }}
      .flash {{ position: absolute; inset: 0; background: #fff8ef; opacity: 0; }}
      .billrow {{ display: flex; align-items: center; gap: 34px; }}
      .bill {{ filter: drop-shadow(0 8px 14px rgba(0,0,0,.35)); }}
      .stamp.inl {{ position: relative; font-size: 96px; }}
      .phs {{ display: flex; gap: 22px; justify-content: center; align-items: center; margin-top: 10px; }}
      .ph {{ display: flex; flex-direction: column; align-items: center; gap: 6px; font-size: 26px; font-weight: 800; }}
      .ph img {{ height: {max(120, h - 140)}px; border-radius: 22px; border: 4px solid rgba(255,255,255,.85); box-shadow: 0 10px 24px rgba(0,0,0,.4); object-fit: cover; }}
      .note {{ font-size: 22px; font-style: italic; opacity: .8; font-weight: 500; letter-spacing: .02em; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{D:.3f}" data-width="1080" data-height="1920">
      <video id="vid" class="clip" src="{spec["video"]}" data-start="0" data-duration="{D:.3f}" data-track-index="0" data-has-audio="true"></video>
      <audio id="sfx" class="clip" src="assets/sfx.wav" data-start="0" data-duration="{D:.3f}" data-track-index="1"></audio>
      {fb_html}
      <div id="panel" class="clip" data-start="0" data-duration="{D:.3f}" data-track-index="2">
        {scenes}
      </div>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      {chr(10).join("      " + x for x in pj)}
      {js}
      {chr(10).join("      " + x for x in fb_js)}
      tl.set({{}}, {{}}, {D:.3f});
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
'''
    os.makedirs(os.path.join(out_dir, 'assets'), exist_ok=True)
    open(os.path.join(out_dir, 'index.html'), 'w').write(doc)
    # sound effects track (built-in synth, no downloads)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import sfx
    if spec.get('sfx') == 'minimal':
        ev = [(s['t'][0], SFX_OF[s['kind']]) for s in sc]
        for s in sc:
            if s['kind'] == 'stamp': ev.append((s.get('stamp_at', s['t'][0] + 0.5), 'punch'))
            if s['kind'] in ('icons', 'formula'):
                ev += [(t, 'pop') for t in (s.get('at') or [])[1:]]
    else:
        ev = rich_sfx(sc, spec)
    for a, b, *_ in spec.get('flashback', []): ev += [(a, 'whoosh'), (b - 0.05, 'click')]
    sfx.render_track(sorted(ev), D, os.path.join(out_dir, 'assets', 'sfx.wav'), spec.get('sfx_gain_db', -14), spec.get('music_db'))

if __name__ == '__main__':
    build(json.load(open(sys.argv[1])), sys.argv[2])
    print('ok', sys.argv[2])
