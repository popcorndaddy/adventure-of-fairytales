"""Batch 5: summon_start (32, blade strikes the stone on 23) -> summon_loop (60, seamless kneel) -> summon_end (28),
and death (80, held on the last frame).
The kneel: right knee on the stone, left foot forward, sword driven point-first into the floor in front of him with
his hand on the hilt. The sword uses a 'pinned tip' mode (tip at a world point, blade leaning to where the hand wants
to be) blended in and out of the normal free-arm mode.
Run: blender -b withered_sentinel_reworked.blend --python ws_batch5.py   (saves in place)"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector, Matrix
import ws_tools as T
from ws_tools import track, eul, dir_az_el, smooth, PX
from ws_common import *

LB, FB = (0.35, -0.55, -0.75), (0.1, -0.85, -0.3)
ARM = ("right_arm", "right_forearm", "right_hand", "sword")

# kneel constants
K_BZ, K_LEAN, K_BY = -10.5, 14.0, 1.0
K_LF, K_RF = (8.5, -15.0), (-8.0, 15.0)
K_RP, K_RYAW, K_LYAW = 62.0, -8.0, 6.0
K_TIP = (-11.0, -22.0, G - 8.0)                       # 8 px of blade buried in the stone
K_HAND = (1.0, -9.0, -8.0)                            # where the hand wants to be relative to the shoulder (px)
K_LUP, K_LFORE = (0.3, -0.62, -0.72), (0.12, -0.9, -0.42)   # claw resting on the forward knee
H_LUP, H_LFORE, H_LX = (0.61, -0.55, -0.55), (0.37, -0.9, -0.35), -30.0   # claw hovering over the stone (summon_loop frame 0)


def pinned_pose(r, f, K, extra=None):
    combat_pose(r, f, K, extra)
    w = track(K["tipw"], f) if "tipw" in K else 0.0
    if w <= 0:
        return
    qf = {b: r.pb[b].rotation_euler.to_quaternion() for b in ARM}
    sh = r.head("right_arm") / PX
    plant_sword_tip(r, track(K["tip"], f), sh + Vector(track(K["tip_hand"], f)), pole=(-0.7, 0.3, -0.5))
    if w < 1:
        for b in ARM:
            q = qf[b].slerp(r.pb[b].rotation_euler.to_quaternion(), w)
            r.pb[b].rotation_euler = q.to_euler("XZY")
        r.upd()


# ================================================================= SUMMON_START (32)
NS1 = 32
SUMMON_START = dict(
    by=[(0, 0), (8, -1.0), (14, -1.5), (21, K_BY), (32, K_BY)],
    bz=[(0, 0), (6, 1.5), (13, 2.0, "i"), (20, -9.0, "l"), (23, K_BZ - 1.5, "o"), (27, K_BZ), (32, K_BZ)],
    lean=[(0, 5), (8, -2), (13, -3, "i"), (20, 10, "l"), (23, K_LEAN + 6, "o"), (28, K_LEAN), (32, K_LEAN)],
    hip_yaw=[(0, -8), (13, -12), (23, -4, "o"), (32, -4)],
    chest_yaw=[(0, -4), (13, -16), (23, -2, "o"), (32, -2)],
    chest_pitch=[(0, 0), (13, -4), (23, 8, "o"), (32, 6)],
    head_pitch=[(0, 5), (13, -14), (19, -6), (23, 30, "o"), (32, 32)],
    head_roll=[(0, 0), (23, 3), (32, 4)],
    jaw=[(0, 8), (4, 12), (13, 22), (20, 10), (23, 26, "o"), (28, 10), (32, 6)],
    rf_z=[(0, 0), (14, 0), (22, 2.0), (32, 2.0)],
    r_az=[(0, -28), (5, -20)], r_el=[(0, -55), (5, -10)], b_az=[(0, -16), (5, -10)], b_el=[(0, -35), (5, -70)],
    tipw=[(0, 0.0), (6, 1.0), (32, 1.0)],
    tip=[(0, (-20.0, -32.0, G + 6.0)), (6, (-15.0, -26.0, 30.0)), (13, (-11.0, -24.0, 44.0), "i"), (19, (-11.0, -22.0, 22.0), "l"),
         (21, (-11.0, -22.0, 8.0), "i"), (23, K_TIP), (32, K_TIP)],
    tip_hand=[(0, (-6.0, -16.0, -18.0)), (6, (-2.0, -14.0, 14.0)), (13, (1.0, -12.0, 30.0), "i"), (21, (1.0, -12.0, 4.0)),
              (23, K_HAND), (32, K_HAND)],
    l_up=[(0, LB), (8, (0.75, 0.1, -0.6)), (13, (0.85, 0.2, -0.45)), (20, (0.6, -0.3, -0.7)), (23, K_LUP, "o"), (26, K_LUP), (32, H_LUP)],
    l_fore=[(0, FB), (8, (0.55, -0.3, -0.75)), (13, (0.6, -0.2, -0.75)), (20, (0.3, -0.7, -0.6)), (23, K_LFORE, "o"), (26, K_LFORE), (32, H_LFORE)],
    l_hand_x=[(0, -16), (13, -6), (23, -24), (26, -24), (32, H_LX)],
    lf_x=[(0, STANCE_FEET["left"][0]), (21, K_LF[0])],
    lf_y=[(0, STANCE_FEET["left"][1]), (14, STANCE_FEET["left"][1]), (20, K_LF[1], "i"), (32, K_LF[1])],
    lf_z=[(0, 0), (14, 0), (17, 4.0), (20, 0, "i"), (32, 0)],
    lf_yaw=[(0, STANCE_YAW["left"]), (20, K_LYAW)],
    rf_x=[(0, STANCE_FEET["right"][0]), (22, K_RF[0])],
    rf_y=[(0, STANCE_FEET["right"][1]), (14, STANCE_FEET["right"][1]), (22, K_RF[1], "o"), (32, K_RF[1])],
    rf_p=[(0, 0), (14, 0), (18, 30), (22, K_RP, "o"), (32, K_RP)],
    rf_yaw=[(0, STANCE_YAW["right"]), (22, K_RYAW)],
    cape_back=[(0, 8), (13, 4), (20, 0), (23, 26, "o"), (28, 16), (32, 12)],
    flutter=[(0, 0), (23, 0), (25, 5), (28, -3), (32, 0)],
)


def start_tremble(f):
    return 2.2 * math.sin((f - 23) * 2.5) * math.exp(-max(0, f - 23) / 2.5) * (f >= 23)


T.bake(rig, "summon_start", NS1, lambda r, f: pinned_pose(r, f, SUMMON_START, start_tremble), loop=None)
print("SUMMON_START_BAKED", flush=True)

# ================================================================= SUMMON_LOOP (60, seamless) - kneeling, channelling the dead
NL = 60
KNEEL = {k: [(0, v[-1][1])] for k, v in SUMMON_START.items()}       # frame-32 values of every track


def pose_summon_loop(r, f):
    K = dict(KNEEL)
    br = wave(f, NL, (1.0, 2, 0.0), (0.3, 3, 0.0))
    K["bz"] = [(0, K_BZ + 0.6 * br)]
    K["lean"] = [(0, K_LEAN - 1.0 * br)]
    K["chest_pitch"] = [(0, 6 - 2.0 * br)]
    K["head_pitch"] = [(0, 32 - 4 * wave(f, NL, (1, 1, 0.0)) - 1.5 * br)]
    K["head_roll"] = [(0, 4 + 2.5 * wave(f, NL, (1, 1, 0.0)))]
    K["head_yaw"] = [(0, 3 * wave(f, NL, (1, 1, 0.0), (0.4, 2, 0.0)))]
    K["jaw"] = [(0, 6 + 5 * max(0.0, wave(f, NL, (1, 2, 0.0))) + 1.2 * wave(f, NL, (1, 7, 0.0)))]
    # the claw leaves the knee and hovers over the stone, palm down, slowly stirring the dead up
    c, s = wave(f, NL, (1, 1, math.pi / 2)), wave(f, NL, (1, 1, 0.0))
    K["l_up"] = [(0, (0.55 + 0.06 * c, -0.55 + 0.06 * s, -0.55))]
    K["l_fore"] = [(0, (0.25 + 0.12 * c, -0.9 + 0.1 * s, -0.35 - 0.05 * br))]
    K["l_hand_x"] = [(0, -30 + 8 * wave(f, NL, (1, 3, 0.0), (0.5, 5, 0.0)))]
    K["tip_hand"] = [(0, tuple(a + b for a, b in zip(K_HAND, (0, 0, 0.8 * br))))]
    K["cape_back"] = [(0, 12 + 1.2 * br)]
    K["flutter"] = [(0, 1.0 * wave(f, NL, (1, 3, 0.0), (0.6, 5, 0.0)))]
    pinned_pose(r, f, K)


# make frame 0 of the loop exactly the last frame of summon_start: blend the start of the claw hover in
_loop_keys = None
T.bake(rig, "summon_loop", NL, pose_summon_loop, loop=True)
print("SUMMON_LOOP_BAKED", flush=True)

# ================================================================= SUMMON_END (28) - wrench the blade out and rise
NE = 28
E0 = lambda k: KNEEL[k][0][1]
SUMMON_END = dict(
    by=[(0, K_BY), (12, 0.5), (28, 0)],
    bz=[(0, K_BZ), (5, K_BZ - 1.0), (8, K_BZ + 1.0, "i"), (14, -3.0, "o"), (20, -1.0), (24, -0.5), (28, 0)],
    lean=[(0, K_LEAN), (5, K_LEAN + 4), (8, 4, "i"), (14, 0, "o"), (22, 6), (28, 5)],
    hip_yaw=[(0, -4), (14, -10), (28, -8)],
    chest_yaw=[(0, -2), (10, -14), (16, -10), (28, -4)],
    chest_pitch=[(0, 6), (5, 9), (9, -6, "o"), (16, -2), (28, 0)],
    head_pitch=[(0, 32), (4, 26), (9, -8, "o"), (16, 0), (28, 5)],
    head_roll=[(0, 4), (8, 0), (28, 0)],
    jaw=[(0, 6), (8, 22, "o"), (14, 18), (22, 10), (28, 8)],
    r_az=[(0, -20), (12, -20), (16, -40), (22, -32), (28, -28)], r_el=[(0, -10), (12, -10), (16, -30), (22, -50), (28, -55)],
    b_az=[(0, -10), (12, -10), (16, -20), (22, -18), (28, -16)], b_el=[(0, -70), (12, -70), (16, 10), (22, -30), (28, -35)],
    tipw=[(0, 1.0), (12, 1.0), (18, 0.0)],
    tip=[(0, K_TIP), (8, K_TIP), (10, (-11.0, -22.0, G + 2.0), "o"), (14, (-14.0, -24.0, 30.0)), (18, (-18.0, -30.0, 24.0))],
    tip_hand=[(0, K_HAND), (8, (1.0, -9.0, -4.0)), (12, (0.0, -10.0, 14.0)), (18, (-4.0, -14.0, -8.0))],
    l_up=[(0, H_LUP), (5, (0.35, -0.7, -0.62)), (12, (0.7, 0.0, -0.7)), (28, LB)],
    l_fore=[(0, H_LFORE), (5, (0.15, -0.95, -0.3)), (12, (0.45, -0.4, -0.8)), (28, FB)],
    l_hand_x=[(0, H_LX), (5, -30), (12, -12), (28, -16)],
    lf_x=[(0, K_LF[0]), (24, STANCE_FEET["left"][0])],
    lf_y=[(0, K_LF[1]), (18, K_LF[1]), (24, STANCE_FEET["left"][1], "i"), (28, STANCE_FEET["left"][1])],
    lf_z=[(0, 0), (18, 0), (21, 3.0), (24, 0, "i"), (28, 0)],
    lf_yaw=[(0, K_LYAW), (24, STANCE_YAW["left"])],
    rf_x=[(0, K_RF[0]), (16, STANCE_FEET["right"][0])],
    rf_y=[(0, K_RF[1]), (8, K_RF[1]), (16, STANCE_FEET["right"][1], "s"), (28, STANCE_FEET["right"][1])],
    rf_z=[(0, 2.0), (8, 2.0), (13, 2.5), (16, 0, "i"), (28, 0)],
    rf_p=[(0, K_RP), (8, K_RP), (14, 10, "o"), (16, 0), (28, 0)],
    rf_yaw=[(0, K_RYAW), (16, STANCE_YAW["right"])],
    cape_back=[(0, 12), (8, 4), (14, 18, "o"), (22, 10), (28, 8)],
    flutter=[(0, 0), (10, 0), (13, 3), (17, -2), (22, 0.5), (28, 0)],
)


def end_tremble(f):
    return 1.6 * math.sin(f * 2.7) * smooth((f - 3) / 2) * (1 - smooth((f - 9) / 1))


T.bake(rig, "summon_end", NE, lambda r, f: pinned_pose(r, f, SUMMON_END, end_tremble))
print("SUMMON_END_BAKED", flush=True)

# ================================================================= DEATH (80, held)
# 0-6 the killing blow rocks him back.  6-18 his legs fail; he drives the sword into the stone to catch himself and
# drops onto his right knee.  18-40 he hangs on the hilt, shuddering, the light going out.  40-54 the claw rises toward
# whoever killed him.  54-62 it falls.  62-80 his grip opens, the sword tips over, and he folds forward and goes still.
NDT = 80
D_TIP = (-12.0, -24.0, G - 4.0)
DEATH = dict(
    by=[(0, 0), (4, 3.0, "o"), (10, 1.0), (18, K_BY), (62, K_BY), (76, -2.0), (80, -2.0)],
    bz=[(0, 0), (4, 0.5), (12, -8.0, "i"), (18, K_BZ, "o"), (40, K_BZ - 0.5), (62, K_BZ - 0.5), (74, K_BZ - 1.6, "i"), (77, K_BZ - 1.0), (80, K_BZ - 1.1)],
    lean=[(0, 5), (4, -8, "o"), (12, 12), (18, 16, "o"), (40, 20), (54, 14), (62, 24), (72, 52, "i"), (76, 49), (80, 50)],
    roll=[(0, 0), (4, 4), (18, -2), (62, -3), (74, 6), (80, 6)],
    hip_yaw=[(0, -8), (4, 4), (18, -4), (80, -4)],
    chest_yaw=[(0, -4), (4, 12, "o"), (18, -2), (62, -4), (74, -10), (80, -10)],
    chest_pitch=[(0, 0), (4, -8, "o"), (18, 6), (40, 10), (54, 4), (62, 12), (74, 18), (80, 18)],
    head_pitch=[(0, 5), (3, -24, "o"), (10, 10), (18, 30), (40, 38), (46, 12), (54, 8), (60, 40, "i"), (74, 46), (80, 46)],
    head_roll=[(0, 0), (4, -6), (18, 6), (40, 10), (54, 2), (62, 14), (80, 18)],
    head_yaw=[(0, 0), (4, -10), (18, 4), (46, -4), (80, 6)],
    jaw=[(0, 8), (3, 30, "o"), (10, 18), (18, 12), (40, 20), (54, 26), (60, 8), (66, 22), (80, 24)],
    r_az=[(0, -28), (4, -50), (10, -35), (62, -40), (72, -75, "i"), (80, -76)],
    r_reach=[(0, 0.86), (62, 0.86), (72, 0.7), (80, 0.7)],
    r_el=[(0, -55), (4, -45), (10, -40), (62, -50), (72, -40, "i"), (80, -40)],
    b_az=[(0, -16), (4, -40), (10, -20), (62, -40), (72, -100, "i"), (80, -102)],
    b_el=[(0, -35), (4, -20), (10, -70), (62, -80), (72, -30, "i"), (80, -30)],
    tipw=[(0, 0.0), (8, 0.0), (12, 1.0), (62, 1.0), (68, 0.0)],
    tip=[(8, (-16.0, -30.0, 14.0)), (12, (-13.0, -26.0, G + 2.0), "i"), (14, D_TIP), (62, D_TIP), (68, (-20.0, -24.0, G + 1.0))],
    tip_hand=[(8, (-4.0, -14.0, -14.0)), (14, (0.0, -10.0, -6.0)), (40, (0.5, -9.0, -9.0)), (62, (1.0, -8.0, -12.0)), (68, (-8.0, -8.0, -24.0))],
    l_up=[(0, LB), (4, (0.6, 0.3, -0.75), "o"), (12, (0.45, -0.3, -0.8)), (18, K_LUP), (40, K_LUP), (46, (0.35, -0.9, 0.15), "o"),
          (54, (0.3, -0.92, 0.25)), (60, (0.35, -0.4, -0.85), "i"), (80, (0.25, -0.15, -0.95))],
    l_fore=[(0, FB), (4, (0.45, 0.1, -0.85), "o"), (12, (0.2, -0.6, -0.75)), (18, K_LFORE), (40, K_LFORE), (46, (0.2, -0.95, 0.25), "o"),
            (54, (0.15, -0.95, 0.3)), (60, (0.2, -0.3, -0.93), "i"), (80, (0.15, -0.1, -0.98))],
    l_hand_x=[(0, -16), (4, 4), (18, -22), (40, -22), (46, -2), (54, 4), (60, -36, "i"), (80, -40)],
    lf_x=[(0, STANCE_FEET["left"][0]), (16, K_LF[0])],
    lf_y=[(0, STANCE_FEET["left"][1]), (8, STANCE_FEET["left"][1]), (14, K_LF[1], "i"), (80, K_LF[1])],
    lf_z=[(0, 0), (8, 0), (11, 3.0), (14, 0, "i"), (80, 0)],
    lf_yaw=[(0, STANCE_YAW["left"]), (14, K_LYAW)],
    rf_x=[(0, STANCE_FEET["right"][0]), (4, STANCE_FEET["right"][0]), (18, K_RF[0])],
    rf_y=[(0, STANCE_FEET["right"][1]), (4, STANCE_FEET["right"][1] + 2), (18, K_RF[1], "o"), (80, K_RF[1])],
    rf_p=[(0, 0), (6, 10), (18, K_RP, "o"), (80, K_RP)],
    rf_z=[(0, 0), (6, 0), (18, 2.0), (80, 2.0)],
    rf_yaw=[(0, STANCE_YAW["right"]), (18, K_RYAW)],
    cape_back=[(0, 8), (4, 2), (18, 16, "o"), (40, 12), (62, 4), (74, -40, "i"), (77, -36), (80, -37)],
    flutter=[(0, 0), (18, 0), (20, 4), (24, -2), (28, 0), (74, 0), (76, 4), (79, 1), (80, 1)],
)


def death_tremble(f):
    hit = 2.0 * math.sin(f * 2.4) * math.exp(-f / 3.0)
    fade = 1.1 * math.sin(f * 2.9) * smooth((f - 20) / 4) * (1 - smooth((f - 40) / 10))
    reach = 0.9 * math.sin(f * 3.4) * smooth((f - 44) / 3) * (1 - smooth((f - 56) / 2))
    return hit + fade + reach


def pose_death(r, f):
    pinned_pose(r, f, DEATH, death_tremble)
    if 44 <= f <= 58:                                   # the reaching claw shakes
        r.rotate("left_forearm", eul(1.5 * math.sin(f * 3.1), 0, 1.2 * math.sin(f * 2.3)))


T.bake(rig, "death", NDT, pose_death, loop=None)
print("DEATH_BAKED", flush=True)


# ================================================================= checks
def snap(act, f):
    rig.ob.animation_data.action = bpy.data.actions[act]
    bpy.context.scene.frame_set(f)
    return pose_snapshot(rig)


ref = snap("sweep", 0)
for a, fa, b, fb in (("summon_start", 0, "sweep", 0), ("summon_start", NS1, "summon_loop", 0), ("summon_loop", 0, "summon_loop", NL),
                     ("summon_loop", 0, "summon_end", 0), ("summon_end", NE, "sweep", 0), ("death", 0, "sweep", 0)):
    dp, dr = pose_diff(snap(a, fa), snap(b, fb))
    print(f"MATCH {a} f{fa} vs {b} f{fb}: {dp:.3f}px {dr:.2f}deg")
has_shin = "right_shin" in rig.vg
for act in ("summon_start", "summon_loop", "summon_end", "death"):
    rig.ob.animation_data.action = bpy.data.actions[act]
    n = int(bpy.data.actions[act].frame_range[1])
    rows = []
    for f in sorted(set([0, n // 4, n // 2, 3 * n // 4, n] + ([23] if act == "summon_start" else []))):
        bpy.context.scene.frame_set(f)
        knee = rig.min_z("right_shin") / PX if has_shin else rig.head("right_foot").z / PX
        tip = rig.sword_tip() / PX; hand = rig.head("right_hand") / PX
        sole = {S: min(p.z for p in rig.sole_points(S)) / PX for S in ("left", "right")}
        rows.append(f"f{f}: knee/shin low {knee:.1f} hand z {hand.z:.1f} tip z {tip.z:.1f} soles L {sole['left']:.1f} R {sole['right']:.1f}")
    print("CHECK", act, " | ".join(rows))
bpy.ops.wm.save_mainfile()
print("BATCH5_OK")
