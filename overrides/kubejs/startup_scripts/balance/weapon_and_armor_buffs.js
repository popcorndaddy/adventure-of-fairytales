// Gear buffs: the pack is boss-heavy, so every weapon and armor piece is stronger.
// Works on vanilla and modded gear alike (Tinkers too), because it adjusts the attribute
// modifiers an item already has, instead of listing items one by one.
//
//   Weapons (anything with attack damage in the main hand):
//     +30% of its total damage, at least +1, no upper limit; the final number is rounded to 0.5.
//     Diamond sword 7 -> 9, netherite sword 8 -> 10.5, a 20-damage boss weapon -> 26.
//     The bonus is merged into the item's own damage line, so the tooltip shows one number.
//   Armor (each worn piece):
//     Its armor value is rounded to a clean half step (modded pieces often have values like 3.15).
//     +30% of its armor value as extra Armor Toughness, at least +0.5, no upper limit.
//     Full diamond: toughness 8 -> 14.5. Full netherite: 12 -> 18.5. Iron (no toughness): 0 -> 4.5.
//     Toughness is what keeps big boss hits from punching through your armor (config/attributeslib.cfg
//     puts toughness into Apothic Attributes' armor formula; by default it ignores toughness).
//
// Only the item's own stats are buffed. This runs at HIGHEST priority, before Apotheosis adds affix and
// gem stats, so those (and enchantments like Sharpness, which aren't item stats) always stack on top
// unchanged, and the same item gets the same bonus every launch.
//
// Tune the numbers below. The King's Crown is skipped: it has its own stats.

const FT_BUFF = {
  weaponPercent: 0.30, weaponMin: 1.0,
  toughnessPercent: 0.30, toughnessMin: 0.5,
  skip: ['kubejs:kings_crown']
}

// Mystical Agriculture's essence staffs (and Mystical Adaptations' Insanium Staff) ship unfinished: no stats,
// no use, "Not yet implemented". Here they are spell staves: melee damage plus Iron's Spells stats, and spell
// slots for scrolls imbued at an Arcane Anvil (slots: server_scripts/recipes/essence_staffs.js).
//   damage/speed are the staff's own (before the weapon buff above); power/regen/cdr/cast are percentages
const FT_STAFFS = {
  'mysticalagriculture:inferium_staff':           { slots: 1, damage: 4,  speed: -3.0, power: 5,  regen: 10, cdr: 0,  cast: 0,  mana: 0 },
  'mysticalagriculture:prudentium_staff':         { slots: 1, damage: 5,  speed: -3.0, power: 8,  regen: 15, cdr: 0,  cast: 0,  mana: 0 },
  'mysticalagriculture:tertium_staff':            { slots: 2, damage: 6,  speed: -2.9, power: 10, regen: 20, cdr: 5,  cast: 0,  mana: 0 },
  'mysticalagriculture:imperium_staff':           { slots: 2, damage: 7,  speed: -2.8, power: 13, regen: 25, cdr: 8,  cast: 5,  mana: 0 },
  'mysticalagriculture:supremium_staff':          { slots: 3, damage: 8,  speed: -2.8, power: 16, regen: 25, cdr: 10, cast: 8,  mana: 50 },
  'mysticalagriculture:awakened_supremium_staff': { slots: 3, damage: 10, speed: -2.7, power: 20, regen: 30, cdr: 12, cast: 10, mana: 100 },
  'mysticaladaptations:insanium_staff':           { slots: 4, damage: 12, speed: -2.6, power: 25, regen: 35, cdr: 15, cast: 15, mana: 200 }
}
global.fairytaleStaffs = FT_STAFFS

const FtUUID = Java.loadClass('java.util.UUID')
const FtRL = Java.loadClass('net.minecraft.resources.ResourceLocation')
const FtForgeRegistries = Java.loadClass('net.minecraftforge.registries.ForgeRegistries')
const FT_STAFF_UUID = {
  damage: 'cb3f55d3-645c-4f38-a497-9c13a33db5cf',   // vanilla's base attack damage id (shows as the green number)
  speed: 'fa233e1c-4180-4865-b01b-bcce9785aca3',    // vanilla's base attack speed id
  power: 'fa17f000-0000-4000-8000-000000000001', regen: 'fa17f000-0000-4000-8000-000000000002',
  cdr: 'fa17f000-0000-4000-8000-000000000003', cast: 'fa17f000-0000-4000-8000-000000000004',
  mana: 'fa17f000-0000-4000-8000-000000000005'
}
const FT_STAFF_ATTR = {
  power: 'irons_spellbooks:spell_power', regen: 'irons_spellbooks:mana_regen', cdr: 'irons_spellbooks:cooldown_reduction',
  cast: 'irons_spellbooks:cast_time_reduction', mana: 'irons_spellbooks:max_mana'
}
let FT_STAFF_ATTR_CACHE = null
function ftStaffAttr(key) {
  if (!FT_STAFF_ATTR_CACHE) FT_STAFF_ATTR_CACHE = {}
  if (!(key in FT_STAFF_ATTR_CACHE)) {
    let a = null
    try { a = FtForgeRegistries.ATTRIBUTES.getValue(new FtRL(FT_STAFF_ATTR[key])) } catch (e) {}
    FT_STAFF_ATTR_CACHE[key] = a
  }
  return FT_STAFF_ATTR_CACHE[key]
}

const FtAttributes = Java.loadClass('net.minecraft.world.entity.ai.attributes.Attributes')
const FtModifier = Java.loadClass('net.minecraft.world.entity.ai.attributes.AttributeModifier')
const FtOperation = Java.loadClass('net.minecraft.world.entity.ai.attributes.AttributeModifier$Operation')

function ftHalf(x) { return Math.round(x * 2) / 2 }
function ftCeilHalf(x) { return Math.ceil(x * 2 - 1e-9) / 2 }
// The buffed total, rounded to a clean half step (some mods, like Epic Knights, use stats such as 7.37:
// rounding only the bonus left numbers like 9.37, which tooltips then showed as both 9.37 and 9.4).
// Whole-number weapons get exactly the same result as before.
function ftBuffedTotal(total, percent, min) { return Math.max(ftHalf(total * (1 + percent)), ftCeilHalf(total + min)) }

// the item's own flat (ADDITION) modifiers for one attribute, as a plain array
function ftFlatMods(event, attribute) {
  let out = []
  let it = event.getModifiers().get(attribute).iterator()
  while (it.hasNext()) {
    let m = it.next()
    if (m.getOperation() == FtOperation.ADDITION) out.push(m)
  }
  return out
}

const FtForgeBus = Java.loadClass('net.minecraftforge.common.MinecraftForge')
const FtPriority = Java.loadClass('net.minecraftforge.eventbus.api.EventPriority')
const FtAttrEvent = Java.loadClass('net.minecraftforge.event.ItemAttributeModifierEvent')

function ftGearBuff(event) {
  try {
    let stack = event.getItemStack()
    if (stack.isEmpty()) return
    if (FT_BUFF.skip.indexOf(String(stack.id)) >= 0) return
    let slot = event.getSlotType()
    let slotName = String(slot.getName())

    if (slotName == 'mainhand') {
      let staff = FT_STAFFS[String(stack.id)]
      if (staff) {
        event.addModifier(FtAttributes.ATTACK_DAMAGE, new FtModifier(FtUUID.fromString(FT_STAFF_UUID.damage), 'Staff damage', staff.damage, FtOperation.ADDITION))
        event.addModifier(FtAttributes.ATTACK_SPEED, new FtModifier(FtUUID.fromString(FT_STAFF_UUID.speed), 'Staff speed', staff.speed, FtOperation.ADDITION))
        ;['power', 'regen', 'cdr', 'cast'].forEach(k => {
          let attr = ftStaffAttr(k)
          if (attr && staff[k] > 0) event.addModifier(attr, new FtModifier(FtUUID.fromString(FT_STAFF_UUID[k]), 'Staff ' + k, staff[k] / 100, FtOperation.MULTIPLY_BASE))
        })
        let mana = ftStaffAttr('mana')
        if (mana && staff.mana > 0) event.addModifier(mana, new FtModifier(FtUUID.fromString(FT_STAFF_UUID.mana), 'Staff mana', staff.mana, FtOperation.ADDITION))
      }
      let mods = ftFlatMods(event, FtAttributes.ATTACK_DAMAGE)
      if (mods.length == 0) return
      let total = 1 // a player's bare-hand damage, which the tooltip number includes
      let main = mods[0]
      mods.forEach(m => { total += m.getAmount(); if (m.getAmount() > main.getAmount()) main = m })
      if (main.getAmount() <= 0) return
      let bonus = ftBuffedTotal(total, FT_BUFF.weaponPercent, FT_BUFF.weaponMin) - total
      event.removeModifier(FtAttributes.ATTACK_DAMAGE, main)
      event.addModifier(FtAttributes.ATTACK_DAMAGE,
        new FtModifier(main.getId(), main.getName(), main.getAmount() + bonus, FtOperation.ADDITION))
      return
    }

    if (String(slot.getType().name()) == 'ARMOR') {
      let armor = ftFlatMods(event, FtAttributes.ARMOR)
      if (armor.length == 0) return
      let value = 0
      armor.forEach(m => { value += m.getAmount() })
      if (value <= 0) return
      // many modded pieces use armor values like 3.15; round the piece's armor to a clean half step too
      let cleanArmor = ftHalf(value)
      if (cleanArmor > 0 && Math.abs(cleanArmor - value) > 1e-6) {
        let big = armor[0]
        armor.forEach(m => { if (m.getAmount() > big.getAmount()) big = m })
        event.removeModifier(FtAttributes.ARMOR, big)
        event.addModifier(FtAttributes.ARMOR, new FtModifier(big.getId(), big.getName(), big.getAmount() + (cleanArmor - value), FtOperation.ADDITION))
        value = cleanArmor
      }
      let uuid = armor[0].getId()
      // fold into the piece's own toughness line when it has one with the same id, else add one
      let tough = ftFlatMods(event, FtAttributes.ARMOR_TOUGHNESS).filter(m => String(m.getId()) == String(uuid))
      let base = 0
      if (tough.length > 0) { base = tough[0].getAmount(); event.removeModifier(FtAttributes.ARMOR_TOUGHNESS, tough[0]) }
      // +30% of the armor value, with the piece's final toughness rounded to a clean half step
      let target = Math.max(ftHalf(base + value * FT_BUFF.toughnessPercent), ftCeilHalf(base + FT_BUFF.toughnessMin))
      event.addModifier(FtAttributes.ARMOR_TOUGHNESS,
        new FtModifier(uuid, 'Fairytale armor toughness', target, FtOperation.ADDITION))
    }
  } catch (e) {
    // never let a strange modded item break attribute loading
  }
}

// HIGHEST priority, so only the item's base stats are read (ForgeEvents.onEvent can only register at NORMAL,
// the same priority as Apotheosis, which made the order random). Registered once: startup scripts don't
// re-run in a running game, but the guard keeps a manual startup reload from adding a second copy.
if (!global.ftGearBuffRegistered) {
  global.ftGearBuffRegistered = true
  FtForgeBus.EVENT_BUS.addListener(FtPriority.HIGHEST, false, FtAttrEvent, event => ftGearBuff(event))
}

