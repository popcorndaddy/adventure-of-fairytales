// Adventures of Fairytale - Spice of Life tooltip shows the right percentage
//
// Spice of Life writes "Hunger recovery reduced by X%" as (int)((1 - multiplier) * 100). Some decimals can't be
// stored exactly (0.85 is kept as 0.8500000238), so 15% came out as 14.99999 and was cut down to 14%, then 19%,
// 24%, and so on up to 50%. The food itself always gave the right amount; only the displayed number was off.
//
// This rewrites that one tooltip line with the number rounded properly. Spice of Life adds its line in a HIGH
// priority tooltip listener (through Architectury); this one runs at normal priority, so always after it.

const FT_SOLT_CALC = Java.loadClass('com.github.leopoko.solclassic.utils.FoodCalculator')
const FT_SOLT_TRANSLATABLE = Java.loadClass('net.minecraft.network.chat.contents.TranslatableContents')
const FT_SOLT_COMPONENT = Java.loadClass('net.minecraft.network.chat.Component')

ForgeEvents.onEvent('net.minecraftforge.event.entity.player.ItemTooltipEvent', event => {
  try {
    let player = event.getEntity()
    if (!player) return
    let lines = event.getToolTip()
    for (let i = 0; i < lines.size(); i++) {
      let line = lines.get(i)
      let contents = line.getContents()
      if (!(contents instanceof FT_SOLT_TRANSLATABLE)) continue
      if (String(contents.getKey()) != 'tooltip.food_reduction') continue
      let multiplier = FT_SOLT_CALC.CalculateMultiplier(event.getItemStack(), player)
      let percent = Math.round((1 - multiplier) * 100)
      lines.set(i, FT_SOLT_COMPONENT.translatable('tooltip.food_reduction', String(percent)).setStyle(line.getStyle()))
      return
    }
  } catch (e) {
    // a tooltip must never crash the game: leave Spice of Life's own line as it was
  }
})
