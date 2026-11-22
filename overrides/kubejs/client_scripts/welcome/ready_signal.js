// Tells the server when this player can actually see the world: in a world, no loading or other
// screen open, for two seconds. The server plays the first-join intro on this signal
// (server_scripts/story/welcome_and_adventure_book.js), so nobody misses it behind a loading screen.
// Sent once per world joined.
const FT_READY = { sent: false, clear: 0 }

ClientEvents.tick(event => {
  let player = Client.player
  if (!player || !Client.level) { FT_READY.sent = false; FT_READY.clear = 0; return }
  if (FT_READY.sent) return
  if (Client.screen != null) { FT_READY.clear = 0; return }
  FT_READY.clear++
  if (FT_READY.clear < 40) return
  FT_READY.sent = true
  player.sendData('fairytale_ready')
})

ClientEvents.loggedOut(event => { FT_READY.sent = false; FT_READY.clear = 0 })
