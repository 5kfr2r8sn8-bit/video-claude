"""Carousel remake: a reference carousel -> the participant's own version.
Person swapped for the participant's photo (sticker look), other dealer's data replaced, TikTok UI removed,
optional new photo background. See ../references/carousel.md.

Usage: python3 carousel.py WORKDIR [slide_key ...]
WORKDIR holds: ref/<key>.jpg (reference slides), me/<n>.jpg (participant photos), bg/*.jpg (backgrounds),
slides.json (per-slide plan). Writes me/cut_<n>.png (cut-outs, made on first use) and out/<key>.jpg."""
import sys, os, json, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import poster

FD = os.path.join(HERE, '..', 'assets', 'fonts') + '/'
LIB = '/usr/share/fonts/truetype/liberation/'
def F(kind, sz):
    if kind.startswith('os'):           # Open Sans (the Public Gold app font)
        f = ImageFont.truetype(FD + 'OpenSans.ttf', int(sz)); f.set_variation_by_name({'os': 'Regular', 'osb': 'Bold', 'osx': 'ExtraBold'}[kind]); return f
    if kind == 'lib': return ImageFont.truetype(LIB + 'LiberationSans-Regular.ttf', int(sz))
    if kind == 'libi': return ImageFont.truetype(LIB + 'LiberationSans-Italic.ttf', int(sz))
    if kind == 'serif':
        f = ImageFont.truetype(FD + 'PlayfairDisplay.ttf', int(sz)); f.set_variation_by_name('Black'); return f

class _Me(dict):
    """me/cut_<n>.png, cut out of me/<n>.jpg on first use (largest person kept). Hand-fix a cut-out by editing the PNG."""
    def __getitem__(self, n):
        p = f'me/cut_{n}.png'
        if not os.path.exists(p):
            im = poster.cut_person(f'me/{n}.jpg'); a = np.asarray(im.getchannel('A'))
            k, lab, st, _ = cv2.connectedComponentsWithStats((a > 128).astype(np.uint8))
            if k > 2:
                keep = cv2.dilate((lab == 1 + np.argmax(st[1:, 4])).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
                im.putalpha(Image.fromarray(np.where(keep, a, 0).astype(np.uint8))); im = im.crop(im.getbbox())
            im.save(p)
        return p
ME = _Me()

def fill(img, mask, k=4, blur=3):
    """Fill mask (uint8 255 = hole). Low-res Telea for a smooth fill, blended back at full res."""
    H, W = mask.shape
    sm = cv2.resize(img, (W // k, H // k), interpolation=cv2.INTER_AREA)
    mm = cv2.dilate(cv2.resize(mask, (W // k, H // k), interpolation=cv2.INTER_NEAREST), np.ones((3, 3), np.uint8))
    f = cv2.inpaint(sm, mm, 5, cv2.INPAINT_TELEA)
    f = cv2.GaussianBlur(cv2.resize(f, (W, H), interpolation=cv2.INTER_CUBIC), (0, 0), blur)
    a = (cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 3) / 255.0)[..., None]
    return (img * (1 - a) + f * a).astype(np.uint8)

def fill_rows(img, mask, seed=1):
    """Fill wide holes row by row: blend the colours at the hole's left and right edges, then add fine grain.
    Avoids the ghost shapes Telea leaves when a whole group of people is removed."""
    out = img.astype(np.float32).copy(); H, W = mask.shape
    for y in range(H):
        xs = np.where(mask[y] > 0)[0]
        if not len(xs): continue
        # contiguous runs
        runs = np.split(xs, np.where(np.diff(xs) > 1)[0] + 1)
        for r in runs:
            a, b = r[0], r[-1]
            L = img[y, max(0, a - 24):max(1, a - 4)].reshape(-1, 3).mean(0) if a > 4 else None
            R = img[y, min(W - 1, b + 4):min(W, b + 24)].reshape(-1, 3).mean(0) if b < W - 5 else None
            if L is None: L = R
            if R is None: R = L
            t = np.linspace(0, 1, b - a + 1)[:, None]; out[y, a:b + 1] = L * (1 - t) + R * t
    sm = cv2.GaussianBlur(out, (0, 0), 9)
    rng = np.random.default_rng(seed); grain = rng.normal(0, 5, out.shape).astype(np.float32)
    res = np.where(mask[..., None] > 0, sm + grain, img)
    a = (cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 4) / 255.0)[..., None]
    return np.clip(img * (1 - a) + res * a, 0, 255).astype(np.uint8)

def fill_fine(img, mask):
    return cv2.inpaint(img, cv2.dilate(mask, np.ones((5, 5), np.uint8)), 7, cv2.INPAINT_TELEA)

def ref_person(img_rgb, region):
    """Mask of the reference person inside region (x0,y0,x1,y1)."""
    import onnxruntime as ort, os
    s = ort.InferenceSession(os.path.expanduser('~/.cache/gac/models/u2net_human_seg.onnx'), providers=['CPUExecutionProvider'])
    H, W = img_rgb.shape[:2]
    x = cv2.resize(img_rgb, (320, 320)).astype(np.float32) / 255
    x = ((x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]).transpose(2, 0, 1)[None].astype(np.float32)
    o = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]; o = (o - o.min()) / (o.max() - o.min() + 1e-9)
    m = (cv2.resize(o, (W, H)) > 0.25).astype(np.uint8) * 255
    keep = np.zeros_like(m); x0, y0, x1, y1 = region; keep[y0:y1, x0:x1] = m[y0:y1, x0:x1]
    return keep

def badge(d_img, cx, cy, r, num):
    """Gold coin badge with a black serif number (redrawn so the TikTok search bar can go and numbers run 1..10)."""
    S = 4; R = r * S; c = Image.new('RGBA', (2 * R + 8 * S, 2 * R + 8 * S), (0, 0, 0, 0)); C = c.width // 2
    yy, xx = np.mgrid[0:c.height, 0:c.width]; dist = np.hypot(xx - C, yy - C)
    t = np.clip((yy - (C - R)) / (2 * R), 0, 1)
    def grad(stops):
        out = np.zeros(t.shape + (3,))
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            k = (t >= p0) & (t <= p1); u = ((t[k] - p0) / (p1 - p0))[:, None]; out[k] = np.array(c0) + (np.array(c1) - np.array(c0)) * u
        return out
    rim = grad([(0, (255, 244, 180)), (0.45, (240, 180, 50)), (0.7, (176, 108, 10)), (1, (255, 210, 90))])
    face = grad([(0, (255, 236, 140)), (0.5, (250, 196, 60)), (1, (222, 150, 30))])
    rgb = np.where((dist < R * 0.82)[..., None], face, rim)
    ring = (np.abs(dist - R * 0.82) < S * 1.5)
    rgb[ring] = (150, 90, 10)
    a = np.clip((R - dist) / S, 0, 1) * 255
    c = Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), 'RGBA')
    d = ImageDraw.Draw(c); f = F('serif', R * (1.25 if len(num) == 1 else 0.95))
    d.text((C + S * 3, C + S * 4), num, font=f, fill=(120, 70, 0, 160), anchor='mm')
    d.text((C, C), num, font=f, fill=(12, 10, 8, 255), anchor='mm')
    sh = Image.new('RGBA', c.size, (0, 0, 0, 0)); sh.putalpha(c.getchannel('A').point(lambda v: int(v * 0.5)))
    out = Image.new('RGBA', c.size, (0, 0, 0, 0)); out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(S * 5)), (0, S * 3)); out.alpha_composite(c)
    gl = Image.new('RGBA', c.size, (255, 210, 110, 0)); gl.putalpha(c.getchannel('A').filter(ImageFilter.GaussianBlur(S * 10)).point(lambda v: int(v * 0.5)))
    out = Image.alpha_composite(gl, out)
    out = out.resize((out.width // S, out.height // S), Image.LANCZOS)
    d_img.alpha_composite(out, (int(cx - out.width / 2), int(cy - out.height / 2)))

def text_color(img, box, light_bg=True):
    x0, y0, x1, y1 = box; p = img[y0:y1, x0:x1].reshape(-1, 3).astype(int); s = p.sum(1)
    sel = p[s <= np.percentile(s, 8)] if light_bg else p[s >= np.percentile(s, 92)]
    return tuple(int(v) for v in np.median(sel, 0))

def edit_text(pil, img_before, e):
    """Replace text in box: clear with local background, draw new text. e = dict(box, text, font, size, color?, x?, y?)"""
    x0, y0, x1, y1 = e['box']
    col = tuple(e['color']) if e.get('color') else text_color(img_before, e['box'], e.get('light_bg', True))
    arr = np.asarray(pil.convert('RGB')).copy(); m = np.zeros(arr.shape[:2], np.uint8); m[y0:y1, x0:x1] = 255
    if e.get('flat', True):   # flat field: median of the ring around the box
        ring = np.concatenate([arr[y0 - 4:y0 - 1, x0:x1].reshape(-1, 3), arr[y1 + 1:y1 + 4, x0:x1].reshape(-1, 3),
                               arr[y0:y1, x0 - 4:x0 - 1].reshape(-1, 3), arr[y0:y1, x1 + 1:x1 + 4].reshape(-1, 3)])
        arr[y0:y1, x0:x1] = np.median(ring, 0)
    else:
        arr = fill_fine(arr, m)
    out = Image.fromarray(arr).convert('RGBA'); d = ImageDraw.Draw(out)
    f = F(e['font'], e['size'])
    while f.getlength(e['text']) > e.get('max_w', 9999) and f.size > 12: f = F(e['font'], f.size - 1)
    d.text((e.get('x', x0), e.get('y', (y0 + y1) / 2)), e['text'], font=f, fill=col, anchor=e.get('anchor', 'lm'))
    return out

def place_me(pil, n, flip, ref_mask, scale=1.0, dx=0, bottom=None, circle=False, border=10, height=None, right=None):
    p = Image.open(ME[n])
    if flip: p = ImageOps.mirror(p)
    ys, xs = np.where(ref_mask > 0)
    h = (height or (ys.max() - ys.min()) * scale); cx = (xs.min() + xs.max()) / 2 + dx; bot = bottom if bottom is not None else ys.max()
    if circle:
        w = (xs.max() - xs.min()) * scale; k = w / p.width
    else:
        k = h / p.height
    p = p.resize((int(p.width * k), int(p.height * k)), Image.LANCZOS)
    st, pad = poster.sticker(p, border)
    if right is not None: cx = right - p.width / 2
    pil.alpha_composite(st, (int(cx - st.width / 2), int(bot - p.height - pad)))
    return pil

def gold_text_line(text, size, width):
    """Serif 3D gold headline line (for replaced headline words)."""
    f = F('serif', size)
    while f.getlength(text) > width and size > 30: size -= 4; f = F('serif', size)
    pad = 40; bb = f.getbbox(text); w, h = bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).text((pad - bb[0], pad - bb[1]), text, font=f, fill=255)
    depth = max(6, size // 12); out = Image.new('RGBA', (w + depth, h + depth), (0, 0, 0, 0))
    sh = Image.new('RGBA', out.size, (0, 0, 20, 0)); sm = Image.new('L', out.size, 0); sm.paste(m, (depth, depth + 6))
    sh.putalpha(sm.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.7))); out.alpha_composite(sh)
    for k in range(depth, 0, -1):
        t = k / depth; col = tuple(int(a + (b - a) * t) for a, b in zip((170, 100, 10), (90, 45, 0)))
        lay = Image.new('RGBA', (w, h), col + (255,)); lay.putalpha(m); out.alpha_composite(lay, (k // 2, k))
    face = poster.vgrad((w, h), [(0, (255, 248, 200)), (0.45, (255, 214, 90)), (0.75, (230, 160, 40)), (1, (255, 200, 90))])
    light = poster.emboss(m, size, 0.04)
    arr = np.asarray(face.convert('RGB'), np.float32) * (0.62 + 0.55 * light[..., None]) + 255 * (light[..., None] ** 14) * 0.6
    fc = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA'); fc.putalpha(m); out.alpha_composite(fc)
    return out

def prep_bg(path, W, H, dark=0.0):
    im = ImageOps.exif_transpose(Image.open(path)).convert('RGB')
    k = max(W / im.width, H / im.height); im = im.resize((int(im.width * k + 1), int(im.height * k + 1)), Image.LANCZOS)
    x0 = (im.width - W) // 2; im = im.crop((x0, im.height - H, x0 + W, im.height))   # keep the bottom (skyline/floor)
    a = np.asarray(im.filter(ImageFilter.GaussianBlur(2.5)), np.float32)
    y = np.linspace(0, 1, H)[:, None, None]
    shade = 0.62 + 0.3 * np.clip(1 - np.abs(y - 0.55) / 0.45, 0, 1)          # darker top (headline) and bottom
    a = a * (shade - dark)
    navy = np.array([10, 24, 70], np.float32); a = a * 0.82 + navy * 0.18          # deep navy luxury tone
    yy, xx = np.mgrid[0:H, 0:W]; v = 1 - 0.35 * np.clip(np.hypot((xx - W / 2) / (W * 0.75), (yy - H / 2) / (H * 0.75)) ** 2, 0, 1)
    return np.clip(a * v[..., None], 0, 255)

def rmask(W, H, box, r=36, feather=3):
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).rounded_rectangle(box, r, fill=255)
    return np.asarray(m.filter(ImageFilter.GaussianBlur(feather)), np.float32) / 255

def swap_bg(out, s):
    W, H = out.size; ref = np.asarray(out.convert('RGB'), np.float32)
    bg = prep_bg('bg/' + s['bg'], W, H, s.get('bg_dark', 0.0))
    m = np.zeros((H, W), np.float32)
    R, G, B = ref[..., 0], ref[..., 1], ref[..., 2]; mx = ref.max(2)
    strict = s.get('strict', False)
    white = np.clip((mx - (185 if strict else 150)) / 45, 0, 1) * np.clip(1 - (mx - ref.min(2) - 120) / 60, 0, 1)
    gold = np.clip(((R - B) - (110 if strict else 55)) / 40, 0, 1) * np.clip((R - (170 if strict else 95)) / 40, 0, 1)
    score = np.maximum(white, gold)
    for x0, y0, x1, y1 in s.get('score', []):
        z = np.zeros((H, W), np.float32); z[y0:y1, x0:x1] = 1; z = cv2.GaussianBlur(z, (0, 0), 6)
        m = np.maximum(m, score * z)
    m = cv2.GaussianBlur(m, (0, 0), 1.2)
    dx = s.get('shift', 0); ref2 = ref.copy(); sm = m.copy()
    for x0, y0, x1, y1 in s.get('solid', []):
        rb = rmask(W, H, (x0, y0, x1, y1))
        if dx:
            sm[:, x0 + dx:x1 + dx] = np.maximum(sm[:, x0 + dx:x1 + dx], rb[:, x0:x1]); ref2[y0:y1, x0 + dx:x1 + dx] = ref[y0:y1, x0:x1]
        else: sm = np.maximum(sm, rb)
    ref = np.where(m[..., None] > 0.01, ref, ref2)
    shadow = cv2.GaussianBlur(sm, (0, 0), 14)
    bg = bg * (1 - 0.6 * shadow[..., None])                                         # soft drop shadow under design
    glow = cv2.GaussianBlur(m, (0, 0), 18)[..., None]
    bg = np.clip(bg + glow * np.array([255, 190, 80]) * 0.35, 0, 255)               # warm glow behind gold text
    res = bg * (1 - sm[..., None]) + ref * sm[..., None]
    return Image.fromarray(res.astype(np.uint8)).convert('RGBA')

# ---------------------------------------------------------------- per-slide plan
S = {}

def run(key):
    s = S[key]; pil = Image.open(f'ref/{key}.jpg').convert('RGB'); W, H = pil.size
    img = np.asarray(pil).copy(); before = img.copy()
    hole = np.zeros((H, W), np.uint8)
    pm = ref_person(img, s['person_region']) if s.get('person_region') else None
    if pm is not None: hole |= cv2.dilate(pm, np.ones((25, 25), np.uint8))
    for x0, y0, x1, y1 in s.get('ui', []): hole[max(0, y0):min(H, y1), max(0, x0):min(W, x1)] = 255
    for x0, y0, x1, y1 in s.get('protect', []): hole[y0:y1, x0:x1] = 0
    img = fill_rows(img, hole) if s.get('rows_fill') else fill(img, hole)
    fine = np.zeros((H, W), np.uint8)
    for x0, y0, x1, y1 in s.get('ui_fine', []): fine[y0:y1, x0:x1] = 255
    if fine.any(): img = fill_fine(img, fine)
    rm = np.zeros((H, W), np.uint8)
    for x0, y0, x1, y1 in s.get('ui_rows', []): rm[y0:y1, x0:x1] = 255
    if rm.any(): img = fill_rows(img, rm)
    dm = np.zeros((H, W), np.uint8)   # carousel dots: small circles at their exact centres
    for cx, cy, r in s.get('dots', []): cv2.circle(dm, (cx, cy), r, 255, -1)
    if dm.any(): img = cv2.inpaint(img, dm, 5, cv2.INPAINT_TELEA)
    icon = np.zeros((H, W), np.uint8)   # white TikTok icons over the card frame: only their own pixels
    for x0, y0, x1, y1 in s.get('ui_icons', []):
        sub = img[y0:y1, x0:x1].astype(int); icon[y0:y1, x0:x1] = ((sub.min(2) > (140 if s.get('icons_grey') else 185)) & (sub.max(2) - sub.min(2) < (45 if s.get('icons_grey') else 999))) * 255
    if icon.any(): img = fill_fine(img, cv2.dilate(icon, np.ones((7, 7), np.uint8)))
    for x0, y0, x1, y1 in s.get('clear', []):
        m = np.zeros((H, W), np.uint8); m[y0:y1, x0:x1] = 255; img = fill(img, m, k=2, blur=2)
    if s.get('headline'):
        hl = s['headline']; m = np.zeros((H, W), np.uint8); x0, y0, x1, y1 = hl['box']; m[y0:y1, x0:x1] = 255
        img = fill(img, m, k=2, blur=2)
    for (x0, y0, x1, y1), ax in s.get('mirror', []):   # rebuild a frame edge from the mirrored opposite edge of the original
        src = before[y0:y1, ax - x1:ax - x0][:, ::-1]
        a_ = np.ones((y1 - y0, x1 - x0, 1), np.float32); fe = 8
        a_[:, :fe, 0] = np.linspace(0, 1, fe); a_[:, -fe:, 0] = np.linspace(1, 0, fe)
        img[y0:y1, x0:x1] = (img[y0:y1, x0:x1] * (1 - a_) + src * a_).astype(np.uint8)
    for x0, y0, x1, y1, sx in s.get('rowfill', []):   # each row takes the clean colour just left of the box
        col = img[y0:y1, sx - 6:sx].astype(np.float32).mean(1)
        img[y0:y1, x0:x1] = cv2.GaussianBlur(col[:, None, :].repeat(x1 - x0, 1), (0, 0), 1.5).astype(np.uint8)
    for (x0, y0, x1, y1), (sx, sy), mode in s.get('copy', []):   # copy a clean patch of the original (flipv = mirrored top-bottom, tile = repeat)
        w, h = x1 - x0, y1 - y0
        if mode == 'flipv': patch = before[sy - h:sy, sx:sx + w][::-1]
        elif mode == 'tile':
            src = before[sy:sy + h, sx:sx + 120]; patch = np.concatenate([src] * (w // 120 + 1), 1)[:, :w]
        else: patch = before[sy:sy + h, sx:sx + w]
        a_ = np.ones((h, w, 1), np.float32); fe = 6
        a_[:, :fe, 0] *= np.linspace(0, 1, fe); a_[:, -fe:, 0] *= np.linspace(1, 0, fe)
        img[y0:y1, x0:x1] = (img[y0:y1, x0:x1] * (1 - a_) + patch * a_).astype(np.uint8)
    out = Image.fromarray(img).convert('RGBA')
    for e in s.get('text', []): out = edit_text(out, before, e)
    if s.get('headline'):
        hl = s['headline']; t = gold_text_line(hl['text'], hl['size'], hl['box'][2] - hl['box'][0] - 40)
        out.alpha_composite(t, (int((hl['box'][0] + hl['box'][2]) / 2 - t.width / 2), int((hl['box'][1] + hl['box'][3]) / 2 - t.height / 2)))
    for e in s.get('gold', []):   # gold value inside a navy panel: heavy sans, gold gradient, dark edge, soft shadow
        f = ImageFont.truetype(FD + 'Poppins-Black.ttf', e['size'])
        while f.getlength(e['text']) > e['max_w']: f = ImageFont.truetype(FD + 'Poppins-Black.ttf', f.size - 2)
        bb = f.getbbox(e['text']); pad = 30; w, h = bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2
        m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).text((pad - bb[0], pad - bb[1]), e['text'], font=f, fill=255)
        t = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0)); sh.putalpha(m.filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.8))); t.alpha_composite(sh, (0, 0))
        for k in range(6, 0, -1):
            lay = Image.new('RGBA', (w, h), (120, 70, 0, 255)); lay.putalpha(m); t.alpha_composite(lay, (0, 0) if k == 0 else (0, 0)); t.alpha_composite(lay)
        edge = Image.new('RGBA', (w, h), (90, 50, 0, 255)); edge.putalpha(m.filter(ImageFilter.MaxFilter(5)))
        t2 = Image.new('RGBA', (w, h + 6), (0, 0, 0, 0)); t2.alpha_composite(sh, (3, 8))
        for k in range(5, 0, -1): t2.alpha_composite(edge, (0, k))
        face = poster.vgrad((w, h), [(0, (255, 246, 190)), (0.45, (255, 214, 80)), (0.55, (240, 170, 30)), (1, (255, 214, 100))]); face.putalpha(m)
        t2.alpha_composite(edge); t2.alpha_composite(face)
        out.alpha_composite(t2, (int(e['cx'] - w / 2), int(e['cy'] - h / 2)))
    if s.get('badge'): badge(out, *s['badge'])
    if s.get('bg'):   # replace the photo background, keep the design (headline, cards, panels, badge)
        out = swap_bg(out, s)
    pre_me = out.copy()
    if pm is not None and s.get('me'):
        me = s['me']; out = place_me(out, me['n'], me.get('flip', False), pm, me.get('scale', 1.0), me.get('dx', 0), me.get('bottom'), me.get('circle', False), me.get('border', 10), me.get('height'), me.get('right'))
    for x0, y0, x1, y1 in s.get('front', []):   # panels that stay in front of the person
        out.paste(pre_me.crop((x0, y0, x1, y1)), (x0, y0))
    out.convert('RGB').save(f'out/{key}.jpg', quality=94)
    return out

if __name__ == '__main__':
    os.chdir(sys.argv[1]); S.update(json.load(open('slides.json'))); os.makedirs('out', exist_ok=True)
    for k in (sys.argv[2:] or sorted(S)): run(k); print('ok', k)
