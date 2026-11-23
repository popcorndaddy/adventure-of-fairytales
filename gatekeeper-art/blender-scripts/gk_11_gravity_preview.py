"""Stage 11 - GRAVITY WELL preview: the clip in the portal arena with its swirling VFX, rendered to
Gatekeeper_Gravity_Well.mp4 (or a few stills with --stills).
VFX: spiral vortex arms on the floor and at chest height that wind faster as the well tightens, ~180 glowing motes and
36 stone chunks spiralling inward on accelerating paths, a purple core light; on the burst (frame 114) a flash, an
expanding shockwave ring and everything flung outward.
Usage: blender -b --python gk_11_gravity_preview.py -- <gatekeeper-art folder> [--stills]"""
import bpy, sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
from mathutils import Vector
import gk_arena as AR

ART = sys.argv[sys.argv.index("--") + 1]
STILLS = "--stills" in sys.argv
bpy.ops.wm.open_mainfile(filepath=os.path.join(ART, "gatekeeper_stage3.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["Gatekeeper_Rig"]
N = 150
BURST, OPEN = 114, 24
col, lights, portal = AR.build(length=N + 1)
rig.animation_data.action = bpy.data.actions["Gatekeeper_Gravity_Well"]
rig.location = (0, 0, 0)
try:
    bpy.data.materials["GK_EyeGlow"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 16.0
except KeyError:
    pass
fx = bpy.data.collections.new("GravityWell_FX"); scene.collection.children.link(fx)
rnd = random.Random(7)


def frac(x):
    return x - math.floor(x)


def smooth(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def intensity(f):
    """How strong the well is: opens at 24, full by 40, swells in the compress beat, gone at the burst."""
    if f < OPEN:
        return 0.0
    if f < BURST:
        return smooth((f - OPEN) / 16) * (1 + 0.35 * smooth((f - 100) / 12))
    return 0.0


def link(o):
    fx.objects.link(o); return o


# ---------------------------------------------------------------- materials
violet = AR._mat_emit("GW_Violet", (0.62, 0.22, 1.0), 22.0)
pink = AR._mat_emit("GW_Pink", (1.0, 0.55, 1.0), 40.0)
arm_m = AR._mat_emit("GW_Arm", (0.55, 0.2, 1.0), 14.0)
wave_m = AR._mat_emit("GW_Wave", (0.8, 0.45, 1.0), 30.0)
flash_m = AR._mat_emit("GW_Flash", (1.0, 0.8, 1.0), 80.0)
stone = bpy.data.materials.get("GK_CorruptedStone")

# ---------------------------------------------------------------- spiral vortex arms (curves)
def spiral(name, turns, r0, r1, z, phase, bevel):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"
    sp = cu.splines.new("POLY"); n = 140
    sp.points.add(n - 1)
    for i in range(n):
        t = i / (n - 1)
        r = r1 + (r0 - r1) * (1 - t) ** 1.25
        a = phase + 2 * math.pi * turns * t
        sp.points[i].co = (r * math.cos(a), r * math.sin(a), 0, 1)
    cu.bevel_depth = bevel; cu.bevel_resolution = 2
    cu.taper_radius_mode = "MULTIPLY" if hasattr(cu, "taper_radius_mode") else None
    o = link(bpy.data.objects.new(name, cu)); o.location = (0, 0, z); o.data.materials.append(arm_m)
    return o


arms = []
for k in range(3):
    arms.append((spiral(f"GW_FloorArm{k}", 1.6, 7.5, 1.2, 0.12, 2 * math.pi * k / 3, 0.06), 1.0, 0.0))
    o = spiral(f"GW_ChestArm{k}", 1.3, 4.2, 1.0, 3.6, 2 * math.pi * k / 3 + 1.0, 0.04)
    o.rotation_euler = (math.radians(9), 0, 0)
    arms.append((o, 1.6, 1.0))

# ---------------------------------------------------------------- motes + debris
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1); mote_mesh = bpy.context.object.data
bpy.data.objects.remove(bpy.context.object)
bpy.ops.mesh.primitive_cube_add(size=1); deb_mesh = bpy.context.object.data
bpy.data.objects.remove(bpy.context.object)
motes = []
for i in range(180):
    o = link(bpy.data.objects.new(f"GW_Mote{i}", mote_mesh.copy()))
    o.data.materials.append(pink if i % 5 == 0 else violet)
    motes.append(dict(o=o, a0=rnd.uniform(0, 2 * math.pi), u0=rnd.random(), rate=rnd.uniform(1 / 46, 1 / 30), rmax=rnd.uniform(3.5, 10.0),
                      z0=rnd.uniform(0.1, 7.0), zc=rnd.uniform(2.6, 4.6), s=rnd.uniform(0.035, 0.09), wob=rnd.uniform(0, 6.28), debris=False))
for i in range(36):
    o = link(bpy.data.objects.new(f"GW_Debris{i}", deb_mesh))
    if stone:
        o.data.materials.clear(); o.data.materials.append(stone)
    motes.append(dict(o=o, a0=rnd.uniform(0, 2 * math.pi), u0=rnd.random(), rate=rnd.uniform(1 / 70, 1 / 50), rmax=rnd.uniform(4.5, 9.0),
                      z0=rnd.uniform(0.05, 0.6), zc=rnd.uniform(0.8, 2.6), s=rnd.uniform(0.12, 0.32), wob=rnd.uniform(0, 6.28), debris=True,
                      spin=Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(-0.2, 0.2)))))


def spiral_pos(m, f):
    u = frac(m["u0"] + m["rate"] * f)
    r = 1.3 + (m["rmax"] - 1.3) * (1 - u) ** 1.4
    ang = m["a0"] + 2 * math.pi * 1.8 * u ** 1.6 + 0.025 * f            # accelerates as it falls in (counter-clockwise from above)
    z = m["z0"] * (1 - u) + m["zc"] * u + 0.25 * math.sin(f * 0.15 + m["wob"])
    env = min(1.0, (1 - u) * 6) * min(1.0, u * 8)
    return Vector((r * math.cos(ang), r * math.sin(ang), z)), env


# ---------------------------------------------------------------- burst pieces
bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.06, major_segments=64, minor_segments=8)
wave = bpy.context.object; bpy.context.collection.objects.unlink(wave); link(wave); wave.name = "GW_Shockwave"
wave.data.materials.append(wave_m)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=24, ring_count=12)
flash = bpy.context.object; bpy.context.collection.objects.unlink(flash); link(flash); flash.name = "GW_Flash"
flash.data.materials.append(flash_m)
core = bpy.data.lights.new("GW_Core", "POINT"); core.color = (0.7, 0.35, 1.0); core.shadow_soft_size = 1.5
core_o = link(bpy.data.objects.new("GW_Core", core)); core_o.location = (0, -0.6, 3.4)

# ---------------------------------------------------------------- key everything per frame
burst_state = {}
for f in range(0, N + 1):
    I = intensity(f)
    for o, spd, ph in arms:
        o.rotation_euler.z = -(0.035 * f + 0.0009 * f * f) * spd + ph      # winds faster and faster
        sc = (0.0 if f < OPEN else min(1.0, I)) * (1 - 0.55 * smooth((f - 102) / 12))
        o.scale = (sc, sc, 1)
        o.keyframe_insert("rotation_euler", frame=f); o.keyframe_insert("scale", frame=f)
    for m in motes:
        o = m["o"]
        if f < BURST:
            p, env = spiral_pos(m, f)
            s = m["s"] * env * min(1.0, I)
            if f == BURST - 1:
                burst_state[o.name] = p.copy()
        else:
            p0 = burst_state[o.name]
            out = Vector((p0.x, p0.y, 0)).normalized() if Vector((p0.x, p0.y)).length > 1e-3 else Vector((1, 0, 0))
            t = f - BURST
            sp = (0.55 if not m["debris"] else 0.38) * (1 - 0.03 * t)
            p = p0 + out * sp * t * 1.6 + Vector((0, 0, (0.18 * t - 0.012 * t * t) if m["debris"] else 0.05 * t))
            p.z = max(p.z, 0.08)
            s = m["s"] * (1 - smooth(t / (18 if not m["debris"] else 30)))
        o.location = p; o.scale = (s, s, s)
        o.keyframe_insert("location", frame=f); o.keyframe_insert("scale", frame=f)
        if m["debris"]:
            o.rotation_euler = tuple(v * f for v in m["spin"]); o.keyframe_insert("rotation_euler", frame=f)
    # core light + burst
    core.energy = 2500 * I + 60000 * math.exp(-max(0, f - BURST) / 3.0) * (f >= BURST)
    core.keyframe_insert("energy", frame=f)
    t = f - BURST
    ws = 0.0 if t < 0 or t > 18 else 0.6 + 13.5 * (1 - (1 - t / 18) ** 2)
    wave.location = (0, 0, 0.3); wave.scale = (ws, ws, max(ws, 0.01) * 0.0 + 1.0)
    wave.keyframe_insert("scale", frame=f)
    wave_m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 0.0 if t < 0 else 30.0 * (1 - smooth(t / 18))
    wave_m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
    fs = 0.0 if t < 0 or t > 6 else 1.1 * math.sin(math.pi * min(1.0, t / 6) ** 0.6)
    flash.location = (0, -0.6, 3.4); flash.scale = (fs, fs, fs); flash.keyframe_insert("scale", frame=f)
for o in fx.objects:
    ad = o.animation_data
    if ad and ad.action:
        fcs = ad.action.fcurves if hasattr(ad.action, "fcurves") else [fc for l_ in ad.action.layers for st in l_.strips for b in st.channelbags for fc in b.fcurves]
        for fc in fcs:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"

# ---------------------------------------------------------------- camera: slow push-in orbit from his front-left
cam = link(bpy.data.objects.new("GW_Cam", bpy.data.cameras.new("GW_Cam"))); scene.camera = cam
tgt = link(bpy.data.objects.new("GW_Target", None)); tgt.location = (0, 0, 3.2)
tc = cam.constraints.new("TRACK_TO"); tc.target = tgt; tc.track_axis = "TRACK_NEGATIVE_Z"; tc.up_axis = "UP_Y"
for f in range(0, N + 1, 5):
    a = math.radians(-38 + 26 * f / N)
    d = 19.5 - 3.5 * smooth(f / BURST) + 2.0 * smooth((f - BURST) / 20)
    cam.location = (d * math.sin(a), -d * math.cos(a), 4.6 - 0.8 * f / N)
    cam.keyframe_insert("location", frame=f)
cam.data.lens = 28

for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        scene.render.engine = eng; break
    except TypeError:
        pass
try:
    scene.view_settings.view_transform = "AgX"; scene.view_settings.look = "AgX - Punchy"
except Exception:
    pass
try:
    scene.eevee.taa_render_samples = 16
except Exception:
    pass
ng = bpy.data.node_groups.get("GK_Bloom")
if ng:
    try:
        scene.compositing_node_group = ng
    except Exception:
        pass
scene.render.fps = 30
scene.frame_start, scene.frame_end = 0, N
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
if STILLS:
    os.makedirs(os.path.join(ART, "gravity_well_preview"), exist_ok=True)
    for f in (10, 40, 70, 106, 116, 124):
        scene.frame_set(f)
        scene.render.filepath = os.path.join(ART, "gravity_well_preview", f"gravity_well_{f:03d}.png")
        bpy.ops.render.render(write_still=True)
    print("STILLS_OK")
else:
    ims = scene.render.image_settings
    if hasattr(ims, "media_type"):
        ims.media_type = "VIDEO"
    ims.file_format = "FFMPEG"
    ff = scene.render.ffmpeg
    ff.format = "MPEG4"; ff.codec = "H264"; ff.constant_rate_factor = "HIGH"
    scene.render.filepath = os.path.join(ART, "Gatekeeper_Gravity_Well.mp4")
    bpy.ops.render.render(animation=True)
    print("VIDEO_OK")
