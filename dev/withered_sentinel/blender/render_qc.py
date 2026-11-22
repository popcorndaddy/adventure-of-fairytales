"""Render QC frames and a contact sheet per action/view.
blender -b withered_sentinel_anim.blend --python render_qc.py -- <act[,act..]|rest|all> <frame_step> <yaws> [res] [cols]"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['rest', '1', '30']
acts, step, views = argv[0], float(argv[1]), [float(v) for v in argv[2].split(',')]
res = int(argv[3]) if len(argv) > 3 else 240; cols = int(argv[4]) if len(argv) > 4 else 10
sc = bpy.context.scene; rig = bpy.data.objects['Sentinel_Rig']; cam = sc.camera
sc.render.resolution_x = res; sc.render.resolution_y = int(res * 1.15)
out = os.path.join(HERE, 'renders'); os.makedirs(out, exist_ok=True)
if acts == 'all': acts = ','.join(sorted(a.name for a in bpy.data.actions if 'bb_length' in a))
def place_cam(yaw, height=4.0, pitch=8, dist=40):
    y = math.radians(yaw); p = math.radians(pitch)
    d = Vector((-math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)))
    target = Vector((0, -1.0, height)); cam.location = target + d * dist
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cam.data.ortho_scale = 13.5
for act in acts.split(','):
    if act == 'rest':
        frames = [0]
    else:
        A = bpy.data.actions[act]; rig.animation_data.action = A
        try: rig.animation_data.action_slot = A.slots[0]
        except Exception: pass
        f1 = A['bb_length'] * 20; n = int(round(f1 / step)); frames = [k * step for k in range(n + 1)]
    for yaw in views:
        place_cam(yaw); tiles = []
        for k, f in enumerate(frames):
            sc.frame_set(int(math.floor(f + 1e-6)), subframe=max(0.0, f - math.floor(f + 1e-6)))
            p = os.path.join(out, f'{act}_y{int(yaw)}_{k:03d}.png'); sc.render.filepath = p
            bpy.ops.render.render(write_still=True)
            im = bpy.data.images.load(p); a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4)
            tiles.append(a[::-1]); bpy.data.images.remove(im)
        h, w = tiles[0].shape[:2]; rows = (len(tiles) + cols - 1) // cols
        sheet = np.zeros((rows * h, min(cols, len(tiles)) * w, 4), np.float32); sheet[..., 3] = 1
        for i, t in enumerate(tiles):
            r, c = divmod(i, cols); sheet[r * h:(r + 1) * h, c * w:(c + 1) * w] = t
        img = bpy.data.images.new(f'sheet_{act}_{int(yaw)}', sheet.shape[1], sheet.shape[0])
        img.pixels = sheet[::-1].ravel(); img.filepath_raw = os.path.join(out, f'SHEET_{act}_y{int(yaw)}.png'); img.file_format = 'PNG'; img.save()
        print('REND', act, yaw, len(frames), 'frames')
