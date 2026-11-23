"""Batch 4: dash (32 frames: wind-up 0-8, roar 8, charge 9-16, skid, recover) +
awaken (68 frames: phase-2 transformation, eruption on 25).  Both start/end on the combat stance.
Run: blender -b withered_sentinel_reworked.blend --python ws_batch4.py   (saves in place)"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector, Matrix
import ws_tools as T
from ws_tools import track, eul, dir_az_el, smooth, PX
from ws_common import *

LB, FB = (0.35, -0.55, -0.75), (0.1, -0.85, -0.3)        # stance claw arm directions

# ================================================================= DASH (32 frames)
# The entity itself is shoved forward on ticks 9-16, so the animation sells the charge: a low coiled wind-up with the
# blade cocked back and the claw reaching at the target, a roar on 8, then a leaning bound with the sword levelled
# forward like a lance, a skidding stop with the body thrown back against the momentum, and a heavy reset.
ND = 32
DASH = dict(
    by=[(0, 0), (6, 3.0), (8, 3.5, "i"), (10, -6.0, "o"), (16, -7.0), (19, -3.0), (24, 1.0), (32, 0)],
    bz=[(0, 0), (6, -3.5), (8, -4.0, "i"), (10, -2.0), (12, -0.5), (14, -2.0), (16, -2.5), (18, -4.5), (24, -1.0), (32, 0)],
    lean=[(0, 5), (6, 14), (8, 15, "i"), (10, 26, "o"), (16, 24), (18, 4), (22, 2), (32, 5)],
    roll=[(0, 0), (6, -3), (10, 2), (13, -2), (16, 1), (22, 0), (32, 0)],
    hip_yaw=[(0, -8), (6, -18), (8, -20), (10, -4, "o"), (16, -6), (20, -2), (32, -8)],
    chest_yaw=[(0, -4), (6, -30), (8, -32, "i"), (10, -4, "o"), (16, -2), (20, 4), (32, -4)],
    chest_pitch=[(0, 0), (6, 3), (8, -2), (10, 4), (16, 4), (18, -4), (24, -1), (32, 0)],
    head_pitch=[(0, 5), (6, 0), (8, -4), (10, -4, "o"), (16, -2), (19, 2), (32, 5)],
    head_yaw=[(0, 0), (6, 12), (8, 10), (10, 0, "o"), (32, 0)],
    jaw=[(0, 8), (6, 6), (7, 10), (8, 28, "o"), (14, 26), (18, 14), (32, 8)],
    r_az=[(0, -28), (6, -120), (8, -125, "i"), (10, -20, "o"), (16, -15), (19, -22), (32, -28)],
    r_el=[(0, -55), (6, -40), (8, -38), (10, -20, "o"), (16, -22), (20, -45), (32, -55)],
    b_az=[(0, -16), (6, -160), (8, -165, "i"), (10, -6, "o"), (16, -4), (20, -10), (32, -16)],
    b_el=[(0, -35), (6, -25), (8, -22), (10, -12, "o"), (16, -14), (20, -30), (32, -35)],
    l_up=[(0, LB), (6, (0.25, -0.95, -0.10)), (8, (0.25, -0.97, 0.0)), (10, (0.5, 0.4, -0.75), "o"), (16, (0.5, 0.45, -0.7)),
          (22, (0.4, -0.4, -0.8)), (32, LB)],
    l_fore=[(0, FB), (6, (0.15, -1.0, 0.05)), (8, (0.15, -1.0, 0.10)), (10, (0.35, 0.2, -0.9), "o"), (16, (0.35, 0.25, -0.9)),
            (22, (0.15, -0.7, -0.6)), (32, FB)],
    l_hand_x=[(0, -16), (6, 0), (8, 4), (10, -24), (16, -24), (32, -16)],
    # feet: push off (heel up), right foot drives through, left bounds out front, skid, then two steps back to stance
    rf_y=[(0, 5.0), (8, 5.0), (10, 9.0, "o"), (13, 2.0), (16, -4.0, "i"), (20, -4.0), (25, 5.0), (32, 5.0)],
    rf_z=[(0, 0), (8, 0), (10, 1.0), (12, 6.0), (14, 4.0), (16, 0, "i"), (20, 0), (22.5, 3.0), (25, 0), (32, 0)],
    rf_p=[(0, 0), (6, 10), (8, 30), (10, 45, "o"), (12, 10), (14, 0), (32, 0)],
    lf_y=[(0, -7.0), (10, -7.0), (12, -3.0), (15, -16.0, "i"), (23, -16.0), (28, -7.0), (32, -7.0)],
    lf_z=[(0, 0), (9, 0), (11, 5.0), (13, 7.0), (15, 0, "i"), (23, 0), (25.5, 3.5), (28, 0), (32, 0)],
    lf_p=[(0, 0), (8, 0), (10, 20), (12, 0), (32, 0)],
    cape_back=[(0, 8), (6, 6), (10, 30, "o"), (16, 32), (19, 10), (24, 12), (32, 8)],
    flutter=[(0, 0), (10, 0), (11, 4), (12, -4), (13, 4), (14, -4), (15, 4), (16, -3), (19, 3), (23, -1), (28, 0), (32, 0)],
)


def dash_tremble(f):
    return 1.2 * math.sin(f * 2.9) * smooth((f - 7) / 1) * (1 - smooth((f - 9) / 1))


T.bake(rig, "dash", ND, lambda r, f: combat_pose(r, f, DASH, dash_tremble))
print("DASH_BAKED", flush=True)

# ================================================================= AWAKEN (68 frames; eruption on 25)
# 0-3 the wound lands: head snaps back.  3-14 he buckles: knees give, torso folds over, claw clutches his chest,
# the sword point sags to the stone.  14-23 he gathers, trembling, curled inward.  23-25 ERUPTS: straightens in two
# frames, arms flung wide, head thrown back, jaw wide.  25-46 the roar holds and shakes him as the armour ignites.
# 46-68 he comes down out of it, heavy, into the combat stance.
NA = 68
CLUTCH_UP, CLUTCH_FORE = (-0.1, -0.75, -0.6), (-0.85, -0.3, 0.4)
WIDE_UP, WIDE_FORE = (0.9, -0.1, 0.4), (0.75, -0.3, 0.6)
AWAKEN = dict(
    by=[(0, 0), (4, 1.0), (14, -2.0), (22, -2.5), (25, 1.5, "o"), (40, 1.0), (56, 0), (68, 0)],
    bz=[(0, 0), (3, -0.8), (14, -8.0, "o"), (20, -8.5), (23, -9.0, "i"), (25, 0.5, "o"), (32, 0.0), (44, -0.5), (56, -2.5), (68, 0)],
    lean=[(0, 5), (3, 1), (14, 30, "o"), (20, 32), (23, 33, "i"), (25, -5, "o"), (40, -3), (50, 1), (60, 6), (68, 5)],
    roll=[(0, 0), (14, -4), (23, -5), (25, 0, "o"), (68, 0)],
    hip_yaw=[(0, -8), (14, -14), (23, -15), (25, 0, "o"), (45, -2), (68, -8)],
    chest_yaw=[(0, -4), (14, -10), (23, -12), (25, 0, "o"), (45, -2), (68, -4)],
    chest_pitch=[(0, 0), (3, -4), (14, 8), (23, 10, "i"), (25, -5, "o"), (42, -4), (56, 0), (68, 0)],
    head_pitch=[(0, 5), (3, -10, "o"), (14, 35), (20, 30), (23, 28, "i"), (25, -30, "o"), (42, -26), (52, -5), (60, 5), (68, 5)],
    head_roll=[(0, 0), (14, 8), (22, 6), (25, 0, "o"), (68, 0)],
    jaw=[(0, 8), (2, 22), (6, 14), (14, 6), (20, 8), (23, 4, "i"), (25, 34, "o"), (44, 30), (50, 14), (58, 8), (68, 8)],
    r_az=[(0, -28), (14, -35), (23, -36, "i"), (25, -95, "o"), (42, -100), (56, -50), (68, -28)],
    r_el=[(0, -55), (14, -60), (23, -62, "i"), (25, 15, "o"), (42, 12), (56, -35), (68, -55)],
    b_az=[(0, -16), (14, -20), (23, -20, "i"), (25, -110, "o"), (42, -115), (56, -50), (68, -16)],
    b_el=[(0, -35), (14, -75), (23, -78, "i"), (25, 30, "o"), (42, 28), (56, -20), (68, -35)],
    l_up=[(0, LB), (4, (0.0, -0.8, -0.55)), (14, CLUTCH_UP), (23, CLUTCH_UP, "i"), (25, WIDE_UP, "o"), (42, (0.92, -0.05, 0.38)),
          (56, (0.5, -0.45, -0.7)), (68, LB)],
    l_fore=[(0, FB), (4, (-0.8, -0.4, 0.35)), (14, CLUTCH_FORE), (23, CLUTCH_FORE, "i"), (25, WIDE_FORE, "o"), (42, (0.78, -0.25, 0.58)),
            (56, (0.15, -0.8, -0.45)), (68, FB)],
    l_hand_x=[(0, -16), (14, -30), (23, -35, "i"), (25, 5, "o"), (42, 5), (68, -16)],
    rf_p=[(0, 0), (8, 0), (14, 30, "o"), (23, 32, "i"), (25, 0, "o"), (68, 0)],
    cape_back=[(0, 8), (14, 2), (23, 0, "i"), (25, 30, "o"), (30, 24), (44, 18), (56, 10), (68, 8)],
    flutter=[(0, 0), (25, 0), (27, 6), (31, -4), (36, 3), (42, -2), (48, 1), (56, 0), (68, 0)],
)


def awaken_tremble(f):
    gather = 1.4 * math.sin(f * 2.8) * smooth((f - 15) / 3) * (1 - smooth((f - 23) / 1))
    roar = 2.6 * math.sin((f - 25) * 2.3) * math.exp(-max(0, f - 25) / 12.0) * (1 - smooth((f - 46) / 6)) * (f >= 25)
    return gather + roar


def pose_awaken(r, f):
    combat_pose(r, f, AWAKEN, awaken_tremble)
    shake = awaken_tremble(f)
    r.rotate("head", eul(0.6 * shake, 0, 0.8 * shake))            # the skull rattles with the roar
    r.rotate("jaw", eul(1.5 * abs(shake)))


T.bake(rig, "awaken", NA, pose_awaken)
print("AWAKEN_BAKED", flush=True)


# ================================================================= checks
def snap(act, f):
    rig.ob.animation_data.action = bpy.data.actions[act]
    bpy.context.scene.frame_set(f)
    return pose_snapshot(rig)


ref = snap("sweep", 0)
for act, n in (("dash", ND), ("awaken", NA)):
    a0, b0 = pose_diff(snap(act, 0), ref); a1, b1 = pose_diff(snap(act, n), ref)
    print(f"{act}: start vs stance {a0:.3f}px {b0:.2f}deg, end vs stance {a1:.3f}px {b1:.2f}deg")
    rig.ob.animation_data.action = bpy.data.actions[act]
    lows, soles = [], {"left": [], "right": []}
    for f in range(n + 1):
        bpy.context.scene.frame_set(f)
        lows.append((rig.min_z("sword") - rig.ground) / PX)
        for S in soles:
            soles[S].append(min(p.z for p in rig.sole_points(S)) / PX)
    print(f"{act}: sword lowest {min(lows):.2f}px; left sole {min(soles['left']):.2f}..{max(soles['left']):.2f}; right sole {min(soles['right']):.2f}..{max(soles['right']):.2f}")
    knees = []
bpy.ops.wm.save_mainfile()
print("BATCH4_OK")
