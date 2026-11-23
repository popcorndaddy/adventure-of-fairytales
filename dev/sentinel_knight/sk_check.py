"""Numeric QC of baked actions: how far each fist is from the sword grip, how low the feet/sword go, foot sliding.
blender -b sentinel_knight_anim.blend --python sk_check.py -- action[,action..]"""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector
import sk_pose as K

names = sys.argv[sys.argv.index("--") + 1].split(",")
r = K.Rig()
blocks = [o for o in bpy.data.objects if "sk_mat" in o]
by_bone = {}
for o in blocks:
    by_bone.setdefault(o["sk_bone"], []).append(o)
PX = K.PX


def low(bones):
    z = 1e9
    for b in bones:
        for o in by_bone.get(b, []):
            for v in o.data.vertices:
                z = min(z, (o.matrix_world @ v.co).z)
    return z / PX


for name in names:
    act = bpy.data.actions[name]
    r.ob.animation_data.action = act
    n = int(act.frame_range[1])
    gap_l, gap_r, feet, sword_low = [], [], {"R": [], "L": []}, []
    for f in range(0, n + 1):
        bpy.context.scene.frame_set(f)
        sw = r.pb["sword"]
        grip = sw.head; d = (sw.tail - sw.head).normalized()
        # off-hand grip point on the handle and where its fist should be
        gl = grip + d * r.grip_l_s
        palm_l = r.pb["hand_L"].head + (r.pb["hand_L"].tail - r.pb["hand_L"].head) * 0.55
        # distance of the left fist from the handle line
        t = (palm_l - grip).dot(d); closest = grip + d * t
        gap_l.append(((palm_l - closest).length / PX, t / PX))
        palm_r = r.pb["hand_R"].head + (r.pb["hand_R"].tail - r.pb["hand_R"].head) * 0.55
        tr = (palm_r - grip).dot(d)
        gap_r.append(((palm_r - (grip + d * tr)).length / PX))
        for S in ("R", "L"):
            feet[S].append(low([f"foot_{S}", f"toe_{S}"]))
        sword_low.append(low(["sword"]))
    print(f"CHECK {name}: frames {n}")
    print(f"  left fist to handle: {min(g for g, _ in gap_l):.2f}..{max(g for g, _ in gap_l):.2f} px off the line, along handle {min(t for _, t in gap_l):.1f}..{max(t for _, t in gap_l):.1f} px")
    print(f"  right fist to handle: {min(gap_r):.2f}..{max(gap_r):.2f} px")
    print(f"  lowest foot R {min(feet['R']):.2f} L {min(feet['L']):.2f}   highest-lowest R {max(feet['R']):.2f} L {max(feet['L']):.2f}")
    print(f"  sword lowest {min(sword_low):.2f} px")
print("CHECK_OK")
