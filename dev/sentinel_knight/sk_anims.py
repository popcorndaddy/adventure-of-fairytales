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
# The guardian at rest: the greatsword stands planted point-down in front of him, BOTH fists closed round the handle
# (right at the guard, left above it), elbows out, square stance. He breathes, his weight settles from foot to foot,
# the grip tightens and eases, and once a loop he rolls the blade a few degrees in his hands. Ready, never relaxed.
@action
def idle():
    N = 100
    TIP = (-1.5, -27.0, -1.5)                         # the point bites into the stone between his feet

    def fn(r, f):
        br = wave(f, N, (1.0, 2, 0.0), (0.35, 3, 0.7), (0.2, 1, 1.4))          # slow, heavy breathing
        sway = wave(f, N, (1.0, 1, 0.0), (0.25, 3, 0.4))                         # weight settles side to side
        roll = bump(f, 62, 10)                                                    # rolls the blade in his hands
        squeeze = 0.06 * wave(f, N, (1, 2, 0.6)) + 0.08 * roll                   # the grip tightens and eases
        G = (-1.5 + 0.6 * sway, -10.0 - 0.3 * br, 51.0 + 0.6 * br)
        d = (Vector(TIP) - Vector(G)).normalized()
        flat = Vector((math.cos(math.radians(6 * roll)), math.sin(math.radians(6 * roll)), 0.0))
        hs, gs = heartbeat(f / 20.0, 36, 0.8)
        K.pose(r, merged(
            body=(0.9 * sway, 0.4, -1.2 + 0.35 * br), hips=(5.0, -1.4 * sway, 1.2 * sway),
            spine=(1.5 - 0.6 * br, 0.4 * sway, 0.0), chest=(2.5 - 1.6 * br, 0.3 * sway, 0.0),
            head=(0.0, 9.0, 0.0), shrug_R=0.8 + 1.4 * br, shrug_L=0.8 + 1.4 * br,
            foot_R=((-8.5, 1.0), 0, -12, 0), foot_L=((8.5, -1.0), 0, 12, 0),
            sword=dict(grip=G, dir=tuple(d), flat=tuple(flat), two=True,
                       elbow_R=(-0.85, 0.25, -0.45), elbow_L=(0.85, 0.25, -0.45)),
            curl_R=1.0 + squeeze, curl_L=1.0 + squeeze, thumb_R=0.9, thumb_L=0.9,
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
