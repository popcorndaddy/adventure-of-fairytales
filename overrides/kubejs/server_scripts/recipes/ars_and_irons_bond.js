// Ars Nouveau + Iron's Spells 'n Spellbooks: two schools of the same art.
// Each mod leans on the other a little, so a mage ends up using both:
//   Iron's needs Ars:  Inscription Table (Worn Notebook), Scroll Forge (Source Gem Block)
//   Ars needs Iron's:  Apprentice / Archmage book upgrades (Arcane Essence / Arcane Ingots;
//                      see kubejs/data/ars_nouveau/recipes)
//   Shared:            Ars Imbuement Chamber makes Iron's Arcane Essence from amethyst,
//                      (with lapis on a pedestal), and every Ars elemental essence can etch an Iron's rune.
// Every original recipe that isn't listed here still works as before.

ServerEvents.recipes(event => {
  // --- Iron's tables are built with Ars pieces
  event.remove({ id: 'irons_spellbooks:inscription_table' })
  event.shaped('irons_spellbooks:inscription_table', ['  B', 'TTT', 'L L'], {
    B: 'ars_nouveau:worn_notebook',
    T: '#minecraft:wooden_slabs',
    L: '#minecraft:wooden_fences'
  }).id('kubejs:ars_bond/inscription_table')

  event.remove({ id: 'irons_spellbooks:scroll_forge' })
  event.shaped('irons_spellbooks:scroll_forge', ['DDD', ' S ', 'OOO'], {
    D: 'minecraft:polished_deepslate',
    S: 'ars_nouveau:source_gem_block',
    O: 'minecraft:crying_obsidian'
  }).id('kubejs:ars_bond/scroll_forge')

  // --- Ars imbuement makes Iron's Arcane Essence (it still drops from magic mobs and loot too)
  event.custom({
    type: 'ars_nouveau:imbuement',
    input: { item: 'minecraft:amethyst_shard' },
    output: 'irons_spellbooks:arcane_essence',
    count: 2,
    source: 1000,
    // plain amethyst already makes Source Gems; a lapis on one pedestal (not consumed) makes it essence instead
    pedestalItems: [{ item: { item: 'minecraft:lapis_lazuli' } }]
  }).id('kubejs:ars_bond/imbue_arcane_essence')

  // --- An Ars elemental essence can stand in for the eight focus items of an Iron's rune
  let FT_RUNE_BOND = {
    fire_essence: 'fire_rune',
    water_essence: 'ice_rune',
    air_essence: 'lightning_rune',
    earth_essence: 'nature_rune',
    abjuration_essence: 'holy_rune',
    conjuration_essence: 'evocation_rune',
    manipulation_essence: 'ender_rune'
  }
  Object.keys(FT_RUNE_BOND).forEach(essence => {
    let rune = FT_RUNE_BOND[essence]
    event.shapeless(`irons_spellbooks:${rune}`, ['irons_spellbooks:blank_rune', `ars_nouveau:${essence}`])
      .id(`kubejs:ars_bond/${rune}`)
  })

})
