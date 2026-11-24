# Tooling (Rootstock)
Search keys: hooks, standup, checkpoint, run_all, ledgers

- Scripts: `tools/*.py` (Rootstock reference tools); hooks: `tools/hooks/` wired in
  `.claude/settings.json` (Standard level, commands use `py -3`).
- The hooks: session_start (standup digest), prompt_gauge, stop_tick, pre_compact, session_end
  (AUTO-CHECKPOINT on /clear: commits and pushes unbanked work - kept on by the CEO 2026-11-22),
  bash_guard, preserve_guard (refuses deletes without a grant), diet_guard, brief_guard,
  delegation_auditor.
- Ledgers and day files: `docs/history/`.

See also: HOOKS_METHOD.md, REPORTING_METHOD.md
