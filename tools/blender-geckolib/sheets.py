"""Contact sheets (8 frames, side + 3/4 rows) for actions of an imported GeckoLib model.
blender -b model.blend --python sheets.py -- out_dir walk howl sweep"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(args[0]); os.makedirs(out, exist_ok=True)
scene = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        scene.render.engine = eng; break
    except TypeError:
        pass
scene.view_settings.view_transform = "Standard"
w = bpy.data.worlds.new("W"); scene.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.3, 0.3, 0.35, 1)
for name, e, loc in (("Key", 3.0, (4, -6, 8)), ("Fill", 1.2, (-6, -3, 3)), ("Back", 1.5, (0, 8, 6))):
    L = bpy.data.lights.new(name, "SUN"); L.energy = e
    o = bpy.data.objects.new(name, L); scene.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, 2)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
bpy.ops.mesh.primitive_plane_add(size=40)
gm = bpy.data.materials.new("G"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.55, 0.55, 0.55, 1)
bpy.context.object.data.materials.append(gm)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scene.collection.objects.link(cam); scene.camera = cam
TW, TH = 300, 330
scene.render.resolution_x, scene.render.resolution_y = TW, TH
for act_name in args[1:]:
    act = bpy.data.actions[act_name]
    rig.animation_data.action = act
    n = int(act.frame_range[1])
    rows = []
    for view in (Vector((1, 0.05, 0.12)), Vector((0.55, -1, 0.3)), Vector((-0.6, 1, 0.35))):   # his left side, front 3/4, back 3/4
        tiles = []
        for i in range(8):
            f = round(n * i / 7)
            scene.frame_set(f)
            c = Vector((0, 0, 2.6))
            cam.location = c + view.normalized() * 13; cam.data.lens = 45
            cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
            p = os.path.join(out, "_t.png"); scene.render.filepath = p
            bpy.ops.render.render(write_still=True)
            im = bpy.data.images.load(p); a = np.empty(TW * TH * 4, dtype=np.float32); im.pixels.foreach_get(a)
            tiles.append(a.reshape(TH, TW, 4)); bpy.data.images.remove(im)
        rows.append(np.concatenate(tiles, axis=1))
    sheet = np.concatenate(rows[::-1], axis=0)
    img = bpy.data.images.new(act_name, TW * 8, TH * len(rows), alpha=False)
    img.pixels.foreach_set(sheet.ravel()); img.filepath_raw = os.path.join(out, f"{act_name}.png"); img.file_format = "PNG"; img.save()
    print("SHEET", act_name)
os.remove(os.path.join(out, "_t.png"))
print("SHEETS_OK")
