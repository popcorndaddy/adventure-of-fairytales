"""Bake every Sentinel action to Blockbench/GeckoLib additive values (40 samples/s) -> baked.json.
Each bone's local transform is rebuilt from the evaluated pose, so IK and constraints are baked in."""
import bpy, sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Matrix, Vector, Euler
import bbmath as BM
from bbmath import G, GI, BONES, WREST
HERE = BM.HERE; RATE = 40
rig = bpy.data.objects['Sentinel_Rig']; PB = rig.pose.bones; AB = rig.data.bones; sc = bpy.context.scene
only = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = os.path.join(HERE, 'king_baked.json')
res = json.load(open(OUT)) if (only and os.path.exists(OUT)) else {}
DEF = [n for n in BM.ORDER if n != 'root']
for A in bpy.data.actions:
    if 'bb_length' not in A or (only and A.name not in only): continue
    rig.animation_data.action = A
    try: rig.animation_data.action_slot = A.slots[0]
    except Exception: pass
    L = float(A['bb_length']); n = int(round(L * RATE))
    prev = {b: Euler([math.radians(v) for v in BONES[b]['rest']], 'XYZ') for b in DEF}
    tracks = {b: {'rot': [], 'pos': []} for b in DEF}
    miss = {}; probes = []
    GRIP = Vector(BM.D['sword']['grip']); TIP = GRIP + Vector((0, 0, -41.8))
    PALM_L = Vector(BONES['left_hand']['pivot']) + Vector((0, -2.0, 0))
    for k in range(n + 1):
        f = k / RATE * 20.0; sc.frame_set(int(math.floor(f + 1e-6)), subframe=max(0.0, f - math.floor(f + 1e-6)))
        for c, end in (('IK_hand.R', 'right_hand'), ('IK_hand.L', 'left_hand'), ('IK_foot.R', 'right_foot'), ('IK_foot.L', 'left_foot')):
            d = (PB[c].head - PB[end].head).length * 8
            if d > miss.get(c, (0, 0))[0]: miss[c] = (round(d, 2), round(k / RATE, 3))
        W = {}
        for b in BM.ORDER:
            K = GI @ (PB[b].matrix @ AB[b].matrix_local.inverted()) @ G
            W[b] = K @ WREST[b]
        if k % 2 == 0:      # 20 Hz world probes (model px) for the game: blade, left palm, feet, crown
            pr = lambda v: [round(x, 2) for x in v]
            probes.append(dict(grip=pr(W['sword'] @ GRIP), tip=pr(W['sword'] @ TIP), palm_l=pr(W['left_hand'] @ PALM_L),
                               foot_l=pr(W['left_foot'] @ Vector(BONES['left_foot']['pivot'])), foot_r=pr(W['right_foot'] @ Vector(BONES['right_foot']['pivot'])),
                               crown=pr(W['crown'] @ Vector(BONES['crown']['pivot']))))
        for b in DEF:
            p = BONES[b]['parent']; Lm = W[p].inverted() @ W[b]
            piv = Vector(BONES[b]['pivot']); pos = (Lm @ Vector((*piv, 1))).xyz - piv
            e = Lm.to_3x3().normalized().to_euler('XYZ', prev[b]); prev[b] = e
            tracks[b]['rot'].append([round(math.degrees(e[i]) - BONES[b]['rest'][i], 3) for i in range(3)])
            tracks[b]['pos'].append([round(v, 4) for v in pos])
    res[A.name] = dict(length=L, loop=A['bb_loop'], rate=RATE, bones=tracks, events=json.loads(A.get('events', '[]')), probes=probes)
    print('BAKE', A.name, n + 1, 'samples  IK miss px (max, at s):', miss)
json.dump(res, open(OUT, 'w'))
print('OUT', OUT)
