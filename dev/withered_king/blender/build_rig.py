"""Build the Withered King rig (v2 skeleton) in Blender from king_data.json:
deform bones with the exact Blockbench names, one textured mesh skinned rigidly to them,
IK controls for feet and hands with pole targets, widgets, a QC camera and ground grid."""
import bpy, sys, os, math
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bbmath as BM
from bbmath import gp, D, BONES, WREST, G

HERE = BM.HERE
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
sc = bpy.context.scene
sc.render.fps = 20; sc.frame_start = 0; sc.frame_end = 80

def wpt(bone, p):          # bb point in a bone's model space -> bb rest world
    return (WREST[bone] @ Vector((p[0], p[1], p[2], 1))).xyz

# ---------------------------------------------------------------- armature
arm = bpy.data.armatures.new('Sentinel_Armature'); arm.display_type = 'OCTAHEDRAL'
rig = bpy.data.objects.new('Sentinel_Rig', arm); sc.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig; rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
heads = {n: Vector(b['head']) for n, b in BONES.items()}
TAIL = {'body': heads['waist'], 'waist': heads['chest'], 'chest': heads['head'],
        'right_arm': heads['right_forearm'], 'right_forearm': heads['right_hand'], 'right_hand': heads['sword'],
        'left_arm': heads['left_forearm'], 'left_forearm': heads['left_hand'],
        'right_leg': heads['right_shin'], 'right_shin': heads['right_foot'], 'left_leg': heads['left_shin'], 'left_shin': heads['left_foot'],
        'cape': heads['cape_mid_low'], 'cape_mid': heads['cape_mid_low'], 'cape_left': heads['cape_left_low'], 'cape_right': heads['cape_right_low'],
        'neck': heads['head'], 'right_clavicle': heads['right_arm'], 'left_clavicle': heads['left_arm']}
for k in range(4): TAIL[f'left_finger{k}'] = heads[f'left_finger{k}'] + Vector((0, -4.0, 0))
TAIL['left_thumb'] = heads['left_thumb'] + Vector((0, -3.0, -0.3))
TAIL['right_fingers'] = heads['right_fingers'] + Vector((0, -3.0, 0))
TAIL['right_thumb'] = heads['right_thumb'] + Vector((0, -1.6, -0.2))
TAIL['crown'] = heads['crown'] + Vector((0, 6.0, 0))
TAIL['right_foot'] = wpt('right_foot', D['foot']['right']['toe']); TAIL['left_foot'] = wpt('left_foot', D['foot']['left']['toe'])
TAIL['sword'] = wpt('sword', (D['sword']['grip'][0], D['sword']['grip'][1], D['sword']['grip'][2] - 41.8))
TAIL['left_hand'] = wpt('left_hand', (BONES['left_hand']['pivot'][0], BONES['left_hand']['pivot'][1] - 6, BONES['left_hand']['pivot'][2]))
def tail_of(n):
    if n in TAIL: return TAIL[n]
    h = heads[n]
    return {'root': h + Vector((0, 0, -6)), 'head': h + Vector((0, 10, 0)), 'jaw': h + Vector((0, -3, -4)), 'skirt': h + Vector((0, -10, 0)),
            'hood_drape': h + Vector((0, -8, 0.5)), 'banner': h + Vector((0, -11, 0)), 'drape_left': h + Vector((0, -8, 0)), 'drape_right': h + Vector((0, -8, 0)),
            'tabard_front': h + Vector((0, -24, -0.5)), 'tabard_back': h + Vector((0, -28, 0.5)), 'tabard_right': h + Vector((0.5, -20, 0)), 'tabard_left': h + Vector((-0.5, -20, 0))}.get(n, h + Vector((0, -16, 0)))
eb = {}
for n in BM.ORDER:
    e = arm.edit_bones.new(n); e.head = gp(heads[n]); e.tail = gp(tail_of(n))
    if (e.tail - e.head).length < 0.05: e.tail = e.head + Vector((0, 0, 0.5))
    d = (e.tail - e.head).normalized()
    e.align_roll(Vector((0, 0, 1)) if abs(d.y) > 0.7 else Vector((0, -1, 0)))
    e.use_deform = True; eb[n] = e
for n, b in BONES.items():
    if b['parent']: eb[n].parent = eb[b['parent']]
def ctrl(name, like, parent, offset=None):
    e = arm.edit_bones.new(name); src = eb[like]
    e.head = src.head.copy(); e.tail = src.tail.copy(); e.roll = src.roll
    if offset is not None: e.head = src.head + offset; e.tail = e.head + Vector((0, 0, 0.6)); e.roll = 0
    e.parent = eb[parent]; e.use_deform = False; return e
for s, sx in (('R', 'right'), ('L', 'left')):
    ctrl(f'IK_foot.{s}', f'{sx}_foot', 'root')
    ctrl(f'POLE_knee.{s}', f'{sx}_shin', 'body', offset=gp(heads[f'{sx}_shin'] + Vector((0, 0, -30))) - gp(heads[f'{sx}_shin']))
    ctrl(f'IK_hand.{s}', f'{sx}_hand', 'root')
    t = arm.edit_bones.new(f'TWIST.{s}'); t.head = eb['root'].head + Vector((0.8 if s == 'L' else -0.8, 0.8, 0)); t.tail = t.head + Vector((0, 0.6, 0))
    t.parent = eb['root']; t.use_deform = False
    Sh, El, Wr = heads[f'{sx}_arm'], heads[f'{sx}_forearm'], heads[f'{sx}_hand']
    ax = (Wr - Sh).normalized(); Cc = Sh + ax * (El - Sh).dot(ax); out = (El - Cc).normalized()
    ctrl(f'POLE_elbow.{s}', f'{sx}_forearm', 'chest', offset=gp(El + out * 20) - gp(El))      # pole straight out from the elbow
ctrl('SWORD', 'sword', 'root')
ctrl('CROWN', 'crown', 'root')
bpy.ops.object.mode_set(mode='POSE')

# ---------------------------------------------------------------- widgets + collections
wcol = bpy.data.collections.new('Widgets'); sc.collection.children.link(wcol); wcol.hide_render = True
def widget(name, verts, edges):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, edges, []); o = bpy.data.objects.new(name, me); wcol.objects.link(o); return o
circ = [(math.cos(a) * 0.5, 0, math.sin(a) * 0.5) for a in [i * math.pi / 12 for i in range(24)]]
W_RING = widget('WGT_ring', circ, [(i, (i + 1) % 24) for i in range(24)])
cub = [(x, y, z) for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)]
W_BOX = widget('WGT_box', cub, [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)])
W_DIA = widget('WGT_diamond', [(0, 0, .5), (0, 0, -.5), (.5, 0, 0), (-.5, 0, 0), (0, .5, 0), (0, -.5, 0)], [(0, 2), (0, 3), (0, 4), (0, 5), (1, 2), (1, 3), (1, 4), (1, 5), (2, 4), (4, 3), (3, 5), (5, 2)])
wcol.hide_viewport = True
cd = arm.collections.new('Deform'); cc = arm.collections.new('Controls'); cm = arm.collections.new('Mechanism')
for b in arm.bones: (cm if b.name.startswith('TWIST') else cc if not b.use_deform else cd).assign(b)
cm.is_visible = False
pb = rig.pose.bones
for b in pb:
    b.rotation_mode = 'XYZ'
for s, sx in (('R', 'right'), ('L', 'left')):
    pb[f'IK_foot.{s}'].custom_shape = W_RING; pb[f'IK_foot.{s}'].custom_shape_scale_xyz = (1.6, 1.6, 1.6)
    pb[f'IK_hand.{s}'].custom_shape = W_BOX; pb[f'IK_hand.{s}'].custom_shape_scale_xyz = (0.9, 0.9, 0.9)
    pb[f'POLE_knee.{s}'].custom_shape = W_DIA; pb[f'POLE_elbow.{s}'].custom_shape = W_DIA
    c = pb[f'{sx}_shin'].constraints.new('IK'); c.target = rig; c.subtarget = f'IK_foot.{s}'; c.pole_target = rig
    c.pole_subtarget = f'POLE_knee.{s}'; c.chain_count = 2; c.use_tail = True
    c = pb[f'{sx}_foot'].constraints.new('COPY_ROTATION'); c.target = rig; c.subtarget = f'IK_foot.{s}'
    c = pb[f'{sx}_forearm'].constraints.new('IK'); c.target = rig; c.subtarget = f'IK_hand.{s}'; c.pole_target = rig
    c.pole_subtarget = f'POLE_elbow.{s}'; c.chain_count = 2; c.use_tail = True
    # forearm twist (pronation): IK ignores roll, so a helper's keyed Y rotation is added on top, after the IK
    c = pb[f'{sx}_forearm'].constraints.new('COPY_ROTATION'); c.name = 'Twist'; c.target = rig; c.subtarget = f'TWIST.{s}'
    c.target_space = 'LOCAL'; c.owner_space = 'LOCAL'; c.mix_mode = 'AFTER'
    c = pb[f'{sx}_hand'].constraints.new('COPY_ROTATION'); c.target = rig; c.subtarget = f'IK_hand.{s}'

# the greatsword and the crown are their own objects: their controls live in world space and the deform bones copy
# them (influence 1 = driven by the control; 0 = simply carried by the hand / head)
c = pb['sword'].constraints.new('COPY_TRANSFORMS'); c.name = 'Sword'; c.target = rig; c.subtarget = 'SWORD'
c = pb['crown'].constraints.new('COPY_TRANSFORMS'); c.name = 'Crown'; c.target = rig; c.subtarget = 'CROWN'; c.influence = 0.0
pb['SWORD'].custom_shape = W_DIA; pb['SWORD'].custom_shape_scale_xyz = (1.5, 1.5, 1.5)
pb['CROWN'].custom_shape = W_RING; pb['CROWN'].custom_shape_scale_xyz = (1.4, 1.4, 1.4)
for b in pb: b.rotation_mode = 'XYZ'
for n in ('SWORD', 'CROWN'): pb[n].rotation_mode = 'QUATERNION'

# calibrate pole angles so the IK reproduces the Blockbench rest pose exactly
vl = bpy.context.view_layer
for s, sx in (('R', 'right'), ('L', 'left')):
    for chain, mid in ((f'{sx}_shin', f'{sx}_shin'), (f'{sx}_forearm', f'{sx}_forearm')):
        c = pb[chain].constraints['IK']; want = rig.data.bones[mid].head_local.copy()
        best = None
        for coarse in [True, False]:
            rng = range(-180, 181, 3) if coarse else [best[1] + d * 0.1 for d in range(-30, 31)]
            for a in rng:
                c.pole_angle = math.radians(a); vl.update()
                err = (pb[mid].head - want).length + (pb[chain].tail - rig.data.bones[chain].tail_local).length
                upper = pb[chain].parent
                err += (upper.matrix.to_quaternion().rotation_difference(rig.data.bones[upper.name].matrix_local.to_quaternion()).angle) * 0.5
                if best is None or err < best[0]: best = (err, a)
        c.pole_angle = math.radians(best[1]); vl.update()
        print(f'POLE {chain} angle {best[1]:.1f} err {best[0]:.4f}')

# ---------------------------------------------------------------- mesh
img = bpy.data.images.load(os.path.join(HERE, 'withered_king.png')); img.alpha_mode = 'STRAIGHT'
mat = bpy.data.materials.new('Sentinel'); mat.use_nodes = True
nt = mat.node_tree; bsdf = nt.nodes.get('Principled BSDF')
tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img; tn.interpolation = 'Closest'
nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color']); nt.links.new(tn.outputs['Alpha'], bsdf.inputs['Alpha'])
bsdf.inputs['Roughness'].default_value = 0.85
try: mat.surface_render_method = 'DITHERED'
except Exception: pass
try: mat.blend_method = 'CLIP'
except Exception: pass
verts, faces, uvs, groups = [], [], [], []
TW, TH = D['tex_w'], D['tex_h']
for c in D['cubes']:
    for f in c['faces']:
        i0 = len(verts)
        for p in f['p']: verts.append(gp(p))
        faces.append((i0, i0 + 3, i0 + 2, i0 + 1)); uvs.append([f['uv'][k] for k in (0, 3, 2, 1)]); groups.append(c['bone'])
me = bpy.data.meshes.new('Sentinel_Mesh'); me.from_pydata(verts, [], faces); me.update()
uvl = me.uv_layers.new(name='UV')
for poly, uv in zip(me.polygons, uvs):
    for li, (x, y) in zip(poly.loop_indices, uv): uvl.data[li].uv = (x / TW, 1 - y / TH)
me.materials.append(mat)
for poly in me.polygons: poly.use_smooth = False
mob = bpy.data.objects.new('Sentinel_Mesh', me); sc.collection.objects.link(mob)
for n in BM.ORDER: mob.vertex_groups.new(name=n)
for poly, g in zip(me.polygons, groups):
    mob.vertex_groups[g].add(list(poly.vertices), 1.0, 'REPLACE')
mob.parent = rig; mod = mob.modifiers.new('Armature', 'ARMATURE'); mod.object = rig

# ---------------------------------------------------------------- ground grid (1 block squares) + QC camera
gi = bpy.data.images.new('grid', 16, 16)
px = []
for y in range(16):
    for x in range(16):
        v = 0.2 if (x // 8 + y // 8) % 2 else 0.26
        if x % 8 == 0 or y % 8 == 0: v = 0.34
        px += [v, v * 1.05, v * 1.1, 1]
gi.pixels = px; gi.pack()
gm = bpy.data.materials.new('Ground'); gm.use_nodes = True
gt = gm.node_tree.nodes.new('ShaderNodeTexImage'); gt.image = gi; gt.interpolation = 'Closest'
gco = gm.node_tree.nodes.new('ShaderNodeTexCoord'); gmap = gm.node_tree.nodes.new('ShaderNodeMapping')
gmap.inputs['Scale'].default_value = (0.5, 0.5, 1)
gm.node_tree.links.new(gco.outputs['Object'], gmap.inputs['Vector']); gm.node_tree.links.new(gmap.outputs['Vector'], gt.inputs['Vector'])
gm.node_tree.links.new(gt.outputs['Color'], gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.mesh.primitive_plane_add(size=24, location=(0, 0, 0)); gpl = bpy.context.active_object; gpl.name = 'Ground'; gpl.data.materials.append(gm)
gpl.hide_select = True
cam_d = bpy.data.cameras.new('QC_Cam'); cam_d.type = 'ORTHO'; cam_d.ortho_scale = 12.5
cam = bpy.data.objects.new('QC_Cam', cam_d); sc.collection.objects.link(cam); sc.camera = cam
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'TEXTURE'; sh.show_shadows = True; sh.show_cavity = True
sh.cavity_type = 'BOTH'; sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = 1.3; sh.background_type = 'WORLD' if hasattr(sh, 'background_type') else sh.background_type
sc.world = sc.world or bpy.data.worlds.new('World'); sc.world.color = (0.035, 0.05, 0.06)
sc.render.resolution_x = 520; sc.render.resolution_y = 600; sc.render.film_transparent = False
sc.display.shadow_focus = 0.4
rig.select_set(True); bpy.context.view_layer.objects.active = rig
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'withered_king_rig.blend'))
print('SAVED rig', len(me.polygons), 'faces')
