#!/usr/bin/env python3
"""Side-by-side layout with motion (Gaya 3 look). The speaker starts FULL SCREEN with a hook card above the head,
then the video shrinks (animated) into a gold-framed 9:16 box on the LEFT while a text frame slides in on the
RIGHT. Each new section the box pops and the text frame slides in again; the speaker keeps a slow push-in.
User asked (Rakaman7): "mula video full, pastu terus kecikkan petak sebelah kiri, frame sebelah kanan tulisan,
gambar ada pergerakan". Everything sits inside TikTok's safe area (x 130-950, y 236-1340).

Usage: python3 sebelah_hf.py spec.json PROJECT_DIR
spec = {
  "video": "assets/cut.mp4", "duration": 139.9, "split_at": 5.9,   # full screen until split_at
  "hook": {"label": "SOALAN PALING KERAP", "title": "Kenapa emas di bank nampak *lebih murah*?"},
  "total": 8, "captions": {"words": "words.json", "keys": [...]},
  "broll": [{"t": [a, b], "img": "assets/emas.jpg"},               # product photos / clips inside the left box
            {"t": [a, b], "video": "assets/klip.mp4"},               # pre-trimmed 1080x1920 clip, muted
            {"t": [a, b], "img": "assets/x.jpg", "fit": "contain"}],  # whole photo visible (user: "bagi nampak semua")
  "sections": [{"t": [a, b], "tag": "SEBAB 1 / 8", "n": 1, "title": "...", "items": [["v"|"x"|"", "text"]], "at": [...], "note": "..."},
               {"t": [a, b], "cta": true, "logo": "assets/pg_logo.png", "title": "...", "pills": [...], "at": [...]}]
}"""
import json, os, re, sys, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from split_hf import e, gold, MARK, phrases, mark_key

BOX = dict(x=136, y=400, s=0.385)          # left box: the full 1080x1920 frame scaled to 416x739
PANEL = dict(x=572, y=400, w=372, h=739)   # right text frame, same height as the box

def build(spec, out):
    D = spec['duration']; S = spec['sections']; N = spec.get('total', 8); sp = spec.get('split_at', 5.9)
    secs, js = '', []
    for i, s in enumerate(S):
        a, b = s['t']; a = max(a, sp + 0.35); sid = f'#s{i}'
        if s.get('cta'):
            pills = ''.join(f'<span class="pill p{j}">{e(p)}</span>' for j, p in enumerate(s.get('pills', [])))
            inner = (f'<div class="logo"><img src="{e(s["logo"])}"/></div>' if s.get('logo') else '') + f'<div class="ttl">{gold(s["title"])}</div><div class="pills">{pills}</div>'
        else:
            dots = ''.join(f'<i class="{"on" if k < s["n"] else ""}"></i>' for k in range(N)) if s.get('n') else ''
            items = ''.join(f'<div class="li l{j}">{MARK.get(m, MARK[""])}<span>{gold(t)}</span></div>' for j, (m, t) in enumerate(s.get('items', [])))
            inner = (f'<span class="tag">{e(s.get("tag", ""))}</span>' + (f'<div class="dots">{dots}</div>' if dots else '')
                     + f'<div class="ttl">{gold(s["title"])}</div><div class="list">{items}</div>' + (f'<div class="note">{gold(s["note"])}</div>' if s.get('note') else ''))
        secs += f'<div class="sec{" cta" if s.get("cta") else ""}" id="s{i}">{inner}</div>'
        js.append(f'tl.fromTo("{sid}", {{opacity: 0, x: 60}}, {{opacity: 1, x: 0, duration: 0.4, ease: "power3.out"}}, {a:.2f});')
        js.append(f'tl.to("{sid}", {{opacity: 0, x: -40, duration: 0.22, ease: "power2.in"}}, {b - 0.22:.2f});')
        js.append(f'tl.fromTo("{sid} .ttl", {{opacity: 0, y: 14}}, {{opacity: 1, y: 0, duration: 0.35}}, {a + 0.15:.2f});')
        if s.get('n'):
            js.append(f'tl.fromTo("{sid} .tag", {{scale: 0.5, opacity: 0}}, {{scale: 1, opacity: 1, duration: 0.35, ease: "back.out(3)"}}, {a + 0.05:.2f});')
            js.append(f'tl.fromTo("#box", {{scale: {BOX["s"] * 1.06:.3f}}}, {{scale: {BOX["s"]}, duration: 0.45, ease: "back.out(2.5)", immediateRender: false}}, {a:.2f});')   # box pops each new reason
        at = s.get('at') or []
        for j in range(len(s.get('items', s.get('pills', [])))):
            t0 = at[j] if j < len(at) else a + 0.6 + j * 0.5; cls = 'p' if s.get('cta') else 'l'
            js.append(f'tl.fromTo("{sid} .{cls}{j}", {{opacity: 0, x: 24}}, {{opacity: 1, x: 0, duration: 0.3, ease: "back.out(2)"}}, {t0:.2f});')
        if s.get('logo'): js.append(f'tl.fromTo("{sid} .logo", {{opacity: 0, scale: 0.6}}, {{opacity: 1, scale: 1, duration: 0.4, ease: "back.out(2.5)"}}, {s.get("logo_at", a + 0.1):.2f});')
    # speaker: full screen -> left box, then a slow push-in that restarts every section (keeps it moving)
    js.insert(0, f'tl.to("#box", {{x: {BOX["x"]}, y: {BOX["y"]}, scale: {BOX["s"]}, duration: 0.9, ease: "power3.inOut"}}, {sp:.2f});')
    js.insert(1, f'tl.to("#box", {{borderRadius: 110, duration: 0.9, ease: "power3.inOut"}}, {sp:.2f}); tl.to("#frame", {{opacity: 1, duration: 0.5}}, {sp + 0.5:.2f});')
    js.insert(2, f'tl.fromTo("#panel", {{opacity: 0, x: 120}}, {{opacity: 1, x: 0, duration: 0.6, ease: "power3.out"}}, {sp + 0.3:.2f});')
    js.insert(3, f'tl.fromTo("#bgwrap", {{opacity: 0}}, {{opacity: 1, duration: 0.6}}, {sp:.2f});')
    starts = [max(s['t'][0], sp + 0.35) for s in S] + [D]
    for a, b in zip(starts, starts[1:]):
        js.append(f'tl.fromTo("#vid", {{scale: 1.0}}, {{scale: 1.12, duration: {b - a:.2f}, ease: "none", immediateRender: false}}, {a:.2f});')
    js.append(f'tl.fromTo("#vid", {{scale: 1.0}}, {{scale: 1.06, duration: {sp:.2f}, ease: "none"}}, 0);')
    # B-roll photos shown INSIDE the left box (voice keeps going), slow push-in; nothing drawn over the product
    brolls = ''
    for j, r in enumerate(spec.get('broll', [])):
        a, b = r['t']; pos = f' style="object-position:{r["pos"]}"' if r.get('pos') else ''   # "pos": "80% 50%" keeps a person at the edge in view
        if r.get('video'):     # a pre-trimmed 1080x1920 clip, muted
            inner = f'<video id="bv{j}" class="clip" src="{e(r["video"])}" data-start="{a:.2f}" data-duration="{b - a:.2f}" data-track-index="{10 + j}" muted playsinline></video>'
        elif r.get('fit') == 'contain':   # whole photo visible, blurred copy fills the rest of the box
            inner = f'<img class="bgfill" src="{e(r["img"])}"/><img class="whole" src="{e(r["img"])}"/>'
        else:
            inner = f'<img src="{e(r["img"])}"{pos}/>'
        brolls += f'<div class="br" id="br{j}">{inner}</div>'
        js.append(f'tl.fromTo("#br{j}", {{opacity: 0, scale: 1.0}}, {{opacity: 1, scale: 1.03, duration: 0.35, ease: "power2.out"}}, {a:.2f});')
        js.append(f'tl.to("#br{j}", {{scale: {1.06 if r.get("video") or r.get("fit") else 1.14}, duration: {b - a - 0.3:.2f}, ease: "none"}}, {a + 0.35:.2f});')
        js.append(f'tl.to("#br{j}", {{opacity: 0, duration: 0.3}}, {b - 0.3:.2f});')
    H = spec.get('hook', {})
    hook = f'<div id="hook"><div class="lbl">{e(H.get("label", ""))}</div><div class="ttl">{gold(H.get("title", ""))}</div></div>' if H else ''
    if H:
        js.append('tl.fromTo("#hook", {opacity: 0, y: -20}, {opacity: 1, y: 0, duration: 0.4}, 0.1);')
        js.append(f'tl.to("#hook", {{opacity: 0, y: -30, duration: 0.3}}, {sp - 0.1:.2f});')
    C = spec.get('captions', {}); caps, cj = '', []
    if C.get('words'):
        for j, (a, b, t) in enumerate(phrases(json.load(open(os.path.join(out, C['words']))))):
            if a >= D or b <= sp: continue          # full-screen opening: the hook card says it
            a = max(a, sp + 0.5)
            if min(b, D) - 0.1 <= a: continue      # phrase already over by the time captions start
            caps += f'<div class="cap" id="k{j}"><span>{mark_key(t, C.get("keys", []))}</span></div>'
            cj.append(f'tl.fromTo("#k{j}", {{opacity: 0, y: 8}}, {{opacity: 1, y: 0, duration: 0.1}}, {a:.2f}); tl.to("#k{j}", {{opacity: 0, duration: 0.06}}, {min(b, D) - 0.06:.2f});')
    bw, bh = int(1080 * BOX['s']), int(1920 * BOX['s'])
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
      #bgwrap {{ position: absolute; inset: 0; opacity: 0; }}
      #bgv {{ position: absolute; left: -10%; top: -10%; width: 120%; height: 120%; object-fit: cover; filter: blur(34px) brightness(.4) saturate(1.2); }}
      #tint {{ position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 40%, rgba(120,84,28,.35), rgba(10,8,5,.78) 72%); }}
      #rays {{ position: absolute; left: -40%; top: -30%; width: 180%; height: 120%;
              background: repeating-conic-gradient(from 0deg at 50% 40%, rgba(255,200,90,.05) 0deg 5deg, rgba(0,0,0,0) 5deg 13deg); }}
      #box {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; transform-origin: 0 0; overflow: hidden; border-radius: 0; }}
      #vid {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; transform-origin: 50% 30%; }}
      .br {{ position: absolute; inset: 0; opacity: 0; overflow: hidden; }}
      .br > img, .br > video {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
      .br > img.bgfill {{ filter: blur(40px) brightness(.55); transform: scale(1.2); }}
      .br > img.whole {{ object-fit: contain; }}
      #frame {{ position: absolute; left: {BOX["x"] - 6}px; top: {BOX["y"] - 6}px; width: {bw + 12}px; height: {bh + 12}px; border-radius: 44px; opacity: 0;
               border: 4px solid #E3B758; box-shadow: 0 0 0 8px rgba(227,183,88,.18), 0 24px 60px rgba(0,0,0,.6); pointer-events: none; }}
      #panel {{ position: absolute; left: {PANEL["x"]}px; top: {PANEL["y"]}px; width: {PANEL["w"]}px; height: {PANEL["h"]}px; border-radius: 34px; opacity: 0;
               background: linear-gradient(180deg, rgba(34,27,18,.9), rgba(12,10,8,.93)); border: 2px solid rgba(220,176,86,.8);
               box-shadow: 0 24px 60px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,230,170,.2); }}
      .sec {{ position: absolute; left: {PANEL["x"]}px; top: {PANEL["y"]}px; width: {PANEL["w"]}px; height: {PANEL["h"]}px; padding: 30px 26px; opacity: 0;
             display: flex; flex-direction: column; }}
      .tag {{ align-self: flex-start; font-size: 24px; font-weight: 900; letter-spacing: .14em; color: #2a1600; padding: 7px 16px; border-radius: 12px;
             background: linear-gradient(180deg, #FFE7A0, #F2C14E 60%, #D49B2A); }}
      .dots {{ display: flex; gap: 7px; margin-top: 14px; }} .dots i {{ width: 13px; height: 13px; border-radius: 50%; background: rgba(255,255,255,.2); display: block; }}
      .dots i.on {{ background: #F2C14E; box-shadow: 0 0 8px rgba(242,193,78,.7); }}
      .ttl {{ font-family: "Play", serif; font-weight: 800; font-size: 46px; line-height: 1.1; margin-top: 16px; }}
      .g {{ color: #F2C14E; }}
      .list {{ display: flex; flex-direction: column; gap: 14px; margin-top: 22px; }}
      .li {{ display: flex; align-items: flex-start; gap: 12px; font-size: 30px; font-weight: 700; line-height: 1.22; opacity: 0; }}
      .li svg {{ flex: none; width: 30px; height: 30px; margin-top: 1px; }}
      .note {{ margin-top: auto; font-size: 20px; font-style: italic; opacity: .8; }}
      .sec.cta {{ align-items: center; justify-content: center; text-align: center; }}
      .sec .logo {{ background: #fff; border-radius: 16px; padding: 8px 20px; opacity: 0; }} .sec .logo img {{ height: 66px; display: block; }}
      .pills {{ display: flex; flex-direction: column; align-items: center; gap: 14px; margin-top: 24px; }}
      .pill {{ font-size: 30px; font-weight: 800; color: #2a1600; padding: 12px 22px; border-radius: 36px; opacity: 0;
              background: linear-gradient(180deg, #FFE7A0, #F2C14E 60%, #D49B2A); box-shadow: 0 8px 20px rgba(0,0,0,.4); }}
      #hook {{ position: absolute; left: 140px; right: 140px; top: 250px; padding: 22px 30px 26px; border-radius: 26px; text-align: center; opacity: 0;
              background: linear-gradient(180deg, rgba(34,27,18,.88), rgba(12,10,8,.9)); border: 2px solid rgba(220,176,86,.75); box-shadow: 0 16px 40px rgba(0,0,0,.45); }}
      #hook .lbl {{ font-size: 24px; font-weight: 800; letter-spacing: .28em; color: #E7B958; }}
      #hook .ttl {{ font-size: 52px; margin-top: 8px; }}
      .sec .ttl {{ font-size: 46px; }}
      .cap {{ position: absolute; left: 136px; width: 808px; top: 1166px; height: 120px; display: flex; align-items: center; justify-content: center; text-align: center;
             font-size: 46px; font-weight: 800; line-height: 1.15; opacity: 0; text-shadow: 0 3px 10px rgba(0,0,0,.5); }}
      .cap span {{ background: rgba(14,11,8,.74); padding: 6px 22px 9px; border-radius: 16px; box-decoration-break: clone; -webkit-box-decoration-break: clone; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{D:.2f}" data-width="1080" data-height="1920">
      <div id="bgwrap"><video id="bgv" class="clip" src="{e(spec["video"])}" data-start="0" data-duration="{D:.2f}" data-track-index="0" muted playsinline></video><div id="tint"></div><div id="rays"></div></div>
      <div id="box"><video id="vid" class="clip" src="{e(spec["video"])}" data-start="0" data-duration="{D:.2f}" data-track-index="1" data-has-audio="true"></video>{brolls}</div>
      <div id="frame"></div>
      <audio id="sfx" class="clip" src="assets/sfx.wav" data-start="0" data-duration="{D:.2f}" data-track-index="2"></audio>
      <div id="ui" class="clip" data-start="0" data-duration="{D:.2f}" data-track-index="3" style="position:absolute;inset:0">
        {hook}
        <div id="panel"></div>
        {secs}
        {caps}
      </div>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
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
    import sfx
    ev = [(0.1, 'shimmer', -4), (sp, 'whoosh', 0), (sp + 0.3, 'swoosh', -4)]
    for s in S:
        a = max(s['t'][0], sp + 0.35); ev.append((a - 0.05, 'swoosh', -4))
        if s.get('n'): ev.append((a + 0.1, 'hit', -3))
        ev += [(t, 'pop', -2) for t in (s.get('at') or [])]
        if s.get('cta'): ev += [(a, 'swell', -3), (a + 0.2, 'coin', -2)]
    for r in spec.get('broll', []): ev += [(r['t'][0], 'whoosh', -3), (r['t'][0] + 0.3, 'shimmer', -5)]
    sfx.render_track(sorted(ev), D, os.path.join(out, 'assets', 'sfx.wav'), spec.get('sfx_gain_db', -11), spec.get('music_db', -14))
    print('ok', out, D)

if __name__ == '__main__':
    build(json.load(open(sys.argv[1])), sys.argv[2])
