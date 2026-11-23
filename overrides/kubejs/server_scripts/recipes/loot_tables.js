// Adventures of Fairytale - loot changes
// End Remastered eyes no longer come from chests or mobs: each one comes from a boss
// (see server_scripts/story/boss_route_pages_and_loot.js), so they're removed from every loot table here.
// Tide and Aquaculture: Neptune's Bounty can also turn up as fishing treasure, whichever rod you use.

LootJS.modifiers(event => {
  event.addLootTableModifier(/.*/).removeLoot(/^endrem:[a-z_]+_eye$/)
  event.addLootTableModifier('minecraft:gameplay/fishing/treasure').randomChance(0.05).addLoot('aquaculture:neptunes_bounty')
})
