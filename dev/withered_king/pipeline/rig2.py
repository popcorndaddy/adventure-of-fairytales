"""Withered King rig v2: extra bones so the animation brief can be met, without changing how the model looks.
Import this BEFORE anything else that imports model3 - it edits model3's bone/cube tables in place.
Added: neck (takes the head's rest tilt), clavicles, crown (its own bone so it can be lifted off), left fingers and
thumb, right fist + thumb, tabards, mantle drapes, hood drape and banner as secondary-motion bones.
Every new bone has zero rest rotation except neck, which inherits the head's old rest rotation, so all cubes keep
their exact world placement."""
import model3 as M

def _add(name, parent, pivot, rot=(0, 0, 0), before=None):
    b = dict(name=name, parent=parent, pivot=[float(v) for v in pivot], rot=list(rot))
    if before:
        i = [x['name'] for x in M.BONES].index(before); M.BONES.insert(i, b)
    else:
        M.BONES.append(b)
    M._b[name] = b
    return b

if '_rig2' not in M.__dict__:
    B = M._b; HY = B['head']['pivot'][1]
    # neck carries the head's old 19 deg rest tilt; the head now pivots at the top of the neck
    _add('neck', 'chest', B['head']['pivot'], B['head']['rot'], before='head')
    B['head']['parent'] = 'neck'; B['head']['pivot'] = [0.0, HY + 2.3, -0.6]; B['head']['rot'] = [0, 0, 0]
    _add('crown', 'head', (0.0, HY + 2.75, -2.8), before='jaw')
    _add('hood_drape', 'head', (0.0, HY + 2.0, 4.0), before='jaw')
    for s, x in (('right', 1), ('left', -1)):
        _add(f'{s}_clavicle', 'chest', (4.0 * x, HY - 5.5, -2.0), before=f'{s}_arm')
        B[f'{s}_arm']['parent'] = f'{s}_clavicle'
    for k, zc in enumerate((-1.8, -0.6, 0.6, 1.8)):
        _add(f'left_finger{k}', 'left_hand', (-12.6, HY - 35.5, zc))
    _add('left_thumb', 'left_hand', (-11.2, HY - 33.4, -2.1))
    _add('right_fingers', 'right_hand', (13.1, HY - 31.5, 0.0))
    _add('right_thumb', 'right_hand', (13.6, HY - 34.6, -0.9))
    _add('tabard_front', 'skirt', (0.0, HY - 24.0, -6.6))
    _add('tabard_back', 'skirt', (0.0, HY - 23.0, 5.4))
    _add('tabard_right', 'skirt', (9.6, HY - 24.0, 1.5))
    _add('tabard_left', 'skirt', (-9.6, HY - 24.0, 1.5))
    _add('drape_left', 'chest', (-6.5, HY - 2.0, -5.8))
    _add('drape_right', 'chest', (7.5, HY - 2.0, -5.6))
    _add('banner', 'chest', (3.0, HY - 7.0, 5.4))
    MOVE = {'neck': 'neck', 'hood_drape': 'hood_drape', 'tabard_front': 'tabard_front', 'tabard_back': 'tabard_back',
            'tabard_side_1': 'tabard_right', 'tabard_side_-1': 'tabard_left', 'mantle_drape_l': 'drape_left',
            'mantle_drape_r': 'drape_right', 'banner': 'banner'}
    for c in M.CUBES:
        n = c['name']
        if n in MOVE: c['bone'] = MOVE[n]
        elif n.startswith('crown_'): c['bone'] = 'crown'
        elif c['bone'] == 'left_hand':
            for k in range(4):
                if n in (f'finger{k}_left', f'finger{k}_mid_left', f'claw{k}_left'): c['bone'] = f'left_finger{k}'
            if n in ('thumb_left', 'thumb_claw_left'): c['bone'] = 'left_thumb'
        elif c['bone'] == 'right_hand':
            if n.startswith('finger') or n.startswith('claw'): c['bone'] = 'right_fingers'
            if n in ('thumb_right', 'thumb_claw_right'): c['bone'] = 'right_thumb'
    # parents must precede children
    order, seen = [], set()
    def visit(b):
        if b['name'] in seen: return
        if b['parent']: visit(M._b[b['parent']])
        seen.add(b['name']); order.append(b)
    for b in list(M.BONES): visit(b)
    M.BONES[:] = order
    M._rig2 = True
