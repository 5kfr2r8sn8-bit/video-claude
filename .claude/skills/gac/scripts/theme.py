"""Participant profile -> look of every GAC video (accent colour, font, CTA, extra words).
build.py calls apply() once per render; every script reads the colours from here at draw time."""
import os, json, colorsys
HERE = os.path.dirname(os.path.abspath(__file__)); FONT_DIR = os.path.join(os.path.dirname(HERE), 'assets', 'fonts')
PRESETS = dict(emas=(247, 178, 40), biru=(56, 140, 255), hijau=(30, 190, 120), marun=(176, 38, 72),
               ungu=(140, 92, 246), putih=(245, 245, 245))
FONTS = dict(montserrat=('Montserrat.ttf', 'Black'), jakarta=('PlusJakartaSans.ttf', 'ExtraBold'), inter=('Inter.ttf', 'Black'))
A = PRESETS['emas']; RIM = (214, 158, 36); LIGHT = (255, 208, 96); DARK = (186, 114, 14); ON = (40, 26, 0)
PROFILE = {}

def _rgb(c):
    if isinstance(c, (list, tuple)): return tuple(int(v) for v in c[:3])
    c = str(c).strip().lower()
    if c in PRESETS: return PRESETS[c]
    c = c.lstrip('#'); return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
def _shade(c, k):   # k > 0 lighter, k < 0 darker (in HLS lightness)
    h, l, s = colorsys.rgb_to_hls(*[v / 255 for v in c]); l = max(0, min(1, l + k))
    return tuple(int(v * 255) for v in colorsys.hls_to_rgb(h, l, s))
def lum(c): return (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) / 255

def load(path=None):
    for p in [path, os.environ.get('GAC_PROFILE'), 'gac_profile.json', os.path.expanduser('~/.config/gac/profile.json'),
              '/mnt/user-data/uploads/gac_profile.json']:
        if p and os.path.exists(p): return json.load(open(p))
    return {}

def apply(profile=None, build=None):
    """Set the accent colour + font everywhere. profile: dict, path or None (auto-find)."""
    global A, RIM, LIGHT, DARK, ON, PROFILE
    p = profile if isinstance(profile, dict) else load(profile); PROFILE = p
    A = _rgb(p.get('warna', 'emas')); RIM = _shade(A, -0.08); LIGHT = _shade(A, 0.14); DARK = _shade(A, -0.2)
    ON = (20, 16, 10) if lum(A) > 0.55 else (255, 255, 255)        # text on an accent pill
    import doc, motion
    motion.GOLD = A
    doc.PALETTES['gold'] = dict(hl=A, mark=DARK); doc.PAL = doc.PALETTES['gold']
    doc.THEMES['clear']['hl_ink'] = ON
    fn, heavy = FONTS.get(str(p.get('font', 'montserrat')).lower(), FONTS['montserrat']); path = os.path.join(FONT_DIR, fn)
    for lst, w in ((doc.REG, 'Medium'), (doc.BOLD, 'Bold'), (doc.HEAVY, heavy)): lst[0] = (path, 0, w)
    doc._fc.clear()
    if build is not None:
        build.COL['gold'] = A; build.COL['accent'] = A; build.COL['yellow'] = A; build._FC.clear()
    return p
