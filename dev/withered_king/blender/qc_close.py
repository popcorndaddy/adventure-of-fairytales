"""Close-up renders around one bone: blender -b withered_king_anim.blend --python qc_close.py -- <action> <bone> <t,t,..> <yaw,yaw> [scale]"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector
import anim_lib as L
a = sys.argv[sys.argv.index('--') + 1:]
act, bone, times, yaws = a[0], a[1], [float(x) for x in a[2].split(',')], [float(x) for x in a[3].split(',')]
scale = float(a[4]) if len(a) > 4 else 4.0
sc = bpy.context.scene; rig = bpy.data.objects['Sentinel_Rig']; cam = sc.camera
A = bpy.data.actions[act]; rig.animation_data.action = A
try: rig.animation_data.action_slot = A.slots[0]
except Exception: pass
sc.render.resolution_x = 300; sc.render.resolution_y = 300
out = os.path.join(L.BM.HERE, 'renders'); os.makedirs(out, exist_ok=True)
for i, t in enumerate(times):
    L.eval_at(t); tgt = rig.matrix_world @ rig.pose.bones[bone].head
    for yaw in yaws:
        y = math.radians(yaw); d = Vector((-math.sin(y), -math.cos(y), 0.2)).normalized()
        cam.location = tgt + d * 30; cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); cam.data.ortho_scale = scale
        sc.render.filepath = os.path.join(out, f'CLOSE_{act}_{bone}_{i}_{int(yaw)}.png'); bpy.ops.render.render(write_still=True)
print('REND close done')
