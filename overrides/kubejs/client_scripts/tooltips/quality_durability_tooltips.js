// Shows a quality's durability change on the tooltip ("Durability +50%"), and hides the tiny
// Luck marker that carries it (see server_scripts/balance/quality_durability.js).
const FtTipSlot = Java.loadClass('net.minecraft.world.entity.EquipmentSlot')
const FtTipLiving = Java.loadClass('net.minecraft.world.entity.LivingEntity')
const FtTipAttributes = Java.loadClass('net.minecraft.world.entity.ai.attributes.Attributes')

function ftTipDurability(stack) {
  // startup_scripts/fixes/quality_durability_tooltip.js hides the Luck marker on screen; it has its own reader
  if (global.ftQdtStackPercent) return global.ftQdtStackPercent(stack)
  let slots = [FtTipLiving.getEquipmentSlotForItem(stack), FtTipSlot.MAINHAND, FtTipSlot.OFFHAND]
  for (let i = 0; i < slots.length; i++) {
    let total = 0
    let it = stack.getAttributeModifiers(slots[i]).get(FtTipAttributes.LUCK).iterator()
    while (it.hasNext()) {
      let v = it.next().getAmount()
      if (Math.abs(v) < 0.001) total += v
    }
    let p = Math.round(total * 1e6)
    if (p != 0) return p
  }
  return 0
}

ItemEvents.tooltip(event => {
  let handler = (stack, advanced, text) => {
    try {
      if (!stack.isDamageableItem()) return
      let p = ftTipDurability(stack)
      if (p == 0) return
      for (let i = text.size() - 1; i >= 0; i--) {
        if (/^[+-]?0 Luck$/.test(String(text.get(i).getString()).trim())) text.remove(i)
      }
      if (p > 0) text.add(Text.green(` +${p}% Durability`))
      else if (p < 0) text.add(Text.red(` ${p}% Durability`))
    } catch (e) { }
  }
  if (event.addAdvancedToAll) event.addAdvancedToAll(handler)
  else event.addAdvanced(Ingredient.all, handler)
})
