"""Shared library for the Ancient Gatekeeper build: textures, materials, mesh builder, skeleton, pose tools.
Units: design in Minecraft pixels (16 px = 1 block = 1 metre). Character faces -Y, Z up, ground at Z = 0."""
import bpy, bmesh, math, os, random
from mathutils import Matrix, Vector, Euler, Quaternion

PX = 1.0 / 16.0
CYAN = (0.30, 0.92, 1.0)
PURPLE = (0.74, 0.30, 1.0)
MAGENTA = (1.0, 0.24, 0.74)
HOT = (0.97, 0.82, 1.0)

GLYPHS = [
    ["#####", "#....", "#.###", "#...#", "###.#", "....#", "#####"],
    ["#.#.#", "#.#.#", "#####", "..#..", "..#..", "#####", "#...#"],
    ["###..", "..#..", "#####", "#...#", "#.#.#", "#.#..", "###.."],
    ["..#..", "#####", "#.#.#", "#####", "..#..", "..#..", ".###."],
    ["#.###", "#.#..", "#.###", "#...#", "#####", "..#..", "..#.."],
    ["#####", "#...#", "#.#.#", "#.#.#", "#...#", "#.###", "#...."],
]
EYE = ["#####", "..#..", "#.#.#", "..#..", "..#.."]


def clamp(v):
    return max(0.0, min(1.0, v))


def jit(c, a, r):
    d = (r.random() - 0.5) * a
    return tuple(clamp(x + d) for x in c)


# ------------------------------------------------------------------ pixel-art texture painters (64x64 tiles)
def walk_cracks(r, n, size=64, steps=14):
    out = set()
    for _ in range(n):
        x, y = r.randrange(size), r.randrange(size)
        for _ in range(steps):
            out.add((x % size, y % size))
            x += r.choice((-1, 0, 1)); y += r.choice((-1, 1, 1))
    return out


def p_stone(seed):
    r = random.Random(seed)
    base = (0.19, 0.16, 0.23)
    cracks = walk_cracks(r, 7)
    veins = walk_cracks(r, 3, steps=20)
    def p(x, y):
        row = y // 8
        bx = (x + (row % 2) * 8) % 16
        if y % 8 == 7 or bx == 0:
            return jit((0.06, 0.045, 0.08), 0.02, r), None
        if y % 8 == 0 or bx == 1:
            return jit((0.29, 0.25, 0.33), 0.04, r), None            # worn brick edge
        if (x, y) in veins:
            return jit((0.33, 0.10, 0.38), 0.05, r), None            # corruption veins
        if (x, y) in cracks:
            return (0.07, 0.05, 0.09), None
        return jit(base, 0.06, r), None
    return p


def p_runestone(seed):
    r = random.Random(seed)
    st = p_stone(seed + 1)
    g = {}
    for i, (gx, gy) in enumerate(((4, 4), (26, 10), (46, 3), (10, 30), (34, 36), (52, 28), (18, 52), (44, 54))):
        col = CYAN if r.random() < 0.22 else PURPLE
        for row, line in enumerate(GLYPHS[(seed + i) % 6]):
            for c, ch in enumerate(line):
                if ch == "#":
                    g[(gx + c, gy + row)] = col
    def p(x, y):
        if (x, y) in g:
            return g[(x, y)], g[(x, y)]
        return st(x, y)
    return p


def p_iron(seed):
    r = random.Random(seed)
    base = (0.17, 0.17, 0.19)
    scratches = set()
    for _ in range(14):
        x, y, L = r.randrange(64), r.randrange(64), r.randint(4, 11)
        for i in range(L):
            scratches.add(((x + i) % 64, (y + i // 2) % 64))
    pits = {(r.randrange(64), r.randrange(64)) for _ in range(50)}
    rust = [(r.uniform(0, 64), r.uniform(0, 64), r.uniform(2, 4.5)) for _ in range(4)]
    def p(x, y):
        lx, ly = x % 32, y % 32
        if lx == 0 or ly == 0:
            return jit((0.06, 0.06, 0.07), 0.02, r), None            # plate seam
        if lx == 1 or ly == 1 or lx == 31 or ly == 31:
            return jit((0.36, 0.35, 0.38), 0.05, r), None            # edge wear
        if (lx, ly) in ((4, 4), (27, 4), (4, 27), (27, 27)):
            return (0.42, 0.40, 0.42), None                          # rivets
        if (lx, ly) in ((4, 5), (27, 5), (4, 28), (27, 28)):
            return (0.05, 0.05, 0.06), None
        if (x, y) in scratches:
            return jit((0.33, 0.33, 0.36), 0.04, r), None
        for cx, cy, cr in rust:
            if (x - cx) ** 2 + (y - cy) ** 2 < cr * cr:
                return jit((0.24, 0.13, 0.08), 0.05, r), None
        if (x, y) in pits:
            return (0.08, 0.08, 0.09), None
        return jit(base, 0.04, r), None
    return p


def p_bronze(seed):
    r = random.Random(seed)
    verd = [(r.uniform(0, 64), r.uniform(0, 64), r.uniform(3, 7)) for _ in range(6)]
    def p(x, y):
        if x % 16 == 0 or y % 16 == 0:
            return jit((0.14, 0.10, 0.06), 0.03, r), None
        if x % 16 == 1 or y % 16 == 1:
            return jit((0.62, 0.47, 0.26), 0.05, r), None            # polished worn edge
        for cx, cy, cr in verd:
            if (x - cx) ** 2 + (y - cy) ** 2 < cr * cr * (0.6 + 0.4 * r.random()):
                return jit((0.22, 0.40, 0.34), 0.06, r), None        # verdigris
        if r.random() < 0.06:
            return jit((0.18, 0.13, 0.08), 0.03, r), None            # grime
        return jit((0.38, 0.28, 0.16), 0.05, r), None
    return p


def p_steel(seed):
    r = random.Random(seed)
    nicks = {(r.randrange(64), r.randrange(64)) for _ in range(40)}
    def p(x, y):
        if (x, y) in nicks:
            return jit((0.52, 0.55, 0.62), 0.05, r), None
        s = 0.03 * math.sin(y * 1.7 + r.random() * 0.4)
        return jit((0.19 + s, 0.21 + s, 0.26 + s), 0.03, r), None   # brushed streaks
    return p


def p_cloth(seed):
    r = random.Random(seed)
    def p(x, y):
        if r.random() < 0.01:
            return PURPLE, PURPLE
        if x % 6 == 0:
            return jit((0.04, 0.02, 0.06), 0.02, r), None
        if (x + y // 3) % 13 == 0:
            return jit((0.15, 0.08, 0.20), 0.03, r), None
        if y % 21 == 0 and r.random() < 0.5:
            return jit((0.03, 0.02, 0.04), 0.01, r), None            # frayed holes
        return jit((0.085, 0.05, 0.115), 0.03, r), None
    return p


def p_solid(c, seed, glow):
    r = random.Random(seed)
    def p(x, y):
        cc = jit(c, 0.12, r)
        return cc, (cc if glow else None)
    return p


MATDEFS = {
    # name: (painter, metallic, roughness, emission strength or 0, solid emissive colour)
    "CorruptedStone": (p_stone(1), 0.0, 0.92, 0, None),
    "RuneStone": (p_runestone(2), 0.0, 0.9, 1.6, None),
    "AncientDarkIron": (p_iron(3), 0.75, 0.55, 0, None),
    "WeatheredBronze": (p_bronze(4), 0.8, 0.5, 0, None),
    "DarkSteel": (p_steel(5), 0.85, 0.38, 0, None),
    "TatteredCloth": (p_cloth(6), 0.0, 0.95, 1.0, None),
    "ChainIron": (p_iron(7), 0.8, 0.5, 0, None),
    "PurpleEnergy": (p_solid(PURPLE, 8, True), 0.0, 0.4, 4.0, PURPLE),
    "CyanRunes": (p_solid(CYAN, 9, True), 0.0, 0.4, 3.5, CYAN),
    "MagentaFragments": (p_solid(MAGENTA, 10, True), 0.0, 0.4, 5.0, MAGENTA),
    "EyeGlow": (p_solid(HOT, 11, True), 0.0, 0.3, 16.0, HOT),          # eyes + core: the focal point
    "FireEnergy": (p_solid((0.82, 0.36, 1.0), 12, True), 0.0, 0.4, 6.0, PURPLE),
}


def make_materials(tex_dir):
    os.makedirs(tex_dir, exist_ok=True)
    mats = {}
    for name, (painter, metal, rough, emit, solid) in MATDEFS.items():
        alb = bpy.data.images.new(f"GK_{name}_Albedo", 64, 64, alpha=False)
        emi = bpy.data.images.new(f"GK_{name}_Emission", 64, 64, alpha=False)
        pa, pe = [], []
        for y in range(64):
            for x in range(64):
                c, g = painter(x, y)
                pa += [c[0], c[1], c[2], 1.0]
                pe += ([g[0], g[1], g[2], 1.0] if g else [0, 0, 0, 1.0])
        alb.pixels = pa; emi.pixels = pe
        for im in (alb, emi):
            im.filepath_raw = os.path.join(tex_dir, im.name + ".png"); im.file_format = "PNG"; im.save()
        m = bpy.data.materials.new(f"GK_{name}")
        m.use_nodes = True
        nt = m.node_tree
        b = nt.nodes["Principled BSDF"]
        b.inputs["Metallic"].default_value = metal
        b.inputs["Roughness"].default_value = rough
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = alb; t.interpolation = "Closest"
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        if emit:
            e = nt.nodes.new("ShaderNodeTexImage"); e.image = emi; e.interpolation = "Closest"
            nt.links.new(e.outputs["Color"], b.inputs["Emission Color"])
            b.inputs["Emission Strength"].default_value = emit
        m["gk_emission_strength"] = emit
        mats[name] = m
    return mats


# ------------------------------------------------------------------ skeleton (pixel coordinates)
def _v(*a):
    return Vector(a)


def bone_specs():
    B = []  # (name, head, tail, parent, deform)
    add = lambda n, h, t, p, d=True: B.append((n, _v(*h), _v(*t), p, d))
    add("root", (0, 0, 0), (0, -12, 0), None)
    add("hips", (0, 0, 46), (0, 0, 54), "root")
    add("spine", (0, 0, 54), (0, 0, 66), "hips")
    add("chest", (0, 0, 66), (0, 0, 86), "spine")
    add("neck", (0, -1, 86), (0, -1, 91), "chest")
    add("head", (0, -1, 91), (0, -1, 108), "neck")
    for s, S in ((1, "L"), (-1, "R")):
        add(f"thigh_{S}", (8 * s, 0, 46), (9 * s, -1, 28), "hips")
        add(f"shin_{S}", (9 * s, -1, 28), (9 * s, 0, 7), f"thigh_{S}")
        add(f"foot_{S}", (9 * s, 0, 7), (9 * s, -10, 3), f"shin_{S}")
        add(f"robe_{S}", (14 * s, 0, 46), (19 * s, 0, 8), "hips")
        # main (lower) arms
        d = Vector((0.5 * s, 0, -0.866))
        add(f"clavicle_{S}", (9 * s, 0, 70), (17 * s, 0, 69), "chest")
        up_h = Vector((19 * s, 0, 68)); fo_h = up_h + d * 20; ha_h = fo_h + d * 18; ha_t = ha_h + d * 9
        add(f"upperarm_{S}", up_h, fo_h, f"clavicle_{S}")
        add(f"forearm_{S}", fo_h, ha_h, f"upperarm_{S}")
        add(f"hand_{S}", ha_h, ha_t, f"forearm_{S}")
        for k in range(3):
            fh = ha_t + Vector((0, (k - 1) * 3.6, 0))
            add(f"finger{k + 1}_{S}", fh, fh + d * 8, f"hand_{S}")
        th = ha_h + d * 4 + Vector((-1.5 * s, -5.5, 0))
        add(f"thumb_{S}", th, th + d * 4 + Vector((0, -3, 0)), f"hand_{S}")
        sk = ha_h + d * 5
        add(f"socket_hand_{S}", sk, sk + d * 3, f"hand_{S}")
        if S == "R":
            add("weapon", sk + Vector((1.2, 0, 0)), sk + Vector((1.2, -12, 0)), "socket_hand_R")
        # extra (upper) arms
        e = Vector((0.71 * s, 0, -0.71)).normalized()
        add(f"clavicle_extra_{S}", (11 * s, 0, 86), (24 * s, 0, 88), "chest")
        eu = Vector((26 * s, 0, 86)); ef = eu + e * 22; eh = ef + e * 20; et = eh + e * 9
        add(f"upperarm_extra_{S}", eu, ef, f"clavicle_extra_{S}")
        add(f"forearm_extra_{S}", ef, eh, f"upperarm_extra_{S}")
        add(f"hand_extra_{S}", eh, et, f"forearm_extra_{S}")
        for k in range(3):
            fh = et + Vector((0, (k - 1) * 3.2, 0))
            add(f"finger{k + 1}_extra_{S}", fh, fh + e * 9, f"hand_extra_{S}")
        th = eh + e * 4 + Vector((-1.5 * s, -5, 0))
        add(f"thumb_extra_{S}", th, th + e * 5 + Vector((0, -3, 0)), f"hand_extra_{S}")
        add(f"fx_fire_{S}", et + e * 9, et + e * 15, f"hand_extra_{S}")
        add(f"socket_extra_{S}", eh + e * 4, eh + e * 7, f"hand_extra_{S}")
    add("robe_F", (0, -11, 46), (0, -13, 10), "hips")
    add("robe_B", (0, 11, 46), (0, 15, 8), "hips")
    # chain bones so the hanging chains swing on their own
    add("chain_chest", (0, -13, 66.5), (0, -13, 56), "chest")
    add("chain_belt", (0, -13.3, 44), (0, -13.3, 30), "hips")
    for s, S in ((1, "L"), (-1, "R")):
        add(f"chain_shoulder_{S}", (25 * s, -13.6, 72), (25 * s, -13.6, 54), f"clavicle_extra_{S}")
        add(f"chain_shoulder_back_{S}", (24 * s, 12.8, 72), (24 * s, 12.8, 58), f"clavicle_extra_{S}")
    return B


def build_armature(collection):
    arm = bpy.data.armatures.new("Gatekeeper_Rig")
    ob = bpy.data.objects.new("Gatekeeper_Rig", arm)
    collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for name, h, t, parent, deform in bone_specs():
        eb = arm.edit_bones.new(name)
        eb.head = h * PX; eb.tail = t * PX
        eb.use_deform = deform
        if parent:
            eb.parent = arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.display_type = "STICK"
    ob.show_in_front = True
    return ob


def bone_px_matrix(rig, name):
    """Rest matrix of a bone mapped to pixel space (local px coords -> armature px coords)."""
    M = rig.data.bones[name].matrix_local.copy()
    M.translation = M.translation * 16.0
    return M


# ------------------------------------------------------------------ mesh builder
class Builder:
    FACES = {  # vertex indices (of the 8 box corners), uv axes
        "front": ((0, 1, 5, 4), "xz"), "back": ((2, 3, 7, 6), "xz"), "left": ((3, 0, 4, 7), "yz"),
        "right": ((1, 2, 6, 5), "yz"), "top": ((4, 5, 6, 7), "xy"), "bottom": ((3, 2, 1, 0), "xy"),
    }
    WORLD_DIR = {"front": Vector((0, -1, 0)), "back": Vector((0, 1, 0)), "left": Vector((-1, 0, 0)),
                 "right": Vector((1, 0, 0)), "top": Vector((0, 0, 1)), "bottom": Vector((0, 0, -1))}

    def __init__(self, mats):
        self.mats = mats
        self.objs = {}
        self.r = random.Random(77)

    def _o(self, key):
        if key not in self.objs:
            self.objs[key] = dict(v=[], f=[], uv=[], fm=[], mats=[], vg=[], bev=[])
        return self.objs[key]

    def box(self, obj, bone, x0, x1, y0, y1, z0, z1, mat, M=None, faces=None, bevel=False):
        """Box in local px coords; M maps local px -> armature px. faces={'front': mat} overrides by WORLD facing."""
        o = self._o(obj)
        faces = faces or {}
        C = [Vector((x0, y0, z0)), Vector((x1, y0, z0)), Vector((x1, y1, z0)), Vector((x0, y1, z0)),
             Vector((x0, y0, z1)), Vector((x1, y0, z1)), Vector((x1, y1, z1)), Vector((x0, y1, z1))]
        L = [c.copy() for c in C]
        if M is not None:
            C = [M @ c for c in C]
        base = len(o["v"])
        o["v"] += [tuple(c * PX) for c in C]
        o["vg"] += [bone] * 8
        o["bev"] += [bevel] * 8
        ou, ov = self.r.randrange(64), self.r.randrange(64)
        for key, (idx, ax) in self.FACES.items():
            m = mat
            if faces:
                n = (C[idx[1]] - C[idx[0]]).cross(C[idx[3]] - C[idx[0]]).normalized()
                best = max(self.WORLD_DIR, key=lambda k: n.dot(self.WORLD_DIR[k]))
                if best in faces and n.dot(self.WORLD_DIR[best]) > 0.6:
                    m = faces[best]
            if m not in o["mats"]:
                o["mats"].append(m)
            o["f"].append(tuple(base + i for i in idx))
            o["fm"].append(o["mats"].index(m))
            a, b = {"xz": (0, 2), "yz": (1, 2), "xy": (0, 1)}[ax]
            o["uv"].append([((L[i][a] - min(x0, x1, y0, y1, z0, z1) * 0 + ou) / 64.0, (L[i][b] + ov) / 64.0) for i in idx])

    def finish(self, rig, colls):
        made = []
        for (coll, name), o in self.objs.items():
            me = bpy.data.meshes.new(name)
            me.from_pydata(o["v"], [], o["f"])
            me.update()
            lay = me.uv_layers.new(name="UVMap")
            for poly, uvs in zip(me.polygons, o["uv"]):
                for li, uv in zip(poly.loop_indices, uvs):
                    lay.data[li].uv = uv
            for mn in o["mats"]:
                me.materials.append(self.mats[mn])
            for poly, mi in zip(me.polygons, o["fm"]):
                poly.material_index = mi
            bw = me.attributes.new("bevel_weight_edge", "FLOAT", "EDGE")
            for e in me.edges:
                a, b = e.vertices
                bw.data[e.index].value = 1.0 if (o["bev"][a] and o["bev"][b]) else 0.0
            ob = bpy.data.objects.new(name, me)
            colls[coll].objects.link(ob)
            groups = {}
            for i, bn in enumerate(o["vg"]):
                groups.setdefault(bn, []).append(i)
            for bn, idx in groups.items():
                ob.vertex_groups.new(name=bn).add(idx, 1.0, "REPLACE")
            if any(o["bev"]):
                bv = ob.modifiers.new("Bevel", "BEVEL")
                bv.limit_method = "WEIGHT"; bv.width = 0.35 * PX; bv.segments = 1; bv.harden_normals = False
            am = ob.modifiers.new("Armature", "ARMATURE"); am.object = rig
            ob.parent = rig
            made.append(ob)
        return made


def glyph(B, obj, bone, glyph_rows, origin, right, up, out, px=1.0, depth=0.6, mat="PurpleEnergy", M=None, hot_top=None):
    """Raised rune strokes: rows of '#' merged into bars. origin = top-left corner on the surface (px),
    right/up/out = unit axes (in the frame M maps from)."""
    right, up, out = Vector(right), Vector(up), Vector(out)
    for row, line in enumerate(glyph_rows):
        c = 0
        while c < len(line):
            if line[c] != "#":
                c += 1; continue
            s = c
            while c < len(line) and line[c] == "#":
                c += 1
            p0 = Vector(origin) + right * (s * px) - up * ((row + 1) * px)
            p1 = p0 + right * ((c - s) * px) + up * px + out * depth
            lo = Vector([min(a, b) for a, b in zip(p0, p1)]); hi = Vector([max(a, b) for a, b in zip(p0, p1)])
            m = hot_top if (hot_top and row == 0) else mat
            B.box(obj, bone, lo.x, hi.x, lo.y, hi.y, lo.z, hi.z, m, M=M)


# ------------------------------------------------------------------ pose tools
def rest3(pb):
    return pb.bone.matrix_local.to_3x3()


def reset_pose(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def set_delta(rig, name, rot_deg=(0, 0, 0), loc_px=(0, 0, 0)):
    """Rotation about armature axes (through the bone's rest frame) and location offset in armature px."""
    pb = rig.pose.bones[name]
    R3 = rest3(pb)
    Rw = Euler(tuple(math.radians(a) for a in rot_deg), "XYZ").to_matrix()
    pb.rotation_quaternion = (R3.inverted() @ Rw @ R3).to_quaternion()
    pb.location = R3.inverted() @ (Vector(loc_px) * PX)
    bpy.context.view_layer.update()


def bone_dir(rig, name):
    pb = rig.pose.bones[name]
    return (pb.matrix.to_3x3() @ Vector((0, 1, 0))).normalized()


def aim(rig, name, direction, twist=0.0):
    pb = rig.pose.bones[name]
    d = Vector(direction).normalized()
    cur = pb.matrix.to_3x3()
    q = (cur @ Vector((0, 1, 0))).rotation_difference(d)
    new = q.to_matrix() @ cur
    if twist:
        new = Matrix.Rotation(math.radians(twist), 3, d) @ new
    M = new.to_4x4(); M.translation = pb.matrix.translation
    pb.matrix = M
    bpy.context.view_layer.update()


def orient(rig, name, direction, normal_hint):
    """Full orientation: bone Y along direction, bone Z as close as possible to normal_hint."""
    pb = rig.pose.bones[name]
    y = Vector(direction).normalized()
    z = Vector(normal_hint); z = (z - y * z.dot(y)).normalized()
    x = y.cross(z)
    M = Matrix((x, y, z)).transposed().to_4x4()
    M.translation = pb.matrix.translation
    pb.matrix = M
    bpy.context.view_layer.update()


def head_px(rig, name):
    return rig.pose.bones[name].head * 16.0


def tail_px(rig, name):
    return rig.pose.bones[name].tail * 16.0


def solve_leg(rig, S, target_px, pole=Vector((0, -1, 0)), foot_pitch=0.0):
    hip = head_px(rig, f"thigh_{S}")
    l1 = (rig.data.bones[f"thigh_{S}"].length) * 16.0
    l2 = (rig.data.bones[f"shin_{S}"].length) * 16.0
    T = Vector(target_px)
    D = T - hip
    d = min(max(D.length, abs(l1 - l2) + 0.01), l1 + l2 - 0.01)
    u = D.normalized()
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    v = (pole - u * pole.dot(u)).normalized()
    knee = hip + u * a + v * h
    ankle = hip + u * d
    aim(rig, f"thigh_{S}", knee - hip)
    aim(rig, f"shin_{S}", ankle - knee)
    rest = rig.data.bones[f"foot_{S}"].matrix_local.to_3x3()
    R = Matrix.Rotation(math.radians(foot_pitch), 3, "X")
    orient(rig, f"foot_{S}", R @ (rest @ Vector((0, 1, 0))), R @ (rest @ Vector((0, 0, 1))))   # keep the sole flat (no roll)


def body_rot(rig):
    pb = rig.pose.bones["chest"]
    return pb.matrix.to_3x3() @ pb.bone.matrix_local.to_3x3().inverted()
