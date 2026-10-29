#!/usr/bin/env python3
"""Replace the background of a talking-head video with a photo (person mask per frame, U^2-Net human seg).
Usage: python3 bgswap.py VIDEO BG.jpg OUT.mov [--blur 3] [--crop x0,y0,x1,y1] [--shade 0.08]
--crop  part of the background photo to use (e.g. to leave out a watermark)
--blur  background blur (depth of field); --shade darkens the background a little so the person stands out.

For a STATIC camera (tripod / phone on a stand). Two passes:
 1. person model mask per frame + a clean plate of the real background (averaged where it is visible);
 2. matte = difference from the plate near the body (pixel-exact: fast hands never vanish), the model
    elsewhere, holes filled, edges refined at full size with a guided filter.
--thr: colour difference that counts as 'you' (raise if the wall shimmers, lower if parts drop out).
Output keeps the original audio; feed it to build.py as the timeline "video"."""
import os, sys, subprocess, argparse
import numpy as np, cv2
from PIL import Image, ImageOps

ap = argparse.ArgumentParser(); ap.add_argument('video'); ap.add_argument('bg'); ap.add_argument('out')
ap.add_argument('--blur', type=float, default=3); ap.add_argument('--crop'); ap.add_argument('--shade', type=float, default=0.08)
ap.add_argument('--thr', type=float, default=16); ap.add_argument('--reach', type=int, default=61); ap.add_argument('--top', type=float, default=0.22)
A = ap.parse_args()

def probe(v):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate',
                        '-of', 'csv=p=0', v], capture_output=True, text=True).stdout.strip().split(',')
    n, d = r[2].split('/'); return int(r[0]), int(r[1]), float(n) / float(d)
W, H, FPS = probe(A.video); SW, SH = W // 4, H // 4          # masks are kept at quarter size

bg = ImageOps.exif_transpose(Image.open(A.bg)).convert('RGB')
if A.crop: bg = bg.crop(tuple(int(v) for v in A.crop.split(',')))
k = max(W / bg.width, H / bg.height); bg = bg.resize((int(bg.width * k + 1), int(bg.height * k + 1)), Image.LANCZOS)
x0, y0 = (bg.width - W) // 2, (bg.height - H) // 2; bg = np.asarray(bg.crop((x0, y0, x0 + W, y0 + H))).astype(np.float32)
if A.blur > 0: bg = cv2.GaussianBlur(bg, (0, 0), A.blur)
bg *= (1 - A.shade)

import onnxruntime as ort
model = os.path.expanduser('~/.cache/gac/models/u2net_human_seg.onnx')
if not os.path.exists(model):
    os.makedirs(os.path.dirname(model), exist_ok=True)
    subprocess.run(['curl', '-fsSL', '-o', model, 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx'], check=True)
so = ort.SessionOptions(); so.intra_op_num_threads = os.cpu_count() or 4
sess = ort.InferenceSession(model, so, providers=['CPUExecutionProvider']); iname = sess.get_inputs()[0].name
mean, std = np.array([0.485, 0.456, 0.406], np.float32), np.array([0.229, 0.224, 0.225], np.float32)

def frames():
    dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', A.video, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    size = W * H * 3
    while True:
        buf = dec.stdout.read(size)
        if len(buf) < size: break
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    dec.wait()

def skin(small_rgb):
    """Skin-coloured pixels (YCrCb box), cleaned."""
    ycc = cv2.cvtColor(small_rgb, cv2.COLOR_RGB2YCrCb)
    s = cv2.inRange(ycc, (40, 135, 85), (250, 175, 128))
    s = cv2.morphologyEx(s, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)); return s.astype(np.float32) / 255

# pass 1: person masks (U^2-Net, quarter size) + a clean plate of the static background (half size)
HW, HH = W // 2, H // 2
masks = []; acc = np.zeros((HH, HW, 3), np.float64); cnt = np.zeros((HH, HW), np.float64)
for n, fr in enumerate(frames()):
    x = ((cv2.resize(fr, (320, 320), interpolation=cv2.INTER_AREA).astype(np.float32) / 255 - mean) / std).transpose(2, 0, 1)[None]
    o = sess.run(None, {iname: x})[0][0, 0]; o = (o - o.min()) / (o.max() - o.min() + 1e-9)
    m = np.clip((cv2.resize(o, (SW, SH), interpolation=cv2.INTER_CUBIC) - 0.15) / 0.7, 0, 1)
    masks.append(m.astype(np.float16))
    if n % 4 == 0:   # plate: average of pixels that are clearly background in this frame
        half = cv2.resize(fr, (HW, HH), interpolation=cv2.INTER_AREA).astype(np.float64)
        bgm = cv2.resize((cv2.dilate((m > 0.15).astype(np.uint8), np.ones((9, 9), np.uint8)) == 0).astype(np.uint8), (HW, HH), interpolation=cv2.INTER_NEAREST).astype(np.float64)
        acc += half * bgm[..., None]; cnt += bgm
    if (n + 1) % 150 == 0: print(f'topeng: {n + 1} bingkai', file=sys.stderr, flush=True)
M = np.stack(masks).astype(np.float32); N = len(M)
plate = (acc / np.maximum(cnt, 1)[..., None]).astype(np.float32); known = cnt >= 3
plate = cv2.GaussianBlur(plate, (0, 0), 1.0)

def matte(fr, n):
    """Pixel-accurate person matte: difference from the clean plate where the background is known,
    the person model elsewhere; refined at full size with a guided filter (edges follow the hijab / fingers)."""
    half = cv2.GaussianBlur(cv2.resize(fr, (HW, HH), interpolation=cv2.INTER_AREA).astype(np.float32), (0, 0), 1.0)
    d = np.abs(half - plate).max(2)
    diff = np.clip((d - A.thr) / 22.0, 0, 1)
    u = cv2.resize(M[n], (HW, HH), interpolation=cv2.INTER_LINEAR)
    zone = cv2.dilate((u > 0.25).astype(np.uint8), np.ones((A.reach, A.reach), np.uint8)).astype(np.float32)
    zone[:int(HH * A.top)] = (u[:int(HH * A.top)] > 0.5)          # far from the body at the top (ceiling fan): trust the model only
    m = np.where(known, diff * zone, u)
    m = np.maximum(m, (u > 0.85).astype(np.float32))               # solid core
    mb = (m > 0.5).astype(np.uint8)
    mb = cv2.morphologyEx(mb, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)); mb = cv2.morphologyEx(mb, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    k, lab, st, _ = cv2.connectedComponentsWithStats(mb)            # drop specks that are not the person
    if k > 1:
        keep = [i for i in range(1, k) if st[i, 4] > 1500]
        mb = np.isin(lab, keep).astype(np.uint8)
    inv = 1 - mb; k2, lab2, st2, _ = cv2.connectedComponentsWithStats(inv)   # fill holes inside the body
    for i in range(1, k2):
        x_, y_, w_, h_, a_ = st2[i]
        if a_ < 4000 and x_ > 0 and y_ > 0 and x_ + w_ < HW and y_ + h_ < HH: mb[lab2 == i] = 1
    full = cv2.resize(mb.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
    g = cv2.ximgproc.guidedFilter(fr, full, 6, 1e-3)
    return np.clip(g, 0, 1)

# pass 2: temporal smoothing + composite
tmp = A.out + '.noaudio.mov'
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', f'{FPS}', '-i', '-',
                        '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
prev = None
for n, fr in enumerate(frames()):
    m = matte(fr, n)
    if prev is not None: m = 0.8 * m + 0.2 * prev                # tiny temporal blend, no visible lag
    prev = m
    a = m[..., None]
    out = fr.astype(np.float32) * a + bg * (1 - a)
    enc.stdin.write(np.clip(out, 0, 255).astype(np.uint8).tobytes())
    if (n + 1) % 150 == 0: print(f'gabung: {n + 1} bingkai', file=sys.stderr, flush=True)
enc.stdin.close(); enc.wait()
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-i', A.video, '-map', '0:v', '-map', '1:a?', '-c', 'copy', A.out], check=True)
os.remove(tmp); print(f'{N} bingkai -> {A.out}')
