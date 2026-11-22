"""Stage 3 - the Gatekeeper's 13 boss clips (30 fps) + automatic checks (floor contact, arm clipping) + contact sheets."""
import bpy, sys, os, math, copy, json
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import gk_lib as L
import gk_pose as GP
import gk_scene as SC

OUT = sys.argv[sys.argv.index("--") + 1]
SHEETS_ON = "--no-sheets" not in sys.argv
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "gatekeeper_stage2.blend"))
scene = bpy.context.scene
scene.render.fps = 30
rig = bpy.data.objects["Gatekeeper_Rig"]
rig.animation_data_create()
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
P = GP.P
BF = GP.BASE_FEET
CLIPS = {}
EVENTS = {}


def deep(p, **ch):
    q = copy.deepcopy(p)
    for k, v in ch.items():
        if isinstance(v, dict) and isinstance(q.get(k), dict):
            q[k].update(v)
        else:
            q[k] = v
    return q


def make(name, keys, loop=False, events=None):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    rig.animation_data.action = act
    GP.reset_continuity()
    for f, pose in keys:
        GP.apply_pose(rig, pose)
        GP.key_all(rig, f)
    # in-between pass: evaluate every 2nd frame between keys and add a corrected key wherever something dips into the floor
    keyed = {k[0] for k in keys}
    fixes = 0
    for f in range(int(keys[0][0]), int(keys[-1][0]) + 1, 2):
        if f in keyed:
            continue
        scene.frame_set(f)
        if GP.fix_inbetween(rig):
            GP.reset_continuity()
            GP.key_all(rig, f); fixes += 1
    if fixes:
        print("  in-between fixes", name, fixes)
    act.frame_range = (keys[0][0], keys[-1][0])
    try:
        act.use_frame_range = True; act.use_cyclic = loop
    except Exception:
        pass
    CLIPS[name] = (keys[0][0], keys[-1][0], loop)
    EVENTS[name] = events or {}
    print("CLIP", name, len(keys), "keys", keys[-1][0], "frames", flush=True)


def xarm(spec_R):
    return {"extra_R": spec_R, "extra_L": GP.mirror_arm(spec_R)}


def mir(a):
    return GP.mirror_arm(a)


def ease(t):
    return t * t * (3 - 2 * t)


def chains(sw, fb=0.0):
    """Chain swing: sw = side-to-side degrees, fb = forward/back degrees."""
    return {"chain_chest": (fb, sw * 0.6, 0), "chain_belt": (fb * 1.2, sw, 0),
            "chain_shoulder_L": (fb, sw, 0), "chain_shoulder_R": (fb, sw, 0),
            "chain_shoulder_back_L": (-fb * 0.6, sw * 0.8, 0), "chain_shoulder_back_R": (-fb * 0.6, sw * 0.8, 0)}


S0 = GP.stance()
XR = S0["extra_R"]
AR = S0["arm_R"]
AL = S0["arm_L"]

# =============================================================== IDLE (loop, 160 f): breath, head, arms, chains, weapon shift
keys = []
for f in range(0, 161, 8):
    ph = 2 * math.pi * f / 80                       # two slow breaths per loop
    b = math.sin(ph)
    yaw = 14 * math.sin(2 * math.pi * f / 160 - 0.6) * (1 if f < 140 else (160 - f) / 20)
    p = P(hips={"loc": (0, 0, -1 - 0.8 * b)}, spine=(3 - 1.0 * b, 0, yaw * 0.1), chest=(3 - 2.0 * b, 0, yaw * 0.25),
          neck=(0, 0, yaw * 0.3), head=(8 + 1.5 * b, 0, yaw * 0.7),
          fire={"L": 1 + 0.12 * math.sin(ph * 3.1), "R": 1 + 0.12 * math.sin(ph * 2.7 + 1)},
          chains=chains(4 * math.sin(2 * math.pi * f / 160 + 1.2), 2 * b))
    p["extra_R"] = dict(XR, upper=(-0.95, -0.12 + 0.06 * math.sin(ph * 0.5), 0.28 + 0.07 * math.sin(ph * 0.5 + 0.8)), curl=40 + 10 * math.sin(ph * 0.5 + 1.5))
    p["extra_L"] = mir(dict(XR, upper=(-0.95, -0.12 + 0.06 * math.sin(ph * 0.5 + 2), 0.28 + 0.07 * math.sin(ph * 0.5 + 2.6)), curl=40 + 10 * math.sin(ph * 0.5 + 0.2)))
    p["robe_L"] = (1.5 * math.sin(ph + 1), 0, 0); p["robe_R"] = (1.5 * math.sin(ph + 2), 0, 0)
    if 96 <= f <= 136:                               # occasional weapon movement: lifts and drags the tip
        t = math.sin(math.pi * (f - 96) / 40)
        p["arm_R"] = dict(AR, upper=(-0.6, -0.25 + 0.12 * t, -0.76), fore=(-0.55, -0.75 + 0.2 * t, -0.35 + 0.15 * t))
        p["weapon"] = {"dir": (-0.5, -0.25 + 0.2 * t, -0.83), "normal": (0, -1, 0), "ground": "touch"}
    keys.append((f, p))
make("Gatekeeper_Idle", keys, loop=True, events={"sword_scrape": [104, 122]})

# =============================================================== AWAKENING (180 f): dormant -> arms unfold -> head turns -> rises dragging sword -> eyes open
KNEEL_FEET = {"L": (11, 14, 7), "R": (-11, 14, 7)}
LIMP_X = {"upper": (-0.4, -0.3, -0.86), "fore": (-0.2, -0.35, -0.9), "curl": 20, "thumb": 10}
FOLDED_X = {"upper": (-0.55, -0.6, -0.58), "fore": (0.1, -0.75, -0.65), "curl": 90, "thumb": 70}   # tucked down in front
DORMANT = dict(hips={"loc": (0, 2, -17)}, spine=(15, 0, 0), chest=(28, 0, -10), neck=(5, 0, -10), head=(35, 0, -25), feet=KNEEL_FEET,
               foot_pitch={"L": 0, "R": 0}, **xarm(FOLDED_X), fire={"L": 0.01, "R": 0.01},
               arm_R={"upper": (-0.6, -0.45, -0.66), "fore": (-0.3, -0.65, -0.7), "hand": (-0.2, -0.65, -0.73), "curl": 100},
               weapon={"dir": (-0.1, -0.35, -0.93), "normal": (0, -1, 0), "ground": "touch"},
               arm_L={"upper": (0.6, -0.2, -0.77), "fore": (0.45, -0.35, -0.82), "curl": 70})
UNFOLD = {"upper": (-0.9, -0.15, 0.1), "fore": (-0.55, -0.2, 0.55), "curl": 30}
make("Gatekeeper_Awakening", [
    (0, P(**DORMANT)),
    (24, P(**deep(DORMANT, chest=(27, 0, -10)))),                                                      # stillness
    (44, P(**deep(DORMANT, extra_R={"upper": (-0.7, -0.3, -0.4), "fore": (-0.4, -0.4, -0.3), "curl": 60}, fire={"R": 0.25, "L": 0.01}))),
    (62, P(**deep(DORMANT, extra_R=UNFOLD, extra_L={"upper": (0.7, -0.3, -0.4), "fore": (0.4, -0.4, -0.3), "curl": 60}, fire={"R": 0.5, "L": 0.25}))),
    (80, P(**deep(DORMANT, **xarm(UNFOLD), head=(30, 0, -18), fire={"R": 0.6, "L": 0.55}))),
    (100, P(**deep(DORMANT, **xarm(UNFOLD), neck=(5, 0, 0), head=(26, 0, 0), chest=(26, 0, 0)))),               # head turns to the player
    (124, P(**deep(DORMANT, **xarm(UNFOLD), hips={"loc": (0, 1, -9)}, spine=(10, 0, 0), chest=(18, 0, 0), head=(24, 0, 0),
                   feet={"L": (11, -2, 7), "R": (-11, 14, 7)}, foot_pitch={"L": 0, "R": 0},
                   arm_R={"upper": (-0.45, 0.2, -0.87), "fore": (-0.4, 0.3, -0.86)}, weapon={"dir": (-0.3, 0.6, -0.75), "normal": (-1, 0, 0), "ground": "touch"}))),
    (148, P(hips={"loc": (0, 0, -2)}, chest=(8, 0, 0), head=(24, 0, 0), **xarm(UNFOLD), fire={"L": 0.8, "R": 0.8},
            arm_R=dict(AR, upper=(-0.5, 0.1, -0.86), fore=(-0.5, -0.2, -0.85)), weapon={"dir": (-0.45, 0.2, -0.87), "normal": (0, -1, 0), "ground": "touch"})),
    (166, P(head=(6, 0, 0), fire={"L": 1.1, "R": 1.1})),                                                # raises head, eyes open
    (180, P()),
], events={"arm_unfold": [44, 62], "head_turn": [100], "sword_drag_sparks": [110, 150], "eyes_open": [160], "fire_ignite": [44, 62]})

# =============================================================== ENTRANCE (100 f, root motion): one heavy step forward, blocks the entrance
make("Gatekeeper_Entrance", [
    (0, P()),
    (14, P(hips={"loc": (-2, 2, -4), "rot": (0, -4, 0)}, chest=(10, 0, 0), head=(12, 0, 0))),                                    # weight onto the back leg
    (30, P(hips={"loc": (-3, -4, 1), "rot": (0, -6, 0)}, chest=(2, 0, 0), feet={"L": (12, -16, 16), "R": BF["R"]}, foot_pitch={"L": -10, "R": 0},
           **xarm(UNFOLD))),
    (40, P(hips={"loc": (0, -14, -6)}, chest=(14, 0, 0), head=(16, 0, 0), feet={"L": (12, -30, 7), "R": BF["R"]}, robe_F=(8, 0, 0),
           chains=chains(0, 10), **xarm({"upper": (-0.95, -0.2, 0.1), "fore": (-0.6, -0.3, 0.6), "curl": 40}))),                      # impact
    (46, P(hips={"loc": (0, -14, -4.5)}, chest=(10, 0, 0), head=(12, 0, 0), feet={"L": (12, -30, 7), "R": BF["R"]}, chains=chains(0, -6))),
    (64, P(hips={"loc": (0, -16, -1)}, chest=(-4, 0, 0), head=(-6, 0, 0), feet={"L": (12, -30, 7), "R": (-11, -16, 10)}, foot_pitch={"R": -8, "L": 0},
           **xarm({"upper": (-0.85, -0.05, 0.5), "fore": (-0.5, -0.1, 0.86), "curl": 10}), fire={"L": 1.5, "R": 1.5})),
    (74, P(root=(0, -32, 0), hips={"loc": (0, 0, -3)}, chest=(-6, 0, 0), head=(-10, 0, 0), feet={"L": (12, -30, 7), "R": (-11, -30, 7)},
           **xarm({"upper": (-0.85, -0.05, 0.5), "fore": (-0.5, -0.1, 0.86), "curl": 10}), fire={"L": 1.6, "R": 1.6})),
    (88, P(root=(0, -32, 0), feet={"L": (11, -34, 7), "R": (-11, -30, 7)}, fire={"L": 1.2, "R": 1.2})),
    (100, P(root=(0, -32, 0), feet={"L": (11, -34, 7), "R": (-11, -30, 7)})),
], events={"heavy_step": [40, 74], "roar": [64]})


# =============================================================== WALKS (root motion, loop)
def walk(name, N, stride, impact_k, lean, drag=False, lift=7.0, events=None):
    keys = []
    for f in range(0, N + 1, 4):
        feet, pitch = {}, {}
        for S in ("L", "R"):
            x = 11 if S == "L" else -11
            y0 = -0.5 * stride if S == "L" else 0.5 * stride
            swing_start = N / 2 if S == "L" else 0
            local = (f - swing_start) % N
            if local < N / 2 and not (S == "L" and f == 0):
                t = local / (N / 2)
                base = y0 if S == "R" else y0
                yy = (y0 if S == "R" else y0) + (-2 * stride) * ease(t)
                if S == "L":
                    yy = y0 + (-2 * stride) * ease(t)
                feet[S] = (x, yy, 7 + lift * math.sin(math.pi * t ** 0.75)); pitch[S] = -12 * math.sin(math.pi * t)
            else:
                planted_y = y0 if (S == "L" and f <= N / 2) else (y0 - 2 * stride)
                if S == "R" and f < N / 2:
                    planted_y = y0
                feet[S] = (x, planted_y, 7); pitch[S] = 0
        # explicit, unambiguous foot schedule
        tL = None if f <= N / 2 else (f - N / 2) / (N / 2)
        tR = f / (N / 2) if f < N / 2 else None
        feet["L"] = (11, -0.5 * stride, 7) if tL is None else (11, -0.5 * stride - 2 * stride * ease(tL), 7 + lift * math.sin(math.pi * tL ** 0.75))
        feet["R"] = (-11, -1.5 * stride, 7) if tR is None else (-11, 0.5 * stride - 2 * stride * ease(tR), 7 + lift * math.sin(math.pi * tR ** 0.75))
        pitch = {"L": 0 if tL is None else -12 * math.sin(math.pi * tL), "R": 0 if tR is None else -12 * math.sin(math.pi * tR)}
        root_y = -2 * stride * f / N
        step = 2 * math.pi * f / (N / 2)
        impact = math.exp(-((f % (N // 2)) / 3.0)) * impact_k
        sway = math.sin(2 * math.pi * f / N)
        p = P(root=(0, root_y, 0), feet=feet, foot_pitch=pitch,
              hips={"loc": (2.4 * sway, 0, -1.6 - 1.6 * math.cos(step) - 1.6 * impact), "rot": (0, 4 * sway, 5 * sway)},
              spine=(3 + 2 * impact, 0, -3 * sway), chest=(lean + 3 * impact, -2 * sway, -4 * sway), head=(8 + 3 * impact, 0, 6 * sway),
              robe_L=(-6 * math.sin(2 * math.pi * f / N - 0.6), 0, 0), robe_R=(6 * math.sin(2 * math.pi * f / N - 0.6), 0, 0),
              robe_F=(3 * impact, 0, 0), robe_B=(-4 * impact, 0, 0), chains=chains(5 * math.sin(2 * math.pi * f / N - 0.9), 6 * impact))
        swing = math.sin(2 * math.pi * f / N + math.pi)
        p["arm_L"] = dict(AL, clav=(0, 0, 4 * swing), upper=(0.52, -0.15 - 0.35 * swing, -0.84), fore=(0.3, -0.6 - 0.2 * swing, -0.74))
        drop = 0.12 * impact
        p["extra_R"] = dict(XR, clav=(0, 10 - 4 * impact, 0), upper=(-0.95, -0.12 + 0.12 * swing, 0.28 - drop), fore=(-0.2, -0.3 + 0.1 * swing, 0.93 - drop))
        p["extra_L"] = mir(dict(XR, clav=(0, 10 - 4 * impact, 0), upper=(-0.95, -0.12 - 0.12 * swing, 0.28 - drop), fore=(-0.2, -0.3 - 0.1 * swing, 0.93 - drop)))
        if drag:
            p["arm_R"] = dict(AR, upper=(-0.45, 0.35, -0.82), fore=(-0.4, 0.45, -0.8), hand=(-0.35, 0.5, -0.8), curl=105)
            p["weapon"] = {"dir": (-0.35, 0.8, -0.5), "normal": (-1, 0, 0), "ground": "touch"}
        else:
            p["arm_R"] = dict(AR, upper=(-0.6, -0.25 + 0.2 * swing, -0.76))      # the sword's weight keeps this arm low and slow
        keys.append((f, p))
    make(name, keys, loop=True, events=events)


walk("Gatekeeper_Walking", 56, 18, 0.6, 4, lift=6, events={"footstep": [0, 28]})
walk("Gatekeeper_Heavy_Walk", 72, 22, 1.3, 8, lift=8, events={"heavy_footstep": [0, 36]})
walk("Gatekeeper_Sword_Drag", 80, 16, 1.0, 10, drag=True, events={"footstep": [0, 40], "sword_drag_sparks": [0, 80]})

# =============================================================== OVERHEAD ATTACK (72 f)
UP_WIDE = {"upper": (-0.75, -0.05, 0.65), "fore": (-0.4, -0.05, 0.92), "curl": 10, "thumb": 10}
SLAM = {"upper": (-0.45, -0.85, 0.15), "fore": (-0.1, -0.8, -0.6), "curl": 80}
RAISED = dict(arm_R={"upper": (-0.6, 0.15, 0.78), "fore": (-0.15, 0.5, 0.85), "hand": (-0.05, 0.65, 0.76)}, weapon={"dir": (0.1, 0.72, 0.68), "normal": (0, -1, 0), "ground": None},
              arm_L={"upper": (0.6, -0.35, 0.3), "fore": (0.3, -0.3, 0.9)}, **xarm(UP_WIDE))
SMASH_FEET = {"L": BF["L"], "R": (-11, -8, 7)}
make("Gatekeeper_Overhead_Attack", [
    (0, P()),
    (10, P(hips={"loc": (0, 4, -3)}, chest=(-4, 0, 0), arm_R={"upper": (-0.5, 0.45, -0.74), "fore": (-0.4, 0.5, -0.77)},            # pull sword backward
           weapon={"dir": (-0.35, 0.7, -0.6), "normal": (-1, 0, 0), "ground": "clamp"}, chains=chains(0, -5))),
    (22, P(hips={"loc": (0, 3, 1)}, spine=(-6, 0, 0), chest=(-14, 0, 0), head=(-6, 0, 0), fire={"L": 1.4, "R": 1.4}, **RAISED)),       # raised above the body
    (28, P(hips={"loc": (0, 3.5, 1.5)}, spine=(-7, 0, 0), chest=(-16, 0, 0), head=(-8, 0, 0), fire={"L": 1.5, "R": 1.5},              # hold the anticipation
           **deep(RAISED, weapon={"dir": (0.1, 0.78, 0.62), "normal": (0, -1, 0), "ground": None}))),
    (30, P(hips={"loc": (0, 3.5, 1.5)}, spine=(-7, 0, 0), chest=(-16, 0, 0), head=(-8, 0, 0), fire={"L": 1.5, "R": 1.5},
           feet={"L": BF["L"], "R": (-11, -3, 12)}, **deep(RAISED, weapon={"dir": (0.1, 0.78, 0.62), "normal": (0, -1, 0), "ground": None}))),
    (34, P(hips={"loc": (0, -4, -7)}, spine=(10, 0, 0), chest=(27, 0, 0), head=(18, 0, 0), feet=SMASH_FEET,                       # smash
           arm_R={"upper": (-0.5, -0.86, -0.1), "fore": (-0.3, -0.9, -0.3), "hand": (-0.2, -0.85, -0.5)}, weapon={"dir": (-0.1, -0.8, -0.6), "normal": (0, 0, 1), "ground": "touch"},
           arm_L={"upper": (0.6, -0.7, -0.4), "fore": (0.45, -0.7, -0.55)}, **xarm(SLAM), fire={"L": 1.9, "R": 1.9}, chains=chains(0, 14))),
    (37, P(hips={"loc": (0, -4, -8.5)}, spine=(11, 0, 0), chest=(30, 0, 0), head=(22, 0, 0), feet=SMASH_FEET,                     # impact compression
           arm_R={"upper": (-0.5, -0.86, -0.12), "fore": (-0.3, -0.88, -0.35), "hand": (-0.2, -0.83, -0.52)}, weapon={"dir": (-0.1, -0.8, -0.6), "normal": (0, 0, 1), "ground": "touch"},
           arm_L={"upper": (0.6, -0.7, -0.4), "fore": (0.45, -0.7, -0.55)}, **xarm(SLAM), fire={"L": 1.3, "R": 1.3}, chains=chains(0, -8))),
    (42, P(hips={"loc": (0, -3.5, -6.5)}, spine=(9, 0, 0), chest=(26, 0, 0), head=(17, 0, 0), feet=SMASH_FEET,
           arm_R={"upper": (-0.5, -0.85, -0.12), "fore": (-0.3, -0.88, -0.35)}, weapon={"dir": (-0.1, -0.8, -0.6), "normal": (0, 0, 1), "ground": "touch"},
           arm_L={"upper": (0.6, -0.7, -0.4), "fore": (0.45, -0.7, -0.55)}, **xarm(SLAM), chains=chains(0, 5))),
    (56, P(hips={"loc": (0, -1.5, -3)}, chest=(12, 0, 0), head=(12, 0, 0), feet=SMASH_FEET, arm_R={"upper": (-0.6, -0.5, -0.62), "fore": (-0.5, -0.7, -0.5)})),   # recovery
    (64, P(feet={"L": BF["L"], "R": (-11, -2, 11)})),
    (72, P()),
], events={"windup": [10], "impact": [34], "ground_crack": [34], "camera_shake": [34]})

# =============================================================== HORIZONTAL SWEEP (66 f): torso + hips rotation, wide arc, shockwave
def sweep_arm(t):
    """t from 0 (wound back on his right) to 1 (finished across on his left)."""
    ang = math.radians(-150 + 210 * t)                 # angle of the blade in the horizontal plane (0 = straight forward)
    d = (math.sin(ang) * 1.0, -math.cos(ang), -0.12)
    return d


SWEEP_FEET = {"L": (13, -5, 7), "R": (-12, 5, 7)}
keys = [(0, P())]
plan = [(10, 0.0, -30, -10, -4), (16, 0.02, -36, -12, -4.5), (20, 0.25, -24, -8, -5), (23, 0.5, -4, -2, -5), (26, 0.75, 18, 7, -5),
        (29, 0.95, 30, 11, -4.5), (34, 1.05, 34, 13, -4)]
for f, t, chest_z, hips_z, hz in plan:
    d = sweep_arm(t)
    ad = Vector(d)
    # the sword arm swings out in front of the body (never across the waist): the arm leads, reaching forward
    fwd = 0.55 + 0.75 * max(0.0, t - 0.4)
    upper = (ad * (0.6 - 0.25 * max(0.0, t - 0.5)) + Vector((-0.45 * (1 - t), -fwd, -0.1))).normalized()
    fore = (ad + Vector((0, -0.3 - 0.5 * max(0.0, t - 0.5), 0.05))).normalized()
    xr = {"upper": (-0.9, -0.1 + 0.6 * (t - 0.5), 0.35), "fore": (-0.4, -0.3, 0.85), "curl": 40}     # extra arms react to the swing
    # the fist arm braces out of the blade's path: forward early, pulled back and wide as the sword comes across
    al = {"upper": (0.5, -0.75, -0.42), "fore": (0.3, -0.85, -0.42)} if t < 0.5 else {"upper": (0.8, 0.35, -0.48), "fore": (0.6, 0.55, -0.58)}
    keys.append((f, P(hips={"loc": (0, 0, hz), "rot": (0, 0, hips_z)}, chest=(7, 0, chest_z), head=(8, 0, -chest_z * 0.45), feet=SWEEP_FEET,
                      arm_R={"upper": tuple(upper), "fore": tuple(fore), "hand": tuple(ad), "curl": 105}, weapon={"dir": d, "normal": (0, 0, 1), "ground": "clamp"},
                      arm_L=dict(al, curl=130),
                      extra_R=xr, extra_L=mir(dict(xr, upper=(-0.9, -0.1 - 0.6 * (t - 0.5), 0.35))),
                      chains=chains(14 * (t - 0.5), 0))))
keys += [(46, P(hips={"loc": (0, 0, -2), "rot": (0, 0, 6)}, chest=(5, 0, 14), head=(8, 0, -6), feet=SWEEP_FEET, chains=chains(-6, 0),
                arm_R={"upper": (-0.3, -0.7, -0.6), "fore": (-0.1, -0.8, -0.6)})),
         (58, P(feet={"L": (12, -2, 9), "R": BF["R"]})), (66, P())]
make("Gatekeeper_Horizontal_Sweep", keys, events={"windup": [10], "swing": [20], "shockwave": [24], "impact": [24]})

# =============================================================== MULTI-ARM ATTACK (110 f): staggered, arms support/guard/prepare
CLAW_BACK = {"upper": (-0.8, 0.5, 0.3), "fore": (-0.3, 0.6, 0.75), "curl": 5, "thumb": 5}
CLAW_HIT = {"upper": (-0.35, -0.92, 0.15), "fore": (0.12, -0.9, -0.4), "curl": 75, "thumb": 60}
CLAW_GUARD = {"upper": (-0.55, -0.75, 0.35), "fore": (0.5, -0.55, 0.65), "curl": 60, "thumb": 40}
FIST_BACK = {"upper": (0.5, 0.55, -0.65), "fore": (0.3, 0.75, 0.3), "curl": 130}
FIST_HIT = {"upper": (0.22, -0.95, -0.2), "fore": (0.05, -1, 0.0), "hand": (0.02, -1, 0.02), "curl": 130}
WIND_R = {"upper": (-0.85, 0.45, -0.1), "fore": (-0.55, 0.8, -0.1), "hand": (-0.45, 0.85, -0.1)}
make("Gatekeeper_Multi_Arm_Attack", [
    (0, P()),
    (7, P(chest=(0, 0, -12), extra_R=CLAW_BACK, extra_L=mir(CLAW_GUARD), arm_L=dict(AL, upper=(0.5, 0.2, -0.84)), hips={"loc": (0, 1, -2)})),
    (12, P(chest=(10, 0, 10), extra_R=CLAW_HIT, extra_L=mir(CLAW_GUARD), arm_L=dict(AL, upper=(0.5, 0.3, -0.8)), hips={"loc": (0, -1, -4)}, fire={"R": 1.7, "L": 1})),
    (18, P(chest=(4, 0, 4), extra_R=dict(CLAW_HIT, upper=(-0.6, -0.7, 0.2)), extra_L=mir(CLAW_BACK), arm_L=FIST_BACK)),
    (24, P(chest=(10, 0, -12), extra_R=CLAW_GUARD, extra_L=mir(CLAW_HIT), arm_L=FIST_BACK, hips={"loc": (0, -1, -4)}, fire={"L": 1.7, "R": 1})),
    (30, P(chest=(12, 0, 16), hips={"loc": (0, -2, -4), "rot": (0, 0, 8)}, extra_R=CLAW_GUARD, extra_L=mir(dict(CLAW_HIT, upper=(-0.5, -0.8, 0.2))), arm_L=FIST_HIT,
           feet={"L": (12, -9, 7), "R": (-11, 4, 7)})),
    (35, P(chest=(13, 0, 18), hips={"loc": (0, -2.5, -4.5), "rot": (0, 0, 9)}, extra_R=CLAW_GUARD, extra_L=mir(CLAW_GUARD), arm_L=FIST_HIT,
           feet={"L": (12, -9, 7), "R": (-11, 4, 7)})),
    (44, P(chest=(6, 0, -6), hips={"loc": (0, -1, -3)}, extra_R=CLAW_BACK, extra_L=mir(CLAW_BACK), arm_L=dict(AL, upper=(0.4, -0.6, -0.7)),
           feet={"L": (12, -9, 7), "R": (-11, 4, 7)})),
    (52, P(hips={"loc": (0, 0, -4), "rot": (0, 0, -10)}, chest=(6, 0, -32), head=(8, 0, 18), arm_R=WIND_R, weapon={"dir": (-0.45, 0.88, -0.1), "normal": (0, 0, 1), "ground": "clamp"},
           extra_R=CLAW_GUARD, extra_L=mir(CLAW_BACK), feet={"L": (12, -9, 7), "R": (-12, 4, 7)})),
    (58, P(hips={"loc": (0, -1, -5)}, chest=(8, 0, 0), arm_R={"upper": (-0.6, -0.7, -0.3), "fore": (-0.2, -0.97, -0.1), "hand": (-0.1, -0.99, -0.05)},
           weapon={"dir": (-0.25, -0.96, -0.1), "normal": (0, 0, 1), "ground": "clamp"}, extra_L=mir(CLAW_HIT), extra_R=CLAW_BACK, feet={"L": (12, -9, 7), "R": (-12, 4, 7)})),
    (62, P(hips={"loc": (0, -1, -5), "rot": (0, 0, 8)}, chest=(8, 0, 20), arm_R={"upper": (-0.25, -0.95, -0.12), "fore": (0.3, -0.93, -0.1), "hand": (0.5, -0.85, -0.15)},
           weapon={"dir": (0.55, -0.82, -0.15), "normal": (0, 0, 1), "ground": "clamp"}, extra_L=mir(CLAW_HIT), extra_R=CLAW_HIT, feet={"L": (12, -9, 7), "R": (-12, 4, 7)},
           fire={"L": 1.8, "R": 1.8})),
    (68, P(hips={"loc": (0, -1, -4), "rot": (0, 0, 13)}, chest=(7, 0, 32), head=(8, 0, -14), arm_R={"upper": (0.1, -0.97, -0.1), "fore": (0.7, -0.7, -0.1)},
           weapon={"dir": (0.92, -0.35, -0.2), "normal": (0, 0, 1), "ground": "clamp"}, extra_R=dict(CLAW_HIT, upper=(-0.5, -0.8, 0.0)), extra_L=mir(CLAW_GUARD),
           feet={"L": (12, -9, 7), "R": (-12, 4, 7)})),
    (86, P(hips={"loc": (0, 0, -2)}, chest=(5, 0, 12), feet={"L": (12, -5, 9), "R": BF["R"]})),
    (110, P()),
], events={"claw_R": [12], "claw_L": [24], "punch": [30], "sword_sweep": [58], "claws_both": [62]})

# =============================================================== BLOCK (44 f)
BLOCK = dict(hips={"loc": (0, 0, -5)}, chest=(6, 0, 0), head=(12, 0, 0),
             arm_R={"upper": (-0.55, -0.62, -0.1), "fore": (0.5, -0.8, 0.2), "hand": (0.6, -0.75, 0.2), "curl": 105},
             weapon={"dir": (1, -0.1, 0.25), "normal": (0, -1, 0), "ground": None},
             extra_R={"upper": (-0.6, -0.7, 0.3), "fore": (0.6, -0.55, 0.55), "curl": 70, "thumb": 50},
             extra_L=mir({"upper": (-0.6, -0.7, 0.3), "fore": (0.6, -0.55, 0.55), "curl": 70, "thumb": 50}),
             arm_L={"upper": (0.4, -0.7, -0.5), "fore": (-0.2, -0.9, 0.3), "curl": 130},
             feet={"L": (14, -4, 7), "R": (-13, 4, 7)})
make("Gatekeeper_Block", [
    (0, P()),
    (6, P(hips={"loc": (0, 0, -2)}, chest=(4, 0, 0))),
    (12, P(**BLOCK)),
    (16, P(**deep(BLOCK, chest=(9, 0, 0), hips={"loc": (0, 2, -6)}, chains=chains(0, -8)))),          # absorbs a hit
    (22, P(**deep(BLOCK, chains=chains(0, 4)))),
    (44, P(**deep(BLOCK, chest=(7, 0, 0)))),
], events={"block_impact": [16]})

# =============================================================== STAGGER (48 f)
FLUNG = {"upper": (-0.9, 0.3, 0.4), "fore": (-0.4, 0.45, 0.8), "curl": 0, "thumb": 0}
make("Gatekeeper_Stagger", [
    (0, P()),
    (4, P(hips={"loc": (0, 3, -1)}, chest=(-16, 0, 6), head=(-22, 0, 10), **xarm(FLUNG), arm_L={"upper": (0.8, 0.3, -0.4), "fore": (0.7, 0.4, -0.2)}, chains=chains(6, -12))),
    (10, P(hips={"loc": (0, 6, 0)}, chest=(-20, 0, 8), head=(-16, 0, 12), **xarm(FLUNG), arm_L={"upper": (0.8, 0.3, -0.4), "fore": (0.7, 0.4, -0.2)},
           feet={"L": BF["L"], "R": (-12, 9, 12)}, foot_pitch={"R": -10, "L": 0}, chains=chains(-4, -16))),
    (14, P(hips={"loc": (0, 6, -4)}, chest=(-8, 0, 4), head=(-4, 0, 6), feet={"L": BF["L"], "R": (-12, 12, 7)}, chains=chains(-2, 8))),
    (22, P(hips={"loc": (0, 4, -3)}, chest=(10, 0, -3), head=(14, 0, -4), feet={"L": BF["L"], "R": (-12, 12, 7)}, chains=chains(2, 6))),
    (32, P(hips={"loc": (0, 2, -2)}, chest=(4, 0, 0), feet={"L": BF["L"], "R": (-12, 7, 9)})),
    (48, P()),
], events={"hit": [2], "stumble_step": [14]})

# =============================================================== RAGE (100 f)
GATHER = {"upper": (-0.7, -0.6, -0.3), "fore": (-0.25, -0.75, -0.6), "curl": 110, "thumb": 80}
SPREAD = {"upper": (-0.8, 0.05, 0.6), "fore": (-0.5, 0.0, 0.87), "curl": 0, "thumb": 0}
ROAR = dict(hips={"loc": (0, 0, 1)}, spine=(-8, 0, 0), chest=(-20, 0, 0), head=(-30, 0, 0), **xarm(SPREAD),
            arm_L={"upper": (0.88, -0.3, -0.37), "fore": (0.7, -0.4, 0.6), "curl": 130},                    # main arms spread wide below the shoulder blocks
            arm_R={"upper": (-0.88, -0.3, -0.37), "fore": (-0.7, -0.45, 0.55), "hand": (-0.6, -0.4, 0.7)},
            weapon={"dir": (-0.6, -0.15, 0.78), "normal": (0, -1, 0), "ground": None}, fire={"L": 2.2, "R": 2.2})
keys = [(0, P()),
        (14, P(hips={"loc": (0, 0, -9)}, spine=(10, 0, 0), chest=(22, 0, 0), head=(16, 0, 0), **xarm(GATHER), fire={"L": 0.6, "R": 0.6},
               arm_L={"upper": (0.55, -0.55, -0.63), "fore": (0.25, -0.7, -0.67), "curl": 130})),
        (28, P(**ROAR, chains=chains(0, -14)))]
for i, f in enumerate(range(31, 64, 3)):
    j = 1 if i % 2 else -1
    keys.append((f, P(**deep(ROAR, chest=(-20 + 2.5 * j, 0, 3 * j), head=(-30 + 3 * j, 0, -4 * j), fire={"L": 2.0 + 0.3 * j, "R": 2.0 - 0.3 * j}, chains=chains(5 * j, -6)))))
keys += [(76, P(**deep(ROAR, chest=(-14, 0, 0), head=(-18, 0, 0), fire={"L": 1.6, "R": 1.6}))), (100, P())]
make("Gatekeeper_Rage", keys, events={"roar": [28], "camera_shake": [30, 60]})

# =============================================================== DEATH (130 f)
KNEEL = dict(hips={"loc": (0, 2, -16)}, spine=(10, 0, 0), chest=(22, 0, 0), head=(20, 0, 0), feet=KNEEL_FEET, foot_pitch={"L": 0, "R": 0},
             **xarm({"upper": (-0.6, -0.3, -0.6), "fore": (-0.3, -0.4, -0.85), "curl": 30}), fire={"L": 0.6, "R": 0.6},
             arm_R={"upper": (-0.6, -0.3, -0.75), "fore": (-0.5, -0.4, -0.75)}, weapon={"dir": (-0.6, -0.2, -0.78), "normal": (0, -1, 0), "ground": "touch"},
             arm_L={"upper": (0.5, -0.2, -0.85), "fore": (0.3, -0.3, -0.9), "curl": 60})
FALLEN = dict(hips={"loc": (0, -12, -22), "rot": (60, 0, 0)}, spine=(6, 0, 0), chest=(8, 0, 0), head=(10, 0, 8), feet=KNEEL_FEET, foot_pitch={"L": 0, "R": 0},
              **xarm({"upper": (-0.95, 0.1, 0.0), "fore": (-0.9, 0.3, -0.1), "curl": 20}), fire={"L": 0.0, "R": 0.0},
              arm_R={"upper": (-0.9, 0.2, -0.2), "fore": (-0.8, 0.5, -0.2)}, weapon={"dir": (-0.7, 0.6, -0.3), "normal": (0, 0, 1), "ground": "touch"},
              arm_L={"upper": (0.9, 0.2, -0.2), "fore": (0.8, 0.5, -0.2), "curl": 40})
make("Gatekeeper_Death", [
    (0, P()),
    (6, P(hips={"loc": (0, 3, -1)}, chest=(-14, 0, 6), head=(-20, 0, 10), **xarm(FLUNG), chains=chains(4, -12))),
    (16, P(hips={"loc": (0, -2, -3)}, chest=(16, 0, -4), head=(18, 0, 0), fire={"L": 0.9, "R": 0.9}, chains=chains(-3, 10))),
    (30, P(**KNEEL)),
    (34, P(**deep(KNEEL, hips={"loc": (0, 2, -17.5)}, chest=(25, 0, 0), chains=chains(0, 12)))),
    (50, P(**deep(KNEEL, chest=(18, 0, 4)))),
    (66, P(**deep(KNEEL, chest=(24, 0, -3), fire={"L": 0.3, "R": 0.3}))),
    (82, P(**deep(KNEEL, hips={"loc": (0, -3, -18), "rot": (22, 0, 0)}, fire={"L": 0.15, "R": 0.15}))),
    (98, P(**FALLEN)),
    (102, P(**deep(FALLEN, hips={"loc": (0, -12, -20.5), "rot": (56, 0, 0)}))),
    (108, P(**FALLEN)),
    (130, P(**FALLEN)),
], events={"hit": [2], "knees_hit_ground": [30], "body_hits_ground": [98], "eyes_fade": [98, 120]})

# =============================================================== CHECKS
meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == rig]
for o in meshes:
    for m in o.modifiers:
        if m.type == "BEVEL":
            m.show_viewport = False
OB = {o.name: o for o in meshes}


def world_mesh(o, dg):
    ev = o.evaluated_get(dg)
    m = ev.to_mesh()
    vs = [o.matrix_world @ v.co for v in m.vertices]
    polys = [tuple(p.vertices) for p in m.polygons]
    ev.to_mesh_clear()
    return vs, polys


def group_polys(o, prefixes):
    names = {g.index: g.name for g in o.vertex_groups}
    member = [False] * len(o.data.vertices)
    for v in o.data.vertices:
        for g in v.groups:
            if names[g.group].startswith(prefixes):
                member[v.index] = True
    return [i for i, p in enumerate(o.data.polygons) if all(member[k] for k in p.vertices)]


ARMS = {
    "arm_R": (("GK_Arm_R", "GK_Armor_Arms"), ("forearm_R", "hand_R", "finger1_R", "finger2_R", "finger3_R", "thumb_R")),
    "arm_L": (("GK_Arm_L", "GK_Armor_Arms"), ("forearm_L", "hand_L", "finger1_L", "finger2_L", "finger3_L", "thumb_L")),
    "extra_R": (("GK_Arm_Extra_R", "GK_Armor_Arms"), ("forearm_extra_R", "hand_extra_R", "finger1_extra_R", "finger2_extra_R", "finger3_extra_R", "thumb_extra_R")),
    "extra_L": (("GK_Arm_Extra_L", "GK_Armor_Arms"), ("forearm_extra_L", "hand_extra_L", "finger1_extra_L", "finger2_extra_L", "finger3_extra_L", "thumb_extra_L")),
}
ARM_POLYS = {k: {on: group_polys(OB[on], tuple(pre)) for on in objs} for k, (objs, pre) in ARMS.items()}
TORSO_PRE = ("hips", "spine", "chest", "neck", "head")
OBST_POLYS = {on: group_polys(OB[on], TORSO_PRE) for on in ("GK_Torso", "GK_Head", "GK_Armor")}

report = {}
for name, (f0, f1, loop) in CLIPS.items():
    rig.animation_data.action = bpy.data.actions[name]
    low, clip_hits = 1e9, {}
    for f in range(int(f0), int(f1) + 1, 4):
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        W = {on: world_mesh(OB[on], dg) for on in set(sum([list(v[0]) for v in ARMS.values()], [])) | {"GK_Torso", "GK_Head", "GK_Armor", "GK_Weapon", "GK_Robe", "GK_Legs", "GK_Chains"}}
        for on, (vs, _) in W.items():
            low = min(low, min(v.z for v in vs))
        obst = []
        for on, idx in OBST_POLYS.items():
            vs, polys = W[on]
            obst.append(BVHTree.FromPolygons(vs, [polys[i] for i in idx], epsilon=0.0))
        wv, wp = W["GK_Weapon"]
        weapon_t = BVHTree.FromPolygons(wv, wp)
        for arm, objs in ARM_POLYS.items():
            hits = 0
            for on, idx in objs.items():
                vs, polys = W[on]
                if not idx:
                    continue
                t = BVHTree.FromPolygons(vs, [polys[i] for i in idx], epsilon=0.0)
                for ob_t in obst:
                    hits += len(t.overlap(ob_t))
                if arm != "arm_R":
                    hits += len(t.overlap(weapon_t))
            if hits:
                clip_hits.setdefault(arm, []).append((f, hits))
    report[name] = {"lowest_px": round(low * 16, 2), "arm_clipping": {a: v for a, v in clip_hits.items()}}
    print("CHECK", name, json.dumps(report[name]), flush=True)
json.dump(report, open(os.path.join(OUT, "anim_checks.json"), "w"), indent=1)
for o in meshes:
    for m in o.modifiers:
        if m.type == "BEVEL":
            m.show_viewport = True

rig.animation_data.action = bpy.data.actions["Gatekeeper_Idle"]
scene["gk_clips"] = {k: [v[0], v[1], int(v[2])] for k, v in CLIPS.items()}
scene["gk_events"] = json.dumps(EVENTS)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "gatekeeper_stage3.blend"))

# =============================================================== contact sheets (8 frames per clip, reading order left->right, top->bottom)
if SHEETS_ON:
    SC.setup(fog=False, arena=False)
    SHEETS = os.path.join(OUT, "anim_sheets")
    os.makedirs(SHEETS, exist_ok=True)
    for f_ in os.listdir(SHEETS):
        os.remove(os.path.join(SHEETS, f_))
    TW, TH = 300, 340
    for name, (f0, f1, loop) in CLIPS.items():
        rig.animation_data.action = bpy.data.actions[name]
        tiles = []
        for i in range(8):
            f = round(f0 + (f1 - f0) * i / 7)
            scene.frame_set(f)
            rp = rig.pose.bones["root"].head
            c = Vector((rp.x, rp.y, 0))
            p = os.path.join(SHEETS, f"_t{i}.png")
            SC.shot(p, tuple(c + Vector((-9.5, -15, 4.2))), tuple(c + Vector((0, 0, 3.6))), 30, (TW, TH))
            im = bpy.data.images.load(p)
            a = np.empty(TW * TH * 4, dtype=np.float32); im.pixels.foreach_get(a)
            tiles.append(a.reshape(TH, TW, 4)); bpy.data.images.remove(im); os.remove(p)
        top = np.concatenate(tiles[:4], axis=1); bot = np.concatenate(tiles[4:], axis=1)
        sheet = np.concatenate([bot, top], axis=0)          # pixel rows run bottom-up
        img = bpy.data.images.new(name + "_sheet", TW * 4, TH * 2, alpha=False)
        img.pixels.foreach_set(sheet.ravel()); img.filepath_raw = os.path.join(SHEETS, f"{name}.png"); img.file_format = "PNG"; img.save()
        print("SHEET", name, flush=True)
print("STAGE3_OK")
