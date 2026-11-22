// Adventures of Fairytale - Mystical Agriculture progression
// Mystical Agriculture gets strong fast, so every tier is tied to another part of the pack:
//   Infusion Altar ......... Create brass + Iron's Spells arcane essence
//   Seed bases ............. Hexerei mandrake root
//   Inferium seeds ......... infused on the altar (no more plain crafting)
//   Essence tiers are mixed in a Create mixer: 4 of the tier below around a crystal = 4 of the next.
//   The mixer hands the crystal back (Create returns crafting leftovers), so an Infusion Crystal
//   spends one of its uses (500, config/mysticalagriculture-common.toml) per 4 essence made.
//   Prudentium, Tertium .... Infusion Crystal
//   Imperium ............... Infusion Crystal, heated
//   Supremium .............. Master Infusion Crystal, heated
//   Insanium ............... Master Infusion Crystal, superheated
//   Machines ............... built on Create brass casings
//   Master Infusion Crystal  Imperium essence and gemstones around a Nether Star (Supremium needs the crystal)
//   Awakening Altar ........ needs Ignitium from Ignis

ServerEvents.recipes(event => {
  let MA = 'mysticalagriculture'

  // ---- remove the defaults being replaced
  ;[
    `${MA}:infusion_altar`, `${MA}:infusion_pedestal`, `${MA}:infusion_crystal`, `${MA}:master_infusion_crystal`,
    `${MA}:prosperity_seed_base`, `${MA}:inferium_seeds`,
    `${MA}:prudentium_essence`, `${MA}:tertium_essence`, `${MA}:imperium_essence`, `${MA}:supremium_essence`,
    'mysticalagradditions:insanium_essence',
    `${MA}:machine_frame`, `${MA}:awakening_altar`
  ].forEach(id => event.remove({ id: id }))

  // ---- the altar and pedestals
  event.shaped(`${MA}:infusion_altar`, ['GCG', ' S ', 'SSS'], {
    G: 'create:brass_ingot', C: 'irons_spellbooks:arcane_essence', S: 'minecraft:chiseled_stone_bricks'
  }).id('kubejs:mystical/infusion_altar')
  event.shaped(`${MA}:infusion_pedestal`, ['GCG', ' S ', ' S '], {
    G: 'create:brass_ingot', C: 'irons_spellbooks:arcane_essence', S: 'minecraft:chiseled_stone_bricks'
  }).id('kubejs:mystical/infusion_pedestal')

  // ---- crystals
  event.shaped(`${MA}:infusion_crystal`, ['A#A', '#X#', 'A#A'], {
    A: 'irons_spellbooks:arcane_essence', '#': `${MA}:prosperity_shard`, X: 'minecraft:diamond'
  }).id('kubejs:mystical/infusion_crystal')
  event.shaped(`${MA}:master_infusion_crystal`, ['E#E', '#X#', 'E#E'], {
    E: `${MA}:imperium_essence`, '#': `${MA}:imperium_gemstone`, X: 'minecraft:nether_star'
  }).id('kubejs:mystical/master_infusion_crystal')

  // ---- seeds
  event.shaped(`${MA}:prosperity_seed_base`, [' P ', 'PSP', ' M '], {
    P: `${MA}:prosperity_shard`, S: 'minecraft:wheat_seeds', M: 'hexerei:mandrake_root'
  }).id('kubejs:mystical/prosperity_seed_base')
  event.custom({
    type: `${MA}:infusion`,
    input: { item: 'minecraft:wheat_seeds' },
    ingredients: [
      { item: `${MA}:inferium_essence` }, { item: 'hexerei:sage_seed' },
      { item: `${MA}:inferium_essence` }, { item: 'hexerei:sage_seed' },
      { item: `${MA}:inferium_essence` }, { item: 'hexerei:sage_seed' },
      { item: `${MA}:inferium_essence` }, { item: 'hexerei:sage_seed' }
    ],
    result: { item: `${MA}:inferium_seeds` }
  }).id('kubejs:mystical/inferium_seeds')

  // ---- essence tiers, brewed in a Create mixer
  // 4 of the tier below around a crystal = 4 of the next tier: essence in matches essence out at every tier.
  // Create gives back each ingredient's crafting leftover, and a crystal's leftover is itself with one use spent,
  // so the crystal comes out of the basin with the essence (the Master crystal never wears down).
  let mix = (id, lower, crystal, result, heat) => {
    let ing = []
    for (let i = 0; i < 4; i++) ing.push({ item: lower })
    ing.push({ item: crystal })
    let recipe = { type: 'create:mixing', ingredients: ing, results: [{ item: result, count: 4 }] }
    if (heat) recipe.heatRequirement = heat
    event.custom(recipe).id(`kubejs:mystical/${id}`)
  }
  let CRYSTAL = `${MA}:infusion_crystal`
  let MASTER = `${MA}:master_infusion_crystal`
  mix('prudentium_essence', `${MA}:inferium_essence`, CRYSTAL, `${MA}:prudentium_essence`, null)
  mix('tertium_essence', `${MA}:prudentium_essence`, CRYSTAL, `${MA}:tertium_essence`, null)
  mix('imperium_essence', `${MA}:tertium_essence`, CRYSTAL, `${MA}:imperium_essence`, 'heated')
  mix('supremium_essence', `${MA}:imperium_essence`, MASTER, `${MA}:supremium_essence`, 'heated')
  mix('insanium_essence', `${MA}:supremium_essence`, MASTER, 'mysticalagradditions:insanium_essence', 'superheated')

  // ---- machines and the awakening altar
  event.shaped(`${MA}:machine_frame`, ['IRI', 'RCR', 'IRI'], {
    I: 'minecraft:iron_ingot', R: 'minecraft:redstone', C: 'create:brass_casing'
  }).id('kubejs:mystical/machine_frame')
  event.shaped(`${MA}:awakening_altar`, ['GCG', ' S ', 'SSS'], {
    G: 'cataclysm:ignitium_ingot', C: 'minecraft:orange_wool', S: `${MA}:soulstone`
  }).id('kubejs:mystical/awakening_altar')
})
