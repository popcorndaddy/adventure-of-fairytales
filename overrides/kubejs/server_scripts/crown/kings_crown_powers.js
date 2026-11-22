// The King's Crown: what it does while worn.
// Flight, Speed II and Haste II, a faint sparkle, and it can never break.
// (+20 hearts and +30 armor are on the item itself, see startup_scripts/items/crown_pieces_and_kings_crown.js)

const CROWN = 'kubejs:kings_crown'
const CROWN_FLAG = 'fairytale_crown_worn'

function crownOff(player) {
  let pd = player.persistentData
  if (!pd.getBoolean(CROWN_FLAG)) return
  pd.putBoolean(CROWN_FLAG, false)
  let name = player.username
  player.server.runCommandSilent(`effect clear ${name} minecraft:speed`)
  player.server.runCommandSilent(`effect clear ${name} minecraft:haste`)
  if (!player.isCreative() && !player.isSpectator()) {
    let ab = player.abilities
    ab.mayfly = false
    ab.flying = false
    player.onUpdateAbilities()
  }
}

PlayerEvents.tick(event => {
  let player = event.player
  if (player.age % 10 !== 0) return
  let head = player.headArmorItem
  if (head.id !== CROWN) { crownOff(player); return }

  let name = player.username
  let server = player.server

  // faint sparkle around the crown, every half second
  server.runCommandSilent(`execute at ${name} run particle minecraft:end_rod ~ ~2.1 ~ 0.25 0.08 0.25 0.003 1`)
  if (player.age % 40 === 0) server.runCommandSilent(`execute at ${name} run particle minecraft:wax_on ~ ~2.0 ~ 0.3 0.1 0.3 0.5 2`)

  if (player.age % 20 !== 0) return
  player.persistentData.putBoolean(CROWN_FLAG, true)

  // never breaks
  if (!(head.hasNBT() && head.nbt.getBoolean('Unbreakable'))) head.getOrCreateTag().putBoolean('Unbreakable', true)
  if (head.getDamageValue() > 0) head.setDamageValue(0)

  // creative-style flight
  let ab = player.abilities
  if (!ab.mayfly) {
    ab.mayfly = true
    player.onUpdateAbilities()
  }

  // Speed II and Haste II, no particles
  player.potionEffects.add('minecraft:speed', 260, 1, true, false)
  player.potionEffects.add('minecraft:haste', 260, 1, true, false)
})
