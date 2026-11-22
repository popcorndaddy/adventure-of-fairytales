"""Authoring helpers for the Sentinel actions.  Values are written in Blockbench terms (pixels, y up,
front = -z, additive degrees on top of the rest pose) and converted to Blender pose-bone keys.
FK bones get sparse keys with chosen easing; IK controls (feet, hands) are keyed from world-space
targets, optionally riding on a torso bone so they follow it."""
import bpy, math
from mathutils import Matrix, Vector, Euler, Quaternion
import bbmath as BM
from bbmath import G, GI, BONES, WREST, local_bb, rot_bb, frame_from

FPS = 20
rig = bpy.data.objects['Sentinel_Rig']; PB = rig.pose.bones; AB = rig.data.bones
sc = bpy.context.scene
CAPE = {'cape', 'cape_mid', 'cape_mid_low', 'cape_left', 'cape_left_low', 'cape_right', 'cape_right_low'}
IK_DRIVEN = {f'{s}_{p}' for s in ('right', 'left') for p in ('arm', 'forearm', 'hand', 'leg', 'shin', 'foot')}
FK_BONES = [n for n in BM.ORDER if n not in IK_DRIVEN and n not in CAPE and n != 'root']
CUR = {}

def B(n): return AB[n].matrix_local
def V(*a): return Vector(a[0] if len(a) == 1 else a)

# ------------------------------------------------------------------ conversions
def basis_from_K(n, Kbb, parent_K=None):
    """pose basis of bone n whose skin transform should be Kbb (bb world rest -> posed). parent_K: parent's Kbb (None = parent unposed)."""
    Kb = G @ Kbb @ GI
    Kp = (G @ parent_K @ GI) if parent_K is not None else Matrix.Identity(4)
    return B(n).inverted() @ Kp.inverted() @ Kb @ B(n)

def fk_basis(n, rot=(0, 0, 0), pos=(0, 0, 0)):
    p = BONES[n]['parent']; Wp = WREST[p] if p else Matrix.Identity(4)
    K_rel = Wp @ local_bb(n, rot, pos) @ local_bb(n).inverted() @ Wp.inverted()
    return B(n).inverted() @ (G @ K_rel @ GI) @ B(n)

def K_now(n):
    """bb skin transform of a deform bone at the current evaluated frame."""
    pb = PB[n]
    return GI @ (pb.matrix @ B(n).inverted()) @ G
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
    CUR.clear(); CUR.update(name=name, length=length, loop=loop, eases={}, action=A)
    return A

EASE = {  # segment leaving a key: (interpolation, easing)
    'smooth': ('BEZIER', 'AUTO'), 'linear': ('LINEAR', 'AUTO'), 'hold': ('CONSTANT', 'AUTO'),
    'in': ('CUBIC', 'EASE_IN'), 'in2': ('QUAD', 'EASE_IN'), 'in4': ('QUART', 'EASE_IN'), 'expo_in': ('EXPO', 'EASE_IN'),
    'out': ('CUBIC', 'EASE_OUT'), 'out2': ('QUAD', 'EASE_OUT'), 'out4': ('QUART', 'EASE_OUT'), 'expo_out': ('EXPO', 'EASE_OUT'),
    'inout': ('SINE', 'EASE_IN_OUT'), 'inout3': ('CUBIC', 'EASE_IN_OUT'), 'back': ('BACK', 'EASE_OUT'), 'back_in': ('BACK', 'EASE_IN'),
    'circ_out': ('CIRC', 'EASE_OUT'),
}

def _key(n, basis, t, ease, prev):
    pb = PB[n]; loc, q, _ = basis.decompose()
    e = q.to_euler('XYZ', prev) if prev is not None else q.to_euler('XYZ')
    pb.location = loc; pb.rotation_euler = e
    f = round(t * FPS, 4)
    pb.keyframe_insert('location', frame=f, group=n); pb.keyframe_insert('rotation_euler', frame=f, group=n)
    CUR['eases'][(n, f)] = ease
    return e

def _keys(n, items):
    """items: [(t, basis, ease)] in time order."""
    prev = None
    for t, basis, ease in sorted(items, key=lambda k: k[0]):
        prev = _key(n, basis, t, ease, prev)

def fk(n, keys):
    """keys: [(t, rot, pos, ease)] bb additive.  rot/pos may be None (=0)."""
    _keys(n, [(k[0], fk_basis(n, k[1] or (0, 0, 0), (k[2] if len(k) > 2 and k[2] else (0, 0, 0))), k[3] if len(k) > 3 else 'smooth') for k in keys])

def ride(space, t_world_rest):
    """turn a rest-world (bb) transform into the current world, following torso bone `space` (None = world)."""
    if not space: return t_world_rest
    return K_now(space) @ t_world_rest

# --- feet
def foot_K(side, spec):
    """spec: d=(dx,dy,dz) move of the flat foot, yaw (deg, + turns toes to his left), pitch (deg, + = toes up), pivot 'heel'|'toe'|'ankle', roll (deg)."""
    s = 'right' if side == 'R' else 'left'
    ank = V(BONES[f'{s}_foot']['head']); Wf = WREST[f'{s}_foot']
    toe = (Wf @ V(*BM.D['foot'][s]['toe'], 1)).xyz; heel = (Wf @ V(*BM.D['foot'][s]['heel'], 1)).xyz
    d = V(*spec.get('d', (0, 0, 0)))
    pit = spec.get('pitch', 0)
    piv = {'heel': heel, 'toe': toe, 'ankle': ank}[spec.get('pivot', 'heel' if pit > 0 else 'toe')] if pit else ank
    ypiv = piv if spec.get('yaw_on_pivot', True) else ank
    M = Matrix.Translation(d) @ Matrix.Translation(ypiv) @ rot_bb((0, spec.get('yaw', 0), spec.get('roll', 0))).to_4x4() @ Matrix.Translation(-ypiv)
    if pit:
        piv_w = (M @ V(*piv, 1)).xyz
        ax = (M.to_3x3() @ V(1, 0, 0)).normalized()
        R = Matrix.Rotation(math.radians(pit), 4, ax)
        M = Matrix.Translation(piv_w) @ R @ Matrix.Translation(-piv_w) @ M
    return M

def feet(side, keys):
    """keys: [(t, spec, ease)]"""
    n = f'IK_foot.{side}'
    _keys(n, [(t, basis_from_K(n, foot_K(side, spec)), ease) for t, spec, ease in keys])

# --- hands
SWORD_GRIP_L = V(*BM.D['sword']['grip'])
def sword_add(mode, tilt=0.0, spin=0.0):
    return (tilt, -180.0 + spin, 0.0) if mode == 'sword' else (tilt, spin, 0.0)

REST_BLADE = {}
def _rest_sword(mode):
    if mode not in REST_BLADE:
        Wh = WREST['right_hand']; Ws = Wh @ local_bb('sword', sword_add(mode))
        R = Ws.to_3x3(); REST_BLADE[mode] = ((R @ V(0, 0, -1)).normalized(), (R @ V(1, 0, 0)).normalized())
    return REST_BLADE[mode]
def auto_flat(blade, mode, Rdelta=None):
    """edge orientation a relaxed wrist gives: the rest grip, carried along by the torso's turn (Rdelta), swung by the
    shortest rotation onto `blade`."""
    b0, f0 = _rest_sword(mode)
    if Rdelta is not None: b0, f0 = Rdelta @ b0, Rdelta @ f0
    q = b0.rotation_difference(V(*blade).normalized()); return tuple(q @ f0)

def hand_K_from_sword(grip, blade, flat, mode, tilt=0.0, spin=0.0):
    Ws = frame_from(SWORD_GRIP_L, grip, (V(0, 0, -1), V(1, 0, 0)), (V(*blade), V(*flat)))
    Wh = Ws @ local_bb('sword', sword_add(mode, tilt, spin)).inverted()
    return Wh @ WREST['right_hand'].inverted()

def palm_local(s): return V(BONES[f'{s}_hand']['pivot']) + V(0, -2.0, 0)
def hand_K_from_palm(side, palm, fingers, normal):
    s = 'right' if side == 'R' else 'left'
    Wh = frame_from(palm_local(s), palm, (V(0, -1, 0), V(1, 0, 0)), (V(*fingers), V(*normal)))
    return Wh @ WREST[f'{s}_hand'].inverted()

def hand_K_offset(side, d=(0, 0, 0), r=(0, 0, 0)):
    """move/rotate the hand from its rest pose about the palm centre (bb world)."""
    s = 'right' if side == 'R' else 'left'
    pc = (WREST[f'{s}_hand'] @ V(*palm_local(s), 1)).xyz
    return Matrix.Translation(pc + V(*d)) @ rot_bb(r).to_4x4() @ Matrix.Translation(-pc)

def hands(side, keys, sword_keys=True):
    """keys: [(t, spec, ease)]; spec: {'sword': (grip, blade, flat, mode[, tilt, spin])} | {'palm': (pos, fingers, normal)}
       | {'off': (d, r)}; plus optional 'space': torso bone the target rides on (targets given in rest-world)."""
    n = f'IK_hand.{side}'; items = []; sw = []
    for t, spec, ease in sorted(keys, key=lambda k: k[0]):
        if 'sword' in spec:
            g, b, f, mode, *rest = spec['sword']; tilt = rest[0] if rest else 0.0; spin = rest[1] if len(rest) > 1 else 0.0
            if f is None:
                Rd = None
                if not spec.get('space'):  # world target: judge the wrist against where the chest is turned right now
                    eval_at(t); Rd = K_now('chest').to_3x3()
                f = auto_flat(b, mode, Rd)
            K = hand_K_from_sword(V(*g), b, f, mode, tilt, spin); sw.append((t, sword_add(mode, tilt, spin), None, ease))
        elif 'palm' in spec:
            K = hand_K_from_palm(side, V(*spec['palm'][0]), spec['palm'][1], spec['palm'][2])
        else:
            K = hand_K_offset(side, *spec['off'])
        if spec.get('space'):
            eval_at(t); K = ride(spec['space'], K)
        items.append((t, basis_from_K(n, K), ease))
    _keys(n, items)
    if sword_keys and sw and side == 'R': fk('sword', sw)

def pole(name, keys):
    """keys: [(t, bb world point (rest torso), ease)] - poles ride on their parent automatically."""
    items = []
    for t, p, ease in keys:
        par = AB[name].parent.name
        rest_head = (GI @ V(*AB[name].head_local, 1)).xyz
        off = V(*p) - rest_head
        Kbb = Matrix.Translation(off)
        items.append((t, B(name).inverted() @ (G @ Kbb @ GI) @ B(name), ease))
    _keys(name, items)

# ------------------------------------------------------------------ finishing
def _fcurves(A):
    try:
        from bpy_extras.anim_utils import action_get_channelbag_for_slot
        cb = action_get_channelbag_for_slot(A, A.slots[0]); return cb.fcurves
    except Exception:
        return A.fcurves

def _has_keys(A, bone):
    return any(f'"{bone}"' in fc.data_path for fc in _fcurves(A))

def _clear_keys(A, bone):
    for fc in list(_fcurves(A)):
        if f'"{bone}"' in fc.data_path:
            try: fc.keyframe_points.clear()
            except Exception:
                while len(fc.keyframe_points): fc.keyframe_points.remove(fc.keyframe_points[0])

def solve_arms():
    """per frame, choose where each elbow points (and, for the sword hand, how far the grip may roll about the blade)
    so the forearm lines up with the hand: the wrist stays close to natural.  Keys the hand controls and elbow poles
    every frame; the sparse authored keys define the targets."""
    A = CUR['action']; nfr = int(round(CUR['length'] * FPS)); vl = bpy.context.view_layer
    res = {}
    for side, s in (('right', 'R'), ('left', 'L')):
        L1 = AB[f'{side}_arm'].length; L2 = AB[f'{side}_forearm'].length
        Bh = AB[f'{side}_hand'].matrix_local.to_3x3()
        a_h = Bh.inverted() @ AB[f'{side}_forearm'].matrix_local.col[1].xyz.normalized()
        res[side] = []; prev = None
        loopy = CUR['loop'] == 'loop'
        frames = (list(range(nfr + 1)) * 2) if loopy else list(range(nfr + 1))
        for pass_i, f in enumerate(frames):
            if loopy and pass_i == nfr + 1: res[side] = []
            sc.frame_set(f)
            S = PB[f'{side}_arm'].head.copy(); Mc = PB[f'IK_hand.{s}'].matrix.copy()
            spine0 = PB['chest'].head.copy(); spine_d = PB['chest'].y_axis.normalized()
            if side == 'right':
                G = PB['sword'].head.copy(); bdir = PB['sword'].y_axis.normalized(); psis = [math.radians(a) for a in range(-90, 91, 10)]
            else:
                G = Mc.translation.copy(); bdir = Vector((0, 0, 1)); psis = [0.0]
            best = None
            perts = [Matrix.Identity(4)]
            if side == 'right':
                q0 = bdir.orthogonal().normalized(); q1 = bdir.cross(q0).normalized()
                for ang in (12, 24):
                    for k in range(6):
                        axv = q0 * math.cos(k * math.pi / 3) + q1 * math.sin(k * math.pi / 3)
                        perts.append(Matrix.Translation(G) @ Matrix.Rotation(math.radians(ang), 4, axv) @ Matrix.Translation(-G))
            for pi_, Pm in enumerate(perts):
              dev = 0.0 if pi_ == 0 else (12 if pi_ <= 6 else 24)
              for psi in psis:
                Rp = Matrix.Rotation(psi, 4, bdir)
                M2 = Pm @ Matrix.Translation(G) @ Rp @ Matrix.Translation(-G) @ Mc
                Wp = M2.translation; want = (M2.to_3x3() @ a_h).normalized()
                dv = Wp - S; d = min(dv.length, (L1 + L2) * 0.999); u = dv.normalized()
                x = (L1 * L1 - L2 * L2 + d * d) / (2 * d); r = math.sqrt(max(0.0, L1 * L1 - x * x))
                v0 = (Vector((0, 0, -1)) - u * u.dot(Vector((0, 0, -1))))
                if v0.length < 1e-3: v0 = Vector((1, 0, 0)) - u * u.x
                v0.normalize(); v1 = u.cross(v0)
                for k in range(36):
                    ph = k * math.pi / 18
                    E = S + u * x + (v0 * math.cos(ph) + v1 * math.sin(ph)) * r
                    fd = (Wp - E).normalized()
                    sw = math.acos(max(-1, min(1, fd.dot(want))))
                    rel = E - spine0; lat = (rel - spine_d * rel.dot(spine_d)).length
                    cost = sw * sw + 4.0 * max(0.0, 1.45 - lat) ** 2 + 0.06 * psi * psi + 0.9 * math.radians(dev) ** 2
                    cost += 0.4 * max(0.0, -math.cos(ph)) ** 2
                    if prev is not None:
                        dph = abs((ph - prev[0] + math.pi) % (2 * math.pi) - math.pi)
                        cost += 1.2 * dph ** 2 + 2.0 * (psi - prev[1]) ** 2 + 1.5 * math.radians(abs(dev - prev[2])) ** 2 + (50.0 if dph > 0.45 else 0.0)
                    if best is None or cost < best[0]: best = (cost, ph, psi, M2, E, S + u * x, sw, dev)
            prev = (best[1], best[2], best[7]); res[side].append(best)
        if loopy: res[side][-1] = res[side][0]
    for side, s in (('right', 'R'), ('left', 'L')):
        _clear_keys(A, f'IK_hand.{s}'); _clear_keys(A, f'POLE_elbow.{s}')
        pc, pp = PB[f'IK_hand.{s}'], PB[f'POLE_elbow.{s}']; pe = None
        for f, (cost, ph, psi, M2, E, Cc, sw, dev) in enumerate(res[side]):
            sc.frame_set(f)
            pc.matrix = M2; vl.update()
            e = pc.rotation_euler.copy()
            if pe is not None: e.make_compatible(pe)
            pc.rotation_euler = e; pe = e.copy(); CUR.setdefault('ctrl_e', {}).setdefault(s, {})[f] = e.copy()
            pc.keyframe_insert('location', frame=f, group=pc.name); pc.keyframe_insert('rotation_euler', frame=f, group=pc.name)
            P = E + (E - Cc).normalized() * 2.5          # same convention the rig's pole angle was calibrated with
            pp.matrix = Matrix.Translation(P) @ pp.matrix.to_3x3().to_4x4(); vl.update()
            pp.keyframe_insert('location', frame=f, group=pp.name)
            CUR['eases'][(pc.name, float(f))] = 'linear'; CUR['eases'][(pp.name, float(f))] = 'linear'
        sws = [math.degrees(r[6]) for r in res[side]]
        print('CHECK', CUR['name'], side, 'forearm-to-hand misalignment: max %.0f mean %.0f deg' % (max(sws), sum(sws) / len(sws)))

def solve_twist_and_knees():
    """per frame: turn each forearm about its own axis so the wrist stays natural, and aim each knee pole along its
    foot so the knee follows the toes.  Keys every frame (IK bones are baked anyway)."""
    A = CUR['action']; nfr = int(round(CUR['length'] * FPS)); vl = bpy.context.view_layer
    knees = [s for s in ('R', 'L') if not _has_keys(A, f'POLE_knee.{s}')]
    tw = {s: [] for s in ('right', 'left')}; kp = {s: [] for s in knees}; prev = {'right': 0.0, 'left': 0.0}
    r0 = {s: B(f'{s}_forearm').to_3x3().inverted() @ B(f'{s}_hand').to_3x3() for s in ('right', 'left')}
    loopy = CUR['loop'] == 'loop'
    order = (list(range(nfr + 1)) * 2) if loopy else list(range(nfr + 1))
    for pass_i, f in enumerate(order):
        if loopy and pass_i == nfr + 1:
            tw = {s: [] for s in ('right', 'left')}; kp = {s: [] for s in knees}
            CUR.pop('wrist_right', None); CUR.pop('wrist_left', None)
        sc.frame_set(f)
        for s in knees:
            side = 'right' if s == 'R' else 'left'
            knee = PB[f'{side}_shin'].head; fm = PB[f'{side}_foot'].matrix
            fwd = (PB[f'{side}_foot'].tail - PB[f'{side}_foot'].head); fwd.z = 0
            body_fwd = (PB['body'].matrix.to_3x3() @ (B('body').to_3x3().inverted() @ Vector((0, -1, 0)))); body_fwd.z = 0
            dirv = (fwd.normalized() + body_fwd.normalized()).normalized() if fwd.length > 1e-4 else body_fwd.normalized()
            want = knee + dirv * 3.75
            pb = PB[f'POLE_knee.{s}']; pb.matrix = Matrix.Translation(want) @ pb.matrix.to_3x3().to_4x4(); vl.update()
            kp[s].append(pb.location.copy())
        for side in ('right', 'left'):
            fn, hn = f'{side}_forearm', f'{side}_hand'; S_ = 'R' if side == 'right' else 'L'; tp = PB['TWIST.' + S_]; pc = PB[f'IK_hand.{S_}']
            def resid(tau):
                tp.rotation_euler = (0, tau, 0); vl.update()
                r = PB[fn].matrix.to_3x3().inverted() @ PB[hn].matrix.to_3x3()
                q = (r @ r0[side].inverted()).to_quaternion()
                tw_ = 2 * math.atan2(q.y, q.w)
                return (tw_ + math.pi) % (2 * math.pi) - math.pi, q.angle
            def solve(t0):
                tau = t0
                for it in range(8):
                    d, ang = resid(tau)
                    if abs(d) < 0.002: break
                    d2, ang2 = resid(tau + d)
                    tau = tau + d if ang2 <= ang else tau - d
                return tau
            TMAX = math.radians(115)
            tau = solve(prev[side])
            if abs(tau) > TMAX:
                M0 = pc.matrix.copy(); best = None
                if side == 'right':      # roll the grip about the blade until the forearm can follow
                    G = PB['sword'].head.copy(); bd = PB['sword'].y_axis.normalized()
                    angs = list(range(-150, 151, 15))
                    cands = [Matrix.Translation(G) @ Matrix.Rotation(math.radians(a), 4, bd) @ Matrix.Translation(-G) @ M0 for a in angs]
                else:                    # the claw can't turn that far: let it settle where the forearm stops
                    ex = tau - math.copysign(TMAX, tau); W = PB[fn].tail.copy(); ax = PB[fn].y_axis.normalized()
                    angs = [0]; cands = [Matrix.Translation(W) @ Matrix.Rotation(-ex, 4, ax) @ Matrix.Translation(-W) @ M0]
                pa = CUR.setdefault('roll_prev', {}).get(side, 0)
                for a_, Mc in zip(angs, cands):
                    pc.matrix = Mc; vl.update(); tt = solve(prev[side]); dd, ang = resid(max(-TMAX, min(TMAX, tt)))
                    c = ang + 2.0 * max(0.0, abs(tt) - TMAX) + 0.0004 * (a_ - pa) ** 2
                    if best is None or c < best[0]: best = (c, Mc, tt, a_)
                CUR['roll_prev'][side] = best[3]
                pc.matrix = best[1]; vl.update()
                e = pc.rotation_euler.copy(); ce = CUR.get('ctrl_e', {}).get(S_, {})
                if f - 1 in ce: e.make_compatible(ce[f - 1])
                pc.rotation_euler = e; ce[f] = e.copy()
                pc.keyframe_insert('location', frame=f, group=pc.name); pc.keyframe_insert('rotation_euler', frame=f, group=pc.name)
                tau = best[2]
            tau = max(-TMAX, min(TMAX, tau)); resid(tau)
            CUR.setdefault('wrist_' + side, []).append(math.degrees(resid(tau)[1]))
            prev[side] = tau; tw[side].append(tau)
    if loopy:
        for side in tw: tw[side][-1] = tw[side][0]
        for s in kp: kp[s][-1] = kp[s][0]
    for side in ('right', 'left'):
        pb = PB['TWIST.' + ('R' if side == 'right' else 'L')]
        for f, tau in enumerate(tw[side]):
            pb.rotation_euler = (0, tau, 0); pb.keyframe_insert('rotation_euler', index=1, frame=f, group=pb.name)
            CUR['eases'][(pb.name, float(f))] = 'linear'
    for side in ('right', 'left'):
        w = CUR.get('wrist_' + side, [0]); print('CHECK', CUR['name'], side, 'wrist bend after twist: max %.0f mean %.0f deg' % (max(w), sum(w) / len(w)))
    for s in knees:
        pb = PB[f'POLE_knee.{s}']
        for f, loc in enumerate(kp[s]):
            pb.location = loc; pb.keyframe_insert('location', frame=f, group=pb.name); CUR['eases'][(pb.name, float(f))] = 'linear'

def finish(back=1.4):
    A = CUR['action']; loop = CUR['loop'] == 'loop'
    solve_arms()
    solve_twist_and_knees()
    for fc in _fcurves(A):
        n = fc.data_path.split('"')[1] if '"' in fc.data_path else None
        for kp in fc.keyframe_points:
            ease = CUR['eases'].get((n, round(kp.co[0], 4)), 'smooth')
            interp, easing = EASE[ease]
            kp.interpolation = interp; kp.easing = easing
            if interp == 'BACK': kp.back = back
            kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
        if loop and not any(k in fc.data_path for k in ('TWIST', 'POLE_', 'IK_hand')):
            m = fc.modifiers.new('CYCLES')
        fc.update()
    A.frame_range = (0, CUR['length'] * FPS); A.use_frame_range = True; A.use_cyclic = loop
    A['bb_loop'] = CUR['loop']; A['bb_length'] = CUR['length']
    print('ANIM', A.name, 'length', CUR['length'], 'fcurves', len(_fcurves(A)))

# ------------------------------------------------------------------ small motion helpers
def lerp(a, b, u): return tuple(x + (y - x) * u for x, y in zip(a, b))
def add3(*vs): return tuple(sum(v[i] for v in vs) for i in range(3))
def sc3(v, k): return tuple(x * k for x in v)
