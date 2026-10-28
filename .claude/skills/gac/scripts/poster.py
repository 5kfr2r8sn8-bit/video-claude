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

def text3d(text, size, style, max_w):
    f = font(size)
    while f.getlength(text) > max_w and size > 40: size -= 4; f = font(size)
    if style == 'sub':
        m = text_mask(text, font(size, 'ExtraBold'), 30); w, h = m.size
        out = Image.new('RGBA', (w, h), (0, 0, 0, 0)); sh = Image.new('RGBA', (w, h), (0, 10, 40, 0)); sh.putalpha(m.filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.8)))
        out.alpha_composite(sh, (0, 0)); out.alpha_composite(sh, (2, 5)); face = Image.new('RGBA', (w, h), (255, 255, 255, 255)); face.putalpha(m)
        out.alpha_composite(face); return out.rotate(-2, resample=Image.BICUBIC, expand=True)
    depth = max(10, size // 7); pad = depth + 40
    m = text_mask(text, f, pad); w, h = m.size; out = Image.new('RGBA', (w, h + depth), (0, 0, 0, 0))
    if style == 'gold':
        face_stops = [(0, (255, 248, 196)), (0.45, (255, 214, 92)), (0.75, (240, 168, 38)), (1, (196, 118, 18))]
        side_a, side_b, rim = (150, 88, 14), (92, 50, 6), (110, 62, 8)
    else:
        face_stops = [(0, (255, 255, 255)), (0.6, (246, 248, 252)), (1, (206, 214, 228))]
        side_a, side_b, rim = (170, 180, 200), (96, 106, 130), (70, 80, 104)
    shadow = Image.new('RGBA', out.size, (0, 6, 30, 0)); sm = Image.new('L', out.size, 0); sm.paste(m, (8, depth + 12))
    shadow.putalpha(sm.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.75))); out.alpha_composite(shadow)
    if style == 'gold':   # warm glow around the gold word
        gl = Image.new('RGBA', out.size, (255, 196, 70, 0)); gm = Image.new('L', out.size, 0); gm.paste(m, (0, depth // 2))
        gl.putalpha(gm.filter(ImageFilter.GaussianBlur(26)).point(lambda v: int(v * 0.65))); out.alpha_composite(gl)
    for k in range(depth, 0, -1):   # extrusion, darker towards the back
        t = k / depth; col = tuple(int(a + (b - a) * t) for a, b in zip(side_a, side_b))
        lay = Image.new('RGBA', (w, h), col + (255,)); lay.putalpha(m); out.alpha_composite(lay, (0, k))
    edge = Image.new('RGBA', (w, h), rim + (255,)); edge.putalpha(m.filter(ImageFilter.MaxFilter(5))); out.alpha_composite(edge)
    if style == 'gold':
        face_stops = [(0, (255, 252, 220)), (0.3, (255, 226, 120)), (0.5, (255, 200, 60)), (0.52, (236, 160, 30)), (1, (255, 206, 90))]
    face = vgrad((w, h), face_stops); face.putalpha(m); out.alpha_composite(face)
    hi = Image.new('RGBA', (w, h), (255, 255, 255, 0))   # thin bright bevel along the top of each letter
    bev = Image.fromarray(np.clip(np.asarray(m, np.int16) - np.asarray(m.transform(m.size, Image.AFFINE, (1, 0, 0, 0, 1, 4)), np.int16), 0, 255).astype(np.uint8))
    hi.putalpha(bev.filter(ImageFilter.GaussianBlur(1)).point(lambda v: int(v * 0.8))); out.alpha_composite(hi)
    if style == 'gold':
        d = ImageDraw.Draw(out); rnd = random.Random(len(text))
        bb = m.getbbox()
        for x, y, r in ((bb[0] + 10, bb[1] + (bb[3] - bb[1]) * 0.55, 13), (bb[2] - 6, bb[1] + (bb[3] - bb[1]) * 0.3, 15),
                        (bb[0] + (bb[2] - bb[0]) * 0.42, bb[1] + 6, 9), (bb[0] + (bb[2] - bb[0]) * 0.8, bb[3] - 10, 8)):
            sparkle(d, x, y, r)
    return out

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
        t = text3d(ln['text'], ln.get('size', 150), ln.get('style', 'white'), W - 90)
        texts.append(t); ys.append(y); y += t.height - ln.get('tight', int(t.height * 0.34))
    text_bottom = ys[-1] - 30 + texts[-1].height - 20
    if spec.get('photo'):
        p = cut_person(P(spec['photo'])); floor = int(H * spec.get('floor', 0.955))
        ph = min(int(H * spec.get('person_h', 0.7)), floor - text_bottom + int(H * spec.get('overlap', 0.0)))
        if spec.get('crop_bottom'):   # poster crop: the person is scaled up from the head and runs off the bottom edge
            ph = int(H * spec['crop_bottom']); floor = text_bottom - int(H * spec.get('overlap', 0.0)) + ph
        p = p.resize((int(p.width * ph / p.height), ph), Image.LANCZOS)
        pg, pad = person_glow(p); x = int(W * spec.get('person_x', 0.5) - pg.width / 2); y0 = floor - ph - pad
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
