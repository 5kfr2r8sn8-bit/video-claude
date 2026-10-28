"""Iman-Gadzhi-style "document" panel: one long off-white page that grows while the
speaker talks. Each block appears at its own (original-video) time, then the page
scrolls so the newest block sits near the bottom of the visible window.

Block types (all take "at": original time in seconds, optional "gap": px before it):
  {"text": "Normal **bold** ==green highlight== __red underline__", "size": 40, "box": true}
  {"num": 2, "text": "optional heading next to the big outline number"}
  {"icon": "emas_bar", "h": 220}          PNG from the icon folder (white bg auto-removed)
  {"arrow": "down" | "down-left" | "down-right", "h": 150}
  {"image": "/path/screenshot.png", "w": 640, "circle": [0.7, 0.4, 0.12]}
  {"space": 60}
"""
import os, re, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BG = (250, 249, 252)
INK = (30, 30, 36)
HL = (186, 236, 160)
RED = (226, 40, 40)
# Marker colours. "gold" (default) suits gold dealers: soft gold highlighter, deep gold
# underline/box. "classic" is Iman's original green highlighter + red pen.
PALETTES = dict(gold=dict(hl=(246, 186, 62), mark=(196, 124, 18)), classic=dict(hl=HL, mark=RED))
PAL = PALETTES['gold']
NUM_FILL, NUM_EDGE = (236, 236, 242), (150, 150, 160)
# "paper": dark ink on the off-white page (landscape side panel).
# "clear": no page at all, white text with a soft shadow straight over the video (default for portrait).
THEMES = dict(paper=dict(ink=INK, hl_ink=INK, num=(NUM_FILL, NUM_EDGE), arrow=(40, 50, 90), shadow=False),
              clear=dict(ink=(255, 255, 255), hl_ink=(28, 20, 4), num=((255, 255, 255, 70), (255, 255, 255)), arrow=(255, 255, 255), shadow=True))
TH = THEMES['paper']

MONT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'fonts', 'Montserrat.ttf')
# House font: Montserrat everywhere (captions Bold, display Black) - user's pick 2026-10-13. Entries: (path, index[, variable-font weight])
REG = [(MONT, 0, 'Medium'), ('/System/Library/Fonts/Avenir Next.ttc', 7), ('/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf', 0),
       ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 0)]
BOLD = [(MONT, 0, 'Bold'), ('/System/Library/Fonts/Avenir Next.ttc', 2), ('/usr/share/fonts/truetype/google-fonts/Poppins-SemiBold.ttf', 0),
        ('/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf', 0), ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 0)]
HEAVY = [(MONT, 0, 'Black'), ('/System/Library/Fonts/Avenir Next.ttc', 8), ('/usr/share/fonts/truetype/google-fonts/Poppins-ExtraBold.ttf', 0)] + BOLD
FONTSETS = dict(paper=(REG, BOLD), clear=(BOLD, HEAVY))   # over video, thin type disappears: go one weight up
_fc = {}
def _font(spec, sz):
    k = (id(spec), sz)
    if k not in _fc:
        e = next(e for e in spec if os.path.exists(e[0])); f = ImageFont.truetype(e[0], sz, index=e[1])
        if len(e) > 2: f.set_variation_by_name(e[2])
        _fc[k] = f
    return _fc[k]

def layout_for(W, H, theme='paper'):
    """Panel rectangle + content box. Portrait keeps text inside the TikTok/Reels safe zone
    (clear of the right-hand buttons and the bottom caption/username area)."""
    if theme == 'clear':  # floats over the full-frame video, chest area / right side
        if H > W: return dict(panel=(0, 940, W, 1580), x0=60, x1=920, view=(990, 1500), anchor=1460, size=58)
        return dict(panel=(W // 2, 60, W, H - 60), x0=W // 2 + 40, x1=W - 70, view=(110, H - 70), anchor=H - 170, size=40)
    if H > W:
        return dict(panel=(0, 860, W, H), x0=60, x1=920, view=(925, 1490), anchor=1440, size=50)
    return dict(panel=(W // 2, 0, W, H), x0=W // 2 + 50, x1=W - 50, view=(70, H - 40), anchor=H - 150, size=36)

# ------------------------------------------------------------------ helpers
def _runs(text):
    """'a **b** ==c== __d__' -> [(word, bold, hl, ul), ...]"""
    out = []; bold = hl = ul = False
    for tok in re.split(r'(\*\*|==|__)', text):
        if tok == '**': bold = not bold
        elif tok == '==': hl = not hl
        elif tok == '__': ul = not ul
        elif tok:
            for w in re.split(r'(\s+)', tok):
                if w and not w.isspace(): out.append((w, bold, hl, ul))
    return out

def _rough_line(d, x0, y0, x1, y1, col, w, seed):
    r = random.Random(seed); n = max(3, int(abs(x1 - x0) / 40)); pts = []
    for i in range(n + 1):
        f = i / n; pts.append((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f + r.uniform(-2.2, 2.2)))
    d.line(pts, fill=col, width=w, joint='curve')

def _brush(d, x0, y0, x1, y1, col, seed):
    """Highlighter stroke with ragged ends, like a marker swipe."""
    r = random.Random(seed); top, bot = [], []
    n = max(4, int((x1 - x0) / 30))
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        top.append((x, y0 + r.uniform(-3, 4))); bot.append((x, y1 + r.uniform(-4, 3)))
    left = [(x0 - r.uniform(4, 12), (y0 + y1) / 2)]; right = [(x1 + r.uniform(4, 12), (y0 + y1) / 2)]
    d.polygon(left + top + right + bot[::-1], fill=col)

def find_icon(icon_dir, name):
    """Path of an icon by name; accepts any image extension and .PNG/.png case differences."""
    if os.path.isabs(name) and os.path.exists(name): return name
    base = os.path.join(icon_dir or '', name)
    if os.path.splitext(name)[1] and os.path.exists(base): return base
    stem = os.path.splitext(name)[0] if os.path.splitext(name)[1].lower() in ('.png', '.jpg', '.jpeg', '.webp') else name
    folder = os.path.dirname(os.path.join(icon_dir or '', stem)) or '.'
    want = os.path.basename(stem).lower()
    if os.path.isdir(folder):
        for f in sorted(os.listdir(folder)):
            st, ext = os.path.splitext(f)
            if st.lower() == want and ext.lower() in ('.png', '.webp', '.jpg', '.jpeg'): return os.path.join(folder, f)
    own = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'ikon')
    if icon_dir != own: return find_icon(own, os.path.basename(stem))   # GAC's bundled icons (betul, pangkah, syiling, ...)
    return base + '.png'

def load_icon(path, h):
    if not os.path.exists(path):   # missing icon: soft accent dot instead of crashing (build also warns)
        import theme; im = Image.new('RGBA', (512, 512), (0, 0, 0, 0)); ImageDraw.Draw(im).ellipse((96, 96, 416, 416), fill=theme.A + (255,))
        return im.resize((h, h), Image.LANCZOS)
    im = Image.open(path).convert('RGBA')
    a = im.getchannel('A')
    if a.getextrema()[0] == 255:  # no transparency: knock out a white/near-white background from the corners
        rgb = im.convert('RGB'); mask = Image.new('L', im.size, 0)
        tmp = rgb.copy()
        for c in [(0, 0), (im.width - 1, 0), (0, im.height - 1), (im.width - 1, im.height - 1)]:
            if sum(tmp.getpixel(c)) > 690: ImageDraw.floodfill(tmp, c, (255, 0, 255), thresh=40)
        px = tmp.load(); mp = mask.load()
        for y in range(im.height):
            for x in range(im.width):
                if px[x, y] == (255, 0, 255): mp[x, y] = 255
        im.putalpha(Image.eval(mask.filter(ImageFilter.GaussianBlur(1.2)), lambda v: 255 - v))
    bb = im.getbbox()
    if bb: im = im.crop(bb)
    k = h / im.height
    return im.resize((max(1, int(im.width * k)), int(h)), Image.LANCZOS)

# ------------------------------------------------------------------ block renderers
# each returns dict(under=RGBA|None, content=RGBA, over=RGBA|None, wipe='x'|'y')
def _text_block(b, CW, base, seed):
    sz = b.get('size', base); fr, fb = _font(TH['fonts'][0], sz), _font(TH['fonts'][1], sz)
    words = _runs(b['text']); lh = int(sz * 1.45); sp = fr.getlength(' ')
    lines, cur, cw = [], [], 0
    for w in words:
        ww = (fb if w[1] else fr).getlength(w[0])
        glue = bool(cur) and re.match(r'^[.,!?;:)%]+$', w[0]) is not None   # punctuation sticks to the previous word
        if cur and not glue and cw + sp + ww > CW - 20: lines.append((cur, cw)); cur, cw = [], 0
        cw += (sp if cur and not glue else 0) + ww; cur.append((w, ww, glue))
    if cur: lines.append((cur, cw))
    pad = 26 if b.get('box') else 6
    h = lh * len(lines) + pad * 2 + 6
    content = Image.new('RGBA', (CW, h), (0, 0, 0, 0)); under = content.copy(); over = content.copy()
    dc, du, do = ImageDraw.Draw(content), ImageDraw.Draw(under), ImageDraw.Draw(over)
    align = b.get('align', 'center')
    for li, (ln, lw) in enumerate(lines):
        x = (CW - lw) / 2 if align == 'center' else 10; y = pad + li * lh
        spans = {'hl': [], 'ul': []}
        for i_, ((w, bold, hl, ul), ww, glue) in enumerate(ln):
            if glue: x -= sp
            for k, on in (('hl', hl), ('ul', ul)):
                if on:
                    if spans[k] and abs(spans[k][-1][1] - x) < sp + 2: spans[k][-1][1] = x + ww
                    else: spans[k].append([x, x + ww])
            dc.text((x, y + lh * 0.12), w, font=fb if bold else fr, fill=TH['hl_ink'] if hl else TH['ink']); x += ww + sp
        for i, (a, e) in enumerate(spans['hl']): _brush(du, a - 6, y + lh * 0.1, e + 6, y + lh * 0.92, PAL['hl'], seed + li * 7 + i)
        for i, (a, e) in enumerate(spans['ul']): _rough_line(do, a - 4, y + lh * 0.98, e + 4, y + lh * 0.98, PAL['mark'], max(4, sz // 9), seed + li * 13 + i)
    if b.get('box'):
        r = random.Random(seed); bw = max(4, sz // 10)
        x0, y0, x1, y1 = 8, 6, CW - 8, h - 6
        for (a, c) in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
            _rough_line(do, a[0] + r.uniform(-3, 3), a[1], c[0] + r.uniform(-3, 3), c[1], PAL['mark'], bw, r.randint(0, 999))
    return dict(under=under, content=content, over=over, wipe='x')

def _num_block(b, CW, base, seed):
    f = _font(HEAVY, b.get('numsize', int(base * 5.2))); txt = str(b['num'])
    bb = f.getbbox(txt); nw, nh = bb[2] - bb[0] + 20, bb[3] - bb[1] + 20
    rest = None
    if b.get('text'):
        rest = _text_block(dict(text=b['text'], size=b.get('size', int(base * 1.1)), align='left'), CW - int(nw * 0.92), base, seed)
    h = max(nh, rest['content'].height if rest else 0)
    content = Image.new('RGBA', (CW, h), (0, 0, 0, 0)); d = ImageDraw.Draw(content)
    nx = 0 if rest else (CW - nw) / 2
    d.text((nx + 10 - bb[0], (h - nh) / 2 + 10 - bb[1]), txt, font=f, fill=TH['num'][0], stroke_width=max(2, base // 14), stroke_fill=TH['num'][1])
    out = dict(under=None, content=content, over=None, wipe='x')
    if rest:
        ox, oy = int(nw * 0.92), (h - rest['content'].height) // 2
        for k in ('under', 'content', 'over'):
            if rest[k] is None: continue
            if out[k] is None: out[k] = Image.new('RGBA', (CW, h), (0, 0, 0, 0))
            out[k].alpha_composite(rest[k], (ox, oy))
    return out

def _arrow_block(b, CW, base, seed):
    h = b.get('h', 150); im = Image.new('RGBA', (CW, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    kind = b['arrow']; cx = CW / 2; sw = {'down': 0, 'down-left': -1, 'down-right': 1}.get(kind, 0)
    p0 = (cx - sw * 70, 8); p3 = (cx + sw * 90, h - 12); c1 = (cx + 60 - sw * 40, h * 0.35); c2 = (cx - 50 + sw * 60, h * 0.65)
    pts = []
    for i in range(41):
        t = i / 40
        pts.append(tuple((1 - t) ** 3 * p0[k] + 3 * (1 - t) ** 2 * t * c1[k] + 3 * (1 - t) * t * t * c2[k] + t ** 3 * p3[k] for k in (0, 1)))
    col = b.get('color') and tuple(b['color']) or TH['arrow']; w = max(4, base // 9)
    d.line(pts, fill=col, width=w, joint='curve')
    ang = math.atan2(pts[-1][1] - pts[-4][1], pts[-1][0] - pts[-4][0])
    for s in (2.5, -2.5):
        d.line([pts[-1], (pts[-1][0] - 26 * math.cos(ang + s * 0.2), pts[-1][1] - 26 * math.sin(ang + s * 0.2))], fill=col, width=w)
    return dict(under=None, content=Image.new('RGBA', (CW, h), (0, 0, 0, 0)), over=im, wipe='y')

def _image_block(b, CW, base, seed, icon_dir, warn):
    if 'icon' in b:
        name = b['icon']; p = find_icon(icon_dir, name)
        h = b.get('h', 200)
        if os.path.exists(p): im = load_icon(p, h)
        else:
            warn.append(f'icon missing: {p}')
            im = Image.new('RGBA', (h, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            d.rounded_rectangle((2, 2, h - 3, h - 3), 24, outline=(170, 170, 180), width=3)
            d.text((h / 2, h / 2), name[:12], font=_font(REG, 22), fill=(130, 130, 140), anchor='mm')
        content = Image.new('RGBA', (CW, im.height + 10), (0, 0, 0, 0)); content.alpha_composite(im, (int((CW - im.width) / 2), 5))
        return dict(under=None, content=content, over=None, wipe='x', pop=True)
    im = Image.open(b['image']).convert('RGBA'); w = min(b.get('w', int(CW * 0.85)), CW - 40); k = w / im.width
    im = im.resize((int(w), int(im.height * k)), Image.LANCZOS)
    m = Image.new('L', im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), 18, fill=255); im.putalpha(m)
    sh = Image.new('RGBA', (im.width + 40, im.height + 40), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((20, 26, im.width + 20, im.height + 26), 18, fill=(0, 0, 0, 70))
    sh = sh.filter(ImageFilter.GaussianBlur(10)); sh.alpha_composite(im, (20, 16))
    content = Image.new('RGBA', (CW, sh.height), (0, 0, 0, 0)); ox = int((CW - sh.width) / 2); content.alpha_composite(sh, (ox, 0))
    over = None
    if b.get('circle'):
        fx, fy, fr_ = b['circle']; over = Image.new('RGBA', content.size, (0, 0, 0, 0)); d = ImageDraw.Draw(over)
        cx, cy, r = ox + 20 + fx * im.width, 16 + fy * im.height, fr_ * im.width
        pts = [(cx + r * 1.15 * math.cos(a / 30 * 2 * math.pi + 0.3), cy + r * 0.8 * math.sin(a / 30 * 2 * math.pi + 0.3)) for a in range(33)]
        d.line(pts, fill=PAL['mark'], width=6, joint='curve')
    return dict(under=None, content=content, over=over, wipe='x')

def _shadowed(r):
    """Soft dark shadow under everything so white text reads over any video."""
    for k in ('content', 'over'):
        im = r[k]
        if im is None: continue
        pad = Image.new('RGBA', im.size, (0, 0, 0, 0))
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); sh.putalpha(im.getchannel('A').point(lambda v: min(255, int(v * 1.0))))
        sh1 = sh.filter(ImageFilter.GaussianBlur(3)); sh2 = sh.filter(ImageFilter.GaussianBlur(10))
        pad.alpha_composite(sh2, (0, 4)); pad.alpha_composite(sh1, (0, 2)); pad.alpha_composite(im)
        r[k] = pad
    return r

# ------------------------------------------------------------------ the page
def _ease(p): p = max(0.0, min(1.0, p)); return p * p * (3 - 2 * p)

class Doc:
    def __init__(self, spec, N, W, H, base_dir='.'):
        global TH, PAL
        PAL = PALETTES[spec.get('palette', 'gold')]
        self.theme = spec.get('theme') or ('clear' if H > W else 'paper'); TH = dict(THEMES[self.theme], fonts=FONTSETS[self.theme])
        self.L = L = layout_for(W, H, self.theme); L.update(spec.get('layout', {}))
        self.CW = L['x1'] - L['x0']; base = spec.get('size', L['size'])
        vh = L['view'][1] - L['view'][0]   # icons/numbers never taller than the visible window allows
        icon_dir = spec.get('icons');
        if icon_dir and not os.path.isabs(icon_dir): icon_dir = os.path.join(base_dir, icon_dir)
        self.warn = []; self.blocks = []; y = 0
        # in a short window (e.g. above the head) icons sit beside the previous line instead of below it
        inline = spec.get('inline_icons', vh < 420); last_text = None
        for i, b in enumerate(sorted(spec['blocks'], key=lambda b: b['at'])):
            if inline and 'icon' in b and last_text is not None and 'side' not in self.blocks[last_text[0]]:
                k, tb, seed = last_text; prev = self.blocks[k]
                ih = min(b.get('h', 200), int(vh * 0.55), 130)
                ic = _image_block(dict(b, h=ih), ih + 10, base, seed, icon_dir, self.warn)['content']
                ic = ic.crop(ic.getbbox() or (0, 0, ic.width, ic.height))
                r = _text_block(dict(tb, align='left'), self.CW - ic.width - 28, base, seed)
                tw = (r['content'].getbbox() or (0, 0, r['content'].width, 0))[2]
                hh = max(r['content'].height, ic.height); gx = int((self.CW - (ic.width + 28 + tw)) / 2)
                for key in ('under', 'content', 'over'):
                    if r[key] is None: continue
                    cv = Image.new('RGBA', (self.CW, hh), (0, 0, 0, 0)); cv.alpha_composite(r[key], (gx + ic.width + 28, (hh - r[key].height) // 2)); r[key] = cv
                if TH['shadow']: r = _shadowed(r); ic = _shadowed(dict(content=ic, over=None))['content']
                y -= prev['h']; r.update(y=prev['y'], h=hh, s=prev['s'], wipe='x',
                                         side=dict(img=ic, x=gx, y=(hh - ic.height) // 2, s=N(b['at'])))
                self.blocks[k] = r; y = prev['y'] + hh; continue
            y += b.get('gap', 30 if self.blocks else 0)
            if 'space' in b: y += b['space']; continue
            if 'text' in b and 'num' not in b: r = _text_block(b, self.CW, base, i * 31)
            elif 'num' in b: r = _num_block(dict(b, numsize=min(int(base * 5.2), int(vh * 0.8))), self.CW, base, i * 31)
            elif 'arrow' in b: r = _arrow_block(dict(b, h=min(b.get('h', 150), int(vh * 0.3))), self.CW, base, i * 31)
            else: r = _image_block(dict(b, h=min(b.get('h', 200), int(vh * 0.6))), self.CW, base, i * 31, icon_dir, self.warn)
            if TH['shadow']: r = _shadowed(r)
            r.update(y=y, h=r['content'].height, s=N(b['at'])); self.blocks.append(r); y += r['h']
            last_text = (len(self.blocks) - 1, b, i * 31) if ('text' in b and 'num' not in b) else None
        # clear theme: a soft dark band behind the text so white type reads over bright backgrounds
        self.scrim = None; sa = spec.get('scrim', 0.38 if self.theme == 'clear' else 0)
        if sa:
            px0, py0, px1, py1 = L['panel']; pw, ph = px1 - px0, py1 - py0
            yy = np.linspace(0, 1, ph)[:, None]; xx = np.linspace(0, 1, pw)[None, :]
            v = np.clip(np.minimum(yy / 0.25, (1 - yy) / 0.25), 0, 1) ** 1.5
            if W > H: v = v * np.clip(xx / 0.3, 0, 1)  # landscape: fade in from the left edge of the right half
            a = (v * np.ones_like(xx) * 255 * sa).astype(np.uint8)
            self.scrim = Image.new('RGBA', (pw, ph), (0, 0, 0, 0)); self.scrim.putalpha(Image.fromarray(a))
        # scroll targets: newest block bottom sits at the anchor line
        top, anchor = L['view'][0], L['anchor']
        self.targets = [(bl['s'], max(0, bl['y'] + bl['h'] - (anchor - top))) for bl in self.blocks]

    def cam(self, t):
        c = 0.0; prev = 0.0
        for s, tg in self.targets:
            if t < s - 0.25: break
            c = prev + (tg - prev) * _ease((t - s + 0.25) / 0.45); prev = max(prev, tg)
        return c

    def frame(self, t):
        """RGBA the size of the panel, transparent where the page is empty."""
        L = self.L; px0, py0, px1, py1 = L['panel']; out = Image.new('RGBA', (px1 - px0, py1 - py0), (0, 0, 0, 0))
        cam = self.cam(t); top = L['view'][0]
        for bl in self.blocks:
            if t < bl['s']: break
            sy = top + bl['y'] - cam
            if sy + bl['h'] < py0 or sy > py1: continue
            p = _ease((t - bl['s']) / 0.28); dy = (1 - p) * 22
            if bl.get('pop'): sc = 0.75 + 0.25 * _ease((t - bl['s']) / 0.3)
            ox, oy = L['x0'] - px0, int(sy + dy) - py0
            for k in ('under', 'content', 'over'):
                im = bl[k]
                if im is None: continue
                if k != 'content':
                    q = _ease((t - bl['s'] - 0.18) / 0.5)
                    if q <= 0: continue
                    if q < 1:
                        im = im.copy(); w_, h_ = im.size
                        cut = (int(w_ * q), 0, w_, h_) if bl['wipe'] == 'x' else (0, int(h_ * q), w_, h_)
                        ImageDraw.Draw(im).rectangle(cut, fill=(0, 0, 0, 0))
                if p < 1:
                    im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v, p=p: int(v * p)))
                if bl.get('pop') and k == 'content' and sc < 1:
                    w2, h2 = int(im.width * sc), int(im.height * sc); im2 = Image.new('RGBA', im.size, (0, 0, 0, 0))
                    im2.alpha_composite(im.resize((w2, h2), Image.LANCZOS), ((im.width - w2) // 2, (im.height - h2) // 2)); im = im2
                c0, c1 = max(0, -oy), min(im.height, out.height - oy)
                if c1 > c0: out.alpha_composite(im.crop((0, c0, im.width, c1)), (ox, oy + c0))
            sd = bl.get('side')
            if sd and t >= sd['s']:  # icon beside the line pops in at its own time
                q = _ease((t - sd['s']) / 0.3); im = sd['img']
                if q < 1:
                    sc = 0.6 + 0.4 * q; im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
                    im.putalpha(im.getchannel('A').point(lambda v, q=q: int(v * q)))
                ix = ox + sd['x'] + (sd['img'].width - im.width) // 2; iy = oy + sd['y'] + (sd['img'].height - im.height) // 2
                c0, c1 = max(0, -iy), min(im.height, out.height - iy)
                if c1 > c0: out.alpha_composite(im.crop((0, c0, im.width, c1)), (ix, iy + c0))
        # soft fade where the page scrolls out of the top of the content area
        fy = max(0, L['view'][0] - py0 - 40); fade = 60
        a = np.array(out.getchannel('A'), dtype=np.float32); n = min(out.height, fy + fade)
        k = np.clip((np.arange(n) - fy) / fade, 0, 1)[:, None]; a[:n] *= k
        by = L['view'][1] - py0; hb = out.height - by           # fade out below the view bottom
        if hb > 0: a[by:] *= np.clip(1 - np.arange(hb) / 50.0, 0, 1)[:, None]
        out.putalpha(Image.fromarray(a.astype(np.uint8)))
        if self.scrim is not None: out = Image.alpha_composite(self.scrim, out)
        return out
