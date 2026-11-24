"""Stage 2 - put the Gatekeeper into the reference stance and render it next to the arena for comparison."""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gk_lib as L
import gk_pose as GP
import gk_scene as SC

OUT = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "gatekeeper_stage1.blend"))
rig = bpy.data.objects["Gatekeeper_Rig"]
GP.apply_pose(rig, GP.stance())
print("SWORD_TIP_Z_PX", round(GP.sword_tip_z(rig), 2))
SC.setup(fog=True, arena=True)
SC.shot(os.path.join(OUT, "stage2_stance_front.png"), (0.8, -17.5, 1.6), (0, 0, 4.6), 30)
SC.shot(os.path.join(OUT, "stage2_stance_34.png"), (-10.5, -13.5, 3.0), (0, 0, 4.4), 32)
SC.shot(os.path.join(OUT, "stage2_stance_face.png"), (0.6, -8.5, 6.3), (0, 0, 6.3), 40)
SC.shot(os.path.join(OUT, "stage2_stance_back.png"), (9, 13, 5), (0, 0, 4.4), 32)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "gatekeeper_stage2.blend"))
print("STAGE2_OK")
