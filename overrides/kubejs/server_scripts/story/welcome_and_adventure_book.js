// Adventures of Fairytale - welcome title + Adventure Book
// Every player gets the book the moment they first join a world, and the title once they're
// actually in-game (see below), once per player per world.
// /adventurebook gives a new copy, /fairytalewelcome replays the title.

console.info('[Fairytale] welcome script loaded')

const ADVENTURE_BOOK = () => Item.of('patchouli:guide_book', '{"patchouli:book":"patchouli:adventure_book"}')

function giveAdventureBook(player) {
  try {
    player.give(ADVENTURE_BOOK())
  } catch (e) {
    player.server.runCommandSilent(`give ${player.username} patchouli:guide_book{"patchouli:book":"patchouli:adventure_book"}`)
  }
}

function showWelcome(player) {
  // the title card, tune and sparkles live in server_scripts/story/title_cards_and_fanfares.js
  global.fairytaleWelcome(player)
}

function hasAdventureBook(player) {
  let inv = player.inventory
  for (let i = 0; i < inv.getContainerSize(); i++) {
    let s = inv.getItem(i)
    if (String(s.id) === 'patchouli:guide_book' && String(s.nbt).indexOf('adventure_book') >= 0) return true
  }
  return false
}

// Every player gets the book and the intro once, on their first time in this world.
// The intro waits for that player's own game to say it's past the loading screen (client_scripts/
// welcome/ready_signal.js), so a friend joining over the internet doesn't miss it behind
// "Loading terrain". If that signal never comes, it plays after two minutes anyway.
// (The flags were renamed when this changed, so anyone who missed the old intro gets it now.)
function giveBookOnce(player) {
  let data = player.persistentData
  if (data.getBoolean('fairytale_book_v2')) return
  data.putBoolean('fairytale_book_v2', true)
  if (hasAdventureBook(player)) return
  giveAdventureBook(player)
  console.info(`[Fairytale] gave Adventure Book to ${player.username}`)
}
function welcomeOnce(player, why) {
  let data = player.persistentData
  if (data.getBoolean('fairytale_welcome_v2')) return
  data.putBoolean('fairytale_welcome_v2', true)
  giveBookOnce(player)
  showWelcome(player)
  console.info(`[Fairytale] showed welcome title to ${player.username} (${why})`)
}

// The Adventure Book is the only thing a new player starts with. Other mods' guide books are switched off in
// their configs (Tinkers, Ars Nouveau, Alex's Mobs, Apotheosis, Ice and Fire Delight); this catches any mod
// that hands one out anyway (Tide's Fishing Journal, other Patchouli books). Only during a player's first
// half-minute in the world, so nothing they pick up or craft later is touched. All of these can be crafted.
const FT_STARTER_BOOKS = ['tconstruct:materials_and_you', 'ars_nouveau:worn_notebook', 'alexsmobs:animal_dictionary',
  'tide:fishing_journal', 'apotheosis:book', 'botania:lexicon', 'productivebees:guide_book', 'hexerei:book_of_shadows',
  'irons_spellbooks:patchouli_book', 'iceandfire:bestiary', 'ftbquests:book']
function removeStarterBooks(player) {
  let inv = player.inventory
  let removed = []
  for (let i = 0; i < inv.getContainerSize(); i++) {
    let s = inv.getItem(i)
    if (s.isEmpty()) continue
    let id = String(s.id)
    let extra = FT_STARTER_BOOKS.indexOf(id) >= 0 ||
      (id === 'patchouli:guide_book' && String(s.nbt).indexOf('adventure_book') < 0)
    if (extra) { removed.push(id); inv.setItem(i, Item.empty) }
  }
  if (removed.length) console.info(`[Fairytale] removed starting books from ${player.username}: ${removed.join(', ')}`)
}
function sweepStartersOnce(player) {
  let data = player.persistentData
  if (data.getBoolean('fairytale_starters_v1')) return
  data.putBoolean('fairytale_starters_v1', true)
  if (data.getBoolean('fairytale_book_v2')) return   // joined before this rule existed: leave their things alone
  let name = player.username
  ;[1, 40, 200, 600].forEach(t => player.server.scheduleInTicks(t, () => {
    let p = player.server.getPlayer(name)
    if (p) removeStarterBooks(p)
  }))
}

PlayerEvents.loggedIn(event => {
  sweepStartersOnce(event.player)
  giveBookOnce(event.player)
  event.player.persistentData.putInt('fairytale_title_wait', 0)
})

NetworkEvents.dataReceived('fairytale_ready', event => {
  let player = event.player
  // a moment after the world appears, so the title isn't lost in the first frames
  player.server.scheduleInTicks(40, () => {
    let p = player.server.getPlayer(player.username)
    if (p) welcomeOnce(p, 'client ready')
  })
})

PlayerEvents.tick(event => {
  let player = event.player
  let data = player.persistentData
  if (data.getBoolean('fairytale_welcome_v2')) return
  let waited = data.getInt('fairytale_title_wait') + 1
  data.putInt('fairytale_title_wait', waited)
  if (waited >= 2400) welcomeOnce(player, 'no ready signal after two minutes')
})

ServerEvents.commandRegistry(event => {
  let { commands: Commands } = event
  event.register(Commands.literal('adventurebook').executes(ctx => {
    giveAdventureBook(ctx.source.playerOrException)
    return 1
  }))
  event.register(Commands.literal('fairytalewelcome').executes(ctx => {
    showWelcome(ctx.source.playerOrException)
    return 1
  }))
})

ServerEvents.recipes(event => {
  event.shapeless(ADVENTURE_BOOK(), ['minecraft:book', 'minecraft:compass']).id('kubejs:adventure_book')
})
