"""Gaya 1 (references/gaya1.md): motion-UI tutorial look.

Drawn per frame by build.py:
  - captions that type themselves letter by letter (subtitles "style": "type")
  - two-tier hook: small kicker that turns on word by word + one giant word ("type": "hook2")
  - giant word with viewfinder corners ("type": "bigword", "style": "gaya1")
  - tilted white pill with an italic serif word ("type": "pill")
  - dark app window that slides up, with typed text / a list / rows ("type": "uipanel")
  - orange button CTA ("type": "cta", "style": "button")
  - chapter tag "step 1 / 5" + progress bar (top-level "chapters")
  - "behind": true on an element puts it behind the speaker (person mask, U^2-Net human seg)
"""
import math, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, '..', 'assets', 'fonts')
FPS = 30
WHITE = (238, 237, 238)
INK = (14, 14, 17)
PANEL = (38, 38, 35)
ORANGE = (254, 89, 52)
TYPE_CPS = 60          # letters per second for typed text (reference: ~2 letters per frame)

_FC = {}
def _f(kind, sz):
    key = (kind, int(sz))
    if key not in _FC:
        try:
            if kind == 'serif':
                f = ImageFont.truetype(os.path.join(FONTS, 'InstrumentSerif-Italic.ttf'), int(sz))
            elif kind == 'mono':
                for p in ('/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf', '/System/Library/Fonts/Menlo.ttc',
                          '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'):
                    if os.path.exists(p): f = ImageFont.truetype(p, int(sz)); break
                else: f = ImageFont.load_default()
            else:
                path, var = {'sans': ('PlusJakartaSans.ttf', 'Bold'), 'sans_med': ('PlusJakartaSans.ttf', 'Medium'),
                             'black': ('Inter.ttf', 'Black')}[kind]
                f = ImageFont.truetype(os.path.join(FONTS, path), int(sz)); f.set_variation_by_name(var)
        except OSError:
            f = ImageFont.load_default()
        _FC[key] = f
    return _FC[key]

def ease_out(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def _alpha(im, a):
    if a >= 0.999: return im
    im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * a))); return im
def _shadow(im, blur=10, a=0.35, dy=6):
    pad = blur * 3; out = Image.new('RGBA', (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); sh.putalpha(im.getchannel('A').point(lambda v: int(v * a)))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)), (pad, pad + dy)); out.alpha_composite(im, (pad, pad)); return out
def _put(fr, im, cx, cy):
    fr.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))
def lighter(c, k=0.25): return tuple(int(v + (255 - v) * k) for v in c[:3])


# ---------------------------------------------------------------- person mask (text behind the speaker)
class Seg:
    """Person masks for the cut video, computed only for the frames that show a "behind" element."""
    MODEL = os.path.expanduser(os.environ.get('GAC_SEG_MODEL', '~/.cache/gac/models/u2net_human_seg.onnx'))
    URL = 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx'

    def __init__(self, video, W, H):
        self.video, self.W, self.H, self.m, self.sess = video, W, H, {}, None

    def _session(self):
        if self.sess is None:
            import onnxruntime as ort
            if not os.path.exists(self.MODEL):
                os.makedirs(os.path.dirname(self.MODEL), exist_ok=True)
                subprocess.run(['curl', '-fsSL', '--retry', '3', '-o', self.MODEL + '.part', self.URL], check=True)
                os.replace(self.MODEL + '.part', self.MODEL)
            self.sess = ort.InferenceSession(self.MODEL, providers=['CPUExecutionProvider'])
        return self.sess

    def prepare(self, windows):
        mean, std = np.array([0.485, 0.456, 0.406]), np.array([0.229, 0.224, 0.225])
        for a, b in windows:
            k0, k1 = int(round(a * FPS)), int(round(b * FPS)) + 1
            k0 = max(0, k0); need = [k for k in range(k0, k1) if k not in self.m]
            if not need: continue
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{k0 / FPS:.3f}', '-i', self.video, '-frames:v', str(k1 - k0),
                                  '-vf', 'scale=320:320', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
            fr = np.frombuffer(raw, np.uint8).reshape(-1, 320, 320, 3)
            s = self._session(); name = s.get_inputs()[0].name
            for i, img in enumerate(fr):
                x = ((img / 255.0 - mean) / std).transpose(2, 0, 1)[None].astype(np.float32)
                o = s.run(None, {name: x})[0][0, 0]; o = (o - o.min()) / (o.max() - o.min() + 1e-9)
                self.m[k0 + i] = (o * 255).astype(np.uint8)

    def at(self, t):
        k = int(round(t * FPS))
        small = self.m.get(k)
        if small is None:
            near = [q for q in self.m if abs(q - k) <= 2]
            if not near: return None
            small = self.m[min(near, key=lambda q: abs(q - k))]
        m = Image.fromarray(small).resize((self.W, self.H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(2))
        return np.asarray(m, dtype=np.float32) / 255.0

def cut_out_person(layer, mask):
    """layer: RGBA frame; mask: float HxW (1 = person). Returns the layer with the person area cleared."""
    if mask is None: return layer
    a = np.asarray(layer.getchannel('A'), dtype=np.float32) * (1 - mask)
    layer = layer.copy(); layer.putalpha(Image.fromarray(a.clip(0, 255).astype(np.uint8))); return layer


# ---------------------------------------------------------------- typed captions
def caption_layout(words, max_w=840):
    """words: [(text, kind)] kind in 'n' normal / 'e' emphasis / 'i' italic serif. Returns lines of (text, kind, font)."""
    def fnt(kind): return _f('serif', 74) if kind == 'i' else _f('sans', 58)
    lines, line, lw = [], [], 0
    for w, kind in words:
        f = fnt(kind); ww = f.getlength(w + ' ')
        if line and lw + ww > max_w: lines.append(line); line, lw = [], 0
        line.append((w, kind, f)); lw += ww
    if line: lines.append(line)
    return lines

def sub_frame_type(grp, t, y, W, H, accent, italic=()):
    """grp: [(word, emph, ws, we)] on the output timeline. Each word types itself from its spoken start."""
    words = []
    for w, emph, ws, we in grp:
        kind = 'i' if w.lower().strip(',.?!') in italic else ('e' if emph else 'n')
        n = int(max(0, (t - ws) * TYPE_CPS)) + (1 if t >= ws else 0)
        words.append((w, kind, min(len(w), n)))
    lines = caption_layout([(w, k) for w, k, _ in words])
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sh = im.copy(); d, ds = ImageDraw.Draw(im), ImageDraw.Draw(sh)
    k = 0; lh = 78
    for li, ln in enumerate(lines):
        tw = sum(f.getlength(w + ' ') for w, _, f in ln); x = (W - tw) / 2; yy = y + (li - (len(lines) - 1)) * lh
        for w, kind, f in ln:
            vis = words[k][2]; k += 1
            if vis > 0:
                col = lighter(accent, 0.3) if kind == 'i' else (accent if kind == 'e' else WHITE)
                ds.text((x, yy + 3), w[:vis], font=f, fill=(0, 0, 0, 150), anchor='ls')
                d.text((x, yy), w[:vis], font=f, fill=col, anchor='ls')
            x += f.getlength(w + ' ')
    return Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5)), im)


# ---------------------------------------------------------------- chapter tag + progress bar
def chapters_frame(chs, t, W, H, accent):
    """chs: [(start, end, label, index, total)] on the output timeline."""
    cur = [c for c in chs if c[0] <= t < c[1]]
    if not cur: return None
    a, b, label, idx, n = cur[-1]
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x0, x1, yb = 60, W - 60, 252
    d.rounded_rectangle((x0, yb, x1, yb + 4), 2, fill=(255, 255, 255, 70))
    frac = min(1.0, (idx + min(1.0, (t - a) / 0.4)) / n)   # the bar grows into the new chapter in 0.4 s
    d.rounded_rectangle((x0, yb, x0 + (x1 - x0) * frac, yb + 4), 2, fill=accent + (255,))
    f = _f('mono', 26); parts = []
    if '·' in label: l, r = label.split('·', 1); parts = [(l + '·', WHITE), (r, accent)]
    elif '/' in label:
        l, r = label.split('/', 1); ws = l.rstrip().rsplit(' ', 1)
        parts = ([(ws[0] + ' ', WHITE)] if len(ws) > 1 else []) + [(ws[-1], accent), (' /' + r, WHITE)]
    else: parts = [(label, WHITE)]
    tw = sum(f.getlength(p) for p, _ in parts); bx, by = x0, 282
    d.rounded_rectangle((bx, by, bx + tw + 28, by + 44), 8, fill=(36, 36, 36, 235))
    x = bx + 14
    for p, c in parts: d.text((x, by + 22), p, font=f, fill=c, anchor='lm'); x += f.getlength(p)
    return im


# ---------------------------------------------------------------- elements
def big_word_img(text, color, size, max_w=900):
    f = _f('black', size)
    while f.getlength(text) > max_w and size > 80: size -= 6; f = _f('black', size)
    bb = f.getbbox(text); w, h = bb[2] - bb[0] + 20, bb[3] - bb[1] + 20
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); ImageDraw.Draw(im).text((10 - bb[0], 10 - bb[1]), text, font=f, fill=color)
    return im

def viewfinder(w, h, a):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); L, s = 46, 5; c = (255, 255, 255, int(220 * a))
    for x, y, dx, dy in ((0, 0, 1, 1), (w - 1, 0, -1, 1), (0, h - 1, 1, -1), (w - 1, h - 1, -1, -1)):
        d.line([(x, y), (x + dx * L, y)], fill=c, width=s); d.line([(x, y), (x, y + dy * L)], fill=c, width=s)
    return im

def pill_img(parts, accent):
    fs, fi = _f('sans', 54), _f('serif', 66)
    tw = sum((fi if k == 'i' else fs).getlength(p) for p, k in parts); h = 104; w = int(tw + 70)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 22, fill=(255, 255, 255, 250)); x = 35
    for p, k in parts:
        f = fi if k == 'i' else fs
        d.text((x, h / 2 + (4 if k == 'i' else 0)), p, font=f, fill=lighter(accent, 0.15) if k == 'i' else INK, anchor='lm'); x += f.getlength(p)
    return _shadow(im, 16, 0.35, 8).rotate(3, resample=Image.BICUBIC, expand=True)

def button_img(text):
    f = _f('sans', 50); w = int(f.getlength(text) + 110); h = 104
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=ORANGE); d.text((w / 2, h / 2), text, font=f, fill=(255, 255, 255), anchor='mm')
    return _shadow(im, 14, 0.35, 6)

def uipanel_img(el, t, accent, s):
    """Dark app window. title; then one of: typed (text that types itself), items (folder list with a moving
    selection: select = [[t, index], ...] on the output timeline) or rows ([[label, value], ...])."""
    w = 820; f, fm, fsm = _f('sans', 42), _f('sans_med', 38), _f('sans_med', 30)
    body = []
    if el.get('typed'):
        n = int(max(0, (t - s - 0.25) * TYPE_CPS)); txt = el['typed'][:n]; lines, ln = [], ''
        for para in txt.split('\n'):
            ln = ''
            for word in para.split(' '):
                if fm.getlength((ln + ' ' + word).strip()) > w - 90: lines.append(ln); ln = word
                else: ln = (ln + ' ' + word).strip()
            lines.append(ln)
        body = [('type', lines)]
    if el.get('items'):
        sel = None
        for ts, ix in el.get('_select', []):
            if t >= ts: sel = ix
        body.append(('items', el['items'], sel))
    if el.get('rows'): body.append(('rows', el['rows']))
    h = 96
    for b in body: h += {'type': lambda b: 58 * max(3, len(b[1])) + 90, 'items': lambda b: 74 * len(b[1]) + 20,
                         'rows': lambda b: 74 * len(b[1]) + 20}[b[0]](b)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 30, fill=PANEL + (250,), outline=(70, 70, 66), width=2)
    for i, c in enumerate(((255, 95, 87), (254, 188, 46), (40, 200, 64))): d.ellipse((30 + i * 34, 34, 52 + i * 34, 56), fill=c)
    d.text((150, 45), el.get('title', ''), font=fsm, fill=(220, 220, 215), anchor='lm'); y = 96
    for b in body:
        if b[0] == 'type':
            for i, ln in enumerate(b[1]): d.text((44, y + 10 + i * 58), ln, font=fm, fill=(235, 235, 230))
            if int(t * 2) % 2 == 0 or len(''.join(b[1])) < len(el['typed']):   # blinking cursor
                last = b[1][-1] if b[1] else ''; cx = 44 + fm.getlength(last) + 4; cy = y + 10 + (len(b[1]) - 1) * 58
                d.rectangle((cx, cy + 4, cx + 3, cy + 46), fill=(235, 235, 230))
            yb = y + 58 * max(3, len(b[1])) + 20
            d.ellipse((w - 92, yb, w - 40, yb + 52), fill=ORANGE); d.text((w - 66, yb + 26), '↑', font=_f('sans', 34), fill=(255, 255, 255), anchor='mm')
            y += 58 * max(3, len(b[1])) + 90
        elif b[0] == 'items':
            for i, it in enumerate(b[1]):
                yy = y + i * 74
                if b[2] == i: d.rounded_rectangle((16, yy, w - 16, yy + 66), 12, fill=accent)
                d.rounded_rectangle((44, yy + 18, 92, yy + 52), 6, fill=(96, 160, 245) if b[2] != i else (255, 255, 255))
                d.text((116, yy + 33), it, font=fm, fill=(255, 255, 255), anchor='lm')
            y += 74 * len(b[1]) + 20
        elif b[0] == 'rows':
            for i, (lab, val) in enumerate(b[1]):
                yy = y + i * 74; d.text((44, yy + 33), lab, font=fm, fill=(235, 235, 230), anchor='lm')
                d.text((w - 44, yy + 33), val, font=f, fill=accent, anchor='rm')
            y += 74 * len(b[1]) + 20
    return _shadow(im, 22, 0.45, 12)

def hook2_img(el, t, accent):
    """Kicker line whose words switch from dim to full as they are spoken, above one giant word."""
    dark = el.get('ink', 'light') == 'dark'          # 'dark' = black text for bright backgrounds (as in the reference)
    on = INK if dark else WHITE; off = (168, 162, 158) if dark else (255, 255, 255, 120)
    fk = _f('sans', el.get('kicker_size', 50)); words = el['_kicker']
    tw = sum(fk.getlength(w + ' ') for w, _ in words)
    big = big_word_img(el['big'], accent if el.get('big_color', 'accent') == 'accent' else (INK if dark else WHITE), el.get('size', 230))
    w = int(max(tw, big.width)) + 40; kh = 96
    im = Image.new('RGBA', (w, kh + big.height), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = (w - tw) / 2
    for word, ts in words:
        d.text((x, kh * 0.55), word, font=fk, fill=on if t >= ts else off, anchor='lm'); x += fk.getlength(word + ' ')
    im.alpha_composite(big, (int((w - big.width) / 2), kh)); return im

def head_top(mask, W):
    """Top of the speaker's head (y px) from a person mask, looking at the centre of the frame."""
    if mask is None: return None
    band = mask[:, int(W * 0.3):int(W * 0.7)].max(1); rows = np.where(band > 0.5)[0]
    return int(rows[0]) if len(rows) else None

def place_behind(el, img_h, big_h, seg, W):
    """Centre y so the giant word's lower third sits behind the head, the whole block below the top UI zone."""
    if 'y' in el and el['y']: return el['y']
    top = head_top(seg.at(el['s'] + 0.05), W) if seg else None
    if top is None: return el['cy']
    bottom = top + int(big_h * 0.38)                       # how far the word overlaps the hair
    return max(235 + img_h / 2, bottom - img_h / 2)

def draw(el, t, W, H, accent, seg=None):
    """Frame of a Gaya 1 element at output time t. Returns (rgba W x H) or None."""
    s, e = el['s'], el['e']
    if t < s or t > e: return None
    if el.get('behind') and not el.get('_placed') and el['type'] in ('hook2', 'bigword'):
        big = big_word_img(el.get('big') or el.get('text'), (0, 0, 0), el.get('size', 230 if el['type'] == 'hook2' else 210))
        img_h = hook2_img(el, s, accent).height if el['type'] == 'hook2' else big.height
        el['cy'] = place_behind(el, img_h, big.height, seg, W); el['_placed'] = True
    fr = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ty = el['type']; u = t - s
    out_a = 1.0 if el.get('cover') and ty == 'hook2' else min(1.0, max(0.0, (e - t) / 0.17))
    if ty == 'hook2':
        _put(fr, hook2_img(el, t, accent), W / 2, el['cy'])
    elif ty == 'bigword':
        img = big_word_img(el['text'], accent if el.get('color', 'accent') in ('accent', 'gold', 'yellow') else tuple(el['color']), el.get('size', 210))
        if u < 0.2:   # viewfinder corners first, then the word fades in over 2 frames
            _put(fr, viewfinder(img.width + 120, img.height + 80, 1 - u / 0.2 * 0.3), W / 2, el['cy'])
        else:
            _put(fr, _alpha(img, min(1.0, (u - 0.2) / 0.07) * out_a), W / 2, el['cy'])
    elif ty == 'pill':
        img = pill_img(el['_parts'], accent); el['_top'] = el['cy'] - img.height / 2 + 20
        p = ease_out(u / 0.17); _put(fr, _alpha(img, p * out_a), W / 2, el['cy'] + 40 * (1 - p))
    elif ty == 'uipanel':
        p = ease_out(u / 0.15); img = uipanel_img(el, t, accent, s); el['_top'] = el['cy'] - img.height / 2 + 40; _put(fr, _alpha(img, min(1, p * 1.5) * out_a), W / 2, el['cy'] + 140 * (1 - p))
    elif ty == 'cta':
        p = ease_out(u / 0.2); _put(fr, _alpha(button_img(el['text']), p * out_a), W / 2, el['cy'] + 30 * (1 - p))
    return fr

def prepare(el, N, W, H, face_top=None):
    """Called once per element: default positions and times mapped to the output timeline."""
    ty = el['type']
    if ty == 'hook2':
        el['_kicker'] = [(w, N(ts)) for w, ts in el['kicker']] if isinstance(el['kicker'], list) else [(w, -1) for w in el['kicker'].split()]
        el.setdefault('behind', True)
        # giant word sits on the top of the head (behind it); kicker above, never inside the top UI zone
        el['cy'] = el.get('y') or (max(400, min(620, (face_top or 520) - 10)))
    elif ty == 'bigword':
        el.setdefault('behind', True); el['cy'] = el.get('y') or max(360, min(560, (face_top or 520) - 40))
    elif ty == 'pill':
        el['_parts'] = [(p[0], p[1] if len(p) > 1 else 'n') for p in el['parts']]; el['cy'] = el.get('y', 1300)
    elif ty == 'uipanel':
        el['_select'] = [(N(ts), ix) for ts, ix in el.get('select', [])]; el['cy'] = el.get('y', 1250)
    elif ty == 'cta':
        el['cy'] = el.get('y', 1420)
    return el

def warm_grade():
    """Reference grade: warm cream/peach, low saturation, deep blacks, soft (rolled-off) highlights."""
    return ("eq=saturation=0.86:contrast=0.98:gamma=1.02,"
            "colorbalance=rs=0.05:gs=0.015:bs=-0.05:rm=0.04:gm=0.01:bm=-0.04:rh=0.02:bh=-0.03,"
            "curves=master='0/0 0.25/0.24 0.5/0.52 0.8/0.81 1/0.9'")
