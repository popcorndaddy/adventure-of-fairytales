# The Withered Sentinel (knight): Blender project

A massive obsidian knight with a beating violet heart, built from your reference image. He's made entirely in Blender by script, then exported to GeckoLib for the pack (EntityJS + KubeJS).

| File | What it is |
|---|---|
| `sentinel_knight.blend` | the built model: the rig, every armour block, the sword, the heart, the FX anchors and the collision helpers |
| `sentinel_knight_anim.blend` | the same, plus all 13 baked actions. **Open this one to look at the animations.** |
| `sk_build.py` + `sk_armor.py` | build the scene from scratch (rig, armour, sword, heart, anchors, collision helpers) |
| `sk_pose.py` | posing toolkit: two-bone IK for arms and legs, planted feet, sword grip (one- and two-handed), finger curl, head look, heartbeat |
| `sk_anims.py` + `sk_actions_more.py` | the 12 actions plus `dormant`, baked per frame (20 fps = Minecraft ticks) |
| `sk_export.py` | GeckoLib export: geo, painted texture atlas, glowmask, animation JSON |
| `sk_check.py`, `sk_dump.py`, `sk_roundtrip.ps1` | quality checks: grip accuracy, foot/floor contact, and a source-vs-reimport comparison of every bone |
| `sk_sheets.ps1`, `sk_review.py`, `sk_reel.py` | 3-angle review sheets and the showcase video |
| `tools/` | the GeckoLib importer, the glow preview and close-up helpers |

## Scene layout (collections)
- `Sentinel_Armature` holds the rig `Sentinel_Rig`, 41 bones:
  - root, pelvis, spine, chest, neck, head;
  - clavicles, upper arms, forearms, hands, three 2-segment fingers and a 2-segment thumb on each hand;
  - thighs, shins, feet, toes;
  - `sword` (child of `hand_R`, the grip point), `heart` and `heart_glow`.
- `Sentinel_Armor`, `Sentinel_Body`, `Sentinel_Weapon` and `Sentinel_Heart` hold rigid blocks, each parented to its bone. They can't float or deform, and the game draws them exactly as Blender does.
- `Sentinel_Effects` holds `FX_*` anchors (heart, sword tip and middle, left palm, feet, eyes). These are where the game spawns particles.
- `Sentinel_Collision` holds helpers only, never exported:
  - `COL_*`: body (2.2 × 5.2 blocks at model scale), head, chest, arms, legs, feet and sword references;
  - `HIT_*`: the attack shapes (sweep arc 5.2 blocks / 230°, stomp radius 4.5, dash box, push cone).

  In game the boss uses model scale 1.4, so the real numbers in `withered_sentinel.js` are 1.4× these.
- `Sentinel_Export` holds a text block that describes the above.

## Look
- **Armour:** near-black obsidian plate with gunmetal trim, jagged teeth, a broken crown and engraved runes. Nothing on the armour glows.
- **Glow:** only the heart glows (plus a faint lit inner chest wall and two dim eyes).
- **Heart:** it sits behind an open ribcage on its own bone, with an additive glow shell that pulses with it. It beats slowly at rest, faster in combat, brighter before big attacks, flares at the awakening, and on death it races, erupts and goes out.
- **Magic:** all purple magic is temporary and spawned by the entity script on animation events (voxel dust, rune glyphs, obsidian shards).

## Rebuild / re-export
```powershell
$b = "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"
& $b -b --python dev\sentinel_knight\sk_build.py -- dev\sentinel_knight\sentinel_knight.blend
& $b -b dev\sentinel_knight\sentinel_knight.blend --python dev\sentinel_knight\sk_anims.py            # all actions; or -- walk,sweep
& $b -b dev\sentinel_knight\sentinel_knight_anim.blend --python dev\sentinel_knight\sk_export.py -- overrides\kubejs\assets\kubejs --anims
```
Then check the result with `dev\sentinel_knight\sk_roundtrip.ps1` (it must report roughly 0 px everywhere) and review it with `sk_sheets.ps1 -NoBake`.

The animation timings are ticks. If you change a hit frame, change the matching tick in `overrides/kubejs/startup_scripts/bosses/withered_sentinel.js` too:
- sweep hits on 24;
- push on 20;
- stomp on 19;
- dash lunges 9–16;
- summon on 30;
- awaken flares on 80.

## Textures (v4, high resolution)
- Atlas is 4096x2048 at 8 texels per model pixel (`TPX`/`SC` in sk_export.py); the geo stays in 512x256 texture units.
- Gatekeeper tiles (64x64) are sampled bilinearly, then fine detail is painted at full resolution:
  mottling, grain, dents, scratches, worn edges, round rivets, soft-edged rune glyphs and glowing tracery.
- Caution: sentinel_knight_anim.blend keeps the geometry from when it was first baked (the older cape).
  Export the geo from sentinel_knight.blend (`sk_cycle.ps1 -NoBuild`), and only the animations with `-Anims`,
  or re-bake after rebuilding.

## Animation QC (v5 polish pass)
- `sk_snap.py` - true per-tick rotation change of every bone (quaternion angle); flags snaps above a threshold.
- `sk_check.py` - grip contact, planted-foot slide (measured at the ball of the foot), floor, blade travel,
  elbow straightness and blade-through-body clipping, per action.
- Export writes rotation keys that are continuous tick to tick (`file_rot_cont`): GeckoLib blends Euler numbers
  between ticks, so equivalent-but-different triples (179 -> -179) would spin a bone for a frame.
- Hands blend between "on the sword" and "free" (`arm_L_w` / `arm_R_w` with the sword's `two_w`), and free-hand
  orientations blend as rotations, so no hand switches or flips in one tick.
- Head: `calm_head` keeps the look on the target (the entity faces it) with a few degrees of drift, a soft spring
  and a ~65 degree neck limit; `head_mode` "pitch" keeps authored nods for kneeling/collapse.
- `sk_sheets.ps1` exports animations only (the anim .blend's geometry is stale) and renders 3-view sheets.
