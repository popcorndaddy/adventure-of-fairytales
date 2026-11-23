// Adventures of Fairytale - durability numbers include the item's quality
//
// A Quality Equipment quality such as "+20% Durability" or "-20% Durability" can't change an item's real
// maximum durability (that is fixed per item type). Instead quality_durability.js (server script) makes the
// item wear out slower or faster. So a +20% diamond chestplate takes 20% more hits before it breaks, but the
// raw numbers would still say 528/528.
//
// This adds one line under the item name showing the durability the item really has left:
//     Durability: 634 / 634 (+20%)
// It counts down by 1 per use, like normal durability, and the durability bar already matches it.
// Items without a quality show their plain numbers. Obscure API's icon row (which showed the raw numbers)
// is turned off in config/Obscuria/obscure-api-client.toml; the vanilla F3+H durability line is replaced
// by this one so there is never a second, different number. Tinkers' Construct tools are left alone: they
// show their own durability.
//
// The quality's durability change rides on a tiny Luck modifier (e.g. -0.000025 for -25%). The server needs it,
// but on screen Quark drew it as a clover icon reading "-0%" or "+0%". On the game's own (render) thread the
// marker is dropped from the item's modifiers, except while these scripts read it, so it never shows up.
// The server, which does the wear scaling, always keeps it.

const FT_QDT_ATTRS = Java.loadClass('net.minecraft.world.entity.ai.attributes.Attributes')
const FT_QDT_SLOT = Java.loadClass('net.minecraft.world.entity.EquipmentSlot')
const FT_QDT_LIVING = Java.loadClass('net.minecraft.world.entity.LivingEntity')
const FT_QDT_TRANSLATABLE = Java.loadClass('net.minecraft.network.chat.contents.TranslatableContents')
const FT_QDT_COMPONENT = Java.loadClass('net.minecraft.network.chat.Component')
const FT_QDT_FORMAT = Java.loadClass('net.minecraft.ChatFormatting')
const FT_QDT_BUS = Java.loadClass('net.minecraftforge.common.MinecraftForge')
const FT_QDT_PRIORITY = Java.loadClass('net.minecraftforge.eventbus.api.EventPriority')
const FT_QDT_ATTR_EVENT = Java.loadClass('net.minecraftforge.event.ItemAttributeModifierEvent')

global.ftQdtReading = 0

// durability change in percent (e.g. -20, 50) for a stack in a slot; same reading as quality_durability.js
function ftQdtPercent(stack, slot) {
  let total = 0
  global.ftQdtReading++
  try {
    let it = stack.getAttributeModifiers(slot).get(FT_QDT_ATTRS.LUCK).iterator()
    while (it.hasNext()) {
      let v = it.next().getAmount()
      if (Math.abs(v) < 0.001) total += v
    }
  } finally {
    global.ftQdtReading--
  }
  return Math.round(total * 1e6)
}
global.ftQdtStackPercent = stack => ftQdtStackPercent(stack)

// hide the Luck marker from everything drawn on screen (runs last, after Quality Equipment adds it)
let ftQdtMinecraft = null
function ftQdtHideMarker(event) {
  try {
    if (global.ftQdtReading > 0) return
    if (!Platform.isClientEnvironment()) return
    if (ftQdtMinecraft == null) ftQdtMinecraft = Java.loadClass('net.minecraft.client.Minecraft').getInstance()
    if (ftQdtMinecraft == null || !ftQdtMinecraft.isSameThread()) return
    let mods = event.getModifiers().get(FT_QDT_ATTRS.LUCK).toArray()
    for (let i = 0; i < mods.length; i++) {
      if (Math.abs(mods[i].getAmount()) < 0.001) event.removeModifier(FT_QDT_ATTRS.LUCK, mods[i])
    }
  } catch (e) {
    // never break an item's attributes over a cosmetic detail
  }
}
if (!global.ftQdtMarkerRegistered) {
  global.ftQdtMarkerRegistered = true
  FT_QDT_BUS.EVENT_BUS.addListener(FT_QDT_PRIORITY.LOWEST, false, FT_QDT_ATTR_EVENT, event => ftQdtHideMarker(event))
}

function ftQdtStackPercent(stack) {
  let slot = FT_QDT_LIVING.getEquipmentSlotForItem(stack)
  let p = ftQdtPercent(stack, slot)
  if (p == 0 && slot != FT_QDT_SLOT.MAINHAND) p = ftQdtPercent(stack, FT_QDT_SLOT.MAINHAND)
  if (p == 0 && slot != FT_QDT_SLOT.OFFHAND) p = ftQdtPercent(stack, FT_QDT_SLOT.OFFHAND)
  return p
}

ForgeEvents.onEvent('net.minecraftforge.event.entity.player.ItemTooltipEvent', event => {
  try {
    let stack = event.getItemStack()
    if (stack.isEmpty() || !stack.isDamageableItem()) return
    if (String(stack.getId()).indexOf('tconstruct:') == 0) return
    let max = stack.getMaxDamage()
    if (max <= 0) return
    let p = ftQdtStackPercent(stack)
    let factor = 1 + p / 100
    let left = max - stack.getDamageValue()
    let effMax = Math.max(1, Math.round(max * factor))
    let effLeft = Math.max(0, Math.min(effMax, Math.round(left * factor)))

    let line = FT_QDT_COMPONENT.literal('Durability: ').withStyle(FT_QDT_FORMAT.GRAY)
      .append(FT_QDT_COMPONENT.literal(effLeft + ' / ' + effMax).withStyle(FT_QDT_FORMAT.WHITE))
    if (p != 0) {
      line.append(FT_QDT_COMPONENT.literal(' (' + (p > 0 ? '+' : '') + p + '%)')
        .withStyle(p > 0 ? FT_QDT_FORMAT.GREEN : FT_QDT_FORMAT.RED))
    }

    let lines = event.getToolTip()
    // drop the vanilla advanced-tooltip line (F3+H), which shows the raw numbers
    for (let i = lines.size() - 1; i >= 1; i--) {
      let contents = lines.get(i).getContents()
      if (contents instanceof FT_QDT_TRANSLATABLE && String(contents.getKey()) == 'item.durability') lines.remove(i)
    }
    lines.add(Math.min(1, lines.size()), line)
  } catch (e) {
    // a tooltip must never crash the game: leave it as it was
  }
})
