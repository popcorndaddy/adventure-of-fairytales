"""Preview video of the exported animations (the same values GeckoLib plays, cloth included).
blender -b withered_king_anim.blend --python render_video.py -- king_final.json out.mp4 [yaw,yaw..]
Poses every deform bone straight from the final GeckoLib keyframes (linear, like GeckoLib), with all rig constraints
muted, moves the body by the in-game root motion for the walk and the dash, burns the clip name into each frame and
joins everything into one MP4 with the sequence editor."""
import bpy, sys, os, json, math, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Matrix, Vector
import bbmath as BM
from bbmath import G, GI, BONES, WREST, local_bb
a = sys.argv[sys.argv.index('--') + 1:]
F = json.load(open(os.path.join(BM.HERE, a[0]))); OUT = os.path.join(BM.HERE, a[1]); YAWS = [float(y) for y in (a[2] if len(a) > 2 else '35').split(',')]
FPS = 24; W, H = 1280, 720
sc = bpy.context.scene; rig = bpy.data.objects['Sentinel_Rig']; PB = rig.pose.bones; AB = rig.data.bones; cam = sc.camera
rig.animation_data.action = None
for pb in PB:
    for c in pb.constraints: c.mute = True
    pb.rotation_mode = 'QUATERNION'; pb.matrix_basis = Matrix.Identity(4)
order = [n for n in BM.ORDER if n in PB]
ORDER = ['withered_king_idle', 'withered_king_walk_drag', 'withered_king_sweep', 'withered_king_dash', 'withered_king_phase_transition',
         'withered_king_kneeling', 'withered_king_phase_two_roar', 'withered_king_hand_shockwave', 'withered_king_ground_stomp', 'withered_king_death']
if len(a) > 3: ORDER = [n for n in ORDER if n in a[3].split(',')]
REPEAT = {'withered_king_walk_drag': 2, 'withered_king_kneeling': 2}
def smooth(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def dash_speed(t, s=0.9, e=1.5, vm=128.0):
    if t < s or t > e: return 0.0
    u = (t - s) / (e - s)
    return vm * (smooth(u / 0.25) if u < 0.25 else (1.0 if u < 0.78 else 1 - smooth((u - 0.78) / 0.22) * 0.55))
def root_px(name, t):
    if name == 'withered_king_walk_drag': return 14.0 * t
    if name == 'withered_king_dash':
        n = 200; return sum(dash_speed((i + 0.5) / n * t) for i in range(n)) * t / n
    return 0.0
def sample(keys, t):
    if t <= keys[0][0]: return keys[0][1]
    if t >= keys[-1][0]: return keys[-1][1]
    lo, hi = 0, len(keys) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if keys[m][0] <= t: lo = m
        else: hi = m
    (t0, v0), (t1, v1) = keys[lo], keys[hi]; u = (t - t0) / (t1 - t0)
    return [x + (y - x) * u for x, y in zip(v0, v1)]
def pose(an, t):
    Wp = {}
    for n in BM.ORDER:
        if n == 'root': Wp[n] = Matrix.Identity(4); continue
        ch = an['bones'].get(n, {})
        r = sample(ch['rotation'], t) if 'rotation' in ch else (0, 0, 0)
        p = sample(ch['position'], t) if 'position' in ch else (0, 0, 0)
        par = BONES[n]['parent']
        Wp[n] = (Wp[par] if par else Matrix.Identity(4)) @ local_bb(n, r, p)
    K = {n: Wp[n] @ WREST[n].inverted() for n in Wp}
    for n in order:
        if n == 'root': continue
        Bn = AB[n].matrix_local; par = AB[n].parent
        Kp = K[par.name] if (par and par.name in K) else Matrix.Identity(4)
        PB[n].matrix_basis = Bn.inverted() @ G @ Kp.inverted() @ K[n] @ GI @ Bn
sc.render.resolution_x = W; sc.render.resolution_y = H; sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'
r = sc.render; r.use_stamp = True; r.use_stamp_note = True; r.stamp_font_size = 26
for k in ('use_stamp_date', 'use_stamp_time', 'use_stamp_render_time', 'use_stamp_frame', 'use_stamp_frame_range', 'use_stamp_memory', 'use_stamp_hostname',
          'use_stamp_camera', 'use_stamp_lens', 'use_stamp_scene', 'use_stamp_marker', 'use_stamp_filename', 'use_stamp_sequencer_strip', 'use_stamp_peak_memory'):
    if hasattr(r, k): setattr(r, k, False)
r.stamp_foreground = (0.85, 0.97, 0.95, 1.0); r.stamp_background = (0.0, 0.0, 0.0, 0.55)
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 16.5
tmp = os.path.join(os.path.dirname(OUT), '_video_frames'); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
frames = []; k = 0
for yaw in YAWS:
    for name in ORDER:
        an = F[name]; L = an['length']; reps = REPEAT.get(name, 1); n = int(round(L * reps * FPS))
        moving = name in ('withered_king_walk_drag', 'withered_king_dash')
        label = f"{name}   {L:g} s{'  (loop x%d)' % reps if reps > 1 else ''}   camera {int(yaw)} deg"
        r.stamp_note_text = label
        for i in range(n + 1 + (FPS // 2)):          # + a half-second hold on the last frame
            t = min(i / FPS, L * reps); tl = t % L if (reps > 1 and t < L * reps) else min(t, L)
            pose(an, tl)
            dy = -(root_px(name, L) * math.floor(t / L + 1e-9) + root_px(name, tl)) * 0.125 if moving else 0.0
            rig.location = (0, 3.5 + dy if moving else 0, 0)
            y = math.radians(yaw); d = Vector((-math.sin(y), -math.cos(y), 0.22)).normalized()
            target = Vector((0, rig.location.y - 0.6, 4.4)); cam.location = target + d * 40
            cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
            bpy.context.view_layer.update()
            p = os.path.join(tmp, f'{k:05d}.png'); sc.render.filepath = p; bpy.ops.render.render(write_still=True); frames.append(p); k += 1
        print('VIDEO', name, int(yaw), n, 'frames', flush=True)
# join the frames into one MP4 in a fresh scene with the sequence editor
vs = bpy.data.scenes.new('video'); vs.sequence_editor_create()
vs.render.resolution_x = W; vs.render.resolution_y = H; vs.render.resolution_percentage = 100
vs.render.fps = FPS; vs.frame_start = 1; vs.frame_end = len(frames)
se = vs.sequence_editor; coll = se.strips if hasattr(se, 'strips') else se.sequences
st = coll.new_image('frames', frames[0], 1, 1)
for p in frames[1:]: st.elements.append(os.path.basename(p))
st.frame_final_duration = len(frames)
ims = vs.render.image_settings
if hasattr(ims, 'media_type'): ims.media_type = 'VIDEO'
ims.file_format = 'FFMPEG'; vs.render.ffmpeg.format = 'MPEG4'; vs.render.ffmpeg.codec = 'H264'
vs.render.ffmpeg.constant_rate_factor = 'HIGH'; vs.render.ffmpeg.ffmpeg_preset = 'REALTIME'
vs.render.filepath = OUT; vs.render.use_stamp = False
bpy.ops.render.render(animation=True, scene=vs.name)
print('VIDEO done', OUT, len(frames), 'frames', round(len(frames) / FPS, 1), 's', flush=True)
