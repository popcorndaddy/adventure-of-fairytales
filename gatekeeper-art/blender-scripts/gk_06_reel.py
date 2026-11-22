"""Stage 6 - combat reel: every Gatekeeper clip in sequence in the portal arena, labelled, with VFX and sound on the
animation-event frames (shockwaves, dust, sparks, whooshes, roars)."""
import bpy, sys, os, math, random, json
sys.path.insert(0, os.path.dirname(__file__))
from mathutils import Vector, Matrix
import gk_arena as AR

OUT = sys.argv[sys.argv.index("--") + 1]
PREVIEW = "--preview" in sys.argv
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "gatekeeper_stage3.blend"))
scene = bpy.context.scene
for c in list(bpy.data.collections):
    if c.name == "Preview_Arena":
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(c)
rig = bpy.data.objects["Gatekeeper_Rig"]
EV = json.loads(scene["gk_events"])
CL = {k: list(v) for k, v in scene["gk_clips"].items()}
SND = os.path.join(OUT, "sounds")
r = random.Random(9)

ORDER = [("Gatekeeper_Awakening", 1), ("Gatekeeper_Entrance", 1), ("Gatekeeper_Idle", 1), ("Gatekeeper_Walking", 2),
         ("Gatekeeper_Heavy_Walk", 2), ("Gatekeeper_Sword_Drag", 2), ("Gatekeeper_Overhead_Attack", 1), ("Gatekeeper_Horizontal_Sweep", 1),
         ("Gatekeeper_Multi_Arm_Attack", 1), ("Gatekeeper_Block", 1), ("Gatekeeper_Stagger", 1), ("Gatekeeper_Rage", 1), ("Gatekeeper_Death", 1)]
ROOT_STEP = {"Gatekeeper_Walking": 36 / 16, "Gatekeeper_Heavy_Walk": 44 / 16, "Gatekeeper_Sword_Drag": 32 / 16, "Gatekeeper_Entrance": 32 / 16}
GAP = 12
segs, f = [], 0
for name, rep in ORDER:
    ln = CL[name][1] - CL[name][0]
    for k in range(rep):
        segs.append((name, f, k))
        f += ln
    f += GAP
END = f
col, lights, portal = AR.build(length=END)

# ---------------------------------------------------------------- NLA: one strip per segment; walking cycles carry the boss forward
rig.animation_data.action = None
tr = rig.animation_data.nla_tracks.new(); tr.name = "Reel"
rig.location = (0, 0, 0)
cur_off = 0.0
for i, (name, f0, k) in enumerate(segs):
    s = tr.strips.new(f"{name}_{i}", f0, bpy.data.actions[name])
    try:
        s.action_slot = s.action.slots[0]
    except Exception:
        pass
    s.extrapolation = "HOLD_FORWARD" if i else "HOLD"
    rig.location = (0, cur_off, 0); rig.keyframe_insert("location", frame=f0)
    if name in ROOT_STEP:
        cur_off -= ROOT_STEP[name]
    if k == 0 and (i + 1 >= len(segs) or segs[i + 1][0] != name):
        cur_off = 0.0 if name not in ROOT_STEP else cur_off
    nxt = segs[i + 1][0] if i + 1 < len(segs) else None
    if nxt != name:
        cur_off = 0.0           # each new clip starts back at the arena mark
ad = rig.animation_data.action
fcs = ad.fcurves if hasattr(ad, "fcurves") else [fc for l_ in ad.layers for st in l_.strips for b in st.channelbags for fc in b.fcurves]
for fc in fcs:
    for kp in fc.keyframe_points:
        kp.interpolation = "CONSTANT"

# eyes and runes fully lit for the reel
eye = bpy.data.materials["GK_EyeGlow"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
eye.default_value = 16.0

# ---------------------------------------------------------------- VFX
spark_m = AR._mat_emit("FX_Spark", (1.0, 0.62, 0.95), 18.0)
dust_m = bpy.data.materials.new("FX_Dust"); dust_m.use_nodes = True
dust_m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.12, 0.09, 0.15, 1)
wave_m = AR._mat_emit("FX_Shockwave", (0.75, 0.35, 1.0), 6.0)
NFX = [0]


def wpos(bone, local=(0, 0, 0), f=None):
    if f is not None:
        scene.frame_set(f)
    pb = rig.pose.bones[bone]
    return rig.matrix_world @ (pb.matrix @ Vector(local))


def ring(f, at, radius, thick=0.1, n=40):
    B = AR.Boxes()
    for i in range(n):
        a = 2 * math.pi * i / n
        Mt = Matrix.Translation((math.cos(a), math.sin(a), 0.06)) @ Matrix.Rotation(a, 4, "Z")
        B.box(-0.035, 0.035, -thick, thick, -0.05, 0.05, wave_m, M=Mt)
    NFX[0] += 1
    w = B.make(f"FX_Ring{NFX[0]}", col)
    AR._key(w, f - 1, loc=tuple(at), sc=0.0); AR._key(w, f, loc=tuple(at), sc=0.3)
    AR._key(w, f + 9, loc=tuple(at), sc=radius); w.scale = (radius * 1.35,) * 3; w.keyframe_insert("scale", frame=f + 16)
    w.scale = (0, 0, 0); w.keyframe_insert("scale", frame=f + 17)


def dust(f, at, n=18, sp=3.0, up=2.5):
    for i in range(n):
        NFX[0] += 1
        o = AR._cube_obj(f"FX_Dust{NFX[0]}", r.uniform(0.05, 0.18), dust_m if i % 3 else bpy.data.materials["GK_CorruptedStone"], col)
        a = r.uniform(0, 2 * math.pi); s_ = r.uniform(0.5, 1) * sp; u = r.uniform(0.4, 1) * up
        AR._key(o, f - 1, loc=tuple(at), sc=0.0)
        for k in range(0, 22, 3):
            t = k / 30.0
            AR._key(o, f + k, loc=(at.x + math.cos(a) * s_ * t, at.y + math.sin(a) * s_ * t, max(0.05, u * t - 4.9 * t * t)), sc=1.0 if k < 21 else 0.0)


def sparks(f0, f1, per=3):
    for f in range(f0, f1, 2):
        tip = wpos("weapon", (0, 87 / 16, 0), f)
        if tip.z > 0.3:
            continue
        for k in range(per):
            NFX[0] += 1
            o = AR._cube_obj(f"FX_Spark{NFX[0]}", r.uniform(0.02, 0.05), spark_m, col)
            v = Vector((r.uniform(-1.5, 1.5), r.uniform(-1.5, 1.5), r.uniform(1.0, 3.0)))
            AR._key(o, f - 1, loc=tuple(tip), sc=0.0)
            for i in range(0, 13, 2):
                t = i / 30.0
                p = tip + v * t + Vector((0, 0, -4.9 * t * t)); p.z = max(p.z, 0.02)
                AR._key(o, f + i, loc=tuple(p), sc=1.0 if i < 12 else 0.0)


se = scene.sequence_editor_create()
strips = se.strips if hasattr(se, "strips") else se.sequences
CH = [3]


def snd(name, f, vol=1.0):
    CH[0] = 3 + (CH[0] - 2) % 10
    s = strips.new_sound(f"{name}{f}", os.path.join(SND, name + ".wav"), CH[0], max(1, int(f))); s.volume = vol


snd("portal_hum", 1, 0.6)
for k in range(1, END, 300):
    snd("guardian_ambient", k, 0.35)
for name, f0, k in segs:
    e = EV.get(name, {})
    for key, frames in e.items():
        for fr in frames:
            F = f0 + fr
            if key in ("impact", "ground_crack") and key == "impact":
                at = wpos("weapon", (0, 87 / 16, 0), F); at.z = 0.02
                ring(F, at, 6.0); dust(F, at, 28, 4, 3.5); snd("impact_boom", F)
            elif key == "shockwave":
                at = wpos("root", (0, 0, 0), F); at.z = 0.02
                ring(F, at, 9.0, thick=0.16); snd("whoosh", F - 6)
            elif key in ("heavy_step", "heavy_footstep", "footstep", "stumble_step", "knees_hit_ground", "body_hits_ground"):
                S = "L" if (fr // 10) % 2 == 0 else "R"
                at = wpos(f"foot_{S}", (0, 0, 0), F); at.z = 0.02
                big = key in ("heavy_step", "heavy_footstep", "body_hits_ground")
                dust(F, at, 16 if big else 9, 2.5, 1.6)
                if big:
                    ring(F, at, 3.0)
                snd("heavy_step", F, 1.0 if big else 0.6)
            elif key == "sword_drag_sparks":
                sparks(F, F + 24 if name != "Gatekeeper_Awakening" else F + 40)
                snd("stone_drag", F, 0.8)
            elif key in ("claw_R", "claw_L", "punch", "swing", "sword_sweep", "claws_both", "windup"):
                snd("whoosh", F - 4, 0.9)
            elif key == "roar":
                snd("guardian_shriek", F)
            elif key in ("arm_unfold", "fire_ignite"):
                snd("guardian_pulse", F, 0.8)
            elif key == "eyes_open":
                snd("eyes_open", F - 48)
            elif key in ("hit", "block_impact"):
                snd("impact_boom", F, 0.5)

# ---------------------------------------------------------------- camera + labels
cam = bpy.data.objects.new("Reel_Cam", bpy.data.cameras.new("Reel_Cam")); col.objects.link(cam); scene.camera = cam
tgt = bpy.data.objects.new("Reel_Target", None); col.objects.link(tgt)
tc = cam.constraints.new("TRACK_TO"); tc.target = tgt; tc.track_axis = "TRACK_NEGATIVE_Z"; tc.up_axis = "UP_Y"
ANG = {"Gatekeeper_Horizontal_Sweep": (-6, -15, 3.2), "Gatekeeper_Multi_Arm_Attack": (8, -15, 4.0), "Gatekeeper_Overhead_Attack": (-11, -12, 2.6),
       "Gatekeeper_Death": (-13, -10, 3.0), "Gatekeeper_Rage": (3, -14, 1.4), "Gatekeeper_Block": (5, -13, 3.0)}
txt_m = AR._mat_emit("FX_Label", (0.9, 0.8, 1.0), 3.0)
labels = []
seen = set()
for name, f0, k in segs:
    if name in seen:
        continue
    seen.add(name)
    walk = name in ROOT_STEP
    off = Vector(ANG.get(name, (-9, -16, 3.0)))
    if walk:
        off = Vector((-10, -18, 3.2))
    cam.location = off; cam.keyframe_insert("location", frame=f0)
    tgt.location = (0, -2.5 if walk else 0, 3.8); tgt.keyframe_insert("location", frame=f0)
    cam.data.lens = 30; cam.data.keyframe_insert("lens", frame=f0)
    td = bpy.data.curves.new(f"Lbl_{name}", "FONT"); td.body = name.replace("Gatekeeper_", "").replace("_", " ").upper(); td.size = 0.045
    t = bpy.data.objects.new(f"Lbl_{name}", td); col.objects.link(t); t.data.materials.append(txt_m)
    t.parent = cam; t.location = (-0.33, -0.165, -1.0)
    labels.append((t, f0))
ad = cam.animation_data.action
fcs = ad.fcurves if hasattr(ad, "fcurves") else [fc for l_ in ad.layers for st in l_.strips for b in st.channelbags for fc in b.fcurves]
for fc in fcs:
    for kp in fc.keyframe_points:
        kp.interpolation = "CONSTANT"
for i, (t, f0) in enumerate(labels):
    f1 = labels[i + 1][1] if i + 1 < len(labels) else END + 1
    for fr, hide in ((0, True), (f0, False), (f1, True)):
        t.hide_render = hide; t.keyframe_insert("hide_render", frame=max(0, fr))
        t.hide_viewport = hide; t.keyframe_insert("hide_viewport", frame=max(0, fr))

for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        scene.render.engine = eng; break
    except TypeError:
        pass
try:
    scene.view_settings.view_transform = "AgX"; scene.view_settings.look = "AgX - Punchy"
except Exception:
    scene.view_settings.view_transform = "Filmic"
try:
    scene.eevee.taa_render_samples = 16; scene.eevee.volumetric_end = 60; scene.eevee.volumetric_tile_size = "8"
except Exception:
    pass
ng = bpy.data.node_groups.get("GK_Bloom")
if ng:
    try:
        scene.compositing_node_group = ng
    except Exception:
        pass
scene.render.fps = 30
scene.frame_start, scene.frame_end = 0, END
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Gatekeeper_CombatReel.blend"))
print("REEL_FRAMES", END)
if PREVIEW:
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    picks = {"Gatekeeper_Overhead_Attack": 36, "Gatekeeper_Horizontal_Sweep": 26, "Gatekeeper_Multi_Arm_Attack": 30, "Gatekeeper_Heavy_Walk": 2,
             "Gatekeeper_Block": 20, "Gatekeeper_Rage": 40, "Gatekeeper_Death": 125, "Gatekeeper_Sword_Drag": 30}
    done = set()
    for name, f0, k in segs:
        if name in picks and name not in done:
            done.add(name)
            scene.frame_set(f0 + picks[name])
            scene.render.filepath = os.path.join(OUT, "reel_preview", f"{name}.png")
            bpy.ops.render.render(write_still=True)
    print("PREVIEW_OK")
else:
    ims = scene.render.image_settings
    if hasattr(ims, "media_type"):
        ims.media_type = "VIDEO"
    ims.file_format = "FFMPEG"
    ff = scene.render.ffmpeg
    ff.format = "MPEG4"; ff.codec = "H264"; ff.constant_rate_factor = "HIGH"
    ff.audio_codec = "AAC"; ff.audio_bitrate = 192; ff.audio_channels = "STEREO"
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.filepath = os.path.join(OUT, "Gatekeeper_Combat_Reel.mp4")
    bpy.ops.render.render(animation=True)
    print("VIDEO_OK")
