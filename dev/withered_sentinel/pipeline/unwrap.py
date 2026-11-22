"""Make every rotation track Euler-continuous (pick, for each key, the equivalent angles nearest the previous key),
so GeckoLib's linear interpolation never spins a bone through 180/360 between two keys."""
import json, sys, numpy as np
sys.path.insert(0, '/home/claude/boss')
import model3 as M
from scipy.spatial.transform import Rotation as Rot
F = json.load(open(sys.argv[1])); fixed = 0
for n, an in F.items():
    for b, chs in an['bones'].items():
        if 'rotation' not in chs: continue
        rest = np.array(M._b[b]['rot']); keys = chs['rotation']; prev = None
        for i, (t, v) in enumerate(keys):
            tot = np.array(v) + rest
            if prev is not None:
                e = Rot.from_euler('xyz', tot, degrees=True).as_euler('xyz', degrees=True)
                best = None
                for a in (e, np.array([e[0] + 180, 180 - e[1], e[2] + 180])):
                    a = prev + (a - prev + 180) % 360 - 180
                    d = np.abs(a - prev).max()
                    if best is None or d < best[0]: best = (d, a)
                if np.abs(best[1] - tot).max() > 1e-3: fixed += 1
                tot = best[1]
            keys[i] = [t, list(np.round(tot - rest, 3))]; prev = tot
json.dump(F, open(sys.argv[1], 'w')); print('keys re-expressed', fixed)
