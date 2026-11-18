"""Vlog3 'gimik' (pengguna: banyak kesan setiap gambar masuk/keluar, zoom in/out, slow-mo, speed; boleh lebih 1 minit).
Each segment gets its own motion (photos: zin/zout/punch/panl/panr; videos: speed ramps + slow push-in), then all are joined
with xfade transitions. Writes base.mp4 (silent) and marks.json (start/end of every segment in the final timeline)."""
import json, os, subprocess
D = 'rakaman/vlog3'; TMP = 'build/vlog3/fx'; OUT = 'build/hf/vlog3/assets/base.mp4'
V = lambda n: f'{D}/{n}.mov'
I = lambda n: f'{D}/{n}.jpeg'
TR = 0.35   # transition length
SEGS = [   # ('v', src, [(in, out, speed), ...]) or ('i', src, dur, effect[, 'contain'])
    ('v', V('IMG_0027'), [(0.0, 3.5, 1.0)]),                                   # 0 hook
    ('v', V('IMG_0027'), [(3.5, 7.5, 2.5), (7.5, 10.5, 0.7), (10.5, 19.9, 2.6)]),  # 1 Ground: Gold ATM (slow-mo pada mesin ATM)
    ('v', V('IMG_9993'), [(0.0, 3.0, 2.0), (3.0, 5.5, 0.6), (5.5, 7.6, 2.0)]),      # 2 Tingkat 1 kaunter
    ('i', I('IMG_0814'), 2.4, 'punch'),                                           # 3 gold bar & dinar
    ('i', I('IMG_0809'), 2.4, 'zout'),                                            # 4 dulang perhiasan
    ('i', I('IMG_0792'), 2.6, 'panl'),                                            # 5 cincin (kad: keluar emas fizikal)
    ('i', I('IMG_0793'), 1.9, 'punch'),                                           # 6 cincin 2
    ('i', I('IMG_0796'), 1.9, 'zin'),                                             # 7 gelang
    ('i', I('IMG_0797'), 1.9, 'zout'),                                            # 8 gelang 2
    ('v', V('IMG_0845'), [(41.0, 45.0, 0.6)]),                                    # 9 pameran (slow-mo)
    ('v', V('IMG_0846'), [(0.0, 8.0, 2.6), (8.0, 11.0, 0.8), (11.0, 15.8, 2.6)]),   # 10 Tingkat 4 Public Safe
    ('i', I('IMG_0843'), 2.4, 'zin', 'contain'),                                  # 11 saiz peti besi
    ('i', I('IMG_0847'), 2.4, 'zout'),                                            # 12 poster
    ('v', V('IMG_0849'), [(0.0, 4.0, 1.8), (4.0, 7.0, 0.7), (7.0, 9.7, 1.8)]),      # 13 Tingkat 8 KDE Ar-Rahnu
    ('i', I('IMG_0853'), 2.6, 'punch'),                                           # 14 di Ar-Rahnu
    ('v', V('IMG_0027'), [(14.0, 19.9, 1.0)]),                                    # 15 penutup
]
XF = ['hblur', 'slideleft', 'fadewhite', 'circleopen', 'smoothup', 'hblur', 'slideright', 'radial',   # no 'zoomin': it pixelates
      'fadewhite', 'smoothleft', 'circleopen', 'hblur', 'slideup', 'fadewhite', 'hblur']
os.makedirs(TMP, exist_ok=True); os.makedirs(os.path.dirname(OUT), exist_ok=True)
enc = ['-c:v', 'libx264', '-crf', '15', '-preset', 'medium', '-g', '30', '-pix_fmt', 'yuv420p', '-an']

def run(cmd): subprocess.run(['ffmpeg', '-y', '-v', 'error'] + cmd, check=True)
def dur(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))

parts = []
for i, s in enumerate(SEGS):
    p = f'{TMP}/s{i:02d}.mp4'
    if os.path.exists(p) and os.environ.get('REUSE'): parts.append(p); continue   # REUSE=1: only redo the transitions
    if s[0] == 'i':
        img, d, fx = s[1], s[2], s[3]; n = int(d * 30)
        z = {'zin': f"1+0.16*on/{n}", 'zout': f"1.16-0.16*on/{n}", 'panl': "1.18", 'panr': "1.18",
             'punch': f"if(lt(on,8),1.32-0.24*on/8,1.08+0.05*(on-8)/{n})"}[fx]
        x = {'panl': f"(iw-iw/zoom)*(1-on/{n})", 'panr': f"(iw-iw/zoom)*on/{n}"}.get(fx, "iw/2-(iw/zoom/2)")
        zp = f"zoompan=z='{z}':x='{x}':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30"
        if len(s) > 4:   # landscape photo: whole photo on its blurred copy, then the motion
            vf = ("split[a][b];[a]scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,gblur=sigma=50,eq=brightness=-0.08[bg];"
                  f"[b]scale=2080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,{zp}")
        else:
            vf = f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,{zp}"
        run(['-loop', '1', '-i', img, '-t', str(d), '-vf', vf] + enc + [p])
    else:
        src, ramps = s[1], s[2]; sub = []
        for j, (a, b, sp) in enumerate(ramps):
            q = f'{TMP}/s{i:02d}_{j}.mp4'
            run(['-ss', str(a), '-t', str(b - a), '-i', src, '-vf', f'scale=1080:1920,setpts=PTS/{sp},fps=30'] + enc + [q]); sub.append(q)
        lst = f'{TMP}/s{i:02d}.txt'; open(lst, 'w').write(''.join(f"file '{os.path.abspath(q)}'\n" for q in sub))
        tot = sum((b - a) / sp for a, b, sp in ramps)
        # slow push-in over the whole clip (keeps every video moving)
        run(['-f', 'concat', '-safe', '0', '-i', lst, '-vf',
             f"scale=w='1080*(1+0.10*t/{tot:.2f})':h='1920*(1+0.10*t/{tot:.2f})':eval=frame,crop=1080:1920,setsar=1"] + enc + [p])
    parts.append(p)
ds = [dur(p) for p in parts]
# xfade chain
inputs = sum([['-i', p] for p in parts], []); fc = []; prev = '[0:v]'; off = 0.0; starts = [0.0]
for k in range(1, len(parts)):
    off += ds[k - 1] - TR; starts.append(round(off, 3))
    outl = f'[x{k}]' if k < len(parts) - 1 else '[vout]'
    fc.append(f"{prev}[{k}:v]xfade=transition={XF[(k - 1) % len(XF)]}:duration={TR}:offset={off:.3f}{outl}"); prev = outl
total = starts[-1] + ds[-1]
run(inputs + ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-filter_complex', ';'.join(fc), '-map', '[vout]', '-map', f'{len(parts)}:a',
     '-t', f'{total:.3f}', '-c:v', 'libx264', '-crf', '15', '-preset', 'medium', '-g', '30', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', OUT])
marks = [(starts[i], round(starts[i] + ds[i], 3)) for i in range(len(parts))]
json.dump(marks, open('build/vlog3/marks_fx.json', 'w'))
print(round(total, 2), marks)
