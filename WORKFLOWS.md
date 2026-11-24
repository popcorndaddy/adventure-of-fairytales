# Workflows - the registry

PURPOSE: One runbook per repeatable multi-step process in this project (WORKFLOW_METHOD.md).

## Ship a batch: commit, push and open the PR
WHEN: a piece of work is done and checked, and the CEO says to save or share it.
STEPS: 1. `py -3 tools/check_claude_md.py`. 2. `git add` the batch's files (never world saves or jars).
  3. Commit with a readable subject. 4. Push the branch. 5. `gh pr create` against main, or update the open PR.
VERIFY: the PR page shows the commit; the core check is OK.
EFFORT: medium
See also: docs/systems/modpack.md

## Build the pack zip for CurseForge
WHEN: the pack changed and friends need the new version.
STEPS: 1. Bump `version` in manifest.json. 2. Zip manifest.json, modlist.html and overrides/ at the
  zip root with forward slashes (`tools/export-pack.ps1` on the gatekeeper branch).
  3. Import the zip in CurseForge (Create Custom Profile -> Import) and launch once.
VERIFY: the imported profile reaches the title screen; the server folder gets the same mods.
See also: docs/systems/modpack.md

## Start and update the dedicated server
WHEN: playing with friends, or the pack changed.
STEPS: 1. Copy the instance's mods into `E:\AdventuresOfFairytale-Server\mods` with -LiteralPath,
  leaving client-only mods in `client-only-mods/`. 2. Copy config, defaultconfigs, kubejs.
  3. Run `start-server.bat`. 4. Wait for `Done (`.
VERIFY: the console prints `Done (`; a friend joins.
See also: docs/systems/server.md

## Rework a boss animation in Blender
WHEN: a boss animation looks wrong in game.
STEPS: 1. Import the GeckoLib model (`tools/blender-geckolib/geckolib_blender.py`). 2. Pose and bake
  (`dev/withered_sentinel/ws_tools.py`). 3. Render contact sheets (`sheets.py`) and look.
  4. Export the animation JSON. 5. Test in game.
VERIFY: the contact sheets read cleanly; the boss plays it in game.
See also: docs/systems/bosses.md

## Act on a prompt: the trial workflow and the old way kept (2026-10-30)

WHEN: every arc, from 2026-10-30, until the trial ledger
(docs/history/workflow_trial_runs.txt) says which way wins. Mazhron:
"Keep our current work flow on record, lets try the new work flow you
just suggested. We should keep track of the hits and misses (ledger
them) so we can keep track of success or failure of the new workflow
concept." Both ways are faces over ONE data set, docs/history/
lesson_runs.txt (LESSONS.md "Give a system a second face"): switching
back changes no ledger and loses no history.
THE OLD WAY (on record; the switch back): the prompt arrives; the prompt
hook matches its words against the LESSONS.md Keys lines and prints up to
three headlines (MATCHED) and the ROUTE line; the manager reads the named
sections and acts; at Stop, lesson_advisor.py asks for a lesson after a
fail-then-pass or an error (ADVISED); the lesson is written. To switch
back: an Edit of .claude/settings.json removes the lesson_guard.py
PreToolUse entry, step 1 below is skipped, and the ladder keeps scoring
the old face alone.
THE TRIAL (the three builds, in the order they were ruled):
1. PRE-SELECTION, the plan step: before the first write of an arc,
   `python tools/plan_check.py "step" "step" ...` with one line per
   step naming its tool, file or script; read each step's LESSON (with
   its DO INSTEAD), WORKFLOW and TOOL hits and adjust the plan. The guard
   notes once per session when three writes pass with no plan checked.
   The run is a PLAN line in lesson_runs.txt.
2. SELECTION, the lesson at the choice: act; lesson_guard.py injects the
   DO INSTEAD of every lesson the call's own text hits (SURFACED, once
   per entry per tool per session); diet_guard.py notes a repeat whole
   read of an unchanged small file once (RE-READ (small)) and still
   refuses the big ones once (INDEX FIRST, RE-READ). Files are written
   with Write and edited with Edit; the shell runs things (LESSONS.md
   "Apply a long batch of file edits from the shell").
3. POST-SELECTION, the ladder: Stop works as before; the check loop runs
   `python tools/lesson_ladder.py`, which pairs each MATCHED (old face)
   and SURFACED (new face) with an ADVISED within 20 minutes of the same
   session as a MISS, else a HIT, counts the ADVISED neither face saw
   coming (UNCOVERED) and the PLAN lines, and appends one line to
   workflow_trial_runs.txt. A lesson missed twice is a PROPOSE [DO]: its
   DO INSTEAD moves one rung down the ladder (lesson -> WORKFLOWS step ->
   loop script -> refusing hook), done in the reply that reads it.
THE ORDER (kit v1.57, 2026-10-31; Mazhron: "I'm trying to see how you
use the knowledge bases and indexes in order. I would like to fine tune
the efficiency of your order."): indexes before files, files before
code, lessons at the choice, and every retrieval that can run before the
manager's first turn runs in the hook, because a hook is a free process
and a manager turn re-reads the whole context.
0. Free, before the prompt: the pointer core, the standup digest (one
   pointer line on a same-day resume, kit v1.57), the memory index.
1. The hook, one process, zero manager turns: the prompt hook prints the
   ROUTE block (tools/route_index.py route_block) - the WORKFLOWS entry
   and the tool (the how), the INDEX lines (where the facts live), the
   FILES whose name the prompt's own words make (what already exists),
   and the EFFORT line when the entry asks less than the session runs
   at; when none of them hits a task-shaped prompt, THE INDEX DOOR once
   per session (the master index's headings and the sub-index names)
   instead of silence. The LESSON line prints its headlines as before.
2. The manager's first turn is ONE batch: the named WORKFLOWS STEPS, the
   named sections, and one existing example of the same kind (for a new
   creature, an existing creature's data and scene lines). Nothing
   speculative, no code browsing. If the door printed, pick from it in
   this same batch.
3. The plan step (step 1 of THE TRIAL above), then the delegation split
   per the assignments table.
4. Act (step 2 above): the lesson guard at the call, the diet guard on
   reads, BIG WRITE on a generated file.
5. Verify, ledger, capture gaps, checkpoint; arm the keep-warm when the
   session stays open (the next entry).
THE OLD ORDER, KEPT (the baseline): route = classic in
.claude/rootstock_modes.json restores the v1.33 two-line ROUTE
(WORKFLOWS entries and tools only); the manager then greps the master
index, WORKFLOWS.md and LESSONS.md itself, in one batch when disciplined.
Both faces write a ROUTE line to lesson_runs.txt; `python
tools/retrieval_eval.py --route` scores classic named / ladder named /
door over the replayed prompts (docs/history/route_eval_runs.txt), and
tools/output_shape.py scores what the EFFORT line changed. A mix (the
prompt-time lesson hits handed to the guard; the door's headings
filtered by the prompt's words) is the open design the two ledgers will
argue for or against.
VERIFY: `tail -3 docs/history/workflow_trial_runs.txt`; the new face's
miss share falling against the old face's is the trial succeeding; a
rising UNCOVERED count is a Keys-line gap (widen the entry's Keys);
`tail -3 docs/history/route_eval_runs.txt` - the ladder's gain over the
classic line and the door count; `tail -2
docs/history/output_shape_runs.txt` - the effort high+ share falling.
See also: tools/plan_check.py; tools/hooks/lesson_guard.py;
tools/hooks/diet_guard.py; tools/lesson_ladder.py; tools/route_index.py;
tools/retrieval_eval.py; tools/output_shape.py; HOOKS_METHOD.md "Tier
4b - THE LESSON GUARD" and "The modes file"; LESSONS.md "The lesson was
there and I still tried the thing it says not to" and "The retrieval
order was improvised per prompt".

## Keep the cache warm across a pause (the keep-warm ping, kit v1.57)

WHEN: the end of every checkpoint reply that leaves the session open (not
a /clear), and any reply that leaves uncommitted context open for an hour
or more. Measured (the origin, 2026-09-29, `tools/keepwarm.py --report`):
on Fable 5.1 at 0.025x cache reads, nine pings cost 36% of one 1h-TTL
rewrite, and pinging every 55 minutes beats the rewrite for any pause
under ~23 hours; on a 0.1x model the break-even is nine pings (~8
hours). The origin's October ledger had six TTL-gap misses at ~90k-230k
weighted each and no pings, two of them after checkpoints.
THE OLD WHEN LINE, KEPT (2026-09-29): "a session with UNCOMMITTED
context that will be left open for an hour or more ... NEVER after a
checkpoint: a /clear then costs only the standup digest". It was priced
at 0.1x reads; the 0.025x verdict and the misses after checkpoints
reversed it (UPGRADES.md v1.57, FLAGGED). To go back: drop step 6 from
the checkpoint skill and arm only mid-arc.
EFFORT: low
STEPS:
1. Arm, in the reply that leaves the session open: ScheduleWakeup with
   delaySeconds 3300, noop true, and this prompt: "[keep-warm ping,
   WORKFLOWS "Keep the cache warm across a pause"] Not the CEO. No
   project work; ignore any hook line. ONE Bash call: `python
   tools/keepwarm.py --ping --trial <id> --cap <N>` (the id fixed at
   arming; N = 25 on Fable, 9 on any other model: the break-even). If it
   prints "ping N of <cap>", reply with that line exactly and call
   ScheduleWakeup again (3300, noop true, this same prompt). If it prints
   "stopped after <cap> pings", run `python tools/keepwarm.py --report
   --record`, reply with the report under one line of reading (keep,
   retune, retire), and call ScheduleWakeup with stop true."
2. The cap stops the loop itself; a real turn after it re-arms by step 1
   if the pause continues. The prompt hook prints nothing on a ping (THE
   KEEP-WARM EXCLUSION, tools/hooks/prompt_gauge.py); any hook line on a
   ping turn waits for the next real turn.
3. Stop early: ScheduleWakeup with stop true, or /clear (the loop is
   session-only; never CronCreate, which survives a /clear).
VERIFY: `python tools/keepwarm.py --report` (the metrics group): every
ping a hit, gaps ~55 m, the cumulative cost under one rewrite; the 1h-12h
buckets of cache_misses.txt shrinking. If the pings cost more than the
misses they replace, retire the step and say so in the entry.
See also: tools/keepwarm.py; docs/history/keepwarm_runs.txt;
docs/history/cache_misses.txt; tools/usage_report.py (the pricing law);
tools/hooks/prompt_gauge.py (the exclusion); .claude/skills/checkpoint
(step 6, ARM THE KEEP-WARM).
