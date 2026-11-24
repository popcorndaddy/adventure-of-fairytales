"""Preview scene (render only, never exported): dark rune arena, fog, purple lighting, bloom, camera helpers."""
import bpy, math, os, random
from mathutils import Vector


def setup(fog=True, arena=True, bloom=True):
    scene = bpy.context.scene
    col = bpy.data.collections.get("Preview_Arena") or bpy.data.collections.new("Preview_Arena")
    if col.name not in scene.collection.children:
        scene.collection.children.link(col)
    for o in list(col.objects):
        bpy.data.objects.remove(o, do_unlink=True)

    def mat(name, color, emit=0.0):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*color, 1)
        b.inputs["Roughness"].default_value = 0.9
        if emit:
            b.inputs["Emission Color"].default_value = (*color, 1)
            b.inputs["Emission Strength"].default_value = emit
        return m

    def cube(name, loc, size, m):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        o = bpy.context.object; o.name = name; o.scale = size
        o.data.materials.append(m)
        for c in o.users_collection:
            c.objects.unlink(o)
        col.objects.link(o)
        return o

    floor_m = mat("Arena_Floor", (0.03, 0.018, 0.05))
    cube("Arena_Floor", (0, 0, -0.25), (80, 80, 0.5), floor_m)
    if arena:
        st = bpy.data.materials.get("GK_CorruptedStone") or mat("Arena_Stone", (0.12, 0.1, 0.15))
        rs = bpy.data.materials.get("GK_RuneStone") or st
        glow = mat("Arena_Glow", (0.74, 0.3, 1.0), 6)
        for i, (x, y) in enumerate(((-12, 9), (12, 10), (-17, -3), (17, -2), (0, 17), (-7, 15), (7, 15))):
            h = 11 + (i % 3) * 2
            p = cube(f"Arena_Pillar{i}", (x, y, h / 2), (2.6, 2.6, h), rs)
            cube(f"Arena_PillarCap{i}", (x, y, h + 0.3), (3.2, 3.2, 0.6), st)
            cube(f"Arena_PillarBase{i}", (x, y, 0.4), (3.2, 3.2, 0.8), st)
            cube(f"Arena_PillarGlow{i}", (x, y - 1.31, h * 0.6), (1.0, 0.04, 1.8), glow)
        r = random.Random(3)
        for i in range(26):
            a = r.uniform(0.15 * math.pi, 0.85 * math.pi); d = r.uniform(8, 22)
            cube(f"Arena_Rubble{i}", (d * math.cos(a), d * math.sin(a) + 2, 0.3), (r.uniform(0.6, 1.8),) * 3, st)

    world = bpy.data.worlds.get("GK_World") or bpy.data.worlds.new("GK_World")
    scene.world = world; world.use_nodes = True
    nt = world.node_tree
    nt.nodes["Background"].inputs[0].default_value = (0.006, 0.003, 0.016, 1)
    for n in [n for n in nt.nodes if n.type == "VOLUME_SCATTER"]:
        nt.nodes.remove(n)
    if fog:
        vs = nt.nodes.new("ShaderNodeVolumeScatter")
        vs.inputs["Color"].default_value = (0.42, 0.22, 0.8, 1); vs.inputs["Density"].default_value = 0.005
        nt.links.new(vs.outputs[0], nt.nodes["World Output"].inputs["Volume"])

    def light(name, kind, energy, loc, color, size=5, target=(0, 0, 3.5)):
        L = bpy.data.lights.new(name, kind); L.energy = energy; L.color = color
        if hasattr(L, "size"):
            L.size = size
        o = bpy.data.objects.new(name, L); o.location = loc; col.objects.link(o)
        o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return o

    light("Arena_Key", "AREA", 3200, (5, -12, 11), (0.85, 0.8, 1.0), 8)
    light("Arena_RimL", "AREA", 4200, (-8, 9, 9), (0.6, 0.3, 1.0), 6)
    light("Arena_RimR", "AREA", 3600, (9, 8, 7), (0.45, 0.4, 1.0), 6)
    light("Arena_Under", "AREA", 900, (0, -9, 0.6), (0.75, 0.35, 1.0), 6, (0, 0, 2))

    cam = bpy.data.objects.get("Arena_Cam")
    if not cam:
        cam = bpy.data.objects.new("Arena_Cam", bpy.data.cameras.new("Arena_Cam"))
        col.objects.link(cam)
    scene.camera = cam

    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = eng; break
        except TypeError:
            pass
    scene.view_settings.view_transform = "Standard"
    try:
        scene.eevee.volumetric_end = 60
    except Exception:
        pass
    if bloom:
        try:
            ng = bpy.data.node_groups.get("GK_Bloom")
            if not ng:
                ng = bpy.data.node_groups.new("GK_Bloom", "CompositorNodeTree")
                ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
                rl = ng.nodes.new("CompositorNodeRLayers"); gl = ng.nodes.new("CompositorNodeGlare"); go = ng.nodes.new("NodeGroupOutput")
                try:
                    gl.glare_type = "BLOOM"
                except Exception:
                    gl.inputs["Type"].default_value = "Bloom"
                for k, v in (("Threshold", 0.9), ("Strength", 0.65), ("Size", 0.55)):
                    if k in gl.inputs:
                        try:
                            gl.inputs[k].default_value = v
                        except Exception:
                            pass
                ng.links.new(rl.outputs["Image"], gl.inputs["Image"]); ng.links.new(gl.outputs["Image"], go.inputs[0])
            scene.compositing_node_group = ng
        except Exception as e:
            print("BLOOM_SKIPPED", e)
    return cam


def shot(path, loc, target, lens=32, res=(1000, 1150)):
    scene = bpy.context.scene
    cam = scene.camera
    cam.location = loc; cam.data.lens = lens
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
