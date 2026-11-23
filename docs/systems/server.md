# Server and multiplayer
Search keys: dedicated server, timeout, world host, connectivity, port 25565

- Dedicated server: `E:\AdventuresOfFairytale-Server` (Forge 1.20.1-47.4.28, Java 17, 10 GB).
  Start with `start-server.bat` (auto-restarts). 45 client-only mods sit in `client-only-mods/`.
- Bracket names (`[Forge]`) break PowerShell -Path copies: always use -LiteralPath.
- Client timeout fixes (instance): Connectivity `disconnectTimeout` 120, `logintimeout` 120,
  Packet Fixer timeout 120, JVM `-Dfml.readTimeout=180`, Forge `versionCheck=false`.
- Friends join with the same pack version; the server owner forwards TCP 25565 or uses a tunnel.

See also: docs/systems/modpack.md
