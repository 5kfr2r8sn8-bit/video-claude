"""Gaya Mewah Emas (references/mewah.md): the luxury gold look of the carousel, for video.

Elements (drawn per frame by build.py through gaya.draw):
  mtitle  serif 3D headline, lines [[text, "white"|"gold"], ...] (hook / cover)
  mword   one big serif 3D gold word with sparkles, pops in
  mstep   gold coin badge (number) + navy panel with gold border, slides in from the side
  mpanel  navy panel: gold title + rows with gold ticks that appear on their spoken time
  mcta    navy pill, gold border, white text + gold keyword
"""
import os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, '..', 'assets', 'fonts')
NAVY = (12, 22, 58)
GOLD_EDGE = (226, 176, 72)
_C = {}

def serif(sz):
    f = ImageFont.truetype(os.path.join(FD, 'PlayfairDisplay.ttf'), int(sz)); f.set_variation_by_name('Black'); return f
def sans(sz, w='Bold'):
    f = ImageFont.truetype(os.path.join(FD, 'Montserrat.ttf'), int(sz)); f.set_variation_by_name(w); return f

def vgrad(w, h, stops):
    y = np.linspace(0, 1, h); out = np.zeros((h, 3))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        k = (y >= p0) & (y <= p1); t = ((y[k] - p0) / max(1e-6, p1 - p0))[:, None]
        out[k] = np.array(c0) + (np.array(c1) - np.array(c0)) * t
    return np.repeat(out[:, None, :], w, axis=1)

def emboss(m, size, soft=0.04):
    hgt = np.asarray(m.filter(ImageFilter.GaussianBlur(max(2, size * soft))), np.float32) / 255.0
    gy, gx = np.gradient(hgt); k = 9.0
    nx, ny, nz = -gx * k, -gy * k, np.ones_like(hgt); n = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    L = np.array([-0.45, -0.65, 0.62]); L = L / np.linalg.norm(L)
    return np.clip((nx * L[0] + ny * L[1] + nz * L[2]) / n, 0, 1)

def sparkle(d, x, y, r, a=255):
    for k in range(3, 0, -1):
        rr = r * k / 3; al = int(a * (0.25 if k == 3 else 0.5 if k == 2 else 1))
        d.polygon([(x, y - rr * 2.2), (x + rr * 0.28, y - rr * 0.28), (x + rr * 2.2, y), (x + rr * 0.28, y + rr * 0.28),
                   (x, y + rr * 2.2), (x - rr * 0.28, y + rr * 0.28), (x - rr * 2.2, y), (x - rr * 0.28, y - rr * 0.28)], fill=(255, 250, 225, al))

def text3d(text, size, style='gold', max_w=960):
    """Serif 3D word/line like the carousel headlines: gold (shiny) or white-cream with gold sides."""
    key = ('t', text, size, style, max_w)
    if key in _C: return _C[key]
    f = serif(size)
    while f.getlength(text) > max_w and size > 30: size -= 4; f = serif(size)
    pad = 50; bb = f.getbbox(text); w, h = bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).text((pad - bb[0], pad - bb[1]), text, font=f, fill=255)
    depth = max(6, size // 11); out = Image.new('RGBA', (w + depth, h + depth + 8), (0, 0, 0, 0))
    sh = Image.new('RGBA', out.size, (0, 0, 20, 0)); sm = Image.new('L', out.size, 0); sm.paste(m, (depth, depth + 8))
    sh.putalpha(sm.filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * 0.75))); out.alpha_composite(sh)
    if style == 'gold':
        gl = Image.new('RGBA', out.size, (255, 196, 80, 0)); gm = Image.new('L', out.size, 0); gm.paste(m, (0, 0))
        gl.putalpha(gm.filter(ImageFilter.GaussianBlur(size * 0.16)).point(lambda v: int(v * 0.55))); out.alpha_composite(gl)
    side = ((170, 100, 10), (90, 45, 0)) if style == 'gold' else ((200, 150, 60), (120, 80, 20))
    for k in range(depth, 0, -1):
        t = k / depth; col = tuple(int(a + (b - a) * t) for a, b in zip(*side))
        lay = Image.new('RGBA', (w, h), col + (255,)); lay.putalpha(m); out.alpha_composite(lay, (k // 2, k))
    stops = ([(0, (255, 248, 200)), (0.45, (255, 214, 90)), (0.75, (230, 160, 40)), (1, (255, 200, 90))] if style == 'gold'
             else [(0, (255, 255, 255)), (0.6, (252, 247, 236)), (1, (236, 222, 196))])
    light = emboss(m, size)
    arr = vgrad(w, h, stops) * (0.62 + 0.55 * light[..., None]) + 255 * (light[..., None] ** 14) * 0.6
    fc = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA'); fc.putalpha(m); out.alpha_composite(fc)
    if style == 'gold':
        d = ImageDraw.Draw(out); bb = m.getbbox(); rnd = random.Random(len(text))
        for fx, fy, r in ((0.02, 0.55, 10), (0.98, 0.2, 13), (0.5, 0.05, 8)):
            sparkle(d, bb[0] + (bb[2] - bb[0]) * fx, bb[1] + (bb[3] - bb[1]) * fy, r)
    out = out.crop(out.getchannel('A').point(lambda v: 255 if v > 12 else 0).getbbox())
    _C[key] = out; return out

def stack(lines, size, max_w=960, gap=-0.12):
    """[[text, style], ...] stacked, centred."""
    ims = [text3d(t, size if st == 'gold' else int(size * 0.8), st, max_w) for t, st in lines]
    W = max(i.width for i in ims); H = sum(i.height for i in ims) + int(sum(i.height for i in ims[:-1]) * gap)
    out = Image.new('RGBA', (W, max(1, H)), (0, 0, 0, 0)); y = 0
    for i in ims: out.alpha_composite(i, ((W - i.width) // 2, y)); y += int(i.height * (1 + gap))
    return out

def coin(num, r=62):
    key = ('c', num, r)
    if key in _C: return _C[key]
    S = 3; R = r * S; c = Image.new('RGBA', (2 * R + 12 * S, 2 * R + 12 * S), (0, 0, 0, 0)); C = c.width // 2
    yy, xx = np.mgrid[0:c.height, 0:c.width]; dist = np.hypot(xx - C, yy - C); t = np.clip((yy - (C - R)) / (2 * R), 0, 1)[..., None]
    rim = np.array([255, 240, 170]) * (1 - t) + np.array([186, 116, 14]) * t
    face = np.array([255, 230, 130]) * (1 - t) + np.array([226, 156, 34]) * t
    rgb = np.where((dist < R * 0.82)[..., None], face, rim); rgb[np.abs(dist - R * 0.82) < S * 1.5] = (150, 90, 10)
    a = np.clip((R - dist) / S, 0, 1) * 255
    c = Image.fromarray(np.dstack([rgb, a]).astype(np.uint8))
    d = ImageDraw.Draw(c); f = serif(R * (1.2 if len(num) == 1 else 0.9))
    d.text((C + S * 2, C + S * 3), num, font=f, fill=(120, 70, 0, 150), anchor='mm'); d.text((C, C), num, font=f, fill=(14, 10, 6, 255), anchor='mm')
    c = c.resize((c.width // S, c.height // S), Image.LANCZOS)
    out = Image.new('RGBA', (c.width + 40, c.height + 40), (0, 0, 0, 0))
    gl = Image.new('RGBA', out.size, (255, 200, 90, 0)); al = Image.new('L', out.size, 0); al.paste(c.getchannel('A'), (20, 20))
    gl.putalpha(al.filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * 0.6))); out.alpha_composite(gl); out.alpha_composite(c, (20, 20))
    _C[key] = out; return out

def navy_panel(w, h, r=34):
    im = Image.new('RGBA', (w + 60, h + 60), (0, 0, 0, 0)); o = 30
    glow = Image.new('L', im.size, 0); ImageDraw.Draw(glow).rounded_rectangle((o, o, o + w, o + h), r, outline=255, width=10)
    g = Image.new('RGBA', im.size, (255, 200, 90, 0)); g.putalpha(glow.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.8))); im.alpha_composite(g)
    body = Image.new('L', (w, h), 0); ImageDraw.Draw(body).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    grad = Image.fromarray(vgrad(w, h, [(0, (22, 36, 86)), (1, (8, 14, 40))]).astype(np.uint8)).convert('RGBA'); grad.putalpha(body.point(lambda v: int(v * 0.93)))
    im.alpha_composite(grad, (o, o))
    ImageDraw.Draw(im).rounded_rectangle((o, o, o + w, o + h), r, outline=GOLD_EDGE + (255,), width=5)
    ImageDraw.Draw(im).rounded_rectangle((o + 9, o + 9, o + w - 9, o + h - 9), r - 8, outline=(255, 226, 150, 120), width=2)
    return im, o

def rich(d, x, y, parts, f, anchor='lm'):
    """parts [[text, 'w'|'g'], ...] drawn on one line; returns end x."""
    for t, c in parts:
        d.text((x, y), t, font=f, fill=(255, 214, 90) if c == 'g' else (255, 255, 255), anchor=anchor); x += f.getlength(t)
    return x

def step_img(num, parts, sub=None, w=820):
    key = ('s', num, str(parts), str(sub), w)
    if key in _C: return _C[key]
    f = sans(52, 'ExtraBold'); fs = sans(36, 'SemiBold'); h = 150 if not sub else 196
    pn, o = navy_panel(w, h); d = ImageDraw.Draw(pn)
    tw = sum(f.getlength(t) for t, _ in parts)
    while tw > w - 210 and f.size > 34: f = sans(f.size - 2, 'ExtraBold'); tw = sum(f.getlength(t) for t, _ in parts)
    rich(d, o + 160, o + (52 if sub else h / 2), parts, f)
    if sub: d.text((o + 160, o + 130), sub, font=fs, fill=(225, 230, 245), anchor='lm')
    cn = coin(num); out = Image.new('RGBA', (pn.width + 40, max(pn.height, cn.height)), (0, 0, 0, 0))
    out.alpha_composite(pn, (40, (out.height - pn.height) // 2)); out.alpha_composite(cn, (0, (out.height - cn.height) // 2))
    _C[key] = out; return out

def tick(d, x, y, s, col=(255, 214, 90)):
    d.ellipse((x - s, y - s, x + s, y + s), fill=col); d.line([(x - s * .45, y), (x - s * .1, y + s * .38), (x + s * .5, y - s * .35)], fill=NAVY, width=max(4, s // 4))

def panel_img(el, t):
    rows = el['rows']; w = el.get('w', 820); h = 120 + 92 * len(rows)
    pn, o = navy_panel(w, h); d = ImageDraw.Draw(pn)
    ft = serif(58); d.text((o + w / 2, o + 62), el['title'], font=ft, fill=(255, 214, 90), anchor='mm')
    fr = sans(44, 'Bold')
    for i, r in enumerate(rows):
        y = o + 150 + i * 92
        if t >= el['_at'][i]:
            tick(d, o + 70, y, 26); rich(d, o + 120, y, r if isinstance(r, list) else [[r, 'w']], fr)
        else:
            d.ellipse((o + 44, y - 26, o + 96, y + 26), outline=(255, 214, 90, 160), width=3)
    return pn

def cta_img(parts):
    key = ('cta', str(parts))
    if key in _C: return _C[key]
    f = sans(50, 'ExtraBold'); tw = sum(f.getlength(t) for t, _ in parts); w, h = int(tw + 120), 116
    pn, o = navy_panel(w, h, r=h // 2); d = ImageDraw.Draw(pn); rich(d, o + 60, o + h / 2, parts, f)
    _C[key] = pn; return pn

def ease_out(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def pop(x):
    x = min(1, max(0, x)); return 0.6 + 0.4 * (1 - (1 - x) ** 3) + 0.12 * math.sin(x * math.pi) * (1 - x)

def _alpha(im, a):
    if a >= 0.999: return im
    im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * a))); return im
def _put(fr, im, cx, cy, sc=1.0):
    if abs(sc - 1) > 0.01: im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BICUBIC)
    fr.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

TYPES = ('mtitle', 'mword', 'mstep', 'mpanel', 'mcta', 'manim')

def prepare(el, N):
    ty = el['type']
    if ty == 'mpanel': el['_at'] = [N(a) for a in el.get('at', [el['t'][0]] * len(el['rows']))]
    el['cy'] = el.get('y') or {'mtitle': 330, 'mword': 360, 'mstep': 1180, 'mpanel': 1150, 'mcta': 1330, 'manim': 1000}[ty]
    return el

def draw(el, t, W, H):
    s, e = el['s'], el['e']; u = t - s; ty = el['type']
    if t < s or t > e: return None
    if ty == 'manim': return manim(el, t, W, H)
    fr = Image.new('RGBA', (W, H), (0, 0, 0, 0)); out_a = 1.0 if el.get('cover') else min(1.0, max(0.0, (e - t) / 0.2))
    if ty == 'mtitle':
        im = stack(el['lines'], el.get('size', 150)); p = 1.0 if el.get('cover') else ease_out(u / 0.3)
        _put(fr, _alpha(im, p * out_a), W / 2, el['cy'] + 30 * (1 - p))
    elif ty == 'mword':
        im = text3d(el['text'], el.get('size', 190), 'gold', 800); _put(fr, _alpha(im, min(1, u / 0.1) * out_a), W / 2, el['cy'], pop(u / 0.35))
    elif ty == 'mstep':
        im = step_img(el['num'], el['parts'], el.get('sub')); p = ease_out(u / 0.3)
        _put(fr, _alpha(im, min(1, p * 1.4) * out_a), W / 2 - 260 * (1 - p), el['cy'])
    elif ty == 'mpanel':
        im = panel_img(el, t); p = ease_out(u / 0.3); _put(fr, _alpha(im, min(1, p * 1.4) * out_a), W / 2, el['cy'] + 160 * (1 - p))
    elif ty == 'mcta':
        im = cta_img(el['parts']); _put(fr, _alpha(im, min(1, u / 0.15) * out_a), W / 2, el['cy'], pop(u / 0.35))
    return fr

def sub_frame(grp, t, y, W, H, max_w=860):
    """Caption: white + gold keywords (and the word being spoken in gold) in a navy pill with a gold rim."""
    f = sans(54, 'ExtraBold'); words = [(w, emph or (ws <= t < we)) for w, emph, ws, we in grp]
    sp = f.getlength(' '); lines, ln, lw = [], [], 0
    for w, g in words:
        ww = f.getlength(w)
        if ln and lw + sp + ww > max_w - 80: lines.append(ln); ln, lw = [], 0
        ln.append((w, g)); lw += (sp if len(ln) > 1 else 0) + ww
    if ln: lines.append(ln)
    lh = 72; bw = int(max(sum(f.getlength(w) for w, _ in l) + sp * (len(l) - 1) for l in lines)) + 70; bh = lh * len(lines) + 34
    fr = Image.new('RGBA', (W, H), (0, 0, 0, 0)); x0, y0 = int((W - bw) / 2), int(y - bh)
    sh = Image.new('L', (W, H), 0); ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 8, x0 + bw, y0 + bh + 8), 26, fill=150)
    s_ = Image.new('RGBA', (W, H), (0, 0, 0, 255)); s_.putalpha(sh.filter(ImageFilter.GaussianBlur(10))); fr.alpha_composite(s_)
    d = ImageDraw.Draw(fr); d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), 26, fill=NAVY + (225,), outline=GOLD_EDGE + (255,), width=3)
    for i, l in enumerate(lines):
        tw = sum(f.getlength(w) for w, _ in l) + sp * (len(l) - 1); x = (W - tw) / 2; yy = y0 + 17 + lh * i + lh / 2
        for w, g in l:
            d.text((x, yy), w, font=f, fill=(255, 214, 90) if g else (255, 255, 255), anchor='lm'); x += f.getlength(w) + sp
    return fr


# ---------------------------------------------------------------- animated illustrations ("manim")
# Simple vector drawings (no AI images), animated per frame. kind: money_fly / wallet_leak / piggy / calendar.
SS = 2   # supersample

def _note(w, h, ang):
    im = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im); W2, H2 = w * SS, h * SS
    d.rounded_rectangle((0, 0, W2 - 1, H2 - 1), 10 * SS, fill=(62, 150, 92), outline=(30, 90, 52), width=3 * SS)
    d.rounded_rectangle((8 * SS, 8 * SS, W2 - 8 * SS, H2 - 8 * SS), 6 * SS, outline=(150, 210, 160), width=2 * SS)
    r = H2 * 0.3; d.ellipse((W2 * 0.68 - r, H2 / 2 - r, W2 * 0.68 + r, H2 / 2 + r), fill=(120, 190, 130))
    d.text((W2 * 0.3, H2 / 2), 'RM', font=sans(H2 * 0.38, 'Black'), fill=(235, 250, 235), anchor='mm')
    im = im.resize((w, h), Image.LANCZOS)
    return im.rotate(ang, resample=Image.BICUBIC, expand=True)

def _gcoin(r, spin=0.0):
    """Gold coin; spin 0..1 squashes it horizontally (turning)."""
    c = coin('RM', r); sx = max(0.15, abs(math.cos(spin * math.pi)))
    return c.resize((max(2, int(c.width * sx)), c.height), Image.BICUBIC)

def _paste(fr, im, cx, cy, a=1.0):
    if a < 0.999: im = _alpha(im, a)
    fr.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def _wallet(s, open_=1.0):
    w, h = int(300 * s), int(210 * s); im = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im); W2, H2 = w * SS, h * SS
    d.rounded_rectangle((0, H2 * 0.12, W2, H2), 26 * SS * s, fill=(118, 70, 38), outline=(70, 40, 20), width=int(4 * SS * s))
    d.rounded_rectangle((W2 * 0.05, H2 * 0.2, W2 * 0.95, H2 * 0.92), 20 * SS * s, outline=(170, 110, 60), width=int(3 * SS * s))
    d.polygon([(0, H2 * 0.14), (W2, H2 * 0.14), (W2, H2 * 0.5), (0, H2 * 0.5)], fill=(140, 86, 46))      # flap
    d.rounded_rectangle((W2 * 0.78, H2 * 0.38, W2 * 1.0, H2 * 0.62), 10 * SS * s, fill=(240, 196, 90), outline=(150, 100, 20), width=int(3 * SS * s))
    # tear at the bottom: jagged dark hole
    pts = []; n = 9
    for i in range(n + 1):
        x = W2 * (0.25 + 0.4 * i / n); y = H2 * (0.97 - (0.12 if i % 2 else 0.02) * open_)
        pts.append((x, y))
    pts += [(W2 * 0.65, H2), (W2 * 0.25, H2)]
    d.polygon(pts, fill=(25, 12, 6))
    return im.resize((w, h), Image.LANCZOS)

def _piggy(s):
    w, h = int(300 * s), int(230 * s); im = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im); W2, H2 = w * SS, h * SS
    pink, dark = (246, 160, 186), (196, 96, 130)
    for lx in (0.28, 0.62): d.rounded_rectangle((W2 * lx, H2 * 0.7, W2 * (lx + 0.11), H2 * 0.98), 8 * SS, fill=dark)
    d.ellipse((W2 * 0.08, H2 * 0.18, W2 * 0.92, H2 * 0.86), fill=pink, outline=dark, width=int(4 * SS * s))
    d.polygon([(W2 * 0.25, H2 * 0.26), (W2 * 0.33, H2 * 0.05), (W2 * 0.43, H2 * 0.22)], fill=dark)        # ear
    d.ellipse((W2 * 0.82, H2 * 0.42, W2 * 1.0, H2 * 0.64), fill=(250, 190, 205), outline=dark, width=int(4 * SS * s))   # snout
    for nx in (0.88, 0.94): d.ellipse((W2 * nx - 5 * SS, H2 * 0.51, W2 * nx + 5 * SS, H2 * 0.55 + 4 * SS), fill=dark)
    d.ellipse((W2 * 0.66, H2 * 0.36, W2 * 0.7, H2 * 0.42), fill=(40, 20, 30))                              # eye
    d.rounded_rectangle((W2 * 0.4, H2 * 0.17, W2 * 0.6, H2 * 0.23), 4 * SS, fill=(90, 40, 60))            # coin slot
    return im.resize((w, h), Image.LANCZOS)

def _calendar(s, filled, cur_p):
    w, h = int(330 * s), int(300 * s); im = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im); W2, H2 = w * SS, h * SS
    d.rounded_rectangle((0, 0, W2 - 1, H2 - 1), 24 * SS * s, fill=(250, 248, 242), outline=GOLD_EDGE, width=int(5 * SS * s))
    d.rounded_rectangle((0, 0, W2 - 1, H2 * 0.26), 24 * SS * s, fill=(22, 36, 86)); d.rectangle((0, H2 * 0.16, W2 - 1, H2 * 0.26), fill=(22, 36, 86))
    d.text((W2 / 2, H2 * 0.13), 'SETIAP BULAN', font=sans(H2 * 0.09, 'ExtraBold'), fill=(255, 214, 90), anchor='mm')
    for ring in (0.3, 0.7): d.rounded_rectangle((W2 * ring - 7 * SS, -10 * SS, W2 * ring + 7 * SS, 22 * SS), 6 * SS, fill=(150, 100, 20))
    cols, rows = 4, 3; cw, ch = W2 * 0.86 / cols, H2 * 0.62 / rows; x0, y0 = W2 * 0.07, H2 * 0.32
    for i in range(cols * rows):
        cx = x0 + (i % cols + 0.5) * cw; cy = y0 + (i // cols + 0.5) * ch; r = min(cw, ch) * 0.36
        if i < filled or (i == filled and cur_p > 0):
            k = 1.0 if i < filled else pop(cur_p)
            rr = r * k; d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(240, 182, 50), outline=(160, 100, 10), width=int(3 * SS * s))
            d.text((cx, cy), 'RM', font=sans(rr * 0.8, 'Black'), fill=(110, 60, 0), anchor='mm')
        else:
            d.ellipse((cx - r * 0.5, cy - r * 0.5, cx + r * 0.5, cy + r * 0.5), outline=(200, 196, 186), width=int(2 * SS * s))
    return im.resize((w, h), Image.LANCZOS)

def manim(el, t, W, H):
    s, e = el['s'], el['e']; u = t - s
    if t < s or t > e: return None
    fr = Image.new('RGBA', (W, H), (0, 0, 0, 0)); kind = el['kind']; sc = el.get('size', 1.0)
    cx, cy = el.get('x', W / 2), el['cy']; fade = min(1.0, u / 0.2, max(0.0, (e - t) / 0.25))
    rnd = random.Random(7)
    if kind == 'money_fly':     # banknotes float up and away from both sides
        for i in range(8):
            side = -1 if i % 2 == 0 else 1; st = i * 0.22; v = u - st
            if v < 0: continue
            x = cx + side * (230 + rnd.uniform(0, 140)) * sc + side * v * 60 * sc
            y = cy + 140 * sc - v * 260 * sc - 40 * math.sin(v * 3 + i)
            n = _note(int(150 * sc), int(76 * sc), side * (10 + v * 40 + rnd.uniform(-15, 15)))
            _paste(fr, n, x, y, fade * min(1, v / 0.15) * max(0, 1 - v / 2.6))
    elif kind == 'wallet_leak':  # torn wallet, notes and coins drop out of the hole
        p = ease_out(u / 0.3); wl = _wallet(sc); _paste(fr, wl, cx, cy - 40 * (1 - p), fade * p)
        for i in range(7):
            v = u - 0.25 - i * 0.16
            if v < 0: continue
            x = cx + (-60 + rnd.uniform(0, 120)) * sc; y = cy + 90 * sc + 0.5 * 1800 * v * v * sc
            if i % 2: it = _note(int(110 * sc), int(56 * sc), rnd.uniform(-60, 60) + v * 200)
            else: it = _gcoin(int(26 * sc), v * 3)
            _paste(fr, it, x, y, fade * max(0, 1 - v / 0.9))
    elif kind == 'piggy':        # coins drop into the piggy bank one by one
        p = ease_out(u / 0.3); pg = _piggy(sc); px, py = cx, cy + 40 * (1 - p)
        period = el.get('every', 1.1); slot = (px - 0.0 * sc, py - pg.height * 0.3)
        for i in range(int(u / period) + 1):
            v = u - 0.3 - i * period
            if v < 0 or v > 0.55: continue
            y = slot[1] - 220 * sc + 0.5 * 1500 * v * v * sc
            if y < slot[1] + 5: _paste(fr, _gcoin(int(30 * sc), v * 2), slot[0], y, fade)
        _paste(fr, pg, px, py, fade * p)
        bump = max(0, 1 - ((u - 0.3) % period) / 0.2) if u > 0.85 else 0
        if bump > 0: ImageDraw.Draw(fr).text((px + pg.width * 0.45, py - pg.height * 0.55), '+RM', font=sans(40 * sc, 'Black'), fill=(255, 214, 90, int(255 * bump * fade)), anchor='mm')
    elif kind == 'calendar':     # a coin appears on each month
        p = ease_out(u / 0.3); per = el.get('every', 0.35); start = 0.35
        filled = int(max(0, u - start) / per); cur = (max(0, u - start) % per) / per
        cal = _calendar(sc, min(12, filled), cur if filled < 12 else 0); _paste(fr, cal, cx, cy + 50 * (1 - p), fade * p)
    return fr
