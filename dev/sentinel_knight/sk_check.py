"""Numeric QC of baked actions: how far each fist is from the sword grip, how low the feet/sword go, foot sliding.
blender -b sentinel_knight_anim.blend --python sk_check.py -- action[,action..]"""
import bpy, sys, os, math
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
BODY = [("pelvis", "chest", 7.5), ("chest", "chest", 8.5), ("thigh_R", "thigh_R", 3.5), ("thigh_L", "thigh_L", 3.5), ("shin_R", "shin_R", 3.0), ("shin_L", "shin_L", 3.0), ("head", "head", 4.5)]


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
    tips, slide = [], {}
    elbow, clip = {}, []
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
            fc = r.pb[f"toe_{S}"].head / PX                      # the ball of the foot: it must not slide
            slide.setdefault(S, []).append((fc.x, fc.y, feet[S][-1]))
        sword_low.append(low(["sword"]))
        for S in ("R", "L"):
            u = (r.pb[f"upperarm_{S}"].tail - r.pb[f"upperarm_{S}"].head).normalized(); fa = (r.pb[f"forearm_{S}"].tail - r.pb[f"forearm_{S}"].head).normalized()
            elbow.setdefault(S, []).append(180 - math.degrees(u.angle(fa)))
        # blade vs body: points along the blade (guard -> tip) inside the torso / thigh capsules
        dn = (sw.tail - sw.head).normalized()
        for k in range(4, 22):
            q = (sw.head + dn * (r.sword_len * k / 22)) / PX
            for (b0, b1, rad) in BODY:
                a0 = r.pb[b0].head / PX; a1 = r.pb[b1].tail / PX
                ab = a1 - a0; t = max(0.0, min(1.0, (q - a0).dot(ab) / ab.length_squared))
                if (q - (a0 + ab * t)).length < rad:
                    clip.append((f, b0)); break
        tips.append(((sw.head + (sw.tail - sw.head).normalized() * r.sword_len) / PX, d.copy()))
    # sword continuity: per-frame tip travel and blade turn (no teleporting between poses)
    jumps = [(tips[i + 1][0] - tips[i][0]).length for i in range(len(tips) - 1)]
    turns = [math.degrees(tips[i][1].angle(tips[i + 1][1])) for i in range(len(tips) - 1)]
    # planted feet: horizontal drift while the sole stays on the floor in consecutive frames
    drift = {}
    for S, tr in slide.items():
        dd = [math.hypot(tr[i + 1][0] - tr[i][0], tr[i + 1][1] - tr[i][1]) for i in range(len(tr) - 1)
              if tr[i][2] < 0.4 and tr[i + 1][2] < 0.4]
        drift[S] = (max(dd) if dd else 0.0, len(dd))
    print(f"CHECK {name}: frames {n}")
    print(f"  sword tip max travel {max(jumps):.1f} px/tick, max blade turn {max(turns):.1f} deg/tick")
    print(f"  planted-foot drift R {drift['R'][0]:.2f} px/tick ({drift['R'][1]} planted frames), L {drift['L'][0]:.2f} ({drift['L'][1]})")
    print(f"  left fist to handle: {min(g for g, _ in gap_l):.2f}..{max(g for g, _ in gap_l):.2f} px off the line, along handle {min(t for _, t in gap_l):.1f}..{max(t for _, t in gap_l):.1f} px")
    print(f"  right fist to handle: {min(gap_r):.2f}..{max(gap_r):.2f} px")
    print(f"  lowest foot R {min(feet['R']):.2f} L {min(feet['L']):.2f}   highest-lowest R {max(feet['R']):.2f} L {max(feet['L']):.2f}")
    print(f"  sword lowest {min(sword_low):.2f} px")
    print(f"  elbow straightness R {min(elbow['R']):.0f}..{max(elbow['R']):.0f} deg, L {min(elbow['L']):.0f}..{max(elbow['L']):.0f} deg (180 = straight)")
    cf = sorted(set(f for f, _ in clip))
    print(f"  blade inside body: {len(cf)} frames {cf[:12]} {sorted(set(b for _, b in clip))}")
    if name == "dash":
        print("  dash elbows by tick R:", [round(x) for x in elbow['R']], "L:", [round(x) for x in elbow['L']])
print("CHECK_OK")
