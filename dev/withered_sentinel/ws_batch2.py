"""Batch 2: idle (passive, 4 s) + idle_combat (ready, 3 s). Both seamless loops.
idle: sword tip pinned on the stone, uneven breathing, slow weight shift, head that locks onto you and drifts.
idle_combat: the sweep's start stance exactly (frame 0 = sweep frame 0), lower, heavier breathing, blade weaving.
Run: blender -b withered_sentinel_reworked.blend --python ws_batch2.py   (saves in place)"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector, Matrix
import ws_tools as T
from ws_tools import track, eul, dir_az_el, smooth, PX
from ws_common import *

# ================================================================= IDLE  (80 frames = 4 s)
NI = 80
IDLE_FEET = {"left": (7.5, -4.5), "right": (-8.0, 3.0)}
IDLE_YAW = {"left": 7.0, "right": -15.0}
TIP = (-21.0, -27.0, G + 0.25)                       # where the sword point rests on the floor (px)

# uneven breathing: a long full breath, then a shorter shallow one with a catch at the top
BREATH = [(0, 0.0), (6, 0.15), (20, 1.0), (25, 0.94), (40, 0.12), (47, 0.05), (56, 0.62), (60, 0.58), (63, 0.66), (74, 0.08)]
# weight drifts from the right (sword) leg to the left and back; hips sit over the loaded leg
WEIGHT = [(0, -0.9), (14, -1.0), (34, 0.6), (50, 1.0), (64, 0.3)]
# head: locks on, holds, slowly drifts left with a tilt, then a small sharp correction back onto the player
HEAD_YAW = [(0, 0.0), (16, 0.5), (30, 8.0), (42, 9.5), (49, 7.5), (52, -2.5), (58, -0.8), (68, 0.0)]
HEAD_ROLL = [(0, 0.0), (18, 0.0), (32, 5.0), (46, 6.0), (52, -1.0), (62, 0.0)]


def pose_idle(r, f):
    b = loop_track(BREATH, f, NI)
    db = loop_track(BREATH, f + 1, NI) - loop_track(BREATH, f - 1, NI)     # breathing rate: + inhale, - exhale
    w = loop_track(WEIGHT, f, NI)
    r.move("body", (w * 1.4, -0.4, -1.4 + 0.45 * b))
    r.rotate("body", eul(7 - 1.2 * b, -1.6 * w, -5 + 1.2 * w))
    for S in ("left", "right"):
        plant(r, S, IDLE_FEET[S], yaw=IDLE_YAW[S])
    # breath lives in the chest and shoulders; the waist follows a frame or two late
    bl = loop_track(BREATH, f - 3, NI)
    r.rotate("waist", eul(3 - 1.0 * bl, 0.6 * w, 1.0 * w))
    r.rotate("chest", eul(5 - 3.2 * b, 0.8 * w, 1.5 * w))
    hy, hr = loop_track(HEAD_YAW, f, NI), loop_track(HEAD_ROLL, f, NI)
    head_world(r, yaw=hy - 3, pitch=9 - 1.5 * b, roll=hr)
    r.rotate("jaw", eul(4 + max(0.0, -db) * 9 + 1.5 * wave(f, NI, (1, 7, 0.4))))     # mouth drops on the exhale
    # sword arm: hand rests on the pommel, the point stays on the stone; the blade leans with his breathing / weight
    sh = r.head("right_arm") / PX
    hand = sh + Vector((-4.0 - 0.4 * w, -12.0, -21.0 + 1.2 * b))
    plant_sword_tip(r, TIP, hand, pole=(-0.7, 0.55, -0.2))
    # free arm hangs heavy, the claw twitches once mid-loop
    lsh = 0.6 * b
    r.aim("left_arm", (0.30 + 0.02 * w, -0.16 - 0.03 * lsh, -0.94))
    r.aim("left_forearm", (0.22, -0.40 - 0.03 * b, -0.88))
    r.aim("left_hand", (0.16, -0.45, -0.88))
    twitch = 10 * bump(f, 36, 1.6) - 4 * bump(f, 39, 2.0)
    r.rotate("left_hand", eul(-14 - twitch, 0, 3 * bump(f, 37, 2)))
    cape(r, back=7 + 1.2 * b, yaw=-1.0 * w, flutter=0.8 * wave(f, NI, (1, 3, 0.0), (0.5, 5, 1.1)))
    r.rotate("skirt", eul(0.6 * wave(f, NI, (1, 2, 0.6)), 0, 0.8 * w))


T.bake(rig, "idle", NI, pose_idle, loop=True)
print("IDLE_BAKED", flush=True)

# ================================================================= IDLE_COMBAT (60 frames = 3 s); frame 0 == sweep frame 0
NC = 60
LEFT_UP0 = Vector((0.35, -0.55, -0.75))
LEFT_FORE0 = Vector((0.1, -0.85, -0.3))


def pose_idle_combat(r, f):
    # two heavy breaths per loop, the second deeper; knees pump with them; weight rocks once
    br = wave(f, NC, (1.0, 2, 0.0), (0.35, 4, 0.0), (0.25, 1, 0.0))
    rock = wave(f, NC, (1.0, 1, 0.0), (0.25, 3, 0.0))
    bx, by, bz = 0.9 * rock, 0.4 * wave(f, NC, (1, 1, 0)), -0.7 * br
    hy = -8 + 2.5 * rock
    r.move("body", (bx, -0.5 + by, -2.5 + bz))
    r.rotate("body", eul(5 + 0.8 * br, -1.0 * rock, hy))
    plant(r, "left", STANCE_FEET["left"])
    plant(r, "right", STANCE_FEET["right"])
    chest_yaw = -4 + 1.5 * wave(f, NC, (1, 1, 0.0), (0.4, 2, 0.0))
    rel = chest_yaw - hy
    r.rotate("waist", eul(2 - 0.6 * br, 0, rel * 0.4))
    r.rotate("chest", eul(3 - 2.6 * br, 0, rel * 0.6))
    # eyes stay locked on the target: the head counters the body's rock
    head_world(r, yaw=-1.6 * rock + 1.2 * wave(f, NC, (1, 3, 0.0)), pitch=5 + 1.2 * wave(f, NC, (1, 2, 0.0)))
    r.rotate("jaw", eul(8 + 4 * max(0.0, wave(f, NC, (1, 2, 0.0))) + 1.2 * wave(f, NC, (1, 5, 0.0))))
    # blade weaves low, point tracking the target, never fully still
    az = -28 + 6 * wave(f, NC, (1, 1, 0.0), (0.35, 3, 0.0))
    he = -55 + 4 * wave(f, NC, (1, 2, 0.0), (0.3, 1, 0.0))
    be = -35 + 5 * wave(f, NC, (1, 2, 0.0), (0.5, 3, 0.0))
    sh = r.head("right_arm")
    r.ik("right_arm", "right_forearm", sh + dir_az_el(az, he) * REACH_R * 0.86, pole=Vector((-0.6, 0.5, -0.6)))
    bd = dir_az_el(az + 12, be)
    r.aim("right_hand", bd)
    sword_to(r, bd)
    # free claw open and ready, flexing
    flex = wave(f, NC, (1, 2, 0.0), (0.4, 3, 0.0))
    r.aim("left_arm", (LEFT_UP0 + Vector((0.05, -0.08, 0.06)) * flex).normalized())
    r.aim("left_forearm", (LEFT_FORE0 + Vector((0.0, -0.06, 0.10)) * flex).normalized())
    r.rotate("left_hand", eul(-16 - 4 * flex))
    cape(r, back=8 + 1.5 * br, yaw=1.4 - 1.2 * rock, flutter=1.2 * wave(f, NC, (1, 3, 0.0), (0.6, 5, 0.0)))
    r.rotate("skirt", eul(0.8 * wave(f, NC, (1, 2, 0.0)), 0, 0.6 * rock))


T.bake(rig, "idle_combat", NC, pose_idle_combat, loop=True)
print("IDLE_COMBAT_BAKED", flush=True)


# ================================================================= checks
def snap(act, f):
    rig.ob.animation_data.action = bpy.data.actions[act]
    bpy.context.scene.frame_set(f)
    return pose_snapshot(rig)


for act, n in (("idle", NI), ("idle_combat", NC)):
    dp, dr = pose_diff(snap(act, 0), snap(act, n))
    print(f"{act} loop seam: frame 0 vs {n}: {dp:.3f}px {dr:.2f}deg")
    rig.ob.animation_data.action = bpy.data.actions[act]
    feet = {S: [] for S in ("left", "right")}
    tip, low = [], []
    for f in range(n + 1):
        bpy.context.scene.frame_set(f)
        for S in feet:
            pts = rig.sole_points(S)
            feet[S].append(sum(pts, Vector()) / len(pts) / PX)
        tip.append(rig.sword_tip() / PX)
        low.append((rig.min_z("sword") - rig.ground) / PX)
    for S, tr in feet.items():
        print(f"{act} {S} foot drift {max((a - tr[0]).length for a in tr):.3f}px")
    print(f"{act} sword tip travel {max((a - tip[0]).length for a in tip):.2f}px, lowest blade point {min(low):.2f}..{max(low):.2f}px above floor")
dp, dr = pose_diff(snap("idle_combat", 0), snap("sweep", 0))
print(f"idle_combat f0 vs sweep f0: {dp:.3f}px {dr:.2f}deg")
bpy.ops.wm.save_mainfile()
print("BATCH2_OK")
