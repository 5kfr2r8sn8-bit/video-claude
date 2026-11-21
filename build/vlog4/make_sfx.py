"""Vlog4: SFX-only track (ikut pilihan pengguna untuk vlog: tiada muzik latar, bunyi kesan kuat)."""
import json, os, sys
sys.path.insert(0, os.path.abspath('.claude/skills/gac/scripts'))
import sfx
m = json.load(open('build/vlog4/marks_fx.json')); spec = json.load(open('build/hf/vlog4/spec.json'))
D = spec['duration']; starts = [a for a, b in m]
ev = [(0.15, 'hit', 0), (0.5, 'shimmer', -2)]
ev += [(t, 'whoosh', 0) for t in starts[1:]]
ev += [(t, 'swell', -3) for t in (starts[1] + 1.8, starts[2] + 0.1, starts[4] + 0.1, starts[5] + 0.1, starts[6] + 2.2)]   # slow-mo moments
ev += [(L['t'][0], 'pop', 0) for L in spec['labels']]
a = spec['end']['t'][0]
ev += [(a - 1.0, 'riser', -2), (a, 'boom', 0), (a + 0.3, 'shimmer', 0)] + [(a + 0.3 + j * 0.6, 'pop', -2) for j in range(len(spec['end']['lines']))]
ev.append((a + 0.4 + len(spec['end']['lines']) * 0.6, 'coin', 0))
sfx.render_track(ev, D, 'build/vlog4/sfx_only.wav', gain_db=0, music_db=None); print(len(ev), 'events')
