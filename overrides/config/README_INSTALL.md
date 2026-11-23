# Adventures of Fairytale — FTB Quests Questbook

**Target:** Minecraft 1.20.1 • Forge 47.4.x • FTB Quests 2001.4.22 (as seen in the supplied crash log)

**Contents:** 16 chapters • 147 quests • 6 groups • 98 quests with at least one manual checkmark.

This is an original, lore-led quest progression assembled for the installed mods in the October 31 crash report (303 jar entries). It is NOT a game-tested pack. Its file syntax and progression references were checked, but game loading and mod registry item names must still be confirmed before publishing.

## Install safely

1. **Back up the entire instance and your world** (including `config/ftbquests/quests` and the existing FTB Quests progress).
2. Close Minecraft and CurseForge's running Minecraft instance.
3. If you already have an FTB Quests questbook you want to keep, **do not blindly overwrite it**. This ZIP is a complete standalone questbook: its `data.snbt` and `chapter_groups.snbt` would replace yours. Use a new **duplicate instance** for the first test.
4. From the ZIP, merge/copy the **`config`** directory into the ROOT of your duplicated Minecraft instance (the directory alongside `mods`, `saves`, and `config`). The files should end up at `config/ftbquests/quests/`.
5. Launch Minecraft, enter a test world, and open FTB Quests. You can use `/ftbquests reload` from an operator account after editing quest files; restart if it doesn't update.
6. Check the chapter groups, several quests per chapter, an item objective, a kill objective, a dimension objective, and a manual checkmark objective before bringing it to multiplayer.
7. For a server, place the same `config/ftbquests/quests/` files in the **server instance**; the server owns quest progress and normally syncs the questbook to clients.

**Important:** Do not copy these quest files into `mods/` and do not rename them to `.json`.

## Structure

```
config/ftbquests/quests/
  data.snbt
  chapter_groups.snbt
  chapters/
    prologue.snbt
    wilds.snbt
    ...16 total .snbt chapter files...
```

## Chapters

| # | Chapter | Quests |
|---|---|---:|
| 01 | Prologue: The First Dawn | 10 |
| 02 | The Wanderer's Atlas | 10 |
| 03 | Bounties of the Harvest | 9 |
| 04 | Hearths, Halls & Kingdoms | 9 |
| 05 | Fire of the Forge | 10 |
| 06 | Oaths of Steel | 9 |
| 07 | The Arcane Colleges | 10 |
| 08 | The Bestiary | 8 |
| 09 | Beneath the World | 9 |
| 10 | The Twilight Crown | 10 |
| 11 | The Dragonbound Path | 10 |
| 12 | Flame and Nether | 8 |
| 13 | The Age of Cataclysm | 10 |
| 14 | The End of the Road | 9 |
| 15 | Legends & Side Stories | 8 |
| 16 | Epilogue: A Fairytale Remembered | 8 |

## How completion works

- **Automatic item requirements:** the player obtains or submits an item (items are **not consumed**, per `default_consume_items: false`). For count requirements, FTB may require you to possess the requested total at one time.
- **Automatic kill requirements:** the player kills a named entity. Only dependable Minecraft and Twilight Forest entity IDs are used.
- **Automatic discovery requirements:** a known structure or vanilla dimension is detected.
- **Manual checkmark requirements:** intentionally used for activities with no reliable FTB Quests event (craft a custom modded armor piece, clear a modded dungeon, defeat a boss with an unverified registry ID, build a settlement). The player must actually perform the described task **and click** the checkmark.
- **Dependencies:** later quests point at prerequisite quest IDs, including across chapters. `flexible` progression supports play at your own pace.
- **Rewards:** modest, vanilla items and XP only; no command execution or creative-mode privileges, keeping multiplayer safer.

## Modded item ID verification needed

The modded item task IDs used below are strongly established but were not read from your exact installed `.jar` registries. Verify each in your live pack before sharing publicly:

- `The Cutting Board`: `farmersdelight:cutting_board`
- `A Proper Kitchen`: `farmersdelight:cooking_pot`

In the F3 debug screen, or with Minecraft commands/JEI, verify that these item IDs exist; if any are missing, edit the corresponding quest task in-game or change it to a manual checkmark. This questbook does **not** rely on the temporarily disabled Traveloptics mod or its unstable Cataclysm integration.

## FTB Quests 1.20.1 format

This is the **legacy 1.20.1 SNBT layout** with inline `title`/`description` fields, e.g. `item: "minecraft:diamond"`, modeled on live 1.20.1 packs such as ATM9. **It intentionally does not use the 1.21+ separate `lang/en_us.snbt` format.** `chapter_groups.snbt` uses `chapter_groups: [ ]`, not `groups: [ ]`.

## Planned scope, not a promise of zero bugs

The source was a crash report, so we know mod IDs but **not** every registered item, every recipe change, every config option, or your active questbook settings. I intentionally avoided unverified modded entity IDs and used clearly marked checkmarks rather than shipping impossible or broken kill tasks. Also note that your crash report listed Forge 47.4.0 while you previously mentioned Forge 47.4.28.

## Author tools

- `QUEST_INDEX.csv`: sortable list of all quests, objectives, dependencies, and IDs.
- `MODS_IN_SOURCE_CRASH_REPORT.csv`: exact mod identities and versions extracted from your report.
- `build_fairytale_quests.py`: generator source for future revisions.

## Quick fixes

- Questbook completely empty: verify FTB Quests (2001.4.x) is installed and copied files are nested exactly under `config/ftbquests/quests`.
- Quest tooltip shows missing item: check spelling and registry version for that specific modded item task.
- Checkmarks do not auto-complete: intentional; click them after doing the objective.
- Existing questbook disappeared: restore `config/ftbquests/quests` from the backup; this ZIP is a complete replacement, not a non-destructive patch.
- Commands require cheats/admin privileges. Don't grant that to normal users; the server operator can test quests and reload files.

Created for Adventures of Fairytale. Keep a backup before distribution.
