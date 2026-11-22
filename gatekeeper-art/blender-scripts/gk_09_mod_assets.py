"""Mod assets: dormant texture/glowmask (only rune glyphs glow) and OGG Vorbis sounds for Minecraft."""
import bpy, sys, os, shutil
import numpy as np

ART = sys.argv[sys.argv.index("--") + 1]
ASSETS = sys.argv[sys.argv.index("--") + 2]
tex = os.path.join(ASSETS, "textures/entity")

# dormant: same albedo, glowmask keeps only the RuneStone tile (tile index 1 -> x 64..128, y 0..64)
shutil.copy(os.path.join(tex, "gatekeeper.png"), os.path.join(tex, "gatekeeper_dormant.png"))
im = bpy.data.images.load(os.path.join(tex, "gatekeeper_glowmask.png"))
w, h = im.size
a = np.empty(w * h * 4, dtype=np.float32); im.pixels.foreach_get(a)
a = a.reshape(h, w, 4)[::-1].copy()
keep = np.zeros_like(a)
keep[0:64, 64:128] = a[0:64, 64:128]
out = bpy.data.images.new("dormant_glow", w, h, alpha=True)
out.pixels.foreach_set(keep[::-1].ravel())
out.filepath_raw = os.path.join(tex, "gatekeeper_dormant_glowmask.png"); out.file_format = "PNG"; out.save()
print("DORMANT_TEX_OK")

# sounds -> OGG Vorbis (mono, 44.1 kHz)
SND = {"ambient": "guardian_ambient", "pulse": "guardian_pulse", "shriek": "guardian_shriek", "step": "heavy_step",
       "impact": "impact_boom", "whoosh": "whoosh", "drag": "stone_drag", "eyes_open": "eyes_open", "portal_flicker": "portal_flicker"}
sdir = os.path.join(ASSETS, "sounds"); os.makedirs(sdir, exist_ok=True)
try:
    bpy.context.preferences.system.audio_channels = "MONO"
except Exception as e:
    print("PREF_CHANNELS", e)
for name, src in SND.items():
    sc = bpy.data.scenes.new("snd_" + name)
    sc.render.fps = 30
    se = sc.sequence_editor_create()
    strips = se.strips if hasattr(se, "strips") else se.sequences
    st = strips.new_sound(name, os.path.join(ART, "sounds", src + ".wav"), 1, 1)
    sc.frame_start, sc.frame_end = 1, st.frame_final_end
    sc.render.ffmpeg.audio_channels = "MONO"          # mixdown takes its channel count from here; Minecraft needs mono
    dst = os.path.join(sdir, name + ".ogg")
    tmp = os.path.join(sdir, "_split_" + name + ".ogg")
    with bpy.context.temp_override(scene=sc):
        bpy.ops.sound.mixdown(filepath=tmp, container="OGG", codec="VORBIS", format="S16", mixrate=44100, accuracy=1024, split_channels=True)
    parts = sorted(f for f in os.listdir(sdir) if f.startswith("_split_" + name))
    if os.path.exists(dst):
        os.remove(dst)
    os.replace(os.path.join(sdir, parts[0]), dst)       # one mono channel (the sources are mono)
    for f in parts[1:]:
        os.remove(os.path.join(sdir, f))
    print("OGG", name, parts, os.path.getsize(dst))
print("ASSETS_OK")
