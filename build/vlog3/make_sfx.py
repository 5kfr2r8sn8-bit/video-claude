"""Vlog3: SFX-only track (pengguna: tiada muzik latar, hanya sound effect yang kuat supaya masih dengar bila lagu TikTok ditambah)."""
import json, os, sys
sys.path.insert(0, os.path.abspath('.claude/skills/gac/scripts'))
import sfx
m = json.load(open('build/vlog3/marks_fx.json')); spec = json.load(open('build/hf/vlog3/spec.json'))
D = spec['duration']; starts = [a for a, b in m]
ev = [(0.15, 'hit', 0), (0.5, 'shimmer', -2)]
for i, t in enumerate(starts[1:], 1):
    ev.append((t, 'whoosh', 0))                         # every transition
for i in (3, 6, 14): ev.append((starts[i] + 0.05, 'punch', 0))   # snap-zoom photos
for i in (4, 7, 9): ev.append((starts[i] + 0.3, 'shimmer', -2))  # jewellery
ev.append((starts[3] + 0.3, 'coin', -2))                # gold bar & dinar
for t in (starts[1] + 1.6, starts[2] + 1.5, starts[10] + 3.08, starts[13] + 2.22): ev.append((t, 'swell', -3))   # slow-mo moments
for K in spec['cards']:
    ev.append((K['t'][0], 'swoosh', -1)); ev.append((K['t'][0] + 0.15, 'impact', -4))
    ev += [(t, 'pop', 0) for t in K.get('at', [])]
for L in spec.get('labels', []): ev.append((L['t'][0], 'pop', 0))
E = spec['end']; a = E['t'][0]
ev += [(a - 1.0, 'riser', -2), (a, 'boom', 0), (a + 0.3, 'shimmer', 0)]
ev += [(a + 0.3 + j * 0.6, 'pop', -2) for j in range(len(E['lines']))]
ev.append((a + 0.4 + len(E['lines']) * 0.6, 'coin', 0))
out = 'build/vlog3/sfx_only.wav'
sfx.render_track(ev, D, out, gain_db=0, music_db=None)
print(len(ev), 'events ->', out)
