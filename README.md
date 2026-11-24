# Adventures of Fairytale

A Forge 1.20.1 CurseForge modpack (Forge 47.4.28, 12 GB RAM recommended).

## What's in here

| Path | What it is |
|---|---|
| `manifest.json` | The mod list CurseForge downloads (project + file IDs), pack name and version |
| `modlist.html` | Human-readable mod list shipped with the pack |
| `overrides/` | Everything copied on top of the mods when the pack installs |
| `overrides/config/` | Mod configs, FTB Quests, FancyMenu menus and assets |
| `overrides/kubejs/` | The pack's own scripts and assets (adventure book, boss route, fixes, balance) |
| `overrides/patchouli_books/` | The Adventure Book |
| `overrides/resourcepacks/`, `overrides/shaderpacks/` | Bundled packs |
| `profileImage/` | Pack icon |
| `dev/` | Source files that aren't part of the pack (none at the moment) |

## Building an importable zip

Zip `manifest.json`, `modlist.html` and the `overrides/` folder together, with them at the top level of
the zip and forward-slash paths. That zip imports into the CurseForge app (Create Custom Profile →
Import) and uploads to the CurseForge author dashboard as a new file.

## Notes

- Mods are never stored here, only referenced in `manifest.json`. To add one, add its CurseForge
  `projectID`/`fileID` there (and a line in `modlist.html`).
- `dev/` and `README.md` stay out of the zip.
