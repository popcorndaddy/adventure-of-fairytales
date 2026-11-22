// Adventures of Fairytale - bosses, eyes, Crown pieces and Apollo's pages
// Generated from tools/fairy_lore.py.
//
// * Every player who deals at least 5% of a major boss's health counts as having fought it.
// * Boss gear (anything that doesn't stack) is copied to every fighter. Everything that stacks is split evenly.
// * Route bosses also give every fighter their own eye or Crown piece.
// * Everyone within 64 blocks (and every fighter) gets that boss's page back in the Adventure Book.
// * End Remastered eyes only exist when a boss gives them. Any other eye crumbles to dust.

const ROUTE = {
  "mowziesmobs:ferrous_wroughtnaut": {
    "page": "p01",
    "name": "the Ferrous Wroughtnaut",
    "reward": "endrem:lost_eye"
  },
  "mowziesmobs:frostmaw": {
    "page": "p02",
    "name": "the Frostmaw",
    "reward": "endrem:cold_eye"
  },
  "mowziesmobs:umvuthi": {
    "page": "p03",
    "name": "Umvuthi",
    "reward": "endrem:rogue_eye"
  },
  "born_in_chaos_v1:sir_pumpkinhead": {
    "page": "p04",
    "name": "Sir Pumpkinhead",
    "reward": "endrem:witch_eye"
  },
  "born_in_chaos_v1:sir_pumpkinhead_without_horse": {
    "page": "p04",
    "name": "Sir Pumpkinhead",
    "reward": "endrem:witch_eye"
  },
  "irons_spellbooks:dead_king": {
    "page": "p05",
    "name": "the Dead King",
    "reward": "endrem:undead_eye"
  },
  "aquamirae:captain_cornelia": {
    "page": "p06",
    "name": "Captain Cornelia",
    "reward": "endrem:black_eye"
  },
  "twilightforest:lich": {
    "page": "p07",
    "name": "the Twilight Lich",
    "reward": "endrem:magical_eye"
  },
  "bosses_of_mass_destruction:lich": {
    "page": "p08",
    "name": "the Night Lich",
    "reward": "endrem:evil_eye"
  },
  "block_factorys_bosses:sandworm": {
    "page": "p09",
    "name": "the Sandworm",
    "reward": "endrem:exotic_eye"
  },
  "cataclysm:ancient_remnant": {
    "page": "p10",
    "name": "the Ancient Remnant",
    "reward": "endrem:old_eye"
  },
  "cataclysm:the_leviathan": {
    "page": "p11",
    "name": "the Leviathan",
    "reward": "endrem:guardian_eye"
  },
  "cataclysm:netherite_monstrosity": {
    "page": "p12",
    "name": "the Netherite Monstrosity",
    "reward": "endrem:nether_eye"
  },
  "block_factorys_bosses:underworld_knight": {
    "page": "p13",
    "name": "the Underworld Knight",
    "reward": "kubejs:crown_band"
  },
  "bosses_of_mass_destruction:void_blossom": {
    "page": "p14",
    "name": "the Void Blossom",
    "reward": "kubejs:crown_jewel"
  },
  "minecraft:wither": {
    "page": "p15",
    "name": "the Wither",
    "reward": "kubejs:crown_crest"
  },
  "cataclysm:the_harbinger": {
    "page": "p16",
    "name": "the Harbinger",
    "reward": "kubejs:crown_setting"
  },
  "minecraft:ender_dragon": {
    "page": "p17",
    "name": "the Ender Dragon",
    "reward": "kubejs:dragons_heart"
  }
}
const OTHER_BOSSES = ["cataclysm:ignis", "cataclysm:ender_guardian", "cataclysm:maledictus", "bosses_of_mass_destruction:gauntlet", "bosses_of_mass_destruction:obsidilith", "block_factorys_bosses:kraken", "aquamirae:maze_mother", "born_in_chaos_v1:lord_pumpkinhead", "soulsweapons:moonknight", "soulsweapons:frost_giant", "soulsweapons:draugr_boss", "soulsweapons:chaos_monarch", "soulsweapons:accursed_lord_boss", "twilightforest:naga", "twilightforest:minoshroom", "twilightforest:knight_phantom", "twilightforest:hydra", "twilightforest:ur_ghast", "twilightforest:alpha_yeti", "twilightforest:snow_queen", "iceandfire:fire_dragon", "iceandfire:ice_dragon", "iceandfire:lightning_dragon", "iceandfire:sea_serpent", "iceandfire:myrmex_queen", "iceandfire:cyclops", "iceandfire:hydra", "aether:slider", "aether:valkyrie_queen", "aether:sun_spirit", "minecraft:warden", "minecraft:elder_guardian"]
const PAGE_RANGE = 64
const PAGE_TITLES = {"start": "Apollo's Book", "night": "What's Left", "p01": "Under the Hills", "p02": "The Snowfields", "p03": "The Grove", "p04": "The Pumpkin Rider", "p05": "The Catacombs", "p06": "The Frozen Sea", "p07": "The Dusk Forest", "p08": "The Cold Tower", "p09": "The Worm", "p10": "Cursed Pyramid", "p11": "The Sunken City", "p12": "Twelve", "p13": "The Black Fortress", "p14": "Bottom of the World", "p15": "The Wither", "p16": "The Machine", "p17": "Bring It Home"}

// A "major boss" for loot sharing: anything on the lists above, or any creature with 150+ max
// health (so every boss from every mod counts, the Wither and Ender Dragon included), as long as
// it isn't a player or someone's tamed pet.
const BIG_HP = 150
// Bosses that fight in several bodies. Every form counts as the same route boss, and the eye or piece
// comes when the last form still standing nearby dies (whichever that is).
//   Sir Pumpkinhead: mounted, on foot (with his Felsteed), then a body and a head that fight separately.
const FT_AABB = Java.loadClass('net.minecraft.world.phys.AABB')
const ROUTE_GROUPS = [
  { re: /^born_in_chaos_v1:(?!lord)[a-z_]*(pumpkinhead|headless)[a-z_]*$/, key: 'born_in_chaos_v1:sir_pumpkinhead' }
]
function routeGroup(type) {
  for (let i = 0; i < ROUTE_GROUPS.length; i++) if (ROUTE_GROUPS[i].re.test(type)) return ROUTE_GROUPS[i]
  return null
}
function routeInfo(type) {
  if (ROUTE[type]) return ROUTE[type]
  let g = routeGroup(type)
  return g ? ROUTE[g.key] : null
}
function otherFormsAlive(boss, group) {
  let me = String(boss.uuid)
  let left = 0
  boss.level.getEntitiesWithin(new FT_AABB(boss.x - 64, boss.y - 32, boss.z - 64, boss.x + 64, boss.y + 32, boss.z + 64)).forEach(e => {
    if (String(e.uuid) === me) return
    if (!group.re.test(String(e.type))) return
    try { if (e.isLiving() && e.isAlive()) left++ } catch (err) {}
  })
  return left
}

function isMajor(boss) {
  let type = String(boss.type)
  if (routeInfo(type) || OTHER_BOSSES.indexOf(type) >= 0) return true
  try { if (boss.isPlayer()) return false } catch (e) {}
  try { if (boss.isTame && boss.isTame()) return false } catch (e) {}
  return boss.maxHealth >= BIG_HP
}
global.fairytaleIsMajor = isMajor
global.fairytaleRouteGroup = type => routeGroup(String(type))

// ---- who fought the boss
// Anyone who took part gets a share of the loot, the eye or crown piece, and the page:
//   swung at it or shot it (even if it blocked: startup_scripts/fighters/boss_fights.js),
//   did it damage, or got hit by it ... and is still within FIGHT_RANGE when it dies;
//   or simply stood within NEAR_RANGE when it died.
const FIGHT_RANGE = 128
const NEAR_RANGE = 32
function markFighter(boss, player, amount) {
  if (!boss || !player || !boss.isLiving || !boss.isLiving()) return
  if (!isMajor(boss)) return
  let pd = boss.persistentData
  let hits = pd.getCompound('fairytale_hits')
  let uuid = player.getStringUuid()
  hits.putFloat(uuid, hits.getFloat(uuid) + Math.max(amount || 0, 0.01))
  pd.put('fairytale_hits', hits)
}
global.fairytaleMarkFighter = (boss, player) => { try { markFighter(boss, player, 0) } catch (e) {} }

function playerFrom(source) {
  let player = source.player
  if (!player) {
    let actual = source.actual
    if (actual && actual.owner && actual.owner.isPlayer && actual.owner.isPlayer()) player = actual.owner
  }
  return player && player.isPlayer() ? player : null
}

EntityEvents.hurt(event => {
  let hurt = event.entity
  // a player hit by a boss (or by something the boss fired) is in the fight
  if (hurt.isPlayer()) {
    let attacker = event.source.actual
    if (attacker && attacker.isLiving && attacker.isLiving() && !attacker.isPlayer()) markFighter(attacker, hurt, 0)
    return
  }
  if (!isMajor(hurt)) return
  let player = playerFrom(event.source)
  if (player) markFighter(hurt, player, Math.min(event.damage, hurt.health))
})

function fighters(boss) {
  let hits = boss.persistentData.getCompound('fairytale_hits')
  let dim = String(boss.level.dimension)
  let out = []
  boss.server.players.forEach(p => {
    if (String(p.level.dimension) !== dim) return
    let d = p.distanceToEntity(boss)
    if ((hits.contains(p.getStringUuid()) && d <= FIGHT_RANGE) || d <= NEAR_RANGE) out.push(p)
  })
  return out
}

global.fairytaleFighters = boss => fighters(boss)

function hand(player, stack) {
  // KubeJS give(): into the inventory, or dropped at the player's feet if it's full
  player.give(stack)
}

function rewardStack(boss, info) {
  if (info.reward.startsWith('endrem:')) {
    let lore = `{"text":"Taken from ${info.name}","color":"gray","italic":true}`
    return Item.of(info.reward, `{FairytaleBoss:1b,display:{Lore:['${lore}']}}`)
  }
  return Item.of(info.reward)
}

function givePage(server, player, page) {
  let name = player.username
  server.runCommandSilent(`advancement grant ${name} only kubejs:fairytale/root`)
  server.runCommandSilent(`advancement grant ${name} only kubejs:fairytale/${page}`)
  // the title card and tune only the first time this player gets this page
  let pd = player.persistentData
  let got = pd.getCompound('fairytale_pages')
  if (got.getBoolean(page)) return
  got.putBoolean(page, true)
  pd.put('fairytale_pages', got)
  try { global.fairytalePage(player, PAGE_TITLES[page] || 'A Torn Page') } catch (e) { console.error(`[Fairytale] page fanfare failed: ${e}`) }
}

// ---- pages, eyes and Crown pieces
EntityEvents.death(event => {
  let boss = event.entity
  if (boss.maxHealth >= 100) console.info(`[Fairytale] big death: ${boss.type} (killer: ${event.source.player ? event.source.player.username : 'none'})`)
  let info = routeInfo(String(boss.type))
  if (!info) return
  let group = routeGroup(String(boss.type))
  // forms that fight in several bodies: check a second later, once the next form (if any) has appeared
  let finish = () => {
    let server = boss.server
    let fought = fighters(boss)
    if (fought.length === 0 && event.source.player) fought.push(event.source.player)

    console.info(`[Fairytale] ${boss.type} died, fighters: ${fought.length}`)

    // The Ender Dragon drops no items: on the first kill its egg appears on the portal. With two
    // or more fighters, each of them also gets a Dragon Egg of their own.
    if (String(boss.type) === 'minecraft:ender_dragon' && fought.length >= 2) {
      try {
        let fight = boss.level.getDragonFight()
        if (fight && !fight.hasPreviouslyKilledDragon()) {
          fought.forEach(p => hand(p, Item.of('minecraft:dragon_egg')))
          console.info(`[Fairytale] first dragon kill: a Dragon Egg for each of ${fought.length} fighters`)
        }
      } catch (e) { console.error(`[Fairytale] dragon egg share failed: ${e}`) }
    }
    // never the same boss's reward twice within two minutes (two last forms dying at once)
    // (wall-clock milliseconds: Level.getGameTime() isn't reachable from KubeJS scripts)
    let now = Date.now()
    fought.forEach(p => {
      let last = p.persistentData.getCompound('fairytale_rewarded')
      if (last.contains(info.page) && now - Number(last.getDouble(info.page)) < 120000) return
      last.putDouble(info.page, now)
      p.persistentData.put('fairytale_rewarded', last)
      try { hand(p, rewardStack(boss, info)) } catch (e) { console.error(`[Fairytale] reward failed for ${p.username}: ${e}`) }
    })

    let told = {}
    let tell = p => {
      if (told[p.username]) return
      told[p.username] = true
      givePage(server, p, info.page)
    }
    try {
      fought.forEach(tell)
      server.players.forEach(p => {
        if (String(p.level.dimension) === String(boss.level.dimension) && p.distanceToEntity(boss) <= PAGE_RANGE) tell(p)
      })
    } catch (e) { console.error(`[Fairytale] page unlock failed: ${e}`) }
  }
  if (!group) { finish(); return }
  boss.server.scheduleInTicks(20, () => {
    let left = otherFormsAlive(boss, group)
    if (left) { console.info(`[Fairytale] ${boss.type} fell, ${left} more of ${info.name} still fighting`); return }
    finish()
  })
})

// ---- shared loot
// How one dropped stack is handed out between n fighters (start = who gets the odd extras first).
// Gear and other unstackable items: everyone gets a copy. Stackable items: split evenly, and
// every fighter gets at least one (so a single Nether Star goes to everyone).
function splitPlan(count, stackable, n, start) {
  let out = []
  for (let i = 0; i < n; i++) out.push(0)
  if (!stackable) { for (let i = 0; i < n; i++) out[i] = count; return out }
  let each = Math.floor(count / n)
  let extra = count % n
  for (let i = 0; i < n; i++) {
    let k = (start + i) % n
    let c = each
    if (extra > 0) { c++; extra-- }
    out[k] = Math.max(1, c)
  }
  return out
}
global.fairytaleSplitPlan = splitPlan

// Gear and other one-off items: the first fighter (picked at random) gets the item as it dropped;
// everyone else gets the same item with their own roll: new enchantments of the same strength, new
// Apotheosis affixes at the same rarity, and no Quality Equipment quality, so it rolls its own.
// Maps, keys, books and other items whose data IS the item are copied exactly.
const FT_EnchantmentHelper = Java.loadClass('net.minecraft.world.item.enchantment.EnchantmentHelper')
const FT_RandomSource = Java.loadClass('net.minecraft.util.RandomSource')
const FT_Apoth = (() => {
  try {
    return { helper: Java.loadClass('dev.shadowsoffire.apotheosis.adventure.affix.AffixHelper'),
             loot: Java.loadClass('dev.shadowsoffire.apotheosis.adventure.loot.LootController') }
  } catch (e) { return null }
})()

function ownRoll(stack) {
  let c = stack.copy()
  let id = String(c.id)
  if (id.startsWith('relics:')) return Item.of(id)          // relics roll their stats when first carried
  if (!c.isDamageableItem() || id.startsWith('tconstruct:')) return c
  let tag = c.getNbt()   // KubeJS calls the vanilla getTag() getNbt()
  if (!tag) return c
  let rand = FT_RandomSource.create()
  let rarity = null
  try {
    if (FT_Apoth && FT_Apoth.helper.hasAffixes(c)) {
      let h = FT_Apoth.helper.getRarity(c)
      if (h.isBound()) rarity = h.get()
    }
  } catch (e) {}
  let power = 0
  try {
    let list = tag.getList('Enchantments', 10)
    for (let i = 0; i < list.size(); i++) power += list.getCompound(i).getShort('lvl')
  } catch (e) {}
  let keys = []
  let it = tag.getAllKeys().iterator()
  while (it.hasNext()) keys.push(String(it.next()))
  let quality = false
  keys.forEach(k => {
    if (/quality/i.test(k)) { quality = true; tag.remove(k) }
  })
  if (quality) tag.remove('AttributeModifiers')
  ;['Enchantments', 'RepairCost', 'affix_data'].forEach(k => tag.remove(k))
  if (power > 0) {
    try { c = FT_EnchantmentHelper.enchantItem(rand, c, Math.min(30, 5 + power * 5), true) } catch (e) {}
  }
  if (rarity) {
    try { c = FT_Apoth.loot.createLootItem(c, rarity, rand) } catch (e) {}
  }
  return c
}

const FT_SHARED = {}   // bosses whose drops were shared out, by uuid
const FT_ROLLED = {}   // bosses whose loot was rolled for each fighter instead, by uuid

EntityEvents.drops(event => {
  let boss = event.entity
  if (!isMajor(boss)) return
  let fought = fighters(boss)
  if (fought.length < 2) return   // one fighter: normal drops
  if (FT_ROLLED[String(boss.uuid)]) return   // everyone else already got their own roll: these are the killer's
  let drops = event.drops
  let any = false
  drops.forEach(itemEntity => {
    let stack = itemEntity.item
    if (stack.isEmpty()) return
    any = true
    let stackable = stack.maxStackSize > 1
    let start = Math.floor(Math.random() * fought.length)
    let plan = splitPlan(stack.count, stackable, fought.length, start)
    for (let i = 0; i < fought.length; i++) {
      let c = plan[i]
      if (c <= 0) continue
      if (stackable || i === start) hand(fought[i], stack.copyWithCount(c))
      else hand(fought[i], ownRoll(stack))
    }
  })
  if (!any) return
  FT_SHARED[String(boss.uuid)] = true
  fought.forEach(p => p.setStatusMessage(Text.of('The spoils were shared out between everyone who fought.').gray()))
  event.cancel()
})

// ---- bosses that leave their loot in a chest (Twilight Forest and others)
// A chest can only be emptied once. Everyone who fought, except whoever landed the final blow,
// gets their own roll of the same loot straight into their inventory; the chest is the killer's.
const FT_LootParams = Java.loadClass('net.minecraft.world.level.storage.loot.LootParams$Builder')
const FT_LCP = Java.loadClass('net.minecraft.world.level.storage.loot.parameters.LootContextParams')
const FT_LCPS = Java.loadClass('net.minecraft.world.level.storage.loot.parameters.LootContextParamSets')
const FT_ResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
const FT_BlockPos = Java.loadClass('net.minecraft.core.BlockPos')
const FT_CHEST_RADIUS = 12

function rollTable(server, tableId, params) {
  let out = []
  try {
    let table = server.lootData.getLootTable(tableId)
    table.getRandomItems(params).forEach(s => { if (!s.isEmpty()) out.push(s) })
  } catch (e) { console.error(`[Fairytale] couldn't roll ${tableId}: ${e}`) }
  return out
}
function entityRoll(boss, source, player) {
  let b = new FT_LootParams(boss.level)
    .withParameter(FT_LCP.THIS_ENTITY, boss)
    .withParameter(FT_LCP.ORIGIN, boss.position())
    .withParameter(FT_LCP.DAMAGE_SOURCE, source)
    .withOptionalParameter(FT_LCP.KILLER_ENTITY, player)
    .withOptionalParameter(FT_LCP.DIRECT_KILLER_ENTITY, player)
    .withParameter(FT_LCP.LAST_DAMAGE_PLAYER, player)
    .withLuck(player.getLuck())
  return rollTable(boss.server, boss.getLootTable(), b.create(FT_LCPS.ENTITY))
}
function chestRoll(level, pos, tableId, player) {
  let b = new FT_LootParams(level)
    .withParameter(FT_LCP.ORIGIN, pos.getCenter())
    .withOptionalParameter(FT_LCP.THIS_ENTITY, player)
    .withLuck(player.getLuck())
  return rollTable(level.server, new FT_ResourceLocation(tableId), b.create(FT_LCPS.CHEST))
}
function lootChestsNear(level, x, y, z) {
  let tables = []
  for (let dx = -FT_CHEST_RADIUS; dx <= FT_CHEST_RADIUS; dx++)
    for (let dy = -6; dy <= 6; dy++)
      for (let dz = -FT_CHEST_RADIUS; dz <= FT_CHEST_RADIUS; dz++) {
        let pos = new FT_BlockPos(x + dx, y + dy, z + dz)
        let be = level.getBlockEntity(pos)
        if (!be) continue
        let nbt = null
        try { nbt = be.saveWithoutMetadata() } catch (e) {}
        if (nbt && nbt.contains('LootTable')) tables.push({ pos: pos, table: String(nbt.getString('LootTable')) })
      }
  return tables
}

EntityEvents.death(event => {
  let boss = event.entity
  if (!isMajor(boss)) return
  let fought = fighters(boss)
  if (fought.length < 2) return
  let killer = event.source.player
  let source = event.source
  let level = boss.level
  let x = Math.floor(boss.x), y = Math.floor(boss.y), z = Math.floor(boss.z)
  let key = String(boss.uuid)
  let name = boss.displayName.string
  // only chests that appear after the death count (not the dungeon's own chests)
  let before = {}
  lootChestsNear(level, x, y, z).forEach(c => { before[String(c.pos)] = true })
  // Many bosses play a death animation and only drop their loot (or place their chest) at the end of it,
  // so wait until the body is gone, then a little longer. If the drops were shared normally, stop here.
  let server = boss.server
  let waited = 0
  let check = () => {
    waited += 20
    if (FT_SHARED[key]) { delete FT_SHARED[key]; return }
    if (!boss.isRemoved() && waited < 600) { server.scheduleInTicks(20, check); return }
    server.scheduleInTicks(40, () => {
      if (FT_SHARED[key]) { delete FT_SHARED[key]; return }
      FT_ROLLED[key] = true
      let chests = lootChestsNear(level, x, y, z).filter(c => !before[String(c.pos)])
      let rolled = 0
      fought.forEach((p, i) => {
        if (killer ? String(p.username) === String(killer.username) : i === 0) return
        let items = chests.length
          ? [].concat.apply([], chests.map(c => chestRoll(level, c.pos, c.table, p)))
          : entityRoll(boss, source, p)
        if (!items.length) return
        items.forEach(s => hand(p, s))
        rolled++
        p.setStatusMessage(Text.of(`Your own share of ${name}'s loot is in your pack. The chest is for whoever struck last.`).gray())
      })
      if (rolled) console.info(`[Fairytale] ${boss.type}: rolled its loot for ${rolled} more fighter(s)`)
    })
  }
  server.scheduleInTicks(20, check)
})

// ---- the first night
// Two steps: the player has to be here for some part of the night (or be asleep in a bed),
// then the page comes the next morning. Sleeping straight through the night counts.
PlayerEvents.tick(event => {
  let player = event.player
  if (player.age % 20 !== 0) return
  let pd = player.persistentData
  if (pd.getBoolean('fairytale_night_page')) return
  let time = Number(player.level.getDayTime()) % 24000
  if (!pd.getBoolean('fairytale_saw_night')) {
    if ((time >= 13000 && time < 23500) || player.isSleeping()) pd.putBoolean('fairytale_saw_night', true)
    return
  }
  if (time < 12000 && !player.isSleeping()) {
    pd.putBoolean('fairytale_night_page', true)
    givePage(player.server, player, 'night')
    console.info(`[Fairytale] night page for ${player.username}`)
  }
})

PlayerEvents.loggedIn(event => {
  event.server.runCommandSilent(`advancement grant ${event.player.username} only kubejs:fairytale/root`)
})

// ---- eyes only come from bosses
const EYE = /^endrem:[a-z_]+_eye$/
PlayerEvents.inventoryChanged(event => {
  let player = event.player
  if (player.isCreative()) return
  let stack = event.item
  if (!EYE.test(stack.id)) return
  let real = false
  try { real = String(stack.nbt).indexOf('FairytaleBoss') >= 0 } catch (e) { real = true }
  if (real) return
  // changing the event's stack doesn't stick; clear the slots themselves on the next tick
  player.server.scheduleInTicks(1, () => {
    let inv = player.inventory
    let removed = 0
    for (let i = 0; i < inv.getContainerSize(); i++) {
      let s = inv.getItem(i)
      if (s.isEmpty() || !EYE.test(String(s.id))) continue
      let boss = false
      try { boss = String(s.nbt).indexOf('FairytaleBoss') >= 0 } catch (e) { boss = true }
      if (boss) continue
      removed += s.count
      inv.setItem(i, Item.empty)
    }
    if (!removed) return
    console.info(`[Fairytale] removed ${removed} non-boss eye(s) from ${player.username}`)
    player.setStatusMessage(Text.of('The eye crumbles to dust. Only the ones taken from bosses are real.').gray())
  })
})

ServerEvents.recipes(event => {
  event.remove({ output: EYE })
  event.shapeless(Item.of('kubejs:kings_crown', '{Unbreakable:1b}'), [
    'kubejs:crown_band', 'kubejs:crown_jewel', 'kubejs:crown_crest', 'kubejs:crown_setting', 'kubejs:dragons_heart'
  ]).id('kubejs:kings_crown')
})
