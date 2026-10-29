#!/usr/bin/env python3
"""Optional effects for GAC, drawn on the cut video BEFORE captions and cards (so zooms never scale the captions).
build.py calls apply() when the timeline has "effects". All times are ORIGINAL video times, like elements.
Types: glass, chart, checklist, zoomcut, phone, pullback, digitalzoom (see references/timeline.md)."""
import os, subprocess, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import doc as docmod, theme

CREAM = (248, 245, 239); INK = (30, 34, 30); BODY = (40, 40, 40)
def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def eio(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def F(w, sz): return docmod._font({'heavy': docmod.HEAVY, 'bold': docmod.BOLD, 'reg': docmod.REG}[w], sz)
def rr_mask(w, h, r):
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255); return m
def frosted(fr, box, r=38, tint=0.45, blur=26, alpha=1.0):
    x0, y0, x1, y1 = [int(v) for v in box]; w, h = x1 - x0, y1 - y0
    if w < 8 or h < 8 or alpha <= 0: return
    sh = Image.new('RGBA', (w + 160, h + 160), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((80, 100, 80 + w, 100 + h), r, fill=(0, 0, 0, int(55 * alpha)))
    fr.alpha_composite(sh.filter(ImageFilter.GaussianBlur(26)), (x0 - 80, y0 - 80))
    reg = fr.crop((x0, y0, x1, y1)).convert('RGB').filter(ImageFilter.GaussianBlur(blur))
    reg = Image.blend(reg, Image.new('RGB', (w, h), CREAM), tint).convert('RGBA'); reg.putalpha(rr_mask(w, h, r).point(lambda v: int(v * alpha)))
    ImageDraw.Draw(reg).rounded_rectangle((0, 0, w - 1, h - 1), r, outline=(255, 255, 255, int(160 * alpha)), width=2)
    fr.alpha_composite(reg, (x0, y0))
def fade(u, d, i=0.35, o=0.3): return ease(u / i) * (1 - ease((u - d + o) / o))
def zoom_img(img, z, cx, cy, ty, W, H):
    x0 = min(max(cx - (W / 2) / z, 0), W - W / z); y0 = min(max(cy - ty / z, 0), H - H / z)
    return img.crop((int(x0), int(y0), int(x0 + W / z), int(y0 + H / z))).resize((W, H), Image.LANCZOS)

# ---------------------------------------------------------------- effects: fx(fr, e, u, d, W, H) -> fr
def fx_glass(fr, e, u, d, W, H):
    """Frosted glass panel; the text types itself letter by letter."""
    p = ease(u / 0.45); out = ease((u - d + 0.3) / 0.3); y = e.get('y', 1150); y0 = y - 150 + 80 * (1 - p) + 60 * out
    frosted(fr, (100, y0, W - 140, y0 + 300), r=40, alpha=p * (1 - out))
    txt = e['text']; f = F('heavy', e.get('size', 84))
    while f.getlength(txt) > W - 340: f = F('heavy', f.size - 4)
    n = int(min(len(txt), max(0, (u - 0.35) / e.get('speed', 0.08)))); a = int(255 * p * (1 - out))
    L = Image.new('RGBA', fr.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(L); tx = (W - 40) / 2 - f.getlength(txt) / 2
    dr.text((tx, y0 + 150), txt[:n], font=f, fill=INK + (a,), anchor='lm')
    if (u * 2) % 1 < 0.6 and n < len(txt) + 3: cx = tx + f.getlength(txt[:n]) + 8; dr.rectangle((cx, y0 + 105, cx + 6, y0 + 195), fill=theme.A + (a,))
    fr.alpha_composite(L); return fr

def fx_chart(fr, e, u, d, W, H):
    """Bars grow one by one and a line draws over them (decorative unless the user gave the values)."""
    vals = e.get('values') or [0.28, 0.42, 0.37, 0.58, 0.71, 0.92]; mx = max(vals); vals = [v / mx * 0.92 for v in vals]
    al = fade(u, d); y1 = e.get('y', 1220) + 220; x0, y0, x1 = 100, y1 - 430, W - 140
    frosted(fr, (x0, y0, x1, y1), r=40, alpha=al)
    L = Image.new('RGBA', fr.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(L); a = int(255 * al)
    if e.get('title'): dr.text((x0 + 44, y0 + 58), e['title'], font=F('heavy', 48), fill=INK + (a,), anchor='lm')
    n = len(vals); bw = min(110, (x1 - x0 - 88) / n * 0.62); gap = (x1 - x0 - 88 - bw * n) / max(1, n - 1); base_y = y1 - 50; top = []
    soft = tuple(int(c * 0.55 + 255 * 0.45) for c in theme.A)
    for k, v in enumerate(vals):
        g = ease((u - 0.25 - 0.13 * k) / 0.55); hgt = (y1 - y0 - 170) * v * g; bx = x0 + 44 + k * (bw + gap)
        dr.rounded_rectangle((bx, base_y - max(hgt, 2), bx + bw, base_y), 14, fill=(theme.A if k == n - 1 else soft) + (a,)); top.append((bx + bw / 2, base_y - hgt - 26))
    lp = ease((u - 0.9) / 0.8)
    if lp > 0 and n > 1:
        m_ = 1 + lp * (n - 1); pts = top[:int(m_)]
        if m_ < n: pts.append(tuple(np.array(top[int(m_) - 1]) + (np.array(top[int(m_)]) - np.array(top[int(m_) - 1])) * (m_ - int(m_))))
        if len(pts) > 1: dr.line(pts, fill=INK + (a,), width=6, joint='curve')
    fr.alpha_composite(L); return fr

def tick_at(k, n, d):
    st = min(0.45, d * 0.2); return st + max(0.2, d - st - 0.35) * k / max(1, n)

def fx_checklist(fr, e, u, d, W, H, ticks=None):
    """Frosted card, a box ticks for each item (on its own spoken time when given)."""
    items = e['items']; al = fade(u, d); p = ease(u / 0.35)
    x0, x1 = 100, W - 140; h = 140 + 78 * len(items) + (60 if e.get('title') else 0); y0 = e.get('y', 1200) - h / 2 + 40 * (1 - p)
    frosted(fr, (x0, y0, x1, y0 + h), r=40, alpha=al)
    L = Image.new('RGBA', fr.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(L); a = int(255 * al); y = y0 + 70
    if e.get('title'): dr.text((x0 + 48, y), e['title'], font=F('heavy', 52), fill=INK + (a,), anchor='lm'); y += 90
    for k, it in enumerate(items):
        t_k = ticks[k] if ticks else tick_at(k, len(items), d); tk = ease((u - t_k) / min(0.22, d / 6)); yy = y + k * 78
        dr.rounded_rectangle((x0 + 48, yy - 24, x0 + 96, yy + 24), 10, outline=INK + (a,), width=4, fill=(theme.A + (int(a * tk),)) if tk > 0 else None)
        if tk > 0:
            pts = [(x0 + 58, yy), (x0 + 70, yy + 13), (x0 + 88, yy - 12)]; n = 1 + 2 * tk; seg = pts[:int(n)]
            if n < 3: seg.append(tuple(np.array(pts[int(n) - 1]) + (np.array(pts[int(n)]) - np.array(pts[int(n) - 1])) * (n - int(n))))
            if len(seg) > 1: dr.line(seg, fill=theme.ON + (a,), width=7, joint='curve')
        f = F('bold', 42)
        while f.getlength(it) > x1 - x0 - 180: f = F('bold', f.size - 2)
        dr.text((x0 + 124, yy), it, font=f, fill=BODY + (int(a * (0.55 + 0.45 * tk)),), anchor='lm')
    fr.alpha_composite(L); return fr

def fx_phone(fr, e, u, d, W, H):
    """Phone slides in from the right with the user's screenshot (or a list) on its screen."""
    p = ease(u / 0.5); out = ease((u - d + 0.3) / 0.3); pw, ph = e.get('w', 320), int(e.get('w', 320) * 2.05)
    cx = e.get('x', 740) + 420 * (1 - p) + 420 * out; cy = e.get('y', 1130)
    sw, sh_ = pw - 24, ph - 24
    if e.get('image') and os.path.exists(e['image']):
        im = Image.open(e['image']).convert('RGB'); k = sw / im.width; im = im.resize((sw, int(im.height * k)), Image.LANCZOS)
        off = int(max(0, im.height - sh_) * eio((u - 0.6) / max(0.5, d - 1.0))) if e.get('scroll', True) else 0
        scr = Image.new('RGBA', (sw, sh_), CREAM + (255,)); scr.paste(im.crop((0, off, sw, off + min(sh_, im.height))), (0, 0))
    else:
        scr = Image.new('RGBA', (sw, sh_), CREAM + (255,)); dr = ImageDraw.Draw(scr)
        dr.text((22, 50), e.get('title', ''), font=F('heavy', 32), fill=INK + (255,), anchor='lm')
        for k, it in enumerate(e.get('items', [])):
            yy = 104 + k * 52; dr.ellipse((22, yy - 8, 38, yy + 8), fill=theme.A + (255,)); dr.text((50, yy), it, font=F('bold', 26), fill=BODY + (255,), anchor='lm')
    scr.putalpha(rr_mask(sw, sh_, 34))
    ph_im = Image.new('RGBA', (pw + 80, ph + 80), (0, 0, 0, 0)); d2 = ImageDraw.Draw(ph_im)
    d2.rounded_rectangle((40, 54, 40 + pw, 54 + ph), 46, fill=(0, 0, 0, 90)); ph_im = ph_im.filter(ImageFilter.GaussianBlur(16)); d2 = ImageDraw.Draw(ph_im)
    d2.rounded_rectangle((40, 40, 40 + pw, 40 + ph), 46, fill=(24, 24, 26, 255)); ph_im.alpha_composite(scr, (52, 52))
    d2.rounded_rectangle((40 + pw / 2 - 46, 60, 40 + pw / 2 + 46, 80), 10, fill=(24, 24, 26, 255))
    fr.alpha_composite(ph_im.rotate(-4 * (1 - p), resample=Image.BICUBIC), (int(cx - ph_im.width / 2), int(cy - ph_im.height / 2))); return fr

def fx_pullback(fr, e, u, d, W, H):
    """The live video pulls back and turns out to be playing inside an app window."""
    p = eio((u - 0.25) / 1.0) * (1 - eio((u - d + 0.4) / 0.4)); sc = 1 - 0.42 * p; full = fr.convert('RGB')
    bgd = full.resize((W // 8, H // 8)).filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BILINEAR)
    bgd = Image.blend(bgd, Image.new('RGB', (W, H), (20, 22, 20)), 0.35 * p).convert('RGBA')
    vw, vh = int(W * sc), int(H * sc); side = int(250 * p); bar = int(56 * p)
    ww, wh = vw + side + int(28 * p), vh + bar + int(14 * p); wx = (W - ww) // 2; wy = int((H - wh) / 2 + 120 * p)
    if p > 0.01:
        sh = Image.new('RGBA', (ww + 200, wh + 200), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((100, 130, 100 + ww, 130 + wh), 36, fill=(0, 0, 0, int(120 * p)))
        bgd.alpha_composite(sh.filter(ImageFilter.GaussianBlur(30)), (wx - 100, wy - 100))
        win = Image.new('RGBA', (ww, wh), (0, 0, 0, 0)); dw = ImageDraw.Draw(win)
        dw.rounded_rectangle((0, 0, ww - 1, wh - 1), int(36 * p), fill=CREAM + (255,), outline=(255, 255, 255, 255), width=2)
        for k, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]): dw.ellipse((26 + k * 30, bar / 2 - 9, 44 + k * 30, bar / 2 + 9), fill=c + (255,))
        dw.text((ww / 2, bar / 2), e.get('window', 'video.mp4'), font=F('bold', 24), fill=(90, 96, 88, 255), anchor='mm')
        if side >= 200:
            x0 = 26; y = bar + 40
            if e.get('title'): dw.text((x0, y), e['title'], font=F('heavy', 28), fill=INK + (255,), anchor='lm')
            for k, it in enumerate(e.get('items', [])[:5]):
                yy = y + 56 + k * 46; done = u > 0.9 + 0.35 * k
                dw.ellipse((x0, yy - 10, x0 + 20, yy + 10), fill=(theme.A + (255,)) if done else None, outline=(theme.A if done else (160, 160, 160)) + (255,), width=3)
                f = F('bold', 24)
                while f.getlength(it) > side - 70: f = F('bold', f.size - 2)
                dw.text((x0 + 34, yy), it, font=f, fill=BODY + (255,), anchor='lm')
            if e.get('percent'):
                pc = int(e['percent'] * ease((u - 0.6) / 1.6)); yb = y + 56 + min(5, len(e.get('items', []))) * 46 + 20
                dw.rounded_rectangle((x0, yb, side - 20, yb + 12), 6, fill=(220, 214, 204, 255)); dw.rounded_rectangle((x0, yb, x0 + max(12, (side - 20 - x0) * pc / 100), yb + 12), 6, fill=theme.A + (255,))
                dw.text((x0, yb + 50), f'{pc}%', font=F('heavy', 52), fill=INK + (255,), anchor='lm')
        win.putalpha(win.getchannel('A').point(lambda v: int(v * min(1, p * 3)))); bgd.alpha_composite(win, (wx, wy))
    vid = full.resize((vw, vh), Image.LANCZOS).convert('RGBA')
    if p > 0.01: vid.putalpha(rr_mask(vw, vh, int(26 * p))); bgd.alpha_composite(vid, (wx + side + int(14 * p), wy + bar))
    else: bgd.alpha_composite(vid)
    return bgd

def make_zoom(kind):
    def fx(fr, e, u, d, W, H):
        fy = e['_face_y']
        if kind == 'zoomcut':
            zs = e.get('zooms', [1.0, 1.22, 1.45, 1.0]); k = min(len(zs) - 1, int(u / (d / len(zs)))); z = zs[k]
            img = zoom_img(fr.convert('RGB'), z, W / 2, fy, H * 0.47, W, H).convert('RGBA')
            if u - k * d / len(zs) < 0.07 and k > 0: img.alpha_composite(Image.new('RGBA', img.size, (255, 255, 255, 60)))
            return img
        z = 1 + (e.get('to', 1.35) - 1) * eio(u / d)
        return zoom_img(fr.convert('RGB'), z, W / 2, fy, fy + (H * 0.47 - fy) * eio(u / d), W, H).convert('RGBA')
    return fx

FX = dict(glass=fx_glass, chart=fx_chart, checklist=fx_checklist, phone=fx_phone, pullback=fx_pullback,
          zoomcut=make_zoom('zoomcut'), digitalzoom=make_zoom('digitalzoom'))
SFX = dict(glass='whoosh', chart='whoosh', checklist='pop', phone='whoosh', pullback='swoosh', zoomcut='hit', digitalzoom='swell')
import effects2   # 17 more effects (orbit, chat, frame_escape, ...): see references/effects.md
FX.update(effects2.FX2); SFX.update(effects2.SFX2)

def apply(video, specs, N, W, H, base_dir, face_box=None):
    """Rewrite `video` (the cut base) with the effects. Returns ([(start, end)] output windows, [(t, sfx)])."""
    wins, ev, todo = [], [], []
    for e in specs:
        if e['type'] not in FX: print(f"WARNING effect '{e['type']}' unknown ({'/'.join(FX)})"); continue
        e = dict(e); s, t_end = N(e['t'][0]), N(e['t'][1])
        if e.get('image') and not os.path.isabs(e['image']): e['image'] = os.path.join(base_dir, e['image'])
        e['_ticks'] = [N(x) - s for x in e['at']] if e.get('at') else None
        fb = face_box(video, s + 0.1) if face_box else None; e['_face_y'] = (fb[0] + fb[1]) / 2 if fb else H * 0.36
        e['_face'] = fb; e['_base'] = base_dir
        todo.append((s, t_end, e)); ev.append((s, SFX[e['type']]))
        if e['type'] == 'checklist': ev += [(s + (x if e['_ticks'] else tick_at(k, len(e['items']), t_end - s)) + 0.1, 'tick') for k, x in enumerate(e['_ticks'] or e['items'])]
        if e['type'] == 'zoomcut':
            n = len(e.get('zooms', [1.0, 1.22, 1.45, 1.0])); ev += [(s + k * (t_end - s) / n, 'hit') for k in range(1, n)]
        if e['type'] in ('glass', 'chart', 'checklist', 'phone', 'pullback') + effects2.PANEL2: wins.append((s, t_end))   # captions hide under panels
    if not todo: return wins, ev
    tmp = video + '.fx.mov'; fps = 30
    dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', video, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                            '-i', video, '-map', '0:v', '-map', '1:a?', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p',
                            '-c:a', 'copy', tmp], stdin=subprocess.PIPE)
    k = 0
    while True:
        buf = dec.stdout.read(W * H * 3)
        if len(buf) < W * H * 3: break
        t = k / fps; act = [(s, e_, e) for s, e_, e in todo if s <= t < e_]
        if act:
            fr = Image.frombytes('RGB', (W, H), buf).convert('RGBA')
            for s, e_, e in act:
                fn = FX[e['type']]; e.setdefault('_ticks', None)
                fr = fn(fr, e, t - s, e_ - s, W, H, e['_ticks']) if e['type'] == 'checklist' else fn(fr, e, t - s, e_ - s, W, H)
            buf = fr.convert('RGB').tobytes()
        enc.stdin.write(buf); k += 1
    enc.stdin.close(); enc.wait(); dec.wait(); os.replace(tmp, video)
    print(f'effects: {len(todo)} applied', flush=True)
    return wins, ev
