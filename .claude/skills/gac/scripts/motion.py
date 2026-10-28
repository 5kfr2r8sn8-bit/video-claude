#!/usr/bin/env python3
"""Full-screen motion-graphic scenes (B-roll) built from the user's icons, text and numbers.
Look: "premium dark" (near-black background, warm gold glow, word-by-word kinetic text,
soft fades), the gold-dealer take on the Apple-keynote / Vox explainer style.

Usage (standalone):  python3 motion.py scene.json OUT.mp4
Scene spec:
  {"type": "drop", "dur": 5.0, "icons": "ikon",
   "text": [["Simpan ", "white"], ["sikit-sikit", "gold"]], "text2": [["setiap bulan", "white"]],
   "container": "tabung", "item": "dinar", "count": 5,
   "labels": ["Jan", "Feb", "Mac", "Apr", "Mei"], "label_icon": "kalendar"}
"""
import sys, os, json, math, random, subprocess, tempfile, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
import sfx, doc as docmod

GOLD = (247, 178, 40); WHITE = (255, 255, 255)
def C(c): return dict(gold=GOLD, white=WHITE).get(c, c) if isinstance(c, str) else tuple(c)
def ease(p): p = max(0.0, min(1.0, p)); return p * p * (3 - 2 * p)
def ease_out(p): p = max(0.0, min(1.0, p)); return 1 - (1 - p) ** 3

MED = [(docmod.MONT, 0, 'SemiBold'), ('/System/Library/Fonts/Avenir Next.ttc', 5), ('/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf', 0)] + docmod.BOLD

BACKDROP = [False]   # True: scene is drawn on a transparent canvas and laid over the dimmed, blurred video

def background(W, H):
    """Near-black with a warm gold glow behind the subject and a little grain."""
    if BACKDROP[0]: return Image.new('RGBA', (W, H), (0, 0, 0, 0))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    base = np.dstack([np.full((H, W), v, np.float32) for v in (12, 10, 8)])
    base *= (1 - 0.35 * (yy / H))[..., None]
    r = np.sqrt(((xx - W / 2) / (W * 0.55)) ** 2 + ((yy - H * 0.58) / (H * 0.32)) ** 2)
    glow = np.clip(1 - r, 0, 1) ** 2
    base += glow[..., None] * np.array([70, 46, 10], np.float32)
    base += np.random.RandomState(1).normal(0, 2.2, (H, W, 1))
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')

_DOT = {}
def bg_at(bg, t, W, H, n=0):
    """Background, optionally with slow-drifting soft gold particles (off by default: not part of
    the Gaku look; turn on with "particles": true on a scene)."""
    fr = bg.copy(); rs = np.random.RandomState(7)
    if not n: return fr
    if 'dot' not in _DOT:
        d = Image.new('RGBA', (120, 120), (0, 0, 0, 0)); ImageDraw.Draw(d).ellipse((30, 30, 90, 90), fill=(255, 196, 90, 255))
        _DOT['dot'] = d.filter(ImageFilter.GaussianBlur(14))
    for i in range(n):
        x0, y0, sp, sz, ph = rs.uniform(0, W), rs.uniform(0, H), rs.uniform(8, 26), rs.uniform(0.25, 1.1), rs.uniform(0, 6.3)
        y = (y0 - sp * t) % (H + 120) - 60; x = x0 + 18 * math.sin(t * 0.4 + ph)
        a = (0.25 + 0.2 * math.sin(t * 0.8 + ph)) * (0.5 + 0.5 * sz)
        dot = _DOT['dot'].resize((int(120 * sz), int(120 * sz)))
        dot.putalpha(dot.getchannel('A').point(lambda v, a=a: int(v * a)))
        fr.alpha_composite(dot, (int(x - dot.width / 2), int(y - dot.height / 2)))
    return fr

def sweep(im, t, start, dur=0.9, width=0.18):
    """One diagonal light sweep across the opaque parts of `im` (the classic gold shine)."""
    p = (t - start) / dur
    if p <= 0 or p >= 1: return im
    w, h = im.size; xx = np.arange(w)[None, :] + np.arange(h)[:, None] * 0.35
    c = (-0.2 + 1.4 * p) * (w + h * 0.35); band = np.clip(1 - np.abs(xx - c) / (width * w), 0, 1) ** 2
    a = np.array(im.getchannel('A'), np.float32) / 255 * band * 0.85
    hl = Image.new('RGBA', (w, h), (255, 246, 220, 0)); hl.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    out = im.copy(); out.alpha_composite(hl); return out

H_PORTRAIT = [True]   # set per render (scenes are called with W, H)
SAFE_TOP, SAFE_BOTTOM = 230, 1490   # portrait 1080x1920: clear of the TikTok/Reels top tabs and bottom caption/username area
def lines_top(lines, y, W, H):
    """Start y for a stack of kinetic lines, moved up if the stack would reach the bottom UI zone."""
    if H <= W: return y
    block = sum(ln.get('size', 84) * 1.4 for ln in lines)
    if y + block > SAFE_BOTTOM:
        key = 'safe:' + ' / '.join(' '.join(t for t, _ in ln['parts']) for ln in lines)
        if key not in _WARNED: _WARNED.add(key); print(f'NOTE moved scene lines up into the safe zone: {key[5:]}', file=sys.stderr)
        y = SAFE_BOTTOM - block
    return y

_WARNED = set()
def kinetic(parts, t, W, y, size=84, start=0.0, per_word=0.16, font=MED, bold=None):
    """One line of text revealed word by word (fade + rise), centred at y. parts: [[text, colour], ...]"""
    fr, fb = docmod._font(font, size), docmod._font(bold or docmod.BOLD, size)
    words = []
    for txt, col in parts:
        for w in txt.split(' '):
            if w: words.append((w, C(col), fb if col != 'white' else fr))
    sp = fr.getlength(' ')
    glue = [i > 0 and all(ch in '?!.,:;%)' for ch in w) for i, (w, _, _) in enumerate(words)]   # punctuation sticks to the word before
    total = sum(f.getlength(w) for w, _, f in words) + sp * (len(words) - 1 - sum(glue))
    max_w = 840 if H_PORTRAIT[0] else W - 100   # portrait: stay clear of the right-hand like/comment/share buttons
    if total > max_w:   # never let a scene line run off screen or under the buttons: shrink it (and say so once)
        key = ' '.join(w for w, _, _ in words)
        if key not in _WARNED:
            _WARNED.add(key); print(f'WARNING scene text too wide at size {size}, shrinking: {key}', file=sys.stderr)
        return kinetic(parts, t, W, y, int(size * (max_w - 20) / total), start, per_word, font, bold)
    im = Image.new('RGBA', (W, int(size * 2)), (0, 0, 0, 0)); x = (W - total) / 2
    for i, (w, col, f) in enumerate(words):
        if glue[i]: x -= sp
        p = ease_out((t - start - i * per_word) / 0.45)
        if p > 0:
            layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
            ImageDraw.Draw(layer).text((x, size * 0.35 + (1 - p) * 26), w, font=f, fill=col + (int(255 * p),))
            im.alpha_composite(layer)
        x += f.getlength(w) + sp
    if BACKDROP[0]:   # over un-dimmed bokeh footage: soft dark halo so white/gold text stays readable
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); sh.putalpha(im.getchannel('A').point(lambda v: int(v * 0.75)))
        out = sh.filter(ImageFilter.GaussianBlur(max(6, size // 9))); out.alpha_composite(im); im = out
    return im, int(y - size)

def load(icon_dir, name, h):
    return docmod.load_icon(docmod.find_icon(icon_dir, name), h)

def glow_shadow(im, blur=22, alpha=0.55, col=(0, 0, 0)):
    sh = Image.new('RGBA', im.size, col + (0,)); sh.putalpha(im.getchannel('A').point(lambda v: int(v * alpha)))
    pad = 60; out = Image.new('RGBA', (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)), (pad, pad + 18)); out.alpha_composite(im, (pad, pad))
    return out, pad

def paste_c(fr, im, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if scale != 1.0: im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if rot: im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1: im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * alpha)))
    fr.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

# ------------------------------------------------------------------ scenes
def scene_drop(spec, W, H):
    """Items (coins) drop one by one into a container (piggy bank), with a label ticking per drop."""
    d = spec.get('icons_dir', spec.get('icons', '.')); dur = spec.get('dur', 5.0)
    cont, cpad = glow_shadow(load(d, spec['container'], spec.get('container_h', 560)))
    item = load(d, spec['item'], spec.get('item_h', 150))
    lab_ic = load(d, spec['label_icon'], 130) if spec.get('label_icon') else None
    n = spec.get('count', 5); labels = spec.get('labels', [])
    t0 = spec.get('drop_at', spec.get('start', 1.1)); fall = 0.55; gap = spec.get('gap', (dur - t0 - 1.2) / max(1, n))   # drop_at: original time (converted like every *_at)
    cx, cy = W / 2, H * spec.get('y', 0.60); slot_y = cy - (cont.height - 2 * cpad) * 0.38
    drops = [t0 + i * gap for i in range(n)]
    events = [(0.05, 'whoosh')] + [(s + fall, 'coin') for s in drops]
    bg = background(W, H); rnd = random.Random(4)
    spins = [rnd.uniform(-25, 25) for _ in range(n)]; xs = [rnd.uniform(-60, 60) for _ in range(n)]

    def frame(t):
        fr = bg_at(bg, t, W, H, 38 if spec.get('particles') else 0)
        a_in = ease(t / 0.4) * ease((dur - t) / 0.35)                     # fade from/to black at the ends
        if spec.get('lines'):   # lines timed to the speech, stacked from the top
            yy = H * spec.get('lines_y', 0.14)
            for ln in spec['lines']:
                sz = ln.get('size', 84); im, ty2 = kinetic(ln['parts'], t, W, yy + sz, sz, start=ln['at'])
                fr.alpha_composite(im, (0, ty2)); yy += sz * 1.4
        else:
            tx, ty = kinetic(spec.get('text', []), t, W, H * 0.20, spec.get('size', 88), start=0.15)
            fr.alpha_composite(tx, (0, ty))
        if spec.get('text2') and not spec.get('lines'):
            tx, ty = kinetic(spec['text2'], t, W, H * 0.20 + spec.get('size', 88) * 1.25, spec.get('size', 88), start=0.55)
            fr.alpha_composite(tx, (0, ty))
        # container pops in, then bounces a little on every landing
        p = ease_out((t - 0.45) / 0.5); bounce = 0.0
        for s in drops:
            q = t - (s + fall)
            if 0 <= q < 0.35: bounce = max(bounce, math.sin(q / 0.35 * math.pi) * 0.035)
        if p > 0: paste_c(fr, cont, cx, cy, (0.85 + 0.15 * p) * (1 + bounce), p)
        # falling items
        for i, s in enumerate(drops):
            q = (t - s) / fall
            if 0 <= q <= 1.15:
                y = H * 0.30 + (slot_y - H * 0.30) * min(1, q) ** 2
                sc = 1.0 if q < 0.85 else max(0.2, 1 - (q - 0.85) * 3)
                paste_c(fr, item, cx + xs[i] * (1 - q), y, sc, min(1, (1.15 - q) * 4), spins[i] * (1 - q))
        # label (month) ticks with every drop
        k = sum(1 for s in drops if t >= s + fall)
        if lab_ic is not None and k:
            q = ease_out((t - (drops[k - 1] + fall)) / 0.3)
            f = docmod._font(docmod.BOLD, 64); txt = labels[k - 1] if k - 1 < len(labels) else str(k)
            row = Image.new('RGBA', (W, 170), (0, 0, 0, 0)); row.alpha_composite(lab_ic, (int(W / 2 - 150 - lab_ic.width / 2), 20))
            ImageDraw.Draw(row).text((W / 2 - 60, 85), txt, font=f, fill=GOLD, anchor='lm')
            paste_c(fr, row, W / 2, H * 0.86, 0.9 + 0.1 * q, q)
        black = Image.new('RGBA', (W, H), (0, 0, 0, int(255 * (1 - a_in))))
        fr.alpha_composite(black)
        return fr
    return frame, dur, events

def _fade(fr, t, dur, W, H, d=0.3):
    a_in = ease(t / d) * ease((dur - t) / d)
    if BACKDROP[0]:
        if a_in < 1: fr.putalpha(fr.getchannel('A').point(lambda v: int(v * a_in)))
        return fr
    if a_in < 1: fr.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * (1 - a_in)))))
    return fr

def _pop(t, at, d=0.45):
    """(scale, alpha) for an element that pops in at time `at`."""
    p = ease_out((t - at) / d)
    return 0.8 + 0.2 * p, p

def scene_kinetic(spec, W, H):
    """Lines of text revealed word by word at their own times, stacked down the screen, with
    optional icons. lines: [{"at", "parts", "size"}], icons: [{"at", "icon", "h", "y"}]"""
    d = spec.get('icons_dir', '.'); dur = spec['dur']; bg = background(W, H)
    lines = spec.get('lines', [])
    ics = [(ic, load(d, ic['icon'], ic.get('h', 320))) for ic in spec.get('icon_list', [])]
    lead = lambda ln: ln.get('size', 92) * ln.get('lead', 1.6)
    text_h = sum(lead(ln) for ln in lines); icon_h = max([im.height + 120 for _, im in ics] or [0])
    y = H * spec['top'] if 'top' in spec else (H * 0.47 - (text_h + icon_h) / 2)   # centre the whole group
    pos = []
    for ln in lines:
        sz = ln.get('size', 92); pos.append(y + sz); y += lead(ln)
    icon_y = (y + 60 + icon_h / 2 - 60) / H
    events = [(ln['at'], 'whoosh') for ln in lines[:1]] + [(ic['at'], 'pop') for ic, _ in ics]
    def frame(t):
        fr = bg_at(bg, t, W, H, 38 if spec.get('particles') else 0)
        for ln, yy in zip(lines, pos):
            im, ty = kinetic(ln['parts'], t, W, yy, ln.get('size', 92), start=ln['at'], per_word=ln.get('per_word', 0.13))
            fr.alpha_composite(im, (0, ty))
        for ic, im in ics:
            sc, al = _pop(t, ic['at'])
            if al > 0: paste_c(fr, glow_shadow(im)[0], W * ic.get('x', 0.5), H * ic.get('y', icon_y), sc, al)   # optional x: several icons side by side
        return _fade(fr, t, dur, W, H)
    return frame, dur, events

def scene_compare(spec, W, H):
    """Title + rows that slide in, each with a ✗/✓ (or any) icon. rows: [{"at", "icon", "text"}]"""
    d = spec.get('icons_dir', '.'); dur = spec['dur']; bg = background(W, H)
    rows = [(r, load(d, r['icon'], 190)) for r in spec.get('rows', [])]
    f = docmod._font(docmod.BOLD, spec.get('row_size', 80))
    if rows:   # one size for every row: the largest that lets the longest row fit beside the side buttons
        cap = (840 if H > W else W - 100) - max(ic.width for _, ic in rows) - 40
        while max(f.getlength(r['text']) for r, _ in rows) > cap and f.size > 40: f = docmod._font(docmod.BOLD, f.size - 2)
    events = [(r['at'], 'pop') for r, _ in rows]
    def frame(t):
        fr = bg_at(bg, t, W, H, 38 if spec.get('particles') else 0)
        if spec.get('title'):
            ti = spec['title']; im, ty = kinetic(ti['parts'], t, W, H * 0.47 - len(rows) * 135 - 120, ti.get('size', 90), start=ti['at'])
            fr.alpha_composite(im, (0, ty))
        y = H * 0.47 - len(rows) * 135 + 20
        for r, ic in rows:
            p = ease_out((t - r['at']) / 0.45)
            if p > 0:
                dx = (1 - p) * -80
                ff = f; tw = ff.getlength(r['text']); cap = (840 if H > W else W - 100) - ic.width - 40
                while tw > cap and ff.size > 40: ff = docmod._font(docmod.BOLD, ff.size - 2); tw = ff.getlength(r['text'])   # stay clear of the side buttons
                if spec.get('align', 'left') == 'left':   # rows share one left edge; the block as a whole is centred
                    x0 = (W - (max(i_.width for _, i_ in rows) + 40 + max(ff.getlength(r_['text']) for r_, _ in rows))) / 2
                else: x0 = (W - (ic.width + 40 + tw)) / 2   # centre each row on its own
                row = Image.new('RGBA', (W, 240), (0, 0, 0, 0)); row.alpha_composite(ic, (int(x0), int((240 - ic.height) / 2)))
                tl_ = Image.new('RGBA', row.size, (0, 0, 0, 0)); ImageDraw.Draw(tl_).text((x0 + ic.width + 40, 120), r['text'], font=ff, fill=C(r.get('color', 'white')), anchor='lm')
                if BACKDROP[0]:   # soft dark halo behind row text over the bokeh video (same as kinetic lines)
                    sh_ = Image.new('RGBA', row.size, (0, 0, 0, 0)); sh_.putalpha(tl_.getchannel('A').point(lambda v: int(v * 0.75)))
                    row.alpha_composite(sh_.filter(ImageFilter.GaussianBlur(max(6, ff.size // 9))))
                row.alpha_composite(tl_)
                paste_c(fr, row, W / 2 + dx, y + 120, 1.0, p)
            y += 270
        return _fade(fr, t, dur, W, H)
    return frame, dur, events

def scene_counter(spec, W, H):
    """Big gold number counting up to a value the speaker said, with icon and text."""
    d = spec.get('icons_dir', '.'); dur = spec['dur']; bg = background(W, H)
    ic = load(d, spec['icon'], spec.get('h', 420)) if spec.get('icon') else None
    at = spec.get('at', 0.3); ct = spec.get('count_time', 1.1)
    events = [(at + k * 0.09, 'tick') for k in range(int(ct / 0.09))] + [(at + ct, 'coin')]
    def frame(t):
        fr = bg_at(bg, t, W, H, 38 if spec.get('particles') else 0)
        if spec.get('title'):
            ti = spec['title']; im, ty = kinetic(ti['parts'], t, W, H * 0.20, ti.get('size', 84), start=ti['at'])
            fr.alpha_composite(im, (0, ty))
        if ic is not None:
            sc, al = _pop(t, spec.get('icon_at', at))
            if al > 0: paste_c(fr, glow_shadow(ic)[0], W / 2, H * 0.42, sc, al)
        p = ease_out((t - at) / ct)
        if t >= at:
            v = spec.get('from', 0) + (spec['to'] - spec.get('from', 0)) * p
            txt = f"{spec.get('prefix', '')}{v:,.0f}{spec.get('suffix', '')}"
            sz_ = spec.get('size', 210); fn = docmod._font(docmod.HEAVY, sz_); full = f"{spec.get('prefix', '')}{spec['to']:,.0f}{spec.get('suffix', '')}"
            while fn.getlength(full) > (840 if H > W else W - 120) and sz_ > 60: sz_ -= 6; fn = docmod._font(docmod.HEAVY, sz_)   # final value must fit
            im = Image.new('RGBA', (W, 320), (0, 0, 0, 0))
            dr = ImageDraw.Draw(im); dr.text((W / 2, 160), txt, font=fn, fill=GOLD, anchor='mm')
            if spec.get('shine'): im = sweep(im, t, at + ct + 0.1)   # optional gold shine (not Gaku)
            g = im.filter(ImageFilter.GaussianBlur(24)); fr.alpha_composite(g, (0, int(H * 0.64 - 160))); fr.alpha_composite(im, (0, int(H * 0.64 - 160)))
        if spec.get('sub'):
            sb = spec['sub']; im, ty = kinetic(sb['parts'], t, W, H * 0.76, sb.get('size', 72), start=sb['at'])
            fr.alpha_composite(im, (0, ty))
        return _fade(fr, t, dur, W, H)
    return frame, dur, events

def pill(text, icon='link', size=50):
    """Minimal CTA pill: dark glass, thin gold rim, small gold glyph (link | pin | arrow), white text."""
    f = docmod._font(docmod.BOLD, size); tw = f.getlength(text); h = int(size * 2.1); w = int(tw + h * 1.9)
    im = Image.new('RGBA', (w + 40, h + 40), (0, 0, 0, 0)); sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((20, 26, w + 20, h + 26), h // 2, fill=(0, 0, 0, 120)); im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(im); d.rounded_rectangle((20, 20, w + 20, h + 20), h // 2, fill=(14, 11, 8, 215), outline=__import__('theme').RIM, width=3)
    cx, cy, r = 20 + h * 0.62, 20 + h / 2, h * 0.2
    if icon == 'pin':      # map pin
        d.ellipse((cx - r, cy - r * 1.25, cx + r, cy + r * 0.75), fill=GOLD); d.polygon([(cx - r * 0.75, cy), (cx + r * 0.75, cy), (cx, cy + r * 1.5)], fill=GOLD)
        d.ellipse((cx - r * 0.38, cy - r * 0.63, cx + r * 0.38, cy + r * 0.13), fill=(14, 11, 8))
    elif icon == 'arrow':  # up arrow
        d.polygon([(cx, cy - r * 1.3), (cx + r, cy - r * 0.2), (cx - r, cy - r * 0.2)], fill=GOLD); d.rectangle((cx - r * 0.3, cy - r * 0.3, cx + r * 0.3, cy + r * 1.2), fill=GOLD)
    else:                  # two linked rings
        for dx in (-r * 0.55, r * 0.55):
            d.rounded_rectangle((cx + dx - r, cy - r * 0.55, cx + dx + r, cy + r * 0.55), r * 0.55, outline=GOLD, width=4)
    d.text((20 + h * 1.15, cy), text, font=f, fill=(255, 255, 255), anchor='lm')
    return im

def scene_hero(spec, W, H):
    """One big icon/product with a glow, plus up to three kinetic lines under it."""
    d = spec.get('icons_dir', '.'); dur = spec['dur']; bg = background(W, H)
    ic = load(d, spec['icon'], spec.get('h', 640)); at = spec.get('icon_at', 0.2)
    lines = spec.get('lines', []); events = [(at, 'whoosh')]
    def frame(t):
        fr = bg_at(bg, t, W, H, 38 if spec.get('particles') else 0); sc, al = _pop(t, at, 0.6)
        drift = 1 + 0.03 * max(0, t - at) / max(1, dur)          # slow push-in
        ici = glow_shadow(ic)[0]
        if spec.get('shine'): ici = sweep(ici, t, at + 0.7, 1.1)
        if al > 0: paste_c(fr, ici, W / 2, H * spec.get('y', 0.42), sc * drift, al)
        y = lines_top(lines, H * spec.get('lines_y', 0.72), W, H)
        for ln in lines:
            sz = ln.get('size', 84); im, ty = kinetic(ln['parts'], t, W, y + sz, sz, start=ln['at'])
            fr.alpha_composite(im, (0, ty)); y += sz * 1.4
        if spec.get('cta'):    # optional CTA pill inside the scene (also covers a "hold" tail after the speech)
            c = spec['cta']; sc2, al2 = _pop(t, c['at'], 0.4)
            if al2 > 0: paste_c(fr, pill(c['text'], c.get('icon', 'link'), c.get('size', 50)), W / 2, min(H * c.get('y', 0.74), SAFE_BOTTOM - 70) if H > W else H * c.get('y', 0.74), sc2, al2)
        return _fade(fr, t, dur, W, H)
    return frame, dur, events

def scene_pan(spec, W, H):
    """Slow camera move across a real photo (e.g. the product tray), darkened at the edges,
    with kinetic lines at the bottom. blur: [[x0, y0, x1, y1], ...] in photo pixels (serial numbers)."""
    dur = spec['dur']; src = Image.open(spec['image']).convert('RGB')
    for b in spec.get('blur', []):
        reg = src.crop(tuple(b)).filter(ImageFilter.GaussianBlur(6)); src.paste(reg, tuple(b[:2]))
    vertical = spec.get('dir', 'x') == 'y'   # tall screenshots: fit the width and scroll down
    k = (W * spec.get('zoom', 1.0) / src.width) if vertical else (H * spec.get('zoom', 1.12) / src.height)
    big = src.resize((int(src.width * k), int(src.height * k)), Image.LANCZOS).convert('RGBA')
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vg = np.clip((np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.45) / (H * 0.62)) ** 2) - 0.55) / 0.6, 0, 1)
    shade = np.clip(0.25 + 0.75 * vg + np.clip((yy - H * 0.62) / (H * 0.3), 0, 1) * 0.7, 0, 0.92) * spec.get('shade', 1.0)
    dark = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dark.putalpha(Image.fromarray((shade * 255).astype(np.uint8)))
    x_from, x_to = spec.get('from', 0.0), spec.get('to', 1.0); lines = spec.get('lines', [])
    events = [(0.05, 'whoosh')]
    def frame(t):
        p = ease(t / dur); sc = 1 + 0.04 * p
        if vertical:
            yo = max(0, big.height - H) * (x_from + (x_to - x_from) * p); xo = (big.width - W) / 2
            crop = big.crop((int(xo), int(yo), int(xo) + W, int(yo) + H))
        else:
            x = (big.width - W) * (x_from + (x_to - x_from) * p)
            crop = big.crop((int(x), int((big.height - H) / 2), int(x) + W, int((big.height - H) / 2) + H))
        if sc != 1: crop = crop.resize((int(W * sc), int(H * sc)), Image.LANCZOS).crop((int(W * (sc - 1) / 2), int(H * (sc - 1) / 2), int(W * (sc - 1) / 2) + W, int(H * (sc - 1) / 2) + H))
        fr = crop.copy(); fr.alpha_composite(dark)
        y = lines_top(lines, H * spec.get('lines_y', 0.74), W, H)
        for ln in lines:
            sz = ln.get('size', 84); im, ty = kinetic(ln['parts'], t, W, y + sz, sz, start=ln['at'])
            fr.alpha_composite(im, (0, ty)); y += sz * 1.4
        return _fade(fr, t, dur, W, H)
    return frame, dur, events

def phone_frame(screen, radius=None):
    """Wrap a screen image in a dark phone body with a thin rim and soft shadow."""
    w, h = screen.size; b = max(14, w // 32); r = radius or w // 8
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    sc = screen.convert('RGBA'); sc.putalpha(m)
    body = Image.new('RGBA', (w + 2 * b, h + 2 * b), (0, 0, 0, 0)); d = ImageDraw.Draw(body)
    d.rounded_rectangle((0, 0, w + 2 * b - 1, h + 2 * b - 1), r + b, fill=(16, 16, 18), outline=(120, 104, 70), width=3)
    body.alpha_composite(sc, (b, b))
    pad = 70; out = Image.new('RGBA', (body.width + 2 * pad, body.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new('RGBA', body.size, (0, 0, 0, 0)); sh.putalpha(body.getchannel('A').point(lambda v: int(v * 0.7)))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(26)), (pad, pad + 24)); out.alpha_composite(body, (pad, pad))
    return out

def card_frame(img, radius=34):
    """Landscape B-roll / photo as a rounded card with a thin gold rim and soft shadow (no phone body)."""
    w, h = img.size
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=255)
    c = img.convert('RGBA'); c.putalpha(m); ImageDraw.Draw(c).rounded_rectangle((0, 0, w - 1, h - 1), radius, outline=GOLD + (230,), width=4)
    pad = 70; out = Image.new('RGBA', (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    sh = Image.new('RGBA', c.size, (0, 0, 0, 0)); sh.putalpha(c.getchannel('A').point(lambda v: int(v * 0.6)))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(26)), (pad, pad + 20)); out.alpha_composite(c, (pad, pad))
    return out

def scene_screen(spec, W, H):
    """Phone mockup: a screen recording (or still) playing inside a phone frame on the dark
    background, with kinetic lines above/below. video: path, start: seconds into the recording."""
    dur = spec['dur']; bg = background(W, H); sw = spec.get('w', 620)
    frames = []
    if spec.get('video'):
        tmp = tempfile.mkdtemp(prefix='scr_')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(spec.get('start', 0)), '-t', f'{dur * spec.get("speed", 1.0):.3f}', '-i', spec['video'],
                        '-vf', f'setpts=PTS/{spec.get("speed", 1.0)},fps=30,scale={sw}:-2' + (',' + spec['grade'] if spec.get('grade') else ''), f'{tmp}/s_%05d.png'], check=True)
        frames = [os.path.join(tmp, f) for f in sorted(os.listdir(tmp))]
    still = Image.open(spec['image']).convert('RGB') if spec.get('image') else None
    if still is not None: still = still.resize((sw, int(still.height * sw / still.width)), Image.LANCZOS)
    cache = {}
    def screen_at(t):
        if not frames: return still
        k = min(len(frames) - 1, int(t * 30))
        if k not in cache: cache.clear(); cache[k] = Image.open(frames[k]).convert('RGB')
        return cache[k]
    lines = spec.get('lines', []); events = [(spec.get('phone_at', 0.15), 'whoosh')]
    def frame(t):
        fr = bg_at(bg, t, W, H, 38 if spec.get('particles') else 0)
        sc, al = _pop(t, spec.get('phone_at', 0.15), 0.5); drift = 1 + spec.get('drift', 0.035) * t / max(1, dur)
        if spec.get('frame') == 'full':   # vertical B-roll: fill the whole screen (cover), lines on top
            im_ = screen_at(t); k_ = max(W / im_.width, H / im_.height) * drift
            im_ = im_.resize((int(im_.width * k_) + 1, int(im_.height * k_) + 1), Image.LANCZOS)
            fr.paste(im_.convert('RGBA'), (int((W - im_.width) / 2), int((H - im_.height) / 2)))
            if _DOT.get('grad_shade') != spec.get('shade', 1.0) or 'grad' not in _DOT:
                _DOT['grad_shade'] = spec.get('shade', 1.0); _DOT.pop('grad', None)
            if 'grad' not in _DOT:   # dark fade top and bottom so labels read over bright footage
                yy = np.linspace(0, 1, H)[:, None]; g_ = np.clip(np.maximum((0.32 - yy) / 0.32, (yy - 0.62) / 0.38), 0, 1) ** 1.4 * spec.get('shade', 1.0)
                _DOT['grad'] = Image.fromarray(np.dstack([np.zeros((H, W, 3)), np.repeat(g_ * 170, W, 1)]).astype(np.uint8), 'RGBA')
            fr.alpha_composite(_DOT['grad'])
            for ln in lines:
                sz = ln.get('size', 80); im, ty = kinetic(ln['parts'], t, W, H * ln.get('y', 0.12) + sz, sz, start=ln['at'])
                fr.alpha_composite(im, (0, ty))
            return _fade(fr, t, dur, W, H, spec.get('fade', 0.3))
        ph = card_frame(screen_at(t)) if spec.get('frame') == 'card' else phone_frame(screen_at(t))   # card: landscape B-roll
        k = min(1.0, H * spec.get('max_h', 0.62) / ph.height); cy = H * spec.get('y', 0.55)
        if H > W:   # portrait: whole phone between y 260 and 1490 (inner phone, shadow padding excluded)
            k = min(k, (SAFE_BOTTOM - 260) / (ph.height - 140)); half = (ph.height - 140) * k / 2
            cy = min(max(cy, 260 + half), SAFE_BOTTOM - half)
        if al > 0: paste_c(fr, ph, W / 2, cy, k * sc * drift, al)
        for ln in lines:
            sz = ln.get('size', 80); im, ty = kinetic(ln['parts'], t, W, H * ln.get('y', 0.12) + sz, sz, start=ln['at'])
            fr.alpha_composite(im, (0, ty))
        return _fade(fr, t, dur, W, H)
    return frame, dur, events

def scene_count(spec, W, H):
    """N copies of a product image popping in one by one (2/3/6 gold bars), an optional side image
    (what that amount can buy) and kinetic lines. items_at: original time each copy appears."""
    d = spec.get('icons_dir', '.'); dur = spec['dur']; bg = background(W, H)
    srcs = spec.get('items') or [spec['item']] * spec['count']          # "items": different pictures, one per slot
    n = len(srcs); cols = spec.get('cols', min(n, 3)); rows = -(-n // cols)
    cw = spec.get('item_w', {1: 620, 2: 440, 3: 300}.get(cols, 280))
    items = []
    for sp in srcs:
        im = load(d, sp, 600); im = im.resize((cw, int(im.height * cw / im.width)), Image.LANCZOS); items.append(glow_shadow(im, 18, 0.5))
    pad = items[0][1]; cell_h = max(im.height - 2 * pad for im, _ in items)
    gx, gy = cw + 24, cell_h + 24
    top = H * spec.get('grid_y', 0.36) - (rows * gy) / 2
    ats = spec.get('items_at', [0.3 + 0.18 * k for k in range(n)])
    side = load(d, spec['side'], spec.get('side_h', 420)) if spec.get('side') else None
    lines = spec.get('lines', [])
    events = [(a_, 'pop') for a_ in ats] + ([(spec['side_at'], 'whoosh')] if side is not None else [])
    def frame(t):
        fr = bg.copy()
        for k in range(n):
            sc, al = _pop(t, ats[k], 0.35)
            if al <= 0: continue
            r_, c_ = divmod(k, cols); in_row = min(cols, n - r_ * cols)
            cx = W / 2 + (c_ - (in_row - 1) / 2) * gx; cy = top + r_ * gy + gy / 2
            paste_c(fr, items[k][0], cx, cy, sc, al)
        if side is not None:
            sc, al = _pop(t, spec['side_at'], 0.5)
            if al > 0: paste_c(fr, glow_shadow(side)[0], W / 2, H * spec.get('side_y', 0.66), sc, al)
        y = H * spec.get('lines_y', 0.12)
        for ln in lines:
            sz = ln.get('size', 80); im, ty = kinetic(ln['parts'], t, W, y + sz, sz, start=ln['at'])
            fr.alpha_composite(im, (0, ty)); y += sz * 1.35
        return _fade(fr, t, dur, W, H)
    return frame, dur, events

def render_frames(spec, folder, W=1080, H=1920, fps=30):
    """Transparent PNG frames of a scene (for laying over the video); returns its sound events."""
    BACKDROP[0] = True
    try:
        frame, dur, events = SCENES[spec['type']](spec, W, H)
        for k in range(int(round(dur * fps))):
            frame(k / fps).save(f'{folder}/f_{k:05d}.png', compress_level=1)
    finally:
        BACKDROP[0] = False
    return events

def scene_gapsave(spec, W, H):
    """Gold coins drop into a phone showing the GAP app; the balance on the screenshot counts up
    (1g, 2g, 3g...) as each coin lands. balance_box: [x0, y0, x1, y1] of the balance text in the
    screenshot's own pixels (it is painted over with the card colour, then redrawn each frame)."""
    d = spec.get('icons_dir', '.'); dur = spec['dur']; bg = background(W, H)
    shot = Image.open(spec['image']).convert('RGB'); sw = spec.get('w', 620)
    if spec.get('crop_h'): shot = shot.crop((0, 0, shot.width, min(shot.height, spec['crop_h'])))   # show only the top of the app, bigger
    bx0, by0, bx1, by1 = spec['balance_box']
    fill = shot.getpixel((max(0, bx0 - 30), (by0 + by1) // 2))
    base = shot.copy(); ImageDraw.Draw(base).rectangle((bx0, by0, bx1, by1), fill=fill)
    k = sw / shot.width; base = base.resize((sw, int(shot.height * k)), Image.LANCZOS)
    cx_s, cy_s = (bx0 + bx1) / 2 * k, (by0 + by1) / 2 * k
    f_bal = docmod._font(docmod.HEAVY, max(18, int((by1 - by0) * k * spec.get('balance_scale', 1.5))))
    coin = load(d, spec.get('item', 'syiling'), spec.get('item_h', 120))
    n = spec.get('count', 4); start = spec.get('start_value', 1); step = spec.get('step', 1); dec = spec.get('decimals', 0)
    t0 = spec.get('drop_at', 0.6); gap = spec.get('gap', 0.6); fall = 0.55
    drops = [t0 + i * gap for i in range(n)]
    events = [(0.1, 'whoosh')] + [(s_ + fall, 'coin') for s_ in drops]
    lines = spec.get('lines', [])
    def screen_at(t):
        landed = sum(1 for s_ in drops if t >= s_ + fall)
        sc = base.copy(); dr = ImageDraw.Draw(sc)
        if landed:
            val = start + (landed - 1) * step
            txt = f"{val:,.{dec}f}{spec.get('unit', 'g')}"
            q = ease_out((t - (drops[landed - 1] + fall)) / 0.25); sz = int(f_bal.size * (1 + 0.25 * (1 - q)))
            fb = docmod._font(docmod.HEAVY, sz)
            dr.text((cx_s, cy_s), txt, font=fb, fill=(150, 22, 38) if q < 1 else (30, 30, 30), anchor='mm')
        else:
            dr.text((cx_s, cy_s), spec.get('empty', '0g'), font=f_bal, fill=(30, 30, 30), anchor='mm')
        return sc
    def frame(t):
        fr = bg_at(bg, t, W, H, 38 if spec.get('particles') else 0)
        sc_, al = _pop(t, spec.get('phone_at', 0.1), 0.45)
        ph = phone_frame(screen_at(t)); kk = min(1.0, H * spec.get('max_h', 0.6) / ph.height); cy = H * spec.get('y', 0.6)
        if H > W:
            kk = min(kk, (SAFE_BOTTOM - 300) / (ph.height - 140)); half = (ph.height - 140) * kk / 2
            cy = min(max(cy, 300 + half), SAFE_BOTTOM - half)
        if al > 0: paste_c(fr, ph, W / 2, cy, kk * sc_, al)
        top_ph = cy - (ph.height - 140) * kk / 2
        target_y = top_ph + (spec['balance_box'][1] * sw / shot.width + 70) * kk
        for i, s_ in enumerate(drops):
            q = (t - s_) / fall
            if 0 <= q <= 1.1:
                y0_ = max(top_ph - 260, H * spec.get('coin_from', 0.0)); y = y0_ + (target_y - y0_) * min(1, q) ** 2
                paste_c(fr, coin, W / 2 + (1 - q) * (40 if i % 2 else -40), y, 1.0 if q < 0.85 else max(0.2, 1 - (q - 0.85) * 3), min(1, (1.1 - q) * 5))
        yy = H * spec.get('lines_y', 0.10)
        for ln in lines:
            sz = ln.get('size', 80); im, ty = kinetic(ln['parts'], t, W, yy + sz, sz, start=ln['at'])
            fr.alpha_composite(im, (0, ty)); yy += sz * 1.35
        return _fade(fr, t, dur, W, H)
    return frame, dur, events

def scene_chart(spec, W, H):
    """Real price line (digitised from a chart the user gave) drawn left to right on a glass card, with an
    optional zoom-out (e.g. 2 years of ups and downs -> the full 10 years). data: [[x, value], ...] json file
    (x in years from `year0`); window: [x0, x1] shown first; zoom_to + zoom_at: window to ease out to;
    draw_at/draw_time: when the line draws; title: kinetic parts; source: small credit line (always give one)."""
    dur = spec['dur']; bg = background(W, H)
    data = spec['data'] if isinstance(spec['data'], list) else json.load(open(os.path.join(spec.get('base', '.'), spec['data'])))
    xs = np.array([d[0] for d in data], float); vs = np.array([d[1] for d in data], float)
    w0 = spec.get('window', [xs[0], xs[-1]]); w1 = spec.get('zoom_to', w0); za = spec.get('zoom_at', 0); zt = spec.get('zoom_time', 1.2)
    da = spec.get('draw_at', 0.3); dt = spec.get('draw_time', 2.0); y0 = spec.get('year0', 0)
    pw, ph = 900, 760; px, py = (W - pw) // 2, int(H * spec.get('card_y', 0.42) - ph / 2)
    ix0, ix1, iy0, iy1 = 70, pw - 70, 70, ph - 120          # plot area inside the card
    card = Image.new('RGBA', (pw, ph), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle((0, 0, pw - 1, ph - 1), 44, fill=(14, 11, 8, 165), outline=GOLD + (120,), width=3)
    fs, fy = docmod._font(MED, 34), docmod._font(docmod.BOLD, 44)
    events = [(da, 'whoosh')] + ([(za, 'whoosh')] if 'zoom_to' in spec else [])
    def frame(t):
        fr = bg_at(bg, t, W, H)
        p = ease((t - za) / zt) if 'zoom_to' in spec else 0.0
        a_, b_ = w0[0] + (w1[0] - w0[0]) * p, w0[1] + (w1[1] - w0[1]) * p
        # reveal: draw across the first window, then keep pace with the zoom so the line reaches the new right edge
        reveal = a_ + (b_ - a_) * ease_out((t - da) / dt) if t < za or 'zoom_to' not in spec else b_
        sel = (xs >= a_) & (xs <= b_); lo, hi = vs[sel].min(), vs[sel].max(); pad = (hi - lo) * 0.12 + 1
        lo, hi = lo - pad, hi + pad
        X = lambda x: ix0 + (x - a_) / (b_ - a_) * (ix1 - ix0); Y = lambda v: iy1 - (v - lo) / (hi - lo) * (iy1 - iy0)
        c = card.copy(); dr = ImageDraw.Draw(c)
        for k in range(1, 4): yy = iy0 + (iy1 - iy0) * k / 4; dr.line((ix0, yy, ix1, yy), fill=(255, 255, 255, 34), width=2)
        for yr in range(int(math.ceil(a_)), int(b_) + 1):      # year ticks, thinned so labels never collide
            step = 1 if b_ - a_ <= 4 else 2
            if (yr - int(math.ceil(a_))) % step and yr != int(b_): continue
            x = X(yr); dr.line((x, iy1, x, iy1 + 12), fill=(255, 255, 255, 120), width=3)
            dr.text((x, iy1 + 22), str(y0 + yr), font=fs, fill=(255, 255, 255, 220), anchor='mt')
        m = sel & (xs <= reveal); pts = [(X(x), Y(v)) for x, v in zip(xs[m], vs[m])]
        if len(pts) > 1:
            gl = Image.new('RGBA', c.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).line(pts, fill=GOLD + (200,), width=22, joint='curve')
            c.alpha_composite(gl.filter(ImageFilter.GaussianBlur(14))); ImageDraw.Draw(c).line(pts, fill=(255, 205, 90, 255), width=9, joint='curve')
            hx, hy = pts[-1]; ImageDraw.Draw(c).ellipse((hx - 16, hy - 16, hx + 16, hy + 16), fill=WHITE + (255,), outline=GOLD, width=6)
        if spec.get('source'): ImageDraw.Draw(c).text((pw - 36, ph - 30), spec['source'], font=docmod._font(MED, 28), fill=(255, 255, 255, 150), anchor='rs')
        sc, al = _pop(t, spec.get('card_at', 0.0), 0.4)
        paste_c(fr, glow_shadow(c, 30, 0.5)[0], W / 2, py + ph / 2 + 18, sc, al)
        for ln in spec.get('lines', []):   # title lines above the card, swapped by their own at/until times
            if t < ln.get('at', 0) or t > ln.get('until_at', 1e9): continue
            sz = ln.get('size', 96); im, ty = kinetic(ln['parts'], t, W, py - 90 + ln.get('dy', 0), sz, start=ln['at'])
            fr.alpha_composite(im, (0, ty))
        return _fade(fr, t, dur, W, H)
    return frame, dur, events

def scene_swap(spec, W, H):
    """One product at a time, swapping in place with a quick cross-fade and a big gold label under it
    (e.g. 5g -> 10g -> 20g -> 50g -> 100g as each is spoken). items: [{"at", "image", "label"}]."""
    d = spec.get('icons_dir', '.'); dur = spec['dur']; bg = background(W, H)
    items = [(it, glow_shadow(load(d, it['image'], spec.get('h', 520)))[0]) for it in spec['items']]
    fl = docmod._font(docmod.HEAVY, spec.get('label_size', 170)); cy = H * spec.get('y', 0.45)
    events = [(it['at'], 'pop') for it, _ in items]
    def frame(t):
        fr = bg_at(bg, t, W, H)
        shown = [(it, im) for it, im in items if t >= it['at']]
        for k, (it, im) in enumerate(shown[-2:]):
            new = k == len(shown[-2:]) - 1
            p = ease_out((t - it['at']) / 0.25) if new else 1.0
            al = p if new else 1 - ease_out((t - shown[-1][0]['at']) / 0.25)
            if al <= 0: continue
            paste_c(fr, im, W / 2, cy, (0.9 + 0.1 * p) if new else 1.0, al)
            lab = Image.new('RGBA', (W, 260), (0, 0, 0, 0)); ImageDraw.Draw(lab).text((W / 2, 130), it['label'], font=fl, fill=GOLD, anchor='mm')
            g = lab.filter(ImageFilter.GaussianBlur(18)); out = Image.new('RGBA', lab.size, (0, 0, 0, 0)); out.alpha_composite(g); out.alpha_composite(lab)
            paste_c(fr, out, W / 2, cy + im.height / 2 + 40, 1.0, al)
        for ln in spec.get('lines', []):
            sz = ln.get('size', 80); im_, ty = kinetic(ln['parts'], t, W, H * spec.get('lines_y', 0.13) + sz, sz, start=ln['at'])
            fr.alpha_composite(im_, (0, ty))
        return _fade(fr, t, dur, W, H)
    return frame, dur, events

def scene_promo(spec, W, H):
    """Event promo: big poster with a gold rim, then (each popping in at its own time) a gold caps date line,
    white venue lines, a big gold pill (link / call to action, dark text) and a spaced gold caps tagline.
    poster, poster_at, date: {"at","text"}, venue: {"at","text"} (wrapped to 2 lines), pill: {"at","text"}, tag: {"at","text"}.
    Everything is fitted inside the portrait safe zone (x 120..960, y 230..1490)."""
    dur = spec['dur']; bg = background(W, H)
    po = Image.open(spec['poster']).convert('RGB'); pw = spec.get('poster_w', 760)
    po = po.resize((pw, int(po.height * pw / po.width)), Image.LANCZOS)
    m = Image.new('L', po.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, po.width - 1, po.height - 1), 26, fill=255)
    card = Image.new('RGBA', (po.width + 16, po.height + 16), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, card.width - 1, card.height - 1), 32, fill=GOLD + (255,))
    pc = po.convert('RGBA'); pc.putalpha(m); card.alpha_composite(pc, (8, 8)); card = glow_shadow(card, 30, 0.6)[0]
    top = spec.get('top', 240); pad_ = 60; cy_po = top - pad_ + card.height / 2   # card includes the glow padding
    y = top + po.height + 16 + spec.get('gap', 34); maxw = 840
    def fitf(fspec, txt, sz, mw=maxw, track=0):
        f = docmod._font(fspec, sz)
        while f.getlength(txt) + track * len(txt) > mw and sz > 24: sz -= 2; f = docmod._font(fspec, sz)
        return f
    items = []   # (at, image, cy)
    if spec.get('date'):
        t_ = spec['date']['text']; f = fitf(docmod.HEAVY, t_, spec['date'].get('size', 64))
        im = Image.new('RGBA', (W, int(f.size * 1.5)), (0, 0, 0, 0)); ImageDraw.Draw(im).text((W / 2, im.height / 2), t_, font=f, fill=GOLD, anchor='mm')
        items.append((spec['date']['at'], im, y + im.height / 2)); y += im.height + 6
    if spec.get('venue'):
        words = spec['venue']['text'].split(); f = docmod._font(docmod.REG, spec['venue'].get('size', 46)); lines, ln = [], ''
        for w in words:
            if f.getlength((ln + ' ' + w).strip()) > maxw: lines.append(ln); ln = w
            else: ln = (ln + ' ' + w).strip()
        lines.append(ln); lh = int(f.size * 1.32)
        im = Image.new('RGBA', (W, lh * len(lines) + 10), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
        for k, l in enumerate(lines): dr.text((W / 2, lh * k + lh / 2), l, font=f, fill=(245, 240, 230), anchor='mm')
        items.append((spec['venue']['at'], im, y + im.height / 2)); y += im.height + 26
    if spec.get('pill'):
        t_ = spec['pill']['text']; f = fitf(docmod.HEAVY, t_, spec['pill'].get('size', 96), 720); ph = int(f.size * 1.55); pw2 = int(min(maxw, f.getlength(t_) + ph * 1.2))
        im = Image.new('RGBA', (pw2 + 60, ph + 60), (0, 0, 0, 0))
        g = np.linspace(0, 1, ph)[:, None]; a = np.array([255, 214, 110]) * (1 - g[..., None]) + np.array([196, 128, 20]) * g[..., None]
        grad = Image.fromarray(np.repeat(a, pw2, axis=1).astype(np.uint8), 'RGB').convert('RGBA')
        mk = Image.new('L', (pw2, ph), 0); ImageDraw.Draw(mk).rounded_rectangle((0, 0, pw2 - 1, ph - 1), ph // 2, fill=255)
        glow = Image.new('RGBA', im.size, (0, 0, 0, 0)); ImageDraw.Draw(glow).rounded_rectangle((24, 30, pw2 + 36, ph + 36), ph // 2, fill=GOLD + (150,))
        im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(16))); im.paste(grad, (30, 30), mk)
        ImageDraw.Draw(im).text((30 + pw2 / 2, 30 + ph / 2), t_, font=f, fill=(30, 20, 6), anchor='mm')
        items.append((spec['pill']['at'], im, y + im.height / 2 - 30)); y += im.height - 30
    if spec.get('tag'):
        t_ = spec['tag']['text']; tr = spec['tag'].get('track', 8); f = fitf(docmod.HEAVY, t_, spec['tag'].get('size', 52), maxw, tr)
        tw = f.getlength(t_) + tr * (len(t_) - 1); im = Image.new('RGBA', (W, int(f.size * 1.6)), (0, 0, 0, 0)); dr = ImageDraw.Draw(im); x = (W - tw) / 2
        for ch in t_: dr.text((x, im.height / 2), ch, font=f, fill=GOLD, anchor='lm'); x += f.getlength(ch) + tr
        items.append((spec['tag']['at'], im, y + im.height / 2))
    events = [(spec.get('poster_at', 0.1), 'whoosh')] + [(a_, 'pop') for a_, _, _ in items]
    if H > W and y > SAFE_BOTTOM: print(f'WARNING promo block reaches y {int(y)} (below the safe zone)', file=sys.stderr)
    def frame(t):
        fr = bg_at(bg, t, W, H)
        sc, al = _pop(t, spec.get('poster_at', 0.1), 0.5)
        if al > 0: paste_c(fr, card, W / 2, cy_po, sc * (1 + 0.02 * t / max(1, dur)), al)
        for a_, im, cy in items:
            sc, al = _pop(t, a_, 0.4)
            if al > 0: paste_c(fr, im, W / 2, cy + (1 - al) * 18, 1.0, al)
        return _fade(fr, t, dur, W, H)
    return frame, dur, events

SCENES = dict(promo=scene_promo, swap=scene_swap, chart=scene_chart, gapsave=scene_gapsave, count=scene_count, screen=scene_screen, pan=scene_pan, drop=scene_drop, kinetic=scene_kinetic, compare=scene_compare, counter=scene_counter, hero=scene_hero)

def render_silent(spec, out, W=1080, H=1920, fps=30):
    """Scene video without audio; returns the scene's sound-effect events (scene-relative times)."""
    H_PORTRAIT[0] = H > W
    frame, dur, events = SCENES[spec['type']](spec, W, H)
    work = tempfile.mkdtemp(prefix='scene_')
    for k in range(int(round(dur * fps))):
        frame(k / fps).convert('RGB').save(f'{work}/f_{k:05d}.png', compress_level=1)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(fps), '-i', f'{work}/f_%05d.png',
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p', out], check=True)
    shutil.rmtree(work, ignore_errors=True)
    return events

def render(spec, out, W=1080, H=1920, fps=30):
    frame, dur, events = SCENES[spec['type']](spec, W, H)
    work = tempfile.mkdtemp(prefix='scene_')
    for k in range(int(dur * fps)):
        frame(k / fps).convert('RGB').save(f'{work}/f_{k:05d}.png', compress_level=1)
    sfx.render_track(events, dur, f'{work}/a.wav', spec.get('sfx_gain_db', -14))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(fps), '-i', f'{work}/f_%05d.png', '-i', f'{work}/a.wav',
                    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                    '-shortest', '-movflags', '+faststart', out], check=True)
    shutil.rmtree(work, ignore_errors=True)
    return out

if __name__ == '__main__':
    spec = json.load(open(sys.argv[1]))
    if not os.path.isabs(spec.get('icons', '.')): spec['icons'] = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), spec.get('icons', '.'))
    spec.setdefault('icons_dir', spec['icons'])
    print(render(spec, sys.argv[2]))
