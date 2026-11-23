"""Batch 3: push (40 frames, palm hits on frame 20) + stomp (38 frames, foot lands on frame 19).
Both start and end on the shared combat stance (== idle_combat / sweep frame 0) so they blend cleanly.
Run: blender -b withered_sentinel_reworked.blend --python ws_batch3.py   (saves in place)"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector, Matrix
import ws_tools as T
from ws_tools import track, eul, dir_az_el, smooth, PX
from ws_common import *

# ================================================================= PUSH  (40 frames; shockwave on 20)
# Story: he plants, draws the claw back past his ear while the whole body coils onto the back (right) leg,
# holds the coil trembling, then drives forward off the back leg with a stamping step of the left foot,
# the arm snapping straight with the palm open on 20. The force kicks back through him; he holds, then resets.
NP = 40
PUSH = dict(
    bx=[(0, 0), (12, -1.6), (17, -1.8), (20, 1.0, "o"), (24, 0.8), (32, 0.2), (40, 0)],
    by=[(0, 0), (12, 3.5), (17, 4.0, "i"), (20, -5.5, "o"), (22, -4.6), (26, -4.2), (34, -1.0), (40, 0)],
    bz=[(0, 0), (8, 0.6), (13, -1.2), (17, -1.6, "i"), (20, -3.2, "o"), (24, -2.6), (34, -0.6), (40, 0)],
    lean=[(0, 5), (12, -1), (17, -2, "i"), (20, 13, "o"), (24, 11), (34, 7), (40, 5)],
    roll=[(0, 0), (12, -2.5), (20, 1.5), (30, 0.5), (40, 0)],
    hip_yaw=[(0, -8), (12, -20), (17, -22, "i"), (20, 6, "o"), (24, 8), (34, -2), (40, -8)],
    chest_yaw=[(0, -4), (12, -38), (17, -42, "i"), (19, 2, "l"), (20, 10, "o"), (23, 13), (30, 8), (40, -4)],
    chest_pitch=[(0, 0), (12, -5), (17, -6), (20, 4, "o"), (24, 3), (40, 0)],
    head_yaw=[(0, 0), (12, 14), (17, 16), (20, -2, "o"), (26, -3), (40, 0)],
    head_pitch=[(0, 5), (12, 10), (17, 12), (20, 2, "o"), (24, 4), (40, 5)],
    jaw=[(0, 8), (12, 4), (17, 3, "i"), (20, 24, "o"), (26, 20), (32, 10), (40, 8)],
    # sword arm counterweights: swings back as the claw drives forward
    r_az=[(0, -28), (12, -12), (17, -10, "i"), (20, -70, "o"), (26, -72), (34, -40), (40, -28)],
    r_el=[(0, -55), (12, -60), (20, -45, "o"), (26, -48), (40, -55)],
    b_az=[(0, -16), (12, 4), (17, 6, "i"), (20, -100, "o"), (26, -104), (34, -50), (40, -16)],
    b_el=[(0, -35), (12, -45), (20, -25, "o"), (26, -28), (40, -35)],
    # claw: drawn back by the ear, elbow high and behind; then a straight palm strike at head height
    l_up=[(0, (0.35, -0.55, -0.75)), (6, (0.55, -0.15, -0.6)), (12, (0.62, 0.55, 0.1)), (17, (0.6, 0.62, 0.18), "i"),
          (19, (0.05, -0.75, 0.25), "l"), (20, (-0.12, -1.0, 0.16), "o"), (26, (-0.1, -1.0, 0.10)), (33, (0.3, -0.75, -0.45)), (40, (0.35, -0.55, -0.75))],
    l_fore=[(0, (0.1, -0.85, -0.3)), (6, (0.15, -0.85, 0.1)), (12, (-0.12, -0.9, 0.42)), (17, (-0.14, -0.88, 0.45), "i"),
            (19, (-0.1, -0.95, 0.3), "l"), (20, (-0.15, -1.0, 0.18), "o"), (26, (-0.14, -1.0, 0.12)), (33, (0.1, -0.9, -0.2)), (40, (0.1, -0.85, -0.3))],
    l_hand=[(0, (0.16, -0.6, -0.78)), (12, (-0.1, -0.35, 0.93)), (17, (-0.1, -0.3, 0.95), "i"), (20, (0.0, -0.35, 0.94), "o"),
            (26, (0.0, -0.4, 0.92)), (33, (0.12, -0.7, -0.3)), (40, (0.16, -0.6, -0.78))],
    l_hand_w=[(0, 0.0), (8, 1.0), (30, 1.0), (40, 0.0)],
    l_hand_x=[(0, -16), (12, -4), (20, 0, "o"), (26, 0), (40, -16)],
    # the left foot steps in on the strike (lift 14-19, stamp on 19) and steps back to stance 28-34
    lf_y=[(0, -7.0), (14, -7.0), (19, -15.0, "i"), (28, -15.0), (34, -7.0), (40, -7.0)],
    lf_z=[(0, 0), (14, 0), (16.5, 3.2), (19, 0, "i"), (28, 0), (31, 2.4), (34, 0), (40, 0)],
    lf_p=[(0, 0), (14, 0), (15, 8), (17, 0), (40, 0)],
    rf_p=[(0, 0), (18, 0), (21, 18, "o"), (27, 14), (33, 0), (40, 0)],
    cape_back=[(0, 8), (17, 4), (20, 22, "o"), (26, 18), (36, 9), (40, 8)],
    flutter=[(0, 0), (20, 0), (23, 4), (27, -3), (32, 1.5), (37, 0), (40, 0)],
)


def push_tremble(f):
    return 0.9 * math.sin(f * 2.6) * smooth((f - 11) / 3) * (1 - smooth((f - 18) / 1)) + \
           2.0 * math.sin((f - 20) * 2.2) * math.exp(-max(0, f - 20) / 2.5) * (f >= 20)


T.bake(rig, "push", NP, lambda r, f: combat_pose(r, f, PUSH, push_tremble))
print("PUSH_BAKED", flush=True)

# ================================================================= STOMP (38 frames; foot lands on 19)
# Story: weight rolls onto the left leg, the right knee comes up high, the body rises and arches back with both
# arms flung wide (sword up and out, claw raised): a held apex that trembles. Then everything drops at once:
# the foot drives down, hips crash, chest folds forward, arms slam down, the jaw opens in a roar on the impact.
NT = 38
STOMP = dict(
    bx=[(0, 0), (9, 2.6), (14, 2.8), (19, 0.6, "o"), (24, 0.3), (38, 0)],
    by=[(0, 0), (10, 1.5), (14, 1.8, "i"), (19, -1.5, "o"), (26, -1.0), (38, 0)],
    bz=[(0, 0), (4, -1.0), (10, 2.2), (14, 2.6, "i"), (18, -2.0, "l"), (19, -6.0, "o"), (22, -5.2), (30, -1.4), (38, 0)],
    lean=[(0, 5), (4, 7), (10, 0), (14, -1.5, "i"), (18, 10, "l"), (19, 18, "o"), (23, 16), (31, 7), (38, 5)],
    roll=[(0, 0), (9, 6), (14, 6.5, "i"), (19, -1, "o"), (25, 0), (38, 0)],
    hip_yaw=[(0, -8), (10, -12), (19, -8, "o"), (38, -8)],
    chest_yaw=[(0, -4), (10, -10), (19, -4, "o"), (38, -4)],
    chest_pitch=[(0, 0), (10, -3), (14, -3.5, "i"), (19, 8, "o"), (23, 7), (38, 0)],
    head_yaw=[(0, 0), (38, 0)],
    head_pitch=[(0, 5), (10, -2), (14, -3, "i"), (19, 16, "o"), (24, 12), (38, 5)],
    head_roll=[(0, 0), (10, -4), (19, 0, "o"), (38, 0)],
    jaw=[(0, 8), (8, 6), (14, 14), (18, 10, "i"), (19, 26, "o"), (27, 22), (33, 10), (38, 8)],
    # sword arm flung wide and up, then slammed down to the side with the point to the floor
    r_az=[(0, -28), (10, -88), (14, -92, "i"), (19, -60, "o"), (24, -55), (38, -28)],
    r_el=[(0, -55), (10, 8), (14, 12, "i"), (19, -58, "o"), (24, -62), (38, -55)],
    r_reach=[(0, 0.86), (10, 0.95), (19, 0.9), (38, 0.86)],
    b_az=[(0, -16), (10, -100), (14, -104, "i"), (19, -55, "o"), (24, -50), (38, -16)],
    b_el=[(0, -35), (10, 35), (14, 40, "i"), (19, -60, "o"), (24, -62), (38, -35)],
    l_up=[(0, (0.35, -0.55, -0.75)), (10, (0.9, -0.2, 0.35)), (14, (0.88, -0.15, 0.45), "i"), (19, (0.55, -0.45, -0.7), "o"),
          (24, (0.5, -0.45, -0.75)), (38, (0.35, -0.55, -0.75))],
    l_fore=[(0, (0.1, -0.85, -0.3)), (10, (0.6, -0.5, 0.65)), (14, (0.55, -0.45, 0.72), "i"), (19, (0.25, -0.55, -0.8), "o"),
            (24, (0.2, -0.6, -0.78)), (38, (0.1, -0.85, -0.3))],
    l_hand_x=[(0, -16), (10, -2), (14, 0), (19, -30, "o"), (26, -24), (38, -16)],
    # right foot: knee lifts high and forward, then drives straight down onto its own footprint
    rf_y=[(0, 5.0), (10, -1.0), (14, -1.5, "i"), (19, 5.0, "i"), (38, 5.0)],
    rf_z=[(0, 0), (3, 0), (10, 15.0), (14, 16.5, "i"), (19, 0, "i"), (38, 0)],
    rf_p=[(0, 0), (2, 0), (4, 16), (8, 4), (14, -2), (18, 0), (38, 0)],
    lf_p=[(0, 0), (38, 0)],
    cape_back=[(0, 8), (10, 3), (14, 2, "i"), (19, -6, "o"), (21, 26), (26, 18), (34, 9), (38, 8)],
    flutter=[(0, 0), (19, 0), (21, 5), (25, -3), (30, 1.5), (35, 0), (38, 0)],
)


def stomp_tremble(f):
    return 1.0 * math.sin(f * 2.7) * smooth((f - 11) / 2) * (1 - smooth((f - 16) / 1)) + \
           2.4 * math.sin((f - 19) * 2.4) * math.exp(-max(0, f - 19) / 2.8) * (f >= 19)


def pose_stomp(r, f):
    combat_pose(r, f, STOMP, stomp_tremble)
    if f < 19:                        # the lifted foot: toes hang, sole tips toward the floor before the slam
        lift = track(STOMP["rf_z"], f) / 16.5
        r.rotate("right_foot", Matrix.Rotation(math.radians(10 * lift), 3, "X"))


T.bake(rig, "stomp", NT, pose_stomp)
print("STOMP_BAKED", flush=True)


# ================================================================= checks
def snap(act, f):
    rig.ob.animation_data.action = bpy.data.actions[act]
    bpy.context.scene.frame_set(f)
    return pose_snapshot(rig)


ref = snap("sweep", 0)
for act, n, hit in (("push", NP, 20), ("stomp", NT, 19)):
    a0, b0 = pose_diff(snap(act, 0), ref); a1, b1 = pose_diff(snap(act, n), ref)
    print(f"{act}: start vs stance {a0:.3f}px {b0:.2f}deg, end vs stance {a1:.3f}px {b1:.2f}deg")
    rig.ob.animation_data.action = bpy.data.actions[act]
    lows, feet = [], {S: [] for S in ("left", "right")}
    for f in range(n + 1):
        bpy.context.scene.frame_set(f)
        lows.append((rig.min_z("sword") - rig.ground) / PX)
        for S in feet:
            feet[S].append(min(p.z for p in rig.sole_points(S)) / PX)
    print(f"{act}: sword lowest {min(lows):.2f}px, left sole z {min(feet['left']):.2f}..{max(feet['left']):.2f}, right sole z {min(feet['right']):.2f}..{max(feet['right']):.2f}")
rig.ob.animation_data.action = bpy.data.actions["push"]
bpy.context.scene.frame_set(20)
hp = rig.world_pt("left_hand", rig.seg_pt["left_hand"]) / PX
print(f"push hit frame 20: left palm at x {hp.x:.1f} y {hp.y:.1f} z {hp.z:.1f} px (forward = -y)")
rig.ob.animation_data.action = bpy.data.actions["stomp"]
for f in (14, 18, 19, 20):
    bpy.context.scene.frame_set(f)
    print(f"stomp f{f}: right sole lowest {min(p.z for p in rig.sole_points('right')) / PX:.2f}px")
bpy.ops.wm.save_mainfile()
print("BATCH3_OK")
