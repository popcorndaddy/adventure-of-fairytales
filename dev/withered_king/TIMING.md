# The Withered King - timing and events

Times are animation seconds. The server triggers an animation and the client blends into it over 4 ticks, so every
server effect is scheduled at `round(t x 20) + 4` ticks after the trigger. Event names come straight from the Blender actions
(they are stored on each action and exported with the bake).

## `withered_king_idle` (6.0 s, loop)

| Stage | From | To |
|---|---|---|
| loop | 0.00 | 6.00 |

## `withered_king_walk_drag` (2.4 s, loop)

| Stage | From | To |
|---|---|---|
| loop (one stride each foot) | 0.00 | 2.40 |

Animation events: `footstep`(R) 0.00, `footstep`(L) 1.20, `drag_contact_loop` 0.00, `drag_catch` 0.72, `drag_release` 1.06

## `withered_king_sweep` (2.85 s, play once)

| Stage | From | To |
|---|---|---|
| anticipation | 0.00 | 0.80 |
| swing | 0.80 | 1.25 |
| follow-through | 1.25 | 1.90 |
| recovery | 1.90 | 2.85 |

Animation events: `windup_begin` 0.00, `warning` 0.15, `scrape` 0.30, `swing_begin` 0.80, `sound` 0.90, `follow_through_begin` 1.25, `recovery_begin` 1.90, `recovery_end` 2.85

| Server tick | Anim s | What happens |
|---|---|---|
| 4 | 0.00 | faces the target until 0.6 s, then the swing direction is locked |
| 10 | 0.30 | scrape particles + grind sound at the blade point (0.3-0.8 s) |
| 21 | 0.85 | damage window opens: the baked blade (grip to tip) is swept through the world every tick; each target hit once |
| 22 | 0.90 | sweep whoosh |
| 30 | 1.30 | damage window closes |

## `withered_king_dash` (2.5 s, play once)

| Stage | From | To |
|---|---|---|
| preparation | 0.00 | 0.90 |
| dash | 0.90 | 1.50 |
| brake / recovery | 1.50 | 2.50 |

Animation events: `windup_begin` 0.00, `warning` 0.10, `dash_launch` 0.90, `dash_stop` 1.50, `footstep`(R) 0.38, `footstep`(L) 1.08, `footstep`(R) 1.24, `footstep`(L) 1.44, `recovery_begin` 1.45, `recovery_end` 2.50

| Server tick | Anim s | What happens |
|---|---|---|
| 4 | 0.00 | faces the target |
| 19 | 0.75 | direction locked (no homing after this) |
| 22 | 0.90 | entity starts moving: per-tick distance table from the animation (7.8 blocks total) |
| 22 | 0.90 | players in his path: damage + thrown ahead of him; stops at walls and ledges |
| 34 | 1.50 | movement ends, brake dust |

## `withered_king_phase_transition` (4.5 s, play once)

| Stage | From | To |
|---|---|---|
| faltering | 0.00 | 1.25 |
| planting the sword | 1.25 | 2.55 |
| kneeling | 2.55 | 4.50 |

Animation events: `falter` 0.00, `plant_begin` 1.25, `sword_impact` 2.35, `kneel_begin` 2.55, `kneeling_reached` 4.50

| Server tick | Anim s | What happens |
|---|---|---|
| 4 | 0.00 | protected from here (no damage, no knockback, no turning) |
| 51 | 2.35 | sword impact sound + debris at the blade point |
| 94 | 4.50 | pose -> kneeling loop |

## `withered_king_kneeling` (3.0 s, loop)

| Stage | From | To |
|---|---|---|
| loop (summoning, protected) | 0.00 | 3.00 |

Animation events: `summon_aura_loop` 0.00

| Server tick | Anim s | What happens |
|---|---|---|
| 4 | 0.00 | aura (ring + motes); heartbeat rises |
| 28 | 1.20 | minions summoned in a safe ring and tracked by UUID |
| 34 | 1.50 | every 0.5 s: alive check, stray/stuck minions pulled back; timeout after 180 s |
| 4 | 0.00 | last minion dead -> roar |

## `withered_king_phase_two_roar` (5.2 s, play once)

| Stage | From | To |
|---|---|---|
| awakening | 0.00 | 1.00 |
| rising | 1.00 | 2.90 |
| roar / howl | 2.90 | 5.20 |

Animation events: `rumble` 0.10, `rise_begin` 1.00, `sword_pulled_free` 2.60, `howl_begin` 2.90, `howl_burst` 3.05, `damageable` 5.20

| Server tick | Anim s | What happens |
|---|---|---|
| 6 | 0.10 | rumble |
| 56 | 2.60 | sword wrenched out: debris |
| 65 | 3.05 | howl: roar + thunder + metallic ring, dark burst, dust, darkness on players within 32, gentle shove |
| 108 | 5.20 | damageable again; phase two |

## `withered_king_hand_shockwave` (2.2 s, play once)

| Stage | From | To |
|---|---|---|
| anticipation | 0.00 | 0.65 |
| release | 0.65 | 0.95 |
| recovery | 0.95 | 2.20 |

Animation events: `windup_begin` 0.00, `palm_charge` 0.20, `release_begin` 0.65, `shockwave` 0.82, `recovery_begin` 0.95, `recovery_end` 2.20

| Server tick | Anim s | What happens |
|---|---|---|
| 4 | 0.00 | faces the target until 0.55 s |
| 8 | 0.20 | palm charge |
| 20 | 0.82 | cone (40 deg, 9 blocks) from the palm: damage + throw ~6.5 blocks by real velocity |

## `withered_king_ground_stomp` (2.7 s, play once)

| Stage | From | To |
|---|---|---|
| anticipation | 0.00 | 1.15 |
| stomp | 1.15 | 1.42 |
| recovery | 1.42 | 2.70 |

Animation events: `windup_begin` 0.00, `warning` 0.40, `stomp_begin` 1.15, `impact` 1.38, `recovery_begin` 1.42, `recovery_end` 2.70

| Server tick | Anim s | What happens |
|---|---|---|
| 4 | 0.00 | faces the target until 0.7 s |
| 32 | 1.38 | impact at the left foot; ring expands 0.6 blocks/tick to 12 blocks (1 s); fragments + debris follow the ring; players hit when it reaches them (once, not if 1.1+ blocks in the air) |

## `withered_king_death` (10.5 s, hold last frame)

| Stage | From | To |
|---|---|---|
| mortal injury | 0.00 | 1.30 |
| collapse to one knee | 1.30 | 3.10 |
| planting the sword | 3.10 | 4.40 |
| removing the crown | 4.40 | 6.30 |
| crown onto the sword | 6.30 | 8.40 |
| final breath and death | 8.40 | 10.00 |
| hold | 10.00 | 10.50 |

Animation events: `mortal_blow` 0.00, `knee_begin` 1.30, `knee_down` 2.60, `plant_begin` 3.10, `sword_impact` 4.05, `crown_reach` 4.40, `crown_grasp` 5.30, `crown_to_sword` 6.30, `crown_placed` 7.55, `crown_released` 7.75, `final_moments` 8.40, `last_breath` 9.10, `still` 10.00, `complete` 10.50

| Server tick | Anim s | What happens |
|---|---|---|
| 4 | 0.00 | protected, AI stopped, minions removed |
| 85 | 4.05 | sword impact |
| 110 | 5.30 | crown lifted |
| 155 | 7.55 | crown set on the guard: chain + resonance |
| 186 | 9.10 | last breath |
| 204 | 10.00 | bell + beacon fade, dust settles, combat music stopped |
| 214 | 10.50 | loot table + XP (credited to the killer), then the body dissolves (or becomes the monument if enabled) |

