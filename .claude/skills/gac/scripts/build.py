#!/usr/bin/env python3
"""Build a styled portrait (1080x1920) or landscape (1920x1080) video from a timeline JSON.
Usage: python3 build.py timeline.json OUT.mp4 [--preview SECONDS]
All element times in the timeline are ORIGINAL video times (as read from the
raw video / SRT). The script maps them onto the cut timeline itself.
See ../references/timeline.md for the full format."""
import sys, os, json, math, subprocess, re, shutil, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(__file__)); import sfx, doc as docmod, theme as gtheme, gaya, mewah

W, H, FPS = 1080, 1920, 30
QA_HITS = {}   # safe-zone hits found while drawing overlays: zone -> [times]
CUT_WORDS = None   # Whisper word list for the cut check, set in main() when the timeline has one          # W/H are switched to 1920x1080 for landscape in main()
FONTS = [('/System/Library/Fonts/Avenir Next.ttc', 0), ('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 0),
         ('/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf', 0), ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 0)]
FONT, FONT_IDX = next(((p, i) for p, i in FONTS if os.path.exists(p)), (None, 0))
COL = dict(white=(255,255,255), yellow=(255,212,59), green=(57,255,120), red=(255,59,59),
           gold=(247,178,40), black=(0,0,0))
def C(c): return COL.get(c, c) if isinstance(c, str) else tuple(c)
_FC = {}
def font(sz):   # display text (big words, cards): house font Montserrat Black, Avenir as fallback
    if sz not in _FC: _FC[sz] = docmod._font(docmod.HEAVY, sz)
    return _FC[sz]
def DY(v): return v * H / 1920      # default y positions are designed for 1920-tall portrait
def parse_srt(path):
    """[[start, end, text], ...] from an .srt file (CapCut export)."""
    def ts(s): h, m, r = s.replace(',', '.').split(':'); return int(h) * 3600 + int(m) * 60 + float(r)
    out = []
    for blk in re.split(r'\n\s*\n', open(path, encoding='utf-8-sig').read().strip()):
        ls = [l for l in blk.strip().splitlines() if l.strip()]
        i = next((k for k, l in enumerate(ls) if '-->' in l), None)
        if i is None: continue
        a, b = [ts(x.strip()) for x in ls[i].split('-->')]
        out.append([round(a, 3), round(b, 3), ' '.join(ls[i + 1:])])
    return out

def face_center(src, t, cache={}):
    """(fx, fy) of the largest face at time t, as fractions of the frame; (0.5, 0.35) if none."""
    k = (src, round(t, 1))
    if k in cache: return cache[k]
    import cv2
    p = os.path.join(tempfile.gettempdir(), '_face.png')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', src, '-frames:v', '1', '-vf', 'scale=640:-2', p])
    img = cv2.imread(p); res = (0.5, 0.35)
    if img is not None:
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        fc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        f = fc.detectMultiScale(g, 1.1, 5, minSize=(40, 40))
        if len(f):
            x, y, w, h = max(f, key=lambda r: r[2] * r[3]); res = ((x + w / 2) / img.shape[1], (y + h / 2) / img.shape[0])
    cache[k] = res; return res

def face_box(video, t):
    """(top of hair, chin) canvas y of the largest face at time t, or None."""
    import cv2
    p = os.path.join(tempfile.gettempdir(), '_fb.png')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', video, '-frames:v', '1', '-vf', 'scale=540:-2', p])
    img = cv2.imread(p)
    if img is None: return None
    fc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    f = fc.detectMultiScale(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 1.1, 5, minSize=(60, 60))
    if not len(f): return None
    x, y, w, h = max(f, key=lambda r: r[2] * r[3]); k = W / img.shape[1]
    return (y - h * 0.32) * k, (y + h * 1.05) * k

def frame_filter(src, sw, sh, t, box_w, box_h, z, face_y=0.38, span=None):
    """ffmpeg scale+crop that fills a box_w x box_h window from the source (no stretching),
    zoomed by z and positioned so the face sits at face_y of the window height."""
    s = max(box_w / sw, box_h / sh) * z; tw, th = int(sw * s) // 2 * 2, int(sh * s) // 2 * 2
    if span:  # median of three samples, so one odd frame does not throw the crop off
        a, b = span; pts = [face_center(src, a + (b - a) * f) for f in (0.2, 0.5, 0.8)]
        fx, fy = sorted(p[0] for p in pts)[1], sorted(p[1] for p in pts)[1]
    else: fx, fy = face_center(src, t)
    x = min(max(0, fx * tw - box_w / 2), tw - box_w); y = min(max(0, fy * th - box_h * face_y), th - box_h)
    return f'scale={tw}:{th},crop={box_w}:{box_h}:{int(x)}:{int(y)}'
def run(cmd): r = subprocess.run(cmd, capture_output=True, text=True); \
    (r.returncode == 0) or sys.exit('FFMPEG FAILED:\n' + ' '.join(cmd)[:400] + '\n' + r.stderr[-1500:]); return r

# ---------------------------------------------------------------- cutting
def person_mask(img):
    """Best-effort person mask (OpenCV GrabCut seeded by face detection). Returns
    uint8 mask or None when it looks unreliable. Works best on plain backgrounds."""
    import cv2
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    fc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    f = fc.detectMultiScale(g, 1.1, 5, minSize=(120, 120))
    if len(f) == 0: return None
    s = 0.4; sm = cv2.resize(img, None, fx=s, fy=s); hh, ww = sm.shape[:2]
    x, y, w, h = [int(v * s) for v in max(f, key=lambda r: r[2] * r[3])]
    m = np.full((hh, ww), cv2.GC_PR_BGD, np.uint8)
    m[max(0, y - int(h * .5)):, max(0, x - int(w * 1.2)):min(ww, x + w + int(w * 1.2))] = cv2.GC_PR_FGD
    m[y:y + h, x + w // 6:x + w - w // 6] = cv2.GC_FGD
    m[:, :int(ww * .03)] = cv2.GC_BGD; m[:, int(ww * .97):] = cv2.GC_BGD
    m[:max(1, y - int(h * .8)), :] = cv2.GC_BGD
    bg, fg = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(sm, m, None, bg, fg, 5, cv2.GC_INIT_WITH_MASK)
    out = np.where((m == 1) | (m == 3), 255, 0).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(out)
    if n > 1: out = np.where(lab == 1 + np.argmax(st[1:, 4]), 255, 0).astype(np.uint8)
    out = cv2.morphologyEx(out, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    out = cv2.resize(out, (img.shape[1], img.shape[0]))
    frac = out.mean() / 255
    return out if 0.12 < frac < 0.75 else None

def freeze_card(png_in, png_out, text, color, outline=False, text_y=None):
    import cv2
    img = cv2.imread(png_in); m = person_mask(img) if outline else None
    base = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).convert('RGBA')
    dim = Image.new('RGBA', base.size, (0, 0, 0, 150))
    if m is not None:
        person = base.copy(); person.putalpha(Image.fromarray(m))
        ring = Image.fromarray(cv2.dilate(m, np.ones((19, 19), np.uint8)))
        outline = Image.new('RGBA', base.size, (255, 255, 255, 0)); outline.putalpha(ring)
        bgd = Image.alpha_composite(base, dim)
        # big text BEHIND the person (text-behind-subject)
        bgd = Image.alpha_composite(bgd, place(text_block([[(text, color)]], 150, glow=True), W / 2, text_y or DY(330), fit=0.94))
        bgd = Image.alpha_composite(bgd, outline)
        out = Image.alpha_composite(bgd, person)
    else:
        out = Image.alpha_composite(base, dim)
        out = Image.alpha_composite(out, place(text_block([[(text, color)]], 140, glow=True), W / 2, text_y or DY(330), fit=0.94))
    out.convert('RGB').save(png_out)
    return m is not None

def src_info(src):
    p = os.path.join(tempfile.gettempdir(), '_probe.png')
    run(['ffmpeg', '-v', 'error', '-y', '-ss', '0.5', '-i', src, '-frames:v', '1', p])
    sw, sh = Image.open(p).size
    has_a = 'audio' in subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', src],
                                      capture_output=True, text=True).stdout
    return sw, sh, has_a

def rel_times(spec, a):
    """Scene specs use ORIGINAL video times in every "at"/"*_at" key; make them scene-relative."""
    if isinstance(spec, dict):
        def conv(k, v):
            if k == 'at' or k.endswith('_at'):
                if isinstance(v, (int, float)): return round(v - a, 3)
                if isinstance(v, list) and all(isinstance(x, (int, float)) for x in v): return [round(x - a, 3) for x in v]
            return rel_times(v, a)
        return {k: conv(k, v) for k, v in spec.items()}
    if isinstance(spec, list): return [rel_times(v, a) for v in spec]
    return spec

def is_hdr(src):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=color_transfer,color_primaries',
                        '-of', 'csv=p=0', src], capture_output=True, text=True).stdout
    return any(k in r for k in ('arib-std-b67', 'smpte2084', 'bt2020'))

def auto_wb_gains(src):
    """Per-channel gains that make the bright neutral areas (walls, shirts, tables) grey instead of tinted."""
    p = os.path.join(tempfile.gettempdir(), '_wb.png'); dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout or 2)
    vf = 'scale=540:-2' + (',scale=in_color_matrix=bt2020:out_color_matrix=bt709' if is_hdr(src) else '')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{dur * 0.4:.2f}', '-i', src, '-frames:v', '1', '-vf', vf, p])
    a = np.asarray(Image.open(p).convert('RGB')).astype(float); l = a.mean(2)
    hi = a[(l > np.percentile(l, 70)) & (l < np.percentile(l, 99))]
    m = hi.mean(0) if len(hi) else np.array([1.0, 1, 1]); return np.clip(m.mean() / m, 0.88, 1.15)

def check_cut_audio(src, segs, words=None, quiet=-30.0, min_gap=0.10):
    """Warn when a cut is not inside a real pause. A cut must sit in a run of at least `min_gap` seconds
    below `quiet` dB (a 50 ms dip between two syllables, as in "tu-run", does not count), and, when a
    Whisper word list is given, must not fall inside a word (with a 60 ms margin).
    Only cut points that are not joined to the neighbouring segment are checked."""
    clips = [s for s in segs if not isinstance(s, dict)]
    try: src_end = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout)
    except ValueError: src_end = 1e9
    def run_below(t0):
        a = max(0.0, t0 - 0.30)
        r = subprocess.run(['ffmpeg', '-hide_banner', '-ss', f'{a:.3f}', '-t', '0.6', '-i', src, '-af',
                            'asetnsamples=n=480,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level',
                            '-f', 'null', '-'], capture_output=True, text=True).stderr
        ts = [a + float(x) for x in re.findall(r'pts_time:([\d.]+)', r)]
        lv = [(-99.0 if v == '-inf' else float(v)) for v in re.findall(r'RMS_level=(-?[\d.]+|-inf)', r)]
        if not ts: return 0.0
        k = min(range(len(ts)), key=lambda q: abs(ts[q] - t0))
        if lv[k] > quiet: return 0.0
        lo = hi = k
        while lo > 0 and lv[lo - 1] <= quiet: lo -= 1
        while hi + 1 < len(lv) and lv[hi + 1] <= quiet: hi += 1
        return ts[hi] - ts[lo] + 0.01
    def in_word(t0):
        for w in words or []:
            if w['s'] + 0.06 < t0 < w['e'] - 0.06: return w['w']
        return None
    for i, s in enumerate(clips):
        a, b = s[0], s[1]
        for t0, joined in ((b, i + 1 < len(clips) and abs(clips[i + 1][0] - b) <= 0.05),
                           (a, i > 0 and abs(clips[i - 1][1] - a) <= 0.05)):
            if joined or t0 < 0.1 or t0 >= src_end - 0.12: continue   # start/end of the file itself is not a cut
            gap = run_below(t0)
            if gap < min_gap:   # audio decides; Whisper word spans often include pauses, so a word name is only a hint
                w = in_word(t0); why = f'only {gap * 1000:.0f} ms of quiet' + (f', near the word "{w}"' if w else '')
                print(f'WARNING cut at {t0:.2f}s is not in a real pause ({why}): a word may be clipped', file=sys.stderr)

def cut(src, segs, work, enhance=True, split_box=None, doc_bg=docmod.BG, scenes=None, icons_dir=None,
        look=None, push=0.0, soft=False):
    """Cut + zoom every segment to W x H. A segment whose 4th item is "split" shows the
    face in split_box (x, y, w, h) and paints the rest with the document colour."""
    lst = open(f'{work}/list.txt', 'w'); M = []; t = 0.0; freeze_ok = []
    sw, sh, has_a = src_info(src)
    if has_a: check_cut_audio(src, segs, CUT_WORDS)
    grade = ("hqdn3d=1.5:1.5:4:4,eq=contrast=1.06:saturation=1.10:brightness=0.015:gamma=1.03,"
             "unsharp=5:5:0.45") if enhance else "null"
    if look in (None, 'asli', 'original'): grade = "null"   # GAC default: keep the phone's own colours (only HDR is converted below)
    if look == 'bright':     # dim indoor/shop footage: lift exposure, warm skin, richer colour, crisp, soft vignette
        grade = ("hqdn3d=2:2:5:5,eq=contrast=1.06:saturation=1.10:brightness=0.02:gamma=1.10,"
                 "colorbalance=rs=0.04:gs=0.01:bs=-0.03:rm=0.03:bm=-0.02,"
                 "curves=master='0/0.02 0.25/0.27 0.5/0.55 0.8/0.84 1/0.97',vignette=PI/6,unsharp=5:5:0.6")
    if look == 'cinematic':  # warm, gently contrasted, dark edges and fine grain: matches the black + gold scenes
        grade = ("hqdn3d=1.5:1.5:4:4,eq=contrast=1.10:saturation=1.04:brightness=-0.02:gamma=0.98,"
                 "colorbalance=rs=0.05:gs=0.01:bs=-0.05:rm=0.03:bm=-0.03:rh=0.02:bh=-0.04,"
                 "curves=preset=medium_contrast,vignette=PI/4.5,unsharp=5:5:0.4,noise=alls=5:allf=t")
    if look == 'premium':    # neutral premium (default, user's pick 2026-10-16): auto white balance so whites stay white,
        # deep but clean contrast, cool-neutral shadows, soft vignette, fine grain - no yellow/orange push
        g = auto_wb_gains(src)
        grade = (f"colorchannelmixer=rr={g[0]:.3f}:gg={g[1]:.3f}:bb={g[2]:.3f},hqdn3d=1.5:1.5:4:4,"
                 "eq=contrast=1.06:saturation=1.08:gamma=1.04,colorbalance=rs=-0.015:bs=0.02:rm=0.01,"
                 "curves=master='0/0.02 0.25/0.25 0.5/0.53 0.75/0.81 1/0.99',vignette=PI/8,unsharp=5:5:0.45,noise=alls=3:allf=t")
    if look == 'warm':       # Gaya 1: warm cream/peach, low saturation, soft highlights
        grade = gaya.warm_grade()
    if look == 'studio':     # white studio (keyed green screen): no auto-WB dimming, no vignette, a touch brighter so the wall stays white
        grade = ("hqdn3d=1.5:1.5:4:4,eq=contrast=1.03,"      # eq saturation/gamma tint a white wall green: keep to contrast only
                 "unsharp=5:5:0.4,noise=alls=2:allf=t")
    if is_hdr(src):          # iPhone HDR (HLG/PQ, BT.2020): convert the colour matrix first, or everything turns dull and yellow
        grade = "scale=in_color_matrix=bt2020:out_color_matrix=bt709,format=yuv420p," + grade
    kinds = [('scene' if (not isinstance(x, dict) and len(x) > 3 and str(x[3]).startswith('scene:')) else 'face') for x in segs]
    bgc = '0x%02X%02X%02X' % doc_bg
    for i, s in enumerate(segs):
        out = f'{work}/seg{i:02d}.mov'
        if isinstance(s, dict) and 'freeze' in s:
            z = s.get('zoom', 1.0); fr = f'{work}/fz{i}.png'; fo = f'{work}/fz{i}_card.png'
            run(['ffmpeg','-v','error','-y','-ss',str(s['freeze']),'-i',src,'-frames:v','1','-vf',
                 f"{frame_filter(src, sw, sh, s['freeze'], W, H, z)},{grade}",fr])
            freeze_ok.append(freeze_card(fr, fo, s.get('text', ''), C(s.get('color', 'yellow')), s.get('outline', False), s.get('text_y')))
            d = float(s.get('dur', 1.0))
            run(['ffmpeg','-v','error','-y','-loop','1','-i',fo,'-f','lavfi','-i','anullsrc=r=48000:cl=mono',
                 '-t',f'{d:.3f}','-vf','fps=30,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','17',
                 '-c:a','pcm_s16le','-ar','48000',out])
            M.append(dict(kind='freeze', at=s['freeze'], new=t, dur=d, layout='full'))
        else:
            a, b = s[0], s[1]; z = s[2] if len(s) > 2 else 1.0; lay = s[3] if len(s) > 3 else 'full'; d = b - a
            mid = a + d / 2
            if lay == 'split' and split_box:
                bx, by, bw, bh = split_box
                vf = f'{frame_filter(src, sw, sh, mid, bw, bh, z, 0.45, (a, b))},pad={W}:{H}:{bx}:{by}:color={bgc},{grade},fps=30'
            else:
                vf = f'{frame_filter(src, sw, sh, mid, W, H, z, 0.38, (a, b))},{grade},fps=30'
                if push:  # slow continuous push-in instead of a static frame
                    nf = max(2, int(d * 30))
                    vf += (f",scale={W * 2}:{H * 2},zoompan=z='{z:.3f}/{z:.3f}+{push}*on/{nf}':d=1:x='iw/2-(iw/zoom/2)'"
                           f":y='ih*0.40-(ih/zoom*0.40)':s={W}x{H}:fps=30")
                if soft:  # blur-dip into / out of motion scenes
                    if i + 1 < len(segs) and kinds[i + 1] == 'scene':
                        vf += f",boxblur=12:1:enable='gte(t,{d - 0.28:.3f})',fade=t=out:st={d - 0.28:.3f}:d=0.28"
                    if i > 0 and kinds[i - 1] == 'scene':
                        vf += ",boxblur=12:1:enable='lte(t,0.22)',fade=t=in:st=0:d=0.22"
            if has_a:
                ain = ['-ss', str(a), '-i', src]; amap = []
                af = f'afade=t=in:d=0.03,afade=t=out:st={d - 0.04:.3f}:d=0.04,aresample=48000'
            else:
                ain = ['-ss', str(a), '-i', src, '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=mono']; amap = ['-map', '0:v', '-map', '1:a']
                af = 'aresample=48000'
            ev = []
            if isinstance(lay, str) and lay.startswith('scene:'):
                # Gaku-style motion scene replaces the picture; the speaker's audio carries on underneath
                import motion
                spec = rel_times(dict((scenes or {})[lay[6:]]), a); hold = float(spec.get('hold', 0))
                spec['dur'] = d + hold; spec['icons_dir'] = icons_dir    # "hold": keep the scene on screen after the speech ends
                if spec.get('backdrop') == 'video':
                    # scene over the speaker's own footage: blurred (bokeh) and 50% black, voice untouched
                    fdir = f'{work}/scene{i:02d}_f'; os.makedirs(fdir, exist_ok=True)
                    ev = motion.render_frames(spec, fdir, W, H)
                    dim = spec.get('dim', 0.5); blur = spec.get('blur', 26)
                    bvf = (f'{frame_filter(src, sw, sh, mid, W, H, z, 0.38, (a, b))},{grade},fps=30'
                           + (f',gblur=sigma={blur}:steps=2' if blur else '') + f',drawbox=x=0:y=0:w=iw:h=ih:color=black@{dim}:t=fill'
                           + (f',tpad=stop_mode=clone:stop_duration={hold:.3f}' if hold else ''))   # "hold": freeze the bokeh after the speech
                    ain3 = ['-ss', str(a), '-t', f'{d:.3f}', '-i', src] + ([] if has_a else ['-f', 'lavfi', '-t', f'{d:.3f}', '-i', 'anullsrc=r=48000:cl=mono'])
                    amap3 = ['-map', '0:a'] if has_a else ['-map', '2:a']
                    run(['ffmpeg', '-v', 'error', '-y'] + ain3[:6] + ['-framerate', '30', '-i', f'{fdir}/f_%05d.png'] + ain3[6:] +
                        ['-filter_complex', f'[0:v]{bvf}[bk];[bk][1:v]overlay=eof_action=pass,format=yuv420p[vo]', '-map', '[vo]'] + amap3 +
                        ['-t', f'{d + hold:.3f}', '-af', af + (',apad' if hold else ''), '-ac', '1', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-c:a', 'pcm_s16le', out])
                    M.append(dict(kind='clip', a=a, b=b, new=t, layout='scene', events=ev))
                    dd = float(run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',out]).stdout)
                    M[-1]['len'] = dd; t += dd; lst.write(f"file '{os.path.basename(out)}'\n"); continue
                sv = f'{work}/scene{i:02d}.mp4'; ev = motion.render_silent(spec, sv, W, H)
                vin = ['-i', sv]; vmap = ['-map', '0:v']
                if has_a: ain2 = ['-ss', str(a), '-t', f'{d:.3f}', '-i', src]
                else: ain2 = ['-f', 'lavfi', '-t', f'{d:.3f}', '-i', 'anullsrc=r=48000:cl=mono']
                run(['ffmpeg','-v','error','-y'] + vin + ain2 + vmap + ['-map','1:a','-t',f'{d + hold:.3f}','-af',af + (',apad' if hold else ''),'-ac','1',
                     '-vf','fps=30','-c:v','libx264','-preset','veryfast','-crf','17','-pix_fmt','yuv420p','-c:a','pcm_s16le',out])
                lay = 'scene'
            else:
                run(['ffmpeg','-v','error','-y'] + ain + ['-t',f'{d:.3f}','-vf',vf,'-af',af,'-ac','1'] + amap +
                    ['-c:v','libx264','-preset','veryfast','-crf','17','-pix_fmt','yuv420p','-c:a','pcm_s16le',out])
            M.append(dict(kind='clip', a=a, b=b, new=t, layout=lay, events=ev))
        d = float(run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',out]).stdout)
        M[-1]['len'] = d; t += d; lst.write(f"file '{os.path.basename(out)}'\n")
    lst.close()
    run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',f'{work}/list.txt','-c:v','copy',
         '-af','loudnorm=I=-14:TP=-1.5:LRA=11' if has_a else 'anull','-c:a','pcm_s16le','-ar','48000',f'{work}/base.mov'])
    return M, t, freeze_ok

def mapper(M, total):
    clips = [m for m in M if m['kind'] == 'clip']
    def N(o):
        for m in clips:
            if m['a'] - 0.02 <= o <= m['b'] + 0.02: return m['new'] + min(max(0, o - m['a']), m['len'])
        nxt = [m for m in clips if m['a'] > o]
        return nxt[0]['new'] if nxt else total
    return N

# ---------------------------------------------------------------- drawing
def text_block(lines, sz, glow=False, stroke=10):
    f = font(sz); widths = [sum(f.getlength(t) for t, _ in ln) for ln in lines]
    lh = int(sz * 1.12); w = int(max(widths)) + 120; h = lh * len(lines) + 80
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    gl = Image.new('RGBA', (w, h), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
    for i, ln in enumerate(lines):
        x = (w - widths[i]) / 2; y = 40 + i * lh
        for t, c in ln:
            c = C(c); d.text((x, y), t, font=f, fill=c, stroke_width=stroke, stroke_fill=(0, 0, 0))
            if glow: gd.text((x, y), t, font=f, fill=c)
            x += f.getlength(t)
    if glow:
        g1 = gl.filter(ImageFilter.GaussianBlur(14)); g2 = gl.filter(ImageFilter.GaussianBlur(30))
        im = Image.alpha_composite(Image.alpha_composite(Image.alpha_composite(g2, g1), g1), im)
    return im
def clean_text(lines, sz):
    """Iman-style hook text: white, no outline, soft drop shadow."""
    f = font(sz); widths = [sum(f.getlength(t) for t, _ in ln) for ln in lines]
    lh = int(sz * 1.15); w = int(max(widths)) + 80; h = lh * len(lines) + 60
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); sh = im.copy(); d, ds = ImageDraw.Draw(im), ImageDraw.Draw(sh)
    for i, ln in enumerate(lines):
        x = (w - widths[i]) / 2; y = 30 + i * lh
        for t, c in ln:
            ds.text((x + 3, y + 5), t, font=f, fill=(0, 0, 0, 150)); d.text((x, y), t, font=f, fill=C(c)); x += f.getlength(t)
    return Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)), im)
def panel(w, h, border=None, fill=(12, 12, 12, 195), r=34):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), r, fill=fill, outline=C(border) if border else None, width=6 if border else 0)
    return im
def icon(kind, sz, col):
    im = Image.new('RGBA', (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im); col = C(col); s = sz
    if kind == 'check':
        d.ellipse((0, 0, s - 1, s - 1), fill=col)
        d.line([(s*.27, s*.52), (s*.44, s*.69), (s*.75, s*.33)], fill=(0, 0, 0), width=max(4, s // 9), joint='curve')
    elif kind == 'cross':
        d.ellipse((0, 0, s - 1, s - 1), fill=col); w_ = max(4, s // 9)
        d.line([(s*.3, s*.3), (s*.7, s*.7)], fill=(0, 0, 0), width=w_); d.line([(s*.7, s*.3), (s*.3, s*.7)], fill=(0, 0, 0), width=w_)
    elif kind in ('up', 'down'):
        p = [(s*.35, s*.45), (s*.65, s*.45), (s*.65, s*.05), (s*.35, s*.05)] if False else None
        if kind == 'down': d.polygon([(s*.32, 0), (s*.68, 0), (s*.68, s*.5), (s*.95, s*.5), (s*.5, s), (s*.05, s*.5), (s*.32, s*.5)], fill=col)
        else: d.polygon([(s*.32, s), (s*.68, s), (s*.68, s*.5), (s*.95, s*.5), (s*.5, 0), (s*.05, s*.5), (s*.32, s*.5)], fill=col)
    elif kind == 'calendar':
        d.rounded_rectangle((0, s*.08, s - 1, s - 1), s // 8, fill=(255, 255, 255)); d.rectangle((0, s*.08, s - 1, s*.35), fill=col)
    elif kind == 'phone':
        d.ellipse((0, 0, s - 1, s - 1), fill=col); d.rounded_rectangle((s*.33, s*.18, s*.67, s*.82), s // 10, outline=(255, 255, 255), width=max(3, s // 16))
    elif kind == 'warning':
        d.polygon([(s/2, 0), (s, s), (0, s)], fill=col); d.text((s/2, s*.62), '!', font=font(int(s*.6)), fill=(0, 0, 0), anchor='mm')
    return im
def card(text, color='gold', ic=None, sub=None, sub_color=None, w=880):
    h = 170 if not sub else 250; im = panel(w, h, border=color); d = ImageDraw.Draw(im); x = 40
    if ic: im.alpha_composite(icon(ic, 110 if not sub else 140, color), (36, (h - (110 if not sub else 140)) // 2)); x = 190 if not sub else 215
    f = font(60); tw = f.getlength(text)
    while tw > w - x - 40 and f.size > 34: f = font(f.size - 2); tw = f.getlength(text)
    if sub:
        d.text((x, 45), text, font=f, fill=(255, 255, 255))
        fs = font(min(f.size, 56)); 
        while fs.getlength(sub) > w - x - 40 and fs.size > 30: fs = font(fs.size - 2)
        d.text((x, 135), sub, font=fs, fill=C(sub_color or color))
    else:
        d.text((x, h / 2), text, font=f, fill=C(color), anchor='lm')
    return im
def place(img, cx, cy, scale=1.0, alpha=1.0, fit=None):
    if fit and img.width * scale > W * fit: scale = W * fit / img.width
    if fit and H > W:   # portrait: the visible part must sit between x 125 and 955 (clear of the right-hand buttons)
        bb = img.getchannel('A').point(lambda v: 255 if v > 60 else 0).getbbox()
        if bb:
            room = 2 * min(955 - cx, cx - 125); ink = (bb[2] - bb[0]) * scale
            if room > 0 and ink > room: scale *= room / ink
    if scale != 1.0: img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
    if alpha < 1.0: a = img.getchannel('A').point(lambda v: int(v * alpha)); img = img.copy(); img.putalpha(a)
    fr = Image.new('RGBA', (W, H), (0, 0, 0, 0)); fr.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))
    return fr
def pop_scale(p):
    if p >= 1: return 1.0
    return 0.65 + 0.5 * math.sin(p / 0.7 * math.pi / 2) if p < 0.7 else 1.15 - 0.15 * (p - 0.7) / 0.3
def env(t, s, e, pop=True, fade_in=True):
    if t < s or t > e: return None
    sc = pop_scale(min(1, (t - s) / 0.25)) if pop else 1.0
    al = max(0, min(1, (t - s) / 0.12 if fade_in else 1, (e - t) / 0.15)); return sc, al

# ---------------------------------------------------------------- subtitles from a script
def script_subs(script, chunks_new, max_words=5):
    """Spread script words over speech chunks (already on the NEW timeline) by duration.
    Words wrapped in *stars* are emphasised. Returns [(start,end,[(word,emph,ws,we),...])]."""
    words = script.split(); total = sum(b - a for a, b in chunks_new)
    if not words or total <= 0: return []
    per = total / len(words); out = []; wi = 0; acc = 0.0
    timed = []
    for a, b in chunks_new:
        n = max(1, round((b - a) / per)) if wi < len(words) else 0
        n = min(n, len(words) - wi)
        if n == 0: continue
        step = (b - a) / n
        for k in range(n):
            w = words[wi]; emph = w.startswith('*') and w.rstrip('.,!?').endswith('*') and len(w) > 2
            timed.append((w.replace('*', ''), emph, a + k * step, a + (k + 1) * step)); wi += 1
    if wi < len(words) and timed:  # leftovers go on the last chunk
        a, b = timed[-1][2], timed[-1][3]
        for w in words[wi:]: timed.append((w.replace('*', ''), w.startswith('*'), a, b))
    i = 0
    while i < len(timed):
        grp = [timed[i]]; i += 1
        while i < len(timed) and len(grp) < max_words and timed[i][2] - grp[-1][3] < 0.25 and not grp[-1][0].endswith(('.', '?', '!', ',')):
            grp.append(timed[i]); i += 1
        out.append((grp[0][2], grp[-1][3], grp))
    return out
SUB_CFG = {}
def sub_frame_minimal(grp, t, y):
    """Gaku-style caption: small, white, sentence case, no outline, soft shadow; key words gold."""
    cfg = SUB_CFG   # subtitles.color / subtitles.shadow: dark captions for a white studio
    base_col = tuple(cfg.get('color', (255, 255, 255))); shadow = tuple(cfg.get('shadow', (0, 0, 0, 200)))
    words = [(w, C('gold') if emph else base_col) for w, emph, ws, we in grp]
    lines, f = minimal_layout([w for w, _ in words])
    sp = f.getlength(' '); lh = int(f.size * 1.25)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sh = im.copy(); d, ds = ImageDraw.Draw(im), ImageDraw.Draw(sh); k = 0
    for li, ln in enumerate(lines):
        tw = sum(f.getlength(w) for w in ln) + sp * (len(ln) - 1); x = (W - tw) / 2; yy = y + (li - (len(lines) - 1)) * lh
        for w in ln:
            col = words[k][1]; k += 1
            ds.text((x, yy + 3), w, font=f, fill=shadow, anchor='ls'); d.text((x, yy), w, font=f, fill=col, anchor='ls'); x += f.getlength(w) + sp
    return Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)), im)

def minimal_layout(words, size=60, max_w=None):
    """Fit caption words inside the safe width: one line if it fits, else two balanced lines,
    shrinking the font a little if a line is still too wide. Returns (lines, font)."""
    max_w = max_w or (840 if H > W else W - 160)   # portrait: keep clear of the right-hand TikTok buttons
    for sz in range(size, 40, -2):
        f = docmod._font(docmod.BOLD, sz); sp = f.getlength(' ')
        width = lambda ws: sum(f.getlength(w) for w in ws) + sp * (len(ws) - 1)
        if width(words) <= max_w: return [words], f
        best = min(range(1, len(words)), key=lambda i: max(width(words[:i]), width(words[i:]))) if len(words) > 1 else 1
        if max(width(words[:best]), width(words[best:])) <= max_w: return [words[:best], words[best:]], f
    return [words], f

def sub_frame(grp, t, y=1460, style=None):
    if style == 'minimal': return sub_frame_minimal(grp, t, y)
    f = font(70); fe = font(84); parts = []
    for w, emph, ws, we in grp:
        cur = ws <= t < we; col = C('gold') if (emph or cur) else (255, 255, 255)
        parts.append((w.upper(), fe if emph else f, col))
    lines, line, lw = [], [], 0
    for p in parts:
        pw = p[1].getlength(p[0] + ' ')
        if line and lw + pw > (840 if H > W else W - 140): lines.append(line); line, lw = [], 0   # portrait: stay inside the x 120..960 safe zone
        line.append(p); lw += pw
    if line: lines.append(line)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for li, ln in enumerate(lines):
        tw = sum(p[1].getlength(p[0] + ' ') for p in ln); x = (W - tw) / 2; yy = y + (li - (len(lines) - 1)) * 98   # extra lines grow upwards, away from the bottom UI
        for w, f_, col in ln:
            d.text((x, yy), w, font=f_, fill=col, stroke_width=9, stroke_fill=(0, 0, 0), anchor='ls'); x += f_.getlength(w + ' ')
    return im

# ---------------------------------------------------------------- transitions
def tear_frames(d):
    import random
    random.seed(7); np.random.seed(7); os.makedirs(d, exist_ok=True)
    noise = (np.random.rand(H, W) * 18).astype(np.uint8)
    base = np.zeros((H, W, 4), np.uint8); base[..., 0] = 238 - noise; base[..., 1] = 234 - noise; base[..., 2] = 224 - noise; base[..., 3] = 255
    paper = Image.fromarray(base, 'RGBA')
    def edge(seed):
        r = random.Random(seed); x = 0; pts = []
        for y in range(0, H + 40, 40): x = max(-60, min(60, x + r.uniform(-38, 38))); pts.append((y, x))
        return pts
    e1, e2 = edge(1), edge(2)
    for t in range(16):
        lead = W - (t + 1) / 8 * (W + 140) if t < 8 else -140
        trail = W + 200 if t < 8 else W + 200 - (t - 7) / 8 * (W + 340)
        mask = Image.new('L', (W, H), 0); ImageDraw.Draw(mask).polygon([(lead + x, y) for y, x in e1] + [(trail + x, y) for y, x in reversed(e2)], fill=255)
        sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sh.putalpha(mask.filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * .45)))
        img = sh.transform((W, H), Image.AFFINE, (1, 0, -14, 0, 1, -6)); p = paper.copy(); p.putalpha(mask)
        Image.alpha_composite(img, p).save(f'{d}/t_{t:02d}.png')
def glow_png(path, col):
    yy, xx = np.mgrid[0:H, 0:W]; r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + (((yy - H * .4) / (H / 2)) ** 2) * .8)
    a = np.clip((r - .82) / .45, 0, 1) ** 1.8; c = C(col)
    g = np.zeros((H, W, 4), np.uint8); g[..., 0], g[..., 1], g[..., 2] = c; g[..., 3] = (a * 120).astype(np.uint8)
    Image.fromarray(g, 'RGBA').save(path)

# ---------------------------------------------------------------- main
def main():
    tl_path, out = sys.argv[1], sys.argv[2]
    preview = float(sys.argv[sys.argv.index('--preview') + 1]) if '--preview' in sys.argv else None
    TL = json.load(open(tl_path)); src = TL['video']; base_dir = os.path.dirname(os.path.abspath(tl_path))
    prof = TL.get('profile') or os.path.join(base_dir, 'gac_profile.json')
    gtheme.apply(prof if isinstance(prof, dict) or os.path.exists(prof) else None, sys.modules[__name__])
    SUB_CFG.update(TL.get('subtitles') or {})
    global W, H
    canvas = TL.get('canvas', 'auto')
    if canvas == 'auto': sw, sh, _ = src_info(src); canvas = 'portrait' if sh >= sw else 'landscape'
    W, H = (1080, 1920) if canvas == 'portrait' else (1920, 1080)
    work = os.path.join(tempfile.gettempdir(), 'vedit_work'); shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    theme = (TL.get('doc') or {}).get('theme') or ('clear' if H > W else 'paper')
    DL = docmod.layout_for(W, H, theme); DL.update((TL.get('doc') or {}).get('layout', {}))
    px0, py0, px1, py1 = DL['panel']
    pp = docmod.layout_for(W, H, 'paper')['panel']   # "split" segments always use the paper side panel
    split_box = (0, 0, W, pp[1]) if H > W else (0, 0, pp[0], H)   # face window = everything outside the panel
    global CUT_WORDS
    wfile = (TL.get('subtitles') or {}).get('words')
    if wfile:
        wfile = wfile if os.path.isabs(wfile) else os.path.join(base_dir, wfile)
        if os.path.exists(wfile): CUT_WORDS = json.load(open(wfile))
    icons_dir = TL.get('icons') or (TL.get('doc') or {}).get('icons') or 'ikon'
    if not os.path.isabs(icons_dir): icons_dir = os.path.join(base_dir, icons_dir)
    M, total, freeze_ok = cut(src, TL['segments'], work, TL.get('enhance', True), split_box,
                              scenes=TL.get('scenes'), icons_dir=icons_dir, look=TL.get('look'),
                              push=TL.get('push', 0.0), soft=TL.get('soft_cuts', False)); N = mapper(M, total)
    splits = [(m['new'], m['new'] + m['len']) for m in M if m.get('layout') in ('split', 'doc')]
    scenes_on = [(m['new'], m['new'] + m['len']) for m in M if m.get('layout') == 'scene']
    FX_EV = []
    if TL.get('effects'):   # optional effects drawn on the cut video itself, under captions and cards
        import effects as fxmod
        fx_wins, FX_EV = fxmod.apply(f'{work}/base.mov', TL['effects'], N, W, H, base_dir, face_box)
        scenes_on += fx_wins
    def in_split(t): return any(a <= t < b for a, b in splits)
    def in_scene(t): return any(a <= t < b for a, b in scenes_on)
    if TL.get('doc') and theme == 'clear' and H > W and 'layout' not in TL['doc']:
        # fit the floating document around the face, measured on the cut video itself:
        # "chest" (default) = between chin and the bottom safe zone, "top" = above the head
        tops, bottoms = [], []
        for m in M:
            if m.get('layout') != 'doc': continue
            for f in (0.25, 0.5, 0.75):
                fb = face_box(f'{work}/base.mov', m['new'] + m['len'] * f)
                if fb: tops.append(fb[0]); bottoms.append(fb[1])
        pos = TL['doc'].get('position', 'chest')
        if pos == 'top' and tops:
            head = int(sorted(tops)[len(tops) // 2] - 10)        # typical top of the hair, with a little air
            head = max(420, min(head, 900))
            TL['doc']['layout'] = dict(panel=(0, 200, W, head), view=(235, head), anchor=head - 15, x0=60, x1=W - 60)  # side buttons start lower
            print(f'doc area above the head: y=235..{head}', file=sys.stderr)
        elif bottoms:
            top = int(min(1150, max(940, sorted(bottoms)[int(len(bottoms) * 0.8)] + 30)))
            TL['doc']['layout'] = dict(panel=(0, top, W, 1580), view=(top + 50, 1500))
            print(f'doc area starts at y={top} (below the chin)', file=sys.stderr)
    DOC = docmod.Doc(TL['doc'], N, W, H, base_dir) if TL.get('doc') else None
    if DOC: px0, py0, px1, py1 = DOC.L['panel']
    if DOC and DOC.warn: print('\n'.join('WARNING ' + w for w in DOC.warn), file=sys.stderr)
    if preview: total_r = min(total, preview)
    else: total_r = total
    sfx_ev = list(FX_EV) if TL.get('auto_sfx', True) else []; auto = TL.get('auto_sfx', True)
    for m in M:
        if m['kind'] == 'freeze' and auto: sfx_ev.append((m['new'], 'impact'))
        if auto: sfx_ev += [(m['new'] + et, en) for et, en in m.get('events', [])]
    # elements
    E = []
    for el in TL.get('elements', []):
        ty = el['type']; s, e = N(el['t'][0]), N(el['t'][1]); el = dict(el, s=s, e=e)
        if el.get('cover'): el.update(s=0.0, pop=False, fade_in=False)   # hook used as the TikTok/Reels cover frame
        if ty in mewah.TYPES:   # Gaya Mewah Emas (mewah.py)
            mewah.prepare(el, N); el.update(dyn=True, img=None, mewah=True)
            snd = {'mtitle': None, 'mword': 'shimmer', 'mstep': 'whoosh', 'mpanel': 'pop', 'mcta': 'coin', 'manim': 'coin'}[ty]
            if auto and snd and el.get('sfx', True) is not False: sfx_ev.append((el['s'], el.get('sfx') if isinstance(el.get('sfx'), str) else snd))
            if ty == 'mpanel' and auto: sfx_ev += [(a, 'pop') for a in el['_at'][1:]]
            E.append(el); continue
        if ty in ('hook2', 'pill', 'uipanel') or (ty, el.get('style')) in (('bigword', 'gaya1'), ('cta', 'button')):
            # Gaya 1 elements (gaya.py): drawn fresh every frame (typing, sliding, karaoke kicker)
            fb = face_box(f'{work}/base.mov', max(0.05, el['s'] + 0.05)) if ty in ('hook2', 'bigword') and H > W else None
            gaya.prepare(el, N, W, H, fb[0] if fb else None); el.update(dyn=True, img=None)
            snd = {'hook2': None, 'bigword': 'tick', 'pill': 'tick', 'uipanel': 'tick', 'cta': 'click'}[ty]
            if auto and snd and el.get('sfx', True) is not False: sfx_ev.append((el['s'], el.get('sfx') if isinstance(el.get('sfx'), str) else snd))
            E.append(el); continue
        if ty == 'title' and H > W and el.get('above_head', el.get('cover')):
            # fit the hook between the top UI zone and the top of the hair, measured on the cut video
            fb = face_box(f'{work}/base.mov', max(0.05, s + 0.05))
            if fb:
                band_top, band_bot = 228, int(fb[0]) - 18
                n = len(el['lines']); sz = el.get('size', 96)
                fit = int((band_bot - band_top) / (1.15 * n))
                if fit < 70:   # head too high in the frame: put the hook on the chest at full size instead of shrinking it
                    print(f'NOTE no room above the head (hair top at y {int(fb[0])}): hook moved to the chest', file=sys.stderr)
                    el['size'] = sz; el['y'] = el.get('chest_y', DY(1180))
                else:
                    if fit < sz:
                        print(f'NOTE hook size {sz} -> {max(44, fit)} so it clears the head (hair top at y {int(fb[0])})', file=sys.stderr)
                        sz = max(44, fit)
                    el['size'] = sz; el['y'] = (band_top + band_bot) / 2   # centre of the free band
        if ty == 'title':
            el['img'] = (clean_text([[(t, c) for t, c in ln] for ln in el['lines']], el.get('size', 96)) if el.get('style') == 'clean'
                         else text_block([[(t, c) for t, c in ln] for ln in el['lines']], el.get('size', 116), glow=el.get('glow', False))); el['cy'] = el.get('y', DY(330)); snd = 'whoosh'
        elif ty == 'bigword':
            sz_ = el.get('size', 150); el['img'] = text_block([[(el['text'], el.get('color', 'yellow'))]], sz_, glow=True)
            while H > W and el['img'].width > 880 and sz_ > 56:   # keep big words clear of the right-hand buttons
                sz_ -= 6; el['img'] = text_block([[(el['text'], el.get('color', 'yellow'))]], sz_, glow=True)
            el['cy'] = el.get('y', DY(1200)); snd = TL.get('bigword_sfx', 'shimmer')   # user's pick 2026-10-09 (gold ding); low 'impact' is inaudible on phones
        elif ty == 'card':
            el['img'] = card(el['text'], el.get('color', 'gold'), el.get('icon'), el.get('sub'), el.get('sub_color')); el['cy'] = el.get('y', DY(1230)); snd = 'pop'
        elif ty == 'image':
            im = Image.open(el['path']).convert('RGBA'); k = el.get('width', 620) / im.width
            im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
            fr = Image.new('RGBA', (im.width + 24, im.height + 24), (0, 0, 0, 0)); ImageDraw.Draw(fr).rounded_rectangle((0, 0, fr.width - 1, fr.height - 1), 28, fill=(255, 255, 255, 235))
            m_ = Image.new('L', im.size, 0); ImageDraw.Draw(m_).rounded_rectangle((0, 0, im.width - 1, im.height - 1), 22, fill=255); im.putalpha(m_)
            fr.alpha_composite(im, (12, 12)); sh = Image.new('RGBA', (fr.width + 60, fr.height + 60), (0, 0, 0, 0)); sh.alpha_composite(fr, (30, 30))
            el['img'] = sh; el['cy'] = el.get('y', DY(760)); snd = 'whoosh'
        elif ty == 'sticker':
            # one plain icon (transparent PNG, no card) popping in with a soft glow; use x/y to place it, e.g. above the head
            im = Image.open(el['path'] if os.path.isabs(el['path']) else os.path.join(base_dir, el['path'])).convert('RGBA'); im = im.crop(im.getbbox())
            k = el.get('h', 190) / im.height; im = im.resize((max(1, int(im.width * k)), el.get('h', 190)), Image.LANCZOS)
            pad = 50; st_im = Image.new('RGBA', (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
            sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); sh.putalpha(im.getchannel('A').point(lambda v: int(v * 0.55)))
            st_im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)), (pad, pad + 10)); st_im.alpha_composite(im, (pad, pad))
            el['img'] = st_im; el['cy'] = el.get('y', DY(330)); snd = 'shimmer'
        elif ty == 'popup':
            # cards / a phone screenshot that pop up over a bokeh-blurred, slightly dimmed video
            def soft_shadow(im, blur=24, a=0.45):
                pad = 60; out = Image.new('RGBA', (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
                sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); sh.putalpha(im.getchannel('A').point(lambda v: int(v * a)))
                out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)), (pad, pad + 20)); out.alpha_composite(im, (pad, pad)); return out
            paths = [pth if os.path.isabs(pth) else os.path.join(base_dir, pth) for pth in el['images']]
            ims = [Image.open(pth).convert('RGBA') for pth in paths]; ims = [im.crop(im.getbbox()) for im in ims]
            if el.get('phone'):
                import motion
                sc_ = ims[0].convert('RGB'); sw_ = el.get('w', 560); sc_ = sc_.resize((sw_, int(sc_.height * sw_ / sc_.width)), Image.LANCZOS)
                comp = motion.phone_frame(sc_)
            elif len(ims) == 1:
                w_ = el.get('w', 860); comp = soft_shadow(ims[0].resize((w_, int(ims[0].height * w_ / ims[0].width)), Image.LANCZOS))
            else:   # fan of cards
                n = len(ims); w_ = el.get('w', 640 if n == 2 else 540); spread = el.get('spread', 300 if n == 2 else 170)
                cards = [soft_shadow(im.resize((w_, int(im.height * w_ / im.width)), Image.LANCZOS)) for im in ims]
                angs = [(-7 + 14 * k / (n - 1)) for k in range(n)]
                rot = [c.rotate(-a_, resample=Image.BICUBIC, expand=True) for c, a_ in zip(cards, angs)]
                cw = max(r.width for r in rot) + spread * (n - 1); ch = max(r.height for r in rot) + 80 * (n - 1)
                comp = Image.new('RGBA', (int(cw), int(ch)), (0, 0, 0, 0))
                for k, r in enumerate(rot):
                    comp.alpha_composite(r, (int(k * spread), int(abs(k - (n - 1) / 2) * 40)))
            maxw = 900 if H > W else W * 0.6; maxh = 1150 if H > W else H * 0.8   # portrait: stays between y 260 and 1490
            k_ = min(1.0, maxw / comp.width, maxh / comp.height)
            if k_ < 1: comp = comp.resize((int(comp.width * k_), int(comp.height * k_)), Image.LANCZOS)
            el['img'] = comp; el['cy'] = el.get('y', DY(860)); snd = 'pop'
        elif ty == 'lowerthird':
            im = Image.new('RGBA', (900, 190), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            d.rounded_rectangle((0, 0, 899, 189), 24, fill=(12, 12, 12, 210)); d.rectangle((0, 0, 14, 189), fill=C(el.get('color', 'gold')))
            d.text((44, 30), el['name'], font=font(62), fill=(255, 255, 255)); d.text((44, 112), el.get('title', ''), font=font(44), fill=C(el.get('color', 'gold')))
            el['img'] = im; el['cy'] = el.get('y', DY(1240)); snd = 'whoosh'
        elif ty == 'cta' and el.get('style') == 'minimal':
            # Gaku-style call to action: small dark glass pill, thin gold rim, link glyph, sentence case
            f = docmod._font(docmod.BOLD, el.get('size', 46)); tw = f.getlength(el['text']); h = int(f.size * 2.1)
            w = int(tw + h * (1.1 if el.get('icon') == 'none' else 1.9)); im = Image.new('RGBA', (w + 40, h + 40), (0, 0, 0, 0))
            sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((20, 26, w + 20, h + 26), h // 2, fill=(0, 0, 0, 120))
            im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10))); d = ImageDraw.Draw(im)
            d.rounded_rectangle((20, 20, w + 20, h + 20), h // 2, fill=(14, 11, 8, 205), outline=gtheme.RIM, width=3)
            cx, cy, r = 20 + h * 0.62, 20 + h / 2, h * 0.2
            if el.get('icon') == 'none':                                       # text-only pill: no glyph, text starts nearer the edge
                pass
            elif el.get('icon') == 'heart':                                    # "tekan like"
                hr = r * 1.15
                d.ellipse((cx - hr * 1.05, cy - hr * 0.75, cx + hr * 0.05, cy + hr * 0.3), fill=(235, 64, 90))
                d.ellipse((cx - hr * 0.05, cy - hr * 0.75, cx + hr * 1.05, cy + hr * 0.3), fill=(235, 64, 90))
                d.polygon([(cx - hr * 1.0, cy - hr * 0.1), (cx + hr * 1.0, cy - hr * 0.1), (cx, cy + hr * 1.0)], fill=(235, 64, 90))
            elif el.get('icon') == 'comment':                                    # speech bubble = "comment below"
                d.rounded_rectangle((cx - r * 1.3, cy - r, cx + r * 1.3, cy + r * 0.7), r * 0.5, outline=gtheme.A, width=4)
                d.polygon([(cx - r * 0.6, cy + r * 0.6), (cx - r * 0.9, cy + r * 1.35), (cx - r * 0.05, cy + r * 0.6)], fill=gtheme.A)
            else:                                                              # two linked rings = "link"
                for dx in (-r * 0.55, r * 0.55):
                    d.rounded_rectangle((cx + dx - r, cy - r * 0.55, cx + dx + r, cy + r * 0.55), r * 0.55, outline=gtheme.A, width=4)
            d.text((20 + h * (0.55 if el.get('icon') == 'none' else 1.15), cy), el['text'], font=f, fill=(255, 255, 255), anchor='lm')
            el['img'] = im; el['cy'] = el.get('y', DY(1290)); snd = 'click'
        elif ty == 'cta':
            im = Image.new('RGBA', (900, 190), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            if el.get('color', 'gold') == 'green':
                d.rounded_rectangle((0, 0, 899, 189), 95, fill=(37, 211, 102)); tf, ts = (255, 255, 255), dict(stroke_width=3, stroke_fill=(0, 90, 40))
            else:  # gold pill with a light top edge, dark text
                g = np.linspace(0, 1, 190)[:, None]; a = np.array(gtheme.LIGHT) * (1 - g[..., None]) + np.array(gtheme.DARK) * g[..., None]
                grad = Image.fromarray(np.repeat(a, 900, axis=1).astype(np.uint8), 'RGB').convert('RGBA')
                m = Image.new('L', (900, 190), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, 899, 189), 95, fill=255); im.paste(grad, (0, 0), m)
                tf, ts = gtheme.ON, {}
            f = font(60)
            while f.getlength(el['text']) > 820: f = font(f.size - 2)
            d.text((450, 95), el['text'], font=f, fill=tf, anchor='mm', **ts)
            el['img'] = im; el['cy'] = el.get('y', DY(1235)); snd = 'coin'
        elif ty == 'disclaimer':
            im = panel(940, 150, fill=(255, 212, 59, 235), r=20); d = ImageDraw.Draw(im); f = font(34)
            words, lines_, ln = el['text'].split(), [], ''
            for w in words:
                if f.getlength(ln + ' ' + w) > 820: lines_.append(ln); ln = w
                else: ln = (ln + ' ' + w).strip()
            lines_.append(ln); im = panel(940, 50 + 40 * len(lines_), fill=(255, 212, 59, 235), r=20); d = ImageDraw.Draw(im)
            for i, l in enumerate(lines_): d.text((470, 25 + 40 * i + 20), l, font=f, fill=(0, 0, 0), anchor='mm')
            el['img'] = im; el['cy'] = el.get('y', DY(300)); snd = 'click'
        elif ty in ('chart', 'checklist', 'counter'):
            el['img'] = None; el['cy'] = el.get('y', DY(1170)); snd = {'chart': 'whoosh', 'checklist': 'pop', 'counter': 'tick'}[ty]
        else:
            print('unknown element type', ty); continue
        if auto and el.get('sfx', True) is not False: sfx_ev.append((s, el.get('sfx') if isinstance(el.get('sfx'), str) else snd))
        if ty == 'checklist' and auto:
            for k in range(1, len(el['items'])): sfx_ev.append((s + k * el.get('gap', 0.9), 'pop'))
        E.append(el)
    subs = []; sent_of = {}   # sent_of[id(group)] = sentence number (a sentence is split into several caption groups)
    if TL.get('subtitles'):
        st = TL['subtitles']
        if 'script' in st:
            ch = st.get('speech')
            if ch is None:
                err = run(['ffmpeg','-i',src,'-af','silencedetect=noise=-30dB:d=0.3','-f','null','-']).stderr
                ss = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', err)]; se = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', err)]
                ch, t0 = [], 0.0
                for a, b in zip(ss, se + [1e9]):
                    if a - t0 > .15: ch.append([t0, a])
                    t0 = b
                last = max(m['b'] for m in M if m['kind'] == 'clip')
                if last - t0 > .15: ch.append([t0, last])
            chn = []
            for a, b in ch:  # clip each chunk to kept material and map
                for m in M:
                    if m['kind'] != 'clip': continue
                    lo, hi = max(a, m['a']), min(b, m['b'])
                    if hi - lo > 0.1: chn.append((N(lo), N(hi)))
            subs = script_subs(st['script'], chn, st.get('max_words', 5))
        elif 'words' in st:   # word-level timing from transcribe.py (Whisper): exact start/end per word
            wp = st['words'] if os.path.isabs(st['words']) else os.path.join(base_dir, st['words'])
            emph = {w.lower() for w in st.get('emphasis', [])}; drop = {w.lower() for w in st.get('drop', ['aa', 'erm', 'em'])}
            fixes = {k.lower(): v for k, v in st.get('fix', {}).items()}
            clips = [m for m in M if m['kind'] == 'clip' and m.get('layout') not in ('scene',)]
            kept = []
            for w in json.load(open(wp)):
                txt = fixes.get(w['w'].lower(), w['w'])
                if txt.lower().strip(',.?!') in drop: continue
                if not any(m['a'] <= w['s'] and w['e'] <= m['b'] + 0.05 for m in clips): continue   # cut away or under a scene
                kept.append((txt, txt.lower().strip(',.?!') in emph, N(w['s']), N(w['e'])))
            # sentence boundaries: SRT lines when available (CapCut splits by sentence), else punctuation and
            # capitalised sentence starters, so one caption never runs across two sentences
            srt_lines = None
            if st.get('srt'):
                sp_ = st['srt'] if os.path.isabs(st['srt']) else os.path.join(base_dir, st['srt'])
                if os.path.exists(sp_): srt_lines = parse_srt(sp_)
            proper = {w.lower() for w in st.get('proper', ['Public', 'Gold', 'GAP', 'Malaysia', 'Indonesia', 'UK', 'Australia', 'RM', 'PG', 'Jewel', 'InsyaAllah', 'Allah'])}
            raw = [w for w in json.load(open(wp))]
            def line_of(w):
                if not srt_lines: return None
                m = (w['s'] + w['e']) / 2
                best = min(range(len(srt_lines)), key=lambda q: 0 if srt_lines[q][0] <= m <= srt_lines[q][1] else min(abs(m - srt_lines[q][0]), abs(m - srt_lines[q][1])))
                return best
            kept2 = []
            for w in raw:
                txt = fixes.get(w['w'].lower(), w['w'])
                if txt.lower().strip(',.?!') in drop: continue
                if not any(m['a'] - 0.05 <= w['s'] < m['b'] for m in clips): continue   # by start time: words on a segment edge stay
                kept2.append((txt, txt.lower().strip(',.?!') in emph, N(w['s']), N(w['e']), line_of(w)))
            # 1) split into sentences/phrases; 2) cut each phrase into evenly sized captions (no orphan words)
            phrases, grp = [], []
            for wd in kept2:
                starts_sentence = (srt_lines is None and wd[0][:1].isupper() and wd[0].lower().strip(',.?!') not in proper)
                if grp and (wd[2] - grp[-1][3] > 0.35 or grp[-1][0].endswith(('.', '?', '!')) or starts_sentence
                            or (srt_lines is None and grp[-1][0].endswith(','))
                            or (srt_lines is not None and wd[4] != grp[-1][4])):
                    phrases.append(grp); grp = []
                grp.append(wd)
            if grp: phrases.append(grp)
            mw = st.get('max_words', 5)
            for pi, ph in enumerate(phrases):
                n = -(-len(ph) // mw); size = -(-len(ph) // n)
                for k in range(0, len(ph), size):
                    g = ph[k:k + size]; subs.append((g[0][2], g[-1][3], [x[:4] for x in g])); sent_of[id(subs[-1])] = ('w', pi)
            if os.environ.get('DEBUG_SUBS'):
                for g in subs: print(f"SUB {g[0]:6.2f}-{g[1]:6.2f}  {' '.join(x[0] for x in g[2])}", file=sys.stderr)
        elif 'lines' in st or 'srt' in st:  # per-line timing from an SRT: [[start, end, text], ...]
            lines = st.get('lines') or parse_srt(st['srt'] if os.path.isabs(st['srt']) else os.path.join(base_dir, st['srt']))
            for a, b, txt in lines:
                chn = []
                for m in M:
                    if m['kind'] != 'clip': continue
                    lo, hi = max(a, m['a']), min(b, m['b'])
                    if hi - lo > 0.1: chn.append((N(lo), N(hi)))
                for g in script_subs(txt, chn, st.get('max_words', 5)): subs.append(g); sent_of[id(g)] = ('l', a)
    # safe zone (portrait): nothing readable in the top 220 px or below y 1500 (TikTok/Reels UI)
    if H > W:
        for el in E:
            if el.get('img') is not None and el['type'] != 'image':
                top, bot = el['cy'] - el['img'].height / 2, el['cy'] + el['img'].height / 2
                if bot > 1500 + 40 or top < 200 - 40:
                    print(f"WARNING {el['type']} outside the safe zone (y {int(top)}..{int(bot)}): {el.get('text') or el.get('lines')}", file=sys.stderr)
        if subs and (TL.get('subtitles') or {}).get('y', DY(1460)) > 1500:
            print(f"WARNING subtitles baseline y {(TL.get('subtitles') or {}).get('y')} is inside the bottom UI zone", file=sys.stderr)
    # keep captions and overlays off the face (portrait): measure the face at each moment and move
    # the item below the chin or above the hair, whichever fits inside the safe zone
    sub_y = {}
    if H > W and TL.get('avoid_face', True):
        fcache = {}
        def fb_at(t):
            k = round(t * 2) / 2
            if k not in fcache: fcache[k] = face_box(f'{work}/base.mov', min(max(0.05, k), total - 0.05))
            return fcache[k]
        pops = [(el['s'], el['e']) for el in E if el['type'] == 'popup']
        def place_off_face(top, bot, t):
            if any(a <= t <= b for a, b in pops): return 0     # face is blurred behind a popup: leave it
            fb = fb_at(t)
            if not fb or bot < fb[0] - 10 or top > fb[1] + 40: return 0
            h = bot - top
            if fb[1] + 50 + h <= 1490: return fb[1] + 50 - top          # below the chin
            if fb[0] - 30 - h >= 230: return fb[0] - 30 - h - top        # above the hair
            return 0
        base_y = (TL.get('subtitles') or {}).get('y', DY(1460))
        for g in subs:
            if any(g[0] < b_ and g[1] > a_ for a_, b_ in pops): continue   # shares time with a popup: keep it low, under the card
            d = place_off_face(base_y - 175, base_y + 25, (g[0] + g[1]) / 2)
            if d: sub_y[id(g)] = base_y + d
        for el in E:
            if el['type'] in ('lowerthird', 'bigword', 'cta', 'card') and el.get('img') is not None and not el.get('pinned_pos'):   # pinned_pos: user-placed (e.g. above one person's head)
                hh = el['img'].height
                d = place_off_face(el['cy'] - hh / 2, el['cy'] + hh / 2, (el['s'] + el['e']) / 2)
                if d: el['cy'] += d
        if sub_y: print(f'NOTE moved {len(sub_y)} captions off the face', file=sys.stderr)
    # manual caption baselines: subtitles.y_at = [[t0, t1, y], ...] (OUTPUT seconds) overrides the automatic placement (e.g. a huge close-up face)
    for a_, b_, y_ in (TL.get('subtitles') or {}).get('y_at', []):
        for g in subs:
            if a_ <= (g[0] + g[1]) / 2 <= b_: sub_y[id(g)] = y_
    # check every caption fits on screen before spending time rendering
    for g in subs:
        ws = [w for w, *_ in g[2]]
        if (TL.get('subtitles') or {}).get('style') == 'minimal':
            lines, f = minimal_layout(ws); sp = f.getlength(' ')
            wid = max(sum(f.getlength(w) for w in ln) + sp * (len(ln) - 1) for ln in lines)
            if wid > W - 80: print(f'WARNING caption too wide ({int(wid)}px): {" ".join(ws)}', file=sys.stderr)
    fx = TL.get('fx', {})
    tears = [N(x) for x in fx.get('tear', [])]; flashes = [N(x) for x in fx.get('flash', [])]
    whips = [N(x) for x in fx.get('whip', [])]; glows = [(N(a), N(b), c) for a, b, c in fx.get('glow', [])]
    if auto:
        sfx_ev += [(t, 'whoosh') for t in tears + whips] + [(t, 'click') for t in flashes]
    sfx_ev += [(N(t), n) for t, n in TL.get('sfx', [])]
    # Gaya 1: accent colour, chapter tag + progress bar, person masks for "behind" elements
    ACC = tuple(COL.get('accent', COL['gold']))[:3]
    CH = []
    if TL.get('chapters'):
        chs = TL['chapters']; n_ = TL.get('chapters_total', len(chs))
        for i, (ta, lab) in enumerate(chs):
            tb = chs[i + 1][0] if i + 1 < len(chs) else TL.get('chapters_end', 1e9)
            CH.append((N(ta), N(tb) if tb < 1e9 else total, lab, i, n_))
    SEG = None
    beh = [(el['s'], min(el['e'], total_r)) for el in E if el.get('dyn') and el.get('behind') and el['s'] < total_r]
    if beh:
        SEG = gaya.Seg(f'{work}/base.mov', W, H); SEG.prepare(beh)
        print(f'person masks: {len(SEG.m)} frames', file=sys.stderr)
    # render overlay frames
    ov = f'{work}/ov'; os.makedirs(ov)
    nf = int(total_r * FPS) + 1
    big_sents = None
    for k in range(nf):
        t = k / FPS; fr = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        if DOC and in_split(t): fr.alpha_composite(DOC.frame(t), (px0, py0))
        back = None
        for el in E:
            if el.get('dyn'):
                lay = mewah.draw(el, t, W, H) if el.get('mewah') else gaya.draw(el, t, W, H, ACC, SEG)
                if lay is None: continue
                if el.get('behind'):
                    back = lay if back is None else Image.alpha_composite(back, lay)
                else: fr.alpha_composite(lay)
                continue
            r = env(t, el['s'], el['e'], el.get('pop', True), el.get('fade_in', True))   # "cover": true shows it fully on frame 1
            if not r: continue
            ty = el['type']; sc, al = r
            if el.get('grow'):   # popup that grows from small to full size over its whole time on screen
                q = min(1.0, (t - el['s']) / max(0.2, el['e'] - el['s'] - 0.3)); sc = 0.25 + 0.75 * (1 - (1 - q) ** 2)
            if ty == 'chart':
                p = min(1, (t - el['s']) / 1.6); col = C(el.get('color', 'green' if el.get('dir', 'up') == 'up' else 'red'))
                pn = panel(900, 330, border=col); d = ImageDraw.Draw(pn); d.text((50, 30), el['title'], font=font(60), fill=(255, 255, 255)); d.text((50, 105), el.get('sub', ''), font=font(60), fill=col)
                pts = [(60, 300), (180, 270), (270, 285), (380, 220), (470, 235), (580, 160), (680, 175), (840, 70)]
                if el.get('dir', 'up') == 'down': pts = [(x, 330 - y + 40) for x, y in pts]
                u = p * (len(pts) - 1); dr = [pts[0]]
                for i in range(len(pts) - 1):
                    if u >= i + 1: dr.append(pts[i + 1])
                    elif u > i: f_ = u - i; dr.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f_, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f_)); break
                d.line(dr, fill=col, width=12, joint='curve'); img = pn; sc = 0.85
            elif ty == 'checklist':
                n_ = len(el['items']); pn = panel(900, 60 + 120 * n_, border=el.get('color', 'gold')); d = ImageDraw.Draw(pn)
                for i, it in enumerate(el['items']):
                    if t - el['s'] >= i * el.get('gap', 0.9):
                        pn.alpha_composite(icon(el.get('icon', 'check'), 90, 'green' if el.get('icon', 'check') == 'check' else 'red'), (40, 38 + i * 120))
                        f = font(60)
                        while f.getlength(it) > 680: f = font(f.size - 2)
                        d.text((150, 38 + i * 120 + 45), it, font=f, fill=C(el.get('last_color', 'gold')) if i == n_ - 1 and n_ > 2 else (255, 255, 255), anchor='lm')
                img = pn; sc = 0.8
            elif ty == 'counter':
                p = min(1, (t - el['s']) / el.get('count_time', 1.2)); p = 1 - (1 - p) ** 3
                v = el.get('from', 0) + (el['to'] - el.get('from', 0)) * p; dec = el.get('decimals', 0)
                txt = f"{el.get('prefix', '')}{v:,.{dec}f}{el.get('suffix', '')}"
                img = text_block([[(txt, el.get('color', 'yellow'))]], el.get('size', 170), glow=True)
                if el.get('label'): fr.alpha_composite(place(text_block([[(el['label'], 'white')]], 64), W / 2, el['cy'] - 150, 1, al, fit=0.95))
                sc = 1.0
            else:
                img = el['img']
            fr.alpha_composite(place(img, el.get('x', W / 2), el['cy'], sc, al, fit=0.95))
        if big_sents is None:   # sentences that overlap a big word anywhere: the whole sentence's captions are dropped
            stext = {}
            for g in subs: stext[sent_of.get(id(g))] = stext.get(sent_of.get(id(g)), '') + ' ' + ' '.join(str(x[0]) for x in g[2]).lower()
            def hides(el, g):   # bigword: any overlapping sentence; pill with "hide_caps": only sentences sharing its words
                if not (g[0] < el['e'] and g[1] > el['s']): return False
                if el['type'] == 'bigword': return True
                if not el.get('hide_caps'): return False
                key = [w for w in re.sub(r'[^\w ]', ' ', str(el.get('text', '')).lower()).split() if len(w) > 2]
                return any(w in stext.get(sent_of.get(id(g)), '') for w in key)
            # GAC: hide only the caption groups that actually overlap a big word / panel, never a whole sentence
            # (participants read missing sentences as a bug)
            big_sents = {id(g) for g in subs if any(hides(el, g) for el in E) or any(in_scene(x) for x in np.arange(g[0], g[1], 0.1))}
        if back is not None:   # behind the speaker: clear the person area, then everything else on top
            back = gaya.cut_out_person(back, SEG.at(t) if SEG else None); back.alpha_composite(fr); fr = back
        if CH:
            chl = gaya.chapters_frame(CH, t, W, H, ACC)
            if chl is not None: fr.alpha_composite(chl)
        cur = [g for g in subs if g[0] <= t <= g[1] + 0.3]
        big_on = any((el['type'] in ('bigword', 'mword', 'mstep', 'mpanel') or el.get('cover')) and el['s'] <= t <= el['e'] for el in E)   # Mewah panels say it already   # big word / cover hook replaces the caption
        # a caption group that overlaps a big word at any moment is dropped entirely: the big word already says it,
        # and showing its leftover words for a split second after the big word looks like a glitch
        if cur and id(cur[-1]) in big_sents: big_on = True
        if cur and not (DOC and in_split(t)) and not in_scene(t) and not big_on:  # document / motion scene replace subtitles
            y_ = sub_y.get(id(cur[-1]), TL['subtitles'].get('y', DY(1460)))
            ups = [el['_top'] for el in E if el.get('dyn') and el['type'] in ('uipanel', 'pill') and el['s'] <= t <= el['e'] and '_top' in el]
            if ups: y_ = min(y_, min(ups) - 34)   # Gaya 1: captions sit just above a panel or pill
            if TL['subtitles'].get('style') == 'mewah':   # Gaya Mewah Emas: navy pill caption
                fr.alpha_composite(mewah.sub_frame(cur[-1][2], t, y_, W, H))
            elif TL['subtitles'].get('style') == 'type':   # Gaya 1: captions type themselves letter by letter
                fr.alpha_composite(gaya.sub_frame_type(cur[-1][2], t, y_, W, H, ACC, {w.lower() for w in TL['subtitles'].get('italic', [])}))
            else:
                fr.alpha_composite(sub_frame(cur[-1][2], t, y_, TL['subtitles'].get('style')))
        if H > W and k % 6 == 0:   # QA: any overlay pixel in the TikTok/Reels UI zones?
            al = np.asarray(fr.getchannel('A'))
            for zn, z in (('atas', al[:220]), ('bawah', al[1500:]), ('kanan', al[700:1500, 960:])):
                if z.size and z.max() > 60: QA_HITS.setdefault(zn, []).append(round(t, 1))
        fr.save(f'{ov}/o_{k:05d}.png', compress_level=1)
    # sound effects track
    sfx.render_track([e for e in sfx_ev if e[0] <= total_r], total_r, f'{work}/sfx.wav', TL.get('sfx_gain_db', -14))
    # compose
    inputs = ['-i', f'{work}/base.mov', '-framerate', '30', '-i', f'{ov}/o_%05d.png', '-i', f'{work}/sfx.wav']
    fc = []; v = '[0:v]'; idx = 3
    blurs = [(el['s'], el['e']) for el in E if el['type'] == 'popup' and el.get('blur', True)]
    if blurs:   # bokeh: blur and dim the video behind every popup
        en = '+'.join(f'between(t,{a:.3f},{b:.3f})' for a, b in blurs)
        fc.append(f"{v}gblur=sigma=22:steps=2:enable='{en}',drawbox=x=0:y=0:w=iw:h=ih:color=black@0.25:t=fill:enable='{en}'[vb]"); v = '[vb]'
    for i, (a, b, c) in enumerate(glows):
        gp = f'{work}/glow{i}.png'; glow_png(gp, c); d = b - a
        inputs += ['-loop', '1', '-framerate', '30', '-t', f'{d:.3f}', '-i', gp]
        fc.append(f'[{idx}:v]format=rgba,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st={max(0, d - .4):.3f}:d=0.4:alpha=1,setpts=PTS-STARTPTS+{a:.3f}/TB[g{i}]')
        fc.append(f'{v}[g{i}]overlay=eof_action=pass[vg{i}]'); v = f'[vg{i}]'; idx += 1
    if whips:
        en = '+'.join(f'between(t,{x - .07:.3f},{x + .07:.3f})' for x in whips)
        fc.append(f"{v}avgblur=sizeX=45:sizeY=1:enable='{en}'[vw]"); v = '[vw]'
    if flashes:
        en = '+'.join(f'between(t,{x:.3f},{x + .07:.3f})' for x in flashes)
        fc.append(f"{v}drawbox=x=0:y=0:w=iw:h=ih:color=white@0.55:t=fill:enable='{en}'[vf]"); v = '[vf]'
    fc.append(f'{v}[1:v]overlay=eof_action=pass[vo]'); v = '[vo]'
    if tears:
        tear_frames(f'{work}/tear')
        for i, x in enumerate(tears):
            inputs += ['-framerate', '30', '-i', f'{work}/tear/t_%02d.png']
            fc.append(f'[{idx}:v]setpts=PTS-STARTPTS+{x - .267:.3f}/TB[t{i}]'); fc.append(f'{v}[t{i}]overlay=eof_action=pass[vt{i}]'); v = f'[vt{i}]'; idx += 1
    fc.append(f'[0:a][2:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[ao]')
    cmd = ['ffmpeg', '-v', 'error', '-y'] + inputs + ['-filter_complex', ';'.join(fc), '-map', v, '-map', '[ao]',
           '-t', f'{total_r:.3f}', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', out]
    run(cmd)
    # QA sheet goes to the temp folder, never next to the video (final/ holds only finished videos)
    sheet = os.path.join(tempfile.gettempdir(), os.path.basename(out).rsplit('.', 1)[0] + '_frames.jpg')
    guides = ('drawbox=y=220:w=iw:h=4:color=red:t=fill,drawbox=y=1500:w=iw:h=4:color=red:t=fill,'
              'drawbox=x=120:y=700:w=4:h=800:color=cyan:t=fill,drawbox=x=960:y=700:w=4:h=800:color=cyan:t=fill,') if H > W else ''
    run(['ffmpeg', '-v', 'error', '-y', '-i', out, '-vf', f'fps=1,{guides}scale=180:-1,tile=10x6', '-frames:v', '1', sheet])
    for zn, ts_ in QA_HITS.items():
        print(f'WARNING safe zone {zn}: overlay di zon butang/caption TikTok pada t={ts_[:12]}', file=sys.stderr)
    print(json.dumps(dict(out=out, duration=round(total_r, 2), full_duration=round(total, 2), frames_sheet=sheet,
                          freeze_outline=freeze_ok, subtitles=len(subs), sfx=len(sfx_ev),
                          safe_zone='BERSIH' if not QA_HITS else {z: v[:12] for z, v in QA_HITS.items()}), indent=1))
if __name__ == '__main__': main()
