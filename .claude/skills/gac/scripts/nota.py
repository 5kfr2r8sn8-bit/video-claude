#!/usr/bin/env python3
"""Gaya NOTA: a frosted-glass note card over the participant's own B-roll (video or photo).
Title, then steps that appear one by one (serif name with a marker stroke + body text), a closing
line, and an accent CTA pill on top. No speaking needed; optional voice-over or music file.
Usage: python3 nota.py nota.json OUT.mp4 [--preview 6]
Spec: {"broll": "clip.mp4" | "photo.jpg", "title": "Berapa gram emas anda perlu sebelum bersara? Jom kira.",
       "steps": [["Langkah 1 :", "Tentukan umur bersara. Contoh: **60 tahun**."], ...],     # optional 3rd item = time (s)
       "close": ["Nampak tak?", "Mula awal, beban setiap bulan jadi ringan."],
       "pill": ["Umur anda sekarang berapa?", "Komen, saya tolong kira. Save post ni."],
       "profile": "gac_profile.json", "audio": "voice_or_music.mp3", "total": 27,
       "font_tajuk": "playfair|montserrat|jakarta|inter", "font_teks": "montserrat|jakarta|inter",
       "warna_kad": "krim|putih|hitam|kelabu|#hex", "warna_huruf": "auto|hitam|putih|#hex",
       "tint": 0.30 (card opacity 0-1), "blur": 9, "show_pill": false, "sfx": false}"""
import sys, os, json, subprocess, re
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import theme, sfx, doc as docmod

W, H, FPS = 1080, 1920, 30
FONTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'fonts')
CREAM = (248, 245, 239); INK = (30, 42, 29); BODY = (38, 38, 38); BOLD_INK = (17, 25, 15)
TITLE_FONTS = dict(playfair=('PlayfairDisplay.ttf', 'Bold'), montserrat=('Montserrat.ttf', 'ExtraBold'),
                   jakarta=('PlusJakartaSans.ttf', 'ExtraBold'), inter=('Inter.ttf', 'Bold'))
BODY_FONTS = dict(montserrat='Montserrat.ttf', jakarta='PlusJakartaSans.ttf', inter='Inter.ttf')
CARD_COLOURS = dict(krim=(248, 245, 239), putih=(255, 255, 255), hitam=(18, 18, 20), kelabu=(120, 124, 128))
LOOK = dict(title=TITLE_FONTS['playfair'], body='Montserrat.ttf')
_F = {}
def serif(sz):   # title / step-name font (Playfair by default)
    k = ('t', LOOK['title'], sz)
    if k not in _F: f = ImageFont.truetype(os.path.join(FONTS, LOOK['title'][0]), sz); f.set_variation_by_name(LOOK['title'][1]); _F[k] = f
    return _F[k]
def sans(sz, w='Medium'):   # body font
    k = ('b', LOOK['body'], w, sz)
    if k not in _F:
        f = ImageFont.truetype(os.path.join(FONTS, LOOK['body']), sz)
        try: f.set_variation_by_name(w)
        except Exception: f.set_variation_by_name('ExtraBold' if w in ('Black', 'ExtraBold') else 'Medium')
        _F[k] = f
    return _F[k]
def setup_look(S):
    """Participant's choices: font_tajuk, font_teks, warna_kad, warna_huruf (names or #hex); text colour auto-contrasts."""
    global CREAM, INK, BODY, BOLD_INK
    LOOK['title'] = TITLE_FONTS.get(str(S.get('font_tajuk', 'playfair')).lower(), TITLE_FONTS['playfair'])
    LOOK['body'] = BODY_FONTS.get(str(S.get('font_teks', 'montserrat')).lower(), 'Montserrat.ttf')
    kc = str(S.get('warna_kad', 'krim')).lower(); CREAM = CARD_COLOURS.get(kc) or theme._rgb(kc)
    hc = str(S.get('warna_huruf', 'auto')).lower()
    if hc == 'auto': INK = (30, 42, 29) if theme.lum(CREAM) > 0.5 else (250, 248, 242)
    else: INK = {'hitam': (25, 25, 25), 'putih': (255, 255, 255)}.get(hc) or theme._rgb(hc)
    dark_text = theme.lum(INK) < 0.5
    BODY = tuple(int(c * 0.85 + (38 if dark_text else 235) * 0.15) for c in INK); BOLD_INK = INK
def ease(x, p=3): x = min(1, max(0, x)); return 1 - (1 - x) ** p
def expo(x): x = min(1, max(0, x)); return 1 - 2 ** (-10 * x) if x < 1 else 1

def runs(text):
    """'a **b** c' -> [('a ', False), ('b', True), (' c', False)]"""
    out = []; parts = re.split(r'(\*\*[^*]+\*\*)', text)
    for p in parts:
        if p.startswith('**') and p.endswith('**'): out.append((p[2:-2], True))
        elif p: out.append((p, False))
    return out
def wrap(text, width, sz):
    """Word-wrap with bold runs; returns lines of [(word, bold)]."""
    words = [(w, b) for t, b in runs(text) for w in t.split(' ') if w]
    lines, cur, cw = [], [], 0
    for w, b in words:
        f = sans(sz, 'ExtraBold' if b else 'Medium'); ww = f.getlength(w + ' ')
        if cur and cw + ww > width: lines.append(cur); cur, cw = [], 0
        cur.append((w, b)); cw += ww
    if cur: lines.append(cur)
    return lines

def block_img(name, body, inner_w, k):
    """One step: serif name with a marker stroke behind it (drawn separately so it can grow) + body text."""
    nsz = int(42 * k); bsz = int(31 * k); lh = int(bsz * 1.42)
    lines = wrap(body, inner_w, bsz) if body else []
    h = int(nsz * 1.25) + (int(8 * k) + lh * len(lines) if lines else 0)
    im = Image.new('RGBA', (inner_w, h + 6), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    nf = serif(nsz); nw = nf.getlength(name)
    d.text((0, nsz * 0.62), name, font=nf, fill=INK + (255,), anchor='lm')
    y = int(nsz * 1.25) + int(8 * k)
    for ln in lines:
        x = 0
        for w, b in ln:
            f = sans(bsz, 'ExtraBold' if b else 'Medium'); d.text((x, y + lh / 2), w, font=f, fill=(BOLD_INK if b else BODY) + (255,), anchor='lm'); x += f.getlength(w + ' ')
        y += lh
    return im, nw, nsz

def marker(w, h, col):
    m = Image.new('RGBA', (int(w) + 16, int(h)), (0, 0, 0, 0)); d = ImageDraw.Draw(m)
    W_, H_ = m.size; pts = [(3, H_ * .25), (W_ * .13, H_ * .1), (W_ * .4, H_ * .3), (W_ * .7, H_ * .15), (W_ * .95, H_ * .2), (W_ - 3, H_ * .2),
                            (W_ - 4, H_ * .85), (W_ * .83, H_ * .95), (W_ * .5, H_ * .75), (W_ * .23, H_ * .9), (W_ * .05, H_ * .85), (4, H_ * .82)]
    d.polygon(pts, fill=col + (170,)); return m

def bookmark(sz, col):
    im = Image.new('RGBA', (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(sz * .2, sz * .08), (sz * .8, sz * .08), (sz * .8, sz * .92), (sz * .5, sz * .7), (sz * .2, sz * .92)], fill=col + (255,)); return im

def broll_frames(spec, total, base_dir):
    src = spec['broll'] if os.path.isabs(spec['broll']) else os.path.join(base_dir, spec['broll'])
    grade = "eq=contrast=1.05:saturation=1.06,unsharp=5:5:0.3"
    cover = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    if src.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.heic')):   # photo: slow push-in (Ken Burns)
        n = int(total * FPS)
        vf = f"{cover},scale={W * 2}:{H * 2},zoompan=z='1+0.08*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS},{grade}"
        cmd = ['ffmpeg', '-v', 'error', '-loop', '1', '-i', src, '-vf', vf, '-frames:v', str(n), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    else:
        cmd = ['ffmpeg', '-v', 'error', '-stream_loop', '-1', '-i', src, '-t', f'{total:.3f}', '-vf', f'{cover},fps={FPS},{grade}',
               '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    return subprocess.Popen(cmd, stdout=subprocess.PIPE)

def main():
    spec_path, out = sys.argv[1], sys.argv[2]; base_dir = os.path.dirname(os.path.abspath(spec_path))
    S = json.load(open(spec_path)); preview = float(sys.argv[sys.argv.index('--preview') + 1]) if '--preview' in sys.argv else None
    prof = S.get('profile'); prof = prof if prof is None or os.path.isabs(prof) else os.path.join(base_dir, prof)
    theme.apply(prof if prof and os.path.exists(prof) else None); setup_look(S)
    # timing: title, then one step every ~3.2 s, close, pill; explicit times win
    t_title = S.get('title_at', 0.7); steps = [list(s) for s in S.get('steps', [])]; t = t_title + 2.7
    for s in steps:
        if len(s) < 3: s.append(t)
        t = s[2] + 3.2
    close = list(S['close']) if S.get('close') else None
    if close and len(close) < 3: close.append(t)
    t_pill = (S['pill'][2] if len(S.get('pill', [])) > 2 else (close[2] if close else t) + 4.0) if (S.get('pill') and S.get('show_pill', False)) else None
    full_total = S.get('total') or ((t_pill or t) + 5.3); total = min(full_total, preview) if preview else full_total
    # layout: card 840 wide, fonts shrink until everything fits above the bottom UI zone
    cx, cy, cw = 100, 346, 840; pad = 52; inner = cw - 2 * pad
    for k in [x / 100 for x in range(100, 59, -4)]:
        tsz = int(43 * k); tl = wrap(S['title'], inner, tsz); tf = serif(tsz)
        t_lines = []; cur = ''
        for w in S['title'].split():
            if cur and tf.getlength(cur + ' ' + w) > inner: t_lines.append(cur); cur = w
            else: cur = (cur + ' ' + w).strip()
        t_lines.append(cur); title_h = int(tsz * 1.18) * len(t_lines)
        blocks = [block_img(n, b, inner, k) for n, b, _ in steps] + ([block_img(close[0], close[1], inner, k)] if close else [])
        gap = int(49 * k); ch = pad - 8 + title_h + sum(gap + im.height for im, _, _ in blocks) + pad - 10
        if cy + ch <= 1490: break
    times = [s[2] for s in steps] + ([close[2]] if close else [])
    title_im = Image.new('RGBA', (inner, title_h + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(title_im)
    for i, ln in enumerate(t_lines): d.text((0, i * int(tsz * 1.18) + tsz * 0.6), ln, font=tf, fill=INK + (255,), anchor='lm')
    mk_col = tuple(int(c * 0.75 + 255 * 0.25) for c in theme.A) if theme.lum(INK) < 0.5 else tuple(int(c * 0.7) for c in theme.DARK)   # light text: darker marker keeps contrast
    blob = Image.new('RGBA', (330, 260), (0, 0, 0, 0)); ImageDraw.Draw(blob).polygon([(60, 0), (230, 12), (330, 90), (300, 200), (210, 240), (150, 150), (20, 55)], fill=theme.DARK + (34,))
    blob = blob.filter(ImageFilter.GaussianBlur(6))
    mask = Image.new('L', (cw, ch), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, cw - 1, ch - 1), 38, fill=255)
    # pill
    pill = None
    if S.get('pill') and S.get('show_pill', False):
        pw, ph = 840, 120; pill = Image.new('RGBA', (pw + 80, ph + 80), (0, 0, 0, 0)); g = np.linspace(0, 1, ph)[:, None]
        cols = np.array(theme.LIGHT) * (1 - g[..., None]) + np.array(theme.DARK) * g[..., None]; cols = np.repeat(cols, pw, axis=1).astype(np.uint8)
        body = Image.fromarray(cols).convert('RGBA'); body.putalpha(Image.new('L', (pw, ph), 0)); m_ = Image.new('L', (pw, ph), 0); ImageDraw.Draw(m_).rounded_rectangle((0, 0, pw - 1, ph - 1), 36, fill=255); body.putalpha(m_)
        glow = Image.new('RGBA', pill.size, (0, 0, 0, 0)); ImageDraw.Draw(glow).rounded_rectangle((40, 52, 40 + pw, 52 + ph), 36, fill=(0, 0, 0, 70)); pill.alpha_composite(glow.filter(ImageFilter.GaussianBlur(18)))
        pill.alpha_composite(body, (40, 40)); dp = ImageDraw.Draw(pill)
        pill.alpha_composite(bookmark(64, theme.ON if theme.lum(theme.A) <= 0.55 else (40, 30, 10)), (70, 40 + (ph - 64) // 2))
        f1 = sans(32, 'Black'); f2 = sans(25, 'Bold'); tx = 160
        while f1.getlength(S['pill'][0]) > pw - 150: f1 = sans(f1.size - 2, 'Black')
        dp.text((tx, 40 + ph * 0.36), S['pill'][0], font=f1, fill=theme.ON + (255,), anchor='lm')
        dp.text((tx, 40 + ph * 0.7), S['pill'][1], font=f2, fill=theme.ON + (230,), anchor='lm')
    # render
    work = os.path.join('/tmp', 'gac_nota'); os.makedirs(work, exist_ok=True)
    dec = broll_frames(S, total, base_dir)
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', f'{work}/v.mp4'], stdin=subprocess.PIPE)
    n = int(round(total * FPS)); last = None
    still = os.path.join('/tmp', os.path.basename(out).rsplit('.', 1)[0] + '_kad_penuh.jpg') if preview else None
    for k_ in range(n + (1 if preview else 0)):   # preview: one extra frame = the finished card, as a still
        t = k_ / FPS if k_ < n else full_total - 1.0
        buf = dec.stdout.read(W * H * 3) if k_ < n else last
        if len(buf) < W * H * 3: buf = last
        last = buf; fr = Image.frombytes('RGB', (W, H), buf).convert('RGBA')
        ca = ease((t - 0.1) / 0.9); cyy = cy + 40 * (1 - ca)
        if ca > 0:
            sh = Image.new('RGBA', (cw + 200, ch + 200), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((100, 130, 100 + cw, 130 + ch), 38, fill=(0, 0, 0, int(40 * ca)))
            fr.alpha_composite(sh.filter(ImageFilter.GaussianBlur(40)), (cx - 100, int(cyy) - 100))
            reg = fr.crop((cx, int(cyy), cx + cw, int(cyy) + ch)).convert('RGB').filter(ImageFilter.GaussianBlur(S.get('blur', 9)))
            card = Image.blend(reg, Image.new('RGB', (cw, ch), CREAM), S.get('tint', 0.30 if theme.lum(CREAM) > 0.5 else 0.45)).convert('RGBA')   # see-through: the scenery shows
            card.alpha_composite(blob, (cw - 330 + 30, -40))
            dc = ImageDraw.Draw(card); dc.rounded_rectangle((0, 0, cw - 1, ch - 1), 38, outline=(255, 255, 255, 153), width=2)
            y = pad - 8
            def reveal(im, at, y, extra=None):
                p = ease((t - at) / 0.75)
                if p <= 0: return
                if extra: extra(p)
                im2 = im.copy(); im2.putalpha(im2.getchannel('A').point(lambda v: int(v * p))); card.alpha_composite(im2, (pad, int(y + 26 * (1 - p))))
            reveal(title_im, t_title, y); y += title_h
            for (im, nw, nsz), at in zip(blocks, times):
                hp = ease((t - at) / 0.6)
                if hp > 0: dc.line((pad, y + gap / 2, cw - pad, y + gap / 2), fill=INK + (int(51 * hp),), width=2)
                y += gap
                mp = ease((t - at - 0.35) / 0.6, 2)
                if mp > 0 and t >= at:
                    mk = marker(nw * mp, nsz * 0.66, mk_col); card.alpha_composite(mk, (pad - 4, int(y + nsz * 0.30)))
                reveal(im, at, y); y += im.height
            card.putalpha(Image.eval(mask, lambda v: int(v * ca)))
            fr.alpha_composite(card, (cx, int(cyy)))
        if pill is not None and t >= t_pill:
            p = expo((t - t_pill) / 0.7); sc = 0.94 + 0.06 * p
            im = pill.resize((int(pill.width * sc), int(pill.height * sc)), Image.LANCZOS); im.putalpha(im.getchannel('A').point(lambda v: int(v * min(1, p * 1.4))))
            fr.alpha_composite(im, (int(W / 2 - im.width / 2), int(222 - 40 - 40 * (1 - p) + (pill.height - im.height) / 2)))
        if k_ == n: fr.convert('RGB').save(still, quality=90); break
        enc.stdin.write(fr.convert('RGB').tobytes())
    enc.stdin.close(); enc.wait(); dec.kill()
    ev = [(0.25, 'whoosh'), (t_title, 'pop')] + [(x, 'pop') for x in times] + ([(t_pill, 'shimmer')] if t_pill else [])
    sfx.render_track([e for e in ev if e[0] < total] if S.get('sfx', False) else [], total, f'{work}/sfx.wav', -9)   # default: silent (music added on TikTok)
    ins = ['-i', f'{work}/v.mp4', '-i', f'{work}/sfx.wav']; fc = '[1:a]anull[ao]'
    if S.get('audio'):
        au = S['audio'] if os.path.isabs(S['audio']) else os.path.join(base_dir, S['audio'])
        ins += ['-i', au]; fc = f"[2:a]volume={S.get('audio_gain', 1.0)}[m];[1:a][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[ao]"
    subprocess.run(['ffmpeg', '-v', 'error', '-y'] + ins + ['-filter_complex', fc, '-map', '0:v', '-map', '[ao]', '-t', f'{total:.3f}',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out], check=True)
    sheet = os.path.join('/tmp', os.path.basename(out).rsplit('.', 1)[0] + '_frames.jpg')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', out, '-vf', 'fps=1,scale=180:-1,tile=10x4', '-frames:v', '1', sheet])
    print(json.dumps(dict(out=out, duration=round(total, 2), full_duration=round(full_total, 2), full_card_still=still, font_scale=k, card=[cx, cy, cw, ch], steps_at=times, pill_at=t_pill, frames_sheet=sheet), indent=1))
if __name__ == '__main__': main()
