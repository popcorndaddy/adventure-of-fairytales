"""Make an imported GeckoLib model glow like in game: the glowmask texture drives emission (GeckoLib's glowing layer).
blender -b model.blend --python add_glow.py -- glowmask.png [strength]   (saves the .blend in place)"""
import bpy, sys

args = sys.argv[sys.argv.index("--") + 1:]
mask = bpy.data.images.load(args[0])
strength = float(args[1]) if len(args) > 1 else 6.0
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    tex = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None)
    if not bsdf or not tex:
        continue
    g = nt.nodes.new("ShaderNodeTexImage"); g.image = mask; g.interpolation = "Closest"
    nt.links.new(tex.inputs["Vector"].links[0].from_socket if tex.inputs["Vector"].links else g.inputs["Vector"], g.inputs["Vector"]) if tex.inputs["Vector"].links else None
    mix = nt.nodes.new("ShaderNodeMath"); mix.operation = "MULTIPLY"
    nt.links.new(g.outputs["Color"], bsdf.inputs["Emission Color"])
    nt.links.new(g.outputs["Alpha"], mix.inputs[0]); mix.inputs[1].default_value = strength
    nt.links.new(mix.outputs[0], bsdf.inputs["Emission Strength"])
    # like the game: texels with alpha 0 in the base texture are cut out, but their glow still shows (additive layer)
    cut = nt.nodes.new("ShaderNodeMath"); cut.operation = "MAXIMUM"
    nt.links.new(tex.outputs["Alpha"], cut.inputs[0]); nt.links.new(g.outputs["Alpha"], cut.inputs[1])
    gl = nt.nodes.new("ShaderNodeMath"); gl.operation = "MULTIPLY"; gl.inputs[1].default_value = 0.22
    nt.links.new(g.outputs["Alpha"], gl.inputs[0])
    sel = nt.nodes.new("ShaderNodeMix"); sel.data_type = "FLOAT"
    nt.links.new(tex.outputs["Alpha"], sel.inputs["Factor"]); nt.links.new(gl.outputs[0], sel.inputs["A"]); sel.inputs["B"].default_value = 1.0
    nt.links.new(sel.outputs["Result"], bsdf.inputs["Alpha"])
    try:
        m.surface_render_method = "DITHERED"
    except Exception:
        m.blend_method = "HASHED"
    print("GLOW", m.name)
bpy.ops.wm.save_mainfile()
print("GLOW_OK")
