"""Review renders of an imported Sentinel model, lit like a dark dungeon so black armour still reads (cold rim light,
low fill, the heart and eyes glowing). Renders one strip of views for one or more frames.
blender -b model.blend --python sk_review.py -- out.png action frame[,frame..] [views=front34,side,back34,front_close]"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
out, act_name, frames = os.path.abspath(args[0]), args[1], [int(x) for x in args[2].split(",")]
views = (args[3] if len(args) > 3 else "front34,side,back34,front_close").split(",")
scene = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
scene.render.engine = "BLENDER_EEVEE"
try:
    scene.view_settings.view_transform = "AgX"; scene.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    scene.view_settings.view_transform = "Standard"
w = bpy.data.worlds.new("W"); scene.world = w
try:
    w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.035, 0.03, 0.05, 1)
except Exception:
    pass
for name, kind, e, loc, col in (("Key", "SUN", 3.2, (5, -7, 8), (1.0, 0.97, 0.94)), ("Rim", "SUN", 5.0, (-3, 9, 5), (0.7, 0.75, 1.0)),
                                ("Rim2", "SUN", 3.0, (7, 6, 4), (0.75, 0.7, 1.0)), ("Fill", "SUN", 0.8, (-8, -5, 2), (0.6, 0.5, 0.9))):
    L = bpy.data.lights.new(name, kind); L.energy = e; L.color = col
    o = bpy.data.objects.new(name, L); scene.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, 2.5)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
for o in bpy.data.objects:
    if o.type == "MESH" and o.parent is None and not any(m.type == "ARMATURE" for m in o.modifiers):
        o.hide_render = True                      # stray importer helpers (backdrops etc.)
bpy.ops.mesh.primitive_plane_add(size=200)
fl = bpy.context.object; fm = bpy.data.materials.new("Floor"); fm.use_nodes = True
fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.09, 0.09, 0.1, 1)
fl.data.materials.append(fm)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scene.collection.objects.link(cam); scene.camera = cam
VIEWS = {"front34": (Vector((0.65, -1, 0.22)), 2.7, 11.5), "side": (Vector((1, 0.02, 0.12)), 2.7, 11.5),
         "back34": (Vector((-0.7, 1, 0.3)), 2.7, 11.5), "front_close": (Vector((0.15, -1, 0.08)), 3.9, 4.6),
         "front": (Vector((0.05, -1, 0.1)), 2.7, 11.5), "top34": (Vector((0.6, -0.8, 0.9)), 2.5, 12)}
TW, TH = 520, 680
scene.render.resolution_x, scene.render.resolution_y = TW, TH
if act_name in bpy.data.actions:
    rig.animation_data_create(); rig.animation_data.action = bpy.data.actions[act_name]
rows = []
tmp = os.path.join(os.path.dirname(out), "_r.png")
for f in frames:
    tiles = []
    for v in views:
        d, tz, dist = VIEWS[v]
        scene.frame_set(f)
        c = Vector((0, 0, tz))
        cam.location = c + d.normalized() * dist; cam.data.lens = 50
        cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = tmp; bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(tmp); a = np.empty(TW * TH * 4, dtype=np.float32); im.pixels.foreach_get(a)
        tiles.append(a.reshape(TH, TW, 4)); bpy.data.images.remove(im)
    rows.append(np.concatenate(tiles, axis=1))
sheet = np.concatenate(rows[::-1], axis=0)
img = bpy.data.images.new("r", sheet.shape[1], sheet.shape[0], alpha=False)
img.pixels.foreach_set(sheet.ravel()); img.filepath_raw = out; img.file_format = "PNG"; img.save()
os.remove(tmp)
print("REVIEW_OK", out)
