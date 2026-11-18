"""Vlog3: one stop centre emas (ikut tingkat). Many sources -> one silent base clip (music added in the composition).
Segment: (src, in, out, speed) for video, ('img', path, dur, mode) for photos (mode 'cover' = slow push-in, 'contain' = whole photo on blurred copy)."""
import json, os, subprocess
D = 'rakaman/vlog3'; TMP = 'build/vlog3/segs'; OUT = 'build/hf/vlog3/assets/base.mp4'
V = lambda n: f'{D}/{n}.mov'
I = lambda n: f'{D}/{n}.jpeg'
SEGS = [   # v3 (pengguna): guna SEMUA gambar yang diberi
    (V('IMG_0027'), 0.0, 3.5, 1.0),        # hook: lobi Public Gold ATM
    (V('IMG_0027'), 3.5, 19.9, 2.2),       # Ground floor: Gold ATM
    (V('IMG_9993'), 0.0, 7.6, 1.3),        # Tingkat 1: kaunter
    ('img', I('IMG_0814'), 2.0, 'cover'),  # gold bar & dinar
    ('img', I('IMG_0809'), 2.0, 'cover'),  # dulang perhiasan
    ('img', I('IMG_0792'), 2.4, 'cover'),  # cincin
    ('img', I('IMG_0793'), 1.8, 'cover'),  # cincin 2
    ('img', I('IMG_0796'), 1.8, 'cover'),  # gelang
    ('img', I('IMG_0797'), 1.8, 'cover'),  # gelang 2
    (V('IMG_0845'), 41.0, 45.0, 0.8),      # cuci mata perhiasan: bahagian hujung (pengguna: lebih cantik, cahaya ok)
    (V('IMG_0846'), 0.0, 15.8, 2.4),       # Tingkat 4: Public Safe
    ('img', I('IMG_0843'), 2.0, 'contain'),  # 3 saiz peti besi
    ('img', I('IMG_0847'), 2.0, 'cover'),  # poster Public Safe
    (V('IMG_0849'), 0.0, 9.7, 1.6),        # Tingkat 8: KDE Ar-Rahnu
    ('img', I('IMG_0853'), 2.2, 'cover'),  # di Ar-Rahnu
    (V('IMG_0027'), 14.0, 19.9, 1.0),      # penutup: lobi
]
os.makedirs(TMP, exist_ok=True); os.makedirs(os.path.dirname(OUT), exist_ok=True)
parts, t, marks = [], 0.0, []
for i, s in enumerate(SEGS):
    p = f'{TMP}/s{i:02d}.mp4'
    if s[0] == 'img':
        _, img, d, mode = s; n = int(d * 30)
        if mode == 'cover':
            vf = (f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
                  f"zoompan=z='1+0.07*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30")
        else:
            vf = ("split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=40,eq=brightness=-0.08[bg];"
                  "[b]scale=1040:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,fps=30")
        cmd = ['ffmpeg', '-y', '-v', 'error', '-loop', '1', '-i', img, '-t', str(d), '-vf', vf + ',format=yuv420p']
    else:
        src, a, b, sp = s; d = (b - a) / sp
        cmd = ['ffmpeg', '-y', '-v', 'error', '-ss', str(a), '-t', str(b - a), '-i', src,
               '-vf', f'scale=1080:1920,setpts=PTS/{sp},fps=30,format=yuv420p', '-an']
    subprocess.run(cmd + ['-c:v', 'libx264', '-crf', '15', '-preset', 'medium', '-g', '30', p], check=True)
    d = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))
    marks.append((round(t, 3), round(t + d, 3))); t += d; parts.append(p)
open(f'{TMP}/list.txt', 'w').write(''.join(f"file '{os.path.abspath(p)}'\n" for p in parts))
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', f'{TMP}/list.txt', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
                '-shortest', '-c:v', 'libx264', '-crf', '15', '-preset', 'medium', '-g', '30', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', OUT], check=True)
json.dump(marks, open('build/vlog3/marks.json', 'w'))
print(round(t, 2), marks)
