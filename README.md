# Adventures of Fairytale

A Forge 1.20.1 adventure modpack (Forge 47.4.28, 336 CurseForge mods), now with **The Ancient Gatekeeper**: a custom boss who guards the End portal.

## Play it (CurseForge app)
1. Download **`Adventures-of-Fairytale-1.2.2.zip`** from this repo (don't unzip it).
2. In the CurseForge app, go to **Minecraft ▸ Create Custom Profile ▸ Import** (the small "import" link) and pick the zip.
3. CurseForge downloads the 336 mods automatically. The Gatekeeper mod is already bundled inside the zip.
4. Give it at least 10–12 GB of RAM (**Profile Options ▸ Java Settings**), then press **Play**.

Your friend does the same import. To play together, use World Host (included) or a LAN world.

> The zip is meant to be imported. It can't be published publicly on CurseForge as-is, because CurseForge only allows mods hosted on CurseForge inside public packs. Upload `gatekeeper-mod` to CurseForge as its own project first if you ever want to publish the pack.

## The Ancient Gatekeeper
- **Where:** the first time you come near an End portal (vanilla stronghold frames or End Remastered's ancient portal frames), he appears dormant in front of it.
- **The seal:** while he lives, no eye can be placed in that portal's frames ("The Gatekeeper's seal holds").
- **The awakening:** come within 20 blocks (or strike him). His extra arms unfold, his head turns, his blade scrapes the stone throwing sparks, his eyes ignite, and he steps forward and roars. The boss bar appears.
- **The fight:** 1200 HP, heavy armor, about 6 blocks tall. He uses an overhead smash (ground shockwave), a 230° horizontal sweep, and a four-arm combo (right claw, left claw, rune fist, sword finisher). He blocks some projectiles, staggers on big hits, and enrages at half health (roar and knockback ring, then faster and stronger, dragging his sword).
- **Gravity well:** when you keep out of his sword reach (7-14 blocks away) he drives his blade into the floor and opens a swirling purple well. For 3 seconds everything within 16 blocks is dragged toward him in a spiral, with crushing damage near the core. Then it bursts, flinging everyone near him outward for heavy damage. Run, or stagger him with a big hit to break it. Cooldown about 19 s (13 s when enraged).
- **Reward:** netherite, diamonds, echo shards, a Totem of Undying and 400 XP. The portal's seal breaks for good. The pack's boss scripts share boss loot with everyone who fought.
- **Testing:** creative mode has an *Ancient Gatekeeper Spawn Egg*.

## Repo layout
| Folder | What's inside |
|---|---|
| `Adventures-of-Fairytale-1.2.2.zip` | the importable pack (current: the Gatekeeper sleeps in every End portal room before you arrive, fights players only, never breaks blocks). `1.1.0` is an older release. |
| `gatekeeper-mod/` | the Forge + GeckoLib mod source. Build with `gradlew build`; run the automated in-game tests with `gradlew runGameTestServer` (7 tests). |
| `gatekeeper-art/` | Blender model, rig and 14 animations (`gatekeeper_stage3.blend`), the cinematic, combat reel and gravity-well preview (`Gatekeeper_Gravity_Well.mp4`), renders, and the Blender Python pipeline (`blender-scripts/`) that builds, animates, checks and converts him to GeckoLib |
| `gatekeeper-art/Unity_Gatekeeper/` | the same boss exported for Unity (FBX with clips, textures, audio, import scripts) |
| `tools/export-pack.ps1` | re-exports the CurseForge instance as a pack zip with the Gatekeeper bundled |
