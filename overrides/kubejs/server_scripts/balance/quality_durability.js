// Quality Equipment durability: a quality now also changes how fast an item wears out.
// Bad qualities wear out up to a third faster (-25%); "Legendary" or "Masterful" gear lasts 50% longer.
// Each quality in config/quality_equipment.toml carries a tiny Luck marker whose value is its
// durability change x 1e-6 (-50% -> -0.00005); tools/quality_config.py writes them.
// Every half second the worn and held items are compared with last time, and any wear is
// scaled up (fragile) or partly refunded (sturdy). Tinkers tools are left alone: they have
// their own durability system.

const FtQSlot = Java.loadClass('net.minecraft.world.entity.EquipmentSlot')
const FtQAttributes = Java.loadClass('net.minecraft.world.entity.ai.attributes.Attributes')
const FT_QSLOTS = ['MAINHAND', 'OFFHAND', 'HEAD', 'CHEST', 'LEGS', 'FEET']

// durability change in percent (e.g. -40, 50) for a stack in a slot, 0 if none
function ftQualityDurability(stack, slot) {
  let total = 0
  let it = stack.getAttributeModifiers(slot).get(FtQAttributes.LUCK).iterator()
  while (it.hasNext()) {
    let v = it.next().getAmount()
    if (Math.abs(v) < 0.001) total += v
  }
  return Math.round(total * 1e6)
}
global.ftQualityDurability = ftQualityDurability

PlayerEvents.tick(event => {
  let player = event.player
  if (player.age % 10 != 0) return
  let data = player.persistentData
  if (!data.contains('ft_qdur')) data.put('ft_qdur', new (Java.loadClass('net.minecraft.nbt.CompoundTag'))())
  let memory = data.getCompound('ft_qdur')
  FT_QSLOTS.forEach(name => {
    let slot = FtQSlot[name]
    let stack = player.getItemBySlot(slot)
    if (stack.isEmpty() || !stack.isDamageableItem()) { memory.remove(name); return }
    let id = String(stack.id)
    let dmg = stack.getDamageValue()
    let before = memory.getCompound(name)
    memory.put(name, before)
    let sameItem = before.getString('id') == id
    let prev = before.getInt('dmg')
    before.putString('id', id)
    before.putInt('dmg', dmg)
    if (!sameItem || id.indexOf('tconstruct:') == 0) return
    let worn = dmg - prev
    if (worn <= 0 || worn > 64) return   // repaired, mended, or a different item swapped in
    let p = ftQualityDurability(stack, slot)
    if (p == 0) return
    // an item with +p% durability wears at 1/(1+p) the normal rate
    let change = worn * (1 / (1 + p / 100) - 1)          // >0 extra wear, <0 refund
    let whole = change > 0 ? Math.floor(change) : Math.ceil(change)
    let step = whole + (Math.random() < Math.abs(change - whole) ? (change > 0 ? 1 : -1) : 0)
    if (step == 0) return
    let next = Math.max(prev, dmg + step)
    if (next >= stack.getMaxDamage()) {
      stack.shrink(1)
      player.server.runCommandSilent(`execute as ${player.username} at @s run playsound minecraft:entity.item.break player @a ~ ~ ~ 0.8 0.9`)
      memory.remove(name)
      return
    }
    stack.setDamageValue(next)
    before.putInt('dmg', next)
  })
})
