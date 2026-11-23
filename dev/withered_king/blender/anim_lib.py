"""Withered King animation system (Blender side).

Authoring is done in Blockbench terms (model pixels, y up, front = -z, additive degrees on the rest pose); this module
turns it into keys on the rig:
  * FK bones (pelvis, spine, neck, head, jaw, clavicles, fingers): sparse keys with chosen easing.
  * feet: IK_foot controls (sparse keys, or dense procedural tracks such as the walk/run gaits).
  * SWORD: the greatsword is its own object (world control, quaternion keys).  Hands GRIP it through grip states
    ('cane' = blade out of the little-finger side, 'normal' = out of the thumb side; the left hand takes a lower,
    mirrored grip for two-handed holds) and can let go / regrip with blends - the hand IK targets are derived from the
    sword every frame while gripping, and from free targets otherwise.
  * CROWN: its own object; during the death it travels head -> left hand -> sword guard (rigid attachment hand-offs).
  * Per frame the elbows are aimed so forearm and hand line up, each forearm gets a natural roll (TWIST helpers),
    and the knees follow the feet.
"""
import bpy, math
from mathutils import Matrix, Vector, Euler, Quaternion
import bbmath as BM
from bbmath import G, GI, BONES, WREST, local_bb, rot_bb, frame_from

FPS = 20
rig = bpy.data.objects['Sentinel_Rig']; PB = rig.pose.bones; AB = rig.data.bones
sc = bpy.context.scene; vl = bpy.context.view_layer
CLOTH = {'cape', 'cape_mid', 'cape_mid_low', 'cape_left', 'cape_left_low', 'cape_right', 'cape_right_low',
         'tabard_front', 'tabard_back', 'tabard_left', 'tabard_right', 'drape_left', 'drape_right', 'hood_drape', 'banner'}
CUR = {}

def B(n): return AB[n].matrix_local
def V(*a): return Vector(a[0] if len(a) == 1 else a)
def lerp(a, b, u): return tuple(x + (y - x) * u for x, y in zip(a, b))
def add3(*vs): return tuple(sum(v[i] for v in vs) for i in range(3))
def norm(v):
    l = math.sqrt(sum(x * x for x in v)); return tuple(x / l for x in v)
def smooth(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)

# ------------------------------------------------------------------ conversions
def basis_from_K(n, Kbb):
    """pose basis for a bone whose parent is unposed root (controls) so its skin transform is Kbb."""
    return B(n).inverted() @ (G @ Kbb @ GI) @ B(n)
def fk_basis(n, rot=(0, 0, 0), pos=(0, 0, 0)):
    p = BONES[n]['parent']; Wp = WREST[p] if p else Matrix.Identity(4)
    K_rel = Wp @ local_bb(n, rot, pos) @ local_bb(n).inverted() @ Wp.inverted()
    return B(n).inverted() @ (G @ K_rel @ GI) @ B(n)
def K_now(n): return GI @ (PB[n].matrix @ B(n).inverted()) @ G      # bb skin transform at the evaluated frame
def W_now(n): return K_now(n) @ WREST[n]
def eval_at(t):
    f = t * FPS; sc.frame_set(int(math.floor(f + 1e-6)), subframe=max(0.0, f - math.floor(f + 1e-6)))

# ------------------------------------------------------------------ actions and keys
def begin(name, length, loop):
    A = bpy.data.actions.get(name)
    if A: bpy.data.actions.remove(A)
    A = bpy.data.actions.new(name); A.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = A
    for pb in PB:
        pb.location = (0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    PB['crown'].constraints['Crown'].influence = 0.0
    _LROLL['prev'] = None
    CUR.clear(); CUR.update(name=name, length=length, loop=loop, eases={}, action=A, grips={'R': [], 'L': []}, crown=None, events=[],
                            free_fn={'R': None, 'L': None})
    PB['crown'].constraints['Crown'].keyframe_insert('influence', frame=0)
    return A

def event(t, kind, **data):
    """a gameplay/effect event on the action timeline (exported to the timing table)."""
    CUR['events'].append(dict(t=round(t, 3), kind=kind, **data))

EASE = {'smooth': ('BEZIER', 'AUTO'), 'linear': ('LINEAR', 'AUTO'), 'hold': ('CONSTANT', 'AUTO'),
        'in': ('CUBIC', 'EASE_IN'), 'in2': ('QUAD', 'EASE_IN'), 'in4': ('QUART', 'EASE_IN'), 'expo_in': ('EXPO', 'EASE_IN'),
        'out': ('CUBIC', 'EASE_OUT'), 'out2': ('QUAD', 'EASE_OUT'), 'out4': ('QUART', 'EASE_OUT'), 'expo_out': ('EXPO', 'EASE_OUT'),
        'inout': ('SINE', 'EASE_IN_OUT'), 'inout3': ('CUBIC', 'EASE_IN_OUT'), 'back': ('BACK', 'EASE_OUT'), 'circ_out': ('CIRC', 'EASE_OUT')}

def _key(n, basis, t, ease, prev):
    pb = PB[n]; loc, q, _ = basis.decompose(); f = round(t * FPS, 4)
    pb.location = loc
    if pb.rotation_mode == 'QUATERNION':
        if prev is not None and q.dot(prev) < 0: q = -q
        pb.rotation_quaternion = q; pb.keyframe_insert('rotation_quaternion', frame=f, group=n); e = q
    else:
        e = q.to_euler('XYZ', prev) if prev is not None else q.to_euler('XYZ')
        pb.rotation_euler = e; pb.keyframe_insert('rotation_euler', frame=f, group=n)
    pb.keyframe_insert('location', frame=f, group=n)
    CUR['eases'][(n, f)] = ease
    return e

def _keys(n, items):
    prev = None
    for t, basis, ease in sorted(items, key=lambda k: k[0]):
        prev = _key(n, basis, t, ease, prev)

def fk(n, keys):
    """keys: [(t, rot[, pos[, ease]])] - bb additive degrees / pixels."""
    _keys(n, [(k[0], fk_basis(n, k[1] or (0, 0, 0), (k[2] if len(k) > 2 and k[2] else (0, 0, 0))), k[3] if len(k) > 3 else 'smooth') for k in keys])

def fingers(side, keys):
    """keys: [(t, curl, spread, ease)]; left: curl/spread per finger, right: fist squeeze."""
    if side == 'L':
        for k in range(4):
            fk(f'left_finger{k}', [(t, (0, (k - 1.5) * sp, cu * (0.9 + 0.07 * k)), None, e) for t, cu, sp, e in keys])
        fk('left_thumb', [(t, (cu * 0.4, 0, cu * 0.5 - sp * 0.6), None, e) for t, cu, sp, e in keys])
    else:
        fk('right_fingers', [(t, (0, 0, cu), None, e) for t, cu, sp, e in keys])
        fk('right_thumb', [(t, (cu * 0.6, 0, cu * 0.3), None, e) for t, cu, sp, e in keys])

def ride(space, K):
    return K if not space else K_now(space) @ K

# --- feet
def foot_K(side, spec):
    """d=(dx,dy,dz) moves the flat foot; yaw (+ toes to his left) about the contact pivot; pitch (+ toes up) about heel/toe."""
    s = 'right' if side == 'R' else 'left'
    ank = V(BONES[f'{s}_foot']['head']); Wf = WREST[f'{s}_foot']
    toe = (Wf @ V(*BM.D['foot'][s]['toe'], 1)).xyz; heel = (Wf @ V(*BM.D['foot'][s]['heel'], 1)).xyz
    d = V(*spec.get('d', (0, 0, 0))); pit = spec.get('pitch', 0)
    pv = spec.get('pivot') or ('heel' if pit > 0 else 'toe' if pit < 0 else 'ankle')
    piv = {'heel': heel, 'toe': toe, 'ankle': ank}[pv]
    M = Matrix.Translation(d) @ Matrix.Translation(piv) @ rot_bb((0, spec.get('yaw', 0), spec.get('roll', 0))).to_4x4() @ Matrix.Translation(-piv)
    if pit:
        pw = (M @ V(*piv, 1)).xyz; ax = (M.to_3x3() @ V(1, 0, 0)).normalized()
        M = Matrix.Translation(pw) @ Matrix.Rotation(math.radians(pit), 4, ax) @ Matrix.Translation(-pw) @ M
    return M
EASEF = {'linear': lambda u: u, 'smooth': lambda u: u * u * (3 - 2 * u), 'inout': lambda u: u * u * u * (u * (u * 6 - 15) + 10),
         'in': lambda u: u * u, 'out': lambda u: 1 - (1 - u) ** 2, 'expo_in': lambda u: u ** 4, 'expo_out': lambda u: 1 - (1 - u) ** 4}
def _pv(sp):
    p = sp.get('pitch', 0); return sp.get('pivot') or ('heel' if p > 0 else 'toe' if p < 0 else 'ankle')
def feet(side, keys):
    """feet are keyed densely (every frame) from eased spec interpolation, so a pivoting foot keeps its toe/heel planted
    between keys instead of the control's location and rotation interpolating along separate chords."""
    n = f'IK_foot.{side}'; keys = sorted(keys, key=lambda k: k[0]); items = []
    f0, f1 = int(round(keys[0][0] * FPS)), int(round(keys[-1][0] * FPS))
    for f in range(f0, f1 + 1):
        t = f / FPS; i = max(0, max(j for j in range(len(keys)) if keys[j][0] <= t + 1e-9))
        if i >= len(keys) - 1: sp = keys[-1][1]
        else:
            (ta, A, ea), (tb, Bk, _) = keys[i], keys[i + 1]; w = EASEF.get(ea, EASEF['smooth'])((t - ta) / (tb - ta)) if tb > ta else 1.0
            da, db = V(*A.get('d', (0, 0, 0))), V(*Bk.get('d', (0, 0, 0)))
            sp = {'d': tuple(da.lerp(db, w))}
            for k_ in ('yaw', 'pitch', 'roll'): sp[k_] = A.get(k_, 0) * (1 - w) + Bk.get(k_, 0) * w
            pa, pb = _pv(A), _pv(Bk)
            sp['pivot'] = pa if pa == pb else (pa if abs(A.get('pitch', 0)) >= abs(Bk.get('pitch', 0)) else pb)
        items.append((t, basis_from_K(n, foot_K(side, sp)), 'linear'))
    _keys(n, items)

# --- sword
GRIP_L = V(*BM.D['sword']['grip'])                    # grip point (top of the handle, under the right fist) in sword space
HANDLE = V(0, 0, 1)                                    # handle runs toward +z (pommel); blade toward -z
def sword_add(mode): return (0.0, -180.0, 0.0) if mode == 'normal' else (0.0, 0.0, 0.0)
_RB = {}
def _rest_sword(mode):
    if mode not in _RB:
        R = (WREST['right_hand'] @ local_bb('sword', sword_add(mode))).to_3x3()
        _RB[mode] = ((R @ V(0, 0, -1)).normalized(), (R @ V(1, 0, 0)).normalized())
    return _RB[mode]
def auto_flat(blade, mode, Rdelta=None):
    """edge orientation a relaxed wrist gives for this blade direction (rest grip swung the shortest way)."""
    b0, f0 = _rest_sword(mode)
    if Rdelta is not None: b0, f0 = Rdelta @ b0, Rdelta @ f0
    return tuple(b0.rotation_difference(V(*blade).normalized()) @ f0)
def sword_W(spec, t=None):
    """bb world transform of the sword (maps sword-space points to world). spec: grip, blade|tip, flat (None=auto), mode, roll."""
    g = V(*spec['grip'])
    b = (V(*spec['tip']) - g).normalized() if 'tip' in spec else V(*spec['blade']).normalized()
    f = spec.get('flat')
    if f is None:
        Rd = None
        if spec.get('torso_relative') and t is not None: eval_at(t); Rd = K_now('chest').to_3x3()
        f = auto_flat(b, spec.get('mode', 'cane'), Rd)
    f = V(*f)
    if spec.get('roll'): f = Matrix.Rotation(math.radians(spec['roll']), 3, b) @ f
    # sword space: blade = -z from the grip point, flat normal = +x
    tip_len = 41.8
    W = frame_from(GRIP_L, g, (V(0, 0, -1), V(1, 0, 0)), (b, f))
    return W
def sword_K(spec, t=None): return sword_W(spec, t) @ WREST['sword'].inverted()
def sword(keys):
    """keys: [(t, spec|Matrix(bb K), ease)] on the SWORD control."""
    _keys('SWORD', [(t, basis_from_K('SWORD', s if isinstance(s, Matrix) else sword_K(s, t)), e) for t, s, e in keys])
def sword_dense(fn, t0, t1, step=1.0 / FPS, ease='linear'):
    """procedural sword: fn(t) -> spec or bb K, evaluated with the torso already posed at t."""
    items = []; n = int(round((t1 - t0) / step))
    for k in range(n + 1):
        t = t0 + k * step; eval_at(t); s = fn(t)
        items.append((t, basis_from_K('SWORD', s if isinstance(s, Matrix) else sword_K(s, t)), ease))
    _keys('SWORD', items)

def tip_world(K=None):
    """world position of the blade tip for a sword skin transform K (default: evaluated now)."""
    K = K if K is not None else K_now('sword')
    return (K @ WREST['sword'] @ V(GRIP_L.x, GRIP_L.y, GRIP_L.z - 41.8, 1)).xyz

# --- hand <-> sword grips
def palm_local(s): return V(BONES[f'{s}_hand']['pivot']) + V(0, -2.0, 0)
def _hand_rel_right(mode):
    """right hand rest-frame transform relative to sword space for a grip mode: W_hand = W_sword @ rel."""
    return local_bb('sword', sword_add(mode)).inverted()
_LREL = {}
def _hand_rel_left(mode, slide=4.0):
    """left hand on the handle below the right fist, palm on the opposite side, fingers wrapping the other way."""
    key = (mode, slide)
    if key not in _LREL:
        Wr = _hand_rel_right(mode)                                   # right hand frame in sword space
        R = Wr.to_3x3(); pr = (Wr @ V(*palm_local('right'), 1)).xyz
        nr = (R @ V(1, 0, 0)).normalized(); fr = (R @ V(0, -1, 0)).normalized()
        q = V(GRIP_L.x, GRIP_L.y, pr.z); o = pr - q
        pl = q + V(0, 0, slide) - o
        Wl = frame_from(palm_local('left'), pl, (V(0, -1, 0), V(1, 0, 0)), (-fr, -nr))
        _LREL[key] = Wl
    return _LREL[key]
_LROLL = {'prev': None}
def _left_roll_K(Ws, mode):
    """the left hand may turn around the handle (a real off-hand does): pick the roll whose wrist-to-palm line points
    back toward the shoulder, so the wrist isn't wrenched; the choice is kept close to the previous frame's."""
    base = _hand_rel_left(mode); a = V(GRIP_L.x, GRIP_L.y, 0)
    Hinv = WREST['left_hand'].inverted(); pr = _palm_rest('L')
    up_rest = (WREST['left_hand'].to_3x3() @ V(0, 1, 0)).normalized()
    sh = (K_now('left_clavicle') @ V(*(WREST['left_arm'] @ V(*BONES['left_arm']['pivot'], 1)).xyz, 1)).xyz
    best = None; prev = _LROLL['prev']
    for th in range(-110, 111, 2):
        rel = Matrix.Translation(a) @ Matrix.Rotation(math.radians(th), 4, 'Z') @ Matrix.Translation(-a) @ base
        K = Ws @ rel @ Hinv
        p = (K @ V(pr.x, pr.y, pr.z, 1)).xyz; up = (K.to_3x3() @ up_rest).normalized()
        sc_ = up.dot((sh - p).normalized()) - 0.0015 * abs(th) - (0.004 * abs(th - prev) if prev is not None else 0)
        if best is None or sc_ > best[0]: best = (sc_, th, K)
    _LROLL['prev'] = best[1]
    return best[2]
def hand_from_sword(side, Ws, mode):
    if side == 'L': return _left_roll_K(Ws, mode)
    rel = _hand_rel_right(mode)
    return Ws @ rel @ WREST['right_hand'].inverted()             # skin transform K of the hand
def grip(side, keys):
    """grip states over time: [(t, state, blend_seconds)] with state 'cane' | 'normal' | 'free'."""
    CUR['grips'][side] = sorted(keys, key=lambda k: k[0])
def hand_K_from_palm(side, palm, fingers_dir, normal):
    s = 'right' if side == 'R' else 'left'
    Wh = frame_from(palm_local(s), palm, (V(0, -1, 0), V(1, 0, 0)), (V(*fingers_dir), V(*normal)))
    return Wh @ WREST[f'{s}_hand'].inverted()
def hand_K_offset(side, d=(0, 0, 0), r=(0, 0, 0)):
    s = 'right' if side == 'R' else 'left'
    pc = (WREST[f'{s}_hand'] @ V(*palm_local(s), 1)).xyz
    d = V(*d) + V(0, 2.5, -1.5)          # the rest arm is straight; free-hand targets keep a relaxed bend in the elbow
    return Matrix.Translation(pc + d) @ rot_bb(r).to_4x4() @ Matrix.Translation(-pc)
def hands(side, keys):
    """free hand targets (used whenever the hand is not gripping): [(t, spec, ease)] spec {'palm':..}|{'off':(d,r)}|
    {'crown': rel} ; 'space': torso bone to ride."""
    n = f'IK_hand.{side}'; items = []
    for t, spec, ease in sorted(keys, key=lambda k: k[0]):
        K = hand_K_from_palm(side, *spec['palm']) if 'palm' in spec else hand_K_offset(side, *spec['off'])
        if spec.get('space'): eval_at(t); K = ride(spec['space'], K)
        items.append((t, basis_from_K(n, K), ease))
    _keys(n, items)

def pole(name, keys):
    items = []
    for t, p, ease in keys:
        rest_head = (GI @ V(*AB[name].head_local, 1)).xyz
        items.append((t, B(name).inverted() @ (G @ Matrix.Translation(V(*p) - rest_head) @ GI) @ B(name), ease))
    _keys(name, items)

# --- crown
def crown_track(fn):
    """fn(t, ctx) -> bb skin transform K of the crown, or None to leave it on the head. ctx has evaluated 'head', 'sword'."""
    CUR['crown'] = fn
def free_override(side, fn):
    """fn(t, keyed_free_K, ctx) -> K or None: per-frame free hand target (e.g. carrying the crown)."""
    CUR['free_fn'][side] = fn

# ------------------------------------------------------------------ helpers for passes
def _fcurves(A):
    try:
        from bpy_extras.anim_utils import action_get_channelbag_for_slot
        return action_get_channelbag_for_slot(A, A.slots[0]).fcurves
    except Exception:
        return A.fcurves
def _has_keys(A, bone): return any(f'"{bone}"' in fc.data_path for fc in _fcurves(A))
def _clear_keys(A, bone):
    for fc in list(_fcurves(A)):
        if f'"{bone}"' in fc.data_path and 'constraints' not in fc.data_path:
            try: fc.keyframe_points.clear()
            except Exception:
                while len(fc.keyframe_points): fc.keyframe_points.remove(fc.keyframe_points[0])
def _blend_K(Ka, Kb, u, pivot=None):
    """blend two skin transforms; with a pivot (a rest-world point, e.g. the palm) the point travels straight between
    its two positions while the rotation turns about it, instead of swinging round the world origin"""
    qa, qb = Ka.to_quaternion(), Kb.to_quaternion()
    if pivot is None:
        la, lb = Ka.translation, Kb.translation
        return Matrix.Translation(la.lerp(lb, u)) @ qa.slerp(qb, u).to_matrix().to_4x4()
    p = V(*pivot); pa = (Ka @ V(p.x, p.y, p.z, 1)).xyz; pb = (Kb @ V(p.x, p.y, p.z, 1)).xyz
    return Matrix.Translation(pa.lerp(pb, u)) @ qa.slerp(qb, u).to_matrix().to_4x4() @ Matrix.Translation(-p)
def _palm_rest(side):
    s = 'right' if side == 'R' else 'left'
    return (WREST[f'{s}_hand'] @ V(*palm_local(s), 1)).xyz

def _grip_weights(side, t):
    """[(state, weight)] for the hand at time t."""
    ks = CUR['grips'][side]
    if not ks: return [('cane', 1.0)] if side == 'R' else [('free', 1.0)]
    prev = ks[0][1]; res = [(prev, 1.0)]
    for i in range(1, len(ks)):
        tk, st, bl = ks[i]
        if t < tk: break
        u = smooth((t - tk) / bl) if bl > 0 else 1.0
        res = [(prev, 1 - u), (st, u)] if u < 1 else [(st, 1.0)]
        prev = st if u >= 1 else prev
        if u < 1: break
    return res

def hand_target(side, t, free_K):
    Ws = K_now('sword') @ WREST['sword']
    parts = []
    for st, w in _grip_weights(side, t):
        if w <= 1e-4: continue
        parts.append((free_K if st == 'free' else hand_from_sword(side, Ws, st), w))
    if len(parts) == 1: return parts[0][0]
    (Ka, wa), (Kb, wb) = parts[0], parts[1]
    return _blend_K(Ka, Kb, wb / (wa + wb), _palm_rest(side))

# ------------------------------------------------------------------ per-frame solving
def solve_frames():
    """pass 1: hand targets from grips (+ crown hand-offs); elbows aimed so forearm and hand line up.
    pass 2: forearm roll (TWIST) and knee aim.  Writes dense keys for IK_hand, POLE_elbow, TWIST, POLE_knee, CROWN."""
    A = CUR['action']; nfr = int(round(CUR['length'] * FPS)); loopy = CUR['loop'] == 'loop'
    targets = {'R': [], 'L': []}; crowns = []
    for f in range(nfr + 1):
        sc.frame_set(f); t = f / FPS
        ctx = {'head': K_now('head'), 'sword': K_now('sword')}
        crowns.append(CUR['crown'](t, ctx) if CUR['crown'] else None)
        ctx['crown'] = crowns[-1]
        for side in ('R', 'L'):
            free = K_now(f'IK_hand.{side}')               # evaluated free target (IK_hand sparse keys) - control rest == hand rest
            ff = CUR['free_fn'][side]
            if ff is not None:
                o = ff(t, free, ctx)
                if o is not None: free = o
            targets[side].append(hand_target(side, t, free))
    # solve elbows on the final targets
    res = {}
    for side, s in (('R', 'right'), ('L', 'left')):
        L1 = AB[f'{s}_arm'].length; L2 = AB[f'{s}_forearm'].length
        Bh = AB[f'{s}_hand'].matrix_local.to_3x3()
        a_h = Bh.inverted() @ AB[f'{s}_forearm'].matrix_local.col[1].xyz.normalized()
        # every frame: 72 candidate elbow positions on the IK circle with their own cost; then a Viterbi pass picks the
        # cheapest path whose swivel never jumps more than DPH_MAX per frame, so the elbow can't flip between branches
        frames = (list(range(nfr + 1)) * 2) if loopy else list(range(nfr + 1))
        NS = 72; cand = []; cost = []
        for f in frames:
            sc.frame_set(f)
            S = PB[f'{s}_arm'].head.copy(); spine0 = PB['chest'].head.copy(); spine_d = PB['chest'].y_axis.normalized()
            Mc = G @ targets[side][f] @ GI @ B(f'IK_hand.{side}')
            Wp = Mc.translation; want = (Mc.to_3x3() @ a_h).normalized()
            dv = Wp - S; d = min(dv.length, (L1 + L2) * 0.999); u = dv.normalized()
            x = (L1 * L1 - L2 * L2 + d * d) / (2 * d); r = math.sqrt(max(0.0, L1 * L1 - x * x))
            v0 = Vector((0, 0, -1)) - u * u.dot(Vector((0, 0, -1)))
            if v0.length < 1e-3: v0 = Vector((1, 0, 0)) - u * u.x
            v0.normalize(); v1 = u.cross(v0); row = []; crow = []
            for k in range(NS):
                ph = k * 2 * math.pi / NS; E = S + u * x + (v0 * math.cos(ph) + v1 * math.sin(ph)) * r
                fd = (Wp - E).normalized(); sw = math.acos(max(-1, min(1, fd.dot(want))))
                rel = E - spine0; lat = (rel - spine_d * rel.dot(spine_d)).length
                crow.append(sw * sw + 4.0 * max(0.0, 1.45 - lat) ** 2 + 0.4 * max(0.0, -math.cos(ph)) ** 2)
                row.append((Mc, E, (v0 * math.cos(ph) + v1 * math.sin(ph)).normalized(), sw))   # 3rd: elbow-out direction
            cand.append(row); cost.append(crow)
        DPH_MAX = 9                                   # states (x5 deg) per frame = 45 deg per 1/20 s
        INF = float('inf'); acc = list(cost[0]); back = []
        for i in range(1, len(frames)):
            nacc = [INF] * NS; bk = [0] * NS
            for k in range(NS):
                best_c, best_j = INF, 0
                for dj in range(-DPH_MAX, DPH_MAX + 1):
                    j = (k + dj) % NS; dph = dj * 2 * math.pi / NS
                    c = acc[j] + 1.2 * dph * dph
                    if c < best_c: best_c, best_j = c, j
                nacc[k] = best_c + cost[i][k]; bk[k] = best_j
            acc = nacc; back.append(bk)
        k = min(range(NS), key=lambda q: acc[q]); path = [k]
        for bk in reversed(back): k = bk[k]; path.append(k)
        path.reverse()
        out = [cand[i][path[i]] for i in range(len(frames))]
        if loopy: out = out[nfr + 1:]
        if loopy: out[-1] = out[0]
        res[side] = out
    for side in ('R', 'L'):
        _clear_keys(A, f'IK_hand.{side}'); _clear_keys(A, f'POLE_elbow.{side}')
        pc, pp = PB[f'IK_hand.{side}'], PB[f'POLE_elbow.{side}']; pe = None
        for f, (Mc, E, Cc, sw) in enumerate(res[side]):
            sc.frame_set(f)
            pc.matrix = Mc; vl.update(); e = pc.rotation_euler.copy()
            if pe is not None: e.make_compatible(pe)
            pc.rotation_euler = e; pe = e.copy()
            pc.keyframe_insert('location', frame=f, group=pc.name); pc.keyframe_insert('rotation_euler', frame=f, group=pc.name)
            pp.matrix = Matrix.Translation(E + Cc * 2.5) @ pp.matrix.to_3x3().to_4x4(); vl.update()   # Cc = elbow-out dir (safe when the arm is straight)
            pp.keyframe_insert('location', frame=f, group=pp.name)
            CUR['eases'][(pc.name, float(f))] = 'linear'; CUR['eases'][(pp.name, float(f))] = 'linear'
        sws = [math.degrees(r[3]) for r in res[side]]
        print('CHECK', CUR['name'], side, 'forearm/hand misalignment max %.0f mean %.0f' % (max(sws), sum(sws) / len(sws)))
    # crown control
    if any(c is not None for c in crowns):
        con = PB['crown'].constraints['Crown']; pc = PB['CROWN']; pq = None
        for f, K in enumerate(crowns):
            con.influence = 1.0 if K is not None else 0.0; con.keyframe_insert('influence', frame=f)
            if K is not None:
                bas = basis_from_K('CROWN', K); loc, q, _ = bas.decompose()
                if pq is not None and q.dot(pq) < 0: q = -q
                pq = q; pc.location = loc; pc.rotation_quaternion = q
                pc.keyframe_insert('location', frame=f, group='CROWN'); pc.keyframe_insert('rotation_quaternion', frame=f, group='CROWN')
                CUR['eases'][('CROWN', float(f))] = 'linear'
    _twist_and_knees()

def _twist_and_knees():
    A = CUR['action']; nfr = int(round(CUR['length'] * FPS)); loopy = CUR['loop'] == 'loop'
    knees = [s for s in ('R', 'L') if not _has_keys(A, f'POLE_knee.{s}')]
    r0 = {s: B(f'{s}_forearm').to_3x3().inverted() @ B(f'{s}_hand').to_3x3() for s in ('right', 'left')}
    order = (list(range(nfr + 1)) * 2) if loopy else list(range(nfr + 1))
    tw = {s: [] for s in ('right', 'left')}; kp = {s: [] for s in knees}; prev = {'right': 0.0, 'left': 0.0}; wr = {'right': [], 'left': []}
    TMAX = math.radians(120)
    for pass_i, f in enumerate(order):
        if loopy and pass_i == nfr + 1:
            tw = {s: [] for s in ('right', 'left')}; kp = {s: [] for s in knees}; wr = {'right': [], 'left': []}
        sc.frame_set(f)
        for s in knees:
            side = 'right' if s == 'R' else 'left'
            knee = PB[f'{side}_shin'].head; fwd = PB[f'{side}_foot'].tail - PB[f'{side}_foot'].head; fwd.z = 0
            bf = PB['body'].matrix.to_3x3() @ (B('body').to_3x3().inverted() @ Vector((0, -1, 0))); bf.z = 0
            dv = (fwd.normalized() + bf.normalized()).normalized() if fwd.length > 1e-4 else bf.normalized()
            pb = PB[f'POLE_knee.{s}']; pb.matrix = Matrix.Translation(knee + dv * 3.75) @ pb.matrix.to_3x3().to_4x4(); vl.update()
            kp[s].append(pb.location.copy())
        for side in ('right', 'left'):
            fn, hn = f'{side}_forearm', f'{side}_hand'; tp = PB['TWIST.' + ('R' if side == 'right' else 'L')]
            def resid(tau):
                tp.rotation_euler = (0, tau, 0); vl.update()
                r = PB[fn].matrix.to_3x3().inverted() @ PB[hn].matrix.to_3x3(); q = (r @ r0[side].inverted()).to_quaternion()
                return (2 * math.atan2(q.y, q.w) + math.pi) % (2 * math.pi) - math.pi, q.angle
            tau = prev[side]
            for it in range(8):
                d, ang = resid(tau)
                if abs(d) < 0.002: break
                d2, ang2 = resid(tau + d); tau = tau + d if ang2 <= ang else tau - d
            tau = max(-TMAX, min(TMAX, tau)); wr[side].append(math.degrees(resid(tau)[1]))
            prev[side] = tau; tw[side].append(tau)
    # forearm roll must never flip: spread any jump over neighbouring frames, then a light zero-phase smooth.
    # (the hand's own orientation comes from IK_hand, so this only changes how the roll is shared along the forearm)
    for s_ in tw:
        v = tw[s_]
        for _ in range(3):
            for i in range(1, len(v)):
                if abs(v[i] - v[i - 1]) > math.radians(30):
                    a, b = max(0, i - 3), min(len(v) - 1, i + 2)
                    for j in range(a + 1, b): v[j] = v[a] + (v[b] - v[a]) * (j - a) / (b - a)
        if len(v) > 4:
            w = v[:]
            for i in range(1, len(v) - 1): w[i] = (v[i - 1] + 2 * v[i] + v[i + 1]) / 4
            tw[s_] = w
    if loopy:
        for s in tw: tw[s][-1] = tw[s][0]
        for s in kp: kp[s][-1] = kp[s][0]
    for side in ('right', 'left'):
        pb = PB['TWIST.' + ('R' if side == 'right' else 'L')]
        for f, tau in enumerate(tw[side]):
            pb.rotation_euler = (0, tau, 0); pb.keyframe_insert('rotation_euler', index=1, frame=f, group=pb.name)
            CUR['eases'][(pb.name, float(f))] = 'linear'
        print('CHECK', CUR['name'], side, 'wrist bend after roll max %.0f mean %.0f' % (max(wr[side]), sum(wr[side]) / len(wr[side])))
    for s in knees:
        pb = PB[f'POLE_knee.{s}']
        for f, loc in enumerate(kp[s]):
            pb.location = loc; pb.keyframe_insert('location', frame=f, group=pb.name); CUR['eases'][(pb.name, float(f))] = 'linear'

def finish(back=1.4):
    A = CUR['action']; loop = CUR['loop'] == 'loop'
    solve_frames()
    for fc in _fcurves(A):
        n = fc.data_path.split('"')[1] if '"' in fc.data_path else None
        dense = any(k in fc.data_path for k in ('TWIST', 'POLE_', 'IK_hand', 'CROWN', 'constraints'))
        for kp in fc.keyframe_points:
            interp, easing = EASE['linear'] if dense else EASE[CUR['eases'].get((n, round(kp.co[0], 4)), 'smooth')]
            kp.interpolation = interp; kp.easing = easing
            if interp == 'BACK': kp.back = back
            kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
        if loop and not dense: fc.modifiers.new('CYCLES')
        fc.update()
    A.frame_range = (0, CUR['length'] * FPS); A.use_frame_range = True; A.use_cyclic = loop
    A['bb_loop'] = CUR['loop']; A['bb_length'] = CUR['length']
    import json; A['events'] = json.dumps(CUR['events'])
    print('ANIM', A.name, 'length', CUR['length'], 'fcurves', len(_fcurves(A)))
