#!/usr/bin/env python3
"""Draw simple flat-graphic icons in the gold-dealer palette (PG maroon + rich gold), transparent PNG.
Use for shapes that blend with any style (gift box, arrows, badges); realistic 3D objects should
still come from an AI image tool so they match the user's existing 3D icon set.
Usage: python3 draw_icon.py hadiah OUT.png"""
import sys, numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 4; N = 1024 * SS
MAROON = ((175, 32, 50), (110, 14, 28)); BODY = ((150, 22, 38), (92, 10, 22)); GOLD = ((255, 226, 140), (196, 124, 18))
def S_(v): return int(v * SS)

def grad(c1, c2, diagonal=False):
    y = np.linspace(0, 1, N)[:, None] * np.ones((1, N)); x = np.ones((N, 1)) * np.linspace(0, 1, N)[None, :]
    t = np.clip(x * 0.5 + y * 0.5, 0, 1) if diagonal else y
    a = np.array(c1)[None, None, :] * (1 - t[..., None]) + np.array(c2)[None, None, :] * t[..., None]
    return Image.fromarray(a.astype(np.uint8), 'RGB').convert('RGBA')

def shape(fn, fill):
    m = Image.new('L', (N, N), 0); fn(ImageDraw.Draw(m)); out = Image.new('RGBA', (N, N), (0, 0, 0, 0)); out.paste(fill, (0, 0), m); return out

def layer(fn, blur=0):
    im = Image.new('RGBA', (N, N), (0, 0, 0, 0)); fn(ImageDraw.Draw(im)); return im.filter(ImageFilter.GaussianBlur(blur)) if blur else im

def sparkles(c, pts):
    def fn(d):
        for cx, cy, r in pts:
            cx, cy, r = S_(cx), S_(cy), S_(r)
            d.polygon([(cx, cy - r * 2), (cx + r * .35, cy - r * .35), (cx + r * 2, cy), (cx + r * .35, cy + r * .35),
                       (cx, cy + r * 2), (cx - r * .35, cy + r * .35), (cx - r * 2, cy), (cx - r * .35, cy - r * .35)], fill=(255, 244, 200, 235))
    c.alpha_composite(layer(fn, S_(1)))

def hadiah():
    c = Image.new('RGBA', (N, N), (0, 0, 0, 0)); gold = grad(*GOLD, diagonal=True)
    c.alpha_composite(layer(lambda d: d.ellipse((S_(170), S_(900), S_(854), S_(980)), fill=(0, 0, 0, 140)), S_(22)))
    c.alpha_composite(shape(lambda d: d.rounded_rectangle((S_(210), S_(470), S_(814), S_(930)), S_(26), fill=255), grad(*BODY)))
    c.alpha_composite(layer(lambda d: d.rounded_rectangle((S_(560), S_(470), S_(814), S_(930)), S_(26), fill=(0, 0, 0, 60))))
    c.alpha_composite(shape(lambda d: d.rounded_rectangle((S_(170), S_(380), S_(854), S_(500)), S_(24), fill=255), grad(*MAROON)))
    c.alpha_composite(layer(lambda d: d.rounded_rectangle((S_(190), S_(392), S_(834), S_(420)), S_(14), fill=(255, 255, 255, 55)), S_(4)))
    c.alpha_composite(shape(lambda d: d.rectangle((S_(462), S_(380), S_(562), S_(930)), fill=255), gold))
    c.alpha_composite(layer(lambda d: d.rectangle((S_(470), S_(380), S_(486), S_(930)), fill=(255, 250, 220, 120)), S_(3)))
    c.alpha_composite(shape(lambda d: (d.ellipse((S_(300), S_(230), S_(520), S_(400)), fill=255), d.ellipse((S_(504), S_(230), S_(724), S_(400)), fill=255)), gold))
    c.alpha_composite(layer(lambda d: (d.ellipse((S_(350), S_(270), S_(480), S_(360)), fill=(120, 70, 8, 255)), d.ellipse((S_(544), S_(270), S_(674), S_(360)), fill=(120, 70, 8, 255))), S_(6)))
    c.alpha_composite(shape(lambda d: d.rounded_rectangle((S_(452), S_(300), S_(572), S_(410)), S_(30), fill=255), grad((255, 236, 170), (214, 150, 30), True)))
    c.alpha_composite(shape(lambda d: (d.polygon([(S_(470), S_(400)), (S_(400), S_(520)), (S_(440), S_(530)), (S_(500), S_(410))], fill=255),
                                       d.polygon([(S_(554), S_(400)), (S_(624), S_(520)), (S_(584), S_(530)), (S_(524), S_(410))], fill=255)), gold))
    sparkles(c, [(760, 300, 34), (250, 560, 20)])
    return c

import math

def radial(c_in, c_out, cx=0.4, cy=0.35):
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / N
    t = np.clip(np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / 0.75, 0, 1)[..., None]
    a = np.array(c_in) * (1 - t) + np.array(c_out) * t
    return Image.fromarray(a.astype(np.uint8), 'RGB').convert('RGBA')

def ground_shadow(c, x0, x1, y):
    c.alpha_composite(layer(lambda d: d.ellipse((S_(x0), S_(y - 30), S_(x1), S_(y + 30)), fill=(0, 0, 0, 120)), S_(22)))

def jam():
    """Gold alarm-style clock face with 24 at the top: open around the clock."""
    c = Image.new('RGBA', (N, N), (0, 0, 0, 0)); ground_shadow(c, 220, 804, 950)
    c.alpha_composite(shape(lambda d: d.ellipse((S_(130), S_(110), S_(894), S_(874)), fill=255), radial((255, 230, 150), (176, 112, 14))))
    c.alpha_composite(shape(lambda d: d.ellipse((S_(190), S_(170), S_(834), S_(814)), fill=255), radial((255, 253, 246), (232, 224, 210), 0.45, 0.4)))
    def ticks(d):
        cx, cy, r = S_(512), S_(492), S_(300)
        for k in range(24):
            ang = k / 24 * 2 * math.pi; big = k % 6 == 0; l = S_(46 if big else 22)
            x0, y0 = cx + math.sin(ang) * r, cy - math.cos(ang) * r; x1, y1 = cx + math.sin(ang) * (r - l), cy - math.cos(ang) * (r - l)
            d.line((x0, y0, x1, y1), fill=(120, 40, 30, 255) if big else (150, 120, 90, 255), width=S_(12 if big else 6))
    c.alpha_composite(layer(ticks))
    from PIL import ImageFont
    fnt = None
    for fp in ['/System/Library/Fonts/Avenir Next.ttc', '/System/Library/Fonts/Supplemental/Arial Bold.ttf']:
        try: fnt = ImageFont.truetype(fp, S_(96), index=0); break
        except Exception: pass
    c.alpha_composite(layer(lambda d: d.text((S_(512), S_(330)), '24', font=fnt, fill=(150, 22, 38, 255), anchor='mm')))
    def hands(d):
        cx, cy = S_(512), S_(492)
        d.line((cx, cy, cx + S_(150), cy + S_(70)), fill=(42, 30, 30, 255), width=S_(22))
        d.line((cx, cy, cx - S_(190), cy + S_(110)), fill=(42, 30, 30, 255), width=S_(14))
        d.ellipse((cx - S_(26), cy - S_(26), cx + S_(26), cy + S_(26)), fill=(196, 124, 18, 255))
    c.alpha_composite(layer(hands))
    c.alpha_composite(layer(lambda d: d.arc((S_(200), S_(180), S_(824), S_(804)), 200, 260, fill=(255, 255, 255, 150), width=S_(14)), S_(3)))
    return c

def bulan():
    """Gold crescent moon with small stars: late night."""
    c = Image.new('RGBA', (N, N), (0, 0, 0, 0))
    m = Image.new('L', (N, N), 0); d = ImageDraw.Draw(m)
    d.ellipse((S_(170), S_(150), S_(830), S_(810)), fill=255); d.ellipse((S_(380), S_(80), S_(960), S_(660)), fill=0)
    moon = Image.new('RGBA', (N, N), (0, 0, 0, 0)); moon.paste(radial((255, 236, 170), (186, 114, 14), 0.3, 0.6), (0, 0), m)
    glow = Image.new('RGBA', (N, N), (255, 200, 80, 0)); glow.putalpha(m.filter(ImageFilter.GaussianBlur(S_(30))).point(lambda v: int(v * 0.5)))
    c.alpha_composite(glow); c.alpha_composite(moon)
    sparkles(c, [(720, 600, 30), (820, 420, 20), (640, 760, 16)])
    return c

def glob():
    """Blue globe with gold meridians and parallels: anywhere in the world."""
    c = Image.new('RGBA', (N, N), (0, 0, 0, 0)); ground_shadow(c, 230, 794, 955)
    c.alpha_composite(shape(lambda d: d.ellipse((S_(150), S_(130), S_(874), S_(854)), fill=255), radial((110, 180, 240), (20, 60, 130), 0.38, 0.32)))
    def lines(d):
        cx, cy, r = S_(512), S_(492), S_(362)
        for k in (-2, -1, 0, 1, 2):        # parallels
            y = cy + k * r * 0.38; hw = math.sqrt(max(0, r * r - (y - cy) ** 2))
            d.ellipse((cx - hw, y - hw * 0.12, cx + hw, y + hw * 0.12), outline=(247, 196, 90, 230), width=S_(8))
        for k in (0.25, 0.6, 0.95):         # meridians
            w = r * k; d.ellipse((cx - w, cy - r, cx + w, cy + r), outline=(247, 196, 90, 230), width=S_(8))
        d.line((cx, cy - r, cx, cy + r), fill=(247, 196, 90, 230), width=S_(8))
    c.alpha_composite(layer(lines))
    c.alpha_composite(layer(lambda d: d.ellipse((S_(260), S_(210), S_(480), S_(380)), fill=(255, 255, 255, 70)), S_(30)))
    return c

def _flag_card(draw_fn, ratio):
    """Flag on a rounded card with a soft shadow and a light gloss."""
    w = S_(860); h = int(w / ratio); x0 = (N - w) // 2; y0 = (N - h) // 2
    f = Image.new('RGBA', (w, h), (0, 0, 0, 0)); draw_fn(ImageDraw.Draw(f), w, h, f)
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), S_(28), fill=255)
    f.putalpha(Image.fromarray(np.minimum(np.array(f.getchannel('A')), np.array(m))))
    gl = np.linspace(0.28, 0, h)[:, None] * np.ones((1, w)); gloss = Image.new('RGBA', (w, h), (255, 255, 255, 0))
    gloss.putalpha(Image.fromarray((gl * 255 * (np.array(m) > 0)).astype(np.uint8))); f.alpha_composite(gloss)
    c = Image.new('RGBA', (N, N), (0, 0, 0, 0))
    sh = Image.new('RGBA', (N, N), (0, 0, 0, 0)); sh.paste(Image.new('RGBA', (w, h), (0, 0, 0, 150)), (x0, y0 + S_(24)), m)
    c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(S_(22)))); c.alpha_composite(f, (x0, y0)); return c

def _star(d, cx, cy, r, n, col, inner=0.45, rot=-math.pi / 2):
    pts = []
    for k in range(2 * n):
        rr = r if k % 2 == 0 else r * inner; a = rot + k * math.pi / n; pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=col)

def _union_jack(d, w, h, x=0, y=0):
    d.rectangle((x, y, x + w, y + h), fill=(1, 33, 105))
    t = h * 0.2; d.line((x, y, x + w, y + h), fill=(255, 255, 255), width=int(t)); d.line((x, y + h, x + w, y), fill=(255, 255, 255), width=int(t))
    d.line((x, y, x + w, y + h), fill=(200, 16, 46), width=int(t * 0.33)); d.line((x, y + h, x + w, y), fill=(200, 16, 46), width=int(t * 0.33))
    d.rectangle((x + w / 2 - h / 6, y, x + w / 2 + h / 6, y + h), fill=(255, 255, 255)); d.rectangle((x, y + h / 2 - h / 6, x + w, y + h / 2 + h / 6), fill=(255, 255, 255))
    d.rectangle((x + w / 2 - h / 10, y, x + w / 2 + h / 10, y + h), fill=(200, 16, 46)); d.rectangle((x, y + h / 2 - h / 10, x + w, y + h / 2 + h / 10), fill=(200, 16, 46))

def bendera_malaysia():
    def fn(d, w, h, im):
        for k in range(14): d.rectangle((0, k * h / 14, w, (k + 1) * h / 14), fill=(204, 0, 1) if k % 2 == 0 else (255, 255, 255))
        cw, ch = w / 2, h * 8 / 14; d.rectangle((0, 0, cw, ch), fill=(1, 0, 102))
        r = ch * 0.36; cx, cy = cw * 0.36, ch / 2
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 204, 0)); d.ellipse((cx - r * 0.82, cy - r * 0.8, cx + r * 0.95, cy + r * 0.8), fill=(1, 0, 102))
        d.ellipse((cx - r * 0.65, cy - r, cx + r * 1.25, cy + r), fill=(1, 0, 102))
        _star(d, cw * 0.68, ch / 2, ch * 0.3, 14, (255, 204, 0), 0.5)
    return _flag_card(fn, 2.0)

def bendera_indonesia():
    def fn(d, w, h, im):
        d.rectangle((0, 0, w, h / 2), fill=(206, 17, 38)); d.rectangle((0, h / 2, w, h), fill=(255, 255, 255))
    return _flag_card(fn, 1.5)

def bendera_uk():
    return _flag_card(lambda d, w, h, im: _union_jack(d, w, h), 2.0)

def bendera_australia():
    def fn(d, w, h, im):
        d.rectangle((0, 0, w, h), fill=(1, 33, 105)); _union_jack(d, w / 2, h / 2)
        W_ = (255, 255, 255)
        _star(d, w * 0.25, h * 0.75, h * 0.14, 7, W_, 0.45)
        for (fx, fy, r) in [(0.75, 0.83, 0.07), (0.75, 0.21, 0.07), (0.63, 0.47, 0.07), (0.87, 0.40, 0.07)]: _star(d, w * fx, h * fy, h * r, 7, W_, 0.45)
        _star(d, w * 0.80, h * 0.56, h * 0.04, 5, W_, 0.45)
    return _flag_card(fn, 2.0)

ICONS = dict(hadiah=hadiah, jam=jam, bulan=bulan, glob=glob, bendera_malaysia=bendera_malaysia,
             bendera_indonesia=bendera_indonesia, bendera_uk=bendera_uk, bendera_australia=bendera_australia)

if __name__ == '__main__':
    name, out = sys.argv[1], sys.argv[2]
    if name not in ICONS: sys.exit(f'unknown icon {name}; available: {", ".join(ICONS)}')
    im = ICONS[name]().resize((1024, 1024), Image.LANCZOS); im = im.crop(im.getbbox()); im.save(out); print(out)
