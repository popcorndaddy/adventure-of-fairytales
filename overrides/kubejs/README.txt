ADVENTURES OF FAIRYTALE - WHERE THINGS LIVE
===========================================

Everything custom in this pack is in four places:

  kubejs/                        scripts, custom items, textures, sounds (this folder)
  patchouli_books/adventure_book the Adventure Book (Apollo's Notes and all the guide pages)
  config/ftbquests/quests        the quest book (42 chapters, one file per chapter)
  config/fancymenu               title screen, loading screens, menu backgrounds and videos


KUBEJS SCRIPTS
--------------
server_scripts/   (reload in game with /reload)
  story/
    boss_route_pages_and_loot.js   the 17-boss route: eyes and crown pieces, torn pages,
                                   shared loot for EVERY boss (listed bosses + anything with
                                   150+ health, Wither and Ender Dragon included): stacks split,
                                   gear re-rolled per player, chest-loot bosses re-rolled for the
                                   fighters who didn't strike last, the
                                   first-night page, eye clean-up, the King's Crown recipe
    title_cards_and_fanfares.js    welcome title card and the "Page Recovered" fanfare
                                   (sounds, titles, particles, timings)
    welcome_and_adventure_book.js  first join, for every player: the Adventure Book, then the
                                   welcome card; /adventurebook and /fairytalewelcome
                                   (new players start with only the Adventure Book: other mods'
                                   guide books are removed in their first 30 seconds; all craftable)
  crown/
    kings_crown_powers.js          what the crown does while worn: flight, Speed II,
                                   Haste II, sparkles, never breaks
  balance/
    quality_durability.js          Quality Equipment qualities also change durability (Worst
                                   wears out up to 1/3 faster, Legendary lasts 50% longer)
    food_recovery.js               Spice of Life: every meal of a different food gives each other
                                   food two steps back (rules in config/solclassic-defaults.toml)
  recipes/
    guide_book_recipes.js          recipes the Adventure Book shows for the Tide Fishing Journal
                                   and the Hexerei Book of Shadows ("Further Reading" pages)
    ars_and_irons_bond.js          Ars Nouveau + Iron's Spells lean on each other: Inscription
                                   Table (Worn Notebook), Scroll Forge (Source Gem Block),
                                   imbuing amethyst into Arcane Essence, Ars essences -> runes
    mod_bug_fixes.js               repairs other mods' broken recipes and tags (Forbidden Arcanus
                                   chest boats; Aether Redux, Farmer's Delight and Diet tags)
    insanium_gear.js               Mystical Adaptations' Insanium upgrades, remade so the piece keeps its
                                   enchantments, gems, quality, augments and name; adds the missing Insanium
                                   Staff and Awakened Supremium Paxel upgrades and fixes the Reprocessor recipe
    mystical_agriculture.js        Mystical Agriculture recipe changes (cross-mod recipes)
    essence_staffs.js              recipes for Mystical Agriculture's staffs (it ships none) and their Iron's
                                   Spells spell slots (1 at Inferium up to 4 at Insanium; imbue at an Arcane Anvil).
                                   Their damage and spell stats are in startup_scripts/balance/weapon_and_armor_buffs.js
    loot_tables.js                 removes End Remastered eyes from chests, adds
                                   Neptune's Bounty to fishing treasure
  checks/
    quest_item_check.js            on world load, logs any quest item missing from the game
    fairytale_test.js              /fairytaletest: the pack tests itself (bosses, pages, loot
                                   sharing, crown, eyes, items). Use a throwaway creative world.

startup_scripts/  (restart the game after changing these)
  items/
    crown_pieces_and_kings_crown.js  registers the 4 crown pieces, the Dragon's Heart and
                                     the King's Crown (stats, tooltips)
  balance/
    weapon_and_armor_buffs.js      every weapon +30% damage (min +1, no cap) and every armor
                                   piece extra toughness (30% of its armor, min 0.5, no cap);
                                   base stats only, affixes/gems/enchants stack on top; tune
                                   the numbers at the top of the file
  sounds/
    custom_sounds.js               registers the pack's own sounds
  book/
    install_adventure_book.js      writes the whole Adventure Book into patchouli_books/ on every launch,
                                   so it works even if an install is missing that folder (generated:
                                   run tools/book_installer_js.py after changing the book)
  fighters/
    boss_fights.js                 co-op boss fights: a swing or shot counts you as a fighter even
                                   if the boss blocks it, and the boss's XP is split between fighters
  fixes/
    aether_redux_crash_guard.js    stops a random Aether Redux startup crash
    sol_tooltip_rounding.js        Spice of Life tooltip shows 15%, 20%... instead of 14%, 19%
    quality_durability_tooltip.js  "Durability: 634 / 634 (+20%)" line under the item name: the real
                                   durability left after the quality's +/-% (wear is scaled by
                                   server_scripts/balance/quality_durability.js)

client_scripts/   (reload with F3+T)
  jei/
    hide_removed_eyes.js           hides the 4 End Remastered eyes that aren't used
  tooltips/
    quality_durability_tooltips.js shows "+50% Durability" etc. on items with a quality
    essence_staff_tooltips.js      hides "Not Yet Implemented" on the staffs and shows their spell slots
  welcome/
    ready_signal.js                tells the server when this player is past the loading screen,
                                   so their first-join intro plays when they can see it


ASSETS AND DATA
---------------
assets/kubejs/textures/item/        crown pieces, King's Crown, Dragon's Heart (+ .mcmeta = beating animation)
assets/kubejs/textures/models/armor the crown as it looks when worn
assets/kubejs/textures/gui/         the Adventure Book's custom cover and crafting frame
assets/kubejs/sounds/               title_dawn_of_adventure.ogg (welcome), letter_secret_found.ogg (pages)
assets/kubejs/sounds.json           sound definitions
assets/kubejs/lang/en_us.json       sound subtitles
assets/patchouli/lang/en_us.json    "A torn-out page" label on locked book entries
data/kubejs/advancements/fairytale/ hidden advancements that unlock each torn page
data/irons_spellbooks/loot_tables/  repaired Catacombs crypt + Citadel tome chests (the mod's own
                                    files used a 1.21 format and loaded empty)
data/ars_nouveau/recipes/           Mage's and Archmage spell book upgrades need Iron's Arcane
                                    Essence / Arcane Ingots (part of the Ars + Iron's bond)
data/naturalist/loot_tables/        tortoise drops a Scute again (used a 1.21 item name)


MENU SCREENS (config/fancymenu/assets)
--------------------------------------
title_screen_video_overgrown_cabin.mp4     title screen background video
create_world_background.png                the "Adventures of Fairytale" picture: startup loading screen,
                                           Create World screen, world loading screen and the menu
                                           background (global_menu_background_texture in options.txt)

Title screen (customization/title_screen_layout.txt): the video background with the firefly
overlay; every button stays in its normal Minecraft/Forge position.
The previous layout (custom button positions) is kept, switched off, as
customization/title_screen_layout_OLD_custom_buttons_disabled.txt.

Video sources: both videos came from moewalls.com (originally named
"minecraft-overgrown-cabin-moewalls-com.mp4" and "minecraft-fireflies-forest-moewalls-com.mp4").


OTHER
-----
config/solclassic-defaults.toml     Spice of Life: Classic Edition settings for new worlds (how much
                                    repeated foods are reduced). An existing world keeps its own copy
                                    in <world>/serverconfig/solclassic-server.toml.
config/quality_equipment.toml       Quality Equipment qualities (stronger than default, with
                                    durability markers: a tiny Luck value = durability % x 1e-6)
config/defaultoptions/options.txt   first-launch settings (fullscreen, GUI scale 2, VSync off, ambient 20%, music 15%),
                                    applied only when a player has no options.txt yet
config/resourcepackoverrides.json  the resource packs every player gets, in order, switched on and locked
                                   (includes Beautiful Enchanted Books: a cover per enchantment, via Forge CIT;
                                   706 covers load. Soul Weapons, Spartan Weaponry and a few other
                                   enchantments it has no art for keep the plain book. The pack is
                                   All Rights Reserved, so its art is not copied into this pack)
                                   (Resource Pack Overrides; hold T on the resource pack screen to reapply)
config/modernfix-mixins.properties remove_spawn_chunks=true: no "Preparing spawn area" wait when a world loads
config/jei/client/jei-client.ini   tooltipSearchMode = DISABLED: JEI starts several seconds faster after joining
config/attributeslib.cfg           Armor Formula: toughness counts (Apothic Attributes' default formula ignores it)
config/Obscuria/obscure-api-client.toml
                                    "Food Icons" = false. Obscure API's food tooltip crashes the game on a
                                    Wicker Basket outside your inventory (in the book, JEI or a chest);
                                    AppleSkin shows the same food values.
                                    "Equipment Icons" = false. Its icon row showed raw durability (ignoring
                                    quality) and a second damage number; Quark's row and the
                                    quality_durability_tooltip.js line replace it.

WRITING SCRIPTS: KubeJS on 1.20.1 runs an old JavaScript engine. Inside a function that contains
another function (an arrow callback counts), a `const` declared inside an if/try/loop block throws
"redeclaration of var" every time it runs. Use `let` inside functions; keep `const` for the top
level of a file.
Some vanilla methods are invisible to scripts when another mod overrides them with a mixin (for example
level.getGameTime() fails with "Cannot find function"). If a call works in /fairytaletest but not in play,
or the other way round, look for that error in logs/kubejs/server.log.

logs/kubejs/ in the game folder has a log for each script type; lines from these scripts
start with [Fairytale].

KubeJS documentation: https://kubejs.com/
