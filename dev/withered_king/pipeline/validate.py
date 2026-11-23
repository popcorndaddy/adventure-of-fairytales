"""Format checks for the exported GeckoLib files: geometry structure, animation channels, bone names, numbers, loops."""
import json, math, sys
d = sys.argv[1]
geo = json.load(open(f'{d}/withered_king.geo.json')); an = json.load(open(f'{d}/withered_king.animation.json'))
errs = []
assert geo['format_version'] == '1.12.0'
g = geo['minecraft:geometry'][0]; bones = g['bones']; names = [b['name'] for b in bones]
if len(set(names)) != len(names): errs.append('duplicate bone names')
idx = {n: i for i, n in enumerate(names)}
for b in bones:
    if 'parent' in b and b['parent'] not in idx: errs.append(f'{b["name"]}: missing parent {b["parent"]}')
    if 'parent' in b and idx[b['parent']] > idx[b['name']]: errs.append(f'{b["name"]}: parent listed after child')
    for c in b.get('cubes', []):
        for k in ('origin', 'size'):
            if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in c[k]): errs.append(f'{b["name"]}: bad cube {k}')
        for f, uv in c['uv'].items():
            u, v = uv['uv']; w, h = uv['uv_size']
            if not (0 <= min(u, u + w) and max(u, u + w) <= g['description']['texture_width'] and 0 <= min(v, v + h) and max(v, v + h) <= g['description']['texture_height']):
                errs.append(f'{b["name"]}: uv outside texture')
need = ['withered_king_idle', 'withered_king_walk_drag', 'withered_king_sweep', 'withered_king_dash', 'withered_king_phase_transition', 'withered_king_kneeling',
        'withered_king_phase_two_roar', 'withered_king_hand_shockwave', 'withered_king_ground_stomp', 'withered_king_death', 'withered_king_remains']
assert an['format_version'] == '1.8.0'
for n in need:
    if n not in an['animations']: errs.append(f'missing animation {n}'); continue
    a = an['animations'][n]; L = a['animation_length']
    for bn, chans in a['bones'].items():
        if bn not in idx: errs.append(f'{n}: unknown bone {bn}')
        for ch, keys in chans.items():
            if ch not in ('rotation', 'position', 'scale'): errs.append(f'{n}/{bn}: channel {ch}')
            for t, v in keys.items():
                tt = float(t)
                if tt < -1e-6 or tt > L + 1e-6: errs.append(f'{n}/{bn}/{ch}: key at {t} outside 0..{L}')
                vals = v['post'] if isinstance(v, dict) else v
                if len(vals) != 3 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in vals): errs.append(f'{n}/{bn}/{ch}@{t}: bad value')
    print(f'{n:34s} {L:6.2f}s loop={a.get("loop", False)!s:20s} bones={len(a["bones"]):2d} keys={sum(len(k) for c in a["bones"].values() for k in c.values())}')
extra = set(an['animations']) - set(need)
if extra: errs.append(f'unexpected animations {sorted(extra)}')
print('geometry bones', len(bones), 'cubes', sum(len(b.get('cubes', [])) for b in bones), 'texture', g['description']['texture_width'], 'x', g['description']['texture_height'])
print('ERRORS' if errs else 'OK', *errs[:30], sep='\n  ')
sys.exit(1 if errs else 0)
