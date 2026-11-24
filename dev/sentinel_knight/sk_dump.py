"""Dump world-space bone heads + a point 1 m along each bone's local Y/Z for chosen action frames, to JSON
(run on the source rig and on the GeckoLib re-import, then compare: proves the export round-trips).
blender -b file.blend --python sk_dump.py -- out.json action f1,f2,..   (frames in ticks)"""
import bpy, sys, json
args = sys.argv[sys.argv.index("--") + 1:]
out, act, frames = args[0], args[1], [int(x) for x in args[2].split(",")]
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
rig.animation_data.action = bpy.data.actions[act]
res = {}
for f in frames:
    bpy.context.scene.frame_set(f)
    d = {}
    for pb in rig.pose.bones:
        M = rig.matrix_world @ pb.matrix
        R = (pb.matrix @ pb.bone.matrix_local.inverted()).to_3x3()       # rotation relative to rest
        d[pb.name] = {"h": list(M.translation), "rx": list(R.col[0]), "ry": list(R.col[1]), "rz": list(R.col[2])}
    res[f] = d
json.dump(res, open(out, "w"))
print("DUMP_OK", len(res))
