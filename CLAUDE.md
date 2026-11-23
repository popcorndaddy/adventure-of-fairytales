# Adventures of Fairytale - project core

Rootstock v1.65 installed 2026-11-22 | updates: ask | level: standard | community: no

A Forge 1.20.1 (47.4.28) CurseForge modpack for a small group of friends, plus its own content:
the Withered Sentinel boss (KubeJS + GeckoLib model) and the Ancient Gatekeeper boss (Forge mod
`gatekeeper-mod/`, art in `gatekeeper-art/`). The owner (the CEO) is not a programmer: explain in plain words.

## How to read
- The one door: docs/index/MASTER_INDEX.md lists every topic file, root note and rule, one line each.
- Grep headings first, read one section; a file past ~10k tokens is section-read or delegated.
- Topic files live in docs/systems/; root *_METHOD.md files are the Rootstock methods.

## How to verify
- Pack change: build the zip (README.md "Building an importable zip") and launch the CurseForge instance.
- Boss/mod change: `gradlew runGameTestServer` in `gatekeeper-mod/` (Java 17).
- Animation change: render the contact sheets (`tools/blender-geckolib/sheets.py`) and look at them.
- Rootstock: `py -3 tools/check_claude_md.py` and `py -3 tools/standup.py`.

## Laws no hook enforces
- Mods are referenced in manifest.json, never committed as jars.
- `dev/` and `README.md` stay out of the pack zip.
- Never commit secrets, the CurseForge instance folder, or world saves.
- THE CONTRADICTION RULE: if the CEO asks for something that contradicts a rule they set
  earlier, FLAG it and get explicit confirmation - never silently comply, never silently refuse.
- Python here is `py -3` (the `python` command is the Microsoft Store placeholder).
