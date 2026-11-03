#!/usr/bin/env python3
"""Split layout (Gaya 3 look): an info board on top, the speaker shrunk into a gold-framed card below, phrase
captions inside the card, blurred copy of the speaker as background. For "N sebab / N tips" talking videos where
the user wants "skrin saya dikecilkan, info di sebelah" (user picked top-bottom, Rakaman7).
Everything sits between y 236 and 1340: TikTok covers the top bar and, on tall phones, the caption/name area below ~1360.

Usage: python3 split_hf.py spec.json PROJECT_DIR   (then: npx hyperframes render -o out.mp4 in PROJECT_DIR)
spec = {
  "video": "assets/cut.mp4", "duration": 139.9, "focus_y": 28,      # object-position y % that keeps the face in the card
  "total": 8,                                                       # number of reasons (progress dots)
  "captions": {"words": "words.json", "keys": ["Public Gold", ...]},
  "sections": [ {"t": [a, b], "tag": "SEBAB 1 / 8", "n": 1, "title": "Nak emas *fizikal*?", "note": "...",
                 "items": [["v"|"x"|"", "text"], ...], "at": [t, ...]}, ...,
                {"t": [a, b], "cta": true, "logo": "assets/pg_logo.png", "title": "...", "pills": ["...", "..."], "at": [..]} ],
  "music_db": -14, "sfx_gain_db": -11
}"""
import json, os, re, sys, html

def e(x): return html.escape(str(x))
def gold(t): return re.sub(r'\*(.+?)\*', r'<b class="g">\1</b>', e(t))
MARK = {'v': '<svg width="34" height="34" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#2FAF72"/><path d="M6.5 12.5l3.5 3.5 7.5-8" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        'x': '<svg width="34" height="34" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#E0524F"/><path d="M8 8l8 8M16 8l-8 8" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/></svg>',
        '': '<svg width="34" height="34" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7" fill="#F2C14E"/></svg>'}

def phrases(words, maxc=28, gap=0.3):
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w); nxt = words[i + 1] if i + 1 < len(words) else None
        n = len(' '.join(x['w'] for x in cur))
        new_sent = nxt is not None and nxt['w'][:1].isupper() and nxt['w'].strip(',.?') not in ('Public', 'Gold', 'GAP', 'Tuan', 'Haji', 'Mohd', 'Zulkifli', 'Shafie')
        if nxt is None or w['w'][-1:] in ',.?!' or nxt['s'] - w['e'] > gap or n > maxc or new_sent:
            out.append(cur); cur = []
    res = []
    for k, p in enumerate(out):
        a = p[0]['s']; b = out[k + 1][0]['s'] if k + 1 < len(out) else p[-1]['e'] + 0.4
        if b - p[-1]['e'] > 0.7: b = p[-1]['e'] + 0.5
        res.append((a, b, ' '.join(x['w'] for x in p)))
    return res

def mark_key(text, keys):
    for k in keys:
        m = re.search(rf'(?<![\w-]){re.escape(k)}(?![\w-])', text, re.I)
        if m: return e(text[:m.start()]) + f'<b class="g">{e(m.group(0))}</b>' + e(text[m.end():])
    return e(text)

def build(spec, out):
    D = spec['duration']; S = spec['sections']; N = spec.get('total', 8); fy = spec.get('focus_y', 28)
    boards, js = '', []
    for i, s in enumerate(S):
        a, b = s['t']; sid = f'#s{i}'
        if s.get('cta'):
            pills = ''.join(f'<span class="pill p{j}">{e(p)}</span>' for j, p in enumerate(s.get('pills', [])))
            inner = (f'<div class="logo"><img src="{e(s["logo"])}"/></div>' if s.get('logo') else '') + f'<div class="ttl">{gold(s["title"])}</div><div class="pills">{pills}</div>'
        else:
            dots = ''.join(f'<i class="{"on" if s.get("n") and k < s["n"] else ""}"></i>' for k in range(N)) if s.get('n') else ''
            items = ''.join(f'<div class="li l{j}">{MARK.get(m, MARK[""])}<span>{gold(t)}</span></div>' for j, (m, t) in enumerate(s.get('items', [])))
            inner = (f'<div class="top"><span class="tag">{e(s.get("tag", ""))}</span><span class="dots">{dots}</span></div>'
                     f'<div class="ttl">{gold(s["title"])}</div><div class="list">{items}</div>' + (f'<div class="note">{gold(s["note"])}</div>' if s.get('note') else ''))
        boards += f'<div class="sec" id="s{i}">{inner}</div>'
        js.append(f'tl.fromTo("{sid}", {{opacity: 0, y: 40}}, {{opacity: 1, y: 0, duration: 0.35, ease: "power3.out"}}, {a:.2f});')
        js.append(f'tl.to("{sid}", {{opacity: 0, y: -30, duration: 0.25, ease: "power2.in"}}, {b - 0.25:.2f});')
        js.append(f'tl.fromTo("{sid} .ttl", {{opacity: 0, scale: 0.92}}, {{opacity: 1, scale: 1, duration: 0.4, ease: "back.out(2)"}}, {a + 0.12:.2f});')
        at = s.get('at') or []
        for j in range(len(s.get('items', s.get('pills', [])))):
            t0 = at[j] if j < len(at) else a + 0.6 + j * 0.5; cls = 'p' if s.get('cta') else 'l'
            js.append(f'tl.fromTo("{sid} .{cls}{j}", {{opacity: 0, x: -30, scale: 0.9}}, {{opacity: 1, x: 0, scale: 1, duration: 0.3, ease: "back.out(2)"}}, {t0:.2f});')
        if s.get('n'): js.append(f'tl.fromTo("{sid} .dots i.on:last-child, {sid} .dots i.on", {{scale: 0.4}}, {{scale: 1, duration: 0.3, stagger: 0.03, ease: "back.out(3)"}}, {a + 0.2:.2f});')
        if s.get('logo'): js.append(f'tl.fromTo("{sid} .logo", {{opacity: 0, scale: 0.6}}, {{opacity: 1, scale: 1, duration: 0.4, ease: "back.out(2.5)"}}, {s.get("logo_at", a + 0.1):.2f});')
    C = spec.get('captions', {}); caps, cj = '', []
    if C.get('words'):
        for j, (a, b, t) in enumerate(phrases(json.load(open(os.path.join(out, C['words']))))):
            if a >= D: continue
            caps += f'<div class="cap" id="k{j}"><span>{mark_key(t, C.get("keys", []))}</span></div>'
            cj.append(f'tl.fromTo("#k{j}", {{opacity: 0, y: 8}}, {{opacity: 1, y: 0, duration: 0.1}}, {a:.2f}); tl.to("#k{j}", {{opacity: 0, duration: 0.06}}, {min(b, D) - 0.06:.2f});')
    doc = f'''<!doctype html>
<html lang="ms">
  <head>
    <meta charset="UTF-8" /><meta name="viewport" content="width=1080, height=1920" />
    <script src="assets/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Mont"; src: url("assets/Montserrat.ttf"); font-weight: 100 900; }}
      @font-face {{ font-family: "Play"; src: url("assets/PlayfairDisplay.ttf"); font-weight: 400 900; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #0b0805; }}
      #root {{ position: relative; width: 1080px; height: 1920px; font-family: "Mont", sans-serif; color: #fff; overflow: hidden; }}
      #bgv {{ position: absolute; left: -10%; top: -10%; width: 120%; height: 120%; object-fit: cover; filter: blur(34px) brightness(.42) saturate(1.2); }}
      #tint {{ position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 30%, rgba(120,84,28,.35), rgba(10,8,5,.75) 70%); }}
      #rays {{ position: absolute; left: -40%; top: -30%; width: 180%; height: 120%;
              background: repeating-conic-gradient(from 0deg at 50% 40%, rgba(255,200,90,.05) 0deg 5deg, rgba(0,0,0,0) 5deg 13deg); }}
      #board {{ position: absolute; left: 120px; width: 840px; top: 236px; height: 500px; border-radius: 40px;
               background: linear-gradient(180deg, rgba(34,27,18,.86), rgba(12,10,8,.9)); border: 2px solid rgba(220,176,86,.75);
               box-shadow: 0 24px 60px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,230,170,.2); }}
      .sec {{ position: absolute; left: 120px; width: 840px; top: 236px; height: 500px; padding: 32px 44px; opacity: 0; display: flex; flex-direction: column; }}
      .top {{ display: flex; align-items: center; justify-content: space-between; }}
      .tag {{ font-size: 26px; font-weight: 900; letter-spacing: .16em; color: #2a1600; padding: 8px 20px; border-radius: 14px;
             background: linear-gradient(180deg, #FFE7A0, #F2C14E 60%, #D49B2A); }}
      .dots {{ display: flex; gap: 8px; }} .dots i {{ width: 16px; height: 16px; border-radius: 50%; background: rgba(255,255,255,.2); display: block; }}
      .dots i.on {{ background: #F2C14E; box-shadow: 0 0 10px rgba(242,193,78,.7); }}
      .ttl {{ font-family: "Play", serif; font-weight: 800; font-size: 50px; line-height: 1.1; margin-top: 18px; }}
      .g {{ color: #F2C14E; }}
      .list {{ display: flex; flex-direction: column; gap: 12px; margin-top: 20px; }}
      .li {{ display: flex; align-items: flex-start; gap: 16px; font-size: 34px; font-weight: 700; line-height: 1.22; opacity: 0; }}
      .li svg {{ flex: none; margin-top: 2px; }}
      .note {{ margin-top: auto; font-size: 24px; font-style: italic; opacity: .8; }}
      .sec .logo {{ align-self: center; background: #fff; border-radius: 18px; padding: 10px 26px; opacity: 0; }} .sec .logo img {{ height: 70px; display: block; }}
      .pills {{ display: flex; flex-direction: column; align-items: center; gap: 16px; margin-top: 26px; }}
      .pill {{ font-size: 36px; font-weight: 800; color: #2a1600; padding: 14px 34px; border-radius: 40px; opacity: 0;
              background: linear-gradient(180deg, #FFE7A0, #F2C14E 60%, #D49B2A); box-shadow: 0 8px 20px rgba(0,0,0,.4); }}
      .sec:has(.pills) {{ align-items: center; text-align: center; justify-content: center; }}
      #card {{ position: absolute; left: 170px; width: 740px; top: 760px; height: 580px; border-radius: 40px; overflow: hidden;
              border: 4px solid #E3B758; box-shadow: 0 0 0 10px rgba(227,183,88,.18), 0 26px 60px rgba(0,0,0,.6); }}
      #vid {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: 50% {fy}%; }}
      .cap {{ position: absolute; left: 190px; width: 700px; top: {spec.get('cap_y', 776)}px; height: 104px;   /* wall above the head: never over the face */ display: flex; align-items: center; justify-content: center; text-align: center;
             font-size: 44px; font-weight: 800; line-height: 1.15; opacity: 0; text-shadow: 0 3px 10px rgba(0,0,0,.5); }}
      .cap span {{ background: rgba(14,11,8,.74); padding: 6px 20px 9px; border-radius: 16px; box-decoration-break: clone; -webkit-box-decoration-break: clone; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{D:.2f}" data-width="1080" data-height="1920">
      <video id="bgv" class="clip" src="{e(spec["video"])}" data-start="0" data-duration="{D:.2f}" data-track-index="0" muted playsinline></video>
      <div id="tint"></div><div id="rays"></div>
      <div id="board"></div>
      <div id="card"><video id="vid" class="clip" src="{e(spec["video"])}" data-start="0" data-duration="{D:.2f}" data-track-index="1" data-has-audio="true"></video></div>
      <audio id="sfx" class="clip" src="assets/sfx.wav" data-start="0" data-duration="{D:.2f}" data-track-index="2"></audio>
      <div id="ui" class="clip" data-start="0" data-duration="{D:.2f}" data-track-index="3" style="position:absolute;inset:0">
        {boards}
        {caps}
      </div>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      tl.fromTo("#board", {{opacity: 0, y: -30}}, {{opacity: 1, y: 0, duration: 0.4}}, 0);
      tl.fromTo("#card", {{opacity: 0, scale: 0.92}}, {{opacity: 1, scale: 1, duration: 0.45, ease: "back.out(1.6)"}}, 0.05);
      tl.fromTo("#rays", {{rotation: 0}}, {{rotation: 25, duration: {D:.2f}, ease: "none"}}, 0);
      {chr(10).join("      " + x for x in js)}
      {chr(10).join("      " + x for x in cj)}
      tl.set({{}}, {{}}, {D:.2f});
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
'''
    os.makedirs(os.path.join(out, 'assets'), exist_ok=True)
    open(os.path.join(out, 'index.html'), 'w').write(doc)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import sfx
    ev = [(0.05, 'shimmer', -4)]
    for s in S:
        a = s['t'][0]; ev.append((a - 0.05, 'swoosh', -4))
        if s.get('n'): ev.append((a + 0.15, 'hit', -3))
        ev += [(t, 'pop', -2) for t in (s.get('at') or [])]
        if s.get('cta'): ev += [(a, 'swell', -3), (a + 0.2, 'coin', -2)]
    sfx.render_track(sorted(ev), D, os.path.join(out, 'assets', 'sfx.wav'), spec.get('sfx_gain_db', -11), spec.get('music_db', -14))
    print('ok', out, D)

if __name__ == '__main__':
    build(json.load(open(sys.argv[1])), sys.argv[2])
