# Adventures of Fairytale

A Forge 1.20.1 adventure modpack (Forge 47.4.28, 336 CurseForge mods, 12 GB RAM recommended) with its own bosses:
**The Ancient Gatekeeper** (guards the End portal), **The Gate Knight**, and **The Withered Sentinel** (guards newly lit Nether portals).

## Play it
- **New install:** download `Adventures-of-Fairytale-1.2.2.zip`, then in the CurseForge app use **Minecraft > Create Custom Profile > Import** and pick the zip (don't unzip it). Give it 10-12 GB of RAM.
- **Keep an existing install up to date:** run **Update Pack.bat** in the instance folder, then restart Minecraft. It copies everything in `overrides/` (scripts, configs, and our own mod jars in `overrides/mods/`) and replaces older versions of our mods.

To play together, use World Host (included) or a LAN world.

> The zip is meant to be imported. It can't be published publicly on CurseForge as-is, because CurseForge only allows mods hosted on CurseForge inside public packs.

## The Ancient Gatekeeper
- **Where:** the first time you come near an End portal (vanilla stronghold frames or End Remastered's ancient portal frames), he appears dormant in front of it.
- **The seal:** while he lives, no eye can be placed in that portal's frames ("The Gatekeeper's seal holds").
- **The awakening:** come within 20 blocks (or strike him). His extra arms unfold, his head turns, his blade scrapes the stone throwing sparks, his eyes ignite, and he steps forward and roars. The boss bar appears.
- **The fight:** 1200 HP, heavy armor, about 6 blocks tall. He uses an overhead smash (ground shockwave), a 230° horizontal sweep, and a four-arm combo (right claw, left claw, rune fist, sword finisher). He blocks some projectiles, staggers on big hits, and enrages at half health (roar and knockback ring, then faster and stronger, dragging his sword).
- **Gravity well:** when you keep out of his sword reach (7-14 blocks away) he drives his blade into the floor and opens a swirling purple well. For 3 seconds everything within 16 blocks is dragged toward him in a spiral, with crushing damage near the core. Then it bursts, flinging everyone near him outward for heavy damage. Run, or stagger him with a big hit to break it. Cooldown about 19 s (13 s when enraged).
- **Reward:** netherite, diamonds, echo shards, a Totem of Undying and 400 XP. The portal's seal breaks for good. The pack's boss scripts share boss loot with everyone who fought.
- **Testing:** creative mode has an *Ancient Gatekeeper Spawn Egg*.

## The Gate Knight
- An ancient dark knight, about 8.4 blocks tall, 600 HP, a little faster than a walking player.
- **Attacks:** a low sweep (~5 blocks), a stomp that heaves the ground up around him (~6 damage within 6 blocks), a two-handed dash (~10 blocks), a palm shockwave that throws you 5-6 blocks back, and a raised-sword guard that stops arrows from the front.
- **At half health** he kneels, invincible, while 9 wither skeletons rise around him. When every one is dead he stands, roars and burns brighter (faster, harder hitting).
- Magic does 15% damage; harmful potion effects don't take hold. He dies kneeling on his sword and crumbles to dust.
- **Spawn:** *Gate Knight Spawn Egg* (Spawn Eggs tab) or `/summon aof_gateknight:gate_knight`.

## The Withered Sentinel
A KubeJS boss (`overrides/kubejs/*/bosses/`) who comes out of newly lit Nether portals. Development renders are in `dev/sentinel_knight/`.

## Repo layout
| Path | What's inside |
|---|---|
| `manifest.json`, `modlist.html` | the CurseForge mod list (project + file IDs) and the readable list |
| `overrides/` | everything copied on top of the mods: `config/`, `kubejs/` (story, boss route, the Withered Sentinel), `mods/` (our own mod jars), `patchouli_books/`, resource and shader packs |
| `Adventures-of-Fairytale-1.2.2.zip` | the importable pack. `1.1.0` is an older release. |
| `gatekeeper-mod/` | the Ancient Gatekeeper mod source (Forge + GeckoLib). `gradlew build`; tests with `gradlew runGameTestServer`. |
| `gatekeeper-art/` | the Gatekeeper's Blender model, rig, animations, videos, Unity export and pipeline |
| `gateknight-mod/` | the Gate Knight mod source and assets (Forge + GeckoLib), with GameTests |
| `dev/` | work files that aren't part of the pack |
| `tools/export-pack.ps1` | re-exports the CurseForge instance as a pack zip |

## Building an importable zip
Zip `manifest.json`, `modlist.html` and `overrides/` together at the top level of the zip with forward-slash paths (or run `tools/export-pack.ps1`). `dev/` and `README.md` stay out of the zip.
