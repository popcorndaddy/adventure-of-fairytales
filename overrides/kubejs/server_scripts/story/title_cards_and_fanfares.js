// Title cards, little tunes and sparkles for the big moments:
//   global.fairytaleWelcome(player)          - first time in the world
//   global.fairytalePage(player, pageTitle)  - a torn page returns to the Adventure Book
// Sounds and particles are played at the player (not at the world origin).

// note block pitch for a semitone step (0 = F#3 ... 24 = F#5)
const FT_NOTE = n => Math.pow(2, (n - 12) / 12).toFixed(3)

function ftAt(player, cmd) {
  player.server.runCommandSilent(`execute as ${player.username} at @s run ${cmd}`)
}
function ftSound(player, sound, volume, pitch) {
  ftAt(player, `playsound ${sound} master @s ~ ~ ~ ${volume} ${pitch} 1`)
}
// tune: [[delayTicks, sound, volume, pitch], ...]
function ftTune(player, tune) {
  let server = player.server
  let name = player.username
  tune.forEach(n => {
    server.scheduleInTicks(n[0], () => {
      let p = server.getPlayer(name)
      if (p) ftSound(p, n[1], n[2], n[3])
    })
  })
}
function ftLater(player, ticks, fn) {
  let server = player.server
  let name = player.username
  server.scheduleInTicks(ticks, () => {
    let p = server.getPlayer(name)
    if (p) fn(p)
  })
}
function ftTitle(player, fadeIn, stay, fadeOut, title, subtitle) {
  let n = player.username
  let s = player.server
  s.runCommandSilent(`title ${n} times ${fadeIn} ${stay} ${fadeOut}`)
  s.runCommandSilent(`title ${n} subtitle ${JSON.stringify(subtitle)}`)
  s.runCommandSilent(`title ${n} title ${JSON.stringify(title)}`)
}
function ftActionbar(player, text) {
  player.server.runCommandSilent(`title ${player.username} actionbar ${JSON.stringify(text)}`)
}

// ---- welcome: the pack's own "Dawn of Adventure" sound (3.85 s). The title fades in with the
// build-up (fully in at the big hit, 2.4 s), holds while it rings, and fades out as the sound dies away.
const FT_WELCOME_TUNE = [[0, 'kubejs:title_dawn_of_adventure', 1.0, 1.0]]
global.fairytaleWelcome = player => {
  ftTune(player, FT_WELCOME_TUNE)
  // titles draw at 4x: kept under 120 GUI px so they fit a 1080p screen at auto GUI scale
  ftTitle(player, 46, 18, 34,
    [{ text: 'Welcome to ', color: '#E8C77A' }, { text: 'Fairytale', color: '#FFD978', bold: true }],
    [{ text: '✦ ', color: '#B57BE8' }, { text: 'an old book, a lost road, a crown', color: '#D9C9F0', italic: true },
     { text: ' ✦', color: '#B57BE8' }])
  // during the build-up: a few soft white motes rising around you
  ftAt(player, 'particle minecraft:end_rod ~ ~0.6 ~ 1.4 0.4 1.4 0.01 12 force @s')
  ftLater(player, 23, p => ftAt(p, 'particle minecraft:end_rod ~ ~0.6 ~ 1.4 0.4 1.4 0.01 16 force @s'))
  ftLater(player, 46, p => {
    // on the big hit: a purple and gold burst
    ftAt(p, 'particle minecraft:dragon_breath ~ ~1.2 ~ 1.2 0.7 1.2 0.03 70 force @s')
    ftAt(p, 'particle minecraft:wax_on ~ ~1.4 ~ 1.4 0.9 1.4 1 45 force @s')
    ftAt(p, 'particle minecraft:firework ~ ~1.8 ~ 1.0 0.6 1.0 0.12 70 force @s')
    ftAt(p, 'particle minecraft:end_rod ~ ~1.2 ~ 0.9 0.9 0.9 0.04 30 force @s')
  })
  ftLater(player, 100, p => ftActionbar(p, [{ text: 'Your ', color: 'gray' }, { text: 'Adventure Book', color: '#C062F0' },
    { text: ' is in your inventory. Start with the first page.', color: 'gray' }]))
}

// ---- a recovered page: the pack's own "Secret Found" sound (1.5 s). The title fades in with it
// (fully in at its peak, 0.4 s), holds while it rings, and fades out with its tail.
// The page's name goes in the subtitle, which has twice the room of the title.
const FT_PAGE_TUNE = [[0, 'kubejs:letter_secret_found', 1.0, 1.0]]
global.fairytalePage = (player, pageTitle) => {
  ftTune(player, FT_PAGE_TUNE)
  ftTitle(player, 8, 20, 28,
    { text: 'Page Recovered', color: '#F2D58A', bold: true },
    [{ text: '✦ ', color: '#9B5FD0' }, { text: pageTitle, color: '#E9DDF7' }, { text: ' ✦', color: '#9B5FD0' }])
  ftAt(player, 'particle minecraft:enchant ~ ~1.2 ~ 1.5 1.2 1.5 1.5 160 force @s')
  ftLater(player, 8, p => {
    ftAt(p, 'particle minecraft:end_rod ~ ~1.4 ~ 0.6 0.8 0.6 0.04 30 force @s')
    ftAt(p, 'particle minecraft:wax_on ~ ~1.4 ~ 0.8 0.6 0.8 1 20 force @s')
    ftAt(p, 'particle minecraft:soul_fire_flame ~ ~0.2 ~ 0.9 0.1 0.9 0.01 25 force @s')
  })
  ftLater(player, 40, p => ftActionbar(p, { text: 'A torn page has returned to your Adventure Book', color: '#D9C9F0', italic: true }))
  ftLater(player, 110, p => ftActionbar(p, [{ text: 'Open your ', color: 'gray' }, { text: 'Adventure Book', color: '#C062F0' },
    { text: ': the new page is marked in Apollo\'s Notes.', color: 'gray' }]))
}
