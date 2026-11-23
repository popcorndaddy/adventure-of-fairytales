# SUBAGENTS - the delegation company for Adventures of Fairytale

PURPOSE: This project's org chart, laws, assignments and ledger (SUBAGENT_METHOD.md is the method).

## The org chart
- CEO: the repo owner (popcorndaddy). Decides; is not a programmer.
- MANAGER: the main Claude Code session (Opus). Plans, briefs, verifies, never does bulk reading itself.
- EMPLOYEES: `.claude/agents/explore.md` and `lookup.md` pinned to haiku for searches;
  sonnet for mechanical edits and transcription; opus only for design-heavy work.

## The seven laws
Tags: delegation, process, architecture | Seven cardinal laws: brief, stamp, verify cheap, ledger, escalate, fan-out caps and preservation

1. THE BRIEF IS EVERYTHING. Employees know NOTHING - no chat history, no
   project lore. A brief is a work order: exact files/paths, exact spec,
   exact output format, any needed rules PASTED IN (never "see the docs").
   A vague brief is the manager's error, not the employee's. The brief
   also tells the employee HOW to spend its turns (v1.43): independent
   reads, greps and checks go in one turn, never one per turn, because
   every extra turn re-reads the whole growing context; only a step that
   needs the previous result waits.
   THE SANDBOX IS CHOSEN BY THE WORK (2026-11-03, after Code Mode and
   programmatic tool calling): a trip of mechanical steps - the same
   edit across files, a check per item, a loop over a CLI or an API - is
   a SCRIPT the manager writes and runs once, printing a verdict; it is
   cheaper than any employee and nothing intermediate enters anyone's
   context. An employee is the sandbox when each step needs judgment (an
   understand-this read, a review, a design call). LESSONS.md "The
   one-script trip"; the diet guard's TRIP DIET note at the third call.
2. EVERY EMPLOYEE STAMPS ITS WORK. Every brief ends by requiring:
   "STAMP: model=<model> effort=<low|med|high> est_tokens=<rough>
    task=<3-5 words> confidence=<high|med|low>"
   If the platform meters real usage (e.g. a subagent_tokens figure in the
   tool result), the manager records THAT - self-estimates run wildly low
   (models cannot see their own meter; we measured ~20x under).
3. VERIFY CHEAPLY, IN ORDER: (a) run the project's tests/checks, (b)
   spot-read only the diff or output, (c) full read only if a+b smell wrong.
   A double-check that costs more than the task defeats the purpose.
4. LEDGER EVERY DELEGATION. One appended line: date, who delegated, task
   type, model/effort, metered tokens, outcome OK or CORRECTED + what was
   wrong. Keep a running TALLY per model (tasks / corrected / success %).
5. THE ESCALATION RULE. When a task type's corrections exceed ~25% of its
   last ~10 tasks, promote that task type - stronger model or higher
   effort - with a dated, attributed change line in the assignments table.
   The ledger justifies staffing changes; nobody argues from vibes.
   THE ASSIGNMENT IS THE MANAGER'S (the origin project's owner, 2026-09-29:
   "You are the manager, you make the decision. You can downgrade or
   upgrade any task you see fit on a trial basis. If there are enough
   failures, then it needs to move up again."): the manager moves any task
   type down a tier on trial without asking; the ledger's correction rate
   moves it back up; the only fixed line is the owner's (in the origin
   project the top model is never an employee, to save tokens). A trial is
   ledgered with "trial" in its line so the rate counts it.
6. THE FAN-OUT LAW (added 2026-09-10 after a public catastrophe: a
   manager asked to "check my markdown files for consistency" spawned
   821 sub-agents and burned 50M+ tokens in thirty seconds). Employees
   are spent money. A delegation batch is a handful of parallel
   employees (the origin project's habit: 4), never a burst, never an
   employee that spawns employees (fan-out is one level deep and the
   manager's decision), and any bulk-orchestration tool only when the
   CEO asks for it. A task that seems to need dozens is a DESIGN problem
   - split it, script it, or ask the CEO - never a bigger fan-out. THE
   HARNESS BACKS IT, CATASTROPHE-ONLY (HOOKS_METHOD.md Tier 2b, the
   fan-out guard; the origin CEO loosened it from a strict first cut the
   same day: "I just wanted to prevent complete runaway agents and
   gigantic token spend"): it refuses only the runaway shapes - a burst
   of spawns inside a minute, a flood inside ten, or token velocity no
   real work produces (a self-clearing cooldown) - and otherwise only
   warns. No unlock commands; nothing fires on real work. A refusal from
   the guard is the CEO's standing decision: the manager stops, reports
   what it was fanning out and why, and never resumes the same loop.
   The guard's numbers are the CEO's to tune, through the /runaway skill
   (shows every limit current vs default, writes the CEO's changes to a
   committed .claude/fanout_limits.json over the script's defaults);
   the manager never raises one on its own.
7. THE PRESERVATION LAW (added 2026-09-10 after public reports of an
   agent whose script deleted a person's files and another that wiped a
   machine). Nobody in the company deletes: not the manager, not an
   employee, not a script either of them writes. A file that is no
   longer wanted RETIRES to a shelf folder with a ledger line; a wiki
   section that is rarely read moves to a COLD SHELF file, verbatim,
   with a stub at the old heading and an index entry; a wrong memory is
   marked superseded in place. Knowledge is hard-won and the rarely used
   kind is still knowledge. A real deletion needs the CEO's express
   permission given TWICE (the manager asks naming the exact target,
   gets a yes, restates, gets a second yes) and the four texts are
   recorded verbatim before the one command runs. The harness backs it
   (HOOKS_METHOD.md Tier 2d, the preserve guard): delete verbs,
   work-discarding git verbs and deletion calls in new code are refused
   on every shell command and every file write; the session scratchpad
   passes; a drive root, the home folder or the repo root pass never,
   grant or not. Every brief carries the law in one line, and a refusal
   in an employee's report is the law working - the manager moves the
   thing or asks the CEO twice, never routes around it.


## THE ASSIGNMENTS
| Task type | Employee model | Notes |
|---|---|---|
| Search / locate (where is X) | haiku (explore) | read-only |
| Look up a fact in docs | haiku (lookup) | read-only |
| Config / KubeJS edits from an exact spec | sonnet | manager verifies in game or server log |
| Log reading (latest.log, crash reports) | haiku | report the lines, never the whole log |
| Blender animation design, boss design | manager (opus) | needs the renders reviewed |

## The ledger
date | who | task | employee | result | corrections
(none yet - the first delegation writes the first line)
