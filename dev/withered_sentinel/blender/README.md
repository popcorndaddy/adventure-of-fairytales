# Withered Sentinel - Blender animation rig

`withered_sentinel_anim.blend` holds all 12 actions (idle, idle_combat, walk, sweep, summon_start, summon_loop,
summon_end, push, awaken, stomp, dash, death) on `Sentinel_Rig`. Scene runs at 20 fps (1 frame = 1 game tick).

Rig: the deform bones keep the exact Blockbench/GeckoLib names. Controls drive them:
- `IK_foot.L/R` (feet, with `POLE_knee.L/R`), `IK_hand.L/R` (hands, with `POLE_elbow.L/R`)
- `TWIST.L/R` (forearm roll, added after the IK)
- torso, head, jaw, skirt, cape strips and sword are plain FK.

Pipeline (scripts here, run with `blender -b <file> --python <script>`):
1. `make_data.py` (outside Blender) exports the model to `sentinel_data.json`; `build_rig.py` builds the rig blend.
2. `anims.py` authors the actions (values are Blockbench pixels/degrees; `anim_lib.py` converts them, solves
   elbows, forearm twist and knee aim per frame).
3. `bake.py` bakes every action to Blockbench additive values -> `baked.json`.
4. `../pipeline/post.py` solves the skirt and cape strips against the body and floor, reduces keys;
   `unwrap.py` keeps Euler tracks continuous; the model builder writes the GeckoLib animation file.
5. `inject.py` puts the solved cloth back into the blend.
