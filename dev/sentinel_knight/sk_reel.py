"""Withered Sentinel (knight) showcase reel: every rebuilt animation in sequence (labelled), rendered to MP4 at 20 fps (= game ticks).
blender -b dev/withered_sentinel/withered_sentinel_reworked.blend --python tools/blender-geckolib/sentinel_reel.py -- out.mp4 [--stills]"""
import bpy, sys, os, math
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
OUT = os.path.abspath(args[0]); STILLS = "--stills" in args
scene = bpy.context.scene
for o in bpy.data.objects:
    if o.type == "MESH" and o.parent is None and not any(m.type == "ARMATURE" for m in o.modifiers):
        o.hide_render = True
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
PX = 1 / 16
ORDER = [("awaken", 1, "AWAKEN"), ("idle", 1, "IDLE"), ("idle_combat", 1, "COMBAT STANCE"), ("walk", 2, "WALK"),
         ("sweep", 1, "SWEEP"), ("push", 1, "PUSH"), ("stomp", 1, "STOMP"), ("dash", 1, "DASH"),
         ("summon_start", 1, "SUMMON"), ("summon_loop", 1, "SUMMON - channelling"), ("summon_end", 1, "SUMMON - release"), ("death", 1, "DEATH")]
WALK_V = 2 * 21.6 / 48 * PX                      # metres per frame (walk ground speed)
GAP = 6

# ---------------------------------------------------------------- NLA sequence + root motion for the walk
rig.animation_data_create(); rig.animation_data.action = None
for t in list(rig.animation_data.nla_tracks):
    rig.animation_data.nla_tracks.remove(t)
tr = rig.animation_data.nla_tracks.new(); tr.name = "Reel"
segs, f, y = [], 0, 0.0
for name, rep, label in ORDER:
    act = bpy.data.actions[name]; n = int(act.frame_range[1])
    for k in range(rep):
        s = tr.strips.new(f"{name}_{k}", f, act)
        try:
            s.action_slot = act.slots[0]
        except Exception:
            pass
        s.extrapolation = "HOLD_FORWARD"
        rig.location = (0, y, 0); rig.keyframe_insert("location", frame=f)
        if name == "walk":
            y -= WALK_V * n
            rig.location = (0, y, 0); rig.keyframe_insert("location", frame=f + n)
        segs.append((name, f, n, label if k == 0 else None))
        f += n
    rig.location = (0, y, 0); rig.keyframe_insert("location", frame=f)
    f += GAP
END = f
ad = rig.animation_data.action
fcs = ad.fcurves if hasattr(ad, "fcurves") else [fc for l_ in ad.layers for st in l_.strips for b in st.channelbags for fc in b.fcurves]
for fc in fcs:
    for kp in fc.keyframe_points:
        kp.interpolation = "LINEAR"

# ---------------------------------------------------------------- stage: dark stone floor, cold rim lights, soul-blue fill
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        scene.render.engine = eng; break
    except TypeError:
        pass
try:
    scene.view_settings.view_transform = "AgX"; scene.view_settings.look = "AgX - Punchy"
except Exception:
    scene.view_settings.view_transform = "Standard"
w = bpy.data.worlds.new("ReelWorld"); scene.world = w
try:
    w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.035, 0.05, 1)
except Exception:
    w.color = (0.03, 0.035, 0.05)
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, -3, 0))
fm = bpy.data.materials.new("ReelFloor"); fm.use_nodes = True
fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.11, 0.11, 0.12, 1)
fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.85
bpy.context.object.data.materials.append(fm)
for name, kind, e, loc, col in (("Key", "SUN", 2.6, (5, -7, 9), (1.0, 0.95, 0.9)), ("Rim", "SUN", 2.2, (-4, 8, 6), (0.45, 0.75, 1.0)),
                                ("Fill", "SUN", 0.6, (-8, -4, 3), (0.5, 0.6, 1.0))):
    L = bpy.data.lights.new(name, kind); L.energy = e; L.color = col
    o = bpy.data.objects.new(name, L); scene.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, 2)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

# ---------------------------------------------------------------- camera follows him; angle per clip
cam = bpy.data.objects.new("ReelCam", bpy.data.cameras.new("ReelCam")); scene.collection.objects.link(cam); scene.camera = cam
tgt = bpy.data.objects.new("ReelTarget", None); scene.collection.objects.link(tgt)
tc = cam.constraints.new("TRACK_TO"); tc.target = tgt; tc.track_axis = "TRACK_NEGATIVE_Z"; tc.up_axis = "UP_Y"
cam.data.lens = 32
ANG = {"walk": (-9, 7, 3.4), "howl": (5, -11, 3.4), "sweep": (4, -12, 4.0), "push": (11, -4, 3.4), "dash": (12, -3, 2.6),
       "death": (-7, -10, 2.6), "summon_start": (-8, -10, 3.0), "summon_loop": (-8, -10, 3.0), "summon_end": (-8, -10, 3.0)}
txt_m = bpy.data.materials.new("ReelLabel"); txt_m.use_nodes = True
b = txt_m.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.75, 0.9, 1.0, 1); b.inputs["Emission Color"].default_value = (0.75, 0.9, 1.0, 1)
b.inputs["Emission Strength"].default_value = 3.0
labels = []
for name, f0, n, label in segs:
    off = Vector(ANG.get(name, (9, -10, 3.2)))
    for fr in (f0, f0 + n):
        scene.frame_set(fr)
        base = Vector((0, rig.location.y, 0))
        tgt.location = base + Vector((0, -0.6, 2.4)); tgt.keyframe_insert("location", frame=fr)
        cam.location = base + off; cam.keyframe_insert("location", frame=fr)
    if label:
        td = bpy.data.curves.new(f"Lbl_{name}", "FONT"); td.body = label; td.size = 0.028
        t = bpy.data.objects.new(f"Lbl_{name}", td); scene.collection.objects.link(t); t.data.materials.append(txt_m)
        t.parent = cam; t.location = (-0.33, -0.175, -1.0)
        labels.append((t, f0))
cad = cam.animation_data.action
cfcs = cad.fcurves if hasattr(cad, "fcurves") else [fc for l_ in cad.layers for st in l_.strips for b_ in st.channelbags for fc in b_.fcurves]
for i, (t, f0) in enumerate(labels):
    f1 = labels[i + 1][1] if i + 1 < len(labels) else END + 1
    for fr, hide in ((0, True), (f0, False), (f1, True)):
        t.hide_render = hide; t.keyframe_insert("hide_render", frame=max(0, fr))

scene.render.fps = 20
scene.frame_start, scene.frame_end = 0, END
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
try:
    scene.eevee.taa_render_samples = 16
except Exception:
    pass
if STILLS:
    d = os.path.splitext(OUT)[0] + "_stills"; os.makedirs(d, exist_ok=True)
    for name, f0, n, label in segs:
        if label:
            scene.frame_set(f0 + n // 2); scene.render.filepath = os.path.join(d, f"{name}.png")
            bpy.ops.render.render(write_still=True)
    print("STILLS_OK", END)
else:
    ims = scene.render.image_settings
    if hasattr(ims, "media_type"):
        ims.media_type = "VIDEO"
    ims.file_format = "FFMPEG"
    ff = scene.render.ffmpeg; ff.format = "MPEG4"; ff.codec = "H264"; ff.constant_rate_factor = "HIGH"
    scene.render.filepath = OUT
    bpy.ops.render.render(animation=True)
    print("VIDEO_OK", END)
