#!/usr/bin/env python3
"""Analyse a talking-head video before editing.
Usage: python3 analyze.py VIDEO OUTDIR
Writes OUTDIR/analysis.json, OUTDIR/sheet.jpg (1 frame/sec contact sheet),
OUTDIR/captions.json (burned-in captions found by OCR, may be empty) and
OUTDIR/speech.json (speech chunks between pauses)."""
import sys, os, json, subprocess, re, glob
import numpy as np
from PIL import Image

def run(cmd): return subprocess.run(cmd, capture_output=True, text=True)

def probe(v):
    d = float(run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',v]).stdout)
    tmp = '/tmp/_probe.png'
    run(['ffmpeg','-v','error','-y','-ss','1','-i',v,'-frames:v','1',tmp])  # autorotated frame
    w, h = Image.open(tmp).size
    has_audio = 'audio' in run(['ffprobe','-v','error','-show_entries','stream=codec_type','-of','csv=p=0',v]).stdout
    return d, w, h, has_audio

def speech_chunks(v, dur, noise='-30dB', mind=0.3):
    err = run(['ffmpeg','-i',v,'-af',f'silencedetect=noise={noise}:d={mind}','-f','null','-']).stderr
    st = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', err)]
    en = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', err)]
    sil = list(zip(st, en + [dur] * (len(st) - len(en))))
    chunks, t = [], 0.0
    for a, b in sil:
        if a - t > 0.15: chunks.append([round(t, 2), round(a, 2)])
        t = b
    if dur - t > 0.15: chunks.append([round(t, 2), round(dur, 2)])
    return sil, chunks

def captions(v, out, w, h):
    """Find burned-in captions (e.g. CapCut auto captions) in the lower band."""
    import shutil
    if not shutil.which('tesseract'):  # no OCR installed (normal on a Mac): rely on the SRT instead
        print('note: tesseract not found, skipping burned-in caption OCR', file=sys.stderr); return []
    d = os.path.join(out, '_cap'); os.makedirs(d, exist_ok=True)
    y0, y1 = int(h * 0.60), int(h * 0.90)
    run(['ffmpeg','-v','error','-y','-i',v,'-vf',f'fps=10,crop={w}:{y1-y0}:0:{y0}',f'{d}/c_%05d.png'])
    fs = sorted(glob.glob(f'{d}/c_*.png'))
    def mask(p):
        a = np.asarray(Image.open(p).convert('RGB')).astype(int)
        return (a.min(axis=2) > 235).astype(np.uint8)
    segs, cur, prev = [], None, None
    for i, p in enumerate(fs):
        m = mask(p); s = int(m.sum()); t = i / 10
        changed = prev is not None and (m != prev).sum() > max(1500, 0.25 * max(s, 1))
        if s > 2500 and (cur is None or changed):
            if cur: cur['end'] = t; segs.append(cur)
            cur = dict(start=t, end=None, frame=p)
        elif s <= 2500 and cur:
            cur['end'] = t; segs.append(cur); cur = None
        prev = m
    if cur: cur['end'] = len(fs) / 10; segs.append(cur)
    res = []
    for s in segs:
        if s['end'] - s['start'] < 0.25: continue
        mid = fs[min(len(fs) - 1, int((s['start'] + s['end']) / 2 * 10))]
        txt = run(['tesseract', _clean(mid), '-', '--psm', '6']).stdout
        txt = ' '.join(txt.split())
        res.append(dict(start=round(s['start'], 2), end=round(s['end'], 2), text=txt))
    return res

def _clean(p):
    # keep only white caption letters that sit next to a dark outline
    import cv2
    a = np.asarray(Image.open(p).convert('RGB')).astype(int)
    white = (a.min(axis=2) > 225) & ((a.max(axis=2) - a.min(axis=2)) < 25)
    dark = cv2.dilate((a.max(axis=2) < 70).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    txt = white & dark
    out = np.where(txt, 0, 255).astype(np.uint8)
    im = Image.fromarray(out).resize((out.shape[1] * 2, out.shape[0] * 2))
    q = p.replace('.png', '_bw.png'); im.save(q); return q

if __name__ == '__main__':
    v, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
    dur, w, h, has_audio = probe(v)
    sil, chunks = speech_chunks(v, dur) if has_audio else ([], [])
    run(['ffmpeg','-v','error','-y','-i',v,'-vf',
         "fps=1,scale=200:-1,drawtext=text='%{pts\\:hms}':x=4:y=4:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=8x8",
         '-frames:v','1',os.path.join(out,'sheet.jpg')])
    caps = captions(v, out, w, h)
    json.dump(caps, open(os.path.join(out,'captions.json'),'w'), indent=1, ensure_ascii=False)
    json.dump(chunks, open(os.path.join(out,'speech.json'),'w'))
    info = dict(video=v, duration=round(dur,2), width=w, height=h, vertical=h > w, has_audio=has_audio,
                silences=[[round(a,2),round(b,2)] for a,b in sil], speech_chunks=chunks,
                burned_captions=len(caps))
    json.dump(info, open(os.path.join(out,'analysis.json'),'w'), indent=1)
    print(json.dumps(info, indent=1))
    for c in caps: print(f"{c['start']:6.2f}-{c['end']:6.2f}  {c['text']}")
