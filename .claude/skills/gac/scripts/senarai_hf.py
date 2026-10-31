#!/usr/bin/env python3
"""List video ("10 cara ...") as a HyperFrames composition: no talking needed. A frosted glass card with a gold edge
over slow, blurred B-roll; each tip pops in with its number, an icon and a gold keyword; progress bar on top.

Usage: python3 senarai_hf.py spec.json PROJECT_DIR   (then: npx hyperframes render -o out.mp4 in PROJECT_DIR)
spec = {
  "title": "10 Cara Jimat Duit", "title_sub": "untuk *Anak Muda*", "label": "TIPS KEWANGAN",
  "items": [["Buat *bajet* setiap kali dapat gaji.", "wallet"], ...],      # *word* = gold
  "outro": "Mana satu awak *dah buat*?", "outro_sub": "Simpan & kongsi dengan kawan",
  "bg": ["assets/a.mp4", "assets/b.mp4"],                                # B-roll, played one after another (blurred)
  "intro": 3.6, "per_item": [2.4, 0.035], "outro_dur": 3.4, "music_db": -12, "sfx_gain_db": -10
}
per_item = [base seconds, extra seconds per character]: longer tips stay longer.
Icons: wallet, food, home, gift, clock, bag, scale, laptop, coins, card."""
import json, os, re, sys, html, subprocess

def e(x): return html.escape(str(x))
def gold(t): return re.sub(r'\*(.+?)\*', r'<b class="g">\1</b>', e(t))

I = {   # 64x64 line icons, gold stroke
    'wallet': '<rect x="8" y="18" width="48" height="34" rx="7"/><path d="M8 26h40a8 8 0 0 1 8 8v4a8 8 0 0 1-8 8"/><circle cx="46" cy="36" r="3"/><path d="M14 18l26-8 4 8"/>',
    'food': '<path d="M14 8v18a6 6 0 0 0 12 0V8M20 8v48"/><path d="M44 56V8c-6 4-8 14-8 22h8"/>',
    'home': '<path d="M8 30L32 10l24 20"/><path d="M14 26v28h36V26"/><rect x="27" y="38" width="10" height="16"/>',
    'gift': '<rect x="10" y="24" width="44" height="12" rx="2"/><rect x="14" y="36" width="36" height="20" rx="2"/><path d="M32 24v32M32 24c-4-10-16-12-14-4s14 4 14 4zM32 24c4-10 16-12 14-4s-14 4-14 4z"/>',
    'clock': '<circle cx="32" cy="34" r="22"/><path d="M32 22v13l9 6M24 6h16"/>',
    'bag': '<path d="M12 22h40l-4 34H16z"/><path d="M24 22v-4a8 8 0 0 1 16 0v4"/><path d="M26 36l12 12M38 36L26 48"/>',
    'scale': '<path d="M32 8v48M18 56h28M12 16h40"/><path d="M12 16L4 34h16zM52 16l-8 18h16z"/>',
    'laptop': '<rect x="12" y="12" width="40" height="28" rx="3"/><path d="M4 50h56l-4-10H8z"/><path d="M32 20v12M26 26h12"/>',
    'coins': '<ellipse cx="32" cy="16" rx="18" ry="6"/><path d="M14 16v10c0 3 8 6 18 6s18-3 18-6V16M14 26v10c0 3 8 6 18 6s18-3 18-6V26M14 36v10c0 3 8 6 18 6s18-3 18-6V36"/>',
    'card': '<rect x="6" y="16" width="52" height="34" rx="5"/><path d="M6 26h52M14 40h12"/><path d="M40 4l20 20M60 4L40 24" stroke="#FF6464"/>',
}
def icon(n, s=110):
    return f'<svg width="{s}" height="{s}" viewBox="0 0 64 64" fill="none" stroke="#F2C14E" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round">{I.get(n, I["coins"])}</svg>'

def build(spec, out):
    items = spec['items']; n = len(items)
    t = spec.get('intro', 3.6); spans = []
    for txt, _ in items:
        d = spec.get('per_item', [2.4, 0.035]); d = d[0] + d[1] * len(txt.replace('*', '')); spans.append((t, t + d)); t += d
    o0 = t; D = round(t + spec.get('outro_dur', 3.4), 2)
    # background clips, one after another, each slowly zoomed
    bg = spec.get('bg', []); bgs, bgj = '', []
    if bg:
        seg = D / len(bg)
        for k, src in enumerate(bg):
            a = k * seg
            bgs += f'<video id="bg{k}" class="clip bg" src="{e(src)}" data-start="{a:.2f}" data-duration="{seg + 0.4:.2f}" data-track-index="{k}" muted playsinline></video>'
            bgj.append(f'tl.fromTo("#bg{k}", {{scale: 1.08, opacity: {0 if k else 1}}}, {{scale: 1.18, opacity: 1, duration: {seg + 0.4:.2f}, ease: "none"}}, {a:.2f});')
    cards = ''
    for k, (txt, ic) in enumerate(items):
        cards += (f'<div class="tip" id="t{k}"><div class="ic">{icon(ic, 150)}</div><div class="num">{k + 1:02d}</div>'
                  f'<div class="txt">{gold(txt)}</div></div>')
    js = [*bgj]
    js.append('tl.fromTo("#intro .lbl", {opacity: 0, y: 20}, {opacity: 1, y: 0, duration: 0.4}, 0.1);')
    js.append('tl.fromTo("#intro .big", {opacity: 0, scale: 0.8}, {opacity: 1, scale: 1, duration: 0.5, ease: "back.out(2)"}, 0.25);')
    js.append('tl.fromTo("#intro .w", {opacity: 0, y: 30, filter: "blur(8px)"}, {opacity: 1, y: 0, filter: "blur(0px)", duration: 0.35, stagger: 0.12}, 0.4);')
    js.append('tl.fromTo("#intro .sub", {opacity: 0}, {opacity: 1, duration: 0.4}, 1.2);')
    js.append(f'tl.to("#intro", {{opacity: 0, y: -40, duration: 0.3}}, {spans[0][0] - 0.3:.2f});')
    js.append(f'tl.fromTo("#head", {{opacity: 0}}, {{opacity: 1, duration: 0.3}}, {spans[0][0]:.2f}); tl.to("#head", {{opacity: 0, duration: 0.3}}, {o0 - 0.2:.2f});')
    js.append(f'tl.fromTo("#frame", {{opacity: 0, scale: 0.9}}, {{opacity: 1, scale: 1, duration: 0.35, ease: "back.out(1.8)"}}, {spans[0][0] - 0.1:.2f}); tl.to("#frame", {{opacity: 0, scale: 0.95, duration: 0.3}}, {o0 - 0.2:.2f});')
    for k, (a, b) in enumerate(spans):
        js.append(f'tl.fromTo("#t{k}", {{opacity: 0, x: 80}}, {{opacity: 1, x: 0, duration: 0.32, ease: "power3.out"}}, {a:.2f});')
        js.append(f'tl.fromTo("#t{k} .num", {{scale: 1.6, opacity: 0}}, {{scale: 1, opacity: 1, duration: 0.35, ease: "back.out(2.5)"}}, {a + 0.05:.2f});')
        js.append(f'tl.fromTo("#t{k} .ic", {{rotation: -20, scale: 0.5}}, {{rotation: 0, scale: 1, duration: 0.4, ease: "back.out(2.5)"}}, {a + 0.12:.2f});')
        js.append(f'tl.fromTo("#t{k} .g", {{backgroundSize: "0% 100%"}}, {{backgroundSize: "100% 100%", duration: 0.45, ease: "power2.out"}}, {a + 0.5:.2f});')
        if k < n - 1: js.append(f'tl.to("#t{k}", {{opacity: 0, x: -80, duration: 0.25, ease: "power2.in"}}, {b - 0.22:.2f});')
        else: js.append(f'tl.to("#t{k}", {{opacity: 0, duration: 0.25}}, {b - 0.22:.2f});')
        js.append(f'tl.to("#bar i", {{width: "{(k + 1) / n * 100:.1f}%", duration: 0.4, ease: "power2.out"}}, {a:.2f});')
        js.append(f'tl.set("#cnt", {{textContent: "{k + 1} / {n}"}}, {a:.2f});')
    js.append(f'tl.fromTo("#outro", {{opacity: 0, scale: 0.85}}, {{opacity: 1, scale: 1, duration: 0.45, ease: "back.out(2)"}}, {o0:.2f});')
    js.append(f'tl.fromTo("#outro .sub", {{opacity: 0, y: 16}}, {{opacity: 1, y: 0, duration: 0.4}}, {o0 + 0.6:.2f});')
    tw = spec['title'].split(' '); big = tw.pop(0) if tw[0].isdigit() else ''   # "10 Cara ..." -> giant gold 10
    title_words = ' '.join(f'<span class="w">{e(w)}</span>' for w in tw)
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
      .bg {{ position: absolute; inset: 0; width: 1080px; height: 1920px; object-fit: cover; filter: blur(9px) brightness(.55) saturate(1.1); }}
      #shade {{ position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 45%, rgba(40,28,10,.15), rgba(8,6,4,.75) 75%); }}
      #ui {{ position: absolute; inset: 0; }}
      .g {{ color: #F2C14E; background-image: linear-gradient(transparent 62%, rgba(242,193,78,.28) 62%); background-repeat: no-repeat; background-size: 0% 100%; }}
      #intro {{ position: absolute; left: 80px; right: 140px; top: 520px; text-align: center; }}
      .lbl {{ font-size: 30px; font-weight: 800; letter-spacing: .32em; color: #F2C14E; }}
      #intro .big {{ font-family: "Play", serif; font-weight: 900; font-size: 260px; line-height: 1; margin-top: 10px;
                    background: linear-gradient(180deg, #FFEDB0, #F2C14E 55%, #B98018); -webkit-background-clip: text; background-clip: text; color: transparent; }}
      #intro .ttl {{ font-family: "Play", serif; font-weight: 700; font-size: 84px; line-height: 1.1; margin-top: 4px; }}
      #intro .w {{ display: inline-block; }}
      #intro .sub {{ font-size: 50px; font-weight: 700; margin-top: 18px; }}
      #head {{ position: absolute; left: 90px; width: 860px; top: 300px; opacity: 0; }}
      #head .row {{ display: flex; justify-content: space-between; align-items: baseline; }}
      #head .ttl {{ font-family: "Play", serif; font-weight: 700; font-size: 46px; }}
      #cnt {{ font-size: 34px; font-weight: 800; color: #F2C14E; }}
      #bar {{ height: 8px; border-radius: 4px; background: rgba(255,255,255,.18); margin-top: 18px; overflow: hidden; }}
      #bar i {{ display: block; height: 100%; width: 0; background: linear-gradient(90deg, #FFE7A0, #F2C14E, #D49B2A); border-radius: 4px; }}
      #frame {{ position: absolute; left: 90px; width: 860px; top: 520px; height: 820px; border-radius: 48px; opacity: 0;
               background: linear-gradient(160deg, rgba(40,30,16,.62), rgba(14,11,8,.72)); backdrop-filter: blur(24px) saturate(1.2);
               border: 2.5px solid rgba(232,190,100,.75); box-shadow: 0 30px 80px rgba(0,0,0,.6), inset 0 1px 0 rgba(255,236,180,.35); }}
      #frame::before {{ content: ""; position: absolute; inset: 16px; border-radius: 36px; border: 1px solid rgba(232,190,100,.28); }}
      .tip {{ position: absolute; left: 90px; width: 860px; top: 520px; height: 820px; padding: 70px 70px; opacity: 0;
             display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; gap: 14px; }}
      .num {{ font-family: "Play", serif; font-weight: 900; font-size: 150px; line-height: 1;
             background: linear-gradient(180deg, #FFEDB0, #F2C14E 55%, #B98018); -webkit-background-clip: text; background-clip: text; color: transparent;
             filter: drop-shadow(0 6px 14px rgba(0,0,0,.45)); }}
      .txt {{ font-size: 66px; font-weight: 800; line-height: 1.22; text-shadow: 0 4px 14px rgba(0,0,0,.45); }}
      #outro {{ position: absolute; left: 80px; right: 140px; top: 700px; text-align: center; opacity: 0; }}
      #outro .q {{ font-family: "Play", serif; font-weight: 700; font-size: 92px; line-height: 1.15; }}
      #outro .sub {{ display: inline-block; margin-top: 34px; font-size: 40px; font-weight: 800; color: #2a1600; padding: 16px 38px; border-radius: 50px;
                    background: linear-gradient(180deg, #FFE7A0, #F2C14E 60%, #D49B2A); box-shadow: 0 10px 26px rgba(0,0,0,.45); }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{D:.2f}" data-width="1080" data-height="1920">
      {bgs}
      <audio id="sfx" class="clip" src="assets/sfx.wav" data-start="0" data-duration="{D:.2f}" data-track-index="9"></audio>
      <div id="ui" class="clip" data-start="0" data-duration="{D:.2f}" data-track-index="10">
        <div id="shade"></div>
        <div id="intro"><div class="lbl">{e(spec.get("label", ""))}</div>{f'<div class="big">{e(big)}</div>' if big else ''}<div class="ttl">{title_words}</div><div class="sub">{gold(spec.get("title_sub", ""))}</div></div>
        <div id="head"><div class="row"><span class="ttl">{e(spec["title"])}</span><span id="cnt">1 / {n}</span></div><div id="bar"><i></i></div></div>
        <div id="frame"></div>
        {cards}
        <div id="outro"><div class="q">{gold(spec.get("outro", ""))}</div><div class="sub">{e(spec.get("outro_sub", ""))}</div></div>
      </div>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      {chr(10).join("      " + x for x in js)}
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
    ev = [(0.25, 'boom', -4), (0.45, 'shimmer', -3)]
    for k, (a, b) in enumerate(spans):
        ev += [(a - 0.05, 'swoosh', -4), (a + 0.08, 'pop', -1), (a + 0.5, 'tick', -8)]
    ev += [(o0, 'swell', -3), (o0 + 0.05, 'coin', -2), (o0 + 0.6, 'shimmer', -4)]
    sfx.render_track(sorted(ev), D, os.path.join(out, 'assets', 'sfx.wav'), spec.get('sfx_gain_db', -10), spec.get('music_db', -12))
    print('ok', out, 'tempoh', D)

if __name__ == '__main__':
    build(json.load(open(sys.argv[1])), sys.argv[2])
