"""Re-encode a video smaller using Blender's video sequencer (no ffmpeg install needed)."""
import bpy, sys, os
src, dst = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
se = sc.sequence_editor_create()
strips = se.strips if hasattr(se, "strips") else se.sequences
mv = strips.new_movie("v", src, 1, 1)
strips.new_sound("a", src, 2, 1)
sc.frame_start, sc.frame_end = 1, mv.frame_final_end - 1
sc.render.fps = 30
sc.render.resolution_x, sc.render.resolution_y = 854, 480
ims = sc.render.image_settings
if hasattr(ims, "media_type"):
    ims.media_type = "VIDEO"
ims.file_format = "FFMPEG"
ff = sc.render.ffmpeg
ff.format = "MPEG4"; ff.codec = "H264"; ff.constant_rate_factor = "LOW"
ff.audio_codec = "AAC"; ff.audio_bitrate = 128; ff.audio_channels = "STEREO"
sc.render.filepath = dst
bpy.ops.render.render(animation=True)
print("COMPRESS_OK", round(os.path.getsize(dst) / 1e6, 1), "MB")
