"""Vlog1: cut the day's clips into one vlog base (video + ambient/speech audio).
Each segment: (src_in, src_out, speed, audio_gain, extra video filter). Encoded one by one, then joined."""
import json, os, subprocess
SRC = 'rakaman/vlog1.mov'; TMP = 'build/vlog1/segs'; OUT = 'build/hf/vlog1/assets/base.mp4'
BLUR_NAME = 'split[a][b];[b]crop=432:211:0:826,boxblur=20:2[bb];[a][bb]overlay=0:826'   # anak's name on the Quran
FOOD = 'crop=594:1056:60:864,scale=1080:1920'   # plate only: background diners (no tudung) cropped out
SEGS = [
    (0.3, 2.3, 1.0, 0.25, ''),          # dashboard - title
    (2.4, 5.6, 1.0, 0.25, ''),          # pagi, sekolah mengaji
    (13.8, 15.8, 1.0, 0.25, BLUR_NAME), # Al-Quran (nama anak dikaburkan)
    (23.8, 34.4, 2.0, 0.15, ''),        # perjalanan ke KL
    (34.6, 42.3, 1.5, 0.2, ''),         # lif
    (42.5, 46.5, 1.0, 0.25, ''),        # G100 Academy
    (47.0, 52.6, 1.2, 0.2, ''),         # kerja & meeting
    (53.1, 58.3, 1.0, 1.0, ''),         # sesi perkongsian (suara)
    (61.45, 64.45, 1.0, 1.0, ''),       # "...dipecah-pecahkan ikut group"
    (69.0, 72.4, 1.0, 0.3, ''),         # group (bahagian tanpa wanita tak bertudung)
    (75.7, 83.0, 1.6, 0.2, ''),         # The Exchange TRX
    (88.8, 89.9, 0.6, 0.2, FOOD),       # makanan
    (84.6, 88.6, 1.0, 0.15, ''),        # menara, kad penutup
]
os.makedirs(TMP, exist_ok=True); os.makedirs(os.path.dirname(OUT), exist_ok=True)
parts, t, marks = [], 0.0, []
for i, (a, b, sp, g, vf) in enumerate(SEGS):
    p = f'{TMP}/s{i:02d}.mov'
    v = (vf + ',' if vf else '') + f'setpts=PTS/{sp},fps=30,format=yuv420p'
    at = f'atempo={sp}' if sp != 1.0 else 'anull'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', str(a), '-t', str(b - a), '-i', SRC,
                    '-filter_complex', f'[0:v]{v}[v];[0:a]{at},volume={g},afade=t=in:d=0.04,afade=t=out:st={(b - a) / sp - 0.05:.3f}:d=0.05[a]',
                    '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-g', '30',
                    '-c:a', 'pcm_s16le', '-ar', '48000', p], check=True)
    d = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))
    marks.append((round(t, 3), round(t + d, 3))); t += d; parts.append(p)
open(f'{TMP}/list.txt', 'w').write(''.join(f"file '{os.path.abspath(p)}'\n" for p in parts))
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', f'{TMP}/list.txt', '-c:v', 'libx264', '-crf', '16',
                '-preset', 'medium', '-g', '30', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', OUT], check=True)
json.dump(marks, open('build/vlog1/marks.json', 'w'))
print(round(t, 2), marks)
