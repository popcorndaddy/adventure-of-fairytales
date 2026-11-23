"""Close-up stills of chosen frames, one view: blender -b model.blend --python closeup.py -- out.png action f1,f2,.. [side|front|back]"""
import bpy, sys, os
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
out, act_name, frames = os.path.abspath(args[0]), args[1], [int(x) for x in args[2].split(",")]
view = {"side": Vector((1, 0.05, 0.12)), "front": Vector((0.55, -1, 0.3)), "back": Vector((-0.6, 1, 0.35))}[args[3] if len(args) > 3 else "side"]
scene = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
scene.render.engine = "BLENDER_EEVEE"
scene.view_settings.view_transform = "Standard"
w = bpy.data.worlds.new("W"); scene.world = w
for name, e, loc in (("Key", 3.0, (4, -6, 8)), ("Fill", 1.5, (-6, -3, 3)), ("Back", 1.5, (0, 8, 6))):
    L = bpy.data.lights.new(name, "SUN"); L.energy = e
    o = bpy.data.objects.new(name, L); scene.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, 2)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scene.collection.objects.link(cam); scene.camera = cam
TW, TH = 500, 650
scene.render.resolution_x, scene.render.resolution_y = TW, TH
rig.animation_data.action = bpy.data.actions[act_name]
tiles = []
tmp = os.path.join(os.path.dirname(out), "_c.png")
for f in frames:
    scene.frame_set(f)
    c = Vector((0, 0, 2.4))
    cam.location = c + view.normalized() * 9; cam.data.lens = 50
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = tmp; bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(tmp); a = np.empty(TW * TH * 4, dtype=np.float32); im.pixels.foreach_get(a)
    tiles.append(a.reshape(TH, TW, 4)); bpy.data.images.remove(im)
img = bpy.data.images.new("c", TW * len(frames), TH, alpha=False)
img.pixels.foreach_set(np.concatenate(tiles, axis=1).ravel()); img.filepath_raw = out; img.file_format = "PNG"; img.save()
os.remove(tmp)
print("CLOSEUP_OK")
