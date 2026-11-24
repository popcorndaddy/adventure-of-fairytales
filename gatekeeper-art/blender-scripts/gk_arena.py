"""The Gatekeeper's portal arena (metres). The boss stands at the origin facing -Y; the portal is behind him at +Y.
build() creates everything in a 'Portal_Arena' collection. Animated parts loop over `length` frames."""
import bpy, math, random
from mathutils import Vector, Matrix
import gk_lib as L

PURPLE = (0.74, 0.30, 1.0)


def _mat_emit(name, color, strength):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Emission Color"].default_value = (*color, 1)
    b.inputs["Emission Strength"].default_value = strength
    return m


def portal_material():
    m = bpy.data.materials.new("Arena_PortalSurface")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.2; nz.inputs["Detail"].default_value = 6
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = "RINGS"; wv.inputs["Scale"].default_value = 1.6; wv.inputs["Distortion"].default_value = 9
    mix = nt.nodes.new("ShaderNodeMath"); mix.operation = "MULTIPLY"
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.25; cr.color_ramp.elements[0].color = (0.02, 0.0, 0.05, 1)
    cr.color_ramp.elements[1].position = 0.75; cr.color_ramp.elements[1].color = (0.95, 0.45, 1.0, 1)
    e = cr.color_ramp.elements.new(0.5); e.color = (0.35, 0.06, 0.6, 1)
    val = nt.nodes.new("ShaderNodeValue"); val.name = "PortalStrength"; val.outputs[0].default_value = 6.0
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], mix.inputs[0]); nt.links.new(wv.outputs["Fac"], mix.inputs[1])
    nt.links.new(mix.outputs[0], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], em.inputs["Color"]); nt.links.new(val.outputs[0], em.inputs["Strength"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    fc = mp.inputs["Location"].driver_add("default_value", 2)          # the swirl drifts over time
    fc.driver.expression = "frame/110"
    fc2 = mp.inputs["Rotation"].driver_add("default_value", 1)
    fc2.driver.expression = "frame/240"
    return m


class Boxes:
    def __init__(self):
        self.v, self.f, self.uv, self.fm, self.mats = [], [], [], [], []

    def box(self, x0, x1, y0, y1, z0, z1, mat, M=None):
        C = [Vector(c) for c in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
        Lc = [c.copy() for c in C]
        if M is not None:
            C = [M @ c for c in C]
        base = len(self.v)
        self.v += [tuple(c) for c in C]
        if mat not in self.mats:
            self.mats.append(mat)
        for idx, (a, b) in (((0, 1, 5, 4), (0, 2)), ((2, 3, 7, 6), (0, 2)), ((3, 0, 4, 7), (1, 2)), ((1, 2, 6, 5), (1, 2)), ((4, 5, 6, 7), (0, 1)), ((3, 2, 1, 0), (0, 1))):
            self.f.append(tuple(base + i for i in idx))
            self.uv.append([(Lc[i][a] / 4.0, Lc[i][b] / 4.0) for i in idx])
            self.fm.append(self.mats.index(mat))

    def make(self, name, col):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        lay = me.uv_layers.new(name="UVMap")
        for poly, uvs in zip(me.polygons, self.uv):
            for li, uv in zip(poly.loop_indices, uvs):
                lay.data[li].uv = uv
        for m in self.mats:
            me.materials.append(m)
        for poly, mi in zip(me.polygons, self.fm):
            poly.material_index = mi
        me.update()
        o = bpy.data.objects.new(name, me)
        col.objects.link(o)
        return o


def _cube_obj(name, size, mat, col):
    B = Boxes(); B.box(-size, size, -size, size, -size, size, mat)
    return B.make(name, col)


def _key(o, f, loc=None, rot=None, sc=None):
    if loc is not None:
        o.location = loc; o.keyframe_insert("location", frame=f)
    if rot is not None:
        o.rotation_euler = rot; o.keyframe_insert("rotation_euler", frame=f)
    if sc is not None:
        o.scale = (sc, sc, sc); o.keyframe_insert("scale", frame=f)


def chain_curve(B, a, b, sag, mat, link=0.26):
    a, b = Vector(a), Vector(b)
    n = max(4, int((b - a).length / (link * 0.8)))
    pts = [a.lerp(b, i / n) - Vector((0, 0, sag * 4 * (i / n) * (1 - i / n))) for i in range(n + 1)]
    for i in range(n):
        p, q = pts[i], pts[i + 1]
        d = (q - p).normalized(); c = (p + q) / 2
        h = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        x = d.cross(h).normalized(); z = x.cross(d)
        if i % 2:
            x, z = z, -x
        M = Matrix((x, d, z)).transposed().to_4x4(); M.translation = c
        B.box(-0.08, 0.08, -link * 0.6, link * 0.6, -0.03, 0.03, mat, M=M)


def build(length=900, seed=11):
    try:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    except Exception:
        pass
    scene = bpy.context.scene
    col = bpy.data.collections.get("Portal_Arena") or bpy.data.collections.new("Portal_Arena")
    if col.name not in scene.collection.children:
        scene.collection.children.link(col)
    r = random.Random(seed)
    M = {k: bpy.data.materials[f"GK_{k}"] for k in ("CorruptedStone", "RuneStone", "AncientDarkIron", "ChainIron", "WeatheredBronze", "DarkSteel")}
    crack = _mat_emit("Arena_CrackGlow", PURPLE, 5.0)
    glyph = _mat_emit("Arena_GlyphGlow", (0.3, 0.85, 1.0), 2.0)
    leak = _mat_emit("Arena_EnergyLeak", (0.85, 0.4, 1.0), 4.5)
    mote = _mat_emit("Arena_Mote", (0.7, 0.4, 1.0), 2.0)
    spire = _mat_emit("Arena_SpireGlow", (0.9, 0.35, 1.0), 8.0)
    portal = portal_material()

    # ---------------- floor: cracked slabs, broken and tilted away from the boss's footprint
    F = Boxes()
    for gx in range(-16, 16):
        for gy in range(-22, 15):
            x0, y0 = gx * 2, gy * 2
            if -10 < x0 < 9 and 7 < y0 < 13:
                continue                                   # steps go here
            near = abs(x0 + 1) < 9 and -14 < y0 + 1 < 8
            top = 0.0 if near else r.uniform(-0.12, 0.04)
            gap = 0.04 if near else r.uniform(0.03, 0.16)
            if not near and r.random() < 0.06:
                Mt = Matrix.Translation((x0 + 1, y0 + 1, top - 0.2)) @ Matrix.Rotation(math.radians(r.uniform(-9, 9)), 4, "X") @ Matrix.Rotation(math.radians(r.uniform(-9, 9)), 4, "Y")
                F.box(-1 + gap, 1 - gap, -1 + gap, 1 - gap, -0.3, 0.3, M["CorruptedStone"], M=Mt)
            else:
                F.box(x0 + gap, x0 + 2 - gap, y0 + gap, y0 + 2 - gap, top - 0.6, top, M["CorruptedStone"])
    F.box(-34, 34, -46, 32, -1.6, -0.55, M["CorruptedStone"])
    for i, (z0, y0) in enumerate(((0, 7.2), (0.5, 8.6), (1.0, 10.0))):       # portal steps
        F.box(-10 + i * 0.6, 10 - i * 0.6, y0, 13.0, z0 - 0.4, z0 + 0.5, M["RuneStone"] if i == 1 else M["CorruptedStone"])
    F.make("Arena_Floor", col)

    # ---------------- glowing fissures running from the portal toward the player
    C = Boxes()
    for k in range(9):
        p = Vector((r.uniform(-5, 5), 7.0, 0.0)); d = Vector((r.uniform(-0.5, 0.5), -1, 0)).normalized()
        for s in range(r.randint(14, 26)):
            d = (d + Vector((r.uniform(-0.6, 0.6), r.uniform(-0.2, 0.1), 0))).normalized()
            q = p + d * r.uniform(0.6, 1.4)
            c = (p + q) / 2; dd = (q - p)
            ang = math.atan2(dd.y, dd.x)
            Mt = Matrix.Translation((c.x, c.y, 0.005)) @ Matrix.Rotation(ang, 4, "Z")
            C.box(-dd.length / 2, dd.length / 2, -0.05, 0.05, -0.02, 0.03, crack, M=Mt)
            p = q
            if p.y < -30:
                break
    for i in range(8):                                               # ring of ancient floor glyphs
        a = 2 * math.pi * i / 8; cx, cy = 11 * math.cos(a), 11 * math.sin(a) - 1
        g = L.GLYPHS[i % 6]
        for row, line in enumerate(g):
            for col_, ch in enumerate(line):
                if ch == "#":
                    x = cx + (col_ - 2) * 0.24; y = cy + (3 - row) * 0.24
                    C.box(x - 0.11, x + 0.11, y - 0.11, y + 0.11, -0.01, 0.02, glyph)
    C.make("Arena_Fissures_Glyphs", col)

    # ---------------- the portal gateway
    G = Boxes()
    for s in (-1, 1):
        x0, x1 = sorted((6 * s, 10 * s))
        G.box(x0, x1, 12, 16, 0, 20, M["RuneStone"])
        G.box(x0 - 0.6, x1 + 0.6, 11.4, 16.6, 0, 1.6, M["CorruptedStone"])
        G.box(x0 - 0.5, x1 + 0.5, 11.5, 16.5, 19, 21, M["AncientDarkIron"])
        a, b = sorted((7.2 * s, 8.8 * s))
        G.box(a, b, 13.2, 14.8, 21, 26, M["CorruptedStone"])
        G.box(a + 0.3, b - 0.3, 13.5, 14.5, 26, 28.5, M["DarkSteel"])
        G.box(a + 0.45, b - 0.45, 13.65, 14.35, 28.5, 29.3, spire)
        a, b = sorted((5.2 * s, 6.0 * s))
        G.box(a, b, 13.3, 14.7, 0, 19.2, M["RuneStone"])
        for z in (4, 9, 14):                                         # broken chunks bitten out of the frame edge
            G.box(*sorted((9.6 * s, 10.4 * s)), 11.8, 12.6, z, z + r.uniform(0.6, 1.4), M["CorruptedStone"])
    G.box(-10.5, 10.5, 11.5, 16.5, 20, 23.5, M["CorruptedStone"])
    G.box(-6, 6, 13.3, 14.7, 18.4, 19.2, M["RuneStone"])
    G.box(-7, 7, 12, 16, 23.5, 25.5, M["RuneStone"])
    G.box(-4, 4, 12.6, 15.4, 25.5, 28, M["AncientDarkIron"])
    G.box(-1, 1, 13.2, 14.8, 28, 33, M["DarkSteel"])
    G.box(-2.5, 2.5, 13.6, 14.4, 31, 31.6, spire)
    G.box(-0.6, 0.6, 13.4, 14.6, 33, 34.2, spire)
    for x in (-8, -4.5, 4.5, 8):                                     # chains hanging from the lintel
        chain_curve(G, (x, 11.4, 20), (x + r.uniform(-0.3, 0.3), 11.3, 20 - r.uniform(3, 6.5)), 0.05, M["ChainIron"])
    G.make("Arena_PortalGate", col)
    S = Boxes()
    S.box(-5.2, 5.2, 13.95, 14.05, 0.2, 18.4, portal)
    S.make("Arena_PortalSurface", col)

    vortex = bpy.data.objects.new("Arena_PortalVortex", None)
    col.objects.link(vortex); vortex.location = (0, 13.7, 9.4)
    for ring, (rad, n, spd) in enumerate(((1.6, 14, 1), (3.0, 22, -1), (4.4, 30, 1))):
        piv = bpy.data.objects.new(f"Arena_VortexRing{ring}", None); col.objects.link(piv); piv.parent = vortex
        for i in range(n):
            a = 2 * math.pi * i / n
            c = _cube_obj(f"Arena_VortexCube{ring}_{i}", r.uniform(0.08, 0.2), leak, col)
            c.parent = piv; c.location = (rad * math.cos(a), r.uniform(-0.3, 0.3), rad * math.sin(a) * 1.5)
        _key(piv, 0, rot=(0, 0, 0)); _key(piv, length, rot=(0, spd * 2 * math.pi * length / 300, 0))

    # ---------------- rune pillars (some broken), chains between them and the gate
    P = Boxes()
    pillars = [(-15, -4, 12), (15, -4, 11), (-17, 8, 15), (17, 8, 14), (-12, -18, 7), (12, -18, 9.5)]
    for i, (x, y, h) in enumerate(pillars):
        P.box(x - 1.2, x + 1.2, y - 1.2, y + 1.2, 0, h, M["RuneStone"])
        P.box(x - 1.6, x + 1.6, y - 1.6, y + 1.6, 0, 1.0, M["CorruptedStone"])
        if h > 10:
            P.box(x - 1.5, x + 1.5, y - 1.5, y + 1.5, h, h + 0.8, M["AncientDarkIron"])
        else:                                                        # broken top + fallen chunks
            for k in range(4):
                a = r.uniform(0, 2 * math.pi); d = r.uniform(2, 4); sz = r.uniform(0.4, 1.0)
                P.box(x + d * math.cos(a) - sz, x + d * math.cos(a) + sz, y + d * math.sin(a) - sz, y + d * math.sin(a) + sz, 0, sz * 1.4, M["RuneStone"])
        P.box(x - 0.3, x + 0.3, y - 1.25, y - 1.2, h * 0.5, h * 0.66, glyph)
    for (a, b, sag) in (((-15, -4, 11.6), (-8, 12, 19.5), 2.5), ((15, -4, 10.6), (8, 12, 19.5), 2.5), ((-17, 8, 14.6), (-9.6, 13, 20.5), 1.5),
                        ((17, 8, 13.6), (9.6, 13, 20.5), 1.5), ((-15, -4, 11.6), (-17, 8, 14.6), 2.0), ((15, -4, 10.6), (17, 8, 13.6), 2.0)):
        chain_curve(P, a, b, sag, M["ChainIron"])
    for k in range(30):                                              # rubble
        a = r.uniform(0, 2 * math.pi); d = r.uniform(9, 26); sz = r.uniform(0.25, 0.9)
        x, y = d * math.cos(a), d * math.sin(a) - 2
        if abs(x) < 6 and -20 < y < 6:
            continue
        P.box(x - sz, x + sz, y - sz * 0.8, y + sz * 0.8, -0.05, sz * 1.1, M["CorruptedStone"])
    P.make("Arena_Pillars_Chains_Rubble", col)

    # ---------------- floating debris (slow bob and tumble)
    for i in range(46):
        sz = r.uniform(0.15, 0.7)
        o = _cube_obj(f"Arena_Debris{i}", sz, M["CorruptedStone"] if i % 4 else M["RuneStone"], col)
        p = Vector((r.uniform(-20, 20), r.uniform(-8, 22), r.uniform(2.5, 17)))
        if abs(p.x) < 5 and p.y < 6:
            p.x += 8 * (1 if p.x >= 0 else -1)
        ph = r.uniform(0, 6.28); amp = r.uniform(0.25, 0.7); rs = Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1)))
        for k in range(0, length + 1, length // 6):
            t = k / length * 2 * math.pi
            _key(o, k, loc=(p.x, p.y, p.z + amp * math.sin(t * 2 + ph)), rot=tuple(rs * (t * 0.6)))

    # ---------------- purple energy leaking out of the portal toward the player
    for i in range(45):
        o = _cube_obj(f"Arena_Leak{i}", r.uniform(0.03, 0.08), leak, col)
        life = r.randint(70, 140); off = r.randrange(life)
        for n in range(-1, length // life + 2):
            t0 = off + n * life
            a = Vector((r.uniform(-4.5, 4.5), 13.6, r.uniform(0.5, 16)))
            b = Vector((a.x * 1.6 + r.uniform(-3, 3), r.uniform(-10, 4), r.uniform(0.1, 1.2)))
            mid = a.lerp(b, 0.5) + Vector((0, 0, r.uniform(-1, 1.5)))
            _key(o, t0, loc=tuple(a), sc=0.0); _key(o, t0 + life * 0.15, loc=tuple(a.lerp(mid, 0.3)), sc=1.0)
            _key(o, t0 + life * 0.6, loc=tuple(mid), sc=1.0); _key(o, t0 + life - 1, loc=tuple(b), sc=0.0)
    for i in range(90):                                               # slow floating motes around the guardian
        o = _cube_obj(f"Arena_Mote{i}", r.uniform(0.025, 0.06), mote, col)
        p = Vector((r.uniform(-9, 9), r.uniform(-8, 10), r.uniform(0.3, 9))); ph = r.uniform(0, 6.28)
        for k in range(0, length + 1, length // 6):
            t = k / length * 2 * math.pi
            _key(o, k, loc=(p.x + 0.6 * math.sin(t + ph), p.y + 0.4 * math.cos(t * 1.3 + ph), p.z + 0.8 * math.sin(t * 0.7 + ph)))

    # ---------------- ground fog volume + world fog + lights
    fogm = bpy.data.materials.new("Arena_GroundFog"); fogm.use_nodes = True
    nt = fogm.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    pv = nt.nodes.new("ShaderNodeVolumePrincipled"); out = nt.nodes.new("ShaderNodeOutputMaterial")
    pv.inputs["Color"].default_value = (0.32, 0.18, 0.5, 1); pv.inputs["Density"].default_value = 0.11
    nt.links.new(pv.outputs[0], out.inputs["Volume"])
    FG = Boxes(); FG.box(-34, 34, -46, 30, 0, 1.6, fogm)
    FG.make("Arena_GroundFog", col)

    world = bpy.data.worlds.get("GK_World") or bpy.data.worlds.new("GK_World")
    scene.world = world; world.use_nodes = True
    wn = world.node_tree.nodes
    wn["Background"].inputs[0].default_value = (0.004, 0.002, 0.01, 1)
    for n in [n for n in wn if n.type == "VOLUME_SCATTER"]:
        wn.remove(n)
    vs = wn.new("ShaderNodeVolumeScatter")
    vs.inputs["Color"].default_value = (0.5, 0.3, 0.85, 1); vs.inputs["Density"].default_value = 0.012
    world.node_tree.links.new(vs.outputs[0], wn["World Output"].inputs["Volume"])

    def light(name, kind, energy, loc, color, size=4.0, rot_to=None):
        Ld = bpy.data.lights.new(name, kind); Ld.energy = energy; Ld.color = color
        if hasattr(Ld, "size"):
            Ld.size = size
        if kind == "AREA":
            Ld.shape = "RECTANGLE"; Ld.size = size; Ld.size_y = size * 1.4
        o = bpy.data.objects.new(name, Ld); col.objects.link(o); o.location = loc
        if rot_to is not None:
            o.rotation_euler = (Vector(rot_to) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return o

    lights = {
        "portal": light("Arena_PortalLight", "AREA", 16000, (0, 13.0, 9.4), (0.72, 0.35, 1.0), 10, (0, -10, 4)),
        "rimL": light("Arena_RimL", "SPOT", 9000, (-9, 10, 13), (0.55, 0.3, 1.0), 1, (0, 0, 5)),
        "rimR": light("Arena_RimR", "SPOT", 8000, (9, 10, 12), (0.45, 0.35, 1.0), 1, (0, 0, 5)),
        "moon": light("Arena_Moon", "SUN", 0.35, (0, -10, 20), (0.55, 0.6, 1.0), 1, (0, 0, 0)),
        "front": light("Arena_FrontFill", "AREA", 700, (0, -14, 4), (0.6, 0.5, 1.0), 8, (0, 0, 4)),
    }
    for k in ("rimL", "rimR"):
        lights[k].data.spot_size = math.radians(55); lights[k].data.spot_blend = 0.6
    return col, lights, portal
