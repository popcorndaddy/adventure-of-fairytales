"""Stage 10 - the Gatekeeper's GRAVITY WELL ability clip (150 frames @ 30 fps = 100 ticks), added to gatekeeper_stage3.blend.

Beats (frame @30fps / game tick):
   0-24  /  0-16  gather: he sinks, all four arms draw in to the chest, the blade comes up point-down
  24     /  16    plunge: the sword is driven into the floor as an anchor (the well opens, pull starts)
  30-102 / 20-68  channel: the three free hands claw and stir the air in slow overlapping circles, the torso
                  winds with them; the pull grows
 102-114 / 68-76  compress: every free arm crushes in toward the chest, he crouches lower, the fire flares
 114     / 76     BURST: everything flings outward, chest thrown back, head up
 114-150 / 76-100 shudder, then recover to the stance
Usage: blender -b --python gk_10_gravity_well.py -- <gatekeeper-art folder>"""
import bpy, sys, os, math, copy, json
sys.path.insert(0, os.path.dirname(__file__))
import gk_lib as L
import gk_pose as GP

ART = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.open_mainfile(filepath=os.path.join(ART, "gatekeeper_stage3.blend"))
scene = bpy.context.scene
scene.render.fps = 30
rig = bpy.data.objects["Gatekeeper_Rig"]
rig.animation_data_create()
P = GP.P
NAME = "Gatekeeper_Gravity_Well"


def mir(a):
    return GP.mirror_arm(a)


def xarm(spec_R, spec_L=None):
    return {"extra_R": spec_R, "extra_L": spec_L if spec_L is not None else mir(spec_R)}


def chains(sw, fb=0.0):
    return {"chain_chest": (fb, sw * 0.6, 0), "chain_belt": (fb * 1.2, sw, 0),
            "chain_shoulder_L": (fb, sw, 0), "chain_shoulder_R": (fb, sw, 0),
            "chain_shoulder_back_L": (-fb * 0.6, sw * 0.8, 0), "chain_shoulder_back_R": (-fb * 0.6, sw * 0.8, 0)}


def lerp3(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


GATHER = {"upper": (-0.7, -0.6, -0.3), "fore": (-0.25, -0.75, -0.6), "curl": 110, "thumb": 80}
SPREAD = {"upper": (-0.8, 0.05, 0.6), "fore": (-0.5, 0.0, 0.87), "curl": 0, "thumb": 0}
# the anchor: blade driven point-first into the floor in front of him, both main-arm wrists stacked on the grip
ANCHOR_R = {"upper": (-0.3, -0.9, -0.3), "fore": (0.12, -0.97, -0.2), "hand": (0.1, -0.3, -0.95), "curl": 110, "thumb": 80}
ANCHOR_W = {"dir": (0.0, -0.1, -0.99), "normal": (0, -1, 0), "ground": None}
RAISED_R = {"upper": (-0.45, -0.55, -0.1), "fore": (0.2, -0.6, 0.77), "hand": (0.1, -0.2, 0.97), "curl": 110, "thumb": 80}
RAISED_W = {"dir": (0.0, -0.15, -0.99), "normal": (0, -1, 0), "ground": None}


def stir(f, phase, amp=1.0):
    """A free hand clawing in a slow circle in front of him; (dx, dz) offsets and a grasp (curl) that tightens on the pull-in."""
    ph = 2 * math.pi * (f - 30) / 36.0 + phase
    return math.cos(ph) * amp, math.sin(ph) * amp, 45 + 35 * (0.5 + 0.5 * math.sin(ph - 0.9))


def channel_pose(f, k_in=0.0):
    """k_in: 0 = arms out stirring, 1 = crushed in to the chest (compress beat)."""
    s = math.sin(2 * math.pi * (f - 30) / 72.0)                   # slow torso wind
    b = math.sin(2 * math.pi * (f - 30) / 36.0)
    dxr, dzr, cr = stir(f, 0.0)
    dxl, dzl, cl = stir(f, math.pi * 0.66)
    dxm, dzm, cm = stir(f, math.pi * 1.33)
    ex_r = {"upper": lerp3((-0.78 + 0.10 * dxr, -0.5, 0.30 + 0.16 * dzr), GATHER["upper"], k_in),
            "fore": lerp3((-0.35 + 0.22 * dxr, -0.85, 0.15 + 0.3 * dzr), GATHER["fore"], k_in),
            "hand": lerp3((0.1 + 0.3 * dxr, -0.9, 0.1 + 0.3 * dzr), (0.3, -0.6, -0.3), k_in),
            "curl": cr + (110 - cr) * k_in, "thumb": 30 + 40 * k_in}
    ex_l = mir({"upper": lerp3((-0.78 - 0.10 * dxl, -0.5, 0.30 + 0.16 * dzl), GATHER["upper"], k_in),
                "fore": lerp3((-0.35 - 0.22 * dxl, -0.85, 0.15 + 0.3 * dzl), GATHER["fore"], k_in),
                "hand": lerp3((0.1 - 0.3 * dxl, -0.9, 0.1 + 0.3 * dzl), (0.3, -0.6, -0.3), k_in),
                "curl": cl + (110 - cl) * k_in, "thumb": 30 + 40 * k_in})
    # main left claw reaches out at the vortex and drags it in, hand over hand
    arm_l = {"upper": lerp3((0.42 + 0.08 * dxm, -0.85, -0.12 + 0.12 * dzm), (0.55, -0.55, -0.63), k_in),
             "fore": lerp3((0.15 + 0.2 * dxm, -0.95, 0.1 + 0.25 * dzm), (-0.2, -0.75, -0.6), k_in),
             "hand": lerp3((0.05 + 0.25 * dxm, -0.95, 0.15 + 0.25 * dzm), (-0.3, -0.6, -0.4), k_in),
             "curl": cm + (130 - cm) * k_in, "thumb": 40 + 40 * k_in}
    hz = -7 - 1.2 * b - 4 * k_in
    return P(hips={"loc": (0, 0, hz), "rot": (0, 0, 4 * s)}, spine=(8 + 4 * k_in, 0, 3 * s), chest=(6 - 3 * b + 10 * k_in, 0, 7 * s),
             neck=(0, 0, -3 * s), head=(-8 + 2 * b + 14 * k_in, 0, -6 * s),
             arm_R=ANCHOR_R, weapon=ANCHOR_W, arm_L=arm_l, extra_R=ex_r, extra_L=ex_l,
             robe_L=(-6 - 3 * b, 0, 0), robe_R=(-6 + 3 * b, 0, 0), robe_F=(4 * b, 0, 0), robe_B=(-5, 0, 0),
             fire={"L": 1.5 + 0.35 * math.sin(f * 0.37) + 0.8 * k_in, "R": 1.5 + 0.35 * math.sin(f * 0.41 + 1) + 0.8 * k_in},
             chains=chains(6 * s, -8 - 4 * b))


ROAR = dict(hips={"loc": (0, 0, 0.5)}, spine=(-8, 0, 0), chest=(-20, 0, 0), head=(-28, 0, 0), **xarm(SPREAD),
            arm_L={"upper": (0.88, -0.3, -0.37), "fore": (0.7, -0.4, 0.6), "curl": 0, "thumb": 0},
            arm_R=ANCHOR_R, weapon=ANCHOR_W, fire={"L": 2.6, "R": 2.6},
            robe_L=(-14, 0, 0), robe_R=(-14, 0, 0), robe_F=(-12, 0, 0), robe_B=(-16, 0, 0))

keys = [
    (0, P()),
    (10, P(hips={"loc": (0, 1, -5)}, spine=(8, 0, 0), chest=(16, 0, 0), head=(14, 0, 0), **xarm(GATHER),
           arm_L={"upper": (0.55, -0.55, -0.63), "fore": (-0.1, -0.8, -0.6), "curl": 130}, arm_R=RAISED_R, weapon=RAISED_W,
           fire={"L": 0.7, "R": 0.7}, chains=chains(0, 8))),
    (18, P(hips={"loc": (0, 1, -3)}, spine=(2, 0, 0), chest=(-6, 0, 0), head=(-4, 0, 0), **xarm(GATHER),
           arm_L={"upper": (0.55, -0.55, -0.63), "fore": (-0.1, -0.8, -0.6), "curl": 130}, arm_R=RAISED_R, weapon=RAISED_W,
           fire={"L": 0.9, "R": 0.9}, chains=chains(0, -6))),
    (24, P(hips={"loc": (0, -1, -10)}, spine=(12, 0, 0), chest=(18, 0, 0), head=(16, 0, 0), **xarm(GATHER),
           arm_L={"upper": (0.4, -0.7, -0.6), "fore": (0.0, -0.8, -0.6), "curl": 120}, arm_R=ANCHOR_R, weapon=ANCHOR_W,
           fire={"L": 1.8, "R": 1.8}, chains=chains(0, 14))),
]
for f in range(30, 103, 6):
    keys.append((f, channel_pose(f)))
for f, k in ((106, 0.45), (110, 0.85), (112, 1.0)):
    keys.append((f, channel_pose(f, k)))
keys.append((114, P(**ROAR, chains=chains(0, -16))))
for i, f in enumerate(range(117, 130, 3)):
    j = 1 if i % 2 else -1
    q = copy.deepcopy(ROAR)
    q["chest"] = (-18 + 2 * j, 0, 2.5 * j); q["head"] = (-26 + 3 * j, 0, -4 * j)
    q["fire"] = {"L": 2.2 + 0.3 * j, "R": 2.2 - 0.3 * j}
    keys.append((f, P(**q, chains=chains(5 * j, -8))))
keys += [(136, P(hips={"loc": (0, 0, -3)}, chest=(4, 0, 0), head=(6, 0, 0), arm_R=ANCHOR_R, weapon=ANCHOR_W, fire={"L": 1.3, "R": 1.3})),
         (142, P(hips={"loc": (0, 0, -2)}, chest=(2, 0, 0), arm_R={"upper": (-0.55, -0.4, -0.73), "fore": (-0.3, -0.85, -0.4)},
                 weapon={"dir": (-0.3, -0.35, -0.88), "normal": (0, -1, 0), "ground": "clamp"})),
         (150, P())]



def blend_pose(a, b, t):
    """Smooth in-between of two pose dicts (numbers / tuples lerp, nested dicts recurse, others switch at the middle)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return {k: blend_pose(a.get(k, b.get(k)), b.get(k, a.get(k)), t) for k in set(a) | set(b)}
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + (b - a) * t
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)) and len(a) == len(b):
        return tuple(x + (y - x) * t for x, y in zip(a, b))
    return a if t < 0.5 else b


def densify(keys, f_from, f_to, step=2):
    """Insert blended poses every `step` frames between existing keys in [f_from, f_to] so the floor solver sees each one."""
    out = []
    for (f0, p0), (f1, p1) in zip(keys, keys[1:]):
        out.append((f0, p0))
        if f0 >= f_from and f1 <= f_to:
            for f in range(f0 + step, f1, step):
                t = (f - f0) / (f1 - f0); t = t * t * (3 - 2 * t)
                q = blend_pose(p0, p1, t)
                if p0.get("weapon") and p1.get("weapon"):
                    q["weapon"]["ground"] = "clamp"
                out.append((f, q))
    out.append(keys[-1])
    return out


keys = densify(keys, 0, 24)
keys = densify(keys, 136, 150)

# ---------------------------------------------------------------- bake (same procedure as gk_03 make())
old = bpy.data.actions.get(NAME)
if old:
    bpy.data.actions.remove(old)
act = bpy.data.actions.new(NAME); act.use_fake_user = True
rig.animation_data.action = act
GP.reset_continuity()
for f, pose in keys:
    GP.apply_pose(rig, pose)
    GP.key_all(rig, f)
keyed = {k[0] for k in keys}
fixes = 0
for f in range(0, 151):
    if f in keyed:
        continue
    scene.frame_set(f)
    if GP.fix_inbetween(rig):
        GP.reset_continuity(); GP.key_all(rig, f); fixes += 1
act.frame_range = (0, 150)
try:
    act.use_frame_range = True; act.use_cyclic = False
except Exception:
    pass
clips = {k: list(v) for k, v in scene["gk_clips"].items()}
clips[NAME] = [0, 150, 0]
scene["gk_clips"] = clips
ev = json.loads(scene["gk_events"]) if "gk_events" in scene else {}
ev[NAME] = {"well_opens": [24], "burst": [114], "camera_shake": [114, 124]}
scene["gk_events"] = json.dumps(ev)

# ---------------------------------------------------------------- checks: floor, sword tip in the floor, extremes
lows, tips = [], []
for f in range(0, 151):
    scene.frame_set(f)
    lows.append(GP.body_min_z(rig)); tips.append(GP.sword_tip_z(rig))
    if f in (30, 66, 114):
        print(f"GW f{f} hand_R z {(rig.matrix_world @ rig.pose.bones['hand_R'].head).z:.2f}  sword tip z {tips[-1]:.2f}")
print(f"GW keys {len(keys)} in-between fixes {fixes}")
print("GW tip below -0.5 at", [(f, round(t, 1)) for f, t in enumerate(tips) if t < -0.5])
print(f"GW body lowest {min(lows):.2f} m (frame {lows.index(min(lows))}), sword tip z during anchor 24-136: "
      f"{min(tips[24:137]):.2f}..{max(tips[24:137]):.2f}")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART, "gatekeeper_stage3.blend"))
print("GRAVITY_WELL_OK")
