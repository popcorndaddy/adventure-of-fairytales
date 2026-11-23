# Withered Sentinel: animate in Blender

`withered_sentinel.blend` is the Sentinel imported from the pack's GeckoLib files (`source/`): his exact model and texture on a 27-bone armature, with all 12 animations as Blender actions.

## Editing an animation
1. Open `withered_sentinel.blend` in Blender.
2. Select **withered_sentinel_rig** and switch to **Pose Mode**.
3. In the **Action Editor** (Dope Sheet ▸ Action Editor), pick an action: `idle`, `idle_combat`, `walk`, `sweep`, `summon_start`, `summon_loop`, `summon_end`, `push`, `awaken`, `stomp`, `dash` or `death`.
4. Move, add or delete keys on the bones (rotate with R, move with G). The timeline runs at **20 fps = Minecraft ticks**.
5. Keep the bones' rotation mode set to **XZY Euler** (as imported), and don't move or rename bones in Edit Mode. The export depends on both.
6. Save the .blend.

## Sending the changes back to the game
```powershell
& "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b dev\withered_sentinel\withered_sentinel.blend --python tools\blender-geckolib\geckolib_blender.py -- export overrides\kubejs\assets\kubejs\animations\entity\withered_sentinel.animation.json
```
This rewrites the animations in that file. Add a comma-separated list of action names at the end to export only those (for example `-- export <file> walk,sweep`). Every key is written with Catmull-Rom smoothing, same as the originals.

## Notes
- A no-edit round trip (import, then export) reproduces all 2,706 original keyframes exactly.
- Blender draws the curves between keys with Bezier "auto" handles, which is close to (but not exactly) GeckoLib's Catmull-Rom. The key values themselves are exact, so in game the motion between keys can differ very slightly from Blender's playback.
- To re-import after the model or animations change: `blender -b --python tools\blender-geckolib\geckolib_blender.py -- import <geo.json> <animation.json> <texture.png> <out.blend>`
- Preview stills: `tools\blender-geckolib\preview.py`

## The rebuilt animations (scripted, in `withered_sentinel_reworked.blend`)
All 12 combat animations in the pack are now posed by Python scripts rather than hand-keyed, so they can be tuned and rebaked:

| Script | Animations | What it guarantees |
|---|---|---|
| `ws_batch1.py` | walk, sweep | IK-planted feet (no sliding: planted feet move at exactly the walk speed), sword tip dragged on the floor while walking, sweep hit on tick 26 |
| `ws_batch2.py` | idle, idle_combat | seamless loops; idle sword point pinned to the stone; idle_combat frame 0 = the shared combat stance |
| `ws_batch3.py` | push, stomp | palm strike on tick 20, foot slam on tick 19; both start and end on the combat stance |
| `ws_batch4.py` | dash, awaken | roar on 8 and lance charge 9-16; phase-2 eruption on tick 25 |
| `ws_batch5.py` | summon_start, summon_loop, summon_end, death | kneel with the blade driven into the stone (tick 23), seamless loop, matching start/end frames; death held on its last frame |

Shared code: `ws_tools.py` (rig, two-bone IK, foot placement, baking) and `ws_common.py` (combat stance, foot planting, sword helpers, key-driven `combat_pose`, loop curves, checks). Each script prints its checks (foot drift, floor contact, loop seams, stance matching) and saves the .blend.

Rebake and export, e.g. batch 3:
```powershell
& "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b dev\withered_sentinel\withered_sentinel_reworked.blend --python dev\withered_sentinel\ws_batch3.py
& "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b dev\withered_sentinel\withered_sentinel_reworked.blend --python tools\blender-geckolib\geckolib_blender.py -- export overrides\kubejs\assets\kubejs\animations\entity\withered_sentinel.animation.json push,stomp
```
Review: `tools\blender-geckolib\sheets.py -- <out_dir> <actions...>` renders 8-frame contact sheets from three angles; `closeup.py -- <out.png> <action> <f1,f2,..> side|front|back` renders close-ups.
Tick timings must stay in step with `WS_LEN` in `overrides/kubejs/startup_scripts/bosses/withered_sentinel.js`.
