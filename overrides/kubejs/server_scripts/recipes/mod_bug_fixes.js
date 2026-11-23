// Fixes for other mods' broken recipes and tags (found by scanning the game log).
// Each one points at an item that doesn't exist in this pack, or uses a format 1.20.1 Forge can't read.
// Broken loot tables are replaced by files in kubejs/data (see kubejs/README.txt).

ServerEvents.recipes(event => {
  // Forbidden Arcanus: the chest boat recipes use a Fabric-only ingredient format and never load
  event.shapeless('forbidden_arcanus:aurum_chest_boat', ['forbidden_arcanus:aurum_boat', '#forge:chests/wooden'])
    .id('forbidden_arcanus:aurum_chest_boat')
  event.shapeless('forbidden_arcanus:edelwood_chest_boat', ['forbidden_arcanus:edelwood_boat', '#forge:chests/wooden'])
    .id('forbidden_arcanus:edelwood_chest_boat')
})

// A tag with even one entry for a missing item fails to load completely. Removing every missing
// entry lets the rest of the tag load as intended. The lists are the game log's "Couldn't load tag" errors.
const FT_TAG_FIXES = {
  "aether_redux:swet_jelly": [
    "aether_genesis:blue_swet_jelly",
    "aether_genesis:dark_swet_jelly",
    "aether_genesis:golden_swet_jelly"
  ],
  "farmersdelight:sweets": [
    "twilightdelight:aurora_cake_slice",
    "twilightdelight:aurora_ice_cream",
    "twilightdelight:aurora_milkshake",
    "twilightdelight:glacier_cake_slice",
    "twilightdelight:glacier_ice_cream",
    "twilightdelight:glacier_milkshake",
    "twilightdelight:phytochemical_cake_slice",
    "twilightdelight:phytochemical_ice_cream",
    "twilightdelight:phytochemical_milkshake",
    "twilightdelight:rainbow_ice_cream",
    "twilightdelight:refreshing_ice_cream",
    "twilightdelight:torchberry_cake_slice",
    "twilightdelight:torchberry_ice_cream",
    "twilightdelight:torchberry_milkshake",
    "twilightdelight:twilight_ice_cream"
  ],
  "farmersdelight:snacks": [
    "twilightdelight:aurora_cake_slice",
    "twilightdelight:glacier_cake_slice",
    "twilightdelight:phytochemical_cake_slice",
    "twilightdelight:torchberry_cake_slice"
  ],
  "diet:sugars": [
    "twilightdelight:aurora_cake_slice",
    "twilightdelight:aurora_ice_cream",
    "twilightdelight:aurora_milkshake",
    "twilightdelight:glacier_cake_slice",
    "twilightdelight:glacier_ice_cream",
    "twilightdelight:glacier_milkshake",
    "twilightdelight:phytochemical_cake_slice",
    "twilightdelight:phytochemical_ice_cream",
    "twilightdelight:phytochemical_milkshake",
    "twilightdelight:rainbow_ice_cream",
    "twilightdelight:refreshing_ice_cream",
    "twilightdelight:torchberry_cake_slice",
    "twilightdelight:torchberry_ice_cream",
    "twilightdelight:torchberry_milkshake",
    "twilightdelight:twilight_ice_cream"
  ],
  "ctov:wares/cardboard_box": ["wares:cardboard_box"],
  "ctov:wares/sealed_delivery_agreement": ["wares:sealed_delivery_agreement"]
}
// the same for biome tags (Integrated Dungeons and Structures lists two Oh The Biomes You'll Go biomes)
const FT_BIOME_TAG_FIXES = {
  "idas:has_structure/byg_redwood_biomes": ["byg:redwood_thicket"],
  "idas:has_structure/bygmohogany_biomes": ["byg:tropical_rainforest"]
}
ServerEvents.tags('worldgen/biome', event => {
  // When Dungeons Arise's Mechanical Nest (the giant floating steampunk city) drops FPS from 150+ to 15-20
  // anywhere near it, so it no longer generates (also emptied in data/dungeons_arise/tags/.../mechanical_nest_biomes.json).
  // Nests already generated in a world stay.
  try { event.removeAll('dungeons_arise:has_structure/mechanical_nest_biomes') } catch (e) { console.warn(`[Fairytale] couldn't disable the Mechanical Nest: ${e}`) }
  Object.keys(FT_BIOME_TAG_FIXES).forEach(tag => {
    FT_BIOME_TAG_FIXES[tag].forEach(missing => {
      try { event.remove(tag, missing) } catch (e) { console.warn(`[Fairytale] couldn't repair biome tag ${tag}: ${e}`) }
    })
  })
})
ServerEvents.tags('item', event => {
  Object.keys(FT_TAG_FIXES).forEach(tag => {
    FT_TAG_FIXES[tag].forEach(missing => {
      try { event.remove(tag, missing) } catch (e) { console.warn(`[Fairytale] couldn't repair tag ${tag}: ${e}`) }
    })
  })
})
