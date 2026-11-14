"""Vlog "a day in my life" (HyperFrames): the day's clips already cut into assets/base.mp4 (see build/vlog1/make_base.py),
with an intro title, one label per activity, captions only where someone speaks, an end card, music bed + soft SFX.
Usage: python3 vlog_hf.py spec.json PROJECT
spec = {
  "video": "assets/base.mp4", "duration": 48.36,
  "title": {"t": [0.15, 2.0], "big": "a day in my life", "small": "DEALER PUBLIC GOLD"},
  "labels": [{"t": [a, b], "text": "Pagi • hantar anak mengaji 📖"}],          # top pill, one per activity
  "captions": [{"t": [a, b], "text": "Ini adalah ruang dan *peluang*"}],      # speech only; *gold* words
  "end": {"t": [a, b], "lines": ["Penat, tapi *berbaloi*", "Sabar & konsisten menabung emas"], "pill": "Follow untuk vlog seterusnya"},
  "cuts": [t, ...], "music_db": -20, "silent": false   # silent: no sound at all; labels may have "sub"
}"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from split_hf import e, gold
import sfx

def build(spec, out):
    D = spec['duration']; js, html, ev = [], '', []
    T = spec.get('title')
    if T:
        a, b = T['t']
        html += f'<div id="title"><div class="big">{e(T["big"])}</div><div class="small">{e(T.get("small", ""))}</div></div>'
        js += [f'tl.fromTo("#title .big", {{opacity: 0, y: 40, filter: "blur(12px)"}}, {{opacity: 1, y: 0, filter: "blur(0px)", duration: 0.7, ease: "power3.out"}}, {a:.2f});',
               f'tl.fromTo("#title .small", {{opacity: 0, y: 20}}, {{opacity: 1, y: 0, duration: 0.5}}, {a + 0.35:.2f});',
               f'tl.to("#title", {{opacity: 0, y: -30, duration: 0.35}}, {b - 0.35:.2f});']
        ev += [(a, 'shimmer', -6)]
    for i, L in enumerate(spec.get('labels', [])):
        a, b = L['t']
        sub = f'<small>{gold(L["sub"])}</small>' if L.get('sub') else ''
        html += f'<div class="lab" id="l{i}"><i></i><span>{gold(L["text"])}{sub}</span></div>'
        js += [f'tl.fromTo("#l{i}", {{opacity: 0, y: -24, scale: 0.92}}, {{opacity: 1, y: 0, scale: 1, duration: 0.45, ease: "back.out(2)"}}, {a:.2f});',
               f'tl.fromTo("#l{i} i", {{scale: 0}}, {{scale: 1, duration: 0.3, ease: "back.out(3)"}}, {a + 0.25:.2f});',
               f'tl.to("#l{i}", {{opacity: 0, y: -16, duration: 0.3}}, {b - 0.3:.2f});']
        ev += [(a, 'pop', -8)]
    for i, C in enumerate(spec.get('captions', [])):
        a, b = C['t']
        html += f'<div class="cap" id="c{i}"><span>{gold(C["text"])}</span></div>'
        js += [f'tl.fromTo("#c{i}", {{opacity: 0, y: 10}}, {{opacity: 1, y: 0, duration: 0.12}}, {a:.2f});',
               f'tl.to("#c{i}", {{opacity: 0, duration: 0.08}}, {b - 0.08:.2f});']
    E = spec.get('end')
    if E:
        a, b = E['t']
        lines = ''.join(f'<div class="el{" big" if j == 0 else ""}">{gold(t)}</div>' for j, t in enumerate(E['lines']))
        html += f'<div id="endshade"></div><div id="end">{lines}' + (f'<div class="pill">{e(E["pill"])}</div>' if E.get('pill') else '') + '</div>'
        js += [f'tl.fromTo("#endshade", {{opacity: 0}}, {{opacity: 1, duration: 0.6}}, {a:.2f});']
        for j in range(len(E['lines'])):
            js.append(f'tl.fromTo("#end .el:nth-child({j + 1})", {{opacity: 0, y: 30, filter: "blur(10px)"}}, {{opacity: 1, y: 0, filter: "blur(0px)", duration: 0.6, ease: "power3.out"}}, {a + 0.3 + j * 0.6:.2f});')
        if E.get('pill'):
            js.append(f'tl.fromTo("#end .pill", {{opacity: 0, scale: 0.7}}, {{opacity: 1, scale: 1, duration: 0.45, ease: "back.out(2.5)"}}, {a + 0.4 + len(E["lines"]) * 0.6:.2f});')
        ev += [(a + 0.3, 'shimmer', -6)]
    ev += [(t - 0.12, 'whoosh', -12) for t in spec.get('cuts', [])]
    silent = spec.get('silent')   # user: "mute kan semua sound" (she adds a TikTok sound herself)
    if not silent: sfx.render_track(ev, D, os.path.join(out, 'assets', 'sfx.wav'), gain_db=-10, music_db=spec.get('music_db', -20))
    vid_audio = ' muted' if silent else ' data-has-audio="true"'
    sfx_el = '' if silent else f'<audio id="sfx" class="clip" src="assets/sfx.wav" data-start="0" data-duration="{D:.2f}" data-track-index="1"></audio>'
    doc = f'''<!doctype html>
<html lang="ms">
  <head>
    <meta charset="UTF-8" /><meta name="viewport" content="width=1080, height=1920" />
    <script src="assets/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "InstSerifItalic"; src: url("assets/InstrumentSerif-Italic.ttf"); }}
      @font-face {{ font-family: "Jak"; src: url("assets/PlusJakartaSans.ttf"); font-weight: 200 800; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; font-family: "Jak", sans-serif; color: #fff; }}
      #vid {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
      #title {{ position: absolute; left: 0; right: 0; top: 700px; text-align: center; text-shadow: 0 6px 30px rgba(0,0,0,.55); }}
      #title .big {{ font-family: "InstSerifItalic"; font-size: 150px; line-height: 1; opacity: 0; }}
      #title .small {{ font-size: 36px; font-weight: 800; letter-spacing: .32em; color: #F2C14E; margin-top: 26px; opacity: 0; }}
      .lab {{ position: absolute; top: 300px; left: 50%; transform: translateX(-50%); display: flex; align-items: center; gap: 18px; white-space: nowrap;
             padding: 20px 34px 22px 26px; border-radius: 60px; background: rgba(255,255,255,.88); color: #2a1d0c; font-size: 42px; font-weight: 800;
             box-shadow: 0 14px 40px rgba(0,0,0,.28); opacity: 0; max-width: 820px; }}
      .lab i {{ width: 22px; height: 22px; border-radius: 50%; background: linear-gradient(180deg, #FFE7A0, #D49B2A); flex: none; display: block; }}
      .lab span {{ display: block; }}
      .lab small {{ display: block; font-size: 30px; font-weight: 700; color: #6b5a3e; margin-top: 4px; }}
      .g {{ color: #C8901F; }}
      .cap {{ position: absolute; left: 130px; width: 820px; top: 1180px; text-align: center; font-size: 50px; font-weight: 800; line-height: 1.2; opacity: 0; }}
      .cap span {{ background: rgba(14,11,8,.72); padding: 8px 24px 12px; border-radius: 18px; box-decoration-break: clone; -webkit-box-decoration-break: clone; }}
      .cap .g {{ color: #F2C14E; }}
      #endshade {{ position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 45%, rgba(10,8,5,.35), rgba(10,8,5,.78)); opacity: 0; }}
      #end {{ position: absolute; left: 130px; right: 130px; top: 640px; text-align: center; }}
      #end .el {{ font-size: 54px; font-weight: 800; margin-top: 26px; opacity: 0; text-shadow: 0 4px 20px rgba(0,0,0,.5); }}
      #end .el.big {{ font-family: "InstSerifItalic"; font-weight: 400; font-size: 118px; line-height: 1.05; margin-top: 0; }}
      #end .el .g, #title .g {{ color: #F2C14E; }}
      #end .pill {{ display: inline-block; margin-top: 54px; font-size: 40px; font-weight: 800; color: #2a1600; padding: 18px 40px; border-radius: 60px;
                   background: linear-gradient(180deg, #FFE7A0, #F2C14E 60%, #D49B2A); opacity: 0; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{D:.2f}" data-width="1080" data-height="1920">
      <video id="vid" class="clip" src="{e(spec["video"])}" data-start="0" data-duration="{D:.2f}" data-track-index="0"{vid_audio}></video>
      {sfx_el}
      <div id="ui" class="clip" data-start="0" data-duration="{D:.2f}" data-track-index="2" style="position:absolute;inset:0">
        {html}
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
</html>'''
    open(os.path.join(out, 'index.html'), 'w').write(doc)
    print('ok', out, D)

if __name__ == '__main__':
    build(json.load(open(sys.argv[1])), sys.argv[2])
