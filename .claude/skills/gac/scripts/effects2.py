"""More GAC video effects (registered into effects.FX). Each fx(fr, e, u, d, W, H) -> RGBA frame.

Golden rule for every effect: the FACE stays clear and nothing readable enters the TikTok UI zones
(top 220 px, below y 1500, right of x 960 between y 700-1500). Overlays sit in the band above the head
or below the chin; full-frame effects (zoom, dolly, cutout...) keep the face itself untouched.

e['_face'] = (top_of_hair_y, chin_y) or None, filled by effects.apply.
Person mask (U^2-Net human seg) is computed on demand for effects that need "behind / in front of you".
"""
import os, math, random, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import theme, mewah

def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def eio(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def inout(u, d, i=0.35, o=0.3): return ease(u / i) * (1 - ease((u - d + o) / o))
def acc(): return tuple(theme.A[:3])
def face(e, H): return e.get('_face') or (H * 0.22, H * 0.48)
def band_top(e, H): return max(240, face(e, H)[0] - 30)          # free band above the head ends here
def band_low(e, H): return min(1470, face(e, H)[1] + 60)          # free band below the chin starts here

_S = {}
def person_mask(fr):
    """float HxW mask (1 = person)."""
    if 'sess' not in _S:
        import onnxruntime as ort
        m = os.path.expanduser('~/.cache/gac/models/u2net_human_seg.onnx')
        if not os.path.exists(m):
            os.makedirs(os.path.dirname(m), exist_ok=True)
            subprocess.run(['curl', '-fsSL', '-o', m, 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx'], check=True)
        _S['sess'] = ort.InferenceSession(m, providers=['CPUExecutionProvider'])
    s = _S['sess']; a = np.asarray(fr.convert('RGB'))
    x = ((cv2.resize(a, (320, 320), interpolation=cv2.INTER_AREA) / 255.0 - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]).transpose(2, 0, 1)[None].astype(np.float32)
    o = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]; o = (o - o.min()) / (o.max() - o.min() + 1e-9)
    m = cv2.resize(o, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_CUBIC)
    prev = _S.get('prev')
    if prev is not None and prev.shape == m.shape: m = 0.65 * m + 0.35 * prev
    _S['prev'] = m
    return np.clip((m - 0.15) / 0.7, 0, 1)

def cut_person(fr, m):
    p = fr.copy(); p.putalpha(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1))); return p

def behind(fr, layer, m):
    """Composite `layer` over the frame but behind the person."""
    a = np.asarray(layer.getchannel('A'), np.float32) * (1 - m)
    layer = layer.copy(); layer.putalpha(Image.fromarray(a.clip(0, 255).astype(np.uint8))); fr = fr.copy(); fr.alpha_composite(layer); return fr

def inpaint_bg(fr, m):
    """Background with the person roughly filled (for dolly / portal / zoom-behind)."""
    a = np.asarray(fr.convert('RGB')); h, w = a.shape[:2]; k = 6
    sm = cv2.resize(a, (w // k, h // k), interpolation=cv2.INTER_AREA)
    mm = (cv2.resize(m, (w // k, h // k)) > 0.2).astype(np.uint8) * 255; mm = cv2.dilate(mm, np.ones((5, 5), np.uint8))
    f = cv2.inpaint(sm, mm, 7, cv2.INPAINT_TELEA); f = cv2.GaussianBlur(cv2.resize(f, (w, h), interpolation=cv2.INTER_CUBIC), (0, 0), 8)
    return Image.fromarray(f).convert('RGBA')

def scale_about(img, z, cx, cy, W, H):
    """Zoom image by z about (cx, cy), output W x H."""
    x0, y0 = cx - cx / z, cy - cy / z
    return img.crop((int(x0), int(y0), int(x0 + W / z), int(y0 + H / z))).resize((W, H), Image.BICUBIC)

def put(fr, im, cx, cy, a=1.0, sc=1.0):
    if sc != 1.0: im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BICUBIC)
    if a < 0.999: im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * a)))
    fr.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def pill(text, size=46, fill=None, ink=(255, 255, 255), pad=34):
    f = mewah.sans(size, 'ExtraBold'); w = int(f.getlength(text) + pad * 2); h = int(size * 1.9)
    im = Image.new('RGBA', (w + 30, h + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((15, 21, w + 15, h + 21), h // 2, fill=(0, 0, 0, 90)); im = im.filter(ImageFilter.GaussianBlur(6)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((15, 15, w + 15, h + 15), h // 2, fill=(fill or acc()) + (255,)); d.text((15 + w / 2, 15 + h / 2), text, font=f, fill=ink, anchor='mm')
    return im

def load_img(path, base=''):
    if not path: return None
    p = path if os.path.isabs(path) else os.path.join(base, path)
    return ImageOps.exif_transpose(Image.open(p)).convert('RGB') if os.path.exists(p) else None

def cover_fit(im, w, h):
    k = max(w / im.width, h / im.height); im = im.resize((int(im.width * k + 1), int(im.height * k + 1)), Image.LANCZOS)
    x0, y0 = (im.width - w) // 2, (im.height - h) // 2; return im.crop((x0, y0, x0 + w, y0 + h))

# ---------------------------------------------------------------- 1 orbit
def fx_orbit(fr, e, u, d, W, H):
    """Words / icons orbit around you: behind you on the far side, below the chin on the near side."""
    m = person_mask(fr); top, chin = face(e, H); cy = (top + chin) / 2 + 40; rx, ry = 430, 230
    items = e.get('items', ['Emas', 'Simpan', 'GAP']); n = len(items); a0 = u * e.get('speed', 1.4); al = inout(u, d)
    back = Image.new('RGBA', fr.size, (0, 0, 0, 0)); front = Image.new('RGBA', fr.size, (0, 0, 0, 0))
    for i, it in enumerate(items):
        ang = a0 + i * 2 * math.pi / n; x = W / 2 + rx * math.cos(ang); y = cy + ry * math.sin(ang)
        depth = math.sin(ang)                                   # > 0: in front (lower part of the ellipse)
        sc = 0.8 + 0.3 * (depth + 1) / 2; p = pill(it, 58)
        if depth > 0 and y < chin + 40: continue               # the near side never crosses the face
        put(front if depth > 0 else back, p, min(x, 900), y, al, sc)
    fr = behind(fr, back, m); fr.alpha_composite(front); return fr

# ---------------------------------------------------------------- 2 chat takeover
def fx_chat(fr, e, u, d, W, H):
    """Chat bubbles pop in one after another and stack up below the chin."""
    msgs = e.get('messages', [['Macam mana nak mula simpan emas?', 'l'], ['Boleh mula RM100 je!', 'r']]); gap = e.get('gap', 0.9)
    f = mewah.sans(40, 'SemiBold'); y = band_low(e, H) + 20; al = 1 - ease((u - d + 0.3) / 0.3)
    shown = [mm for k, mm in enumerate(msgs) if u >= 0.2 + k * gap][-4:]
    for k, (txt, side) in enumerate(shown):
        idx = msgs.index([txt, side]) if [txt, side] in msgs else k; age = u - 0.2 - idx * gap
        words, lines, ln = txt.split(), [], ''
        for w in words:
            if f.getlength((ln + ' ' + w).strip()) > 560: lines.append(ln); ln = w
            else: ln = (ln + ' ' + w).strip()
        lines.append(ln); bw = int(max(f.getlength(l) for l in lines) + 60); bh = 56 * len(lines) + 34
        im = Image.new('RGBA', (bw + 20, bh + 24), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
        col = (255, 255, 255) if side == 'l' else (220, 248, 198)
        dd.rounded_rectangle((10, 10, bw + 10, bh + 10), 30, fill=col + (250,))
        for i, l in enumerate(lines): dd.text((40, 10 + 17 + 56 * i + 28), l, font=f, fill=(30, 30, 30), anchor='lm')
        x = 140 + bw / 2 if side == 'l' else 940 - bw / 2
        put(fr, im, x, y + bh / 2, al * min(1, age / 0.12), 0.85 + 0.15 * ease(age / 0.2)); y += bh + 18
        if y > 1470: break
    return fr

# ---------------------------------------------------------------- 3 frame escape / 17 frame break
def _framed(fr, e, u, d, W, H, shards=False):
    m = person_mask(fr); p = eio(u / 0.5) * (1 - eio((u - d + 0.4) / 0.4)); sc = 1 - 0.28 * p
    bg = fr.convert('RGB').resize((W // 10, H // 10)).filter(ImageFilter.GaussianBlur(2)).resize((W, H)).convert('RGBA')
    bg.alpha_composite(Image.new('RGBA', (W, H), (10, 14, 30, int(150 * p))))
    vw, vh = int(W * sc), int(H * sc * 0.82); cx, cy = W / 2, H * 0.52
    box = (int(cx - vw / 2), int(cy - vh / 2), int(cx + vw / 2), int(cy + vh / 2))
    inner = scale_about(fr, 1 / sc, cx, cy, W, H).crop(box); bg.paste(inner, box[:2])
    dd = ImageDraw.Draw(bg); dd.rectangle(box, outline=(255, 255, 255, 255), width=int(18 * p) + 1)
    out = Image.alpha_composite(bg, Image.new('RGBA', (W, H)))
    person = cut_person(scale_about(fr, 1 / (0.92 + 0.08 * (1 - p)), cx, cy, W, H), cv2.resize(m, (W, H)))
    if p > 0.02:   # the person breaks out of the frame (in front of the border, full size)
        out.alpha_composite(person)
    else: out = fr
    if shards and 0 < u < 1.2:
        rnd = random.Random(3); dd = ImageDraw.Draw(out)
        for i in range(26):
            ang = rnd.uniform(0, 2 * math.pi); r = 80 + 900 * ease(u / 1.0); x = cx + math.cos(ang) * r * rnd.uniform(0.4, 1); y = box[1] + math.sin(ang) * r * 0.4
            s = rnd.uniform(14, 34); a = int(220 * (1 - u / 1.2))
            ft, fc = face(e, H)
            if ft - 40 < y < fc + 40 and 250 < x < 830: continue   # never over the face
            dd.polygon([(x, y - s), (x + s * 0.7, y + s * 0.5), (x - s * 0.6, y + s * 0.3)], fill=(235, 245, 255, a), outline=(255, 255, 255, a))
    return out
def fx_frame_escape(fr, e, u, d, W, H): return _framed(fr, e, u, d, W, H, False)
def fx_frame_break(fr, e, u, d, W, H): return _framed(fr, e, u, d, W, H, True)

# ---------------------------------------------------------------- 4 snap zoom
def fx_snap(fr, e, u, d, W, H):
    """Fast punch-in on the face (3 frames) with a motion-blur flash, hold, snap back at the end."""
    top, chin = face(e, H); fy = (top + chin) / 2; z1 = e.get('to', 1.3)
    k = ease(u / 0.1) * (1 - ease((u - d + 0.1) / 0.1)); z = 1 + (z1 - 1) * k
    img = scale_about(fr, z, W / 2, fy, W, H)
    if 0 < u < 0.1 or d - 0.1 < u < d:
        img = Image.blend(img.convert('RGB'), img.convert('RGB').filter(ImageFilter.GaussianBlur(6)), 0.6).convert('RGBA')
    return img

# ---------------------------------------------------------------- 5 checklist pop
def fx_checklist_pop(fr, e, u, d, W, H):
    """Items pop in (bounce + sparkle) as gold-ticked pills below the chin, one per spoken time."""
    items = e.get('items', []); ats = e.get('_ticks') or [0.3 + k * 0.7 for k in range(len(items))]
    y = band_low(e, H) + 40; al = 1 - ease((u - d + 0.3) / 0.3); f = mewah.sans(44, 'ExtraBold')
    for k, it in enumerate(items):
        age = u - ats[k]
        if age < 0: continue
        w = int(f.getlength(it) + 150); h = 96; im = Image.new('RGBA', (w + 30, h + 30), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
        dd.rounded_rectangle((15, 15, w + 15, h + 15), 30, fill=(255, 255, 255, 245), outline=acc() + (255,), width=4)
        mewah.tick(dd, 15 + 58, 15 + h / 2, 26, acc()); dd.text((15 + 104, 15 + h / 2), it, font=f, fill=(25, 25, 25), anchor='lm')
        sc = mewah.pop(age / 0.3); put(fr, im, W / 2 - 20, y, al, sc)
        if age < 0.35:
            sp = Image.new('RGBA', fr.size, (0, 0, 0, 0)); mewah.sparkle(ImageDraw.Draw(sp), W / 2 + w / 2 - 10, y - 40, 14, int(255 * (1 - age / 0.35))); fr.alpha_composite(sp)
        y += h + 20
    return fr

# ---------------------------------------------------------------- 6 headline storm
def fx_headlines(fr, e, u, d, W, H):
    """A storm of headline cards flies in from the edges and settles above the head and below the chin."""
    heads = e.get('headlines', ['Harga emas naik lagi', 'Simpan emas jadi trend', 'Inflasi makin tinggi']); al = 1 - ease((u - d + 0.3) / 0.3)
    top_band = (250, band_top(e, H) - 40); low_band = (band_low(e, H) + 40, 1460); rnd = random.Random(5); f = mewah.serif(46)
    for k, hd in enumerate(heads):
        st = 0.15 * k; age = u - st
        if age < 0: continue
        band = top_band if k % 2 == 0 else low_band
        if band[1] - band[0] < 80: band = low_band
        ty = band[0] + (band[1] - band[0]) * ((k // 2) % 3 + 0.5) / 3; tx = W / 2 + rnd.uniform(-90, 60)
        sx = -700 if k % 2 == 0 else W + 700; p = ease(age / 0.35); x = sx + (tx - sx) * p
        w = int(f.getlength(hd) + 70); h = 90; im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
        dd.rectangle((0, 0, w - 1, h - 1), fill=(250, 248, 240, 245)); dd.rectangle((0, 0, 12, h), fill=(200, 30, 40))
        dd.text((38, h / 2), hd, font=f, fill=(20, 20, 20), anchor='lm')
        im = im.rotate(rnd.uniform(-5, 5), resample=Image.BICUBIC, expand=True); put(fr, im, min(x, 960 - im.width / 2), ty, al)
    return fr

# ---------------------------------------------------------------- 7 zoom portal
def fx_portal(fr, e, u, d, W, H):
    """A round portal opens BEHIND you and zooms into an image (or a zoomed view of the scene)."""
    m = person_mask(fr); top, chin = face(e, H); cx, cy = W / 2, (top + chin) / 2
    p = ease(u / 0.6) * (1 - ease((u - d + 0.4) / 0.4)); R = 60 + 1400 * p
    img = load_img(e.get('image'), e.get('_base', ''))
    src = cover_fit(img, W, H).convert('RGBA') if img else inpaint_bg(fr, m)
    src = scale_about(src, 1.6 - 0.6 * eio(u / d), cx, cy, W, H)
    mask = Image.new('L', (W, H), 0); ImageDraw.Draw(mask).ellipse((cx - R, cy - R, cx + R, cy + R), fill=255)
    ring = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(ring).ellipse((cx - R, cy - R, cx + R, cy + R), outline=acc() + (230,), width=10)
    ring = ring.filter(ImageFilter.GaussianBlur(3)); src.putalpha(mask.filter(ImageFilter.GaussianBlur(4))); src.alpha_composite(ring)
    return behind(fr, src, m)

# ---------------------------------------------------------------- 9 studio reveal
def fx_studio(fr, e, u, d, W, H):
    """Background turns into a dark studio; spotlights switch on one by one and sweep; you stay as you are."""
    m = person_mask(fr); p = ease(u / 0.5) * (1 - ease((u - d + 0.4) / 0.4))
    st = Image.fromarray(mewah.vgrad(W, H, [(0, (14, 16, 26)), (0.7, (26, 22, 40)), (1, (8, 8, 12))]).astype(np.uint8)).convert('RGBA')
    beams = Image.new('L', (W, H), 0); dd = ImageDraw.Draw(beams)
    for k, bx in enumerate((160, 540, 920)):
        if u < 0.3 + k * 0.35: continue
        sw = math.sin(u * 1.4 + k) * 120
        dd.polygon([(bx, -10), (bx - 60, -10), (W / 2 + sw - 260, H), (W / 2 + sw + 260, H)], fill=110)
    beams = beams.filter(ImageFilter.GaussianBlur(40)); light = Image.new('RGBA', (W, H), (255, 236, 190, 255)); light.putalpha(beams); st.alpha_composite(light)
    fl = Image.new('L', (W, H), 0); ImageDraw.Draw(fl).ellipse((W * 0.1, H * 0.78, W * 0.9, H * 1.02), fill=140)
    gl = Image.new('RGBA', (W, H), (255, 220, 150, 255)); gl.putalpha(fl.filter(ImageFilter.GaussianBlur(60))); st.alpha_composite(gl)
    bg = Image.blend(fr.convert('RGB'), st.convert('RGB'), p).convert('RGBA')
    bg.alpha_composite(cut_person(fr, m)); return bg

# ---------------------------------------------------------------- 10 b-roll overlay
def fx_broll(fr, e, u, d, W, H):
    """Your photo / clip in a rounded card above the head (or below the chin), slow Ken Burns."""
    img = load_img(e.get('image'), e.get('_base', ''))
    if img is None: return fr
    p = ease(u / 0.35) * (1 - ease((u - d + 0.3) / 0.3)); pos = e.get('pos', 'top')
    if pos == 'top': y0, y1 = 250, band_top(e, H) - 20
    else: y0, y1 = band_low(e, H) + 20, 1470
    h = max(160, int(y1 - y0)); w = min(820, int(h * e.get('aspect', 1.6)))
    z = 1.0 + 0.08 * u / max(d, 0.1)
    mk = Image.new('L', (w, h), 0); ImageDraw.Draw(mk).rounded_rectangle((0, 0, w - 1, h - 1), 28, fill=255)
    k = cover_fit(img, int(w * z), int(h * z)).crop((0, 0, w, h)).convert('RGBA'); k.putalpha(mk)
    card = Image.new('RGBA', (w + 16, h + 16), (0, 0, 0, 0)); ImageDraw.Draw(card).rounded_rectangle((0, 0, w + 15, h + 15), 34, fill=(255, 255, 255, 255)); card.alpha_composite(k, (8, 8))
    put(fr, card, W / 2 - 30, (y0 + y1) / 2 + 40 * (1 - p), p); return fr

# ---------------------------------------------------------------- 11 paper cutout
def fx_paper(fr, e, u, d, W, H):
    """You become a paper cut-out (thick white edge, drop shadow) on a kraft-paper backdrop."""
    m = person_mask(fr); p = ease(u / 0.35) * (1 - ease((u - d + 0.3) / 0.3))
    rnd = np.random.default_rng(1); paper = np.full((H, W, 3), (214, 190, 150), np.float32)
    paper += cv2.GaussianBlur(rnd.normal(0, 14, (H, W)).astype(np.float32), (0, 0), 2)[..., None]
    bg = Image.blend(fr.convert('RGB'), Image.fromarray(paper.clip(0, 255).astype(np.uint8)), p).convert('RGBA')
    mm = (m > 0.5).astype(np.uint8) * 255; edge = cv2.dilate(mm, np.ones((31, 31), np.uint8))
    sh = Image.new('RGBA', (W, H), (40, 25, 10, 0)); sh.putalpha(Image.fromarray(edge).filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(v * 0.55 * p)))
    bg.alpha_composite(sh, (14, 20))
    wh = Image.new('RGBA', (W, H), (255, 255, 255, 0)); wh.putalpha(Image.fromarray(edge).point(lambda v: int(v * p)))
    bg.alpha_composite(wh); bg.alpha_composite(cut_person(fr, m)); return bg

# ---------------------------------------------------------------- 12 dolly zoom
def fx_dolly(fr, e, u, d, W, H):
    """Vertigo: you stay the same size while the background rushes away behind you."""
    m = person_mask(fr); top, chin = face(e, H); cx, cy = W / 2, (top + chin) / 2
    z = 1.0 + e.get('amount', 0.35) * eio(u / d) * (1 - eio((u - d + 0.25) / 0.25))
    bg = scale_about(inpaint_bg(fr, m), 1 / max(0.6, 1 - (z - 1)) if e.get('out', True) else z, cx, cy, W, H)
    bg = scale_about(bg, z, cx, cy, W, H) if not e.get('out', True) else bg
    bg.alpha_composite(cut_person(fr, m)); return bg

# ---------------------------------------------------------------- 13 magazine cover
def fx_magazine(fr, e, u, d, W, H):
    """Magazine cover: big masthead BEHIND your head, cover lines at the sides and bottom, barcode."""
    m = person_mask(fr); p = ease(u / 0.4) * (1 - ease((u - d + 0.3) / 0.3)); top, chin = face(e, H)
    mast = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(mast); title = e.get('title', 'EMAS')
    f = mewah.serif(260)
    while f.getlength(title) > W - 120: f = mewah.serif(f.size - 10)
    dd.text((W / 2, max(250, top - 60)), title, font=f, fill=acc() + (int(255 * p),), anchor='ms')
    fr = behind(fr, mast, m)
    dd = ImageDraw.Draw(fr); fs = mewah.sans(40, 'ExtraBold'); fsm = mewah.sans(30, 'SemiBold'); a = int(255 * p)
    dd.text((70, 250), e.get('issue', 'EDISI KHAS'), font=fsm, fill=(255, 255, 255, a))
    for k, ln in enumerate(e.get('lines', ['Simpan emas', 'mula RM100'])[:3]):
        y = band_low(e, H) + 30 + k * 76; t_ = ln.upper(); tw = fs.getlength(t_)
        dd.rounded_rectangle((66, y - 8, 94 + tw, y + 56), 10, fill=(12, 22, 58, int(210 * p)))
        dd.text((80, y), t_, font=fs, fill=((255, 255, 255) if k % 2 else acc()) + (a,))
    bx, by = 760, 1370
    if p > 0.05:
        dd.rectangle((bx, by, bx + 170, by + 100), fill=(255, 255, 255, a)); rnd = random.Random(2); x = bx + 10
        while x < bx + 160: wdt = rnd.choice((2, 3, 5)); dd.rectangle((x, by + 10, x + wdt - 1, by + 80), fill=(0, 0, 0, a)); x += wdt + rnd.choice((2, 3))
    return fr

# ---------------------------------------------------------------- 14 liquid glass
def fx_liquid(fr, e, u, d, W, H):
    """Liquid glass pill below the chin: refracts the video behind it (wobble), bright rim, text."""
    p = ease(u / 0.4) * (1 - ease((u - d + 0.3) / 0.3)); txt = e.get('text', ''); f = mewah.sans(e.get('size', 62), 'ExtraBold')
    while f.getlength(txt) > 700: f = mewah.sans(f.size - 4, 'ExtraBold')
    w, h = int(min(820, f.getlength(txt) + 140)), 170; cx, cy = W / 2 - 20, band_low(e, H) + 120 + 40 * (1 - p)
    x0, y0 = int(cx - w / 2), int(cy - h / 2); reg = np.asarray(fr.convert('RGB').crop((x0, y0, x0 + w, y0 + h))).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); ph = u * 3
    mx = (xx + 10 * np.sin(yy / 18 + ph) + (xx - w / 2) * 0.08).clip(0, w - 1); my = (yy + 8 * np.cos(xx / 22 + ph) + (yy - h / 2) * 0.12).clip(0, h - 1)
    ref = cv2.remap(reg, mx, my, cv2.INTER_LINEAR); ref = cv2.GaussianBlur(ref, (0, 0), 3) * 0.8 + 255 * 0.2
    gl = Image.fromarray(ref.clip(0, 255).astype(np.uint8)).convert('RGBA'); mk = Image.new('L', (w, h), 0); ImageDraw.Draw(mk).rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=int(255 * p))
    gl.putalpha(mk); dd = ImageDraw.Draw(gl)
    dd.rounded_rectangle((2, 2, w - 3, h - 3), h // 2, outline=(255, 255, 255, int(200 * p)), width=3)
    dd.rounded_rectangle((h * 0.4, 12, w - h * 0.4, 30), 9, fill=(255, 255, 255, int(110 * p)))
    dd.text((w / 2, h / 2 + 4), txt, font=f, fill=(20, 22, 30, int(255 * p)), anchor='mm')
    sh = Image.new('RGBA', (w + 80, h + 80), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((40, 54, 40 + w, 54 + h), h // 2, fill=(0, 0, 0, int(70 * p)))
    fr.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)), (x0 - 40, y0 - 40)); fr.alpha_composite(gl, (x0, y0)); return fr

# ---------------------------------------------------------------- 15 zoom through cut
def fx_zoomthrough(fr, e, u, d, W, H):
    """Transition across a cut: rush INTO the frame before the cut, rush OUT of the next shot after it."""
    top, chin = face(e, H); cy = (top + chin) / 2; mid = d / 2
    if u < mid: z = 1 + 2.2 * (u / mid) ** 2
    else: z = 1 + 2.2 * (1 - (u - mid) / mid) ** 2
    img = scale_about(fr, z, W / 2, cy, W, H)
    if z > 1.3:
        a = np.asarray(img.convert('RGB')).astype(np.float32); acc_ = a.copy()
        for k in (1.03, 1.06, 1.09): acc_ += np.asarray(scale_about(img, k, W / 2, cy, W, H).convert('RGB')).astype(np.float32)
        img = Image.fromarray((acc_ / 4).astype(np.uint8)).convert('RGBA')
    return img

# ---------------------------------------------------------------- 16 green screen
def fx_greenscreen(fr, e, u, d, W, H):
    """Swap the background for a photo (or a colour) for this stretch; you stay in front."""
    m = person_mask(fr); img = load_img(e.get('image'), e.get('_base', ''))
    bg = cover_fit(img, W, H).filter(ImageFilter.GaussianBlur(e.get('blur', 3))).convert('RGBA') if img else Image.new('RGBA', (W, H), tuple(e.get('color', (12, 22, 58))) + (255,))
    p = min(1, u / 0.15, max(0, (d - u) / 0.15)); out = Image.blend(fr.convert('RGB'), bg.convert('RGB'), p).convert('RGBA')
    out.alpha_composite(cut_person(fr, m)); return out

# ---------------------------------------------------------------- 8 growth curve
def fx_growth(fr, e, u, d, W, H):
    """Rising curve that draws itself below the chin, glowing gold line, filled area, arrow head, counter."""
    vals = e.get('values', [1, 1.4, 1.3, 2, 2.6, 3.4]); p = ease((u - 0.2) / max(0.6, d - 0.8)); al = 1 - ease((u - d + 0.3) / 0.3)
    x0, x1 = 120, 900; y1 = 1450; y0 = max(band_low(e, H) + 40, y1 - 330); lo, hi = min(vals), max(vals)
    pts = [(x0 + (x1 - x0) * k / (len(vals) - 1), y1 - (y1 - y0) * (v - lo) / max(1e-6, hi - lo)) for k, v in enumerate(vals)]
    n = p * (len(pts) - 1); k = int(n); dr = pts[:k + 1]
    if k < len(pts) - 1: f_ = n - k; dr.append((pts[k][0] + (pts[k + 1][0] - pts[k][0]) * f_, pts[k][1] + (pts[k + 1][1] - pts[k][1]) * f_))
    lay = Image.new('RGBA', fr.size, (0, 0, 0, 0)); dd = ImageDraw.Draw(lay); a = int(255 * al)
    dd.rounded_rectangle((x0 - 40, y0 - 70, x1 + 40, y1 + 30), 30, fill=(12, 22, 58, int(200 * al)), outline=acc() + (a,), width=3)
    if len(dr) > 1:
        dd.polygon(dr + [(dr[-1][0], y1), (x0, y1)], fill=acc() + (int(70 * al),))
        g = Image.new('RGBA', fr.size, (0, 0, 0, 0)); ImageDraw.Draw(g).line(dr, fill=acc() + (a,), width=26, joint='curve'); lay.alpha_composite(g.filter(ImageFilter.GaussianBlur(10)))
        dd.line(dr, fill=(255, 236, 170, a), width=10, joint='curve')
        hx, hy = dr[-1]; dd.ellipse((hx - 14, hy - 14, hx + 14, hy + 14), fill=(255, 255, 255, a))
    if e.get('label'): dd.text((x0, y0 - 35), e['label'], font=mewah.sans(40, 'ExtraBold'), fill=(255, 255, 255, a), anchor='lm')
    if e.get('source'): dd.text((x1, y1 + 5), e['source'], font=mewah.sans(22, 'SemiBold'), fill=(210, 210, 220, a), anchor='rb')
    fr.alpha_composite(lay); return fr

FX2 = dict(orbit=fx_orbit, chat=fx_chat, frame_escape=fx_frame_escape, frame_break=fx_frame_break, snapzoom=fx_snap,
           checklist_pop=fx_checklist_pop, headlines=fx_headlines, portal=fx_portal, growth=fx_growth, studio=fx_studio,
           broll=fx_broll, paper=fx_paper, dolly=fx_dolly, magazine=fx_magazine, liquid=fx_liquid, zoomthrough=fx_zoomthrough,
           greenscreen=fx_greenscreen)
SFX2 = dict(orbit='whoosh', chat='pop', frame_escape='swoosh', frame_break='impact', snapzoom='hit', checklist_pop='pop',
            headlines='whoosh', portal='swell', growth='riser', studio='swell', broll='whoosh', paper='pop', dolly='swell',
            magazine='click', liquid='whoosh', zoomthrough='whoosh', greenscreen='swoosh')
PANEL2 = ('chat', 'checklist_pop', 'headlines', 'growth', 'liquid', 'broll', 'magazine')   # captions hide while these show
