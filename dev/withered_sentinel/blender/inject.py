"""Put the solved cape strips and skirt (from capes_skirt.json) back into the Blender actions, so the .blend
matches what the game plays.  blender -b withered_sentinel_anim.blend --python inject.py"""
import bpy, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anim_lib as L
D = json.load(open(os.path.join(L.BM.HERE, 'capes_skirt.json')))
rig = L.rig
for name, bones in D.items():
    A = bpy.data.actions.get(name)
    if not A: continue
    rig.animation_data.action = A
    try: rig.animation_data.action_slot = A.slots[0]
    except Exception: pass
    for b in bones: L._clear_keys(A, b)
    L.CUR.clear(); L.CUR.update(name=name, length=A['bb_length'], loop=A['bb_loop'], eases={}, action=A)
    for b, keys in bones.items():
        L._keys(b, [(t, L.fk_basis(b, tuple(v)), 'linear') for t, v in keys])
    for fc in L._fcurves(A):
        if any(f'"{b}"' in fc.data_path for b in bones):
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    print('INFO injected', name, len(bones), 'bones')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(L.BM.HERE, 'withered_sentinel_anim.blend'))
print('SAVED')
