# The Gatekeeper — Unity setup

## What's in this folder
| File | What it is |
|---|---|
| `Gatekeeper.fbx` | the boss: skinned mesh, full rig (4 independent arms with fingers, legs, robe, chains, weapon) and all 13 clips |
| `Gatekeeper_PortalArena.fbx` | the arena: floor, portal gate, portal surface, rune pillars, chains, rubble, fissures and glyphs |
| `Textures/` | `GK_*_Albedo.png` and `GK_*_Emission.png` for every material (point-filtered pixel art) |
| `Audio/` | portal hum and flicker, stone drag, heavy step, impact boom, whoosh, eyes open, ambient drone, pulse, shriek |
| `Editor/GatekeeperImporter.cs` | sets up the FBX automatically: scale, rig, clip loop and root-motion flags, Animation Events, pixel textures, plus a **Tools ▸ Gatekeeper ▸ Build Materials** menu |
| `GatekeeperFX.cs` | runtime component: eyes and core ignite on `eyes_open`, slow rune pulse, and event-driven VFX and sound |
| `gatekeeper_manifest.json` / `gatekeeper_events.txt` | clip table, event frames, materials and sockets |

## Import
1. Copy the folder into `Assets/Gatekeeper/`. Keep `Editor/` as it is: the importer must sit in a folder named Editor.
2. Run **Tools ▸ Gatekeeper ▸ Build Materials**. This creates URP Lit (or Standard) materials with HDR emission and assigns them.
3. Add a **Bloom** post-processing volume (threshold about 1, intensity 0.6–1) so the eyes, core and runes glow.
4. Add `GatekeeperFX` to the boss. Drag in `GK_EyeGlow`, the rune materials and an AudioSource, then fill the effects list with your particle prefabs and sounds (for example `impact` → shockwave prefab and `impact_boom`).

## Clips (30 fps)
| Clip | Frames | Loop | Root motion | Events |
|---|---|---|---|---|
| Gatekeeper_Idle | 0–160 | ✔ | – | sword_scrape 104 / 122 |
| Gatekeeper_Awakening | 0–180 | – | – | arm_unfold 44 / 62, head_turn 100, sword_drag_sparks 110–150, eyes_open 160 |
| Gatekeeper_Entrance | 0–100 | – | ✔ (2 m forward) | heavy_step 40 / 74, roar 64 |
| Gatekeeper_Walking | 0–56 | ✔ | ✔ | footstep 0 / 28 |
| Gatekeeper_Heavy_Walk | 0–72 | ✔ | ✔ | heavy_footstep 0 / 36 |
| Gatekeeper_Sword_Drag | 0–80 | ✔ | ✔ | footstep, sword_drag_sparks |
| Gatekeeper_Overhead_Attack | 0–72 | – | – | windup 10, impact / ground_crack / camera_shake 34 |
| Gatekeeper_Horizontal_Sweep | 0–66 | – | – | windup 10, swing 20, shockwave / impact 24 |
| Gatekeeper_Multi_Arm_Attack | 0–110 | – | – | claw_R 12, claw_L 24, punch 30, sword_sweep 58, claws_both 62 |
| Gatekeeper_Block | 0–44 | – | – | block_impact 16; hold the last frame while blocking |
| Gatekeeper_Stagger | 0–48 | – | – | hit 2, stumble_step 14 |
| Gatekeeper_Rage | 0–100 | – | – | roar 28, camera_shake 30 / 60 |
| Gatekeeper_Death | 0–130 | – | – | hit 2, knees_hit_ground 30, body_hits_ground 98, eyes_fade 98 |

**Boss intro in game:** play Gatekeeper_Awakening, then Gatekeeper_Entrance (root motion carries him forward into the gate), then Idle or Heavy_Walk. Start the fight after Entrance. `Gatekeeper_Intro_Cinematic.mp4` shows the intended camera, lighting and sound timing.

## Attachment points (bones)
- `weapon`: the greatsword (child of `socket_hand_R`)
- `socket_hand_R`, `socket_hand_L`: the main hands
- `socket_extra_R`, `socket_extra_L`: the additional clawed hands
- `fx_fire_R`, `fx_fire_L`: the energy orbs and flames, scale-animated. Parent fire particles here.
- `chest`: the core; `head`: the eyes and roar; `root`: shockwaves
- `chain_*`: chain swing bones; `robe_F/B/L/R`: robe bones

Scale: 1 Minecraft block = 1 m. The boss is about 8.4 m tall.
