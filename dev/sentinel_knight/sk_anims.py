"""All twelve Withered Sentinel actions, authored on the knight rig with sk_pose.
Run: blender -b sentinel_knight.blend --python sk_anims.py -- [action,action,...]   (saves sentinel_knight_anim.blend)
Each action is a function returning (frames, pose_fn, loop) and is baked per frame.
Timings are in ticks (20 fps); the entity script (withered_sentinel.js) uses the same tick numbers."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector, Matrix
import sk_pose as K
from sk_pose import track, wave, bump, smooth, ease_in, ease_out, dir_az_el, heartbeat, merged
from mathutils import Quaternion

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = set(args[0].split(",")) if args and args[0] else None
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sentinel_knight_anim.blend")
if os.path.exists(OUT):
    bpy.ops.wm.open_mainfile(filepath=OUT)          # keep previously baked actions
r = K.Rig()
SL = 56.0                                          # sword length (grip -> tip), px


def planted_sword(grip, tip, flat):
    d = (Vector(tip) - Vector(grip)).normalized()
    return dict(grip=grip, dir=tuple(d), flat=flat, two=False)


ACTIONS = {}


def action(fn):
    ACTIONS[fn.__name__] = fn
    return fn


# ====================================================================== IDLE (5 s loop)
# A commanding rest: the blade's point is planted in the stone, the right fist loose on the grip. His weight rolls slowly
# from foot to foot, the planted sword rocks with it, the left arm hangs relaxed and swings a little behind the body.
# Midway he lifts the left hand onto the pommel over the right (a knight's rest), breathes there, and lets it fall again.
@action
def idle():
    N = 100
    TIP = (-19.0, -36.0, 0.8)                        # the sword point stays planted on the stone

    def fn(r, f):
        br = wave(f, N, (1.0, 2, 0.0), (0.35, 3, 0.7), (0.2, 1, 1.4))          # uneven breathing
        sway = wave(f, N, (1.0, 1, 0.0), (0.25, 3, 0.4))                         # slow weight shift (+ = onto his left foot)
        lag = wave(f, N, (1.0, 1, -0.9), (0.25, 3, -0.5))                        # the free arm trails the body
        rest = smooth((f - 26) / 14) * (1 - smooth((f - 64) / 14))               # left hand up on the pommel
        G = (-13.0 + 7.0 * rest + 0.9 * sway, -20.0 + 6.0 * rest, 50.0 + 0.6 * br)
        hs, gs = heartbeat(f / 20.0, 36, 0.8)
        hang = dict(hand=(15.0 - 0.8 * lag, -6.0 - 1.6 * lag + 0.6 * br, 36.5 + 0.5 * br), point=(0.15, -0.3 - 0.12 * lag, -0.94),
                    palm=(-0.95, 0.15, 0.0), elbow=(0.45, 0.85, -0.2))
        top = dict(hand=(G[0] + 1.5, G[1] - 2.0, G[2] + 4.2 + 0.3 * br), point=(-0.75, -0.55, -0.35), palm=(-0.15, 0.1, -0.98),
                   elbow=(0.85, 0.3, -0.45))
        K.pose(r, merged(
            body=(1.1 * sway, 0.3 - 0.4 * rest, -0.8 + 0.35 * br - 0.3 * rest), hips=(4.0 + 1.5 * rest, -1.6 * sway, -6.0 + 1.5 * sway + 3 * rest),
            spine=(1.0 - 0.6 * br + 1.5 * rest, 0.5 * sway, 1.5 - 1.5 * rest), chest=(2.0 - 1.6 * br + 1.5 * rest, 0.4 * sway, 2.0 - 1.5 * rest),
            head=(0.0, 7.0, 0.0), shrug_R=0.8 + 1.4 * br, shrug_L=1.6 * br + 2.0 * rest,
            foot_R=((-7.0, 1.5), 0, -14, 0), foot_L=((7.5, -2.0), 0, 9, 0),
            sword=dict(planted_sword(G, TIP, (0.95, -0.3, 0.0)), elbow_R=(-0.85, 0.55, -0.2)),
            arm_L=lerpP(hang, top, rest),
            curl_R=0.85 + 0.1 * rest, curl_L=0.3 + 0.06 * wave(f, N, (1, 2, 0.5)) + 0.45 * rest, spread_L=0.25 * (1 - rest), thumb_L=0.35 + 0.35 * rest,
            wobble_L=(0.06 * wave(f, N, (1, 3, 0)), 0.05 * wave(f, N, (1, 4, 1)), 0.07 * wave(f, N, (1, 5, 2))),
            heart=(hs, gs)))
    return N, fn, "true"


# ====================================================================== IDLE_COMBAT (3 s loop)
COMBAT = dict(body=(0.0, 1.0, -4.0), hips=(9.0, 0.0, -14.0), spine=(2.0, 0.0, 4.0), chest=(3.0, 0.0, 6.0),
              foot_R=((-8.0, 5.0), 0, -28, 0), foot_L=((7.0, -7.0), 0, 12, 0),
              grip=(-3.0, -13.0, 41.0), az=6.0, el=28.0)


def combat_base(f=0, N=60, intensity=1.0):
    """The shared combat guard (frame 0 of idle_combat and the start/end of every attack)."""
    br = wave(f, N, (1.0, 2, 0.0), (0.3, 4, 0.0))
    rock = wave(f, N, (1.0, 1, 0.0))
    weave_a = wave(f, N, (1.0, 1, 0.0), (0.4, 3, 0.0)) * intensity
    weave_e = wave(f, N, (1.0, 2, 0.0), (0.3, 1, 0.0)) * intensity
    bx, by, bz = COMBAT["body"]
    hp, hr, hy = COMBAT["hips"]
    g = COMBAT["grip"]
    d = dir_az_el(COMBAT["az"] + 3.5 * weave_a, COMBAT["el"] + 3.0 * weave_e)
    return dict(
        body=(bx + 0.7 * rock, by, bz - 0.6 * br), hips=(hp + 0.8 * br, -1.0 * rock, hy + 2.0 * rock),
        spine=(COMBAT["spine"][0] - 0.5 * br, 0, COMBAT["spine"][2]), chest=(COMBAT["chest"][0] - 1.6 * br, 0, COMBAT["chest"][2] + 1.0 * rock),
        head=(-hy - COMBAT["spine"][2] - COMBAT["chest"][2] + 22 - 2.0 * rock, 4.0 + 0.8 * br, 0.0),
        shrug_R=1.5 * br, shrug_L=1.5 * br,
        foot_R=COMBAT["foot_R"], foot_L=COMBAT["foot_L"],
        sword=dict(grip=(g[0] + 0.5 * rock, g[1], g[2] + 0.5 * br), dir=tuple(d), flat=(1.0, 0.0, 0.2), two=True,
                   elbow_R=(-0.8, 0.4, -0.5), elbow_L=(0.7, 0.3, -0.6)),
        curl_R=1.0 + 0.06 * wave(f, N, (1, 3, 0)), curl_L=1.0 + 0.06 * wave(f, N, (1, 3, 1.5)), thumb_L=0.9)


@action
def idle_combat():
    N = 60

    def fn(r, f):
        P = combat_base(f, N)
        # the front foot re-plants once (a small weight adjustment), seamless
        shuffle = bump(f, 40, 4.0)
        P["foot_L"] = ((7.0, -7.0 - 1.2 * shuffle), 1.2 * shuffle, 12, 0)
        hs, gs = heartbeat(f / 20.0, 100, 1.0)
        K.pose(r, merged(**P, heart=(hs, gs)))
    return N, fn, "true"


exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sk_actions_more.py")).read())


# ====================================================================== run
for name, fn in ACTIONS.items():
    if ONLY and name not in ONLY:
        continue
    n, pose_fn, loop = fn()
    K.bake(r, name, n, pose_fn, loop)
    print("BAKED", name, n, "frames", flush=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
if not ONLY:
    import json
    ev_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "overrides", "kubejs", "startup_scripts", "bosses", "withered_sentinel_events.js")
    with open(ev_path, "w") as fh:
        fh.write("// GENERATED by dev/sentinel_knight/sk_anims.py from the animations: timing markers (ticks) for withered_sentinel.js\n")
        fh.write("// telegraph = the readable wind-up, impact = damage tick, [a, b] = windows. Do not edit by hand: change the animation.\n")
        for line in json.dumps(EVENTS, indent=2).splitlines():
            fh.write("//   " + line + "\n")
        # stored as a JSON string: nested objects in the KubeJS global map come back as fragile Java objects
        fh.write("global.WS_EVENTS_JSON = " + json.dumps(json.dumps(EVENTS)) + "\n")
    print("EVENTS_OK", ev_path)
print("ANIMS_DONE", OUT)
