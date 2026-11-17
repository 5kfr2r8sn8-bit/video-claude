"""Vlog1: cut the day's clips into one vlog base (video + ambient/speech audio).
Each segment: (src_in, src_out, speed, audio_gain, extra video filter). Encoded one by one, then joined."""
import json, os, subprocess
SRC = 'rakaman/vlog2.mov'; TMP = 'build/vlog2/segs'; OUT = 'build/hf/vlog2/assets/base.mp4'
BLUR_NAME = 'split[a][b];[b]crop=432:211:0:826,boxblur=20:2[bb];[a][bb]overlay=0:826'   # anak's name on the Quran
FOOD = 'crop=594:1056:60:864,scale=1080:1920'   # plate only: background diners (no tudung) cropped out
BLUR_PAPER = 'split[a][b];[b]crop=330:440:500:1480,gblur=sigma=9[bb];[a][bb]overlay=500:1480'   # soalan exam pada kertas dikaburkan
SEGS = [   # Vlog2: persediaan exam pelajar (bunyi asal dibisukan; muzik ditambah kemudian)
    (0.2, 3.6, 1.0, 0, ''),               # bilik guru - tajuk
    (3.8, 9.6, 1.3, 0, ''),               # fotostat
    (9.8, 17.6, 1.25, 0, BLUR_PAPER),     # siapkan kertas soalan
    (17.6, 19.6, 0.6, 0, BLUR_PAPER),     # penutup
]
os.makedirs(TMP, exist_ok=True); os.makedirs(os.path.dirname(OUT), exist_ok=True)
parts, t, marks = [], 0.0, []
for i, seg in enumerate(SEGS):
    p = f'{TMP}/s{i:02d}.mov'
    if seg[0] == 'img':   # still photo: slow push-in, silent
        _, img, d = seg; n = int(d * 30)
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-loop', '1', '-i', img, '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', str(d),
                        '-filter_complex', f"[0:v]scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,zoompan=z='1+0.06*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,format=yuv420p[v]",
                        '-map', '[v]', '-map', '1:a', '-c:v', 'libx264', '-crf', '16', '-g', '30', '-c:a', 'pcm_s16le', p], check=True)
        marks.append((round(t, 3), round(t + d, 3))); t += d; parts.append(p); continue
    a, b, sp, g, vf = seg
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
json.dump(marks, open('build/vlog2/marks.json', 'w'))
print(round(t, 2), marks)
