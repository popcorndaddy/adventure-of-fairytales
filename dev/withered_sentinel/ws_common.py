"""Shared posing helpers for the Withered Sentinel batches (combat stance, foot planting, sword, cape, loop curves).
Importing this builds the Rig from the open .blend."""
import bpy, math
from mathutils import Vector, Matrix
import ws_tools as T
from ws_tools import track, eul, dir_az_el, smooth, PX

rig = T.Rig()
G = rig.ground / PX                      # ground height in px
ANK = 3.5                                 # ankle height above the sole (px)
REACH_R = rig.lengths["right_arm"] + rig.lengths["right_forearm"]


def bump(u, c, w):
    d = (u - c) / w
    return math.exp(-d * d)


# ================================================================= shared combat stance (sweep ends, idle_combat, attacks)
STANCE_FEET = {"left": (8.0, -7.0), "right": (-8.5, 5.0)}
STANCE_YAW = {"left": 4.0, "right": -22.0}


def plant(r, S, xy, z=0.0, pitch=0.0, yaw=None):
    yaw = STANCE_YAW[S] if yaw is None else yaw
    a = Vector((xy[0], xy[1], G + ANK + z))
    if pitch > 0:
        # heel lifts about the toe: keep the (yawed) flat-foot toe point where it is and swing the ankle up
        rel = (r.toe[S] - r.ankle_rest[S]) / PX
        Rz = Matrix.Rotation(math.radians(yaw), 3, "Z")
        toe = a + Rz @ rel
        a = toe - Rz @ Matrix.Rotation(math.radians(pitch), 3, "X") @ rel
    r.place_foot(S, a, pitch=pitch, yaw=yaw)


def head_world(r, yaw=0.0, pitch=0.0, roll=0.0):
    R = Matrix.Rotation(math.radians(yaw), 3, "Z") @ Matrix.Rotation(math.radians(pitch), 3, "X") @ Matrix.Rotation(math.radians(roll), 3, "Y") @ r.base_rot["head"]
    r.set_world_rot("head", R)


def sword_to(r, d, min_clear=0.03):
    """Point the blade along d; if the tip would go under the floor, raise it just enough."""
    d = Vector(d).normalized()
    r.aim("sword", d)
    if r.min_z("sword") < r.ground + min_clear:
        flat = Vector((d.x, d.y, 0)).normalized()
        lo, hi = math.asin(max(-1, min(1, d.z))), math.radians(80)
        for _ in range(20):
            mid = (lo + hi) / 2
            r.aim("sword", flat * math.cos(mid) + Vector((0, 0, math.sin(mid))))
            if r.min_z("sword") < r.ground + min_clear:
                lo = mid
            else:
                hi = mid
        r.aim("sword", flat * math.cos(hi) + Vector((0, 0, math.sin(hi))))


def drag_blade(r, f, azimuth=168.0, contact=0.015):
    """The blade trails behind him with its tip ON the stone: search the downward angle at which the lowest
    point of the sword just touches the floor (contact px above it). azimuth 180 = straight back, <180 = out to his right."""
    chatter = 0.6 * math.sin(f * 1.9) + 0.35 * math.sin(f * 3.3)          # the edge skips over the stone
    flat = dir_az_el(-(azimuth + chatter), 0)                              # negative azimuth = his right side
    lo, hi = math.radians(5), math.radians(85)                             # angle below horizontal
    for _ in range(26):
        mid = (lo + hi) / 2
        r.aim("sword", flat * math.cos(mid) - Vector((0, 0, math.sin(mid))))
        if r.min_z("sword") < r.ground + contact:
            hi = mid
        else:
            lo = mid
    r.aim("sword", flat * math.cos(hi) - Vector((0, 0, math.sin(hi))))


def plant_sword_tip(r, tip_px, hand_px, pole=(-0.6, 0.5, -0.4), hand_roll_dir=None):
    """Grounded sword: the tip stays pinned at tip_px (world px) and the blade leans toward where the hand wants to be
    (hand_px). The arm is solved so the sword's pivot sits on that line, one blade length from the tip."""
    P = Vector(tip_px) * PX
    want = Vector(hand_px) * PX
    L = r.lengths["sword"]
    u = (want - P).normalized()
    H = P + u * L                                   # where the sword pivot must be
    target = H.copy()
    for _ in range(5):
        r.ik("right_arm", "right_forearm", target, pole=Vector(pole))
        r.aim("right_hand", -u if hand_roll_dir is None else Vector(hand_roll_dir))
        r.aim("sword", P - r.head("sword"))
        err = r.sword_tip() - P
        target -= err
    return (r.sword_tip() - P).length / PX


def cape(r, back=8.0, yaw=0.0, flutter=0.0):
    r.rotate("cape", eul(back, 0, yaw))
    for b, k in (("cape_mid", 0.35), ("cape_left", 0.3), ("cape_right", 0.3)):
        r.rotate(b, eul(back * k + flutter, 0, yaw * 0.5))
    for b, k in (("cape_mid_low", 0.4), ("cape_left_low", 0.35), ("cape_right_low", 0.35)):
        r.rotate(b, eul(back * k + flutter * 1.5, 0, yaw * 0.6))


# ================================================================= loop curves
def loop_track(keys, f, n):
    """Periodic Catmull-Rom through (frame, value) keys over a cycle of n frames (seamless loop, no end holds)."""
    f = f % n
    k = sorted(keys)
    m = len(k)
    for i in range(m):
        f0, v0 = k[i][0], k[i][1]
        f1, v1 = k[(i + 1) % m][0], k[(i + 1) % m][1]
        span = (f1 - f0) % n or n
        if (f - f0) % n < span:
            t = ((f - f0) % n) / span
            return T._catmull(k[i - 1][1], v0, v1, k[(i + 2) % m][1], t)
    return k[0][1]


def wave(f, n, *terms):
    """Sum of sines with whole-number harmonics over n frames: (amp, harmonic, phase). Zero at f = 0 when phases are 0."""
    return sum(a * math.sin(2 * math.pi * h * f / n + p) for a, h, p in terms)


# ================================================================= checks
def pose_snapshot(r):
    return {p.name: p.matrix.copy() for p in r.pb}


def pose_diff(a, b):
    """Largest bone-head offset (px) and rotation difference (deg) between two snapshots."""
    dp = max((a[k].translation - b[k].translation).length for k in a) / PX
    dr = max(math.degrees(a[k].to_quaternion().rotation_difference(b[k].to_quaternion()).angle) for k in a)
    return dp, dr


# ================================================================= generic key-driven combat pose
# combat stance values (identical to sweep frame 0)
BASE = dict(bx=0.0, by=0.0, bz=0.0, lean=5.0, roll=0.0, hip_yaw=-8.0, chest_yaw=-4.0, chest_pitch=0.0, waist_pitch=0.0,
            head_yaw=0.0, head_pitch=5.0, head_roll=0.0, jaw=8.0,
            r_az=-28.0, r_el=-55.0, r_reach=0.86, b_az=-16.0, b_el=-35.0,
            l_up=(0.35, -0.55, -0.75), l_fore=(0.1, -0.85, -0.3), l_hand=None, l_hand_w=0.0, l_hand_x=-16.0,
            cape_back=8.0, cape_yaw=None, flutter=0.0,
            lf_x=STANCE_FEET["left"][0], lf_y=STANCE_FEET["left"][1], lf_z=0.0, lf_p=0.0,
            rf_x=STANCE_FEET["right"][0], rf_y=STANCE_FEET["right"][1], rf_z=0.0, rf_p=0.0,
            lf_yaw=STANCE_YAW["left"], rf_yaw=STANCE_YAW["right"])


def combat_pose(r, f, K, extra=None):
    g = lambda k: track(K[k], f) if k in K else BASE[k]
    hy = g("hip_yaw")
    r.move("body", (g("bx"), -0.5 + g("by"), -2.5 + g("bz")))
    r.rotate("body", eul(g("lean"), g("roll"), hy))
    plant(r, "left", (g("lf_x"), g("lf_y")), z=g("lf_z"), pitch=g("lf_p"), yaw=g("lf_yaw"))
    plant(r, "right", (g("rf_x"), g("rf_y")), z=g("rf_z"), pitch=g("rf_p"), yaw=g("rf_yaw"))
    rel = g("chest_yaw") - hy
    trem = extra(f) if extra else 0.0
    r.rotate("waist", eul(2 + g("waist_pitch"), 0, rel * 0.4))
    r.rotate("chest", eul(3 + g("chest_pitch"), 0, rel * 0.6 + trem))
    head_world(r, yaw=g("head_yaw"), pitch=g("head_pitch"), roll=g("head_roll"))
    r.rotate("jaw", eul(g("jaw")))
    sh = r.head("right_arm")
    r.ik("right_arm", "right_forearm", sh + dir_az_el(g("r_az"), g("r_el")) * REACH_R * g("r_reach"), pole=Vector((-0.6, 0.5, -0.6)))
    bd = dir_az_el(g("b_az"), g("b_el"))
    r.aim("right_hand", bd)
    sword_to(r, bd)
    r.aim("left_arm", Vector(g("l_up")).normalized())
    r.aim("left_forearm", Vector(g("l_fore")).normalized())
    lh = g("l_hand")
    if lh is not None:
        r.aim("left_hand", Vector(lh).normalized(), blend=g("l_hand_w"))
    r.rotate("left_hand", eul(g("l_hand_x")))
    cy = g("cape_yaw") if "cape_yaw" in K else -0.35 * g("chest_yaw")
    cape(r, back=g("cape_back"), yaw=cy, flutter=g("flutter"))


