"""True per-tick rotation change of every bone (quaternion angle, degrees), to separate real snaps from Euler artefacts.
blender -b sentinel_knight_anim.blend --python sk_snap.py -- [threshold] [action,...]"""
import bpy, sys, math
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
thr = float(args[0]) if args else 25.0
only = set(args[1].split(",")) if len(args) > 1 else None
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for act in sorted(bpy.data.actions, key=lambda a: a.name):
    if not act.get("sk_export", False) or (only and act.name not in only):
        continue
    rig.animation_data.action = act
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    prev = None; worst = []
    for f in range(f0, f1 + 1):
        bpy.context.scene.frame_set(f)
        cur = {}
        for pb in rig.pose.bones:
            M = pb.matrix if not pb.parent else pb.parent.matrix.inverted() @ pb.matrix
            cur[pb.name] = M.to_quaternion()
        if prev:
            for n, q in cur.items():
                a = math.degrees(2 * math.acos(min(1.0, abs(prev[n].dot(q)))))
                if a > thr: worst.append((round(a, 1), n, f))
        prev = cur
    worst.sort(reverse=True)
    print(f"SNAP {act.name}: {len(worst)} bone-ticks over {thr} deg; worst {worst[:6]}")
print("SNAP_OK")
