"""Render quick preview stills of an imported GeckoLib model: (action, frame) pairs from the command line.
blender -b model.blend --python preview.py -- out_dir idle:0 sweep:30 death:79"""
import bpy, sys, os, math
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
out = args[0]; os.makedirs(out, exist_ok=True)
scene = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH")
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        scene.render.engine = eng; break
    except TypeError:
        pass
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("W"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.25, 0.25, 0.3, 1)
for name, kind, energy, loc in (("Key", "SUN", 3.0, (4, -6, 8)), ("Fill", "SUN", 1.0, (-6, -3, 3)), ("Back", "SUN", 1.5, (0, 8, 6))):
    L = bpy.data.lights.new(name, kind); L.energy = energy
    o = bpy.data.objects.new(name, L); scene.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, 2)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
bpy.ops.mesh.primitive_plane_add(size=30)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scene.collection.objects.link(cam); scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = 700, 800
for spec in args[1:]:
    act, fr = spec.split(":")
    rig.animation_data.action = bpy.data.actions[act]
    scene.frame_set(int(fr))
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg); me = ev.to_mesh()
    pts = [mesh.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear()
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    c = (lo + hi) / 2; size = max(hi - lo)
    for tag, d in (("front", Vector((0.45, -1, 0.25))), ("side", Vector((-1, -0.35, 0.25)))):
        cam.location = c + d.normalized() * size * 2.3
        cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler(); cam.data.lens = 50
        scene.render.filepath = os.path.join(out, f"{act}_{fr}_{tag}.png")
        bpy.ops.render.render(write_still=True)
print("PREVIEW_OK")
