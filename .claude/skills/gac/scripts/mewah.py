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

TYPES = ('mtitle', 'mword', 'mstep', 'mpanel', 'mcta')

def prepare(el, N):
    ty = el['type']
    if ty == 'mpanel': el['_at'] = [N(a) for a in el.get('at', [el['t'][0]] * len(el['rows']))]
    el['cy'] = el.get('y') or {'mtitle': 330, 'mword': 360, 'mstep': 1180, 'mpanel': 1150, 'mcta': 1330}[ty]
    return el

def draw(el, t, W, H):
    s, e = el['s'], el['e']; u = t - s; ty = el['type']
    if t < s or t > e: return None
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
