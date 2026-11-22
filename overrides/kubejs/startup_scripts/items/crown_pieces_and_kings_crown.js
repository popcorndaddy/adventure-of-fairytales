// Adventures of Fairytale - the King's Crown and its pieces
// The four pieces and the Dragon's Heart only come from bosses (see server_scripts/story/boss_route_pages_and_loot.js).

StartupEvents.registry('item', event => {
  let piece = (id, name, lore) => event.create(id)
    .displayName(name)
    .rarity('epic')
    .unstackable()
    .fireResistant()
    .tooltip(Text.of(lore).gray().italic())

  piece('crown_band', 'Band of the Crown', 'The gold ring the rest of the Crown was built on.')
  piece('crown_jewel', 'Jewel of the Crown', 'It still glows, faintly, when you hold it to the light.')
  piece('crown_crest', 'Crest of the Crown', "The King's mark, bent but whole.")
  piece('crown_setting', 'Setting of the Crown', 'The claws that held the Jewel in place.')

  event.create('dragons_heart')
    .displayName("Dragon's Heart")
    .rarity('epic')
    .unstackable()
    .fireResistant()
    .glow(true)
    .tooltip(Text.of('It is still beating.').darkPurple().italic())

  event.create('kings_crown', 'helmet')
    .displayName("The King's Crown")
    .rarity('epic')
    .fireResistant()
    .glow(true)
    .tooltip(Text.of('Bring it home.').gold().italic())
    .tooltip(Text.of('While worn: flight, Speed II, Haste II').lightPurple())
    .modifyTier(tier => {
      // slot order is feet, legs, chest, head: the crown alone gives 30 armor
      tier.setSlotProtections([3, 6, 8, 30])
      tier.setToughness(8.0)
      tier.setKnockbackResistance(0.3)
      tier.setDurabilityMultiplier(100)
      tier.setEnchantmentValue(30)
    })
    .modifyAttribute('minecraft:generic.max_health', 'fairytale_kings_crown_health', 40, 'addition')
    .modifyAttribute('minecraft:generic.luck', 'fairytale_kings_crown_luck', 2, 'addition')
})
