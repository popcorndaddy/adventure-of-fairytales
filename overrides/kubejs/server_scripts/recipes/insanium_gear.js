// Insanium gear (Mystical Adaptations): two Insanium Ingots and two Insanium Gemstones around a piece of
// Awakened Supremium gear make the Insanium version of it.
//
// Mystical Adaptations upgrades at a plain crafting table, which only carries over the damage: enchantments,
// Apotheosis affixes and gems, Quality Equipment qualities, Mystical Agriculture augments and custom names
// were all lost. These recipes replace its own and copy the whole piece across instead.
//
// If a piece carries its own attribute list in NBT (written by some other mod), the old piece's base stats
// in that list are swapped for the Insanium piece's base stats, and everything else in it is kept.
//
// Also added: the Insanium Staff (Mystical Adaptations registers it but ships no recipe), an Insanium Paxel
// from the Awakened Supremium Paxel, and a working Insanium Seed Reprocessor recipe (its own asks for an
// "awakened_supremium_reprocessor" that Mystical Agriculture 7 no longer has).

const FT_IG_SLOT = Java.loadClass('net.minecraft.world.entity.EquipmentSlot')
const FT_IG_REG = Java.loadClass('net.minecraft.core.registries.BuiltInRegistries')
const FT_IG_NBT = Java.loadClass('net.minecraft.nbt.NbtUtils')
const FT_IG_LIST = Java.loadClass('net.minecraft.nbt.ListTag')

// [awakened supremium piece, insanium piece]
const FT_IG_UPGRADES = [
  ['helmet', 'helmet'], ['chestplate', 'chestplate'], ['leggings', 'leggings'], ['boots', 'boots'],
  ['sword', 'sword'], ['axe', 'axe'], ['pickaxe', 'pickaxe'], ['shovel', 'shovel'], ['hoe', 'hoe'],
  ['sickle', 'sickle'], ['scythe', 'scythe'], ['shears', 'shears'], ['bow', 'bow'], ['crossbow', 'crossbow'],
  ['fishing_rod', 'fishing_rod'], ['staff', 'staff']
].map(p => ['mysticalagriculture:awakened_supremium_' + p[0], 'mysticaladaptations:insanium_' + p[1]])
FT_IG_UPGRADES.push(['mysticalagradditions:awakened_supremium_paxel', 'mysticaladaptations:insanium_paxel'])

// the item's own base modifiers for a slot, before any event changes them: [{attr, id, amount, op, mod}]
// Mystical Agriculture's armor has two getAttributeModifiers methods, (slot, stack) and (stack, slot), which
// Rhino can't choose between, so the Forge one is named by its full signature
const FT_IG_MODS_SIG = 'getAttributeModifiers(net.minecraft.world.entity.EquipmentSlot,net.minecraft.world.item.ItemStack)'
function ftIgItemMods(stack, slot) {
  let item = stack.getItem()
  try { return item[FT_IG_MODS_SIG](slot, stack) } catch (e) { return item.getDefaultAttributeModifiers(slot) }
}
global.ftIgItemMods = ftIgItemMods

function ftIgBase(id, slot) {
  let out = []
  let stack = Item.of(id)
  let it = ftIgItemMods(stack, slot).entries().iterator()
  while (it.hasNext()) {
    let e = it.next()
    let m = e.getValue()
    out.push({ attribute: e.getKey(), attr: String(FT_IG_REG.ATTRIBUTE.getKey(e.getKey())), id: String(m.getId()),
      amount: m.getAmount(), op: m.getOperation().toValue(), mod: m })
  }
  return out
}

// swap the old piece's base stats for the new piece's, in an NBT attribute list
function ftIgRebase(out, oldId, newId) {
  let tag = out.getNbt()
  let list = tag.getList('AttributeModifiers', 10)
  let kept = new FT_IG_LIST()
  let slots = FT_IG_SLOT.values()
  for (let i = 0; i < list.size(); i++) {
    let entry = list.getCompound(i)
    let slotName = String(entry.getString('Slot'))
    let attr = String(entry.getString('AttributeName'))
    let uuid = ''
    try { uuid = String(FT_IG_NBT.loadUUID(entry.get('UUID'))) } catch (e) {}
    let amount = entry.getDouble('Amount')
    let op = entry.getInt('Operation')
    let stale = false
    for (let s = 0; s < slots.length; s++) {
      if (String(slots[s].getName()) != slotName) continue
      ftIgBase(oldId, slots[s]).forEach(b => {
        if (b.attr != attr) return
        if (b.id == uuid || (b.op == op && Math.abs(b.amount - amount) < 1e-6)) stale = true
      })
    }
    if (!stale) kept.add(entry)
  }
  tag.put('AttributeModifiers', kept)
  for (let s = 0; s < slots.length; s++) {
    let slot = slots[s]
    ftIgBase(newId, slot).forEach(b => out.addAttributeModifier(b.attribute, b.mod, slot))
  }
}

function ftIgUpgrade(base, oldId, newId) {
  let out = Item.of(newId)
  // KubeJS renames the vanilla getTag/setTag/hasTag on item stacks to getNbt/setNbt/hasNBT
  // (its own hasTag(tagName) checks item tags instead)
  let baseTag = base.getNbt()
  if (baseTag) {
    let tag = baseTag.copy()
    tag.remove('FairytaleInsanium')   // from the old Insanium infusion, which these recipes replace
    out.setNbt(tag)
    if (tag.contains('AttributeModifiers', 9)) ftIgRebase(out, oldId, newId)
  }
  out.setCount(1)
  return out
}

ServerEvents.recipes(event => {
  let MAD = 'mysticaladaptations'
  // Mystical Adaptations' own upgrade recipes (they keep only damage) and its broken reprocessor recipe
  FT_IG_UPGRADES.forEach(p => {
    if (p[1] != `${MAD}:insanium_staff` && p[1] != `${MAD}:insanium_paxel`) event.remove({ id: p[1] })
  })
  event.remove({ id: `${MAD}:insanium_reprocessor` })

  FT_IG_UPGRADES.forEach(p => {
    let oldId = p[0]
    let newId = p[1]
    event.shaped(newId, [' G ', 'ISI', ' G '], {
      G: 'mysticalagradditions:insanium_gemstone',
      I: 'mysticalagradditions:insanium_ingot',
      S: oldId
    }).modifyResult((grid, result) => {
      let base = grid.find(Ingredient.of(oldId))
      if (base.isEmpty()) return result
      return ftIgUpgrade(base, oldId, newId)
    }).id(`kubejs:insanium_gear/${newId.split(':')[1]}`)
  })

  event.shaped(`${MAD}:insanium_reprocessor`, [' E ', 'IFI', ' B '], {
    E: 'mysticalagradditions:insanium_essence',
    I: 'mysticalagradditions:insanium_ingot',
    F: 'mysticalagriculture:seed_reprocessor',
    B: 'mysticalagradditions:insanium_block'
  }).id('kubejs:insanium_gear/insanium_reprocessor')
})
