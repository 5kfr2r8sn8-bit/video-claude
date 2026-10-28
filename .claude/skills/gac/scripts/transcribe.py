#!/usr/bin/env python3
"""Speech-to-text for the user's videos (faster-whisper large-v3-turbo on the CPU; works in the claude.ai sandbox too).
Usage: python3 transcribe.py VIDEO [OUT_BASE] [--lang ms] [--vocab "extra, words"] [--profile gac_profile.json] [--force]
Writes OUT_BASE.srt (CapCut-style lines, split at pauses) and OUT_BASE.words.json
([{"w": word, "s": start, "e": end, "p": probability}, ...]). OUT_BASE defaults to VIDEO + '.whisper'; an existing SRT of that name (any letter case) is never overwritten.
Low-probability words are listed at the end so the plan can ask the user to check them."""
import sys, os, json, subprocess, tempfile

# Local copy if one exists (Claude Code on a Mac), otherwise faster-whisper downloads it by name (~1.6 GB, cached).
_LOCAL = [os.environ.get('WHISPER_MODEL', ''), os.path.expanduser('~/.local/share/edit-video-pro/models/large-v3-turbo'),
          os.path.expanduser('~/.local/share/gac/models/large-v3-turbo')]
MODEL = next((p for p in _LOCAL if p and os.path.exists(os.path.join(p, 'model.bin'))), None)
# claude.ai chats often block huggingface.co but allow GitHub release downloads: same model files, mirrored there
GH_MIRROR = 'https://github.com/sirujang/gac-models/releases/download/whisper-turbo/'
GH_FILES = ['config.json', 'preprocessor_config.json', 'tokenizer.json', 'vocabulary.json', 'model.bin']
def get_model():
    if MODEL: return MODEL
    hf_ok = subprocess.run(['curl', '-sf', '-o', '/dev/null', '--max-time', '6', 'https://huggingface.co'], capture_output=True).returncode == 0
    if hf_ok:
      try:   # 1) Hugging Face (normal faster-whisper download)
        from faster_whisper.utils import download_model
        return download_model('large-v3-turbo')
      except Exception as e:
        print(f'Hugging Face gagal ({type(e).__name__}); cuba GitHub...', file=sys.stderr)
    else: print('Hugging Face disekat; muat turun model dari GitHub (~1.6 GB, sekali setiap chat)...', file=sys.stderr)
    dst = os.path.expanduser('~/.cache/gac/large-v3-turbo'); os.makedirs(dst, exist_ok=True)
    for f in GH_FILES:   # 2) GitHub release mirror (~1.6 GB, once per chat)
        p = os.path.join(dst, f)
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            r = subprocess.run(['curl', '-fL', '--retry', '3', '-o', p + '.part', GH_MIRROR + f], capture_output=True, text=True)
            if r.returncode != 0:
                sys.exit('Tak dapat muat turun model Whisper (Hugging Face dan GitHub disekat). Minta SRT dari CapCut atau skrip yang ditaip.')
            os.replace(p + '.part', p)
    return dst
# Gold-dealer vocabulary nudges Whisper toward the right spellings of terms it otherwise mishears.
VOCAB = ("Public Gold, akaun emas GAP, GAP, GSAP, dinar, goldbar, gold bar, emas 916, emas 999, "
         "spread, gram, Ar-Rahnu, PG Jewel, simpanan emas, tuan puan, InsyaAllah, RM")

# Word-level fixes for terms Whisper reliably mishears in Malay gold-dealer talk. Keys are lower-case
# word sequences (after joining "e" + "-commerce" style pieces); values replace them, keeping the timing.
WORD_FIXES = {('eko', 'mask'): ('akaun', 'emas'), ('ekau', 'mas'): ('akaun', 'emas'), ('e-commerce',): ('akaun', 'emas'),
              ('ecommerce',): ('akaun', 'emas'), ('akaun', 'mas'): ('akaun', 'emas'), ('penyimpak',): ('penyimpan',),
              ('gamenya',): ('gramnya',), ('gap',): ('GAP',), ('gsap',): ('GSAP',), ('grup',): ('group',),
              ('plus-plus',): ('++',), ('splitnya',): ('spreadnya',), ('public', 'gold'): ('Public', 'Gold'),
              ('mask',): ('emas',), ('akaun', 'akaun'): ('akaun',),
              # from the fungsi5gram test (2026-10-04)
              ('golubah',): ('goldbar',), ('golba',): ('goldbar',), ('public', 'goal'): ('Public', 'Gold'),
              ('account',): ('akaun',), ('grab', 'emas'): ('gram', 'emas'), ('motocash',): ('motor', 'cash'),
              ('menaikkan', 'umrah'): ('menunaikan', 'umrah'),
              # from the kelebihangap test (2026-10-04)
              ('eko', 'emas'): ('akaun', 'emas'), ('ikut', 'emas', ): ('akaun', 'emas'), ('stop', 'emas'): ('stok', 'emas'),
              ('kelebaran',): ('kelebihan',), ('grant', 'emas'): ('gram', 'emas'), ('pilih', 'video'): ('pin', 'video'),
              # from the 5gram test (2026-10-08)
              ('ekon', 'mas'): ('akaun', 'emas'), ('menabur',): ('menabung',), ('golbol',): ('goldbar',),
              ('sekeping', 'global'): ('sekeping', 'goldbar'), ('seketul', 'global'): ('seketul', 'goldbar')}
# Fixes for words Whisper reliably mishears in Malay gold-dealer talk (applied to the joined text).
# Text-level tidy-ups only (word fixes live in WORD_FIXES; a loose regex here once turned every "emas" into "akaun emas").
FIXES = [(r'(\d)\s+,(\d{3})', r'\1,\2'), (r'(\w)\s+-(\w)', r'\1-\2'), (r'\s+([,.?!])', r'\1')]

def fix_text(t):
    import re
    for a, b in FIXES: t = re.sub(a, b, t, flags=re.I)
    return re.sub(r'\s{2,}', ' ', t).strip()

def join_words(ws):
    """Join Whisper word pieces: pieces starting with punctuation or '-' attach to the previous word."""
    out = ''
    for w in ws:
        out += w if (w[:1] in ',.?!-' or not out) else ' ' + w
    return out

def ts(t):
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f'{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'

def clean_words(words):
    """Attach punctuation/hyphen pieces to the word before, then apply WORD_FIXES (longest match first)."""
    merged = []
    for w in words:
        if merged and w['w'][:1] in ',.?!-' :
            merged[-1] = dict(merged[-1], w=merged[-1]['w'] + w['w'], e=w['e'], p=min(merged[-1]['p'], w['p']))
        else: merged.append(dict(w))
    out, i = [], 0
    while i < len(merged):
        for n in (2, 1):
            key = tuple(x['w'].lower().strip(',.?!') for x in merged[i:i + n])
            if len(key) == n and key in WORD_FIXES:
                rep_, a, b = WORD_FIXES[key], merged[i]['s'], merged[i + n - 1]['e']
                tail = merged[i + n - 1]['w'][len(merged[i + n - 1]['w'].rstrip(',.?!')):]
                step = (b - a) / len(rep_)
                for k, r in enumerate(rep_):
                    out.append(dict(w=r + (tail if k == len(rep_) - 1 else ''), s=round(a + k * step, 3), e=round(a + (k + 1) * step, 3), p=1.0))
                i += n; break
        else:
            out.append(merged[i]); i += 1
    return out

def lines_from_words(words, max_gap=0.3, max_len=2.8, max_words=7):
    """Group words into subtitle lines at pauses, sentence ends, or when a line gets long."""
    out, cur = [], []
    for w in words:
        if cur and (w['s'] - cur[-1]['e'] > max_gap or w['e'] - cur[0]['s'] > max_len or len(cur) >= max_words
                    or cur[-1]['w'].rstrip().endswith(('.', '?', '!', ','))):
            out.append(cur); cur = []
        cur.append(w)
    if cur: out.append(cur)
    return [(ln[0]['s'], ln[-1]['e'], fix_text(join_words([x['w'] for x in ln]))) for ln in out]

def main():
    args = sys.argv[1:]
    if not args: sys.exit(__doc__)
    video = args[0]; out = args[1] if len(args) > 1 and not args[1].startswith('--') else os.path.splitext(video)[0] + '.whisper'
    # never overwrite the user's own SRT (macOS file names are case-insensitive: kelebihangap.srt == kelebihanGAP.srt)
    folder = os.path.dirname(os.path.abspath(out)) or '.'
    taken = {f.lower() for f in os.listdir(folder)} if os.path.isdir(folder) else set()
    if (os.path.basename(out) + '.srt').lower() in taken and '--force' not in args:
        sys.exit(f'{out}.srt already exists (maybe the user\'s own SRT). Use another OUT name, e.g. {out}.whisper')
    lang = args[args.index('--lang') + 1] if '--lang' in args else 'ms'
    vocab = VOCAB + (', ' + args[args.index('--vocab') + 1] if '--vocab' in args else '')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import theme
    prof = theme.load(args[args.index('--profile') + 1] if '--profile' in args else None)
    if prof.get('perkataan'): vocab += ', ' + ', '.join(prof['perkataan'])
    for k, v in (prof.get('betulkan') or {}).items():   # participant's own fixes, e.g. {"cloud": "Claude"}
        WORD_FIXES[tuple(k.lower().split())] = tuple(v.split())
    wav = os.path.join(tempfile.gettempdir(), '_stt.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-vn', '-ac', '1', '-ar', '16000', wav], check=True)
    from faster_whisper import WhisperModel
    model = WhisperModel(get_model(), device='cpu', compute_type='int8')
    segs, info = model.transcribe(wav, language=lang, word_timestamps=True, vad_filter=True,
                                  initial_prompt=vocab, beam_size=5, condition_on_previous_text=False)
    words = []
    for sg in segs:
        for w in sg.words or []:
            words.append(dict(w=w.word.strip(), s=round(w.start, 3), e=round(w.end, 3), p=round(w.probability, 3)))
    words = clean_words(words)
    json.dump(words, open(out + '.words.json', 'w'), ensure_ascii=False, indent=0)
    lines = lines_from_words(words)
    with open(out + '.srt', 'w', encoding='utf-8') as f:
        for i, (a, b, t) in enumerate(lines, 1): f.write(f'{i}\n{ts(a)} --> {ts(b)}\n{t}\n\n')
    unsure = [w for w in words if w['p'] < 0.5]
    print(json.dumps(dict(srt=out + '.srt', words=out + '.words.json', lines=len(lines), words_n=len(words),
                          language=info.language, unsure=[f"{w['w']} @{w['s']:.1f}s" for w in unsure][:40]),
                     ensure_ascii=False, indent=1))

if __name__ == '__main__': main()
