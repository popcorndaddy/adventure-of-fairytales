"""Crown hand-off check for withered_king_death: prints palm-to-crown and crown-to-guard distances, renders close-ups."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector
import anim_lib as L
sc = bpy.context.scene; rig = bpy.data.objects['Sentinel_Rig']; cam = sc.camera
A = bpy.data.actions['withered_king_death']; rig.animation_data.action = A
try: rig.animation_data.action_slot = A.slots[0]
except Exception: pass
piv = Vector(L.BONES['crown']['pivot']); s_axis = Vector((L.GRIP_L.x, L.GRIP_L.y, -7.8))
for t in [0, 4.0, 5.0, 5.3, 5.6, 6.0, 6.4, 7.0, 7.55, 7.75, 8.4, 9.5, 10.5]:
    L.eval_at(t)
    cw = L.W_now('crown') @ piv; hw = L.K_now('head') @ L.WREST['crown'] @ piv
    palm = L.W_now('left_hand') @ L.palm_local('left')
    guard = L.W_now('sword') @ s_axis
    up = (L.W_now('crown').to_3x3() @ Vector((0, 1, 0))).normalized(); sup = (L.W_now('sword').to_3x3() @ Vector((0, 0, 1))).normalized()
    print('CROWN t=%.2f  crown-head %.2f  palm-crown %.2f  crown-guard %.2f  crown-up.vs.handle %.0fdeg  crownY %.1f' % (
        t, (cw - hw).length, (palm - cw).length, (cw - guard).length, math.degrees(up.angle(sup)), cw.y))
# close-ups on the crown
sc.render.resolution_x = 360; sc.render.resolution_y = 360
out = os.path.join(L.BM.HERE, 'renders'); os.makedirs(out, exist_ok=True)
for k, t in ([] if '--norender' in sys.argv else enumerate([4.6, 5.3, 5.9, 6.5, 7.2, 7.75, 8.6, 10.5])):
    L.eval_at(t); c = L.G @ (L.K_now('crown') @ piv) if False else None
    pb = rig.pose.bones['crown']; tgt = rig.matrix_world @ pb.head
    for yaw in (20, 100):
        y = math.radians(yaw); d = Vector((-math.sin(y), -math.cos(y), 0.25)).normalized()
        cam.location = tgt + d * 30; cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); cam.data.ortho_scale = 5.0
        sc.render.filepath = os.path.join(out, f'CROWN_{k}_{yaw}.png'); bpy.ops.render.render(write_still=True)
print('CROWN renders done')
