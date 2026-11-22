import json, sys, numpy as np
F = json.load(open(sys.argv[1])); out = {}
for n, an in F.items():
    rate = 40; N = int(round(an['length'] * rate)) + 1; ts = np.arange(N) / rate; bones = {}
    for b, chs in an['bones'].items():
        tr = {}
        for ch, key in (('rotation', 'rot'), ('position', 'pos')):
            if ch in chs:
                kt = [k[0] for k in chs[ch]]; kv = np.array([k[1] for k in chs[ch]])
                tr[key] = np.stack([np.interp(ts, kt, kv[:, i]) for i in range(3)], 1).round(4).tolist()
            else: tr[key] = [[0, 0, 0]] * N
        bones[b] = tr
    out[n] = dict(length=an['length'], loop=an['loop'], rate=rate, bones=bones)
json.dump(out, open(sys.argv[2], 'w'))
