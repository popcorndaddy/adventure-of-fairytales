# The Withered King

A two-phase boss for Adventures of Fairytale (Forge 1.20.1). He's a cursed king who drags a huge greatsword
behind him. At half health he kneels and calls up his dead army. When the last of them falls he rises with a howl.
He dies kneeling beside his planted sword with his crown resting on its hilt.

- Entity: `kubejs:withered_king` (spawn egg in the Spawn Eggs tab, or `/summon kubejs:withered_king`)
- Needs: **KubeJS**, **EntityJS 0.7.5+**, **GeckoLib 4** (all three are in the pack's manifest)
- Everything was built from the existing character model (no new geometry). The skeleton was re-rigged in
  Blender and all ten animations were authored and baked there.

## Files

```
overrides/kubejs/
  startup_scripts/bosses/withered_king.js        the entity + the whole fight (server-side state machine)
  startup_scripts/bosses/withered_king_data.js   generated: event times, blade/palm/foot paths, dash motion (from the bake)
  server_scripts/bosses/withered_king_goals.js   targeting + look-around goals (EntityJS needs these in server scripts)
  config/withered_king.json                      every number you might want to tune (read at startup)
  data/kubejs/loot_tables/entities/withered_king.json   his drops
  assets/kubejs/geo/entity/withered_king.geo.json
  assets/kubejs/animations/entity/withered_king.animation.json     the 10 animations (+ "remains" pose)
  assets/kubejs/textures/entity/withered_king{,_awakened}{,_glowmask}.png
dev/withered_king/
  README.md  TIMING.md                            this guide; per-animation stages, events and server ticks
  withered_king.bbmodel                           Blockbench file with the model and every animation
  blender/                                        rig + animation project and the scripts that build it
  pipeline/                                       post-processing (cloth, secondary motion), export, validation
  test/harness.js                                 runs the fight logic in Node with a fake world
  qc/                                             contact sheets (3 angles) of every animation
```

## Animations

| Name | Length | Used for |
|---|---|---|
| `withered_king_idle` | 6.0 s loop | standing, fist on the planted sword's hilt, laboured breathing |
| `withered_king_walk_drag` | 2.4 s loop | walking at speed 0.20, the point dragging behind him and catching on the ground once a cycle |
| `withered_king_sweep` | 2.85 s | phase 1+2 melee: ~6-block ground-skimming frontal arc |
| `withered_king_dash` | 2.5 s | phase 1+2 gap closer: two-handed low charge, 7.8 blocks |
| `withered_king_phase_transition` | 4.5 s | 50% health: falters, plants the sword, sinks to one knee |
| `withered_king_kneeling` | 3.0 s loop | protected while his summoned army lives |
| `withered_king_phase_two_roar` | 5.2 s | rises, pulls the sword out, howls |
| `withered_king_hand_shockwave` | 2.2 s | phase 2: palm blast that throws players ~6.5 blocks |
| `withered_king_ground_stomp` | 2.7 s | phase 2: 12-block shockwave ring |
| `withered_king_death` | 10.5 s (holds) | The King's Last Rest: crown lifted off and set on the sword |

Stage boundaries, animation events and the exact server tick of every effect are in `TIMING.md`.

## How the fight works

States (shown by `global.wkState(entity)` and in the log with `boss.debug: true`):
`IDLE / WALKING -> SWEEP_WINDUP/ATTACK/RECOVERY, DASH_WINDUP/ATTACK/RECOVERY -> PHASE_TRANSITION ->
KNEELING_INVULNERABLE -> PHASE_TWO_RISE -> PHASE_TWO_ROAR -> PHASE_TWO_COMBAT (+ SHOCKWAVE_*, STOMP_*) -> DYING -> DEAD`.

- **Server-authoritative.** All decisions, hits, movement and timing happen in the server tick. The server triggers each
  action's animation once, and every client plays it from the same packet. The kneeling and dying loops are also
  carried by the entity's synced pose, so a player who arrives late still sees him kneeling or dying.
- **Hit timing.** Each server effect fires at `round(t x 20) + 4` ticks after the trigger. The extra 4 ticks are
  the animation blend, so damage lands on the frame where the blade or foot actually hits.
- **Sweep.** The blade's real grip-to-tip path from the bake is swept through the world each tick from 0.85 s to 1.3 s.
  Only the frontal arc can hit, and each target is hit at most once.
- **Dash.** He faces the target until 0.75 s, then the direction locks. During the dash the entity moves by the exact
  per-tick distance the running feet were animated for (7.8 blocks). He stops at walls and ledges. Anyone in his
  path is hit and thrown ahead of him.
- **50% gate.** Damage that would take him past half health stops at the gate. The transition runs once. From the
  transition until the howl ends he takes no damage and no knockback, and hits on him make a dull clang. He doesn't
  turn or move.
- **Minions.** They spawn in a ring on safe ground (not inside blocks or players) and are tracked by UUID, so other
  mobs nearby don't count. Strays and stuck ones are teleported back. After `phase.timeoutSeconds` any left crumble
  away so the fight can't soft-lock.
- **Shockwave.** A cone from his palm. Players are thrown by real velocity: about 6.5 blocks on level ground, less
  into walls or slopes.
- **Stomp.** The ring starts at his stomping foot and rolls out 0.6 blocks per tick to 12 blocks. You're hit once,
  when it reaches you, unless you're 1.1+ blocks in the air. The rising ground is made of temporary block-display
  fragments that follow the terrain surface. No world blocks are changed.
- **Death.** A lethal blow leaves him at 1 HP in a protected dying state. The 10.5 s sequence plays, then he dies for
  real: the loot table drops, XP is credited to the player who landed the blow, and the body dissolves.
  `death.monument: true` leaves a permanent statue of his last pose instead (only a creative player can break it).

## Testing guide

1. Start a world in a **creative superflat** test world. Run `/gamerule doMobSpawning false` and `/time set night`.
2. Run `/summon kubejs:withered_king ~ ~ ~5`. Switch to survival (`/gamemode survival`). Turn on
   `boss.debug: true` in `kubejs/config/withered_king.json` beforehand to log every state change to `logs/latest.log`.
3. **Walk / idle.** Back away. His feet should stay planted (no ice-skating) and the point should leave a trail of
   block particles behind him. Stand still at 4 blocks and he idles.
4. **Sweep.** Stand 3-5 blocks in front of him. You get about 0.8 s of warning (he turns away and scrapes the blade
   back). The hit should land when the blade reaches you, not before. Standing behind him or more than ~6.5 blocks
   away, you take nothing.
5. **Dash.** Stand 8-14 blocks away. He crouches with the sword pointed at you, pauses, then charges in a straight
   line. Sidestep after he locks on and he misses you and skids to a stop.
6. **Phase transition.** Bring him to half health: `/data merge entity @e[type=kubejs:withered_king,limit=1] {Health:460f}`,
   then hit him once. He falters, plants the sword and kneels. Hit him: no damage, just a clang. Six minions appear
   around him. Kill them; he rises and howls (darkness for 5 s) and his armour glows.
7. **Phase two.** Only now should the palm shockwave (it throws you about 6 blocks) and the stomp appear. For the
   stomp, stand at different distances: the farther you are, the later you're hit. Jump as the ring reaches you and
   you aren't hit at all. Fragments rise and settle back, and the ground is unchanged afterwards.
8. **Death.** Finish him (`/data merge ... {Health:5f}` then hit). The sequence must play to the end without being
   interrupted: knee, sword planted, crown lifted with his left hand and set on the sword's guard, last breath.
   Loot and XP appear only at the very end.
9. **Multiplayer.** Repeat steps 4-8 with two players. Both should see the same animation at the same moment.
   A player who joins (or arrives) while he kneels should see him kneeling.

Things to watch for (the QA list from the brief): foot sliding, the sword going through his body, hands leaving the
hilt, the crown off its spot, snapping between animations, hits that land before or after the visible impact, and
damage during the protected states.

## Tuning

Edit `kubejs/config/withered_king.json` and restart (startup scripts only load at launch). Every damage number, range,
cooldown, the stomp radius and ring speed, the minion list, the timeout, XP and the monument option are in there.
Delete the file to get the defaults back.

## Rebuilding the animations (Blender 4.x)

```
cd dev/withered_king/blender
blender -b --python make_data.py          # once: rig data from the model (needs pipeline/rig2.py + model3.py)
blender -b --python build_rig.py          # -> withered_king_rig.blend
blender -b withered_king_rig.blend --python anims.py      # all 10 actions -> withered_king_anim.blend
blender -b withered_king_anim.blend --python bake.py      # -> king_baked.json (GeckoLib values, 40 samples/s, events, probes)
blender -b withered_king_anim.blend --python render_qc.py -- all 8 20,100,200 300   # contact sheets
blender -b withered_king_anim.blend --python qc_clip.py   # sword/crown/body intersections, ground, foot slide
python pipeline/post.py king_baked.json king_final.json  # skirt + cape cloth, tabards/drapes/hood/banner springs, key reduction
WK_FINAL=king_final.json python pipeline/build_king.py   # geo + animation json + bbmodel + textures
python pipeline/validate.py out                           # format checks
python pipeline/make_js_data.py king_baked.json withered_king_data.js
node test/harness.js
```

The rig: root, pelvis (`body`), `waist`, `chest`, `neck`, `head`, `jaw`, clavicles, arms with IK + FK
(`IK_hand.*`, elbow poles, forearm roll helpers), four left fingers + thumb, right fist + thumb, leg IK with knee
poles, a `SWORD` control (the sword can be held, passed between hands or planted), a `CROWN` control (on the head, in
the hand, or set on the sword: one crown, switched by constraint influence), and secondary bones for the capes,
skirt, tabards, mantle drapes, hood drape and banner.

## Known limits

- **Camera shake** isn't possible from a script in vanilla 1.20.1. The howl uses darkness, sound and particles
  instead.
- **Late joiners and one-shot actions.** A player who starts tracking him partway through a one-shot action (an
  attack or the roar) sees the loop until the next action. The kneeling and dying states are always correct.
- **Wall during a dash.** If he hits a wall mid-dash, the entity stops but the running animation finishes in place.
- **Small contacts left by the QC.** These come from the model's own proportions. The pommel can brush the right
  pauldron by up to 3 px (3/8 of a block) for a few frames in the shockwave, stomp and death. A crown spike touches the
  head by about 1.7 px for a moment while he sets the crown down.
- Nothing here has been run inside Minecraft yet. The checks so far are the Blender QC scripts, the export format
  validator, an independent re-render of the exported animation data, and the Node harness for the fight logic.
