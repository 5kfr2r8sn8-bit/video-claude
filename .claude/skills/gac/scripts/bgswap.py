#!/usr/bin/env python3
"""Replace the background of a talking-head video with a photo (person mask per frame, U^2-Net human seg).
Usage: python3 bgswap.py VIDEO BG.jpg OUT.mov [--blur 3] [--crop x0,y0,x1,y1] [--shade 0.08]
--crop  part of the background photo to use (e.g. to leave out a watermark)
--blur  background blur (depth of field); --shade darkens the background a little so the person stands out.

Two passes so hands do not flicker:
 1. a mask for every frame = U^2-Net person mask, plus skin-coloured pixels next to the body
    (moving hands are often missed by the person model);
 2. each frame's mask is smoothed against its neighbours in time (5-frame window, upper percentile:
    a hand that is there in most neighbouring frames stays solid), then feathered and composited.
Output keeps the original audio; feed it to build.py as the timeline "video"."""
import os, sys, subprocess, argparse
import numpy as np, cv2
from PIL import Image, ImageOps

ap = argparse.ArgumentParser(); ap.add_argument('video'); ap.add_argument('bg'); ap.add_argument('out')
ap.add_argument('--blur', type=float, default=3); ap.add_argument('--crop'); ap.add_argument('--shade', type=float, default=0.08)
ap.add_argument('--window', type=int, default=5); ap.add_argument('--no-skin', action='store_true')
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

# pass 1: masks
masks = []
for n, fr in enumerate(frames()):
    x = ((cv2.resize(fr, (320, 320), interpolation=cv2.INTER_AREA).astype(np.float32) / 255 - mean) / std).transpose(2, 0, 1)[None]
    o = sess.run(None, {iname: x})[0][0, 0]; o = (o - o.min()) / (o.max() - o.min() + 1e-9)
    m = np.clip((cv2.resize(o, (SW, SH), interpolation=cv2.INTER_CUBIC) - 0.15) / 0.7, 0, 1)
    if not A.no_skin:
        sk = skin(cv2.resize(fr, (SW, SH), interpolation=cv2.INTER_AREA))
        near = cv2.dilate((m > 0.5).astype(np.uint8), np.ones((15, 15), np.uint8)).astype(np.float32)
        near[:SH // 3] = 0                                     # hands: lower two thirds, next to the body
        m = np.maximum(m, cv2.GaussianBlur(sk * near, (0, 0), 1.0))
    masks.append(m.astype(np.float16))
    if (n + 1) % 150 == 0: print(f'topeng: {n + 1} bingkai', file=sys.stderr, flush=True)
M = np.stack(masks).astype(np.float32); N = len(M); r = A.window // 2

# pass 2: temporal smoothing + composite
tmp = A.out + '.noaudio.mov'
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', f'{FPS}', '-i', '-',
                        '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
for n, fr in enumerate(frames()):
    win = M[max(0, n - r):min(N, n + r + 1)]
    m = np.percentile(win, 70, axis=0)                          # solid if present in most neighbouring frames
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))   # close pin-holes inside the hand
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_CUBIC)
    a = cv2.GaussianBlur(np.clip(m, 0, 1), (0, 0), 1.5)[..., None]
    out = fr.astype(np.float32) * a + bg * (1 - a)
    enc.stdin.write(np.clip(out, 0, 255).astype(np.uint8).tobytes())
    if (n + 1) % 150 == 0: print(f'gabung: {n + 1} bingkai', file=sys.stderr, flush=True)
enc.stdin.close(); enc.wait()
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-i', A.video, '-map', '0:v', '-map', '1:a?', '-c', 'copy', A.out], check=True)
os.remove(tmp); print(f'{N} bingkai -> {A.out}')
