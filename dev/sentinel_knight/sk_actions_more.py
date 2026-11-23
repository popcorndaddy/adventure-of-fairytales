# walk, sweep, push, stomp, dash, summon_start/loop/end, awaken, death.
# Executed inside sk_anims.py (uses action, K, track, wave, bump, smooth, combat_base, merged, heartbeat, dir_az_el ...).
# Ticks: these frame numbers are the event ticks used by withered_sentinel.js.

LEFT_HANG = dict(hand=(14.5, -3.0, 34.0), point=(0.1, -0.2, -1.0), palm=(-1.0, 0.1, 0.0), elbow=(0.5, 0.6, -0.2))


def lerpP(a, b, w):
    """Blend two pose dicts value by value (numbers / tuples / nested dicts)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return {k: lerpP(a.get(k, b.get(k)), b.get(k, a.get(k)), w) for k in set(a) | set(b)}
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return a + (b - a) * w
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)) and len(a) == len(b):
        return tuple(lerpP(x, y, w) for x, y in zip(a, b))
    return a if w < 0.5 else b


def sword_dir(az, el):
    return tuple(dir_az_el(az, el))


# ====================================================================== WALK (2.4 s loop, two heavy steps; no foot sliding)
NW, STEP = 48, 21.6
VW = 2 * STEP / NW                     # 0.9 px per tick: a planted foot moves back at exactly this speed
STANCE, YC = 28, -11.0


def foot_walk(S, f):
    t = (f - (0 if S == "R" else NW // 2)) % NW
    x = -6.5 if S == "R" else 6.5
    if t <= STANCE:
        y = YC + VW * t
        if t < 4:
            return (x, y), 0.0, 0.0, -10 * (1 - smooth(t / 4))                  # heel strike, toe still up
        if t > STANCE - 7:
            return (x, y), 0.0, 0.0, 26 * ease_in((t - (STANCE - 7)) / 7)       # heel peels, ball planted
        return (x, y), 0.0, 0.0, 0.0
    s = (t - STANCE) / (NW - STANCE)
    y0 = YC + VW * STANCE
    y = y0 + (YC - y0) * smooth(s)
    lift = 5.5 * math.sin(math.pi * min(1.0, s ** 0.8))
    p = track([(0, 26), (0.35, 8), (0.75, -6), (1.0, -10)], s)
    return (x, y), lift, 0.0, p


@action
def walk():
    def fn(r, f):
        u = (f % (NW // 2)) / (NW // 2)
        ph = 2 * math.pi * (f + 5) / NW
        hz = track([(0, 0, "c"), (0.15, -1.6, "c"), (0.45, 0.7, "c"), (0.7, 0.3, "c"), (1.0, 0, "c")], u)
        hx = -1.7 * math.sin(ph)
        yaw = -6.0 * math.sin(ph)
        fR, fL = foot_walk("R", f), foot_walk("L", f)
        armR = fR[0][1] / 14.0; armL = fL[0][1] / 14.0                         # arms counter-swing the legs
        impact = bump(u, 0.12, 0.07)
        G = (-13.0 + 0.5 * hx, -3.0 - 3.0 * armR, 37.5 + 0.7 * hz)
        hs, gs = heartbeat(f / 20.0, 50, 0.9)
        K.pose(r, merged(
            body=(hx, 0.0, -1.0 + hz), hips=(6.0 + 1.2 * impact, 2.2 * math.sin(ph), yaw),
            spine=(2.0, -0.8 * math.sin(ph), -0.5 * yaw), chest=(2.0 + 1.5 * impact, -0.6 * math.sin(ph), -1.1 * yaw),
            head=(0.0, 6.0 + 2.0 * bump(u, 0.2, 0.1), 0.0), shrug_R=1.5 * impact, shrug_L=1.5 * impact,
            foot_R=fR, foot_L=fL,
            sword=dict(grip=G, dir=sword_dir(-24 + 5 * armR, -34 + 4 * armR), flat=(1.0, 0.0, 0.3), two=False,
                       elbow_R=(-0.8, 0.5, -0.3)),
            arm_L=dict(hand=(14.6 - 0.4 * hx, -2.0 - 6.5 * armL, 34.5), point=(0.1, -0.15 - 0.3 * armL, -1.0), palm=(-1.0, 0.1, 0.0),
                       elbow=(0.5, 0.6, -0.2)),
            curl_R=1.0, curl_L=0.45 + 0.1 * math.sin(ph * 2), spread_L=0.15, thumb_L=0.5,
            heart=(hs, gs)))
    return NW, fn, "true"


# ====================================================================== SWEEP (50 ticks, blade crosses his front on tick 24)
@action
def sweep():
    N = 50
    G = [(0, (-3.0, -13.0, 41.0)), (8, (-11.0, -2.0, 52.0)), (14, (-12.0, 4.0, 57.0)), (18, (-12.5, 4.5, 58.0), "i"),
         (21, (-9.0, -10.0, 48.0), "l"), (24, (2.0, -15.0, 44.0), "l"), (27, (12.0, -7.0, 43.0), "o"), (32, (15.0, 3.0, 45.0)),
         (38, (12.0, -2.0, 44.0)), (50, (-3.0, -13.0, 41.0))]
    AZ = [(0, 6), (8, -95), (14, -150), (18, -158, "i"), (21, -70, "l"), (24, 8, "l"), (27, 70, "o"), (32, 118), (38, 100), (50, 6)]
    EL = [(0, 28), (8, 28), (14, 22), (18, 20, "i"), (21, 4, "l"), (24, -4, "l"), (27, -12, "o"), (32, -24), (38, -10), (50, 28)]
    HY = [(0, -14), (10, -34), (18, -40, "i"), (21, -12, "l"), (24, 18, "l"), (28, 34, "o"), (34, 36), (50, -14)]
    CY = [(0, 6), (10, -24), (18, -32, "i"), (21, 0, "l"), (24, 24, "l"), (28, 34, "o"), (34, 30), (50, 6)]
    BX = [(0, 0), (14, -2.2), (18, -2.4), (24, 1.8, "o"), (32, 2.2), (50, 0)]
    BY = [(0, 1.0), (14, 3.0), (18, 3.2), (24, -2.0, "o"), (32, -1.5), (50, 1.0)]
    BZ = [(0, -4.0), (14, -6.0), (18, -6.4), (22, -5.0), (25, -7.2, "o"), (32, -6.0), (50, -4.0)]
    HEEL = [(0, 0), (22, 0), (27, 30, "o"), (34, 26), (44, 0), (50, 0)]
    PIV = [(0, -28), (22, -28), (28, -2, "o"), (40, -10), (50, -28)]

    def fn(r, f):
        P = combat_base(0)
        coil = smooth((f - 12) / 4) * (1 - smooth((f - 19) / 1.5))
        tremble = 0.8 * math.sin(f * 2.6) * coil
        P.update(body=(track(BX, f), track(BY, f), track(BZ, f)), hips=(9.0 + 3 * bump(f, 25, 3), 0.0, track(HY, f)),
                 chest=(3.0 + 4 * bump(f, 25, 3), 0.0, track(CY, f) + tremble), spine=(2.0, 0.0, 0.5 * track(CY, f)),
                 head=(-track(HY, f) - track(CY, f) * 0.6 + 12 - 6 * bump(f, 26, 5), 4.0, 0.0))
        P["foot_R"] = ((-8.0, 5.0), 0.0, track(PIV, f), track(HEEL, f))
        g = track(G, f)
        P["sword"] = dict(grip=g, dir=sword_dir(track(AZ, f), track(EL, f)), flat=(0.0, 0.0, 1.0), two=True,
                          elbow_R=(-0.6, 0.6, -0.5), elbow_L=(0.6, 0.6, -0.5))
        P["curl_R"] = P["curl_L"] = 1.0 + 0.12 * bump(f, 23, 4)
        amp = 1.0 + 0.9 * smooth((f - 8) / 10) * (1 - smooth((f - 28) / 12))
        P["heart"] = heartbeat(f / 20.0, 110 + 40 * coil, amp)
        K.pose(r, merged(**P))
    return N, fn, "false"


# ====================================================================== PUSH (40 ticks, palm strike on tick 20)
@action
def push():
    N = 40

    def fn(r, f):
        P = combat_base(0)
        coil = smooth(f / 12) * (1 - smooth((f - 17) / 3))
        hit = smooth((f - 17) / 3) * (1 - smooth((f - 28) / 12))
        back = 1 - smooth((f - 30) / 10)
        P.update(body=(-0.8 * coil, 1.0 + 2.5 * coil - 4.0 * hit, -4.0 - 1.2 * coil - 1.5 * hit),
                 hips=(9.0 - 6 * coil + 9 * hit, 0.0, -14.0 - 14 * coil + 18 * hit),
                 chest=(3.0 - 5 * coil + 5 * hit, 0.0, 6.0 - 16 * coil + 14 * hit),
                 head=(10 + 8 * coil - 6 * hit, 6.0 - 4 * hit, 3 * coil), shrug_L=4 * coil)
        P["foot_L"] = ((7.0, -7.0 - 7.0 * smooth((f - 15) / 5) * back), 3.0 * bump(f, 17.5, 1.6), 12, 0)
        P["foot_R"] = ((-8.0, 5.0), 0.0, -28, 26 * hit)
        # sword drops to his right side, one-handed, while the claw does the work
        sw = smooth(f / 6) * (1 - smooth((f - 32) / 8))
        base_g = (-3.0, -13.0, 41.0)
        P["sword"] = dict(grip=lerpP(base_g, (-13.0, -2.0, 38.0), sw), dir=sword_dir(lerpP(6, -30, sw), lerpP(28, -30, sw)),
                          flat=(1.0, 0.0, 0.2), two=True, two_w=1 - smooth(f / 4) + smooth((f - 34) / 6))
        if 2 <= f <= 37:
            cocked = dict(hand=(9.0, -1.0, 52.0), point=(0.0, -0.5, 0.85), palm=(0.0, -1.0, 0.1), elbow=(0.8, 0.6, -0.5))
            thrust = dict(hand=(3.0, -27.0, 50.0), point=(0.0, -0.05, 1.0), palm=(0.0, -1.0, 0.0), elbow=(0.6, 0.2, -0.8))
            rest = dict(hand=(10.0, -9.0, 40.0), point=(0.1, -0.5, -0.8), palm=(-0.6, -0.2, 0.0), elbow=(0.6, 0.6, -0.4))
            a = lerpP(rest, cocked, smooth((f - 2) / 10))
            a = lerpP(a, thrust, smooth((f - 16) / 4))
            a = lerpP(a, rest, smooth((f - 26) / 11))
            P["arm_L"] = a
            P["curl_L"] = 0.9 * coil + (-0.15) * hit + 0.6 * (1 - coil - hit) * (f > 26)
            P["spread_L"] = 1.0 * hit; P["thumb_L"] = 0.2
        P["heart"] = heartbeat(f / 20.0, 110, 1.0 + 0.9 * coil + 0.6 * hit)
        K.pose(r, merged(**P))
    return N, fn, "false"


# ====================================================================== STOMP (40 ticks, foot lands on tick 19)
@action
def stomp():
    N = 40
    LIFT = [(0, 0), (3, 0), (11, 15.0, "o"), (15, 16.0, "i"), (19, 0, "i"), (40, 0)]
    FY = [(0, 5.0), (11, -1.0), (15, -1.5, "i"), (19, 2.0, "i"), (32, 2.0), (40, 5.0)]
    BZ = [(0, -4.0), (4, -5.0), (12, -1.0), (15, -0.6, "i"), (19, -9.0, "o"), (23, -8.0), (32, -5.0), (40, -4.0)]
    LEAN = [(0, 9), (12, 2), (15, 1, "i"), (19, 22, "o"), (24, 18), (40, 9)]

    def fn(r, f):
        P = combat_base(0)
        apex = smooth((f - 10) / 3) * (1 - smooth((f - 16) / 1))
        trem = 1.2 * math.sin(f * 2.7) * apex + 2.0 * math.sin((f - 19) * 2.3) * math.exp(-max(0, f - 19) / 3.0) * (f >= 19)
        P.update(body=(2.6 * smooth(f / 10) * (1 - smooth((f - 19) / 5)), 1.0, track(BZ, f)),
                 hips=(track(LEAN, f), 5 * smooth(f / 10) * (1 - smooth((f - 19) / 4)), -14.0 + 6 * smooth(f / 10) * (1 - smooth((f - 24) / 12))),
                 chest=(3 + 0.5 * track(LEAN, f) - 6 * apex, 0.0, 6.0 + trem),
                 head=(10.0, 4.0 + 8 * bump(f, 20, 3), 0.0))
        P["foot_R"] = ((-7.5, track(FY, f)), track(LIFT, f), -20, -8 * apex)
        P["knee_R"] = (-0.3, -1.0, 0.0)
        raise_ = smooth((f - 2) / 9) * (1 - smooth((f - 17) / 2))
        P["sword"] = dict(grip=lerpP((-3.0, -13.0, 41.0), (-17.0, -6.0, 58.0), raise_), dir=sword_dir(lerpP(6, -60, raise_), lerpP(28, 55, raise_) - 70 * smooth((f - 17) / 2) * (1 - smooth((f - 30) / 10))),
                          flat=(0.3, 0.0, 1.0), two=True, two_w=1 - smooth((f - 2) / 4) + smooth((f - 30) / 8))
        if 3 <= f <= 37:
            out = dict(hand=(32.0, -3.0, 58.0), point=(0.9, 0.0, 0.4), palm=(0.0, -0.2, -1.0), elbow=(0.6, 0.6, -0.4))
            slam = dict(hand=(17.0, -10.0, 30.0), point=(0.2, -0.4, -0.9), palm=(-0.5, -0.3, 0.0), elbow=(0.6, 0.6, -0.3))
            a = lerpP(LEFT_HANG, out, smooth((f - 3) / 8))
            a = lerpP(a, slam, smooth((f - 16) / 3))
            a = lerpP(a, dict(hand=(8.0, -12.0, 40.0), point=(-0.3, -0.6, -0.6), palm=(-0.6, 0.3, 0.0), elbow=(0.6, 0.5, -0.4)), smooth((f - 26) / 11))
            P["arm_L"] = a
            P["curl_L"] = 0.3 + 0.6 * smooth((f - 16) / 3); P["spread_L"] = 0.8 * raise_
        P["heart"] = heartbeat(f / 20.0, 120, 1.0 + 1.2 * apex + 0.8 * bump(f, 20, 2))
        K.pose(r, merged(**P))
    return N, fn, "false"


# ====================================================================== DASH (32 ticks: crouch 0-7, explode 8-16, brake, recover)
@action
def dash():
    N = 32
    BZ = [(0, -4.0), (6, -9.0), (8, -9.4, "i"), (10, -3.0, "o"), (16, -4.0), (19, -8.0), (26, -5.0), (32, -4.0)]
    BY = [(0, 1.0), (6, 3.0), (8, 3.4, "i"), (11, -7.0, "o"), (16, -8.0), (20, -3.0), (32, 1.0)]
    LEAN = [(0, 9), (6, 20), (8, 22, "i"), (11, 32, "o"), (16, 28), (19, 2), (24, 4), (32, 9)]

    def fn(r, f):
        P = combat_base(0)
        P.update(body=(0.0, track(BY, f), track(BZ, f)), hips=(track(LEAN, f), 0.0, track([(0, -14), (7, -22), (11, -4, "o"), (20, -8), (32, -14)], f)),
                 chest=(3.0, 0.0, track([(0, 6), (7, -6), (11, 4, "o"), (32, 6)], f)),
                 head=(track([(0, 22), (7, 26), (11, 6, "o"), (32, 22)], f), track([(0, 4), (8, -6), (11, -10, "o"), (19, 2), (32, 4)], f), 0.0))
        P["foot_R"] = ((-8.0, track([(0, 5.0), (8, 5.0), (11, 9.0, "o"), (14, -2.0), (17, -9.0, "i"), (32, 5.0)], f)),
                       track([(0, 0), (10, 0), (12, 6.0), (15, 4.0), (17, 0, "i"), (24, 0), (27, 3.0), (30, 0)], f), -28,
                       track([(0, 0), (6, 14), (9, 52, "o"), (12, 8), (15, 0), (32, 0)], f))
        P["foot_L"] = ((7.0, track([(0, -7.0), (9, -7.0), (12, -3.0), (15, -16.0, "i"), (24, -16.0), (29, -7.0), (32, -7.0)], f)),
                       track([(0, 0), (9, 0), (11, 5.0), (13, 7.0), (15, 0, "i"), (24, 0), (26.5, 3.5), (29, 0), (32, 0)], f), 12,
                       track([(0, 0), (8, 0), (10, 20), (12, 0), (32, 0)], f))
        # the blade is drawn in close along his body, then driven forward like a lance through the lunge
        P["sword"] = dict(grip=track([(0, (-3.0, -13.0, 41.0)), (7, (-9.0, 2.0, 40.0)), (11, (-4.0, -16.0, 42.0), "o"), (17, (-4.0, -15.0, 41.0)), (32, (-3.0, -13.0, 41.0))], f),
                          dir=sword_dir(track([(0, 6), (7, -8), (11, 4, "o"), (32, 6)], f), track([(0, 28), (7, 8), (11, 2, "o"), (17, 6), (32, 28)], f)),
                          flat=(1.0, 0.0, 0.2), two=True, elbow_R=(-0.7, 0.6, -0.4), elbow_L=(0.7, 0.5, -0.5))
        P["shrug_R"] = P["shrug_L"] = 3 * bump(f, 7, 2.5)
        P["heart"] = heartbeat(f / 20.0, 140, 1.4 + 0.8 * bump(f, 9, 2.5))
        K.pose(r, merged(**P))
    return N, fn, "false"


# ====================================================================== SUMMON (start 40 ticks, loop 60 seamless, end 30)
SUMMON_TIP = (-12.0, -22.0, -6.0)          # sword driven into the stone in front of him (6 px deep)
SG = (-8.0, -14.0, 47.0)                   # right fist on the grip of the planted sword
HAND_UP = dict(hand=(18.0, -16.0, 70.0), point=(0.1, -0.35, 1.0), palm=(0.0, -1.0, 0.35), elbow=(0.9, 0.3, -0.4))


def summon_pose(f, k, br=0.0, loopf=None):
    """k = 0 combat guard -> 1 full summoning stance."""
    P = combat_base(0)
    sum_P = dict(body=(0.0, 0.0, -6.5 + 0.6 * br), hips=(8.0, 0.0, -6.0), spine=(-2.0 - 1.0 * br, 0.0, 2.0), chest=(-4.0 - 2.0 * br, 0.0, 4.0),
                 head=(10.0, -8.0 - 2 * br, 0.0), foot_R=((-9.0, 2.0), 0.0, -18, 0.0), foot_L=((9.0, -4.0), 0.0, 14, 0.0))
    for kk, v in sum_P.items():
        P[kk] = lerpP(P[kk], v, k)
    planted = dict(grip=SG, dir=tuple((Vector(SUMMON_TIP) - Vector(SG)).normalized()), flat=(1.0, 0.0, 0.0), two=False)
    P["sword"] = lerpP(P["sword"], planted, k) if k < 1 else planted
    P["sword"]["two"] = k < 0.35
    P["sword"]["two_w"] = 1 - smooth(k / 0.35)
    return P


@action
def summon_start():
    N = 40

    def fn(r, f):
        k = smooth(f / 22)
        P = summon_pose(f, k)
        drive = bump(f, 20, 2.0)                                   # the blade is rammed into the floor
        P["body"] = (P["body"][0], P["body"][1], P["body"][2] - 2.0 * drive)
        if f >= 6:
            raise_ = smooth((f - 16) / 20)
            low = dict(hand=(10.0, -9.0, 40.0), point=(0.1, -0.5, -0.8), palm=(-0.6, -0.2, 0.0), elbow=(0.6, 0.6, -0.4))
            P["arm_L"] = lerpP(low, HAND_UP, raise_)
            P["curl_L"] = 0.8 - 0.75 * smooth((f - 22) / 16)        # the claw slowly opens
            P["spread_L"] = smooth((f - 24) / 14)
            P["thumb_L"] = 0.6 - 0.5 * smooth((f - 24) / 14)
            P["wobble_L"] = (0.08 * math.sin(f * 0.7), 0.06 * math.sin(f * 0.9 + 1), 0.1 * math.sin(f * 0.8 + 2))
        P["heart"] = heartbeat(f / 20.0, 80 + 40 * smooth(f / 40), 1.0 + 1.0 * smooth((f - 10) / 30))
        K.pose(r, merged(**P))
    return N, fn, "hold"


@action
def summon_loop():
    N = 60

    def fn(r, f):
        br = wave(f, N, (1, 2, 0.0), (0.3, 3, 0.0))
        P = summon_pose(f, 1.0, br)
        c, s = wave(f, N, (1, 1, math.pi / 2)), wave(f, N, (1, 1, 0.0))
        a = dict(HAND_UP); a["hand"] = (18.0 + 1.2 * c, -16.0 + 0.8 * s, 70.0 + 0.8 * br)
        a["palm"] = (0.15 * c, -1.0, 0.25 + 0.15 * s)
        P["arm_L"] = a
        P["curl_L"] = 0.05 + 0.08 * wave(f, N, (1, 3, 0.0)); P["spread_L"] = 1.0 + 0.1 * wave(f, N, (1, 2, 1.0)); P["thumb_L"] = 0.1
        P["wobble_L"] = (0.1 * wave(f, N, (1, 4, 0.0)), 0.08 * wave(f, N, (1, 5, 1.0)), 0.12 * wave(f, N, (1, 3, 2.0)))
        P["head"] = (10.0 + 3 * s, -8.0 - 2 * br, 3 * c)
        P["heart"] = heartbeat(f / 20.0, 120, 1.8)                 # 120 bpm over 3 s = 6 beats: seamless
        K.pose(r, merged(**P))
    return N, fn, "true"


@action
def summon_end():
    N = 30

    def fn(r, f):
        k = 1 - smooth((f - 14) / 14)
        P = summon_pose(f, k)
        close = smooth(f / 9)
        release = smooth((f - 10) / 3)
        recoil = bump(f, 15, 3.0)
        P["body"] = (P["body"][0], P["body"][1] + 2.5 * recoil, P["body"][2])
        P["chest"] = (P["chest"][0] - 6 * recoil, P["chest"][1], P["chest"][2])
        if f < 26:
            compress = dict(hand=(9.0, -10.0, 52.0), point=(0.0, -0.3, 1.0), palm=(-0.8, -0.5, 0.0), elbow=(0.8, 0.6, -0.5))
            fling = dict(hand=(22.0, -18.0, 50.0), point=(0.6, -0.6, 0.4), palm=(0.4, -0.9, 0.0), elbow=(0.6, 0.3, -0.7))
            a = lerpP(HAND_UP, compress, close)
            a = lerpP(a, fling, release)
            a = lerpP(a, dict(hand=(10.0, -9.0, 40.0), point=(0.1, -0.5, -0.8), palm=(-0.6, -0.2, 0.0), elbow=(0.6, 0.6, -0.4)), smooth((f - 18) / 8))
            P["arm_L"] = a
            P["curl_L"] = 0.05 + 1.0 * close - 1.0 * release + 0.6 * smooth((f - 18) / 8)
            P["spread_L"] = (1 - close) + release * (1 - smooth((f - 18) / 8))
        P["heart"] = heartbeat(f / 20.0, 120, 1.8 * (1 - 0.5 * smooth((f - 16) / 14)) + 1.2 * bump(f, 12, 2))
        K.pose(r, merged(**P))
    return N, fn, "false"


# ====================================================================== AWAKEN (100 ticks: dormant -> alive -> flare -> guard)
KNEEL = dict(body=(0.0, 1.0, -15.0), hips=(14.0, 0.0, -4.0), spine=(10.0, 0.0, 0.0), chest=(14.0, 0.0, 0.0), head=(0.0, 42.0, 0.0),
             foot_R=((-7.0, 13.0), 0.0, -8, 62.0), foot_L=((7.5, -9.0), 0.0, 6, 0.0), knee_R=(-0.2, -1.0, -0.3), knee_L=(0.2, -1.0, 0.2))
KNEEL_TIP = (-2.0, -22.0, -1.5)
KNEEL_G = (-2.0, -15.0, 42.0)


@action
def awaken():
    N = 100

    def fn(r, f):
        guard = combat_base(0)
        stir = smooth((f - 20) / 20)                 # fingers tighten, shoulders move, head begins to rise
        rise = smooth((f - 40) / 25)                 # stands up, draws the sword out of the stone
        ready = smooth((f - 64) / 14)                # swings into the guard
        flare = bump(f, 80, 3.5)                     # the heart flares, chest thrown open
        P = lerpP(dict(guard, **KNEEL), guard, rise)
        P["head"] = lerpP((0.0, 42.0 - 18 * stir, 0.0), guard["head"], rise)
        P["head"] = (P["head"][0], P["head"][1] - 14 * flare, P["head"][2])
        P["chest"] = (P["chest"][0] - 10 * flare, P["chest"][1], P["chest"][2])
        P["shrug_R"] = 2.5 * stir * (1 - rise) + 3 * flare; P["shrug_L"] = 2.0 * stir * (1 - rise) + 3 * flare
        kneel_sword = dict(grip=KNEEL_G, dir=tuple((Vector(KNEEL_TIP) - Vector(KNEEL_G)).normalized()), flat=(1.0, 0.0, 0.0), two=True,
                           elbow_R=(-0.6, -0.2, -0.8), elbow_L=(0.6, -0.2, -0.8))
        held = dict(grip=(-12.0, -6.0, 52.0), dir=sword_dir(-40, -10), flat=(1.0, 0.0, 0.3), two=False)
        s = lerpP(kneel_sword, held, smooth((f - 52) / 12))
        s = lerpP(s, guard["sword"], ready)
        s["two"] = f < 56 or f > 70
        s["two_w"] = 1.0 if f < 52 else (1 - smooth((f - 52) / 4) if f < 64 else smooth((f - 70) / 8))
        P["sword"] = s
        P["curl_R"] = 0.7 + 0.3 * stir; P["curl_L"] = 0.7 + 0.3 * stir
        P["foot_R"] = lerpP(KNEEL["foot_R"], guard["foot_R"], rise)
        P["foot_L"] = lerpP(KNEEL["foot_L"], guard["foot_L"], rise)
        P["knee_R"] = lerpP(KNEEL["knee_R"], (-0.25, -1.0, 0.0), rise); P["knee_L"] = lerpP(KNEEL["knee_L"], (0.25, -1.0, 0.0), rise)
        bpm = 18 + 30 * stir + 60 * rise + 40 * flare
        amp = 0.15 + 0.6 * stir + 0.6 * rise + 2.2 * flare
        hs, gs = heartbeat(f / 20.0, bpm, amp)
        P["heart"] = (hs + 0.25 * flare, min(gs + 0.7 * flare, 1.9))
        K.pose(r, merged(**P))
    return N, fn, "false"


# ====================================================================== DEATH (100 ticks, held: recoil, stagger, drop the sword, knees, collapse, the heart dies)
COLLAPSE = dict(body=(1.0, 0.0, -19.0), hips=(34.0, -4.0, 6.0), spine=(18.0, -3.0, 4.0), chest=(20.0, -4.0, 6.0), head=(8.0, 50.0, -14.0),
                foot_R=((-7.0, 12.0), 0.0, -10, 64.0), foot_L=((7.0, 10.0), 0.0, 10, 64.0), knee_R=(-0.2, -1.0, -0.4), knee_L=(0.2, -1.0, -0.4))


@action
def death():
    N = 100

    def fn(r, f):
        P = dict(merged(**combat_base(0)))
        hit = bump(f, 4, 3.0)
        stag = smooth((f - 6) / 12)
        buckle = smooth((f - 20) / 12)
        fall = smooth((f - 56) / 14)
        P.update(body=(0.0, 1.0 + 4.0 * stag, -4.0 + 1.0 * hit), hips=(9.0 - 14 * hit - 4 * stag, 3 * stag, -14.0 + 10 * stag),
                 chest=(3.0 - 12 * hit, 4 * stag, 6.0 - 8 * hit), head=(16.0, 4.0 - 22 * hit + 10 * stag, 8 * stag))
        P["foot_R"] = ((-8.0, 5.0 + 6.0 * smooth((f - 8) / 6)), 3.0 * bump(f, 11, 1.8), -28, 0.0)
        knees = dict(body=(0.5, 0.0, -15.0), hips=(12.0, -3.0, 2.0), spine=(6.0, -2.0, 2.0), chest=(4.0, -2.0, 4.0), head=(4.0, 24.0, -6.0),
                     foot_R=((-7.0, 12.0), 0.0, -10, 62.0), foot_L=((7.0, 9.0), 0.0, 10, 62.0), knee_R=(-0.2, -1.0, -0.4), knee_L=(0.2, -1.0, -0.4))
        for k, v in knees.items():
            P[k] = lerpP(P[k], v, buckle)
        for k, v in COLLAPSE.items():
            P[k] = lerpP(P[k], v, fall)
        # the sword: held through the recoil, slips from the fingers at 18, falls and lands flat at 30
        held = dict(grip=(-11.0, -8.0, 44.0), dir=sword_dir(-30, -20), flat=(1.0, 0.0, 0.3), two=False)
        P["sword"] = lerpP(P["sword"], held, smooth((f - 2) / 8)) if f < 18 else held
        P["sword"]["two"] = f < 8; P["sword"]["two_w"] = 1 - smooth((f - 3) / 5)
        if f >= 18:
            t = (f - 18) / 12.0
            drop_g = lerpP((-11.0, -8.0, 44.0), (-14.0, -16.0, 1.3), ease_in(t))
            drop_d = lerpP(tuple(sword_dir(-30, -20)), tuple(sword_dir(-55, 0)), smooth(t))
            drop_n = lerpP((1.0, 0.0, 0.3), (0.0, 0.0, 1.0), smooth(t))
            bounce = 1.6 * bump(f, 31.5, 1.2)
            P["sword_world"] = ((drop_g[0], drop_g[1], drop_g[2] + bounce), drop_d, drop_n, 1.0)
            P["curl_R"] = 0.2
        if f >= 8:
            hang_L = dict(hand=(13.0, -6.0, 26.0 - 6 * buckle), point=(0.0, -0.3, -1.0), palm=(-1.0, 0.0, 0.0), elbow=(0.5, 0.5, -0.3))
            P["arm_L"] = lerpP(dict(hand=(18.0, 2.0, 46.0), point=(0.5, 0.3, -0.7), palm=(0.0, 1.0, 0.0), elbow=(0.6, 0.6, -0.2)), hang_L, smooth((f - 8) / 14))
            P["curl_L"] = 0.4
        if f >= 18:
            P["arm_R"] = dict(hand=(-13.0, -6.0, 26.0 - 6 * buckle), point=(0.0, -0.3, -1.0), palm=(1.0, 0.0, 0.0), elbow=(-0.5, 0.5, -0.3))
        if f >= 56:
            for S, sx in (("R", -1), ("L", 1)):
                fallen = dict(hand=(sx * 11.0, -22.0, 4.0), point=(0.0, -0.6, -0.8), palm=(0.0, 0.0, -1.0), elbow=(sx * 0.8, 0.2, -0.4))
                cur = P["arm_R"] if S == "R" else P["arm_L"]
                P["arm_" + S] = lerpP(cur, fallen, fall)
        # heart: racing, violent, a massive final flare at 76, then extinguished
        violent = smooth((f - 34) / 6) * (1 - smooth((f - 74) / 2))
        bpm = 90 + 80 * violent
        hs, gs = heartbeat(f / 20.0, bpm, 1.0 + 1.6 * violent + 0.4 * math.sin(f * 1.7) * violent)
        flare = bump(f, 77, 2.2)
        dead = smooth((f - 79) / 8)
        P["heart"] = ((hs + 0.4 * flare) * (1 - 0.35 * dead), min(gs + 0.9 * flare, 2.0) * (1 - dead) + 0.001)
        K.pose(r, merged(**P))
    return N, fn, "hold"


# ====================================================================== DORMANT (2 s loop): the first frame of awaken, held, a faint slow heartbeat
@action
def dormant():
    N = 40
    _, afn, _ = awaken()

    def fn(r, f):
        afn(r, 0)
        hs, gs = heartbeat(f / 20.0, 30, 0.25)                      # 30 bpm over 2 s = one beat: seamless
        r.scale("heart", hs); r.scale("heart_glow", (0.35 * gs) / max(hs, 1e-3))
    return N, fn, "true"
