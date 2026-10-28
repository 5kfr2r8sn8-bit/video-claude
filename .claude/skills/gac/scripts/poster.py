#!/usr/bin/env python3
"""Cover / carousel poster: 3D headline + the participant's own photo (cut out) on a drawn background.
Usage: python3 poster.py spec.json OUT.png

spec = {
  "size": [1080, 1350],                     # 4:5 (TikTok photo / Instagram); [1080, 1920] for 9:16
  "photo": "foto.jpg",                      # person is cut out automatically (U^2-Net human seg)
  "person_h": 0.62, "person_x": 0.5,        # height as a share of the canvas, centre x
  "background": "sky" | "gold" | "path/to/image.jpg",
  "lines": [{"text": "Cara Daftar", "style": "white", "size": 150},
            {"text": "Akaun Emas", "style": "gold", "size": 170},
            {"text": "di Public Gold", "style": "white", "size": 150},
            {"text": "Tak sampai 5 minit, siap!", "style": "sub", "size": 62}],
  "top": 70                                 # y of the first line
}
Styles: white / gold = chunky 3D extruded text (gold gets a glow and sparkles); sub = flat white with a shadow.
Nothing in the drawn background comes from another person's picture."""
import json, os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
MONT = os.path.join(HERE, '..', 'assets', 'fonts', 'Montserrat.ttf')

def font(sz, var='Black'):
    f = ImageFont.truetype(MONT, int(sz)); f.set_variation_by_name(var); return f

# ---------------------------------------------------------------- person cut-out
def cut_person(path):
    import onnxruntime as ort
    model = os.path.expanduser('~/.cache/gac/models/u2net_human_seg.onnx')
    if not os.path.exists(model):
        import subprocess
        os.makedirs(os.path.dirname(model), exist_ok=True)
        subprocess.run(['curl', '-fsSL', '-o', model, 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx'], check=True)
    im = ImageOps.exif_transpose(Image.open(path)).convert('RGB'); W, H = im.size
    s = ort.InferenceSession(model, providers=['CPUExecutionProvider'])
    x = np.asarray(im.resize((320, 320), Image.BILINEAR)) / 255.0
    x = ((x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]).transpose(2, 0, 1)[None].astype(np.float32)
    o = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]; o = (o - o.min()) / (o.max() - o.min() + 1e-9)
    m = Image.fromarray((o * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    m = m.point(lambda v: 0 if v < 40 else (255 if v > 200 else int((v - 40) * 255 / 160)))
    out = im.convert('RGBA'); out.putalpha(m); return out.crop(m.getbbox())

# ---------------------------------------------------------------- backgrounds
def bg_sky(W, H, seed=3):
    """Rich blue sky, soft large clouds, a bright horizon band and a navy floor with a light pool for the subject."""
    rnd = np.random.default_rng(seed)
    y = np.linspace(0, 1, H)[:, None, None]
    stops = [(0, (6, 22, 92)), (0.35, (16, 62, 178)), (0.62, (60, 132, 228)), (0.70, (178, 214, 250)),
             (0.72, (40, 70, 140)), (1, (10, 20, 52))]
    g = np.zeros((H, 1, 3))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        k = (y[:, 0, 0] >= p0) & (y[:, 0, 0] <= p1); t = ((y[k, 0, 0] - p0) / (p1 - p0))[:, None]
        g[k, 0] = np.array(c0) + (np.array(c1) - np.array(c0)) * t
    img = Image.fromarray(np.repeat(g, W, axis=1).astype(np.uint8), 'RGB').convert('RGBA')
    clouds = Image.new('L', (W // 6, H // 6), 0); d = ImageDraw.Draw(clouds)
    for _ in range(14):
        cx, cy = rnd.uniform(-10, W // 6 + 10), rnd.uniform(0, H // 6 * 0.62); r = rnd.uniform(10, 28)
        for _ in range(7):
            ox, oy = rnd.normal(0, r), rnd.normal(0, r * 0.2); rr = r * rnd.uniform(0.5, 1.0)
            d.ellipse((cx + ox - rr, cy + oy - rr * 0.45, cx + ox + rr, cy + oy + rr * 0.45), fill=int(rnd.uniform(90, 170)))
    clouds = clouds.filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BICUBIC)
    white = Image.new('RGBA', (W, H), (240, 246, 255, 255)); white.putalpha(clouds.point(lambda v: int(v * 0.5)))
    img.alpha_composite(white)
    pool = Image.new('L', (W, H), 0); ImageDraw.Draw(pool).ellipse((W * 0.15, H * 0.80, W * 0.85, H * 1.05), fill=170)
    lite = Image.new('RGBA', (W, H), (120, 170, 240, 255)); lite.putalpha(pool.filter(ImageFilter.GaussianBlur(W // 10)))
    img.alpha_composite(lite)
    vig = Image.new('L', (W, H), 0); ImageDraw.Draw(vig).ellipse((-W * 0.35, -H * 0.25, W * 1.35, H * 1.3), fill=255)
    dark = Image.new('RGBA', (W, H), (0, 6, 30, 255)); dark.putalpha(ImageOps.invert(vig.filter(ImageFilter.GaussianBlur(W // 5))).point(lambda v: int(v * 0.75)))
    img.alpha_composite(dark)
    return img

def bg_gold(W, H):
    y = np.linspace(0, 1, H)[:, None, None]; a, b = np.array([40, 26, 6]), np.array([150, 104, 28])
    img = Image.fromarray(np.repeat(a + (b - a) * y, W, axis=1).astype(np.uint8), 'RGB').convert('RGBA')
    glow = Image.new('L', (W, H), 0); ImageDraw.Draw(glow).ellipse((W * 0.05, H * 0.35, W * 0.95, H * 1.1), fill=200)
    warm = Image.new('RGBA', (W, H), (255, 220, 140, 255)); warm.putalpha(glow.filter(ImageFilter.GaussianBlur(W // 5)))
    img.alpha_composite(warm); return img

def bokeh(img, n=40, seed=5):
    W, H = img.size; rnd = random.Random(seed); lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for _ in range(n):
        x, y, r = rnd.uniform(0, W), rnd.uniform(H * 0.3, H), rnd.uniform(3, 12)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 230, 170, rnd.randint(60, 160)))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(2)))

# ---------------------------------------------------------------- 3D text
def text_mask(text, f, pad):
    bb = f.getbbox(text); w, h = bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).text((pad - bb[0], pad - bb[1]), text, font=f, fill=255); return m

def vgrad(size, stops):
    w, h = size; y = np.linspace(0, 1, h); out = np.zeros((h, 3))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        k = (y >= p0) & (y <= p1); t = ((y[k] - p0) / max(1e-6, p1 - p0))[:, None]
        out[k] = np.array(c0) + (np.array(c1) - np.array(c0)) * t
    return Image.fromarray(np.repeat(out[:, None, :], w, axis=1).astype(np.uint8), 'RGB').convert('RGBA')

def sparkle(d, x, y, r, a=255):
    for k in range(3, 0, -1):
        rr = r * k / 3; al = int(a * (0.25 if k == 3 else 0.5 if k == 2 else 1))
        d.polygon([(x, y - rr * 2.2), (x + rr * 0.28, y - rr * 0.28), (x + rr * 2.2, y), (x + rr * 0.28, y + rr * 0.28),
                   (x, y + rr * 2.2), (x - rr * 0.28, y + rr * 0.28), (x - rr * 2.2, y), (x - rr * 0.28, y - rr * 0.28)], fill=(255, 250, 225, al))
    d.ellipse((x - r * 0.5, y - r * 0.5, x + r * 0.5, y + r * 0.5), fill=(255, 255, 255, a))

POPPINS = os.path.join(HERE, '..', 'assets', 'fonts', 'Poppins-Black.ttf')

def line_mask(text, size, track=-0.035, pad=60):
    """Heavy headline mask: Poppins Black with tight tracking (letters almost touching, as in thumbnail posters)."""
    f = ImageFont.truetype(POPPINS, int(size)); tr = track * size
    w = int(sum(f.getlength(c) + tr for c in text) + pad * 2); asc, desc = f.getmetrics(); h = asc + desc + pad * 2
    m = Image.new('L', (w, h), 0); d = ImageDraw.Draw(m); x = pad
    for c in text: d.text((x, pad), c, font=f, fill=255); x += f.getlength(c) + tr
    return m.crop(m.getbbox()), f

def emboss(m, size, soft=0.05):
    """Lighting (0..1) of a pillow-shaped surface built from the letter mask; light from the top-left."""
    hgt = np.asarray(m.filter(ImageFilter.GaussianBlur(max(2, size * soft))), np.float32) / 255.0
    gy, gx = np.gradient(hgt); k = 9.0
    nx, ny, nz = -gx * k, -gy * k, np.ones_like(hgt); n = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    L = np.array([-0.45, -0.65, 0.62]); L = L / np.linalg.norm(L)
    return np.clip((nx * L[0] + ny * L[1] + nz * L[2]) / n, 0, 1)

PAL = {
    'gold':  dict(face=[(0, (255, 236, 120)), (0.35, (255, 206, 30)), (0.7, (244, 150, 0)), (1, (255, 186, 20))],
                  side=((196, 110, 0), (110, 52, 0)), rim=(132, 66, 0), spec=(255, 250, 210), lit=(0.62, 0.55)),
    'white': dict(face=[(0, (255, 255, 255)), (0.6, (246, 248, 252)), (1, (214, 222, 236))],
                  side=((176, 188, 214), (104, 116, 150)), rim=(78, 88, 120), spec=(255, 255, 255), lit=(0.93, 0.1)),
}

def text3d(text, size, style, max_w, target_w=None):
    if style == 'sub':
        m, f = line_mask(text, size, track=-0.01, pad=30)
        while m.width > max_w * 0.8 and size > 30: size -= 2; m, f = line_mask(text, size, track=-0.01, pad=30)
        w, h = m.size; P = 24; out = Image.new('RGBA', (w + P * 2, h + P * 2), (0, 0, 0, 0)); mm = Image.new('L', out.size, 0); mm.paste(m, (P, P))
        sh = Image.new('RGBA', out.size, (0, 8, 40, 0)); sh.putalpha(mm.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(4)))
        out.alpha_composite(sh, (0, 0)); out.alpha_composite(sh, (3, 6))
        face = Image.new('RGBA', out.size, (255, 255, 255, 255)); face.putalpha(mm); out.alpha_composite(face)
        return out.rotate(3, resample=Image.BICUBIC, expand=True)
    m, f = line_mask(text, size)
    if target_w:   # fit the line to a target width (thumbnail look: every line spans the frame)
        size = size * target_w / m.width; m, f = line_mask(text, size)
    while m.width > max_w and size > 40: size -= 4; m, f = line_mask(text, size)
    pal = PAL['gold' if style == 'gold' else 'white']
    depth = int(size * 0.13); dx = 0.42; P = depth + 50
    w, h = m.size; W2, H2 = w + P * 2, h + P * 2
    M = Image.new('L', (W2, H2), 0); M.paste(m, (P - depth // 3, P - depth // 2)); ox, oy = P - depth // 3, P - depth // 2
    out = Image.new('RGBA', (W2, H2), (0, 0, 0, 0))
    sm = Image.new('L', (W2, H2), 0); sm.paste(m, (int(ox + depth * 0.9), int(oy + depth * 1.5)))   # drop shadow
    sh = Image.new('RGBA', (W2, H2), (0, 4, 24, 0)); sh.putalpha(sm.filter(ImageFilter.GaussianBlur(size * 0.07)).point(lambda v: int(v * 0.7)))
    out.alpha_composite(sh)
    if style == 'gold':
        gl = Image.new('RGBA', (W2, H2), (255, 190, 60, 0)); gl.putalpha(M.filter(ImageFilter.GaussianBlur(size * 0.18)).point(lambda v: int(v * 0.55)))
        out.alpha_composite(gl)
    (a0, a1) = pal['side']
    for k in range(depth, 0, -1):   # extrusion towards the bottom-right, lit side lighter
        t = k / depth; col = tuple(int(a + (b - a) * t) for a, b in zip(a0, a1))
        lay = Image.new('RGBA', (w, h), col + (255,)); lay.putalpha(m); out.alpha_composite(lay, (int(ox + k * dx), int(oy + k)))
    edge = Image.new('RGBA', (W2, H2), pal['rim'] + (255,)); edge.putalpha(M.filter(ImageFilter.MaxFilter(3))); out.alpha_composite(edge)
    light = emboss(m, size, 0.05 if style == 'gold' else 0.022)
    base = np.asarray(vgrad((w, h), pal['face']).convert('RGB'), np.float32)
    col = base * (pal['lit'][0] + pal['lit'][1] * light[..., None]) + np.array(pal['spec']) * (light[..., None] ** 14) * 0.85
    face = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), 'RGB').convert('RGBA'); face.putalpha(m.filter(ImageFilter.MinFilter(3)))
    out.alpha_composite(face, (ox, oy))
    if style == 'gold':
        d = ImageDraw.Draw(out); bb = M.getbbox()
        for fx, fy, r in ((0.03, 0.6, 24), (0.97, 0.15, 28), (0.42, 0.05, 16), (0.8, 0.95, 14), (0.62, 0.5, 9)):
            x, y = bb[0] + (bb[2] - bb[0]) * fx, bb[1] + (bb[3] - bb[1]) * fy; flare(out, x, y, r)
    return out.rotate(2, resample=Image.BICUBIC, expand=True)

def flare(img, x, y, r):
    """Lens-flare glint: soft glow, long thin horizontal streak, 4-point star."""
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.ellipse((x - r * 2.2, y - r * 2.2, x + r * 2.2, y + r * 2.2), fill=(255, 210, 120, 120))
    lay = lay.filter(ImageFilter.GaussianBlur(r)); d = ImageDraw.Draw(lay)
    d.line([(x - r * 7, y), (x + r * 7, y)], fill=(255, 236, 190, 150), width=max(2, r // 6))
    sparkle(d, x, y, r * 0.75); img.alpha_composite(lay)

def sticker(p, border=16, vivid=True):
    """Person as a sticker: punchy colours, thick white outline, soft drop shadow."""
    from PIL import ImageEnhance
    if vivid:
        a = p.getchannel('A'); rgb = p.convert('RGB')
        rgb = ImageEnhance.Color(rgb).enhance(1.35); rgb = ImageEnhance.Contrast(rgb).enhance(1.15)
        rgb = ImageEnhance.Sharpness(rgb).enhance(1.8); rgb = ImageEnhance.Brightness(rgb).enhance(1.04)
        p = rgb.convert('RGBA'); p.putalpha(a)
    pad = border * 3; W2, H2 = p.width + pad * 2, p.height + pad * 2
    a = Image.new('L', (W2, H2), 0); a.paste(p.getchannel('A').point(lambda v: 255 if v > 110 else 0), (pad, pad))
    ring = a.filter(ImageFilter.MaxFilter(border * 2 + 1)).filter(ImageFilter.GaussianBlur(1.5)).point(lambda v: 255 if v > 127 else 0)
    out = Image.new('RGBA', (W2, H2), (0, 0, 0, 0))
    sh = Image.new('RGBA', (W2, H2), (0, 6, 30, 0)); sh.putalpha(ring.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.6)))
    out.alpha_composite(sh, (6, 14))
    wh = Image.new('RGBA', (W2, H2), (255, 255, 255, 255)); wh.putalpha(ring.filter(ImageFilter.GaussianBlur(0.8))); out.alpha_composite(wh)
    out.alpha_composite(p, (pad, pad)); return out, pad

def person_glow(p):
    """Soft white halo around the person, like a rim light."""
    pad = 60; out = Image.new('RGBA', (p.width + pad * 2, p.height + pad * 2), (0, 0, 0, 0))
    a = Image.new('L', out.size, 0); a.paste(p.getchannel('A'), (pad, pad))
    halo = Image.new('RGBA', out.size, (255, 246, 220, 0)); halo.putalpha(a.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.85)))
    out.alpha_composite(halo); out.alpha_composite(p, (pad, pad)); return out, pad

def main():
    spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; base = os.path.dirname(os.path.abspath(sys.argv[1]))
    P = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    W, H = spec.get('size', [1080, 1350]); bgk = spec.get('background', 'sky')
    if bgk == 'sky': img = bg_sky(W, H); bokeh(img)
    elif bgk == 'gold': img = bg_gold(W, H); bokeh(img)
    elif bgk == 'own':   # the participant's own photo, blurred into bokeh, darker at the top for the headline
        src = ImageOps.exif_transpose(Image.open(P(spec['photo']))).convert('RGB')
        img = ImageOps.fit(src, (W, H)).filter(ImageFilter.GaussianBlur(spec.get('blur', 28))).convert('RGBA')
        y_ = np.linspace(0, 1, H)[:, None]; a = (0.72 * (1 - y_ / 0.6).clip(0, 1) + 0.18).clip(0, 1)
        shade = Image.fromarray((np.repeat(a, W, axis=1) * 255).astype(np.uint8))
        dk = Image.new('RGBA', (W, H), tuple(spec.get('shade', [28, 16, 4])) + (255,)); dk.putalpha(shade); img.alpha_composite(dk)
        bokeh(img, 60)
    else: img = ImageOps.fit(Image.open(P(bgk)).convert('RGBA'), (W, H))
    # headline first (to know where it ends), then the person fitted between the headline and the floor
    texts, y, ys = [], spec.get('top', 70), []
    for ln in spec['lines']:
        t = text3d(ln['text'], ln.get('size', 150), ln.get('style', 'white'), W - 60, W * ln['width'] if ln.get('width') else None)
        t = t.crop(t.getchannel('A').point(lambda v: 255 if v > 20 else 0).getbbox())
        texts.append(t); ys.append(y + 30); y += t.height - int(t.height * ln.get('overlap', 0.16))
    text_bottom = ys[-1] - 30 + texts[-1].height - 20
    if spec.get('photo'):
        p = cut_person(P(spec['photo'])); floor = int(H * spec.get('floor', 0.955))
        ph = min(int(H * spec.get('person_h', 0.7)), floor - text_bottom + int(H * spec.get('overlap', 0.0)))
        if spec.get('crop_bottom'):   # poster crop: the person is scaled up from the head and runs off the bottom edge
            ph = int(H * spec['crop_bottom']); floor = text_bottom - int(H * spec.get('overlap', 0.0)) + ph
        p = p.resize((int(p.width * ph / p.height), ph), Image.LANCZOS)
        pg, pad = (sticker(p, spec.get('border', 16)) if spec.get('look', 'sticker') == 'sticker' else person_glow(p))
        x = int(W * spec.get('person_x', 0.5) - pg.width / 2); y0 = floor - ph - pad
        sh = Image.new('L', (W, H), 0); fy = floor
        ImageDraw.Draw(sh).ellipse((x + pad - 40, fy - 30, x + pad + p.width + 40, fy + 26), fill=210)
        shl = Image.new('RGBA', (W, H), (0, 0, 10, 255)); shl.putalpha(sh.filter(ImageFilter.GaussianBlur(16)))
        if not spec.get('crop_bottom'): img.alpha_composite(shl)
        img.alpha_composite(pg, (x, y0))
    for t, y in zip(texts, ys):
        img.alpha_composite(t, (int((W - t.width) / 2), int(y - 30)))
    img.convert('RGB').save(out_path, quality=95)
    print(json.dumps({'out': out_path, 'size': [W, H]}))

if __name__ == '__main__': main()
