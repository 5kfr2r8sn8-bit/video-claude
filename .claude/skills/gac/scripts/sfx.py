"""Synthesised sound effects (no internet, no sample library needed).
Each function returns mono float32 at 48 kHz in -1..1."""
import numpy as np, wave
SR = 48000
import os, subprocess
SFX_DIRS = [os.environ.get('GAC_SFX_DIR', ''), os.path.join(os.getcwd(), 'sfx')]   # optional real sound files; otherwise synthesised
_FILES = {}
def from_file(name):
    """Real sound files beat synthesis: <sfx dir>/<name>.(wav|mp3|m4a) is used when present.
    Returns (samples, hit) where hit = sample index where the sound 'lands' (end of the loud part, for risers)."""
    if name in _FILES: return _FILES[name]
    for d in SFX_DIRS:
        for ext in ('wav', 'mp3', 'm4a', 'aif'):
            f = os.path.join(d, f'{name}.{ext}')
            if d and os.path.exists(f):
                raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True).stdout
                x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
                blk = SR // 50; lv = np.array([np.sqrt((x[i:i + blk] ** 2).mean() + 1e-12) for i in range(0, len(x), blk)])
                loud = np.nonzero(lv > lv.max() * 0.25)[0]; hit = (loud[-1] + 1) * blk if len(loud) else len(x)
                _FILES[name] = (x, hit); return _FILES[name]
    _FILES[name] = None; return None
def _t(d): return np.arange(int(SR * d)) / SR
def _env(n, a=0.005, r=None):
    e = np.ones(n); na = max(1, int(SR * a)); e[:na] = np.linspace(0, 1, na)
    if r: e *= np.exp(-np.arange(n) / (SR * r))
    return e
def _lp(x, k):
    k = max(1, int(k)); return np.convolve(x, np.ones(k) / k, mode='same')
def whoosh(d=0.35):
    t = _t(d); n = np.random.randn(len(t)); out = np.zeros_like(t)
    for i in range(0, len(t), 512):  # sweep a low-pass from dark to bright and back
        p = i / len(t); k = 2 + 30 * (1 - np.sin(np.pi * p)); out[i:i+512] = _lp(n, k)[i:i+512]
    return 0.6 * out * np.sin(np.pi * t / d) ** 2
def pop(d=0.09):
    t = _t(d); f = 900 * np.exp(-t * 30) + 300
    return 0.7 * np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(len(t), 0.002, 0.025)
def click(d=0.03):
    t = _t(d); return 0.5 * np.random.randn(len(t)) * _env(len(t), 0.0005, 0.004)
def tick(d=0.04):
    t = _t(d); return 0.45 * np.sin(2 * np.pi * 3200 * t) * _env(len(t), 0.0005, 0.006)
def impact(d=0.7):
    t = _t(d); f = 110 * np.exp(-t * 4) + 40
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(len(t), 0.002, 0.25)
    hit = _lp(np.random.randn(len(t)), 6) * _env(len(t), 0.001, 0.03)
    return 0.9 * body + 0.4 * hit
def riser(d=1.0):
    t = _t(d); f = 200 + 1400 * (t / d) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR); noise = _lp(np.random.randn(len(t)), 4)
    return 0.35 * (0.6 * tone + 0.4 * noise) * (t / d) ** 1.5
def coin(d=0.6):
    t = _t(d); a = np.sin(2 * np.pi * 1976 * t) * _env(len(t), 0.001, 0.08)
    b = np.zeros_like(t); s = int(SR * 0.07); b[s:] = np.sin(2 * np.pi * 2637 * t[:-s]) * _env(len(t) - s, 0.001, 0.2)
    return 0.4 * (a + b)
def hit(d=0.45):
    """Big-word accent that phone speakers can play: a short rising whoosh into a mid-range thud
    (fundamental ~220 Hz with harmonics) plus a bright click. The old 'impact' sits at 40-150 Hz,
    which phones cannot reproduce, so it was silent on TikTok."""
    t = _t(d); pre = int(SR * 0.12)
    sw = whoosh(0.12) * 0.7
    tt = t[: len(t) - pre]; f = 260 * np.exp(-tt * 9) + 160
    ph = 2 * np.pi * np.cumsum(f) / SR
    thud = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)) * _env(len(tt), 0.002, 0.09)
    clk = _lp(np.random.randn(len(tt)), 2) * _env(len(tt), 0.0005, 0.012)
    out = np.zeros_like(t); out[:pre] = sw[:pre]; out[pre:] = 0.75 * thud + 0.35 * clk
    return out

def _verb(x, d=0.6, mix=0.25):
    """tiny reverb tail: a few decaying echoes so synthetic hits don't sound dry"""
    out = np.concatenate([x, np.zeros(int(SR * d))])
    for k, (ms, g) in enumerate([(23, .5), (41, .4), (67, .3), (97, .22), (131, .15), (179, .1)]):
        s = int(SR * ms / 1000); out[s:s + len(x)] += mix * g * x
    return out
def swoosh(d=0.5):
    """A: airy swoosh (no thud) - calm, premium"""
    t = _t(d); n = np.random.randn(len(t)); out = np.zeros_like(t)
    for i in range(0, len(t), 256):
        p = i / len(t); k = 1 + 18 * (1 - p) ** 2; out[i:i+256] = _lp(n, k)[i:i+256]
    return _verb(0.5 * out * np.sin(np.pi * t / d) ** 3, 0.4, 0.3)
def boom(d=0.9):
    """B: cinematic boom - sub + mid body + noise burst + tail"""
    t = _t(d); f = 70 * np.exp(-t * 3) + 45
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(len(t), 0.003, 0.35)
    fm = 180 * np.exp(-t * 6) + 120; ph = 2 * np.pi * np.cumsum(fm) / SR
    mid = (np.sin(ph) + 0.6 * np.sin(2 * ph) + 0.35 * np.sin(3 * ph)) * _env(len(t), 0.002, 0.12)
    burst = _lp(np.random.randn(len(t)), 3) * _env(len(t), 0.001, 0.05)
    return _verb(0.55 * sub + 0.45 * mid + 0.35 * burst, 0.7, 0.3)
def shimmer(d=0.9):
    """C: gold shimmer - bell-like ding with sparkle (fits gold/emas)"""
    t = _t(d); out = np.zeros_like(t)
    for f, a, r in [(1568, .5, .35), (2349, .35, .25), (3136, .25, .18), (4699, .15, .12)]:
        out += a * np.sin(2 * np.pi * f * t + 1.5 * np.sin(2 * np.pi * f * 1.41 * t) * np.exp(-t * 8)) * _env(len(t), 0.001, r)
    return _verb(0.45 * out, 0.6, 0.35)
def punch(d=0.35):
    """D: punchy kick-thud - short, modern, TikTok-style"""
    t = _t(d); f = 160 * np.exp(-t * 25) + 55
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(len(t), 0.001, 0.1)
    clk = _lp(np.random.randn(len(t)), 1) * _env(len(t), 0.0003, 0.006)
    return np.tanh(1.8 * (0.9 * body + 0.4 * clk)) * 0.8
def alarm(d=0.7):
    """warning: two short two-tone beeps (for scam / amaran scenes), bright enough for phone speakers"""
    t = _t(d); out = np.zeros_like(t)
    for k, (st, f) in enumerate([(0.0, 1180), (0.17, 880), (0.36, 1180), (0.53, 880)]):
        s0 = int(SR * st); n = int(SR * 0.13); tt = np.arange(n) / SR
        b = np.sign(np.sin(2 * np.pi * f * tt)) * 0.35 + np.sin(2 * np.pi * f * tt) * 0.4
        e = np.ones(n); e[:60] = np.linspace(0, 1, 60); e[-200:] = np.linspace(1, 0, 200)
        out[s0:s0 + n] += _lp(b, 3) * e
    return 0.55 * out
def boing(d=0.6):
    """funny 'boing': springy pitch wobble (for humour labels)"""
    t = _t(d); f = 260 + 140 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 4) + 120 * np.exp(-t * 6)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return 0.55 * (np.sin(ph) + 0.3 * np.sin(2 * ph)) * _env(len(t), 0.003, 0.22)
def swell(d=1.15):
    """riser 'swell': low saw hum that grows and opens up (filter sweep) into a bright airy noise,
    stopping sharply at its peak (lands on the moment, like a reverse cymbal)"""
    t = _t(d); p = t / d
    ph = 2 * np.pi * np.cumsum(70 + 40 * p ** 2) / SR
    saw = sum(np.sin(k * ph) / k for k in range(1, 18))          # rich low saw
    out = np.zeros_like(t); n = np.random.randn(len(t)); blk = 384
    for i in range(0, len(t), blk):                               # low-pass that opens: dark hum -> bright
        q = p[min(i, len(t) - 1)]; k = max(1, int(60 * (1 - q) ** 2.2) + 1)
        nk = max(1, int(14 * (1 - q) ** 1.5) + 1)
        out[i:i + blk] = (_lp(saw, k)[i:i + blk] * (0.9 - 0.4 * q) + _lp(n, nk)[i:i + blk] * (0.15 + 0.85 * q ** 2.5))
    env = p ** 2.4; env[-int(SR * 0.012):] *= np.linspace(1, 0, int(SR * 0.012))
    return _verb(0.5 * out * env, 0.3, 0.2)
LIB = dict(swell=swell, boing=boing, alarm=alarm, swoosh=swoosh, boom=boom, shimmer=shimmer, punch=punch, hit=hit, whoosh=whoosh, pop=pop, click=click, tick=tick, impact=impact, riser=riser, coin=coin)
def write(path, x):
    x = np.clip(x, -1, 1); y = (x * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes())
def render_track(events, total, path, gain_db=-14):
    """events: list of (time_sec, name). Writes one mono wav covering the whole video."""
    np.random.seed(3); out = np.zeros(int(SR * (total + 1)))
    for t, name in events:
        ff = from_file(name)
        if ff is None and name not in LIB: continue
        if ff is not None:   # user's own sound file; risers land their cut-off on the moment
            x, hit = ff; s = int(SR * max(0, t))
            if name in ('riser', 'swell'):
                s -= hit
                if s < 0: x = x[-s:]; s = 0
            e = min(len(out), s + len(x)); out[s:e] += x[:e - s] * 10 ** (6 / 20); continue
        x = LIB[name](); s = int(SR * max(0, t))
        if name in ('riser', 'swell'): s = max(0, s - len(x) + (int(SR * 0.3) if name == 'swell' else 0))  # risers end on the moment
        if name == 'hit': s = max(0, s - int(SR * 0.12))  # the thud lands on the moment, its whoosh just before
        e = min(len(out), s + len(x)); out[s:e] += x[:e - s]
    out *= 10 ** (gain_db / 20); write(path, out[:int(SR * total)])
