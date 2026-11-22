"""Stage 5 - cinematic boss introduction in the portal arena: portal destabilises, the Gatekeeper awakens,
unfolds his arms, turns his head, drags his sword (sparks), opens his eyes, steps forward and blocks the gate."""
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
try:
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
except Exception:
    pass
END = 600
col, lights, portal = AR.build(length=END)
try:
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
except Exception:
    pass
rig = bpy.data.objects["Gatekeeper_Rig"]
SND = os.path.join(OUT, "sounds")
r = random.Random(5)

# ---------------------------------------------------------------- the boss: NLA strips
A, E = 180, 390
rig.animation_data.action = None
tr = rig.animation_data.nla_tracks.new(); tr.name = "Cinematic"
s1 = tr.strips.new("Awakening", A, bpy.data.actions["Gatekeeper_Awakening"]); s1.extrapolation = "HOLD"
s2 = tr.strips.new("Entrance", E, bpy.data.actions["Gatekeeper_Entrance"]); s2.extrapolation = "HOLD_FORWARD"
s1.blend_out = 0; s2.blend_in = 8
for s in (s1, s2):
    try:
        s.action_slot = s.action.slots[0]
    except Exception:
        pass

# ---------------------------------------------------------------- eyes & core: dark until he wakes
eye = bpy.data.materials["GK_EyeGlow"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
for f, v in ((0, 0.0), (A + 150, 0.0), (A + 156, 4.0), (A + 162, 1.5), (A + 172, 20.0), (A + 190, 16.0), (E + 64, 26.0), (E + 80, 16.0)):
    eye.default_value = v; eye.keyframe_insert("default_value", frame=f)
for name, base in (("GK_RuneStone", 1.6), ("GK_PurpleEnergy", 4.0), ("GK_CyanRunes", 3.5), ("GK_MagentaFragments", 5.0)):
    inp = bpy.data.materials[name].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    for f, k in ((0, 0.08), (A + 40, 0.15), (A + 150, 0.4), (A + 172, 1.0), (E + 64, 1.5), (E + 80, 1.0)):
        inp.default_value = base * k; inp.keyframe_insert("default_value", frame=f)

# ---------------------------------------------------------------- portal flicker / destabilisation
ps = portal.node_tree.nodes["PortalStrength"].outputs[0]
pl = lights["portal"].data
keys = [(0, 3.5), (40, 4.0), (70, 2.2), (74, 5.0), (100, 3.0), (104, 8.5), (108, 1.2), (112, 7.0), (124, 2.0), (132, 9.0), (136, 0.8),
        (140, 10.0), (150, 3.0), (156, 11.0), (162, 1.5), (172, 12.0), (180, 6.0), (230, 5.0), (330, 6.0), (A + 172, 9.0), (E + 40, 13.0),
        (E + 52, 6.5), (E + 64, 12.0), (E + 90, 7.0), (END, 6.5)]
for f, v in keys:
    ps.default_value = v; ps.keyframe_insert("default_value", frame=f)
    pl.energy = 2600 * v; pl.keyframe_insert("energy", frame=f)

# ---------------------------------------------------------------- VFX helpers
spark_m = AR._mat_emit("FX_Spark", (1.0, 0.62, 0.95), 18.0)
dust_m = bpy.data.materials.new("FX_Dust"); dust_m.use_nodes = True
dust_m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.12, 0.09, 0.15, 1)
wave_m = AR._mat_emit("FX_Shockwave", (0.75, 0.35, 1.0), 6.0)


def weapon_tip(f):
    scene.frame_set(f)
    pb = rig.pose.bones["weapon"]
    M = rig.matrix_world @ pb.matrix
    return M @ Vector((0, 87 / 16.0, 0))


def sparks(f0, f1, per=3):
    """Sparks spraying from the sword tip while it scrapes the stone."""
    n = 0
    for f in range(f0, f1, 2):
        tip = weapon_tip(f)
        if tip.z > 0.25:
            continue
        for k in range(per):
            o = AR._cube_obj(f"FX_Spark{n}", r.uniform(0.02, 0.05), spark_m, col); n += 1
            v = Vector((r.uniform(-1.5, 1.5), r.uniform(-1.8, 0.4), r.uniform(1.0, 3.2)))
            life = r.randint(8, 14)
            AR._key(o, f - 1, loc=tuple(tip), sc=0.0)
            for i in range(0, life + 1, 2):
                t = i / 30.0
                p = tip + v * t + Vector((0, 0, -4.9 * t * t))
                p.z = max(p.z, 0.02)
                AR._key(o, f + i, loc=tuple(p), sc=1.0 if i < life else 0.0)
    return n


def impact(f, at, radius=3.5, dust=26, ring=True):
    """Ground impact: a purple shockwave ring plus a burst of dust and stone chips."""
    if ring:
        B = AR.Boxes()
        for i in range(36):
            a = 2 * math.pi * i / 36
            Mt = Matrix.Translation((math.cos(a), math.sin(a), 0.05)) @ Matrix.Rotation(a, 4, "Z")
            B.box(-0.04, 0.04, -0.1, 0.1, -0.04, 0.04, wave_m, M=Mt)
        w = B.make(f"FX_Shockwave{f}", col)
        AR._key(w, f - 1, loc=tuple(at), sc=0.0); AR._key(w, f, loc=tuple(at), sc=0.3)
        AR._key(w, f + 10, loc=tuple(at), sc=radius); w.scale = (radius * 1.3,) * 3; w.keyframe_insert("scale", frame=f + 18)
        w.scale = (0, 0, 0); w.keyframe_insert("scale", frame=f + 19)
    for i in range(dust):
        o = AR._cube_obj(f"FX_Dust{f}_{i}", r.uniform(0.06, 0.2), dust_m if i % 3 else bpy.data.materials["GK_CorruptedStone"], col)
        a = r.uniform(0, 2 * math.pi); sp = r.uniform(1.5, 4.0); up = r.uniform(0.8, 3.5)
        AR._key(o, f - 1, loc=tuple(at), sc=0.0)
        for k in range(0, 25, 3):
            t = k / 30.0
            p = Vector(at) + Vector((math.cos(a) * sp * t, math.sin(a) * sp * t, max(0.05, up * t - 4.9 * t * t)))
            AR._key(o, f + k, loc=tuple(p), sc=1.0 if k < 24 else 0.0)


def foot_pos(S, f):
    scene.frame_set(f)
    pb = rig.pose.bones[f"foot_{S}"]
    p = rig.matrix_world @ pb.head
    return Vector((p.x, p.y, 0.02))


ev = json.loads(scene["gk_events"])
n_sp = sparks(A + 110, A + 152)
for f in ev["Gatekeeper_Entrance"]["heavy_step"]:
    impact(E + f, foot_pos("L" if f < 60 else "R", E + f), radius=3.2)
print("SPARKS", n_sp)

# point lights riding on the boss: core glow and fire glow
for name, bone, color, energy in (("FX_CoreLight", "chest", (0.85, 0.45, 1.0), 240), ("FX_FireLightR", "fx_fire_R", (0.8, 0.35, 1.0), 300),
                                  ("FX_FireLightL", "fx_fire_L", (0.8, 0.35, 1.0), 300)):
    Ld = bpy.data.lights.new(name, "POINT"); Ld.energy = energy; Ld.color = color; Ld.shadow_soft_size = 0.4
    o = bpy.data.objects.new(name, Ld); col.objects.link(o)
    o.parent = rig; o.parent_type = "BONE"; o.parent_bone = bone
    o.location = (0, -0.9 if bone == "chest" else 0.4, 0)
    for f, v in ((0, 0.0), (A + 40, 0.0), (A + 70, energy * 0.6), (A + 172, energy), (E + 64, energy * 1.6), (E + 85, energy)):
        Ld.energy = v; Ld.keyframe_insert("energy", frame=f)

# ---------------------------------------------------------------- camera: one shot per story beat
cam = bpy.data.objects.new("Cine_Cam", bpy.data.cameras.new("Cine_Cam")); col.objects.link(cam); scene.camera = cam
cam.data.sensor_width = 36
tgt = bpy.data.objects.new("Cine_Target", None); col.objects.link(tgt)
tc = cam.constraints.new("TRACK_TO"); tc.target = tgt; tc.track_axis = "TRACK_NEGATIVE_Z"; tc.up_axis = "UP_Y"
SHOTS = [  # frame, camera position, look-at, lens
    (0, (0.6, -44, 1.7), (0, 12, 8.5), 28), (96, (0.4, -32, 1.8), (0, 12, 8.0), 28),                   # 1 player approaches the portal
    (100, (-3, -21, 0.8), (0, 13, 9), 24), (178, (-1.5, -17, 1.1), (0, 13, 8.5), 24),                 # 2-3 portal flickers, energy leaks
    (180, (-14, -11, 2.4), (0, 2, 2.6), 34), (214, (-12, -9.5, 3.0), (0, 1, 3.0), 36),                # 4 a shape in the shadows awakens
    (215, (7.5, -7.5, 5.8), (0, 0, 4.8), 34), (262, (6.0, -6.5, 6.4), (0, 0, 5.2), 36),               # 5 additional arms unfold
    (263, (1.6, -7.8, 6.2), (0, -0.5, 5.6), 46), (300, (1.0, -7.2, 6.0), (0, -0.5, 5.6), 50),          # 6 head turns toward the player
    (301, (-9, -8.5, 0.6), (-2.8, -0.4, 0.9), 30), (338, (-8, -6.5, 0.7), (-2.2, 0, 1.0), 32),        # 7 the blade drags: sparks
    (339, (0.5, -4.8, 6.0), (0, 0, 6.05), 52), (388, (0.4, -4.3, 6.05), (0, 0, 6.05), 58),            # 8 raises his head, eyes open
    (389, (0.2, -26, 1.0), (0, 6, 7.0), 30), (430, (0.2, -24, 0.9), (0, 4, 6.6), 30),                 # 9-10 silhouette blocks the gate, heavy step
    (470, (0.0, -21, 0.9), (0, 2, 6.0), 28), (600, (0.0, -17.5, 1.3), (0, 1, 5.6), 30),               # 11 the fight begins
]
for f, p, t, lens in SHOTS:
    cam.location = p; cam.keyframe_insert("location", frame=f)
    tgt.location = t; tgt.keyframe_insert("location", frame=f)
    cam.data.lens = lens; cam.data.keyframe_insert("lens", frame=f)
# hard cuts between shots: constant interpolation on the frame where a new shot starts
cuts = {100, 180, 215, 263, 301, 339, 389}
for idb in (cam, tgt, cam.data):
    ad = idb.animation_data
    if not ad or not ad.action:
        continue
    try:
        fcs = ad.action.fcurves
    except AttributeError:
        fcs = [fc for layer in ad.action.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
    for fc in fcs:
        for i, kp in enumerate(fc.keyframe_points):
            nxt = fc.keyframe_points[i + 1].co.x if i + 1 < len(fc.keyframe_points) else None
            if nxt is not None and int(round(nxt)) in cuts:
                kp.interpolation = "CONSTANT"
            else:
                kp.interpolation = "BEZIER"
# camera shake on the heavy steps and the roar
for f0, amp in ((E + 40, 0.18), (E + 74, 0.14), (E + 64, 0.08)):
    for k in range(1, 12):
        f = f0 + k
        scene.frame_set(f)
        base = cam.matrix_world.translation.copy()
        d = Vector((r.uniform(-1, 1), 0, r.uniform(-1, 1))) * amp * (1 - k / 12)
        cam.location = base + d; cam.keyframe_insert("location", frame=f)

# ---------------------------------------------------------------- sound cues
se = scene.sequence_editor_create()
strips = se.strips if hasattr(se, "strips") else se.sequences
def snd(name, f, ch, vol=1.0):
    s = strips.new_sound(name + str(f), os.path.join(SND, name + ".wav"), ch, f); s.volume = vol
    return s
for f in (1, 300):
    snd("portal_hum", f, 1, 0.8)
for f in (1, 236, 472):
    snd("guardian_ambient", f, 2, 0.5)
for f in (100, 132, 152, 168):
    snd("portal_flicker", f, 3, 0.8)
snd("guardian_pulse", A + 40, 4, 0.9); snd("guardian_pulse", A + 62, 5, 0.9)
snd("stone_drag", A + 108, 6, 1.0)
snd("eyes_open", A + 172 - 48, 7, 1.0)
snd("heavy_step", E + 40, 8, 1.0); snd("impact_boom", E + 40, 9, 0.6)
snd("guardian_shriek", E + 62, 10, 1.0)
snd("heavy_step", E + 74, 8, 0.9)
snd("guardian_pulse", E + 120, 4, 0.7)

# ---------------------------------------------------------------- render settings
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        scene.render.engine = eng; break
    except TypeError:
        pass
scene.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in scene.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
scene.view_settings.look = "None"
try:
    scene.view_settings.look = "AgX - Punchy"
except Exception:
    pass
try:
    scene.eevee.taa_render_samples = 24
    scene.eevee.volumetric_end = 70; scene.eevee.volumetric_tile_size = "8"
    scene.eevee.use_volumetric_shadows = True
except Exception:
    pass
scene.render.fps = 30
scene.frame_start, scene.frame_end = 0, END
try:
    ng = bpy.data.node_groups.get("GK_Bloom")
    if ng:
        scene.compositing_node_group = ng
except Exception:
    pass
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Gatekeeper_Cinematic.blend"))

if PREVIEW:   # quick stills at each story beat
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    for f in (60, 150, 200, 240, 285, 320, 368, 415, 450, 590):
        scene.frame_set(f)
        scene.render.filepath = os.path.join(OUT, "cine_preview", f"beat_{f:03d}.png")
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
    scene.render.filepath = os.path.join(OUT, "Gatekeeper_Intro_Cinematic.mp4")
    bpy.ops.render.render(animation=True)
    print("VIDEO_OK")
