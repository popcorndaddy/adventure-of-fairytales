"""Isolated hand close-up on the source rig (only the hand, fingers, thumb and sword blocks shown).
blender -b sentinel_knight_anim.blend --python tools/handview.py -- out.png action frame R|L"""
import bpy, sys, os
import numpy as np
from mathutils import Vector
args = sys.argv[sys.argv.index("--") + 1:]
out, act, frame, S = os.path.abspath(args[0]), args[1], int(args[2]), args[3]
scene = bpy.context.scene
rig = bpy.data.objects["Sentinel_Rig"]
rig.animation_data.action = bpy.data.actions[act]
scene.frame_set(frame)
keep = {f"hand_{S}", f"thumb1_{S}", f"thumb2_{S}", "sword"} | {f"{f}{k}_{S}" for f in ("index", "middle", "ring") for k in (1, 2)}
for o in bpy.data.objects:
    if o.type == "MESH":
        o.hide_render = o.get("sk_bone") not in keep or "sk_mat" not in o
        if not o.hide_render:
            m = bpy.data.materials.new(o.name); m.diffuse_color = o.color
            m.use_nodes = True; m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (
                (0.85, 0.65, 0.2, 1) if o["sk_bone"].startswith(("index", "middle", "ring", "thumb")) else (0.25, 0.25, 0.3, 1))
            o.data.materials.clear(); o.data.materials.append(m)
scene.render.engine = "BLENDER_EEVEE"
w = bpy.data.worlds.new("W"); scene.world = w
L = bpy.data.lights.new("K", "SUN"); L.energy = 3; lo = bpy.data.objects.new("K", L); scene.collection.objects.link(lo); lo.rotation_euler = (0.6, 0.3, 0.5)
c = rig.matrix_world @ rig.pose.bones[f"hand_{S}"].tail
cam = bpy.data.objects.new("C", bpy.data.cameras.new("C")); scene.collection.objects.link(cam); scene.camera = cam
tiles = []
scene.render.resolution_x, scene.render.resolution_y = 420, 420
tmp = os.path.join(os.path.dirname(out), "_h.png")
for d in (Vector((0, -1, 0.2)), Vector((1 if S == "R" else -1, -0.3, 0.2)), Vector((-1 if S == "R" else 1, -0.3, 0.2))):
    cam.location = c + d.normalized() * 0.9
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = tmp; bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(tmp); a = np.empty(420 * 420 * 4, dtype=np.float32); im.pixels.foreach_get(a)
    tiles.append(a.reshape(420, 420, 4)); bpy.data.images.remove(im)
img = bpy.data.images.new("h", 420 * 3, 420, alpha=False)
img.pixels.foreach_set(np.concatenate(tiles, axis=1).ravel()); img.filepath_raw = out; img.file_format = "PNG"; img.save()
os.remove(tmp); print("HAND_OK")
