// Essence staffs as spell staves (stats: startup_scripts/balance/weapon_and_armor_buffs.js).
// Mystical Agriculture registers a staff for every tier but ships no recipes for them, so here they get
// the same recipe line as its swords: Inferium from Arcane Essence and a Blaze Rod, each tier after from
// the one before (keeping its enchantments and imbued spells), Awakened Supremium on the Awakening Altar,
// Insanium in recipes/insanium_gear.js.
//
// Every staff carries an Iron's Spells spell container with as many slots as its tier allows. Put a scroll
// on it at an Arcane Anvil to imbue that spell; each scroll fills the next empty slot. The spells show up on
// the spell wheel while the staff is in your main hand.

const FT_STAFF_LINE = ['inferium', 'prudentium', 'tertium', 'imperium', 'supremium']
const FT_STAFF_KEY = 'irons_spellbooks:spell_container'
const FT_STAFF_LEGACY_KEY = 'ISB_Spells'
const FT_STAFF_CTAG = Java.loadClass('net.minecraft.nbt.CompoundTag')
const FT_STAFF_LTAG = Java.loadClass('net.minecraft.nbt.ListTag')

function ftStaffInfo(id) {
  let all = global.fairytaleStaffs
  return all ? all[id] : null
}

// give the staff its spell slots (or more of them, after an upgrade). Returns true if the stack changed.
function ftStaffSlots(stack) {
  if (!stack || stack.isEmpty()) return false
  let info = ftStaffInfo(String(stack.id))
  if (!info) return false
  let tag = stack.getOrCreateTag()
  let key = tag.contains(FT_STAFF_KEY) ? FT_STAFF_KEY : (tag.contains(FT_STAFF_LEGACY_KEY) ? FT_STAFF_LEGACY_KEY : null)
  if (key) {
    let cur = tag.getCompound(key)
    if (cur.getInt('maxSpells') >= info.slots && cur.getBoolean('spellWheel') && !cur.getBoolean('mustEquip')) return false
    cur.putInt('maxSpells', Math.max(cur.getInt('maxSpells'), info.slots))
    cur.putBoolean('spellWheel', true)
    cur.putBoolean('mustEquip', false)
    tag.put(key, cur)
    return true
  }
  let fresh = new FT_STAFF_CTAG()
  fresh.putInt('maxSpells', info.slots)
  fresh.putBoolean('spellWheel', true)
  fresh.putBoolean('mustEquip', false)
  fresh.putBoolean('improved', false)
  fresh.put('data', new FT_STAFF_LTAG())
  tag.put(FT_STAFF_KEY, fresh)
  return true
}
global.fairytaleStaffSlots = ftStaffSlots

ServerEvents.tags('item', event => {
  // lets the Arcane Anvil imbue them even before they've been given their slots
  Object.keys(global.fairytaleStaffs || {}).forEach(id => event.add('irons_spellbooks:imbue_whitelist', id))
})

ServerEvents.recipes(event => {
  let MA = 'mysticalagriculture'
  event.shaped(`${MA}:inferium_staff`, [' G ', 'IAI', ' R '], {
    G: `${MA}:inferium_gemstone`, I: `${MA}:inferium_ingot`, A: 'irons_spellbooks:arcane_essence', R: 'minecraft:blaze_rod'
  }).id('kubejs:mystical/staff/inferium_staff')
  for (let i = 1; i < FT_STAFF_LINE.length; i++) {
    let tier = FT_STAFF_LINE[i]
    event.custom({
      type: 'cucumber:shaped_transfer_damage',
      transfer_nbt: true,
      pattern: [' G ', 'ISI', ' G '],
      key: {
        G: { item: `${MA}:${tier}_gemstone` },
        I: { item: `${MA}:${tier}_ingot` },
        S: { item: `${MA}:${FT_STAFF_LINE[i - 1]}_staff` }
      },
      result: { item: `${MA}:${tier}_staff` }
    }).id(`kubejs:mystical/staff/${tier}_staff`)
  }
  event.custom({
    type: `${MA}:awakening`,
    transfer_nbt: true,
    essences: [
      { item: `${MA}:air_essence`, count: 40 }, { item: `${MA}:earth_essence`, count: 40 },
      { item: `${MA}:water_essence`, count: 40 }, { item: `${MA}:fire_essence`, count: 40 }
    ],
    input: { item: `${MA}:supremium_staff` },
    ingredients: [
      { item: `${MA}:awakened_supremium_gemstone` }, { item: `${MA}:awakened_supremium_ingot` },
      { item: `${MA}:awakened_supremium_gemstone` }, { item: `${MA}:awakened_supremium_ingot` }
    ],
    result: { item: `${MA}:awakened_supremium_staff` }
  }).id('kubejs:mystical/staff/awakened_supremium_staff')
})

// a staff gets its slots the moment it lands in an inventory (crafted, picked up, from creative, upgraded)
PlayerEvents.inventoryChanged(event => {
  try { ftStaffSlots(event.item) } catch (e) { console.warn(`[Fairytale] staff slots: ${e}`) }
})
