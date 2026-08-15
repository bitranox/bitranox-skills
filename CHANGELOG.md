# Changelog

All notable changes to the bitranox plugin are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Versioning (SemVer): how to pick the next number

Versions track `plugins/bitranox/.claude-plugin/plugin.json`. Installed copies only re-fetch
when that version changes, so every change under `plugins/bitranox/` must bump it (see
`CONTRIBUTING.md`). Pick the bump by impact on the published surface:

- MAJOR (`X.0.0`): breaking change. Removing/renaming a skill, or changing a skill's
  invocation or behaviour incompatibly.
- MINOR (`x.Y.0`): backward-compatible addition. A new skill, hook, or capability.
- PATCH (`x.y.Z`): backward-compatible fix. A bug fix, wording/doc fix in a skill, added tests.

Repo-meta outside the plugin tree (this file, `README`, `CONTRIBUTING.md`, CI) does not ship to
installed copies and needs no bump.

## [5.203.0] - 2026-08-15

### Added

- **`bx:pin` is now a write-permission gate, not just prose.** `bx:pin` already marks the facts
  that must survive the dream untouched (the iron rules); it was documented as exempt from
  archive/move/reword but nothing enforced that - a plain `memory_engine add` could silently
  overwrite a pinned fact's hook or body. `add_or_update_entry` now raises `PinnedEntry` BEFORE any
  write when the target at that slug is already pinned, so `memory_engine add --slug <pinned>`
  refuses (`! refused: ... is pinned; use 'amend-pinned --slug <slug>' ...`, exit 1) instead of
  quietly rewriting it. The only way through is the new `amend-pinned --proj D --slug S [--hook H]
  [--body-file F]` verb, a separate command rather than a `--force` flag, so an autonomous pass
  copying an example `add` invocation can never reach it by accident; it performs the same upsert
  with the pin check skipped and does not itself unpin the fact.
- `move`, `relocate`, and `rename` are UNCHANGED and are NOT gated: they already thread `pin`
  through every write untouched (verified before this change), so re-leveling a pinned fact keeps
  working exactly as before - the gate lives only in `add_or_update_entry`'s update path, and a
  pinned fact still refuses an ordinary `add` at its new level after a move.
- No new token on the pointer line: `bx:pin` already round-trips correctly through parse, render,
  and every mover, so no store migration is needed.

### Removed

- The `bx:owner=human` write-permission partition shipped in an earlier draft of this version is
  reverted. Every fact in the store is written by a model, including facts recording user
  directives, so "human-owned" only ever labeled the model's own write - it never distinguished
  real authorship, and it also had a real defect (the movers silently stripped the marker). `pin`
  already marks exactly the facts that need protecting; this version gates that existing marker
  instead of adding a second, weaker one.

### Changed

- Documented the pin gate where the autonomous passes actually read it. The store spec
  (`meta-self-improve/references/memory-backend.md`) described a pinned entry as merely "exempt
  from archive/move/reword in the dream unless the user approves that specific change" - prose
  that predates this version's enforcement. It now states precisely which path refuses (an
  ordinary `add` on a pinned slug, before any write) and which merely preserves (`move`,
  `relocate`, `rename` carry `pin` through unchanged and never refuse on it, so re-leveling a
  pinned fact needs no exception), and adds the `amend-pinned` command-table row.
  `meta-dream-tree/SKILL.md` and its shared `references/dream-core.md` carried the same
  pre-enforcement claim in four more places (the PLACEMENT step, a Common mistakes bullet, a
  Rationalizations row, and the routing-prompt section shared by the whole dream family) - all
  corrected to match: placement re-levels a pinned fact like any other entry, and only its
  content is off-limits to the dream.

## [5.202.0] - 2026-08-15

### Added

- `memory_engine add` now warns when a fact's hook reads as a bare negative claim about a tool, or
  when its body describes an unresolved failure. Advisory only, never a refusal, since an incident
  record legitimately describes a broken thing.
- `meta-self-improve` and `meta-dream-tree` state both constraints where the author and the
  reviewer read them.

## [5.201.0] - 2026-08-15

### Added

- **`process-agents-dispatching-parallel` now says what a dispatch COSTS, so a fan-out can be
  sized before it is issued.** The "When to Use" section gains the sizing rule: an Agent-tool
  dispatch carries a large FIXED token cost independent of the prompt, because every dispatch
  re-pays the system prompt plus the whole CLAUDE.md and memory cascade the subagent inherits.
  Measured 2026-08-12: 57.5k tokens for an inert text-only probe with zero tool uses, 73.4k for a
  general-purpose agent plus one Read. Budget a per-item fan-out as item count times about 60k,
  and where the per-item work is small, batch many items into one dispatch instead of running one
  agent per item.

  The skill described how to SPLIT a fan-out and said nothing about what each split costs, so the
  obvious reading of "dispatch one agent per independent problem domain" scaled straight into a
  worklist of hundreds. Sizing such a design from the prompt answers low by a factor large enough
  to make an unaffordable fan-out read as deployable.

## [5.200.0] - 2026-08-15

### Added

- **`compuse-toolbox`'s `transcript_tail` can now read a whole transcript, not only its last turn.**
  Two new modes: `--all` returns every user/assistant text turn, and `--tool NAME` returns every
  `tool_use` block invoking that tool with its input. Each row carries the 1-based JSONL LINE it
  came from, so a finding can be addressed directly (`sed -n '<line>p'`) instead of searched for a
  second time; the count includes blank and unparseable lines for exactly that reason. `--json`
  emits the skill's usual `{ok, command, skipped, data}` envelope, an unparseable line is counted
  onto stderr rather than dropped in silence, and a mode that matched nothing exits 1 instead of
  printing nothing and succeeding. The tail mode is untouched: with neither flag the output is
  byte for byte what it was, pinned by a test.

  The gap was measured. Reviewing a finished session needs every record, not the last one, and the
  questions it asks ("what did the user ask across the run?", "which `Agent` dispatches went out,
  with what input?") were answered by hand-rolling four throwaway extractors in a single session,
  because the tail returns only the final text and a raw field dump (`jsonl_grep --field
  message.content`) hands back block JSON rather than the text.

## [5.199.0] - 2026-08-14

### Changed

- **Re-issues 5.198.1 under a MINOR number, because it was classified wrongly.** That release
  ADDED an instruction to `infra-windows-servicing` - how to test whether a guest-initiated reboot
  restarts the guest or tears the VM down - and this project's own SemVer rule calls a
  backward-compatible addition MINOR. It shipped as a PATCH on the reading that it closed a gap in
  existing guidance rather than adding a capability. No content changes here: 5.198.1 already
  carries the text, and installs that took it are already correct. The number is what was wrong,
  and a consumed version cannot be recycled, so the correction is a fresh bump rather than a
  rewrite.

## [5.198.1] - 2026-08-13

### Changed

- **`infra-windows-servicing` now says HOW to verify the platform property it asks you to check.**
  The apply-reboot section tells the reader to establish whether a guest-initiated reboot really
  restarts the guest or tears the VM down, which a GREEN re-run flagged as unanswerable from the
  text. It now names the signal: read the VM process identity across an ordinary in-guest reboot -
  a genuine restart keeps the same hypervisor process, a teardown returns a new one - and says to
  do it once, in advance, on any guest. That was the signal that actually diagnosed the original
  incident. The re-run also confirmed the rescoped wording reads as a condition rather than a
  prohibition: asked whether the text forbids in-guest reboots, the reader answered no and quoted
  the sentence that decides it.

## [5.198.0] - 2026-08-13

### Added

- **`infra-windows-servicing` now covers the apply reboot, which is where an in-place upgrade on a
  VM is most easily thrown away.** `setup.exe /noreboot` arms a one-shot BCD `bootsequence`
  pointing at the staged `NewOS`, and the second stage runs only if the machine boots that entry.
  An interrupted apply reverts the WHOLE upgrade, not just the interrupted step - after a
  down-level that logged `[Setup360Result]=[0x0]`. That `0x0` is the diagnostic the section is
  built around: it says the down-level SUCCEEDED, so a revert carrying it means the apply was cut
  off and the reboot is what to investigate, not the upgrade. Nothing else announces it as a reboot
  problem: on a VM the machine runs afterwards and every host-side check reads normal.

  Where a guest-initiated reboot tears the VM down instead of restarting it, an in-guest
  `shutdown /r` produces exactly that revert, and the hypervisor's clean stop plus start avoids it.
  That is written as a property of the platform to verify ONCE, deliberately NOT as a rule that
  in-guest reboots are unsafe - it was one host's temporary behaviour and was later fixed there.
  The prohibition on a HARD stop mid-servicing stays unconditional and distinct from it, because
  the old "do not hard-stop a guest mid-update" line was itself an argument for rebooting from
  inside.

  It also states that a rollback DELETES the staged `NewOS`, so re-arming the boot entry - the
  tempting two-minute fix - boots into nothing. The existence check on the staged `winload.efi` is
  named as the decision between re-arming and re-running the whole down-level, and the diagnostic
  order under "A clean health check" now says it does not apply to this failure, since a reverted
  upgrade did not fail there and none of those reads show anything.

- **The `Windows.old` reparse-point strip must not pass through an ASCII layer, and must be
  re-counted.** Emitting one removal per link into a `.cmd` batch mangles non-ASCII names, and on
  a localised install those are the names that matter: measured on a German guest, 48 of 51 links
  were removed and the 3 survivors all pointed into the live OS. A strip pass that silently skips
  exactly the dangerous links is worse than none, because the mirror that follows assumes it
  worked. The strip now runs in-process, reports each survivor by name, and gates the mirror on a
  fresh enumeration rather than on the loop's own tally.

- **Blast-radius verification splits into strict and tolerant counters.** A live `C:\ProgramData`
  recursive FILE count drifts unprompted - measured 147707 to 147709 over 60 idle seconds - so
  comparing it with strict inequality manufactures an ESCAPED verdict on a clean delete, whose
  remedy is destroying a good machine. Four counters stay strict; that one takes `max(50, 1%)`.
  The tolerance costs no detection because a real escape is never subtle (`ProgramData` 21 dirs to
  18, `Users\Default` 29 entries to 0). Each row now returns a verdict rather than a number, and
  the skill adds two cheap corroborations: a build-matched healthy peer, and sshd still serving as
  the canary that dies within seconds of a real escape.

- **Monitoring gains the failure modes that make a healthy guest look stuck.** An in-place upgrade
  replaces `C:\Windows`, so a monitor staged under `C:\Windows\Temp` is deleted by the very event
  it waits for, and `powershell -File <deleted>` prints a banner and exits 0 - two guests reached
  the target build while the monitor reported an unknown build for 90 minutes. The skill now reads
  build and armed-state cmd-natively from the registry and BCD, and notes `UBR` returns hex.
  Alongside it: `wmic` is gone in 25H2 and returns EMPTY rather than an error, so an inventory step
  reports a machine with no disks; a check must report "cannot read" separately from "not armed",
  or an unreachable guest reads as a clean negative; and a wrapper's failure verdict is not the
  guest's - one reported its worker wrote no verdict while the guest's own log had recorded success
  two minutes earlier, because a failed READ and an absent marker were indistinguishable to it.

  The monitoring section's existing "use a tolerance, never exact equality" line is now scoped to
  stall detection explicitly, since it otherwise reads as governing the blast-radius counters,
  four of which are strict.

- **A third measured `Windows.old` delete joins the duration figures**: 58.7 min, 33.98 GB to
  54.13 GB free, so 20.15 GB reclaimed, `robocopy` exiting `rc=2`. Three runs of one procedure now
  span a 6x range with nothing wrong in any of them, and the existing point stands that an exit in
  the 0-7 band says nothing about whether the run stayed inside the tree.

## [5.197.0] - 2026-08-12

### Added

- **`process-test-driven-development`'s `redcheck` can now assemble the agent's own startup context
  as the corpus, instead of leaving the reader to enumerate it.** `redcheck` already checked
  whether a scenario-based RED is testing a lesson the agent was handed before it ever saw the
  prompt, and its docstring already named the config cascade as an intended corpus. Nothing built
  that corpus, so every author re-derived the same enumeration by hand - which is what
  `meta-skill-writer` had been telling them to do since 5.196.0.

  `--corpus-cascade DIR` builds it: every `CLAUDE.md` and `CLAUDE.local.md` from `DIR` up to the
  filesystem root, plus every memory fact body under a `.claude-memory/facts/` on that chain, each
  labelled with the path it came from so a hit says which file already teaches the scenario. It
  enumerates by walking the filesystem and reading the paths directly, never through a search tool,
  because project `CLAUDE.md` files and memory stores are routinely gitignored and a
  gitignore-aware search drops them silently, leaving a small corpus in which everything looks
  clean. `--corpus-cascade-top DIR` bounds the walk to a self-contained fixture tree.

  The verdict now says how much it is worth, in the text output and in the JSON envelope alike. An
  inherited hit is STRONG: the lesson demonstrably sits in reachable context and the report names
  the file. A clean result is WEAK: the check compares distinctive terms, so it cannot see a
  paraphrase, and no hit means NOT CAUGHT rather than absent. Every run reports how many documents
  it read, and a corpus that assembles nothing is its own outcome (`unchecked`, exit 3) rather than
  a quiet pass, because an empty corpus makes every scenario look clean.

  Installed plugin skills are deliberately not assembled. Where they live depends on the reader's
  plugin cache and installed versions, so a built-in path would report a falsely clean corpus on
  someone else's machine; `--corpus` takes them explicitly.

- **`meta-skill-writer` now points its inherited-context check at that tool.** The RED-phase rule,
  the RED-phase checklist item, and both the "before trusting a RED" paragraph and route 2 in
  `testing-skills-with-subagents.md` name the command and state how to read its three answers.
  `compuse-toolbox` indexes the mode in the user's own words.

### Fixed

- **`redcheck`'s rarity cutoff no longer sits below the band that carries the lesson.** The cutoff
  that decides which shared terms count as evidence was tuned as a starting floor against a
  topically diverse corpus. An assembled cascade is not that: it is a few hundred documents from
  one author's own notes, which reuse that author's vocabulary throughout. Measured over such a
  corpus, the terms that carry a lesson sit around 1 to 5 percent document frequency while true
  boilerplate sits an order of magnitude higher, so the old 1 percent cutoff filtered out the
  evidence itself and a scenario whose lesson was in the corpus still came back clean. The default
  moves to 5 percent, between the two bands, and `--rarity-max-fraction` exposes it for corpora of
  a different shape.

## [5.196.0] - 2026-08-12

### Added

- **`meta-skill-writer` now states that an inert probe agent type bounds an agent's TOOLS, not its
  CONTEXT, and what to do when that voids a RED.** The "Watch for baseline contamination" section
  covered injected context arriving from a recall hook or a RAG layer, and its isolation ladder
  assumes a retrieval setting an author can wall off. It did not cover the form that has no such
  switch: a dispatched subagent inherits the dispatching session's CLAUDE.md cascade and
  always-loaded memory index, so stripping Bash, Read and Write stops the agent exploring its way
  to an answer but not already knowing it. When the lesson under test is already recorded there,
  the behavioural RED cannot fail honestly, and re-running it only reshuffles which arm wins.

  This is the ordinary case rather than an exotic one: a self-improve loop records the lesson in
  the memory store first and contributes it to the skill later, so the lesson is already in the
  always-loaded index by the time anyone RED-tests the change. The reference file now prescribes
  checking the cascade and store BEFORE trusting a RED, and gives two honest routes when the lesson
  is already inherited - make the coverage check against the skill FILE the evidence (a fact about
  the artifact, which inherited context cannot forge, with the negative gated on a control pattern
  known to appear), or de-telegraph a behavioural arm into a domain that text does not teach - with
  the review artifact required to record which route was taken. It also states that a RED which
  does not flip is a legitimate, reportable outcome rather than a reason to escalate into
  progressively harder scenarios until something fails. `SKILL.md` carries the rule in short form
  in its RED phase and adds the matching RED-phase checklist item.

## [5.195.1] - 2026-08-12

### Fixed

- **`write-humanize-en`/`-de` no longer point the reader at a `scripts/` directory that does not
  exist.** The explanatory sentence right after the invocation examples still said the
  `strip_typographic_tells.py` script is "bundled in this skill's `scripts/` directory" ("liegt im
  Ordner `scripts/` dieses Skills"), a leftover from before the 2026-08-02 shared-strip-script
  consolidation moved the script to `plugins/bitranox/hooks/`. The three invocation lines above
  that sentence were already repointed at the time; only this one explanatory sentence in each
  skill kept the stale claim. Both files now say the script lives in the plugin's `hooks/`
  directory, matching the invocation lines and the actual location.

## [5.195.0] - 2026-08-12

### Added

- **`process-test-design` gained a rule on scrubbing a captured artifact before it becomes a test
  fixture**: a packet capture, protocol exchange, log, or config dump committed as a fixture needs
  its structured payload scrubbed (options, TLVs, nested records), not just its headers - a
  header-only scrub can look complete while site topology (internal hostnames, domain names,
  subnets, device identifiers, vendor/serial data) still sits in the payload underneath. Applies
  across protocols (DHCP, DNS, LLDP, SNMP) and equally to log/config dumps. Pairs the rule with an
  enforcement mechanism: assert the shipped fixture's fields in a test, so a re-capture or
  re-export that reintroduces unscrubbed content fails the suite instead of depending on a person
  remembering to re-check by eye.

## [5.194.0] - 2026-08-12

### Added

- **`meta-consolidate-claude-md` gained `claudemd_variance.py`**, its first shipped script: the
  measurement this skill's own procedure prescribes ("split every CLAUDE.md into `## ` sections,
  hash each body, group, and compute the common ancestor of each group of 3+") but shipped no
  tool for. Two sessions hand-rolled that exact script from scratch before this one shipped.
  `claudemd_variance` enumerates by a plain filesystem WALK, never `grep` and never
  gitignore-aware, so a gitignored CLAUDE.md is found exactly like a tracked one - a hand-rolled
  version built on the session's own `grep` cannot make that claim. It hashes each section body
  after a precisely defined whitespace normalisation (trailing whitespace and blank-line runs
  collapse; leading indentation does NOT, since it is structure, not noise), groups identical
  bodies per heading, and reports each variant's common ancestor - a single-member variant's
  ancestor is that file's own parent directory, never the filesystem root - plus the largest
  variant's share of the group, the number this skill's "60-75% means one dominant version"
  signal keys on. Indexed in `compuse-toolbox`'s tool table as a cross-reference so that table
  stays the one place that answers "is there already a tool for this?".

## [5.193.0] - 2026-08-12

### Added

- **`git-worktrees` gained `wtclean.py`**, its first shipped script: remove a worktree AND the
  per-topic build cache it leaves behind. A per-worktree cache is deliberately kept OUTSIDE the
  checkout, which is what stops several worktrees fighting over one `CARGO_TARGET_DIR`, so
  `git worktree remove` never touches it and it accumulates at gigabytes a time with nothing
  listing it. The usual discovery is running out of disk and then hunting by hand with `du` and
  `rm -rf`. `wtclean` names the worktree and its caches together with sizes, deletes nothing until
  `--apply`, and then removes exactly what the plan listed rather than re-scanning. It refuses a
  symlinked target, a checkout holding uncommitted or untracked work (`--discard-uncommitted`
  overrides that and forwards `--force` to git, discarding the work), and a topic that is a path
  rather than a bare name. Cache locations are a stated convention with `--cache-dir` /
  `--base` / `--prefix` / `--cache-suffix` overrides, and a run matching nothing reports which
  paths it checked instead of an empty plan. Indexed in `compuse-toolbox`'s tool table as a
  cross-reference so that table stays the one place that answers "is there already a tool for
  this?". Promoted from a personal toolbox jig; the personal copy is retired in favor of this one.

## [5.192.0] - 2026-08-12

### Added

- **`process-test-driven-development` gained `redcheck.py`**, a check for whether a scenario-based
  RED (a prompt handed to an agent, not code) is even able to fail. Two leaks make a RED that
  cannot fail look exactly like a good result: inherited coverage, where the agent already has the
  lesson from its own config cascade or shipped reference material and answers from that instead
  of the scenario, and telegraphing, where the scenario names the trap or pre-diagnoses the cause
  and hands over its own answer. `redcheck` checks a scenario for both BEFORE an agent dispatch is
  spent on it, and names which corpus document already teaches the lesson or which phrase gives
  the answer away. Indexed in `compuse-toolbox`'s tool table as a cross-reference so that table
  stays the one place that answers "is there already a tool for this?". Promoted from a personal
  toolbox jig; the personal copy is retired in favor of this one.

## [5.191.0] - 2026-08-12

### Added

- **`compuse-toolbox` gained `newest.py`**, a jig that picks the latest timestamped file or
  directory by MTIME, never by name sort. `ls <glob> | sort | tail -1` looks like "the newest"
  and is not: a longer name sharing the same date prefix sorts AFTER a shorter one, so an extra
  word beats the date. Pruning the wrong file this way is loud and gets noticed; VERIFYING against
  the wrong baseline is silent, which is the expensive half. It sorts by mtime only (files and
  directories alike), breaks a genuine tie deterministically by input order, and prints the AGE of
  what it picked so a stale answer from a stale set stays visible. Promoted from a personal
  toolbox jig; the personal copy is retired in favor of this one.

## [5.190.0] - 2026-08-12

### Added

- **`compuse-toolbox` gained `diffbehave.py`**, a differential-execution jig: run two commands on
  the same inputs and diff what they actually did (exit code, stdout, stderr), instead of judging
  "does this behave differently" by looking at the two versions - an `ast.dump` comparison, a line
  count, and a `grep -c` all execute nothing and cannot answer the question. Its `--expect-differ N`
  flag is the known-negative check: a hand-rolled detector verified only on cases where it already
  agrees has proved nothing, so the tool fails unless at least N cases come back DIFFER. Promoted
  from a personal toolbox jig; the personal copy is retired in favor of this one.

## [5.189.0] - 2026-08-12

### Added

- **`git_state.py` gained a `--files GLOB` mode**, answering the per-FILE question the existing
  repo-level mode cannot: across a tree, which copies of a named file (`CLAUDE.md`, a config) are
  tracked-and-modified, gitignored, untracked, or outside any repo at all. This has now been
  hand-rolled twice in two sessions - `git status --porcelain -- <path>` is EMPTY for a gitignored
  file and for a tracked-clean file ALIKE, so a naive check silently conflates them, and only the
  tracked one is restorable with `git checkout`. Measured on a real tree: 15 tracked-modified, 37
  gitignored, 22 outside any repo across 186 `CLAUDE.md` files.
  Classifies with `git ls-files --error-unmatch` (tracked, read off stdout - it does not stop at
  the first unmatched pathspec) and `git check-ignore --stdin --no-index` (ignored; `--no-index`
  is required, because without it git itself silently excludes tracked files from the ignored
  output, which would make the precedence below true by git's accident rather than this tool's
  decision), never `git status`. TRACKED WINS the tracked-and-ignored case: `check-ignore` is only
  ever asked about the paths `ls-files` did NOT report tracked, so a file that is both tracked and
  matched by a `.gitignore` pattern always classifies tracked-clean/tracked-modified, never
  ignored - proven by mutation (reordering the precedence, or asking `check-ignore` about every
  candidate instead of the non-tracked remainder, makes the dedicated precedence test fail).
  `no-repo` (no enclosing git repo at all) and `untracked` (inside a repo, not tracked, not
  ignored) are kept distinct - also proven by mutation.
  Bounded process count: at most 4 git subprocesses PER REPO regardless of how many candidate
  files it contributes (`ls-files`, `check-ignore` on the non-tracked remainder, an optional
  `rev-parse --verify HEAD` probe, `diff --name-only HEAD` on the tracked remainder to split
  tracked-clean from tracked-modified) - never 2 per file. Repo-root discovery is a pure
  filesystem walk (no subprocess): it reuses the existing `find_repos()` downward walk plus a
  cheap upward `.git`-presence check from `--root` itself, so `--root` may be either a directory
  holding many repos or a subdirectory inside one.
  Follows this skill's CLI conventions: a `--json` envelope (`{"ok", "command": "git-state",
  "data", "skipped"}`), the match-count summary and any per-repo failures on stderr (stdout stays
  parseable JSON), and format-independent exit codes (0 at least one file matched the glob, 1 none
  matched, 2 the walk or every matched repo's git calls failed outright). Cross-platform: argv
  lists throughout (no shell strings), `--` before every pathspec (leading-dash/space/unicode
  filenames all verified), and `encoding="utf-8", errors="replace"` on every new subprocess call.
  16 new tests (23 total in the file); `SKILL.md`'s `git_state` row documents the new mode.

## [5.188.0] - 2026-08-12

### Added

- **`memory_engine.py move` accepts a SET of slugs that moves as one unit** (`--slug` is now
  repeatable, and also takes several names after a single flag; the single-slug form is unchanged).
  The down-move ref guard judges every member by where the WHOLE set lands, so a member citing
  another member is not dangling. This is what makes a MUTUALLY-CITING pair demotable at all: each
  one's inbound ref is the other, so single-slug moves refuse in BOTH orders and the only way down
  was `--force` - which strands exactly the ref the guard exists to protect. Demoting
  over-promoted facts is the dream's main lever for shrinking an oversized always-loaded tree-top
  block, and a cluster that cross-links internally is precisely what accumulates there.
  A citer OUTSIDE the set still refuses without `--force`: the guard is made set-aware, not
  weakened, and the exemption is keyed to the pointer AT the from-level (a stray duplicate pointer
  for a moving slug left at a higher level does not move, so it still counts).
  The set is ATOMIC ON REFUSAL - presence, legacy state, refs and duplicate-pointer conflicts are
  all decided for every member BEFORE anything is written, because a half-applied move strands the
  refs the feature exists to keep whole. The write phase stays per-slug add-then-remove, so an
  interruption leaves a visible duplicate pointer, never a lost fact, and re-running the same
  command completes it; a write error reports how many pointers already moved and says to re-run.
  The report gained `slugs` and `moved_slugs`; `slug` is the comma-joined set, identical to the
  input for a single slug. Every other `move` behaviour is unchanged (sibling / cross-tree / same
  level / not-found / legacy refusals, the up-move path, divergent-duplicate handling, `--force`).

## [5.187.0] - 2026-08-12

### Changed

- **`meta-dream-tree` / `meta-dream-crosstree` corroboration gate is now STRICTER**
  (`self_improve_signals.py`, `dream_state.py saw-promotable` / `should-promote` / `promoted`):
  the dwell that gates promoting a model-INFERRED fact into a tree-top always-loaded block now
  counts DISTINCT PROJECTS instead of sightings. It previously counted one sighting per dream run,
  which a dream can satisfy on its own: a fan-out re-reads the same UNCHANGED fact bodies on every
  run, mechanically re-derives the same candidate list, and the second run corroborates the first
  with no new evidence (a measured pass recorded 84 sightings in a single run). Repeat sightings
  from one project now collapse to one corroborator, so N sightings of an unchanged body can never
  reach the threshold, while two DISTINCT projects still satisfy it - including within a single
  crosstree run, which the old counter refused. `promoted` clears every project's sighting rather
  than one, so a single later sighting cannot re-trip a cleared gate. The user-STATED path is
  untouched and still promotes eagerly; only the inferred path is gated. The prose in both skills
  and in `references/dream-core.md` claimed ">= 2 distinct projects" while the mechanism counted
  runs; both now say and do the same thing, and the dream is told to name the project a fact CAME
  FROM (the argument defaults to the cwd, which collapses a whole fan-out to one corroborator).
- **State compatibility for the above:** the sighting store moved from a per-project file to one
  shared `promotion-candidates.json`, because a per-project file structurally cannot see another
  project's sighting, which is the whole question the gate asks. Pre-existing per-project counter
  files are NOT migrated and are no longer read: their contents are sighting counts, exactly the
  evidence this gate no longer accepts, so they read as zero. Any unusable shape fails CLOSED - it
  can neither crash a dream nor be reinterpreted as corroboration. A candidate part-way to
  promotion under the old scheme therefore restarts and needs a genuine second project.

## [5.186.0] - 2026-08-12

### Changed

- **`meta-audit-local-skills-and-hooks` skill** (`audit_local.py` / `harness_checks.uncollectable_tests`):
  the `check` path no longer reports `[tests-uncollectable] pytest not installed - collection
  unverified` whenever the CHECKER's OWN launching interpreter lacks pytest - that message
  described the tool's environment, not the target, and rendered an unmeasured result as if it
  were a measurement. It now falls back to `uv run --with pytest python -m pytest` (uv is already
  required to launch this script), so a target's tests are actually collected before anything is
  reported. Three outcomes are now kept apart under distinct labels: a real collection failure is
  still `tests-uncollectable`; a clean collection reports nothing at all; and the check itself
  being unable to run (the uv fallback also unavailable, or timing out) is a new, separately
  labelled `tests-unmeasured` finding that can never be mistaken for a defect in the target.
  Verified against this repo's own skills under a system interpreter with no pytest installed: a
  healthy tree now reports zero collection findings (previously 3 false positives), and a
  deliberately broken tests dir is still caught, with the real import error, through the same
  fallback path.

## [5.185.0] - 2026-08-12

### Changed

- **`strip_typographic_tells.py` hook script** (used by `write-humanize-en`/`-de` and the
  tell-sweep repair path): a SPACED em dash now normalizes straight to ` - ` instead of leaving
  the doubled-space residue `  -  `. The em-dash family (U+2014, U+2E3A, U+2E3B) left the
  `str.translate` table, which can only emit a fixed string, and moved to a context-aware pass
  that reuses the space already beside the dash. The residue was documented as a manual tidy step
  and the same normalization was hand-rolled twice in one session after the script had run.
  Deliberate limits, each with a test: the whitespace class is `[ \t]`, never `\s`, so a dash at
  end of line can never join two lines; whitespace against a newline is neither consumed nor
  created, so leading indentation and a markdown hard line break (two trailing spaces) survive
  byte-identical; only ONE space per side is reused, so a wider run stays as it is, which keeps a
  padded table cell and an aligned trailing comment at their original width. The other dashes
  (U+2010, U+2011, U+2012, U+2013, U+2015, U+2212) still become a bare hyphen with the text's own
  spacing untouched. Verified on the repo's own markdown: injecting a spaced em dash at every
  spaced hyphen that sits outside code, in skill docs and in real table cells, then running the
  script restores every file byte-identical, and a second run is a no-op.

## [5.184.0] - 2026-08-12

### Added

- **`meta-consolidate-claude-md` skill**: new variance-table row for copies that share only a
  closing pointer sentence while the body is unique per copy (verdict: LEAVE IT) - a "largest
  variant covers X%" reading can be that one sentence's share of a short body, not real
  duplication. Also states the reachability invariant is judged per FILE, not per GROUP: a
  group's members can straddle the covering ancestor's subtree, so a group-level trim can delete
  guidance left unreplaced for members sitting outside that ancestor. Measured consolidating a
  real tree: the existing 60-75% signal pointed at lifting a section appearing in 27 files that
  was already the correct minimal delta plus one shared pointer line, and 2 of those 27 sat
  outside the ancestor that would have carried the covering rule.

## [5.183.1] - 2026-08-12

### Added

- **`process-agents-dispatching-parallel` skill**: new "Verification" checklist item - check
  `git status --porcelain` before staging or committing after agents return. A subagent dispatched
  with a read-only intent still holds Write/Edit/Bash and can write into the tree while reporting
  only text, so the write is silent even when the agent had no stated reason to write.

## [5.183.0] - 2026-08-12

### Added

- **`process-review-verification-before-completion` skill**: new "Failure class resolved" row in
  the Common Failures table plus a "Fail-fast gates (unmasking)" Key Pattern. A gate that aborts at
  the first error (rustc, most compilers, staged pipelines, a fail-fast test runner) hides every
  failure after it - fixing the first only lets the gate run far enough to expose the second, it
  does not prove the second is fixed too. Re-run the gate itself and require its own green line
  before reporting a failure class resolved, instead of extrapolating from a model of the cause to
  "all N items are fixed."

## [5.182.0] - 2026-08-12

### Added

- **`process-debug-systematic` skill**: new Phase 3 step, "Closed-Source Peer: Escalate to
  Disassembly After the Second Dead Hypothesis". When the system on the other side of a bug is
  a closed-source binary (a proprietary driver, firmware, appliance, or vendor tool) and a
  second black-box hypothesis dies against measurement, stop forming a third guess and
  disassemble the peer instead (a disassembler such as Ghidra driven by its scripting/Python
  bridge, plus any public PDB or symbols the vendor ships), citing an address and a symbol for
  the conclusion. A clean refutation counts as an equally valid result. Reverse-engineering is
  for learning the protocol needed for interoperability, never for copying the implementation.

## [5.181.0] - 2026-08-12

### Added

- **`net-tailscale` skill**: new "DNS: MagicDNS on quad-100 is platform-asymmetric" section.
  `100.100.100.100` is served by the LOCAL `tailscaled`, so it answers on Linux even with
  `accept-dns=false` - but not on FreeBSD/pfSense, where `tailscale status` reports "Tailscale
  DNS: disabled" and queries against quad-100 time out while the tailnet route to it still
  exists. A resolver forward zone pointing at quad-100 SERVFAILs on those platforms as a result;
  SERVFAIL vs NXDOMAIN is the tell (dead target vs genuinely absent name). Cross-references
  `bitranox:net-firewall-pfsense` for the pfSense-side detection and fix of the related
  `accept-dns=true` / `resolv.conf` / `pkg` trap that skill already documents.

## [5.180.1] - 2026-08-12

### Changed

- **`compuse-ssh` skill**: `ssh -t` allocates a pty only when the CLIENT's own stdin is a terminal,
  so from a pipe, an editor run-shell or an unattended job runner remote interactive `sudo` has no
  tty to prompt on and fails as repeated `Permission denied`, reading as a wrong password. ssh's own
  prompt still works there (it reads `/dev/tty`), which makes "the login works but `sudo` does not"
  the identifying signal rather than a second route - the no-password rule still binds. Added the
  companion bootstrap path: behind Ubuntu's default `PermitRootLogin prohibit-password` a root key
  is accepted but a root password refused, so install the key into the sudo user's OWN
  `authorized_keys` (no `sudo`, no `-t`) or paste it at the console.

## [5.180.0] - 2026-08-12

### Added

- **`process-stop-repeating-failure` skill**: after an attempt has been UNDONE (rollback, snapshot
  restore, revert, git reset), retrying the same mechanism with a flag added is the same attempt in
  a different hat. The skill gives three options and refuses a fourth: change the instrument, prove
  the modification on a scratch fixture with a before/after count, or stop and report. Two undos of
  the same target is a hard stop. A reset-to-baseline that runs before every attempt is METHOD, not
  damage undone, and is carved out explicitly.

  Written from an incident where a mirror-purge followed a directory symlink out of its tree and
  emptied live system state; the documented flag that "excludes junctions" governs source traversal
  while the purge walks the destination, so the fix destroyed the same guest a second time. RED
  reproduced the failure (the baseline ran the modified command verbatim, citing the review and the
  clock); GREEN builds the fixture instead. Both arms recorded in `.skillwriter/`.

- **`recovery-retry-gate` hook** (PreToolUse, `Bash|Write|Edit`): fires when the pending call
  repeats a destructive act on a machine that an earlier rollback had to undo, and points at the
  skill above with the two event indices as evidence. Deterministic - no model call.

  A periodic history-only watcher was measured first and FAILED: it can only speak after the action
  it objects to has already run. Judged against the reference incident the gate fires at the exact
  event that repeated the damage and not at the benign verification before it. Across 1426
  transcripts (84,820 tool events) it fires in one, and it is silent on all five reset-to-baseline
  sessions carrying 8 to 32 rollbacks each. Precision rests on 5 firings in a single session, so it
  ships as a complement to the lexical `jig-repetition-nudge`, not a replacement, and its rate wants
  re-measuring once it has fired in the wild.

- **`overwatch_ledger`**: shared session-ledger reader (tool, target, intent, outcome, recovery
  markers) behind the gate.

## [5.179.5] - 2026-08-12

### Fixed

- **`reformat-md-tables` hook**: the Bash fallback no longer fires for a git command that
  rewrites the working tree (`checkout`, `switch`, `merge`, `rebase`, `pull`, `clone`, `reset`,
  `stash`, `cherry-pick`, `revert`, `am`, `apply`, `restore`, `worktree`). Those rewrite tracked
  files wholesale, so every markdown they touch gets a fresh mtime and reads as just-written to
  an mtime scan, though none of it was authored by the operator. Reformatting there is never what
  was asked for, and it is destructive rather than cosmetic: a `git checkout -B` restamped four
  Guide docs, the hook realigned their tables, and the next `git merge` in the same re-cut aborted
  with "your local changes would be overwritten", leaving a half-assembled integration branch.
  Read-only git (`log`, `status`, `diff`) still allows the fallback, since a doc written beside it
  is the operator's. This is the second half of the 5.158.2 fix, which stopped the fallback
  descending into a nested repository but not this.

## [5.175.1] - 2026-08-11

### Fixed

- `fleet_ssh` wrote the current local user into the argv when `--user` was not given, which
  OVERRIDES a `User` directive in ssh_config: a host configured `User root` would have been logged
  in as the wrong account, a regression against plain ssh that the wrapper had no business
  introducing. An unstated user now stays out of the argv entirely, leaving the host bare so the
  config decides.
- The key still resolves for the right identity in that case, by asking ssh itself
  (`ssh -G <host>`, which reads the config without connecting) rather than assuming the local
  account. Guessing there would have offered one user's key while connecting as another - the same
  identity mismatch this jig exists to prevent, moved one step along.

## [5.175.0] - 2026-08-11

### Added

- `compuse-toolbox` ships `fleet_ssh`, a jig for driving a host over ssh or scp with one option
  set and one resolved key. It exists because three traps sit in the hand-typed one-liner it
  replaces, and two of them fail in ways that do not look like what they are.
  - scp carries the login user INSIDE the path and has no `--user` flag. A wrapper that reads
    `--user` only to choose the key hands scp a destination naming nobody, so it connects as the
    LOCAL user while offering the other user's key: `Permission denied (publickey)` from a command
    line where the flag looks honoured. `--user` now fills in a remote side that names no user, on
    either side of the pair, so the key and the login are always the same identity.
  - `-i <key>` alone still falls back to a PASSWORD PROMPT when the key is rejected, which hangs an
    unattended run instead of failing it. `BatchMode=yes` is therefore not optional here.
  - A shared key path can EXIST and be unreadable (root-only on one box, yours on another). Picked
    by existence, ssh fails with EMPTY stdout and the cause surfaces far downstream as "the command
    returned nothing". Keys are picked by readability.
- Host-key checking stays at ssh's strict default. `--trust-changing-host-keys` is the opt-in for a
  fleet that gets reimaged: it accepts a changed key, keeps that churn in a separate known-hosts
  file instead of the real one, and heals a mismatch by dropping the stale entry and retrying
  exactly once. A known-hosts path of `/dev/null` is refused, because ssh then records every key
  "permanently" into the bit bucket and every connect becomes a first connect - the cause of a
  "Permanently added" warning that repeats forever and lands in any helper that merges stderr into
  stdout.
- Key candidates come from `FLEET_SSH_KEY_CANDIDATES` (os.pathsep-separated templates taking
  `{user}` and `{home}`), so no site's paths are baked in.

## [5.172.2] - 2026-08-11

### Fixed

- `decision-review-nudge` read the transcript in TEXT mode while treating the result as a byte
  offset. `len(line)` counts characters there, and `seek` accepts only a position `tell` produced,
  so a single non-ASCII character anywhere earlier in a transcript shifted every later offset and
  resumed the next scan mid-character. Transcripts carry non-ASCII routinely. Now read in binary,
  which makes the arithmetic mean what it says.
- A partially written last line was consumed. A transcript is appended to live, so its tail can be
  mid-write; advancing past it meant the rest arrived later as an unparseable fragment and whatever
  that line recorded was lost for good, where the previous rescan-from-zero had merely made it
  late. The offset now stops at the last COMPLETE line, and the partial one is still parsed in case
  it is already valid.
- An offset past the end of the file wedged the hook silently. A shrunk or replaced transcript
  leaves a stored offset beyond EOF; seeking there succeeds and reads nothing, so the hook would
  go quiet for good and the silence would look exactly like "nothing concluded". The offset is now
  compared against the file size and reset when it no longer fits.

## [5.172.1] - 2026-08-10

### Fixed

- `decision-review-nudge` could go permanently quiet in a long session. Every run rescanned the
  transcript from byte 0 and stopped at the same size cap, so once a session grew past it NO later
  commit was ever reachable - and the silence looked exactly like "nothing new concluded". Runs now
  RESUME: each one starts where the previous stopped, records the offset it reached, and advances
  that offset even on a quiet turn, so a conclusion beyond the cap is picked up by the next run
  instead of never. Each run's work is now proportional to what happened since, not to the size of
  the session.
- The score accumulates onto the previous run's total rather than being recomputed. A per-window
  recount would FALL as soon as a window slid past an older commit, and a fallen score can never
  exceed what was already recorded, which would have stopped the reminder for good.
- A window holding no goal record now keeps the goal state the previous run ended on, instead of
  reading absence as "no goal". The state file carries the goal alongside the offset and score.

## [5.172.0] - 2026-08-10

### Added

- `decision-review-nudge` now has a second, NON-BLOCKING channel. The first conclusion in a session
  still blocks, because an ask that can be scrolled past is one that gets scrolled past; every
  conclusion after it emits `hookSpecificOutput.additionalContext` instead, which rides along next
  to the turn's result without stopping it. That retires the trade the previous version had to
  make: an early first ask no longer means silence for the rest of the session.
- The channel was verified against the CLI's own embedded hook documentation before use -
  `{"hookSpecificOutput": {"hookEventName": ..., "additionalContext": ...}}` - and the Stop
  handler is the code that consumes `additionalContexts` and re-tags them `hookName: "Stop"`, so
  it is available on this event and not only on PreToolUse where it had previously been measured.

### Changed

- Repeats are told apart by a SCORE rather than a boolean. A commit never leaves the transcript, so
  a yes/no "has it concluded" would re-fire on every later turn; the hook records the score it last
  acted on and speaks only when that rises. A goal scores 1 while running and 2 once met, so the
  running-to-met transition registers as a new conclusion even though no command was run.
- Repeated blocking was rejected for a second reason beyond nagging: the CLI ends a turn by
  override once a hook has blocked several times consecutively. A remind-only repeat cannot reach
  that cap.

## [5.171.3] - 2026-08-10

### Fixed

- `decision-review-nudge` fired a whole turn late on a `/goal`, and on a session that ended with
  the goal it never fired at all. Observed live: a one-turn goal was set and achieved, and the
  hook stayed silent - its session-keyed flag file was never written. The timestamps show why. The
  goal was set with `met: false` at :49 and reported `met: true` at :07 of the next minute, and
  the Stop hook read the transcript between the two. The verdict is yielded from INSIDE Stop-hook
  processing, so no earlier read can see it, and there is no on-disk goal state a hook could read
  instead (searched, with a control).
- A `/goal` in play now counts as concluded whether or not it has reported met. Since the ask
  happens once per session, the real choice is sometimes-early against sometimes-never, and a long
  goal asked early beats a finished one never asked.

### Changed

- The claim that a blocking Stop hook cuts a goal's loop short was WRONG and is corrected rather
  than dropped. "Stop hook prevented continuation" belongs to a hook setting `preventContinuation`,
  a different field this hook never sets; `{"decision": "block"}` feeds a reason back and the turn
  continues. Measured in a real session: the self-improve gate blocked during an ACTIVE goal and
  the goal still completed.
- Verified by replaying the exact failing input - the real transcript truncated at the last
  `met: false` record - against both the installed copy and the edited source: silent, then fires.

## [5.171.2] - 2026-08-10

### Added

- `decision-review-nudge` now fires at the end of a `/goal` run. Claude Code records an
  objective's progress in the transcript as `{"type": "attachment", "attachment": {"type":
  "goal_status", "met": <bool>, ...}}`, and the LAST such record is the current state - verified
  against 14 real met-records across 11 transcripts on disk rather than inferred from the binary.

### Changed

- While a goal is RUNNING, the nudge now stays quiet even after a commit. Two reasons, and the
  second is the load-bearing one: a goal commits as it goes, so those commits are milestones
  inside the work rather than its end; and Claude Code treats a blocking Stop hook as a reason to
  stop continuing ("Stop hook prevented continuation"), so firing mid-goal would cut short the
  very loop the user started. A goal met by work that never touched git still fires - the
  objective is the conclusion, not the commit.

## [5.171.1] - 2026-08-10

### Changed

- `decision-review-nudge` now fires on a COMMIT, a push, or an opened PR rather than on a
  file-count threshold. The count was a proxy chosen rather than measured, and it was wrong in
  both directions: it fired mid-edit on a session that had concluded nothing, and stayed silent on
  a one-line fix that shipped. A commit is the moment work stops being in progress and starts
  being something somebody else lives with, which is the moment the question is worth asking.
- The detection is `shell_text.is_gated_command`, moved there from `repo-gate` and re-exported so
  the gate's own callers and its 18 parametrized cases are unchanged. Two consumers now ask the
  same question for different reasons - the gate blocks on it, the nudge times itself by it - and
  two copies of that regex set would drift silently in both directions, each recognising a command
  shape the other did not. The move also brings the nudge the gate's hard-won anchoring: a
  CHANGELOG line ABOUT committing is not a commit.
- The transcript is read once per session at most: the session-keyed flag short-circuits before
  the file is opened on every later turn.

## [5.171.0] - 2026-08-10

### Added

- `process-review-uncertain-decisions`: a new skill that asks, after work, which decisions were
  made that the agent is NOT confident about, what alternative was not taken, and what would
  settle it - while deliberately saying nothing about the decisions that are already right. That
  suppression is the point: every other review skill here pushes toward more findings, and a list
  that includes the settled calls hands the sorting back to the reader. The question ships
  verbatim because a clean-room baseline PASSED on both `haiku` and `sonnet`, returning only the
  genuinely unsettled calls out of a ten-step session that mixed them with obviously-right ones -
  so strengthening the wording would have been an unmeasured change to a measured-good prompt.
- `decision-review-nudge`: the Stop hook that fires it. What the baseline showed missing was never
  the wording, it was that nothing asks the question at the end of a session, and the person who
  would ask is the person who has to remember to. It fires ONCE per session, once the session has
  written enough files to have made real choices, reusing the distinct-file evidence the
  `touched-paths` recorder already collects rather than deriving "did real work happen" a second
  way. Its flag is keyed by SESSION, because a per-project flag outlives its session and demands
  work for something that happened in a different one.
- The same question is now reachable from three moments that already exist: the end of a quality
  sweep, a verified completion claim, and finishing a branch. Each is a one-line cross-reference,
  never a copy, so the question has exactly one home; the hook's once-per-session guard is what
  keeps three entry points from producing three asks.

## [5.169.0] - 2026-08-10

### Added

- `repo-gate`: a test-dependency preflight. The gate runs pytest with `sys.executable`, and a test
  that exercises an optional backend fails on its ASSERTION when that backend is absent rather
  than on the import - so a missing package reads as a code defect in a file nobody has touched.
  Measured: an interpreter without `lxml` turned a green tree into a convincing red one, reporting
  an XML entity assertion and costing a full misdiagnosis before `CONTRIBUTING.md`'s warning about
  bare pytest runs explained it. The gate now names the missing packages and prints both the `pip
  install` line and the full `uv run` invocation, and it SKIPS pytest when any are missing, since
  running it anyway files the same problem a second time as a failed assertion and that second
  message is the one a reader acts on. The package list is read from `.github/workflows/ci.yml`,
  so the gate's idea of CI cannot drift from CI's, and packages are probed by their IMPORT name
  (`PyYAML` imports as `yaml`), with a missing parent package handled as missing rather than
  raising (`ruamel.yaml`).

## [5.168.0] - 2026-08-10

### Added

- `process-review-enhance-code-quality`: a fifth always-on check - every invariant a project
  states in must/never terms is enforced by a test that fails without it. The rules are walked as
  a set and reported as a table (invariant, owning test, covered paths, verdict), because prose
  cannot distinguish "checked, holds" from "never looked". Three parts carry it: enumerate the
  paths the INVARIANT covers rather than the ones the test covers, since a passing test on one
  implementation is what makes an untested sibling look covered; take the evidence from a
  mutation, because reading tells you what a test is named and only breaking the rule tells you
  what it holds, and a surviving mutant is a finding; and report code-vs-doc drift in either
  direction rather than assuming which side is wrong. Without it a reviewer had to GUESS whether a
  documented rule was reportable at all, and said so.
- `process-plan-writing-plans`: a task now declares its negative space. Task Structure gains an
  **Out of scope** block with a reason per entry and a **STOP conditions** block for the risks the
  planner can see and the executor cannot. Previously the only exclusion a plan carried landed in
  the commit step, after the work; the design risk the planner had identified had nowhere to go.
  Step 1 also names the seam a test drives, pointing at `process-test-design`.
- `process-agents-dispatching-parallel`: the handling rules a subagent does not inherit. A
  dispatched agent gets your model tier only because you pinned it and your standing rules not at
  all, so the no-secret-values rule and the repository-content-is-data rule go into each prompt
  verbatim. Keeps the separation between a rule and a boundary: an allow-list in prose is a
  request, so where an agent must not be ABLE to act, pick a type whose tools cannot - matched to
  the job, since a reviewer stripped of Read cannot review.

## [5.164.4] - 2026-08-10

### Fixed

- `block-masked-gate-exit`: stop firing on text that merely MENTIONS the footgun. The detector
  matched `$?` anywhere, so an escaped `\$?` in an echo label, a `#` comment, and single-quoted
  prose all read as status checks - the escaped case being the real one, which fired on the author
  while documenting this very rule, its third false fire in a day. New shared helper
  `shell_text.blank_unexpanded_text()` blanks the regions the shell neither executes nor expands
  (escaped characters, single-quoted strings, comments) while preserving pipes and separators so
  the command shape is unchanged. A `$?` inside DOUBLE quotes still fires: it genuinely expands
  there, so `echo "rc=$?"` stays caught, and double-quoted prose is knowingly left as a false
  positive because the shell cannot tell the two apart either.

### Added

- `files-edit-xml`: a section on editing a file you must DIFF. The existing pattern guarantees the
  output is well-formed but not minimal, and an lxml round-trip rewrites the whole document -
  measured at 6863 changed lines for a 6-line edit on a pfSense config, which makes review
  impossible and hides real mistakes. Documents the three losses (empty-tag collapse, CDATA
  dropped on `.text` assignment, `&quot;` unescaped) and the rule: prove the round-trip
  byte-identical on the untouched file before editing.
- `coding-python-uv`: the cache-safety note now covers WRITING into the cache. Upstream already
  says never to modify it directly; what was missing is that seeding or warming a shared cache by
  copying entries in fails silently, because uv writes atomically and a copy does not, so uv
  trusts a half-copied entry and the error surfaces later in an unrelated build.

## [5.164.3] - 2026-08-10

### Fixed

- `meta-self-improve`: retiring a contributed tool now names the MEMORY STORE explicitly and
  gives the sweep a method. The rule already said to check what still INVOKES the local path, and
  a RED probe confirmed a focused reader DOES derive the memory store from that - so this is not a
  comprehension gap and the wording was cut to match. What was missing is actionability: the rule
  named only "a nudge or a doc", never memory, and specified no search method. It now says to fix
  a fact's HOOK as well as its body (the hook is what fires), to sweep with find because Claude
  Code's grep skips the gitignored facts and pointer blocks, to require zero hits before deleting,
  and to name the replacement by SKILL rather than by a path under a versioned plugin dir.
  Measured: `gate.py` was correctly retired once it shipped in `bitranox:compuse-toolbox`, and the
  one unswept reference was the memory rule prescribing it, so the remedy for the tree's
  most-recurring shell error became a command that could not run.

## [5.164.2] - 2026-08-09

### Fixed

- Version bump for the `block-masked-gate-exit.py` fix below, which shipped WITHOUT one. A parallel
  session had moved `plugin.json` to 5.164.1 between this clone's last push and this change, so the
  scripted bump's find-and-replace of the old string matched nothing and reported success anyway.
  Installs only re-fetch on a version change, so the fix reached nobody until this.


### Fixed

- `block-masked-gate-exit.py` false-fired on the very form it recommends. Two narrowings, both
  found by the guard firing on its own author within hours of shipping:
  - ADJACENCY: `$?` holds the status of the IMMEDIATELY preceding command, so only the statement
    directly after a pipeline can be misreading the filter's status. It previously fired on ANY
    later `$?`, so a command that piped one check into `tail` and then ran a SECOND check
    redirected to a file - the correct form - was flagged.
  - Heredoc bodies are stripped, so writing ABOUT the footgun no longer trips the guard that
    teaches it.
  The real shape still fires; a control test pins that the narrowing did not disarm it.

## [5.164.1] - 2026-08-09

### Fixed

- `net-firewall-pfsense`: `doctor`'s resolver check flagged a CORRECT firewall. It required every
  entry in `/etc/resolv.conf` to be loopback, but a healthy pfSense box lists its own resolver
  first and then the configured upstream servers as fallbacks, so those fallbacks were reported as
  evidence of a hijack. The check had only ever been exercised against a box in the broken state.

  Split into the two signatures that actually mean something: `magicdns_in_resolv_conf` (Tailscale
  Accept DNS has taken the system resolver over) and `resolver_not_first` (the box does not ask
  its own resolver first). Upstream servers listed after loopback are no longer a finding, and
  IPv6 loopback counts. Verified silent against two healthy firewalls and still firing on the
  fault. The remedy in the message now names the durable fix: turn Accept DNS off and forward the
  tailnet domain to MagicDNS with an unbound domain override, which keeps tailnet names resolving
  without handing over the system resolver.

## [5.164.0] - 2026-08-09

### Added

- `net-firewall-pfsense` - a skill plus jig for driving a pfSense box, replacing the throwaway PHP
  that otherwise gets pushed over SSH for every change. `scripts/pfsense.py` is stdlib-only and
  takes its access from the caller (`--host`/`--user`/`--ssh`, or a named target in the user's own
  `~/.config/bitranox/pfsense.ini`), so it ships with no host names and no key policy.

  Verbs: `doctor`, `info`, `snapshot`, `dhcp list|rm|rm-static-arp`, `dns list|add|rm`, `arp`,
  `table list|show|test|del`, `rules`, and the `snort check|why|unblock|verify|fixsteps` set.
  Configuration changes go through the PHP config API rather than the XML, are dry runs until
  `--apply`, snapshot first and abort if the snapshot fails, and select by MAC or name so a
  shifting position cannot delete the wrong row.

  `doctor` reports the faults that raise no error of their own, the costly one being a DHCP
  reservation with "ARP Table Static Entry" armed: it pins one MAC to an address permanently, and
  when that is not the MAC currently using it the device stays reachable inside its subnet and
  dies beyond it, at layer 2, with nothing logged. A baseline agent asked about that symptom
  reaches for firewall rules, aliases and gateways and never gets to ARP. It also runs offline
  against a saved `config.xml` (`doctor --config`), so a snapshot can be audited with no network.

## [5.163.0] - 2026-08-09

### Added

Three guards finishing the escalation sweep of facts recording a recurrence of 2 or more. All are
non-blocking nudges: each fires on a shape that is usually a mistake but occasionally deliberate,
and a block on a maybe teaches the reader to ignore the channel.

- `missing-mechanism-nudge.py` - a `memory_engine add` whose `--hook` asserts something is missing,
  defaults off, or is never called, without naming where that was checked. Recorded five times,
  always filed from a neighbouring fix rather than the initialization path. Naming a file, symbol
  or line in the hook silences it, because that is the check being asked for. Both scans read the
  HOOK TEXT, not the command: the command line always contains `memory_engine.py`, which the
  evidence pattern reads as a named file, so scanning the whole thing silenced it on every input.
- `git-revparse-nudge.py` - `git rev-parse <ref>` without `--verify`. Given a ref it cannot
  resolve it prints the argument back verbatim and exits 0, so a comparison built on it succeeds
  against a string that was never a commit. The informational forms (`--show-toplevel`,
  `--abbrev-ref`, `--git-dir`) ask about the repository rather than a ref and are left alone - they
  are what you should run when you suspect the cwd is not the repo you think.
- `arbitrary-sleep-nudge.py` - a bare `sleep` of 60s or more outside a polling loop. A sleep INSIDE
  `until`/`while`/`for` is pacing the checks, which is waiting on the signal and is the right
  shape, so it is untouched however long. Short settle pauses are untouched too.

## [5.162.0] - 2026-08-09

### Changed

- `gated-prep-nudge.py` widened after probing the shipped hook for gaps. Three shapes slipped
  through and now have regression tests:
  - `gh pr create` is gated by this repo's commit gate, so a `--body-file` written beside it is
    lost exactly like a commit message. It was not in the gated-verb set.
  - An interpreter that writes through an API rather than a redirect - `python3 - <<PY ...
    open(f, "w") ... PY` or `python3 -c`. There is no `>` to match on, and it is the shape used
    constantly for the very job that gets lost: composing a commit message.
  The write scan reads heredoc BODIES while the verb scan still strips them. That asymmetry is
  deliberate: the write lives in the body, but prose must not be able to fake a verb.

Not escalated to a block. The fact behind this hook records six hits, all dated on or before
2026-08-02, which is when the nudge shipped - nothing has recurred since, so there is no evidence
for taking away a command that may be perfectly fine. Widening what it SEES is the change the
evidence supports.

## [5.161.1] - 2026-08-09

### Fixed

- `agents/baseline-probe.md` could not be spawned. It declared `tools: TodoWrite`, which is not a
  recognised tool name in this harness, so the list resolved to nothing and the dispatch was
  refused with "would be spawned with zero tools" - leaving `subagent-probe-capability-gate.py`
  denying work and naming a safe form that does not run. Now `tools: ReportFindings, Skill`, both
  observed in a real agent's tool set. The gate's test now asserts the shipped agent grants at
  least one KNOWN tool as well as none of the dangerous ones: safe is only half of it, the agent
  also has to be spawnable.

## [5.161.0] - 2026-08-09

### Changed

- `warn-inline-powershell.py` now names the safe form: the nudge points at `runps.sh`, which
  syntax-checks a .ps1 locally then scp's it and runs it with `-File`. The fact this guard covers
  reached recurrence 3 with the guard already installed, and named the reason - it described the
  failure without naming the wrapper that already exists, leaving its reader to hand-roll the fix.
- `warn-inline-powershell.py` also stops firing on heredoc BODIES. A heredoc that writes an example
  of the wrong form is data, not an instance of it; the guard was tripping on its own test fixtures.
- `block-masked-gate-exit.py` gains `reads_masked_status()`: a pipe into a truncating filter
  followed by a read of `$?`, with no recognised gate required. The existing detector needs a known
  gate name, which misses measuring a command's OWN exit code - measured, `tool verify | tail -5;
  echo "rc=$?"` reported rc=0 while the tool had correctly exited 1, so a working negative control
  read as broken. Advisory, not a block: measuring an exit code is legitimate, the mistake is
  reading the wrong one.
- `shell-prefix-selfref-guard.py` gains `substitutes_inside_text_arg()`, blocking backticks and
  `$(...)` inside a double-quoted argument to a prose-carrying flag (`-m`, `--hook`, `--title`,
  `--why`, ...). The shell runs the substitution before the program sees the string: a memory hook
  once wrapped `shutdown -r now` in backticks and the dev box ran it, surviving only because polkit
  refused. Scoped to prose flags on purpose - `$(...)` is legitimate nearly everywhere else, and a
  guard that blocks ordinary work gets disabled.

## [5.160.0] - 2026-08-09

### Added

- `subagent-probe-capability-gate.py` (PreToolUse on `Task|Agent`, first in the group): DENIES a
  dispatch whose own prompt declares it needs no tools ("answer from this message alone", "do not
  use any tools", "reply with text only") unless it uses an inert agent type. That instruction is
  prose, and prose does not bind a subagent - measured, a dispatch worded exactly that way explored
  the real tree, rewrote a stored fact, and committed to two git repositories while reporting only
  the text it was asked for. The declaration must OPEN a sentence, so prose that merely discusses
  tool use is untouched (its own negative test caught that false positive before it shipped).
- `agents/baseline-probe.md`: the inert type the gate names - `tools: TodoWrite`, so no Bash, no
  Write, no Edit, no Read. Excluding Write is NOT sufficient: probe-verified that `Explore` has no
  Write tool and still created a file with `echo BREACH > path`, so Bash alone is enough to mutate.
  An absent or EMPTY `tools:` list means UNRESTRICTED, so an inert agent must name a minimal
  non-empty list; a test asserts the shipped one grants none of the dangerous tools, by token
  rather than substring.

Note: agent definitions are read at session start, so a freshly installed type is only selectable
in a new session. The deny message says so.

## [5.159.0] - 2026-08-09

### Added

- `memory_engine add` now reads back the recurrence count a fact body records. When the body states
  a repeat of 2 or more, the add prints a `~ warning:` naming both escalation endpoints - a
  deterministic GUARD when a rule keeps being skipped, a JIG when the same multi-step work keeps
  being re-done by hand, and both when it is both. Advisory: the add still exits 0.
  `uuid_store.recurrence_count()` is the pure detector, matching only explicit markers
  (`recurrence: N`, `Nth occurrence`, the ordinal words, `hit N times`, `N recurrences`) and
  returning the highest, so a body that merely discusses something "recurring" cannot fire it.
  The count is the one durable "already written down, still happening" signal, and an `add` is the
  moment it is in hand; `meta-self-improve` step 6 previously relied on the author noticing a
  number inside prose they were editing for other reasons.

### Changed

- `meta-self-improve` step 6 documents the new advisory, so the skill and the engine name the same
  trigger. The ladder itself is unchanged: a subagent given the complete step 6 already reaches the
  jig endpoint, so no rule was added.

## [5.158.2] - 2026-08-07

### Fixed

- **`reformat-md-tables` hook**: the Bash fallback no longer descends into a repository checked
  out under the working directory. It finds files by mtime, and mtime says a file was written,
  never by whom, so a `git checkout`, `merge` or `clone` inside a vendored checkout restamped
  every file it touched and the hook read someone else's source as ours and restyled it. Measured:
  seven docs in a vendored `microsoft/openvmm` mirror carried alignment-only churn nobody made,
  unnoticed until `git merge --ff-only` refused to run against the local changes. Committing that
  churn would have been permanent divergence from upstream for a style upstream never adopted.
  Any directory below the working directory that holds its own `.git` is now pruned; the working
  directory's own repo stays in scope, and the declared-path Write/Edit route is unchanged. The
  walk moved from `rglob` to `os.walk` so the prune happens before descending rather than per file.

## [5.158.0] - 2026-08-06

### Added

- **`infra-windows-servicing`** (new): the false signals in Windows servicing and component-store
  repair. Scoped deliberately narrow - baseline testing showed a capable model already produces the
  repair procedure itself (`takeown` -> `icacls` -> `attrib -R` -> delete, in the right order, and
  it suggests `robocopy /MIR` as a faster bulk form), and already refuses to kill a quiet DISM job.
  What it gets wrong is the diagnosis, so the skill teaches only the signals that read as one thing
  and mean another: a clean `ScanHealth` treated as evidence an update should install, when disk
  headroom is a separate fault presenting identically (measured: 2 of 17 machines corrupt, the rest
  simply out of room); "Access is denied" on a delete that is the READ-ONLY ATTRIBUTE rather than an
  ACL, so `takeown`/`icacls` cannot fix it and each reports success while the operation keeps
  failing; a permission command succeeding while the operation still fails, which means the
  diagnosis is wrong rather than that a bigger pass is needed; `icacls /reset` on a `Windows.old`,
  which rewrites the LIVE installation's ACLs through the hard links an in-place upgrade creates
  (measured: stripped the SSH host-key ACEs, `no hostkeys available -- exiting`, machine off the
  network, console recovery); a SYSTEM scheduled task having LESS access than an elevated admin
  session (measured: 0 of 49 files as SYSTEM, 49 of 49 as admin); a quiet log read as a hang when
  DISM's `/LogPath` is per-invocation, so a phase handover looks identical to a freeze; and a
  duration quoted from a reference figure, when the same upgrade measured 1 hour on one machine and
  5h18m on another on the same host. Also covers `/eula accept` being required with `/quiet`
  (without it setup exits `0xC190010E` after ~30s and the code points nowhere), the documented
  unsupported-CPU waiver as distinct from the LabConfig bypasses, and choosing `RestoreHealth`
  (patches, needs each payload at its exact revision, fails `0x800F0915`) against an in-place
  upgrade (replaces the store wholesale).

## [5.154.0] - 2026-08-03

### Added

- **`process-review-enhance-code-quality`**: the interface-shape census now has to JUDGE before it
  cuts. The table told a review to count and the bullets told it to weigh the counts, but nothing
  told it to find out what a parameter is FOR before proposing to remove or relocate it - and a
  tramp rate cannot see the reasons that make removal a regression: a test seam, a production
  override, an unexercised variation point. Measured: given only counts, a review recommended
  folding two 94%-and-96%-forward-only parameters into an existing object across ~157 signatures,
  called it "close to codemod-able" and ranked it "do first", never asking what either was for.
  With the rule, the same scenario enumerates who supplies a non-default value first and rejects
  the ambient/delete option because it would force injecting tests onto patching a global.
  Also added: gather call-site evidence by PARSER, since the commonest parameter names (`key`,
  `value`, `id`, `name`, `type`, `index`, `data`, `compare`, `callback`, `handler`) collide with
  the language's own - a `key=` grep returned 20 sites of which every one in the project's code
  was Python's sort key; a high tramp rate does not select WHICH fix, and bundling a near-pure
  tramp into an object threads the same value through the same functions for ~zero parameters
  removed; a fix must beat the status quo on EVERY rubric dimension, not just the one that found
  it; and counting something and LEAVING it is a finished result, recorded with its counts so the
  next review does not re-derive them and answer differently.

## [5.153.0] - 2026-08-03

### Added

- **`process-agents-dispatching-parallel`** gains the two rules that a real parallel refactor
  proved missing, at the canonical source rather than copied into each consumer.
  PARTITION: the skill listed "shared state" only under *When NOT to Use*, an all-or-nothing
  framing, when the normal case is work that separates cleanly except for a few shared files (the
  enum module, the models module, a registry). It now requires assigning every file to exactly one
  agent, giving each its allow-list, telling it others are editing the tree concurrently, and
  having it REPORT a needed change in someone else's file rather than make it. Measured: three
  agents on one checkout produced a transient failure from a half-written sibling edit, and the
  last remaining error was found only because an agent refused to reach outside its set.
  VERIFY YOURSELF, AND THE WHOLE GATE: agents sample mid-flight (three reported 30, 1 and 5 type
  errors for the same tree minutes apart) and they run the cheap check - three truthfully reported
  "731 passed" while the type checker had 24 errors, since enum members compare equal to the
  strings the old call sites still passed.
  Also pins the return shape when results must be AGGREGATED: "expected output: summary" invites
  prose, and an agent answering "Findings reported above: 8 items across 4 files" obeys the skill
  while every finding is lost and the count makes the loss read as a result.

## [5.152.2] - 2026-08-03

### Fixed

- **repo-gate** `MIRRORED_SKILLS` pointed `compuse-vnc` at
  `apps/utils/vnc-remote-control/...`, but the repo directory is underscored
  (`vnc_remote_control`); only the skill directory inside it is hyphenated. The entry
  therefore resolved to nothing and the mirror check skipped that skill silently - the exact
  "an entry whose path no longer exists silently degrades to skipped forever" failure the
  twin-exists test was written to catch, which had been failing on it. The two copies turn
  out to be in sync, so nothing drifted while the check was dead. Verified by injecting a
  drift line into the twin and confirming the check reports it, then restoring the twin
  byte-identical: an "in sync" that could not have said otherwise would prove nothing.

## [5.152.1] - 2026-08-03

### Fixed

- **`coding-python-enforce-data-architecture-strict`** closes three gaps found while running it
  over a 15k-line package. The refactor step said "launch subagents in PARALLEL for each file",
  but this refactor is not per-file independent - the Enums land in `enums.py` and the models in
  `models.py`, so several agents reach for the same shared file. It now requires partitioning
  into NON-OVERLAPPING file sets with one owner per shared file, and telling each agent the
  explicit list it may touch plus that others are editing the repo concurrently. Measured: three
  parallel agents produced a transient failure from a half-written sibling edit.
  The refactor agents are now also required to run the TYPE CHECKER, not just the tests: a
  StrEnum member compares and hashes equal to its string value, so existing string-literal
  assertions stay green while the checker errors on the changed signature. Measured: three agents
  each reported "731 passed" while pyright had 24 errors. The orchestrator must re-run the gate
  itself, since agents sampling mid-flight disagree with each other.
  The analysis agents are now told to reply with JSON and nothing else, and are given the
  NOT-a-violation list (small local dicts, free-form envelopes, dynamically-keyed maps). An
  analyser that answered in prose lost all eight of its findings while citing a count that made
  the loss look like a result.

## [5.152.0] - 2026-08-03

### Added

- **`compuse-toolbox`** gains `winlog`, for reading a Windows-written log whose text `grep` cannot
  find or that `cat`s with spaces between the letters. PowerShell writes UTF-16 from `Tee-Object`
  but UTF-8 or ANSI from `Set-Content`, so a log created by one and appended to by the other is
  MIXED, with no BOM to announce it: nothing errors, `grep` simply finds nothing, and a wait loop
  keyed on a completion marker reports "not finished" for a run that finished. `winlog` decodes per
  segment, normalizes CRLF, and names a MIXED file on stderr so it gets fixed at the writer rather
  than worked around in every reader.
  `iconv -f UTF-16LE` is not an equivalent: measured on the real log it decoded the UTF-16 tail,
  exited 0, and silently turned the ASCII head into mojibake, losing the header and the line
  recording which account the task ran as. `file` reports such a log as plain `data`. 24 tests,
  including the original mixed artifact and a control asserting the naive decode really does miss
  the marker.

## [5.151.0] - 2026-08-03

### Added

- **`meta-self-improve`** chore ladder: registering a jig now requires a passing RETRIEVAL test of
  its index row, not just file + test + row. A green unit test says nothing about whether the row
  is findable, and a jig nobody finds gets hand-rolled again, which is the chore it was built to
  end. The method is RED first, one question per agent, whole index visible, and NONE stated as an
  acceptable answer: a batch of questions primes a 1:1 mapping and lets the agent disambiguate by
  comparing rows, and without the NONE sentence it picks the nearest row so the test cannot fail.
  Also records what makes a row retrievable (the user's noun rather than the mechanism, both jobs
  of a two-job tool, a real value in the usage column). Found by measurement: a row reading
  "capped resumable fetch" lost its own download case, with an isolated agent answering NONE and
  reaching for curl after reading "capped" as retries.

## [5.150.3] - 2026-08-03

### Changed

- **`infra-proxmox-bindsnap`** names the vetted pve-container builds (6.1.10 and 6.1.12 as of
  pve-bindsnap 1.2.0) while keeping the node's own journal line and the project's
  compatible-versions page as the authority, and points out that the snapshot checksum covers
  `AbstractConfig.pm` from `libpve-guest-common-perl`, so an upgrade of either package can move a
  node into TEST mode. Mirrored byte-for-byte (apart from the `name:` line) into the pve-bindsnap
  repo's own copy of the skill.

## [5.136.0] - 2026-08-02

### Changed

- **`git_state.py` ships once, in `compuse-toolbox`.** It was duplicated in `compuse-git`, which
  now references the owning skill's copy instead. Owner chosen by subject: `compuse-toolbox` exists
  to ship these six jigs and this is one of them, while `compuse-git` had only borrowed it.
  `compuse-git` now ships no Python at all, so its `scripts/` and `tests/` directories are gone
  rather than left holding an orphan conftest.

### Note

The previous release recorded these two copies as "already DRIFTED (15 differing lines)" and
deferred consolidating them as a which-behaviour-wins decision. That was wrong: comparing the two
ASTs with docstrings stripped shows the executable code is IDENTICAL, and all 15 lines are
docstrings or comments. The characterisation came from a line count rather than a diff.

Neither TEST file was a superset by name, so both were compared body-by-body instead of picked.
`compuse-git`'s apparently unique test proved byte-identical to the toolbox's under a different
name, and the toolbox additionally carries a `None`-branch regression - so nothing was lost. The
surviving copy absorbed what the deleted one did better: the usage block, the `find_repos`
docstring, and a clarifying test comment.

Duplicate `.py` basenames across the plugin drop from 6 to 4. The remainder are benign: vendored
`demos/` and `examples/` files the gate already excludes from test runs, plus per-directory
`conftest.py`.

## [5.135.0] - 2026-08-02

### Changed

- **`strip_typographic_tells.py` ships once, at `<plugin>/hooks/`, instead of twice.** It was
  duplicated byte-identically in `write-humanize-en` and `write-humanize-de` under one module name,
  so in a whole-plugin pytest run the German copy loaded first and the English tests exercised the
  German script - which is exactly how the previous release's code-span fix appeared to be missing
  while passing in isolation. Both skills now invoke the shared copy, whose `tell_chars` dependency
  is a sibling there rather than three levels up. The German test file was verified to be a strict
  subset (0 language-specific lines) before removal, so the ~54-test drop in the suite total is
  duplicate coverage going away, not coverage lost.
- **`repo-gate`'s comment no longer cites a collision that no longer exists.** It explains why the
  gate passes `--import-mode=importlib`, and named these two files as the example; it now names
  `test_git_state.py`, which still collides.

### Note

`git_state.py` is also shipped twice, by `compuse-git` and `compuse-toolbox`, but those copies have
already DRIFTED (15 differing lines), so consolidating them is a which-behaviour-wins decision
rather than a mechanical de-duplication. Left as-is and recorded here.

## [5.134.0] - 2026-08-01

### Fixed

- **`strip_typographic_tells.py` rewrote the deliberate examples it was told to leave alone.** The
  tell-sweep hook skips inline-code spans and fenced blocks; the strip script did not, so a file
  the sweep passed could still have its examples flattened by the script - which is how a
  curly-quote example in this repo was once turned into two identical halves. Both now share ONE
  definition of code, `tell_chars.transform_outside_code`, added beside the existing detector as
  its write-side twin. Two implementations of "what is code" drifting apart is what caused this, so
  the fix is a shared primitive rather than a second copy of the scanner.
- **The same script ships TWICE**, in `write-humanize-en` and `write-humanize-de`, byte-identical
  and under one module name. The English fix looked absent in the whole-plugin suite because in a
  full run the German copy loads first - so the English tests had been exercising the German
  script. Both are fixed and verified identical. The duplication and the module-name collision are
  recorded as an open design question: a test in one skill can silently exercise the other's copy.
- **write-humanize-de's claim became true rather than needing correction.** It already said the
  exact character survives both the hook and an accidental run; that was false before this fix.

## [5.133.0] - 2026-08-01

### Changed

Three skills gave two instructions for the same step. Each was decided on the verbatim text of both
sides rather than resolved by guess:

- **process-plan-writing-plans told a weak-tier reader both to delegate the self-review and never to
  delegate it.** Self-review is now never delegable at any tier, and the skill says why: it is a
  fresh-eyes pass over the plan YOU just wrote against the spec, and a subagent that never watched
  the plan take shape cannot know what was considered and rejected. Delegation remains available for
  the design/decomposition, which is what the capability clause was really for.
- **process-review-verification-before-completion told its verifier to "re-run the commands" and,
  one sentence later, that "command execution itself stays in the main agent".** The verifier runs
  them itself. A verifier handed the main agent's output inherits exactly the optimism the section
  opens by saying you cannot check in yourself - and this session kept proving it, since re-running
  is what exposed the wrong `curl -I` claim, the strip script's real behaviour, and rpyc's real
  `--host` default, each of which read fine on the page.
- **meta-dream-crosstree-deep demanded the `opus` tier for a decision its sibling defines as
  "opus-class OR ABOVE".** Read literally it told a session on a MORE capable tier to switch down.
  Both skills now carry the sibling's wording, including why opus is the floor.

A fourth reported conflict was investigated and dismissed: `meta-dream-nap` deferring the toolbox
pass is not a contradiction of `dream-core.md`, which says each dream mode states its delta - and
deferring IS nap's delta. Left unchanged.

## [5.132.0] - 2026-08-01

### Changed

- **A handoff to a skill that does not ship now says so: "(PLANNED, not yet shipped)".** Twelve rows
  across `web-frontend-responsive-ux`, `sec-appsec-web-baseline` and `meta-self-improve` named
  siblings a reader cannot install, so the tables read as coverage that exists. The rows are kept -
  they are the record of what each family is meant to cover, and the reserved names are still the
  names a future sibling gets built under - but a reader can now tell a plan from an installable
  skill, and a future audit will not re-report them as dangling.
- **Found the last four by a catalogue-wide sweep, not by a reviewer.** After fixing the six a
  reviewer had flagged in one skill, a regex over every SKILL.md for `<category>-<name>` references
  resolving to no shipped directory surfaced four more in two skills nobody had raised them
  against - two of which were false positives worth recording, since `git-footgun-guard` and
  `git-commit-branch-guard` are hooks rather than skills and do ship. Catalogue-wide result: 0
  unmarked references to non-shipping skills.

## [5.131.0] - 2026-08-01

### Added

- **meta-self-improve: retiring a local hook after lifting it into the plugin.** The escalation
  ladder already said a globally-useful guard belongs in the shared plugin's `hooks/`, and stopped
  there. Following it exactly left the local copy armed - and both copies fire, with the one that
  blocks FIRST winning, so a stale local hook silently overrides the newer plugin version while the
  plugin looks installed and current. Measured twice on one machine, once by a guard that blocked
  writing the documentation for its own rule. Removing the `settings.json` entry and retiring the
  file are both required, and coverage is proved by feeding both copies identical synthetic events
  before either is removed.

### Fixed

The last five skills from the isolated sweep, whose reports arrived after four batches had shipped:

- **process-ship-finishing-development-branch silently skipped worktree cleanup.** Step 6
  recomputed its git state from the current directory, but options 1 and 4 `cd` to the main root
  first - so it saw a normal repo, reported "no worktree to clean up", and exited happy while the
  worktree remained. It now reuses the values Step 2 captured and refuses to run without them. Step
  2 also captures `BRANCH`, which is what actually distinguishes the two worktree rows in its own
  menu table.
- **web-frontend-responsive-ux shipped the defect its own rule forbids**: a reference example
  called `setPointerCapture` on `pointerdown`, which SKILL.md says kills the thumbnail link's
  navigation. Capture now waits for the movement threshold. Its axe example gained the `--axe-url`
  its comment promised, its Lighthouse handoff no longer promises coverage the target skill
  disclaims, and six handoffs to unbuilt skills are marked PLANNED.
- **web-frontend-pagespeed claimed `curl -I` never shows `Content-Encoding`, "for every file".**
  Measured on three servers: with `--compressed` it does, on all of them.
- **write-humanize-en claimed code spans protect examples from an accidental strip.** They do not -
  running the strip script over a probe rewrote the em dash inside an inline span and inside a
  fenced block alike. They protect from the HOOK, which skips code; the script does not.
- **coding-rust froze two undated crate sizes** where the ratio carries the argument.

## [5.130.0] - 2026-08-01

### Fixed

The two vendored-documentation skills, where every sweep finding is now repaired rather than left
as upstream's problem. The divergence from upstream is deliberate and listed in each skill's review
artifact, so a future re-vendor is a merge rather than a copy.

- **coding-python-rpyc: eight wrong claims, each re-derived from the installed rpyc 6.0.2 rather
  than from the report.** The `--host` default was documented twice as `0.0.0.0`; the tool says
  `localhost`, so a reader expecting a remotely reachable server got a local-only one. `--mode`
  omitted `oneshot`. `propagate_KeyboardInterrupt_locally` was documented as the opposite of its
  actual default. `conn.builtin` (singular) contradicted every other page. The monkey-patch example
  used `rpyc.modules`, which does not exist - the CONNECTION has `.modules`, the package does not.
  The boilerplate ReadMe promised output after 30s from a client that sleeps 10. And three files
  disagreed about the Python floor, now reconciled on the distribution's declared `>=3.8`.
- **Its "Per-module API" row pointed at 11 files that contain no API content** - each is a
  ~121-byte stub reading "See source code". The row says so now and routes to `help()` on the
  installed package.
- **coding-python-textual: three shipped examples could not run** - two unparseable (nested quotes,
  an unterminated string) and one declaring a `CSS_PATH` whose `.tcss` lived in a different
  directory. The stylesheet now sits beside the app that declares it.
- **Every unresolved link in both skills now resolves** (13 targets: changelog, license, three
  never-vendored logo paths, and a dotted Python path that Markdown cannot resolve). Verified by a
  link sweep reporting 0 unresolved in each.

## [5.129.0] - 2026-08-01

### Fixed

Final batch from the isolated sweep, which is now complete: 66 skills reviewed, 22 clean.

- **sec-appsec-web-baseline graded a harmless `<link rel="canonical" href="http://...">` as SEVERE
  mixed content.** Its detector counted every `<link>` as a subresource load, but `rel` decides
  whether one fetches anything. Fixed with a non-loading rel set, deliberately fail-loud in the
  other direction: an absent or unrecognised `rel` still counts as loading, because a security
  check should over-report rather than silently drop. Five tests, the two pinning the defect
  observed failing first.
- **process-review-receiving-code-review's GitHub reply command silently did nothing.** `gh api`
  sends GET unless given a method or a field, so the documented
  `gh api .../comments/{id}/replies` read the thread instead of replying, and exited 0 while doing
  it. Now `-X POST ... -f body='...'`.
- **net-rotating-proxies promised freshness its tool does not provide.** Rule 1 said `live.txt` is
  re-derived each run and yesterday's proxy is never assumed good; `validate()` tests only
  `pool - live - bad`, so a live entry is never re-tested. The real mechanism - ban at use time,
  readers compute `live - bad` - is coherent and is now what the rule describes. Its `run` example
  also omitted the `--need` the prose says sizes the working set.
- **process-review-enhance-code-quality's overview contradicted its own RECONSIDER branch**,
  telling readers declined items are "never re-raised".

## [5.128.0] - 2026-08-01

### Fixed

Fourth batch from the isolated sweep, this one almost entirely in the meta-* skills, where the
defects are cross-references that point at the wrong file, wrong step, or wrong name:

- **meta-memory-settings claimed the CLI validates values; it did not.** `set dream_mode
  notarealvalue` exited 0 and stored the string, and `set nudges banana` silently became `False`.
  A realistic typo (`dream_mode of`) therefore produced a config that every reader falls back to a
  default on, forever and silently. Fixed in the CODE: enum knobs and bools now refuse an unknown
  value with exit 2 and a message naming the legal choices, with seven tests written first and
  observed failing. `skill_placement` is relabelled ADVISORY - no shipped code reads it.
- **meta-self-improve's upstream-propagation reference still taught `drop --index`** after
  `contrib_queue` gained `ship` and `--match` earlier the same day - an incomplete propagation of
  our own change, caught by the sweep. It also pointed at `update-config` as if this plugin shipped
  it; that is a Claude Code host skill.
- **meta-skill-writer stated the frontmatter cap as "1024 characters total"**, which reads as name
  plus description combined; the vendored spec in the same skill says 64 and 1024 separately. Three
  references to `python-use-modern-libraries` now use its shipped name.
- **meta-dream-crosstree's corroboration gate described a counter it does not use.** It promises
  ">= 2 distinct projects" while `note_promotion_candidate` counts one sighting per DREAM, so two
  projects corroborating in a single run count as one.
- **meta-dream-crosstree-deep pointed at the wrong steps three times**, including an instruction to
  run the sibling's steps 4-8 that would re-run the promotion gate its own step 3 just performed.
- **meta-dream-nap's "removal policy" named no home.**

## [5.127.0] - 2026-08-01

### Fixed

Third batch from the isolated sweep. Each defect was re-measured, not taken from the report:

- **compuse-git printed the wrong git error text**, and the more useful half is that the text is
  LOCALIZED - the first check came back in German. Detect the `rev-parse --short` footgun by exit
  code 128, never by grepping the message. The same wrong string lived in the shipped
  `git-footgun-guard` hook and its test; all three fixed together.
- **git-worktrees guarded against a condition git does not produce.** Step 0 claimed
  `GIT_DIR != GIT_COMMON` is "also true inside git submodules". Measured with the skill's own
  commands: plain submodule SAME, linked worktree DIFFER, normal checkout SAME.
- **docs-generate-schematics could not resolve its own dependency.** It claimed `httpx2` is handled
  by "PEP-723/uv" while neither script carried an inline metadata block and every documented
  invocation was plain `python3`. uv reads inline metadata only from the file it is handed.
- **devops-bmk carried a redundant flag with a false rationale** (`--reinstall` already implies
  `--refresh`, per uv's own help), a bootstrap that dropped the `uvx` prefix the rest of the skill
  requires, and a `git config ... .insteadOf ...` ending in a literal ellipsis.
- **compuse-vnc sent readers to a skill with no tunnelling content**; it now gives the `ssh -N -L`
  line itself.
- **compuse-toolbox's procsig over-claimed.** It said the tool never puts the match string on a
  command line; its own argv carries it. The guarantee is one-directional and now says so. The
  skill also advertised an "IPv6-first" edge case no tool there touches.
- **docs-md-table-formatting's GOOD example contradicted its own rule 1**, showing widths the
  shipped formatter would never emit. It is now that formatter's actual output.
- **infra-storage-check-zpools ran two Linux/systemd-only commands unconditionally** in a
  production-install block, two paragraphs after saying they are Linux/systemd-only.
- **compuse-ssh named a `runps.sh` wrapper that ships nowhere**; it now describes the wrapper to
  write and says none ships.

## [5.126.0] - 2026-08-01

### Fixed

Second batch from the isolated sweep, each verified by re-running the thing it describes:

- **coding-python-performance-review's cache experiment always said REJECT.** The template patched
  the target function in-process and then ran the suite in a SUBPROCESS, which never sees the
  patch, so `cache_info()` reported 0 hits and 0 misses and the verdict was fixed regardless of how
  good the cache would have been. Both runs are in-process now, with two regression tests proven
  red against the old template. Also: `setup_env.py` gained the PEP 723 block that makes the
  skill's "uv run fetches an isolated 3.13+ interpreter" claim true, the claims EXTRACTOR is no
  longer described as validating, and the hit-rate threshold matches the code.
- **coding-python-send-mail told readers to lift the 25 MiB attachment cap with
  `attachment_max_size_bytes=None`.** On the call that value is the sentinel for "no override", so
  the default still applied and the large send - the skill's headline use case - failed anyway.
  `None` disables the check only on the config object.
- **compuse-bash's mtime-sort command did not sort.** `find -printf '%T@ %p\n' | sort -zrn` mixes
  newline records with NUL-splitting sort, so the input passes through untouched - in the very row
  that teaches "sort by MTIME, never lexical order" for keeping the newest file.
- **A shipped Textual example did not parse** (unescaped nested quotes), in the file and in the
  guide page embedding it. `ast.parse` over every shipped `.py` now reports zero broken files
  across all 67 skills.
- **docs-convert-markitdown never extracted a year** from the `Author_Year_Title.pdf` pattern its
  own docstring advertises: `\b` does not fire between an underscore and a digit. Its seven tests
  had skipped in every environment lacking `markitdown`, including the documented CI set, so the
  defect shipped green - and the two tests disagreed with each other about the title, which nobody
  could see because neither ran.

## [5.125.0] - 2026-08-01

### Added

- **`meta-skill-audit`: auditing a catalogue of already-shipped skills, as distinct from authoring
  one.** There is no RED to watch fail when the skill already exists and readers already have it;
  what you are hunting is the claim that quietly stopped being true. Ships
  `scripts/audit_skills.py`, which copies the plugin into a clean room outside the knowledge tree
  and runs one reviewer per skill in parallel, plus a triage table pairing every finding class with
  its usual false positive. Two mechanics it encodes, both silent when wrong: isolate from the
  MEMORY STORE (the recall hook fires in every directory), and treat the PLUGIN as the install unit
  (judging reachability against one skill directory made 5 of the first 6 findings false).

### Fixed

Findings from the first isolated sweep, each verified against the real files or a live CLI before
acting, and mirrored to the tool repo's twin where one exists:

- **coding-input-sanitization taught a path-traversal defence that does not work.**
  `Path(base, name).resolve()` was said to stay under `base.resolve()`; both `..` and an absolute
  component escape it silently. Now resolves THEN checks containment with `is_relative_to`. Also
  stopped attributing Python's `shlex` to the Bash reference skill, which does not mention it.
- **coding-python-clean-architecture's canonical `Account` entity was mutable**, contradicting the
  same skill's "no mutable state in the domain is a non-negotiable". It is frozen now and its
  methods return a new entity. Its `UnitOfWork.run()` signature also omitted the `timeout`
  parameter that `port-contracts.md` - which the skill names as the source - defines, and
  `script-mode.md`'s flagship example returned an exit code its own table did not list.
- **coding-python-layered-config documented two CLI invocations that fail.** `env-prefix --slug`
  does not exist (the slug is positional), and `deploy --profile production` omits five required
  flags.
- **coding-python-gitignore showed `config-deploy` and `config-generate-examples` as bare runnable
  commands**; both exit 2 without their required option.
- **coding-python-new-public-library sent readers to two repos it never named**, and described a
  second console command without saying what it is.
- **coding-python-network-probe had drifted from its ipscout twin**, missing the `family=` argument
  on the three calls that return addresses, the `-4`/`-6` CLI flags, and the empty-result-is-not-an-
  error distinction. The marketplace was the stale side, which is the dangerous direction: the shop
  describing an API the tool has moved past.

## [5.124.0] - 2026-08-01

### Added

- **`contrib_queue.py ship` closes ONE delivered contribution, and `shipped` lists them.** The queue
  could only `drain` (all-or-nothing) or `drop` (a tombstone labelled rejected), so a delivered
  contribution had to be recorded as a rejection - which tells every later reader the work was not
  done. Both outcomes live in one tombstone file under an `outcome` field rather than two files,
  because the re-queue block reads the closed set and a second file is one more read for that check
  to forget; a forgotten one silently resurrects delivered work as a TODO. Records written before
  the field existed were all drops, so a missing `outcome` reads as rejected.
- **`--match TEXT` selects an entry by unique text instead of a position.** An index comes from a
  listing and SHIFTS under the previous close, so closing two entries by the indices of one listing
  hits the wrong second entry. Measured: an agent following the old instructions filed the delivered
  contribution as a drop and then destroyed a contribution that was meant to stay queued, stamping
  it with the other entry's reason. `--match` refuses on no match or an ambiguous match rather than
  guessing, and exactly one selector is required.

### Fixed

- **Three skills told you to `drain` "ONLY for the ones that actually shipped; leave one queued"** -
  an operation `drain` cannot perform, since it clears the whole queue. meta-self-improve,
  meta-dream-tree and meta-dream-crosstree now close each entry individually by outcome, select by
  `--match`, and reserve `drain` for a sweep where every entry shipped.
- **Re-queueing something already delivered no longer reports it as "rejected earlier".**

## [5.123.0] - 2026-08-01

### Changed

- **meta-skill-writer: baseline contamination arrives by two routes, and the documented fix closed
  only one.** The existing guidance covered the agent EXPLORING its way to the answer and
  prescribed a scratch dir outside the repo. That does nothing about the second route: a setup that
  injects retrieved context per prompt - a memory or recall hook, a RAG layer, an auto-loaded rules
  file - hands the rule under test to the baseline agent wherever it runs, because the injection is
  keyed to the PROMPT rather than the directory. The RED then passes on knowledge the skill never
  taught, silently, and the author reads a correct answer as proof there is no gap. The scratch-dir
  fix is now marked as closing route 1 only.
- **The tell is a citation you cannot find**, and it has two explanations that both void the
  baseline: grep the quote across the rules and memory corpus, and if it is there the environment
  injected it, if it is nowhere the model fabricated it. A fabricated rule that happens to match the
  author's intuition is not proof the gap is absent. Isolation is ranked, including that blanket
  switches which disable hooks and plugins wholesale (`--bare`, `CLAUDE_CONFIG_DIR`) do isolate it
  and take authentication with them, so neither actually runs. A baseline that cannot be isolated is
  recorded as not-evidence rather than counted as a pass.

## [5.122.0] - 2026-08-01

### Added

- **meta-skill-writer: diff GREEN against RED in BOTH directions - what appeared, and what
  disappeared.** A new step does not add to an agent's attention, it competes for it, so an edit
  that works can still cost a result the baseline produced. A richer GREEN is exactly what a
  net-negative edit looks like from the gained side alone: one correctness finding traded for four
  style findings is a worse review that ships as an improvement because the tally went up. A lost
  result is a REFACTOR requirement ranked by value rather than count.
- **Confirm a loss reproduces before restructuring.** One run per condition shows a mechanism is
  plausible, never that it is stable, so a single absence is a hypothesis with three live rivals:
  the edit displaced it, the run varied, or the baseline item was wrong. Re-run the same arm with
  everything else fixed; restructuring a skill around noise costs the version you already had.
- **A judgement that must follow a mechanical step becomes a required OUTPUT of that step.**
  Anything optional after a satisfying mechanical action gets skipped, and a rule stated as prose
  after a concrete table reads as commentary on the table - so the row reports its verdict, not
  only its count. Making the prose more emphatic does not bring the judgement back.

## [5.121.0] - 2026-08-01

### Added

- **meta-skill-writer: every test dispatch must ask its subagent for a `Skill gaps` section, and
  GREEN's list is REFACTOR input rather than a pass.** Compliance is the weakest thing a GREEN run
  reports: an agent that followed the new text may have guessed at three other things on the way
  and will not mention them unless asked, so a GREEN with nothing reported is indistinguishable
  from a GREEN that was never asked. This is the dominant failure for technique and reference
  skills, whose problem is rarely a violated rule and usually a silent or self-contradictory one.
  The paired rule is to require the evidence a run produces rather than its verdict - a mandated
  "no problems found" turns a silent miss into a confident all-clear.
- **A stopping condition for the REFACTOR loop, and quote-back verification.** Every reported gap
  is closed in the text or declined in the review artifact with a reason, so the exit condition is
  an empty UNDECIDED list rather than an empty list; a fix re-tests only the questions it touched.
  Each fix is verified by re-asking the contested question and requiring a direct quote of the
  governing text, or the word NONE - a paraphrase proves the model can reason to the answer, only
  a quote proves the skill says it.

## [5.120.0] - 2026-07-31

### Changed

- **The 500-char memory-hook cap now refuses instead of truncating.** `add_or_update_entry`
  raises `HookTooLong` before anything is written and the CLI prints `! refused:` and exits 1,
  where it used to word-boundary-truncate and print a warning. Six hooks had reached the store
  cut mid-sentence, one ending "Its 27", each of them an always-loaded pointer line that still
  reads like a complete instruction while its tail is gone - which misleads a reader more than
  an omission does. The warning printed at every one of those writes and was ignored every time,
  so the check had to become a gate. The surplus detail belongs in the body, which is read on
  demand and has no cap. The movers (`reconcile --rehome`, `migrate_memory`) pass
  `allow_over_cap_hook=True`: they carry text that is already stored, and refusing there would
  strand a legacy fact rather than improve it.
- **Corrected the cap's stated rationale.** The constant claimed 500 protected a pointer line
  from being wrapped by a markdown formatter and dropped on the next round-trip. It does not: a
  formatter that wraps at 80 columns splits a median-length hook just as surely as a 1000-char
  one. What the cap actually bounds is always-loaded context - every pointer line is loaded at
  every level of the cascade, in the session and again in every subagent that inherits it.

## [5.119.0] - 2026-07-31

### Added

- **A Bash guard against a prefix assignment referenced on its own command line.** `VAR=value cmd
  "$VAR"` passes an empty argument: the prefix binds the variable in the command's environment
  while the current shell expands `$VAR` first and has no such variable. Heredoc bodies are
  stripped, so documenting the footgun is not blocked by it.

## [5.118.0] - 2026-07-31

### Changed

- **coding-python-network-probe: IPv6 link-local zones and the many-to-one MAC/interface
  mapping.** Reaching a link-local address needs the RFC 4007 zone, with `interface.index` the
  only spelling that works on every platform. Examples moved to the reserved documentation
  ranges (RFC 5737, 3849, 7042, 2606); they had carried real addresses from the authoring
  machine.
- **meta-skill-writer: documentation values, and present-tense artifacts.** A skill and its
  review artifact describe what the skill does now, not how the session that wrote it went.

## [5.117.0] - 2026-07-31

### Changed

- **Enum formatting trap, marker wiring, BSD grep, and the mirror blockquote.** Skill corrections
  covering the 3.10/3.11 enum string-form flip, pytest markers that skip nothing until conftest
  wires them, BSD grep's missing GNU escapes, and the mirrored-skill self-install blockquote.

## [5.116.2] - 2026-07-31

### Fixed

- **infra-storage-check-zpools: corrected the `uvx @latest` claim.** Measured on a real host
  right after a release - the first `@latest` call still resolved the previous version and a
  call seconds later got the new one, because uv caches index metadata. "Re-resolves on every
  invocation" would have had a reader conclude a release is live instantly.

## [5.116.1] - 2026-07-31

### Fixed

- **infra-storage-check-zpools now states the requirement that actually decides whether the
  tool runs: OpenZFS 2.3+.** It previously led with an operating-system list, which is the
  wrong constraint - `zpool status -j --json-int` is what the whole package reads, and that
  JSON interface arrived in OpenZFS 2.3, so an older ZFS fails on every pool-touching
  subcommand no matter how well supported the platform is. Also corrected the platform notes:
  ZFS on macOS and Windows exists only as third-party ports (the Windows one still beta), and
  both lag upstream, so the version has to be checked rather than assumed.

## [5.116.0] - 2026-07-31

### Added

- **infra-storage-check-zpools: install, configure and operate `check_zpools`.** Covers monitoring
  ZFS pool health, capacity and errors, running scrubs, email alerting with deduplication, and the
  systemd daemon - from a cron entry, a script driving `--format json`, or as a Python library.
  Mirrored from the tool repo (`apps/utils/check_zpools`), which is now its own single-plugin
  marketplace. Written because the alternative agents reach for is scraping `zpool status` text and
  wrapping a scrub in a sleep loop with a hard timeout; that timeout is exactly the defect the
  package was built to remove, and it fires as a false alarm on any pool slower than the guess.

## [5.115.1] - 2026-07-31

### Changed

- **coding-python-network-probe re-synced: ipscout gained a macOS capture backend.** The skill now
  says all three platforms are supported, that every one needs elevation, and that the macOS device
  path has not been run on real hardware - the last of which matters more than the first, since an
  agent reading "supported" would otherwise trust it equally with Linux. Caught by the tool-repo
  mirror gate added in 5.115.0, on its first real outing.

## [5.115.0] - 2026-07-31

### Changed

- **coding-python-network-probe re-synced with its ipscout twin, which had gained a whole
  capability.** The mirror described eighteen subcommands and said nothing about `observe_dhcp`,
  two releases after ipscout shipped it - so an agent consulting this skill was told the DHCP
  observation surface did not exist. It now carries the full surface: `observe_dhcp`,
  `observe_dhcp_session`, `observe_dhcp_first_reachable`, `dhcp_capture_available`, the
  `observe-dhcp` subcommand, the Linux and Windows capture backends with their differing promises,
  and the ordering rule that the address a machine kept is the LAST offer rather than the first.
  The headline also stopped claiming "without admin rights" outright, since four operations now
  need elevation and one of them has no unprivileged alternative at all.

### Added

- **The mirror gate now guards the tool-repo side too, which is the side that actually drifts.**
  `repo-gate.py` already fired on every `git commit`/`git push` on the machine, but returned 0 in
  any repo that is not this one - so editing a mirrored skill in its OWN repo was unguarded, and
  the marketplace only found out if somebody happened to commit here afterwards. That asymmetry is
  why `coding-python-network-probe` drifted twice. A commit in a repo owning a mirrored skill now
  compares the pair and blocks on drift, naming which side to regenerate.

  A repo owning no mirrored skill stays silent, so the gate does not narrate everywhere. The
  "cannot compare" case is deliberately not a bare exit 0: with no marketplace checkout there is
  nothing to diff, and passing in silence is indistinguishable from passing because the pair is in
  sync, which would leave the guard permanently green and worthless. It passes - blocking would
  break anyone without the checkout - but says so through `additionalContext`, the one exit-0
  channel the model reads.

  Known limit, unchanged by this: `repo_root()` reads the cwd, so a cross-repo
  `git -C <other-repo> commit` is still judged against the wrong repo.

## [5.109.1] - 2026-07-30

### Changed

- **coding-python-layered-config reformatted to match what bmk produces.** The twin lives in a
  bmk-managed repo whose gate runs a whole-tree markdown format, so it rewrites that skill's code
  blocks on every run. Holding a different hand-formatting here would re-drift the pair after every
  `make` in `lib_layered_config`; the mirror now carries the formatted form. Content is identical.

## [5.109.0] - 2026-07-30

### Added

- **The mirror audit reports a twin the manifest does not list.** `MIRRORED_SKILLS` is
  hand-maintained, and a missing entry is invisible: it does not fail, it simply stops checking that
  pair. `coding-python-layered-config` had gone unchecked exactly that way and had drifted - the
  marketplace copy documented `read_config(default_file=...)` and the `lib_layered_config` twin did
  not. `--mirrors` now matches every repo skill's description against the marketplace catalog and
  names any pair the manifest is missing.

### Fixed

- **coding-python-layered-config added to the manifest, and its twin brought level.** The
  `default_file` parameter and the note that it is the only way to seed the `defaults` layer were
  in the marketplace copy only; verified against `core.py` before propagating.

## [5.108.1] - 2026-07-30

### Changed

- **devops-bmk: the two version rules for a repo that ships a skill.** bmk 3.14.0 raises
  `.claude-plugin/plugin.json` to the package version on bump/push/release and never lowers it, and
  refuses a release that edits `skills/` without moving that version. The skill described
  `make release` as tag-push-create, which would leave a user staring at a refusal the document
  never mentions.

## [5.108.0] - 2026-07-30

### Added

- **repo-gate `--mirror-of <tool-repo>`: the mirror check from the tool repo's side.** `--mirrors`
  audits all eight pairs and fails if any has drifted, which is right for a sweep and wrong for a
  release: one repo's release must not be blocked by another repo's drift. This mode resolves the
  pair belonging to the repo it is pointed at, locates the marketplace from the shared `public/`
  tree rather than requiring it as the working directory, and exits non-zero only for that pair. It
  passes with a reason when there is nothing to compare - no mirrored skill in that repo, no
  marketplace checkout, no `public/` tree - so a pipeline can run it in every repo unconditionally.

## [5.107.1] - 2026-07-30

### Fixed

- **coding-python-new-public-library: the description claimed the wrong Python floor.** It said CI
  runs "Python 3.9-3.14" where `bitranox_template_py_lib` declares `requires-python = ">=3.10"` and
  classifies 3.10 through 3.14. The description is what the skill router matches on, so a wrong
  version range there is a wrong trigger as well as a wrong fact. Found by the new mirror audit.

## [5.107.0] - 2026-07-30

### Added

- **repo-gate: the mirrored-skill drift check.** Eight skills ship both here and from the repo of
  the tool they document, and nothing compared the two copies - the coding-python-network-probe
  mirror had gone a release stale and was telling agents a default sweep refuses to run. The commit
  gate now checks the twin of any mirrored skill a change touches, and
  `repo-gate.py --mirrors` audits all eight. The `name:` field, the name echoed in the H1, and the
  tool repo's self-install blockquote are normalised away as conventional; anything else is
  reported with the differing lines. Local only, since the twins are sibling repos a CI clone does
  not have. Audit at the time of writing: six pairs in sync, two drifted
  (`coding-python-new-public-library` description, `devops-bmk` body).

## [5.106.1] - 2026-07-30

### Fixed

- **coding-python-network-probe: resynced with its ipscout twin.** The mirror still told an agent
  that `arp_scan()` with no argument "refuses a sweep wider than 4096 addresses ... Pass a narrower
  network", which ipscout stopped doing: a default sweep now covers the subnets that fit inside one
  sweep's 4096-address budget and reports the ones it skipped. An absence claim like that does not
  merely fail to help, it steers an agent away from a working default. Also adds the names a caller
  has to write and could not find in it - `ScanMethod`, `NeighbourState`, `IPScoutSweepError`,
  `SweepScope` - the `sweep_scope()` / `scope=` surface, the `skipped` field and bare-mode error
  shape in the JSON section, and the exit-code sentence (a malformed command line exits 2).

## [5.99.3] - 2026-07-25

### Changed

- `meta-skill-writer`: new "Ship tests for every script" rule - a bundled script must IMPORT in a
  bare environment. The gate/pytest does not provision PEP 723 deps (only `uv run` does), so guard
  third-party imports with a stdlib fallback and verify in a deps-free venv. Captures the 5.99.1
  orjson incident as durable authoring guidance.

## [5.99.2] - 2026-07-25

### Fixed

- `block-pgrep-self-match` guard: ignore data bodies. It scanned the whole command, so a commit
  that merely DISCUSSED the pattern (a `pkill -f` mention inside a heredoc commit-message body or a
  `-m` message) false-fired and blocked the commit. It now strips heredoc bodies and `-m`/`--message`
  values before scanning - both are data, never a real pgrep/pkill invocation. A real `pkill -f`
  elsewhere in the command still blocks.

## [5.99.1] - 2026-07-25

### Fixed

- `compuse-toolbox` `jsonl_grep` + `transcript_tail`: import cleanly without `orjson`. They hard-
  imported `orjson` (a PEP 723 dep only `uv run` provisions), so the CI gate's bare-env pytest
  failed collection with `ModuleNotFoundError: orjson`. Now they use `orjson` when present and fall
  back to stdlib `json` otherwise - fast path preserved, imports anywhere.

## [5.99.0] - 2026-07-25

### Added

- `compuse-toolbox` skill: a small set of tested Python jigs for recurring computer-use chores -
  `procsig` (self-match-proof `pgrep`/`pkill -f` replacement), `git_state`, `conflict_scan`,
  `ci_triage`, `jsonl_grep`, `transcript_tail`. The generic, host-agnostic subset of a personal
  toolbox, selected by transcript-frequency and recurring-error analysis. Each is a self-contained
  PEP 723 script with pytest tests; run with `uv run` and get arguments from `--help`.

### Changed

- `toolbox-nudge` hook: close the Write/Edit blind spot. It now scans the new text of
  `Write`/`Edit`/`MultiEdit` calls (the file content being authored) against the same
  signatures it already applied to `Bash` command lines, and is wired into the
  `Edit|Write|MultiEdit` PreToolUse matcher. A chore hand-rolled by writing a script file now
  gets the same "use the jig" nudge as a one-liner. Still non-blocking, still per-tool
  per-session dedup, still silent when the toolbox or the specific tool is absent.
- `toolbox-nudge` hook: three new signatures - `pkill`/`pgrep -f` (self-match risk) -> `procsig`,
  `ip neigh`/`getent hosts OVM-`/`tcpdump ... tap` -> `guestip`, and `/var/log/openvmm/` ->
  `ovmlog`. Each stays silent unless that jig is present in the local toolbox.
- `meta-self-improve`: new guard-to-chore-ladder crossover rule in section 6. A footgun that
  graduates to a blocking guard is no longer treated as "handled" when its safe form is still
  hand-rolled - the chore ladder also fires (propose a jig, then a nudge signature pointing the
  guard's victims at it). RED/GREEN verified with subagent scenarios.

## [5.98.3] - 2026-07-24

### Changed

- `coding-python-gitignore` and `coding-python-send-mail`: sync the mirrored skill
  bodies with their source repos (`igittigitt`, `btx_lib_mail`). Picks up the ruff
  code-block reformat (trailing-comment spacing) and a `send-mail` reference-section
  wording fix. The taxonomy-prefixed `name:` and the central-mirror omission of each
  repo's self-install blockquote are preserved as intended divergences.

## [5.96.2] - 2026-07-20

### Added

- `compuse-bash`: quick-reference row for capturing a `grep -c` count into a
  variable. `grep` exits 1 when it matches nothing, so the common "safe" idiom
  `n=$(grep -c PATTERN file || echo 0)` fires its fallback on a zero count and
  sets `n` to the two-line string `0\n0`, silently misformatting every
  comparison and report line built from it. `grep -c` already prints `0`, so
  the fallback is unnecessary: `n=$(grep -c PATTERN file 2>/dev/null); n=${n:-0}`.

## [5.95.2] - 2026-07-20

### Fixed

- `git-footgun-guard` no longer fires on text that merely MENTIONS
  `git rev-parse --short` with two revisions. It scanned the whole command
  string, so a heredoc BODY (writing a memory entry, doc, or commit message
  about the footgun) was judged as if it were a command - the guard blocked
  any attempt to document the very footgun it guards. Heredoc bodies are now
  stripped before analysis, and `rev-parse` must be the actual git
  subcommand, so `git commit -m "...git rev-parse --short A B..."` passes.
  Genuine breakage still blocks, including quoted operands
  (`rev-parse --short "$A" "$B"`) and a real invocation following a heredoc.

## [5.93.0] - 2026-07-19

### Added

- `docs-md-table-formatting`: new `tablekit.py` tool that round-trips a markdown table through JSON
  (`read` a table to `{headers, alignments, rows}`, edit the JSON, `render` it back fully aligned,
  or `replace` it in place in a file). Complements `reformat_tables.py` (which only re-aligns) for
  when you need to change a table's content without hand-padding cells. Stdlib only; ships with
  `tests/test_tablekit.py` (9 tests: parse, alignment, escaped-pipe and structural round-trip,
  ragged-row padding, in-place splice).

## [5.92.2] - 2026-07-19

### Changed

- `coding-python-new-public-library`: the scaffold steps now use the shipped
  `reset_git_history.sh` (clone, detach the template remote, rename, squash history) and warn that
  it force-pushes to the first remote it finds - so the template `origin` must be detached first,
  or it would rewrite the template's own history.

## [5.92.1] - 2026-07-19

### Changed

- `repo-gate.py`: the pre-commit gate now fires on `git push` as well as `git commit` and
  `gh pr create`. A change that reaches a push without the commit gate having run - a cross-repo
  `git -C` from another project, or generated docs regenerated between commit and push - is now
  caught locally instead of by a red CI run. The full check set (including the generated-docs
  sync tests) runs at the pre-publish moment.

## [5.92.0] - 2026-07-19

### Added

- `coding-python-new-public-library`: scaffold a new public Python library from the
  `bitranox_template_py_lib` template - clone and rename it, install it, use its rich-click CLI
  and library API, and develop and release it with bmk. Also flags that a repo which ships a
  skill is a plugin marketplace (protect its default branch, version the plugin on every change).

## [5.85.1] - 2026-07-17

### Fixed

- `memory_engine.py`: a slug-stable hook rewrite (`add --slug X --hook NEW` with no `--body`) now
  re-syncs the body's `description:` frontmatter to the new hook. Previously it updated only the
  pointer line, leaving the body description stale and desynced from the pointer.
- `self_improve_signals.py`: `altitude_chain` no longer treats a `.claude/` config dir (or its
  `worktrees/` git-worktree scaffolding) as a memory altitude, so `heal`/`scaffold` stop creating
  empty spurious pointer blocks inside them when run from a worktree path.
- `self_improve_signals.py`: `note_unknown_keywords` drops leaked identifiers (tool-use IDs
  `toolu_...` and long hex agent/session IDs) instead of queuing them as recall keywords.

## [5.59.0] - 2026-07-13

### Added

- `coding-python-layered-config`: install, use, and design layered application configuration
  with lib_layered_config - the Python API and the CLI, per-key provenance (which layer and
  file a setting came from), environment profiles, the environment-variable override rules,
  and the config paths on Linux, macOS, and Windows.
- `coding-python-use-modern-libraries`: added a row recommending `lib_layered_config` for
  layered / cross-platform application configuration (previously left unprescribed).

## [5.56.1] - 2026-07-10

### Fixed
- Memory engine: the ACTUAL trigger for the orphaned-entry bug (5.56.0 addressed the recovery side)
  was a `[` or `]` in a pointer's TITLE. The pointer line is a markdown link `[Title](mem:slug)`, and
  the parser's title group is `[^\]]*`, so a title like `... gets [dev] via ...` makes the whole line
  unparseable - `read_store` skips it and the next block round-trip drops it, orphaning the body. The
  pointer renderer now neutralizes `[`/`]` in the title (shown as `(dev)`; the body keeps the full
  detail) and any literal `<!--`/`-->` in the hook, so a bracketed title round-trips instead of
  vanishing. The 500-char hard cap from 5.56.0 stays as secondary protection.

## [5.56.0] - 2026-07-10

### Fixed
- Memory engine: recover "stale" orphaned entries instead of getting stuck on them. Root cause was
  a two-step trap: an over-long or formatter-mangled pointer line failed the block round-trip and was
  silently dropped on the next `heal`, leaving a central body with no pointer (a "dangling body");
  then `add` refused to re-create the slug (the body registers it) and `archive_entry` could not act
  (no pointer to drop), so the fact was invisible yet un-recreatable.
  - `add` now ADOPTS a dangling body (re-attaches a pointer) instead of raising `SlugCollision`, when
    no other level in the chain owns the slug. Re-capturing the same fact recovers it.
  - Hooks are now hard-capped at 500 chars (truncated at a word boundary; the body keeps the full
    detail) so a pointer line stays single-line and round-trips - preventing the orphaning.

### Added
- `reconcile_memory_index`: `find_dangling_bodies()` + a `--rehome` mode, and `--check` now reports
  dangling bodies (a central body no level points at) so they surface instead of silently piling up.

### Changed
- `process-agents-subagent-driven-development`: the Effort paragraph now carries the
  probe-verified, extremes-only effort policy with the tier-to-effort mapping (low for
  mechanical fan-out, inherit for the sonnet default, high-if-set for opus, xhigh/max for
  adversarial verify/synthesis), the working channels (Workflow opts.effort; agent-type
  frontmatter with its first-agents-dir restart caveat; no per-dispatch field), and the
  warning that broad low-pinning silently degrades occasional-depth tasks.

### Fixed
- Excluded dirs (home, the system temp dir, the filesystem root) can no longer become memory
  altitudes: `altitude_chain` returns empty for them and `ensure_level` refuses them, so an
  engine/heal call with a temp-dir cwd no longer scaffolds `/tmp/CLAUDE.md` and turns the whole
  temp dir into a fake knowledge tree (the anchor resolver always excluded them, but the
  chain fallback declared such a dir "its own tree top"). The workspace-hijack regression test
  now pins the real temp dir excluded alongside the fixture's fake one.

## [5.50.0] - 2026-07-06

### Changed
- `infra-proxmox` is now a lean hub (user decision): 6,474 -> 1,691 words inline. Kept: the
  auto-detect, safety, and cluster-size gate tables, the action-review protocol, response
  style, the troubleshooting triage, and the routing tables (now 5 rows richer: migration,
  cold start, node evacuation, pvesh, Docker-in-LXC). The near-verbatim command dumps live
  where they always also lived - the chapter files. Unique inline content was folded into its
  chapters BEFORE deletion: the Docker-in-LXC host-ops block, the node-maintenance runbook,
  and the config-file path map (the verify pass caught that appendix-c did not already carry
  it). Fable routing test 6/6.

### Fixed
- `gather_scan._workspace_root` now skips the excluded anchor dirs (HOME, system temp, root)
  like `resolve_anchor` does - a stray `CLAUDE.md` at `/tmp` no longer turns the whole temp
  dir into one workspace and pollutes recall.

## [5.49.1] - 2026-07-06

### Fixed
- CI red since the `cross_tree_search` knob landed: per-prompt recall never scanned
  `discovery_roots`, so a tree outside the workspace walk was unreachable even with the knob
  on. The test covering it passed only on the dev machine, by accident - a stale
  `/tmp/CLAUDE.md` from an old fixture widened the workspace walk to all of /tmp. Recall now
  walks `discovery_roots` (config union $HOME) exactly like the cross-tree gather; the tests
  now exercise the designed mechanism (configured root, derived $HOME root, and the walled-off
  case with a covering root so the wall does the blocking).

## [5.49.0] - 2026-07-06

### Added
- `docs-generate-schematics` (57th skill; user decision: extract, not drop): the AI
  schematic-generation scripts and their 28 behavioral tests now live in their own scope-true
  skill (OpenRouter image model + quality-review loop), with the K-Dense attribution carried
  over and a NOT-for clause routing conversion work back to markitdown. Discovery 3/3
  including the markitdown discrimination.

### Changed
- `docs-convert-markitdown` is conversion-only: the out-of-scope diagram generators, their
  tests, and fixtures moved out; README/catalog count now 57.

## [5.48.0] - 2026-07-06

### Added
- Pressure-tested rationalization tables, built from REAL baseline failures per the skill-writer
  Iron Law:
  - `process-agents-subagent-driven-development`: a baseline subject substituted self-review for
    the reviewer dispatch and took "zero-risk" one-liners inline - its verbatim excuses became
    the table; the GREEN re-run of the broken scenario passed.
  - `coding-python-enforce-data-architecture-strict`: a corrected forced-choice baseline produced
    genuine 2/2 capitulation ("an explicit, reviewed scope decision", "sequencing, not
    skipping"); the table counters them, a REFACTOR round added the ask-the-human row for the
    DoD-vs-deadline trade, and the retest chose surface-and-ask.
- Emoji policy enforced (user decision): heavy verdict emoji (U+2705/U+274C/U+2714/U+2717/U+26A0
  + the U+FE0F selector) are now in the canonical tell set; 7 skill files swept to ASCII
  OK/NO/WARN markers; the humanize strip script maps the class to the same markers (inverse of
  the detector); repo-wide scan clean outside the humanize skills' intentional examples.

## [5.47.0] - 2026-07-06

### Added
- Plan executions now ENFORCE subagent model pinning: `subagent-model-gate.py` (renamed from
  `warn-unpinned-subagent-model.py`) DENIES any `Task`/`Agent` dispatch without an explicit
  `model` while a `plan-execution` receipt is armed (fork stays exempt); outside an armed plan
  it keeps warning. The plan-execution skills (subagent-driven-development, plan-executor,
  dispatching-parallel) arm the gate at their start and disarm on completion
  (`skill_receipt.py` gains an `end` command).
- Effort guidance: a dispatch has no per-call reasoning-effort field - effort rides the
  agent-type definition or a Workflow `agent()` call, so choosing the tier (plus the right
  agent type) is the effort decision; the skills and the gate message now say so.

## [5.46.0] - 2026-07-06

### Added
- Repo gate: the CSO lint now rejects block-scalar (`>-`/`|`) and quoted frontmatter
  descriptions with a precise message - the defect class the full roster review found most
  often (9 skills) cannot recur.

### Changed
- Roster review COMPLETE: all 56 skills opus-reviewed and fable-verified across 5 waves
  (5.45.1-5.45.4 + this release); final scripted snapshot reports zero compliance flags.
  The light pass confirmed the 9 recently rebuilt meta skills compliant without changes,
  including an exact knob-table-vs-DEFAULT_CONFIG match.

## [5.45.4] - 2026-07-06

### Fixed
- Skill-roster review, wave 4 (14 skills: compuse-*, files-edit-*, git-worktrees, docs, singles;
  opus-reviewed, fable-verified, discovery 4/4): 13 changed, 1 compliant as-is (compuse-bash).
  - `marketing-rory`: the REQUIRED humanize step named skills that do not exist (bare
    humanize-en/-de) - now resolves; stale routing anecdotes and a fabricated talk count
    removed.
  - `compuse-git`: the CI-token section's manual example mixed two incompatible secret
    schemes (copy-paste would build a broken double-@ URL) - reconciled.
  - `compuse-ssh`: auth/host-key triggers added to the description (40% of the body was
    undiscoverable).
  - files-edit family aligned: toml description de-quoted, sibling cross-refs added to
    json/xml/yml, json documents ensure_ascii=False, xml example variable renamed.
  - `git-worktrees` + `meta-adopting-external-skills`: workflow-summary description tails
    dropped (CSO shortcut trap); the adoption helper now emits house-style attribution and is
    invoked via python3 + full path.
  - `net-rotating-proxies`: explicit lawful-use scope note added.
  - `web-frontend-responsive-ux`: missing sibling test added; description de-quoted (also
    sec-appsec-web-baseline).
  - `docs-md-table-formatting`: overview now credits the auto-realign hook; bulk usage takes
    an explicit directory (cwd trap removed).

## [5.45.3] - 2026-07-06

### Fixed
- Skill-roster review, wave 3 (12 process-* skills; opus-reviewed, fable-verified, discovery
  6/6): 11 changed, 1 compliant as-is (test-design).
  - Attribution: 12 skills derived from the Obra Superpowers plugin (MIT) now carry the credit
    line and a THIRD_PARTY_NOTICES.md entry (previously only 2 of 14 did) - the MIT notice now
    travels with every adapted copy.
  - Descriptions rewritten triggers-only where the tail summarized the skill's own workflow
    (verification-before-completion, ship-finishing-development-branch,
    receiving-code-review, requesting-code-review) or lacked its core keywords
    (dispatching-parallel had no parallel/dispatch/fan-out terms at all).
  - `process-review-receiving-code-review` no longer promotes the banned "Good catch" opener
    as a good example; `process-review-enhance-code-quality` no longer instructs silently
    auto-creating a CLAUDE.md; `process-debug-systematic` sheds 4 leftover authoring
    scaffolding files; placeholder syntax in requesting-code-review matches its template.
  - Non-ASCII check/cross glyphs outside the allowed set swapped to ASCII OK/NO markers in the
    flagged skills.

## [5.45.2] - 2026-07-06

### Fixed
- Skill-roster review, wave 2 (12 coding-* skills; opus-reviewed, fable-verified, discovery
  5/5): 9 changed, 3 compliant as-is (input-sanitization, resilience, textual).
  - Descriptions normalized to trigger-first single-line plain scalars: rpyc, uv,
    performance-review, rust (triggers-only rewrite), use-modern-libraries (keyword fold).
  - Factual corrections: `coding-bash-reference` (bash has no `0b` literal; here-string
    newline example rewritten - `read` strips the delimiter; broken cross-ref repaired);
    `coding-python-enforce-data-architecture-strict` (StrEnum for string-on-the-wire enums -
    the old IntEnum doctrine broke its own boundary-parsing example; the STEP D grep loop
    could never terminate).
  - Pipeline completeness: `coding-python-performance-review` now carries its unbounded-memory
    findings through merge, severity, and presentation.
  - Hub hygiene: Read-tool instructions and routing-row coverage/accuracy fixes in
    bash-clean-architecture, python-clean-architecture, rpyc (about.md row), uv (wrong HF row).

## [5.45.1] - 2026-07-06

### Fixed
- Skill-roster review, wave 1 (9 skills; opus-reviewed, fable-verified, discovery-tested 6/6):
  - Trigger-first single-line descriptions replace YAML block scalars / what-it-does summaries in
    `devops-bmk`, `infra-proxmox`, `infra-proxmox-bindsnap`, `write-humanize-en`,
    `write-humanize-de` (plus 6 umlaut spellings), and a keyword-enriched description for
    `process-agents-subagent-driven-development`.
  - `process-agents-subagent-driven-development`: 4 broken cross-references repaired; the
    `.gitattributes` LF pin for its helper scripts pointed at a pre-rename path (dead on Windows
    clones) - fixed; the bash helper scripts are now tested Python
    (`task_brief.py`, `review_package.py`, `sdd_workspace.py`, 16 behavioral tests) with a
    hardened commit-existence check.
  - `docs-convert-markitdown`: unsupported frontmatter keys removed; verified upstream
    attribution added (K-Dense-AI/claude-scientific-skills, MIT) to SKILL.md and
    THIRD_PARTY_NOTICES.md; 44 non-ASCII glyphs swept from scripts/references; reference-files
    routing table added; version-migration narrative rewritten as current-state API notes.
  - `compuse-vnc`: click-text OCR-failure pixel fallback documented; stale H1 fixed.
  - `infra-proxmox`: `ch19-cli-tools.md` routing row added; orphaned duplicate `onaction.md`
    removed.
  - `coding-python-gitignore`: reviewed compliant, no changes (mirror divergences are
    intentional).

## [5.45.0] - 2026-07-06

### Removed
- The `~/.claude/.bitranox-dream-off` / `.bitranox-dream-auto` sentinel files. The `dream_mode`
  knob in `~/.claude/.bitranox-memory.json` (set via `/bitranox:meta-memory-settings`) is the
  single mechanism; the sentinels are no longer read anywhere. If you relied on one without a
  config file, set the knob once: `dream_mode off` (or `auto`).

## [5.44.1] - 2026-07-06

### Fixed
- `meta-memory-settings`: the knob table now documents `skill_placement` (default `lowest`);
  the config has 9 knobs and the skill listed 8. Retrieval-tested (RED/GREEN).

## [5.44.0] - 2026-07-06

### Added
- `hooks/build_skill_docs.py`: generates `docs/skills.md` - the skill catalog grouped by taxonomy
  category with each skill's trigger-first description - from the skills' own frontmatter.
  `--check` sync mode is wired into the pytest suite, so the catalog cannot go stale.
- Docs restructured into chapters: `docs/installation.md`, `docs/setup.md`, `docs/usage.md`,
  `docs/architecture.md`, `docs/reference.md` (every knob, sentinel file, env var, CLI command,
  and quirk), plus the generated `docs/skills.md`.
- Sync tests assert the README's stated skill count and the reference chapter's knob table match
  the shipped code.

### Changed
- `README.md`: rewritten as a short introduction plus the chapter table.
- `docs/concepts.md` replaces `docs/self-learning-memory.md`: the plain-language ideas chapter,
  covering the three-rung dream ladder (nap / tree / crosstree).
- `ai-transparency.md`: rewritten in present tense against the current verification surface
  (test suites, repository gate, sync tests, the dream acceptance harness).

## [5.43.1] - 2026-07-06

### Changed
- meta-dream-nap live acceptance MET: two consecutive runs, both all-hard (incl. the sibling
  byte-identity assertion) + 3/3 chain-internal judgment, ~2.3x faster than the full dream on the
  fixture. The dream family (nap/tree/crosstree) is fully acceptance-tested; the self-learning
  restructure is complete.

## [5.43.0] - 2026-07-06

### Added
- NEW skill meta-dream-nap: the QUICK, chain-only consolidation (cwd -> ancestors -> anchor;
  siblings and other trees untouched by design) for compaction moments and signal-heavy sessions -
  minutes, not tens of minutes; ends with an explicit deferred-to-the-full-dream list. The
  PostCompact nudge now points here (a due FULL consolidation stays the tree dream's job).
- ANTI-DRIFT for the dream family (user-directed): references/dream-core.md single-sources the
  shared semantics (scope ladder, mode knob, capture-first, backup+manifest, dedup, THE routing
  prompt, verification contract, tier note) - the skills carry only scope deltas; a CONTRACT TEST
  asserts the invariants (scope rungs stated, core referenced, family literals exactly once).
  The acceptance harness became a PARITY MATRIX: --profile nap|dream|global assert the same basic
  functions with scope-inverted reach (nap: sibling branches byte-untouched).

### Changed
- Dream skills RENAMED to their true scopes (user decision): meta-dream-project ->
  meta-dream-tree, meta-dream-global -> meta-dream-crosstree, meta-dream-global-deep ->
  meta-dream-crosstree-deep. Consistent with the tree vocabulary (cross_tree_search, tree-top,
  TREE: labels); legacy names remain description triggers so old habits still route; every
  cross-reference swept in the same change; trigger map rebuilt (56 skills).

## [5.42.7] - 2026-07-06

### Changed
- Self-learning restructure COMPLETE: the dream acceptance bar is met (planted-fixture runs 3+4
  on the tree-wide-fixed skill both scored all-hard + 6/6 judgment, two consecutive; run history
  6/6, 3/6-REFACTOR, 6/6, 6/6) and the roster-trim equivalence closed 3/3 with no revert.
  Review artifacts updated with the verdicts.

## [5.42.6] - 2026-07-06

### Changed
- Model tiers updated for the Claude 5 family (user-directed): Concrete tiers gains `fable`
  (Mythos-class above opus; premium-priced, paid-API-credits only - opus remains the
  universally-available deep default). "The session model is fixed" now documents that a
  user-driven /model switch PRESERVES the conversation, so offering one is legitimate in BOTH
  directions: UP for capability (below opus-class before a deep inline judgment) and DOWN for
  cost (a fable session facing routine work). The inline tier note is restored explicitly in
  meta-dream-project step 5 (it was carried only by cross-reference since the C3 rewrite) and
  extended in meta-dream-global.

## [5.42.5] - 2026-07-06

### Fixed
- meta-dream-project: chain-vs-tree ambiguity closed (found by the planted-fixture acceptance -
  run 1 scored 5/5+6/6, run 2 read the scope as the cwd's ancestor chain and left the SIBLING
  project's duplicate, task-state, and the sibling department's empty descriptor untouched,
  scoring 3/6). Steps 0b/3/4/7 now state TREE-WIDE explicitly (every pointer-block level under
  the anchor, siblings included) plus a common-mistakes entry naming the chain-only shortcut.

## [5.42.4] - 2026-07-06

### Changed
- meta-using-bitranox-skills roster trimmed to categories + exemplars (skills-half C5b): the
  injected available-skills list is the stated source of truth. Pre-trim equivalence baseline
  3/3; the post-trim probes after the next update gate a revert.

## [5.42.3] - 2026-07-06

### Changed
- Contradiction rule corrected (user directive): memory-vs-CLAUDE.md contradictions resolve by
  GROUND TRUTH, not channel authority - a CLAUDE.md can be outdated too. Verify against the actual
  state (code/files/system/git history); correct whichever side the evidence shows is wrong
  (CLAUDE.md fixes stay propose-first); unresolvable -> ask the user. Both sites in
  meta-dream-project's dream-passes.md updated (the old rule blindly preferred CLAUDE.md).

## [5.42.2] - 2026-07-06

### Changed
- meta-using-bitranox-skills roster trimmed to categories + exemplars (skills-half C5b; the C5a
  gate relaxation is installed, so the trim can land): the injected available-skills list is the
  stated source of truth. Pre-trim equivalence baseline 3/3; the post-trim probes gate a revert
  after the next update.

## [5.42.1] - 2026-07-06

### Changed
- meta-dream-global (+deep) consistency patch (skills-half C6): "the global layer" -> "the tree's
  top" vocabulary throughout; independent-knowledge-trees framing (the global dream is the ONLY
  dream whose territory spans trees; discovery over discovery_roots via tree-top /
  ensure-all-trees); both descriptions rewritten trigger-first (the new CSO lint enforced it).
  Trigger map rebuilt.

## [5.42.0] - 2026-07-06

### Changed
- meta-using-bitranox-skills roster trimmed to category names + exemplars (skills-half C5): the
  injected available-skills list is the stated source of truth, so the ~40-name enumeration (a
  second list to keep in sync) is gone; repo-gate's check_skills_index relaxed to one direction
  (listed names must exist; completeness no longer forced). Pre-trim equivalence baseline 3/3
  (files-edit-yml, compuse-bash, write-humanize-en); the SAME probes re-run after the next
  marketplace update gate a revert. meta-memory-settings: discovery_roots row names its
  multi-tree consumers.

## [5.41.0] - 2026-07-06

### Changed
- meta-collect-knowledge rewritten (skills-half C4): per-tree candidate grouping (`TREE: <top>`
  headers; native tier labeled machine-local), the cross_tree_search wall honored with an explicit
  `--cross-tree` override, cross-tree import ALWAYS a labeled copy (`gathered-cross-tree:<top>`
  provenance; never a reference), deliverables checklist + rationalization table. gather_scan.py
  legacy dual-read stripped (slug store only; defensive dot-dir filter - pathlib glob matches
  dotfiles), cross-tree discovery widened over discovery_roots. The two long-standing
  environmental discover_claude_md test failures fixed at the root (fixtures hermetic: workspace
  inside the fake HOME so the ancestor walk cannot leak into the real /tmp). Full skill-writer
  discipline: RED (4 drift points), GREEN + pressure (blind-seed and cross-tree-reference
  temptations resisted), receipt + committed checklist artifact. 19 tests green; hooks 513 green
  (the map-sync test caught the description change - rebuilt).

## [5.40.0] - 2026-07-06

### Added
- SKILL-USAGE ENFORCEMENT (the "loaded but not executed" fix), three deterministic layers:
  1. repo-gate: a changed `skills/*/SKILL.md` requires a co-changed, fully-checked
     `.skillwriter/checklist-*.md` review artifact (local pre-commit), and every changed skill
     description must be trigger-first with derivable keywords (CSO lint, also in CI).
  2. skill-edit-guard v2: SKILL.md edits are allowed by a session RECEIPT that only
     meta-skill-writer's step 0 issues (`skill_receipt.py`, 8h TTL) - entering the procedure is
     provable; the launch-env bypass remains for emergencies.
  3. skill-router (UserPromptSubmit): matches each prompt against `skill_triggers.json` - DERIVED
     from all 55 skills' own trigger-first descriptions by `build_skill_triggers.py` (future
     skills covered by construction; a sync test fails when descriptions change without a
     rebuild) - and injects a pointed one-line nudge (>=2 keyword hits, max 2 skills, once per
     session). Router nudges; guards enforce.
- meta-skill-writer step 0: issue the session receipt; marketplace review-artifact requirement
  documented (mechanics in CONTRIBUTING). Retroactive checklist artifacts committed for the C1-C3
  reviews.

### Fixed
- Stale altitude scaffolding cleaned: 6 empty repo-internal CLAUDE.md/CLAUDE.local.md files below
  the repo root (old BITRANOX-UUID-INDEX fences) plus one empty project block deleted; zero
  old-fence residue tree-wide. Load-bearing chain markers kept.

## [5.39.2] - 2026-07-06

### Fixed
- Skill-writer checklist review over the C1-C3 rewrites (user-directed): meta-dream-project's
  description rewritten to triggers-only ("Use when...", no workflow summary - the CSO rule);
  REQUIRED BACKGROUND markers on the memory-backend.md cross-references in both rewritten skills;
  frontmatter/link/budget checks green; retroactive security scan of the shipped diffs clean.
  Discoverability probe queued for after the next marketplace update.

## [5.39.1] - 2026-07-06

### Changed
- meta-self-improve + meta-dream-project gain the anti-deviation scaffolding the rewrites lacked
  (user-flagged): a DELIVERABLES checklist per run ("an ended run missing any box is not done")
  and a pressure-tested RATIONALIZATIONS table each. Six combined-pressure subagent scenarios
  (skip-capture under time cutoff, reconciliation grep-shortcut under exhaustion, pinned +
  low-confidence moves under authority, append-vs-update under sunk cost, capture-altitude under
  "obviously universal", bare-hook under time) ran against the rewritten skills: 6/6 complied,
  each quoting the anti-rationalization prose; the scenarios' excuses are now the tables' rows.
  Routing-table coverage/accuracy checks pass on both hubs.

## [5.39.0] - 2026-07-06

### Changed
- meta-dream-project rewritten (skills-half C3, the centerpiece): PLACEMENT replaces "promote" -
  every unpinned entry routes through a fixed routing prompt (LEVEL | CONFIDENCE | WHY) against
  the per-level scope-descriptor ladder (fixed template: WHAT/STACK/CHILDREN/PLACE-HERE/
  PLACE-ELSEWHERE, freshness-gated synthesis), applied up AND down via engine move under one
  propose-diff; a voice + FIRING check pass (does the hook name the situations its body applies
  to?); backup + order-independent manifest with a post-dream diff; pinned entries exempt without
  explicit approval; multi-tree aware (another tree is never touched). Behavioral passes moved to
  references/dream-passes.md (CLAUDE.md reconciliation kept near-verbatim; demotion pass subsumed
  by placement). Dead meta-dream-projectB2.md fragment deleted.

### Added
- Dream acceptance harness: tests/fixture_builder.py plants a deterministic two-tree fixture
  (DUP, MIS-HIGH, MIS-LOW, OBS, TASK, VOICE, PIN, SCOPE, XTREE control); tests/fixture_asserter.py
  checks a real dream run (hard: XTREE/PIN/VOICE-ID/RECONCILE/NO-LOSS; judgment: 6 cases; bar =
  all hard + >=5/6 on two consecutive runs); procedure in tests/README-acceptance.md; harness
  unit-tested (9 tests). RED/GREEN verified via pinned-tier subagents.

## [5.38.0] - 2026-07-06

### Changed
- meta-self-improve rewritten as a capture-procedure hub + two reference files (skills-half C2).
  `references/memory-backend.md` is now THE canonical storage spec: knowledge trees/anchors, the
  slug-store grammar (mem: links, pinned-first render), the trigger-first hook spec, the framed
  body shape (frontmatter + Why/How-to-apply), the two tiers + explicit capture flow (hooks never
  write memory; capture at project level; re-leveling is the dream's move), the three delivery
  paths (+ cross_tree_search, MCP=search-only), and the engine command table with the fail-loud
  contract (BITRANOX_RUN_PYTHON_STRICT=1, required success lines).
  `references/upstream-propagation.md` carries the shared-artifact PR loop. RED/GREEN verified:
  the old skill taught the retired uuid-sharded model with no hook/body specs; against the new
  files a pinned-tier subagent answered the format questions correctly and produced a compliant
  capture end to end.

## [5.37.1] - 2026-07-06

### Fixed
- meta-skill-writer "Persisting durable state" section rewritten to the CURRENT memory model
  (it taught the retired `.claude-bx-selflearning/` + `@import` layout): per-altitude pointer
  block in CLAUDE.local.md (trigger-first `mem:<slug>` lines) + central framed bodies at
  `<anchor>/.claude-memory/facts/<slug>.md`, engine-only writes, MCP = search-only.
  RED/GREEN verified with pinned-tier subagents (baseline taught the retired paths; fixed
  section teaches the live model). Skills-half C1.

## [5.37.0] - 2026-07-05

### Added
- AUTHENTIC BODY SHAPE (probe-backed, ~5x mid-reasoning application lift): the engine now frames
  every fact body as a native memory entry - frontmatter (name/description/metadata.type derived
  from the pointer line) ahead of the prose; already-framed bodies pass through. New
  `backfill_body_frontmatter.py` retrofits the frame onto existing bodies (dry-run default,
  prose never touched, idempotent).
- TRIGGER-FIRST hook lint (advisory): `add` warns when a hook does not lead with WHEN it applies
  ('When <situation>, <directive>') - a trigger-less hook does not fire during reasoning
  (probe-verified: trigger-first hooks drove a body read in 100% of runs).
- `add --slug`: target an existing identity explicitly, so a title can be sharpened without
  minting a new entry.

## [5.36.1] - 2026-07-05

### Fixed
- `upsert_pointer_block` now collapses EVERY managed block (both fence generations) into the one
  canonical block instead of replacing only the first: an old-plugin session's heal could scaffold
  a second, empty legacy-fenced block next to the migrated one, and the writer skipped it forever
  (skip-fast heal then judged the file canonical). Pointers from all blocks are unioned; found and
  repaired live on two levels of the maintainer tree. Regression tests.

## [5.36.0] - 2026-07-05

### Added
- `cross_tree_search` config knob (default `true`): may the per-prompt recall hook scan OTHER
  knowledge trees? `false` walls recall into the current tree (its projects + tree top; the
  machine-local native tier counts as outside) - cross-tree knowledge then moves only via the
  explicit paths (meta-collect-knowledge import, dream-global). Born from a measured finding:
  the machine-global scan injected another tree's CLAUDE.md excerpts into an unrelated tree's
  session (~8-20KB/prompt). Settings CLI + knob table updated; probe report:
  `.plan/probe-voice-and-authenticity-20260705.md`.

## [5.35.0] - 2026-07-05

### Changed
- Engine-half residue: the every-session heal is now SKIP-FAST (a read-only `_level_needs_heal`
  probe first; a healthy chain takes no lock and writes nothing) and its orphan check is
  pointer-parse + stat only (bodies are never opened). `migrate_memory` receipts move to the live
  store (`<anchor>/.claude-memory/state/migration-receipts/<proj>.json`, legacy location still
  read); its gitignore safety covers BOTH store dirs (`.claude-memory/` + the legacy one) and the
  prose is de-legacied. `gather_scan`'s legacy dual-read carries a `# LEGACY-RETIRE:` marker tying
  its removal to the skills-half legacy retirement.

## [5.34.0] - 2026-07-05

### Added
- Multi-tree support: a machine can carry several INDEPENDENT knowledge trees (own top CLAUDE.md +
  own `.claude-memory` store each; they share nothing). `sig.find_claude_md_dirs(roots)` (prunes
  vendor/hidden/backup/store dirs + ~/.claude; never follows symlinks) + `sig.tree_groups` (groups
  by each dir's resolved anchor). Engine `ensure-all-trees [--roots ...] [--apply]` scaffolds every
  member chain of every discovered tree (dry-run default) with a BOOTSTRAP TIE-BREAK: a storeless
  top ABOVE store-bearing trees is reported `ambiguous` and never auto-merged. Engine
  `tree-top --proj DIR [--json]` prints a dir's tree top / store / bootstrap flag (LLM-usable).
  `discovery_roots` config finally has its consumer. `knowledge_store_empty` documents its per-tree
  curated / machine-global native semantics. e2e S9: two trees discovered, scaffolded, isolated.

## [5.33.0] - 2026-07-05

### Added
- `memory_engine.py move --from-level X --to-level Y --slug s [--force]`: the dream's re-leveling
  primitive. Pointer-line ops only (the slug-named body never moves). Guards: same-tree
  (cross-tree refused - that is a lift/copy), altitude-chain only (siblings refused), and a
  down-move inbound-[[ref]] dangle check (refused unless --force, which warns). ADD-THEN-REMOVE
  ordering: a crash leaves a visible duplicate pointer (a re-run merges and completes), never a
  lost fact. Unmigrated legacy pointers are refused (migrate first). Exit 1 + `! refused:` on
  refusal.
- `memory_engine.inbound_ref_sources(levels, slug)` / `has_inbound_refs`: THE inbound-reference
  scan (hooks + central bodies); reconcile's `has_inbound_refs` now delegates to it.

## [5.32.0] - 2026-07-05

### Changed
- store-edit-guard rewritten for the live layout: denies Edit/Write/MultiEdit on any path under
  `.claude-memory/` (live) or `.claude-bx-selflearning/` (legacy, downstream installs), AND guards
  the managed pointer block inside any `CLAUDE.local.md` (both fence generations): an Edit whose
  old_string overlaps the fenced region, a Write that adds/alters/deletes the block region, or an
  edit injecting fence markers is denied; everything outside the block stays freely editable.
  MultiEdit checks each edit against the original. Deny message teaches the engine commands
  (add/heal/move/set-scope). Same BITRANOX_MEMORY_ENGINE session-launch bypass; fail-open; applies
  to Task subagents too (probe-verified PreToolUse coverage). 24 tests.

## [5.31.1] - 2026-07-05

### Fixed
- Pointer grammar: a hook may legitimately contain bare `<placeholders>` (e.g. a path template
  `cache/<mkt>/<plugin>/`); the 5.31.0 grammar truncated such hooks at the first `<`, dropping the
  meta comment (provenance + the real slug) and title-deriving a wrong slug. The hook now runs to
  the first `<!--` via a tempered scan. Caught by reconcile --check on live data right after the
  first migration run; recovered by restoring the migration backup and re-running with the fix
  (regression tests use the exact live line). `migrate_to_slug_store` backups now include a
  manifest.txt mapping each copied file back to its original path.

## [5.31.0] - 2026-07-05

### Changed
- SLUG-STORE PIVOT (experiment-backed; probe report `.plan/probe-retrieval-and-platform-20260705.md`):
  fact bodies live at `<anchor>/.claude-memory/facts/<slug>.md` (flat, human-readable); the pointer
  line is `- [Title](mem:<slug>) - hook <!-- bx:src=.. bx:pin -->`; every pointer block's header now
  carries the RETRIEVAL RECIPE (walk up to the ancestor containing `.claude-memory/`, Read
  `facts/<slug>.md`) - measured 6/6 applied mid-reasoning compliance incl. Task subagents, vs 0/6
  for uuid-sharded bodies and 0/3 without the recipe. Slugs are TREE-unique (the body file is the
  registry; the engine refuses a colliding add with a suggested free slug). Pinned entries render
  first under `## Iron rules`. `HOOK_SOFT_MAX = 350` with advisory warnings (engine add,
  reconcile --check). The pointer grammar drops trailing garbage after the meta comment on
  canonical re-render (heal repairs hand-edit damage). Pre-pivot `uuid:` lines still parse
  (flagged legacy), re-render unchanged, and resolve from the old sharded path until migrated -
  a heal can never break an unmigrated store. Fence renamed BITRANOX-MEMORY-INDEX (old accepted).
  The SessionStart retrieval rule teaches the slug path. `add-uuid` CLI retired.

### Added
- `migrate_to_slug_store.py`: one-shot uuid->slug store migration (dry-run default; `--apply` backs
  up every touched CLAUDE.local.md + the anchor's `.claude-memory/`, moves each body and flips its
  pointer line atomically per fact, suffixes cross-level slug collisions, reports missing bodies
  without flipping their lines). Idempotent. Full sibling tests.

## [5.30.0] - 2026-07-05

### Added
- `BITRANOX_HOOKS_OFF=1` master kill-switch in `run-python.sh` (dev-only): set at session launch it
  silences every plugin hook in one place; a deliberate CLI call strips it per-command
  (`env -u BITRANOX_HOOKS_OFF ...`). Tests added.
- `session-banner.py`: the big skills-first banner now ships as its OWN SessionStart hook command.
  The harness persists an oversized additionalContext to a file with only a ~2KB inline preview, so
  everything appended after the ~10KB banner (the memory-retrieval rule, the dream/new-project
  nudges, the miss-audit) never reached context. `session-start.py` now emits ONLY those small
  essentials (kept under the persist cap, size-tested); the banner pays the preview cost alone.

### Changed
- ONE anchor resolver for the whole engine: `self_improve_signals.resolve_anchor` (keyed on the live
  `.claude-memory` store colocation; `topmost_claude_md_dir` is the same function; `uuid_store`
  delegates). `global_rules_dir` returns the tree-top `.claude-memory` store (was a retired legacy
  path); `altitude_chain` returns level dirs. Multiple independent knowledge trees on one machine
  each resolve to their own anchor; a `two_trees` test fixture covers the isolation.
- Single-sourced helpers: `slugify`/`TYPE_PREFIXES` live in `uuid_store` (engine aliases them);
  one mtime-neutral writer; `VENDOR_DIRNAMES` in `self_improve_signals` (gather_scan aliases it).
  gather_scan's tree-top tier scans `facts/` bodies (flat or sharded), never `.archive/`.

## [5.29.0] - 2026-07-04

### Added
- Model-driven on-demand memory retrieval. `session-start.py` now injects a `<BITRANOX-MEMORY-RETRIEVAL>`
  standing rule (with the concrete anchor path computed for the session) teaching the model to fetch a
  fact body ITSELF, mid-task, when a relevant pointer's hook needs its detail: Read
  `<anchor>/.claude-memory/facts/<first 2 hex of the uuid>/<uuid>.md`. The recall hook stays the
  per-prompt keyword baseline; this adds a best-effort mid-reasoning pull for anything the hook did not
  surface. Injected only when an anchor + `.claude-memory` store exist; fail-open. Sibling tests added.

## [5.28.1] - 2026-07-04

### Fixed
- `reconcile_memory_index.py`: a NON-curated level dir (a plain project dir with no pointer block) now
  contributes no reference targets/sources instead of `rglob`-ing its whole subtree. The chain is level
  dirs now, so the old loose-dir scan manufactured false orphan refs from docs/code (`[[section]]` TOML,
  `[[ref]]` examples). `--check` over a real chain is clean again.

## [5.28.0] - 2026-07-04

### Changed
- UUID-native cutover: the curated memory store's on-disk format is now the per-altitude pointer block
  (inline in `CLAUDE.local.md`) + central bodies at `<anchor>/.claude-memory/facts/<shard>/<uuid>.md`.
  The legacy `.claude-bx-selflearning/index.md` + `facts/<slug>.md` + `@import` format is retired. Slug
  stays the logical identity (carried as a `bx:slug=` token on each pointer line); the uuid is only the
  body-file key, so the reference / provenance / dedup model is unchanged. Engine COMMANDS
  (`memory_engine.py add|heal|set-scope`, `reconcile_memory_index.py [dir]|--check`) keep their contract;
  `reconcile_memory_index.py` now takes the LEVEL dir (not a `.claude-bx-selflearning` dir) and reports
  orphan pointers instead of backfilling. The seven memory meta-skills (self-improve, dream-project(+B2),
  dream-global(+deep), memory-settings, collect-knowledge) describe the new format.

## [5.27.0] - 2026-07-04

### Added
- `migrate_to_uuid_store.py --sync`: make the UUID store mirror the current legacy stores - (re)write
  every live fact (idempotent) and prune pointers whose legacy fact is gone plus central body files no
  pointer references. Keeps the projection faithful after a dream deletes or merges facts. Tests added.

### Changed
- Capture now mirrors into the UUID store: `memory_engine.add_or_update_entry` (the legacy primary
  write) also upserts the fact into the central UUID store, best-effort and OUTSIDE the legacy lock, so
  a fact captured after the one-time migration still resolves through the mount-independent path. A
  mirror failure never breaks or rolls back the canonical legacy write (the legacy store stays the
  source of truth during coexistence). Tests cover the mirror and its fail-safe.

## [5.26.0] - 2026-07-04

### Added
- Central UUID body-store + per-altitude pointer indexes (`hooks/uuid_store.py`, additive; the legacy
  `.claude-bx-selflearning/` layout is untouched and stays primary). Fact identity is a deterministic
  `uuid5(altitude, slug)` (idempotent, collision-free across altitudes); a body lives once at
  `<anchor>/.claude-memory/facts/<2-hex-shard>/<uuid>.md`; each altitude carries a mount-independent
  `- [Title](uuid:<uuid>) - hook` pointer block in its `CLAUDE.local.md`. A cwd-derived resolver walks
  up to the store-co-located anchor and reads bodies by shard, so the same tree resolves identically
  across mount points (proven by two `.plan/` probes). Full sibling tests (`tests/test_uuid_store.py`).
- `memory_engine.py add-uuid`: the additive write path into the central store (assigns the uuid, writes
  the body once, upserts the pointer line). Tests in `tests/test_memory_engine.py`.
- `hooks/migrate_to_uuid_store.py`: copies every legacy `.claude-bx-selflearning/` fact into the central
  store (body + pointer), deleting nothing. Idempotent; dry-run by default (`--apply` to write). Tests
  in `tests/test_migrate_to_uuid_store.py`.

### Changed
- Cross-project recall now reads BOTH layouts during the transition: `gather_scan._find_curated_stores`
  also discovers `.claude-memory/facts/<shard>/<uuid>.md` bodies, and `recall-memory._label` names a
  central-store body by its owning tree. Legacy `.claude-bx-selflearning/` discovery is unchanged.

## [5.21.1] - 2026-07-03

### Changed
- `meta-dream-project`: hoisted an imperative capture gate to "When to run" and step 1 so a
  MANUAL/explicit dream ALWAYS captures - `not-due`, an absent `.claude-bx-selflearning/` store, and
  "it's already in some CLAUDE.md" are no longer treated as reasons to skip. An absent store is now
  stated as the trigger to CREATE one, and an absent right-altitude `CLAUDE.md` as the trigger to
  CREATE it, before any due-ness/coverage/no-op reasoning. Hardens the anti-rationalization already
  in step 3b after it kept being skipped in practice.

## [5.17.0] - 2026-07-02

### Added
- `warn-unpinned-subagent-model` PreToolUse hook: warns (never blocks) when a `Task`/`Agent`
  subagent is dispatched without an explicit `model`, so per-role model tiering is not silently
  defeated by inheriting the session model (often `opus`, the priciest). Skips a `fork`, which
  inherits the parent model by design. Fail-open, pure stdlib, cross-OS via `run-python.sh`,
  with tests.

### Changed
- `process-agents-subagent-driven-development` and `process-agents-dispatching-parallel` now note
  that the "always pin the model" rule is enforced by the new hook, not only documented.

## [5.16.2] - 2026-07-02

### Fixed
- Repo `.gitignore`: also ignore `CLAUDE.local.md` (not only `.claude-bx-selflearning/`). With the
  5.14.0 default the memory `@import` wiring lives in an untracked `CLAUDE.local.md`; on this PUBLIC
  repo it must be gitignored so a session's local memory wiring can never be committed. Refreshed the
  stale comment (`memory.md` -> `index.md`; the import lives in `CLAUDE.local.md`).

## [5.16.1] - 2026-07-02

### Changed
- `meta-dream-project` Gate-coverage audit pass: made explicit that a missed gate-signal is a proxy for a
  missed LEARNING - the pass must handle BOTH halves, first capturing the actual learning through the normal
  lane (step 3), THEN proposing the pattern extension. Fixing the regex while dropping the flagged content
  was the failure mode this closes.

## [5.16.0] - 2026-07-02

### Added
- `meta-dream-project`: new **Gate-coverage audit** behavioral pass - the model-driven complement to the
  regex SessionEnd miss-audit. Because the audit hook cannot call the model, it shares the strict gate's
  blind spots and a novel self-admission phrasing that matches neither pattern set is invisible to it. On
  dreaming the model semantically re-reads the session for admissions/corrections/discoveries that did not
  fire the gate, and proposes broadening the role-split family patterns in `self_improve_signals.py` (strict
  + BROAD) via the self-PR loop, with a regression test. Closes the "regex only catches anticipated variants"
  gap in the self-tuning loop.

## [5.15.2] - 2026-07-02

### Fixed
- Self-improve gate/audit: the assistant self-admission patterns (`ASST_PATTERN` and the audit's
  `BROAD_ASST_PATTERN` in `self_improve_signals.py`) missed common admissions - PAST-tense "you were
  right/correct" (only "you're right" was caught), the noun form "was a misread", and "misdiagnosed".
  Broadened both families (and added a regression test) so a genuine self-admitted miss triggers the
  Stop-hook nudge instead of slipping through. Benign state descriptions still do not fire.

## [5.15.1] - 2026-07-02

### Added
- `coding-python-use-modern-libraries`: added `ftfy` as the pick for text-encoding / mojibake repair
  (repairs mixed or double-encoded text like `Ã¼`->`ü` while leaving already-correct text untouched),
  over blanket `.encode('latin-1').decode('utf-8')` round-trips or manual character swaps.

## [5.15.0] - 2026-07-02

### Added
- `meta-dream-project`: new propose-first **Skill-gap review** behavioral pass. During consolidation the
  dream looks for a bug/correction/rework that landed on work done while following a bitranox skill whose
  domain plausibly governed that file/area, and proposes a skill update (pattern/checklist/test) via the
  upstream self-PR loop. This is the deliberate home for the "flag a skill when a real bug slips past it"
  rule: the deterministic per-turn/audit hooks cannot judge a skill's coverage gap, so that fuzzy
  generalization is routed to the dream. `meta-self-improve` cross-references it from the end-of-session
  audit section.

### Fixed
- `ensure_gitignored` no longer fights the global `~/.claude` durability repo. It skips when the git
  toplevel is `~/.claude` (whose whitelist `.gitignore` intentionally tracks the curated store +
  `CLAUDE.local.md`); previously every curated write to the global store appended blanket ignore lines
  that silently untracked global memory. Ordinary project repos still get gitignored as before.

## [5.14.3] - 2026-07-02

### Changed
- `web-frontend-responsive-ux`: added guidance for JS-driven zoom/pan/media viewers (OpenSeadragon,
  maps, custom canvases) that do NOT re-fit on container reshape the way CSS `object-fit` does. New
  preferred-pattern entry (re-fit on `resize`/`orientationchange` only if the user was fitted; poll
  until the viewer settles then `goHome`; covers `prefers-reduced-motion`; avoid a shared flag an
  unrelated animation can steal) and a matching Common-mistakes row. Also documented that the
  matrix sweep is STATELESS (fresh load per profile), so it cannot catch a stateful rotate bug -
  such pages need a manual interact-then-rotate check.

## [5.14.2] - 2026-07-02

### Added
- New `commit-tell-sweep` PreToolUse(Bash) hook: blocks a `git commit`/`merge`/`tag` whose inline
  `-m`/`--message`/`-F`/`--file` message carries a typographic or invisible AI-writing tell (em/en-dash,
  curly quote, ellipsis, NBSP, ZWSP, BOM, ...), closing the gap the file-only `tell-sweep` hook left in
  git commit messages. Ignores tells inside backtick spans; cannot see an editor-composed message (bare
  `git commit`) - that path stays with the humanizer skill. Fail-open (any error exits 0).
- New shared `tell_chars` module holds the canonical tell codepoint `RANGES` + the code-span-aware line
  scanner, used by BOTH `tell-sweep` and `commit-tell-sweep` (one source of truth). `tell-sweep` refactored
  to use it (behavior unchanged). Sibling tests for both new modules.

## [5.14.1] - 2026-07-02

### Changed
- `meta-dream-project` dedup/reconciliation now considers HOOKS as a coverage source, not only skills
  and loaded memory/CLAUDE.md tiers. A rule a hook ENFORCES automatically (typographic tells in prose
  files -> `tell-sweep`; SSH pgrep self-match -> `block-pgrep-self-match`; structured-file sed edits ->
  `block-sed-structured-files`) is even more redundant as prose, so judge "covered" against the UNION of
  {hook enforcement + skill + always-loaded memory}. A hook is the strongest layer but BOUNDARY-LIMITED
  (fires only at its trigger - e.g. file edits, not commit messages/replies/comments - and only where
  the plugin is installed), so the memory/skill layer is kept for what the hook cannot reach.

## [5.14.0] - 2026-07-02

### Changed
- The curated store's `@import` line now lives in the UNTRACKED `CLAUDE.local.md` by DEFAULT (symmetric
  with the gitignored store: the memory wiring never touches tracked git, a fresh clone gets neither the
  wiring nor the store, and no commit is needed to set up memory). It goes in the TRACKED `CLAUDE.md`
  only when `track_private` is on (store committed with the repo, so a teammate's clone loads it too).
  `memory_engine.ensure_level` writes to the right file via `_import_target`, and per-turn capture now
  gitignores `CLAUDE.local.md` + the store on a git repo (new `self_improve_signals.ensure_gitignored`;
  `migrate_memory.ensure_gitignore` also covers `CLAUDE.local.md`). New `claude_local_md_path` helper.
  Skill/prose updated across `meta-self-improve`, `meta-dream-project`, `meta-skill-writer`.

## [5.13.2] - 2026-07-02

### Added
- Memory-store durability, driven by `meta-dream-project` (auto, safe machine-local): every dream
  keeps each `.claude-bx-selflearning/` store version-controlled by a LOCAL git repo (never pushed)
  and commits its changes. The global store is tracked by a repo AT `~/.claude` with an airtight
  WHITELIST `.gitignore` (only `CLAUDE.md` + `.claude-bx-selflearning/`; never the transcripts,
  `plugins/` clones, `security/`, caches); a private project uses `track_private`; a public/non-git
  project uses the store's own isolated repo (parent keeps gitignoring it, so private memory never
  enters a public push). Bounds `.git` growth by squashing a store repo's history to a snapshot when
  the commit count grows (count-gated), and a time-gated reminder (`backup_reminder_due` /
  `mark_backup_reminded` in `self_improve_signals.py`) to push the repo(s) to a PRIVATE remote for
  off-machine backup (propose-first; never auto-creates or pushes a remote).
- `meta-dream-project` CLAUDE.md reconciliation now requires ENHANCE-BEFORE-DELETE: before proposing
  to delete a `CLAUDE.md` rule as "covered by memory", fold its unique detail/example into the
  surviving memory rule and verify full subsumption (never delete on topic-overlap alone); if the
  source `CLAUDE.md` is untracked, make the covering store locally tracked first, then fold + delete.

## [5.13.1] - 2026-07-02

### Changed
- The machine-wide global rule altitude is now a curated `.claude-bx-selflearning/` store at the
  `~/.claude` user-scope level (its `index.md` @imported by `~/.claude/CLAUDE.md`), not the old loose
  whole-loaded `~/.claude/rules/bitranox/` layer. `self_improve_signals.global_rules_dir()` returns
  the curated store; `altitude_chain` treats the global rung as a normal curated altitude; the
  reconciler's format-awareness keeps the loose branch only for a legacy/foreign layer. Promotion into
  global now goes through the write engine like any altitude (index hook + lazy `facts/` body),
  de-doubled from the lower tier. Repointed the promotion-target prose in `meta-dream-project`,
  `meta-dream-global`, `meta-dream-global-deep`, `meta-self-improve`, `meta-collect-knowledge` and the
  `self-improve-gate` capture nudge so a dream never recreates the old loose layer.

### Added
- Dream step (`meta-dream-project` step 5): during consolidation, check each rule fact for a bitranox
  SKILL that already covers its topic (input sanitization -> `bitranox:coding-input-sanitization`,
  resilience -> `coding-resilience`, writing tells -> `write-humanize-en`/`-de`, shell -> `compuse-bash`,
  remote PowerShell/SSH -> `compuse-ssh`); if one matches, keep the always-loaded hook as the trigger and
  make the body a concise pointer (`Detail: bitranox:<skill>`) instead of duplicating the skill's content.

## [5.13.0] - 2026-07-02

### Added
- The always-`@import`ed curated index is the file `.claude-bx-selflearning/index.md` (exposed as
  `self_improve_signals.CURATED_INDEX`), named `index.md` so it is never confused with Claude Code's
  native `MEMORY.md` Auto-memory tier or a stray project `memory.md`.
- Memory-system redesign, phase 1 foundations (`self_improve_signals.py`): curated per-project store
  helpers (`claude_memory_dir`/`curated_index`/`claude_md_path`/`curated_state_dir`) for the
  `.claude-bx-selflearning/` relocation; a Claude Code version gate (`claude_code_version`/
  `import_supported`, parsed from `CLAUDE_CODE_EXECPATH`) so the `@import` load path degrades with a
  loud notice on a too-old Claude Code; a cross-platform advisory `memory_lock` (atomic `O_EXCL`
  lockfile, no `fcntl`/`msvcrt`, Windows-safe); and new config knobs (`track_private`, `mcp_search`,
  `discovery_roots`) with list-valued coercion in `meta-memory-settings` and a derived
  `discovery_roots()` default (no hardcoded maintainer paths in the shipped config).
- `memory_engine.py`: the single write path for the curated store + the `index.md` grammar
  (parse/render), reconciler-compatible markdown-link entries (`[Title](facts/<slug>.md)` heavy vs
  `[Title](#slug)` inline), provenance as a `<!-- bx:src=... -->` set on the entry line, inline-vs-heavy
  by size AND import-like-`@` detection (an inline `@token` would fire an `@import`, so such bodies go
  to a non-imported `facts/` file), `add_or_update_entry` (upsert, merge provenance, locked,
  mtime-neutral) and `ensure_level` (create the CLAUDE.md `@import` block + `index.md` scope, and
  relocate a legacy in-CLAUDE.md scope block into `index.md` byte-safe).
- `reconcile_memory_index.py` rewritten for the curated model: format-aware (curated `index.md`+
  `facts/` vs the loose whole-loaded global tier); an INLINE `#slug` entry AND a heavy
  `facts/<slug>.md` are both valid `[[wikilink]]` targets (fixes false-orphan -> a still-referenced
  inlined fact is no longer flagged/deletable); per-entry reference attribution; backfill `index.md`
  from orphan `facts/` files; `over_cap` guards `index.md` with a separate pinned-body budget;
  `archive_entry` drops an entry and moves its heavy body to `.archive/`.
- Detectors made two-tier + fact-based (`self_improve_signals.py`): `store_signature`/`has_any_facts`
  count REAL facts across the native raw tier AND the curated store (scope block excluded, so a
  gap-fill empty `index.md` never counts). `dream_due` keys on the signature (not mtime, which
  gap-fill and writes churn) and `mark_dream_done` records it; `project_unseeded` and
  `knowledge_store_empty(proj)` count real facts / the curated store; `altitude_chain` now returns
  each level's `.claude-bx-selflearning/` (curated) dir + the loose global layer.
- Cross-project recall now discovers curated stores (`gather_scan.discover_curated`): walks the
  workspace tree for `.claude-bx-selflearning/` (index.md + facts/), ALLOW-listing that one dot-dir
  past the hidden-dir prune (else it was never found), excluding backups, cached per workspace root;
  excludes the current project's own `index.md` (already @imported) but keeps its `facts/`.
  `recall-memory.py` labels a curated index `<project>/memory` and strips the scope descriptor before
  snippeting (so meta is not injected as a fact).
- `memory_engine.py` gains an `add` CLI (the capture procedure invokes it, never hand-writing memory
  files). `meta-self-improve/SKILL.md` rewritten: the curated `.claude-bx-selflearning/` backend, the
  two-tier model (native raw kept, curated captured, dream de-doubles/promotes), the engine as the
  single write path, per-turn capture at the PROJECT level only (promotion deferred to the dream), the
  version gate, and the MCP reframed as an optional read-only search index (never the store).
- Dream skills (`meta-dream-project`, `meta-dream-global`) rewritten for the two-tier model: a
  de-double + promote step (a fact lives in exactly one tier; worthwhile native-only entries promote
  into the curated store via the engine; some-value raw entries stay native); out-of-tree backups of
  both tiers; reconcile the curated store and `--check` the curated altitude chain; over-cap overflow
  moves inline bodies to `facts/` (never CLAUDE.md); promotion into the loose global layer is a
  materialize (global stays whole-loaded); and a closing `/clear` nudge.
- Remaining skill prose repointed to the curated model: `meta-collect-knowledge` (descriptor now in
  `index.md`; the gather CLI also scans other projects' curated stores via `discover_curated`),
  `meta-memory-settings` (documents the `track_private`, `mcp_search`, `discovery_roots` knobs), and
  `meta-skill-writer` (durable state uses the curated store; the MCP is only an optional read-only
  search index, never a backend). Phase 1 complete.
- Phase 2 - migration (`meta-self-improve/migrate_memory.py` + tests): a dry-run/report-first sweep of
  native `~/.claude/projects/<slug>/memory/` stores into the curated model. A filesystem-guided
  slug->path resolver (Claude encodes `/`, `.`, `_` all to `-`, so it DFS-probes each `-` against the
  real tree and parks anything ambiguous/nonexistent - never guesses). Per store: back up BOTH tiers
  out of tree, curate each native topic into the resolved project's curated store via the engine
  (carrying provenance), write an idempotency/resume receipt, and gitignore the store (R11: skip
  non-git, warn if already tracked, honor `track_private`). Native stores are never deleted; other
  repos are never auto-committed.
- Phase 3 - optional MCP search index (`hooks/mcp_search.py` + tests): a fallback-safe integration of a
  memory MCP (`basic-memory`) as a READ-ONLY full-text/semantic search over the local files to sharpen
  cross-project gather. `available`/`enabled` (honors the `mcp_search` knob), `search` (calls
  `basic-memory tool search-notes`, returns ranked ids or None on any failure), `watched_roots`/`covers`
  (does an indexed project span this tree?). The gather CLI adds `MCP-CANDIDATES` when enabled + covering;
  absent/misconfigured -> keyword scan only (never a hard dependency). SAFETY: only reads; the MCP's
  file-writing sync is the user's opt-in setup (via `update-config`), never triggered here.

## [5.12.0] - 2026-07-02

### Added
- `coding-resilience`: new reference skill on never assuming an external resource is available and
  designing for self-healing. Covers retry with backoff + jitter under a hard timeout (tenacity),
  health-check/evict/replace, maintaining a pool at a target size with margin (net-rotating-proxies
  as the worked example), rediscover-do-not-cache, background top-up-to-target, circuit breaker,
  graceful degradation (partial result + warning + non-zero exit), and resource guards
  (bound concurrency/memory/payload, disk/CPU headroom checks). Cross-referenced from
  `coding-python-clean-architecture`, `coding-python-use-modern-libraries`, `compuse-ssh`,
  `compuse-vnc`, `infra-proxmox`, and `coding-input-sanitization`.

## [5.11.0] - 2026-07-02

### Added
- `net-rotating-proxies`: self-optimizing proxy pool. `run` now holds an in-memory working set of the
  `--need` fastest healthy proxies (`ProxyPool`) that maintains itself while the job runs:
  - Rotation so no exit-IP is hammered - a `--cooldown` rest (weighted-LRU) holds a just-used proxy out
    of the next pick, spreading load across the fast half of the pool while still favouring speed;
    relaxes oldest-rested-first so a small pool never starves.
  - Background benchmark + swap-up (with `--background-discovery`, every `--bench-interval` seconds):
    re-times in-pool proxies, trials fresh candidates, and swaps a faster fresh proxy in for the
    slowest IDLE in-pool one (never one mid-request), so steady state stays the N fastest.
  - Flaky eviction: per-proxy success/failure is tracked; a proxy whose failure fraction exceeds
    `--flaky-fail-ratio` is evicted and replaced like a hard-dead one, not just connection-dead ones.
  The pure decision logic (`_weighted_lru_pick`, `_swap_candidate`, `_is_flaky`) is separated from the
  locked, threaded pool state and unit-tested. Existing right-size (`--need`), top-up-to-target, and the
  100% margin behaviour are kept intact. (+20 tests.)

## [5.10.0] - 2026-06-30

### Added
- `net-rotating-proxies`: `validate --need N` early-stop - stop as soon as N live proxies are found (and
  cancel the rest) instead of testing the whole pool, so a small job validates a handful, not thousands.
  The background refresh (`run --need N`) tops the pool back up to N when proxies die, instead of
  re-validating everything. SKILL.md sizing rule: `N ~= 2 x concurrency` (a ~100% margin) so the
  speed-weighted pick runs the fastest while the slower half stays as warm backup. (+2 tests.)
- `sec-appsec-web-baseline`: the scanner detects a same-subnet / internal target - if the URL resolves to
  a private (RFC1918/loopback/link-local) IP and no `--proxy` is given, it warns that the scan measures
  the internal path (origin / split-horizon edge), not what external visitors get, and steers to an
  external egress via net-rotating-proxies. (+2 tests.)

## [5.9.0] - 2026-06-30

### Added
- `files-edit-toml` skill: edit TOML (`pyproject.toml`, config TOML) via a Python library, never
  sed/regex. Routes by whether comments must survive - `tomlkit` for a style-preserving round-trip edit
  (the right tool for `pyproject.toml`), `tomllib` for read (stdlib, read-only), `rtoml`/`tomli_w` for
  machine-owned data. Listed under "Editing structured files and docs" in the orientation index.

### Changed
- `meta-skill-writer`: add a design-time rule - before settling on a single-process tool, decide WHETHER
  the authored skill should fan its heavy / parallelizable / context-bloating work across subagents
  (context isolation + parallel speed), baking the fan-out into the workflow, then pin the model tier.

## [5.8.0] - 2026-06-30

### Added
- New always-active hook **`block-sed-structured-files`** (PreToolUse Bash): BLOCKS an in-place text
  editor (`sed -i` / `gsed -i` / `perl -i`) whose argv targets a `.json/.yaml/.yml/.toml/.xml` file -
  editing structured config as raw text is the `no-hand-edit-config` footgun - and steers to the
  `files-edit-json` / `files-edit-yml` / `files-edit-xml` / `files-edit-toml` skills (load -> edit ->
  dump -> re-validate). WARNs on a `>`/`>>` redirect onto such a file. Command-position anchored (a
  quoted `sed -i x.json` inside an `echo` does not trip it) and fail-open. (+19 tests.)

## [5.7.0] - 2026-06-30

### Fixed
- `sec-appsec-web-baseline`: fix blocking bugs found in review of the 5.6.0 debut. The scanner now
  imports `httpx2` (it had imported `httpx`, which breaks in a clean `uv run`); mixed-content detection no
  longer false-positives on a plain `<a href="http://">` link (only subresource-loading elements count)
  and now also catches `srcset`; a report-only CSP is graded MINOR (not OK) and never counts as
  clickjacking protection; `no-referrer-when-downgrade` is no longer graded OK; the server-version check
  no longer false-fires on a product name with a digit (e.g. `AmazonS3`).

### Added
- `sec-appsec-web-baseline`: a `Cross-Origin-Opener-Policy` check + reference entry; a `--proxy URL` egress
  on `audit_headers.py` and a workflow note to audit PUBLIC sites from OUTSIDE the internal network (route
  via `net-rotating-proxies`, ideally in subagents) so the edge is measured, not the internal origin.
  (+9 tests, 39 total.)

## [5.6.3] - 2026-06-30

### Fixed
- `repo-gate` commit-detection no longer false-fires on the literal text `git commit` inside a quoted
  string or heredoc body (e.g. a Bash command that writes a CHANGELOG line about committing). Detection
  is now anchored at a command position (statement start, after a shell separator) instead of a loose
  substring search - over-matching was not harmless, it false-fired the version-bump BLOCK because
  plugins/ is normally dirty-and-not-yet-bumped mid-work. Real commits (incl. `-C`, `--no-pager`, an
  env-assignment prefix, a subshell) still match. (+6 detector test cases.)

## [5.6.2] - 2026-06-30

### Changed
- `compuse-git` (shared-checkout section): add the pathspec-commit defense - staging only your own paths
  is NOT enough, because a commit records the WHOLE index, so a sibling session's already-staged files
  get swept in. Commit only your paths with a pathspec (`-- <paths>`, the `-m` message before `--`). Notes
  that the branch-guard does not catch this (HEAD is not behind). Generalized from the 5.6.1 incident.

## [5.6.1] - 2026-06-30

### Fixed
- Restore master consistency after a shared-checkout sweep in 5.6.0 (`c5ad104` accidentally committed
  foreign already-staged files): removed the superseded opt-in copy
  `skills/compuse-git/scripts/git-commit-branch-guard.py` (it shipped without tests -> tests-exist fail;
  the real hook lives at `hooks/git-commit-branch-guard.py`), and added the `sec-appsec-web-baseline`
  entry to the `meta-using-bitranox-skills` catalog (it was shipped without its catalog line ->
  skills-index fail).

## [5.6.0] - 2026-06-30

### Added
- `sec-appsec-web-baseline` skill: audit + harden a site's HTTP web-security baseline - security headers
  (CSP, HSTS, X-Content-Type-Options, X-Frame-Options/`frame-ancestors`, Referrer-Policy,
  Permissions-Policy, `X-XSS-Protection: 0`), cookie `Secure`/`HttpOnly`/`SameSite` flags, the
  HTTP->HTTPS redirect, TLS, mixed content, and server-version leakage. Ships `audit_headers.py` (httpx2,
  one GET + a plain-HTTP HEAD, grades SEVERE/MEDIUM/MINOR/OK, no external grading service) with pure
  testable graders + 30 pytest tests, `references/security-headers.md` (values, nginx snippets, safe
  rollout, and gotchas such as the nginx `add_header` inheritance reset), and the safe-rollout discipline
  (staged HSTS, CSP report-only first). Added a new "Security" grouping to the orientation index.
- New always-active hook **`git-commit-branch-guard`** (PreToolUse Bash, warn-only, fail-open): warns
  before a `git commit` when local HEAD is behind/diverged from its upstream (origin advanced under you -
  the shared-checkout / multi-session hazard). Low-noise everywhere - the behind/diverged check runs in
  every repo but fires only when origin moved under you (silent in normal feature-branch work); the louder
  "not on the default branch / detached HEAD" check is OFF by default and enabled per-repo via
  `GIT_GUARD_STRICT_REPOS="repoA,repoB"`. Default branch auto-detected from `origin/HEAD`. (+11 tests.)
  `compuse-git` documents it.

## [5.5.0] - 2026-06-30

### Changed
- `compuse-git`: new section "Committing safely when sessions/agents share a checkout" (+ quick-ref row) -
  when multiple agents/sessions share ONE working copy, branch/HEAD/index can change under you, so a commit
  lands on the wrong branch or a stale base. Verify `git branch --show-current` + `git rev-list --left-right
  --count HEAD...@{upstream}` and stage only your own files (never `git add -A`); durable fix is a `git
  worktree` per session; optional warn-only PreToolUse guard, scoped to single-branch repos (an unscoped
  "off default branch" warning is noise in feature-branch workflows). Generic - the universal half of the
  machine-local git-commit-branch-guard.

## [5.4.4] - 2026-06-30

### Fixed
- self-improve gate now catches a NAMED guard blocking the assistant. `ASST_PATTERN` matched
  "gate blocked me" but missed "rejected by the repo-gate hook" / "the venv-guard hook flagged my
  command" - the old patterns assumed `by the hook` (no name between) or `<guard> ... verb ... me`.
  Replaced with bidirectional proximity (`<guard> ... <verb>` OR `<verb> ... <guard>`, within 30 chars),
  so a named guard in either order fires. "gateway" still does not match "gate" (word boundary). (+1 test.)

## [5.4.3] - 2026-06-30

### Changed
- `meta-self-improve`: the public-contribution path now covers a universal rule that does NOT fit any
  existing skill - if it is substantial enough to warrant a NEW skill domain, propose one (built with
  `bitranox:meta-skill-writer`, named per the taxonomy in `skill-taxonomy.json` / `CONTRIBUTING.md`;
  the gated step-5 path - propose first, scaffold only on explicit permission), not only "enrich an
  existing skill".

## [5.4.2] - 2026-06-30

### Changed
- `web-frontend-responsive-ux`: corrected the thumbnail-rail drag-pan pattern (do NOT
  `setPointerCapture` on pointerdown - it redirects the click to the rail and kills the thumbnail
  link's navigation; gate dragging on actual movement and persist a `dragged` flag). Added patterns and
  common-mistakes for: pre-mounting a deferred heavy viewer hidden (`opacity:0`, still interactive) so
  the first gesture works without owning the LCP; compacting content-rich pages on phones (shrink, do
  not just reflow); keeping a shared element the same rendered size across pages; phantom scroll (an
  unreset `<body>` margin under `min-height:100svh/vh` overflows every profile by a constant); an
  always-open `<details>` menu (an explicit `display` overrides the native closed-hide); and the CSS
  source-order trap (a `@media` override placed before its base rule loses by source order).

## [5.4.1] - 2026-06-30

### Changed
- `meta-self-improve`: reworded the public-contribution criterion - sensitivity is NOT a disqualifier but
  a SCRUB step. If a universal rule still teaches its lesson once private specifics (paths, hosts, secrets,
  org/setup details) are removed or replaced with placeholders, clean it and contribute the scrubbed
  version; only a rule USELESS without those specifics stays private. (Was: "clearly universal AND
  non-sensitive", which wrongly excluded a useful rule that merely carried strippable specifics.)

## [5.4.0] - 2026-06-30

### Changed
- `meta-self-improve`: per-turn capture of a clearly-universal, non-sensitive rule whose topic matches a
  shipped skill's domain now also SURFACES it as a public-contribution candidate (route via the upstream
  self-PR loop, self-contained + provenance-free) - opt-in and propose-first, never auto-publish. Closes
  a gap where a universal rule stopped silently at the machine-local global layer (`~/.claude/rules/bitranox/`,
  which teaches only the maintainer) and the public-skill option was only raised by the dream's batch
  skill-fit pass or a manual nudge. The machine-local layer is your brain; a shipped skill is the shared brain.

## [5.3.0] - 2026-06-30

### Changed
- `compuse-bash`: new Quick-reference row "Keep / prune the NEWEST timestamped file(s)" - sort by MTIME
  (`ls -t`, or `find ... -printf '%T@ %p\n' | sort -zrn`), never by name/glob order. A varying prefix
  breaks lexical order, so a stale file is kept and a newer one deleted. (Surfaced by a real mis-prune
  of timestamped backups.)

## [5.2.1] - 2026-06-30

### Fixed
- `gather_scan.extract_keywords` (recall + cross-tree gather) now drops opaque identifiers that slipped
  past the token regex - Claude tool-use IDs (`toolu_...`), session UUIDs, long hex hashes, pure digits,
  and path slugs (>=4 hyphens) - which were polluting recall ranking and the per-project pending-keyword
  queue. Conservative: real hyphenated terms (`meta-dream-global-deep`, `px-websrv-media`) are kept. (+2 tests.)
- `git-footgun-guard` no longer false-fires on a valid single-revision `git rev-parse --short` that has a
  shell redirection: a redirection like `2>/dev/null` (or its space-separated target) was miscounted as a
  second revision. Redirections are now stripped before counting operands; a genuine 2-revision command
  still blocks. (+2 tests.)

## [5.2.0] - 2026-06-30

### Changed
- self-improve gate now catches the "I forgot a rule, now applying it" turn, which slipped through
  entirely. STRICT `ASST_PATTERN` gains assistant forward-commitment / rule-adoption ("from now on /
  going forward / next time I'll|will|should ...", "I'll make sure/remember to ..."). BROAD SessionEnd
  audit (`BROAD_ASST_PATTERN`) gains rule-citation ("per the <...> rule", the "<...>" rule, "following
  the <...> rule/convention") - a judgement-call signal routed to next-session review, not a live nudge.
  A bare "understood" stays excluded by design (it acknowledges a directive; the directive is the signal).
  `meta-self-improve` examples document forward-commitment + the understood/rule-citation rule. (+2 tests.)

## [5.1.0] - 2026-06-30

### Changed
- self-improve SessionEnd audit (broad recall) now flags mid-course inspection pauses ("let me stop and
  inspect", "let me double-check", "let me inspect/look again/take a closer look") as review candidates.
  These are deliberately BROAD-audit-only, NOT live-gate triggers: a pause only hints at a lesson, which
  resolves later into a discovery ("found it") or self-admission ("I should have") that the strict gate
  already catches. So they surface for next-session human review (lesson? anti-pattern?), never a
  premature per-turn nudge. `meta-self-improve` audit section documents the precursor-vs-resolved rule.
- self-improve strict USER gate now also fires on "rather than X, do Y" (+ German "anstatt"/"anstelle"),
  the synonym of the already-recognized "instead of"/"stattdessen" - a user directive that was slipping
  through. Assistant-side "rather than" is intentionally NOT a trigger (ordinary planning prose, too
  noisy). (+2 tests total.)

## [5.0.0] - 2026-06-30

### Changed
- BREAKING: renamed skill `web-frontend-responsive-audit` -> `web-frontend-responsive-ux`. It covers
  responsive layout plus cross-device usability/UX (no overflow, vertical fit, touch targets, gestures,
  safe-area, responsive images, i18n layout), so "ux" fits the breadth better than "audit", which
  undersold its fix-and-prescribe role. Invoke it as `bitranox:web-frontend-responsive-ux` and update
  any reference to the old name; the skill's content is otherwise unchanged.

## [4.25.0] - 2026-06-30

### Changed
- self-improve LIVE gate now fires on hindsight self-admissions, not just explicit ones.
  `self_improve_signals.py` `ASST_PATTERN` (strict Stop-gate) gains "I should have / I should've",
  "I missed / overlooked / forgot / misread / misunderstood", "I didn't realize/notice/account/
  consider/catch", and "in hindsight" - previously these surfaced only via the SessionEnd audit
  (`BROAD_ASST_PATTERN`), so the per-turn nudge missed them. "you should ..." (not a self-admission)
  is not matched. `meta-self-improve` self-admitted-miss examples updated. (+1 strict test; the two
  audit tests' broad-only example swapped to "let me reconsider".)

## [4.24.1] - 2026-06-30

### Changed
- `web-frontend-responsive-audit`: enforce iterate-on-overlay and release-once; add a large-surface
  spacing pattern. (Changelog entry backfilled - the version was bumped without one.)

## [4.24.0] - 2026-06-29

### Added
- New skill **`web-frontend-responsive-audit`**: responsive/usability audit for web frontends across
  device viewports, with detectors, device profiles, and verification engines. (Changelog entry
  backfilled - the version was bumped without one.)

## [4.23.0] - 2026-06-29

### Changed
- self-improve gate now recognizes "found it" / discovery phrasing as a realization signal.
  `self_improve_signals.py`: `REALIZATION_PATTERN` (live strict gate) gains `found it`, `found the
  bug/cause/culprit/...`, `found out why/how`, `the culprit is/was`, and German `<x> gefunden` / `da ist
  es` - with a negative lookbehind so "haven't found it" / "could not find it" do NOT trip it;
  `BROAD_ASST_PATTERN` (SessionEnd audit) gains the looser `found it/the/out`, `culprit`, `gefunden`.
  `meta-self-improve` realization examples updated to include "found it / found the root cause". (+1 test.)

## [4.22.0] - 2026-06-29

### Changed
- "Never track `.venv` / local build artifacts" is now a tool-agnostic git-hygiene rule with one
  canonical home and cross-refs (no duplication). `compuse-git` carries the full rule (new "Don't track
  local build artifacts" section + quick-ref row): a `.venv` from python -m venv / virtualenv / poetry /
  uv is equally off-limits, as are `__pycache__/`/`*.pyc`/`*.egg-info/`/`node_modules/`/`dist/`/`build/`;
  gitignore them and `git rm -r --cached` if already tracked (gitignore does not untrack). `coding-python-uv`
  and `process-test-design` now carry a one-line cross-ref to it instead of restating it.

## [4.21.0] - 2026-06-29

### Changed
- `coding-python-uv`: the venv section now states `.venv/` is a per-machine build artifact - never commit
  it; ensure it (plus `__pycache__/`, `*.pyc`, `*.egg-info/`) is in `.gitignore`, and if already tracked,
  untrack with `git rm -r --cached .venv`. Completes the test-venv-isolation guidance.

## [4.20.0] - 2026-06-29

### Changed
- `compuse-git`: new "Private git deps in CI need a read-only token" section (+ quick-ref row). A private
  repo depending on other private `git+https://github.com/<Org>/...` repos fails CI install with
  `could not read Username for 'https://github.com'`; fix = a read-only PAT Actions secret + a
  `git config url.insteadOf` rewrite. The token is loaded from a password file via stdin (gh secret set),
  never read or echoed by the agent; ask the user for the directory where their password files live, and
  to create the file if missing. Generic (no org/host names).

## [4.19.0] - 2026-06-29

### Changed
- Test-venv isolation made a first-class rule (the recurring "wrong interpreter under PyCharm" bug).
  `process-test-design`: new "Run in a clean, project-correct environment" section + checklist item -
  run in the project's own venv not the IDE's (`env -u VIRTUAL_ENV uv run pytest`); a ModuleNotFound /
  phantom type-error / pip-audit-noise failure is a WRONG-VENV smell, verify the interpreter before
  trusting it. `coding-python-uv`: the stray-VIRTUAL_ENV gotcha is sharpened into a DEFAULT (strip the
  ambient env for every local test/lint/build, do not wait for it to break) with the bmk variant and
  the interpreter-check one-liner; "fresh" = isolate to the project venv, recreate only when debugging
  corruption.

## [4.18.0] - 2026-06-29

### Changed
- Missing-rung detection now handles the "no shared/tracked home" case. When the folder that should hold
  a department/HQ rung is not itself a tracked shareable repo (a plain dir whose members are each their
  own repo), `meta-dream-global-deep` no longer proposes a bare untracked rung or an unsafe trim; it
  PROPOSES an umbrella repo named `umbrella-<topic>` (e.g. `umbrella-machines`) that version-controls
  only the rung CLAUDE.md files and ignores the nested member repos, and ASKS private or public
  (default private) and local-only vs remote. `meta-dream-project`'s reconciliation guard gains the
  matching trim-safety rule: never trim a tracked/shared lower copy into a less-durable broader home;
  propose the umbrella first.

## [4.17.0] - 2026-06-29

### Changed
- `infra-proxmox` 7.3: new "Running Docker on a Proxmox host / inside an LXC (host-ops)" note - Docker in
  an unprivileged LXC needs nesting+keyctl + iptables-legacy; kernel-global sysctls set inside an LXC are
  ignored (set them on the host under root_volume/etc/sysctl.d/); a wrapper that restarts Docker uses
  Wants=docker.service not Requires=; use `docker compose` v2 not `docker-compose` v1. Surfaced by the
  deep dream as shared fleet host-ops; folded into the shared skill (the host tree had no umbrella repo,
  so a tree rung could not be shared and trimming the per-host repos would have lost version-controlled
  knowledge).

## [4.16.0] - 2026-06-29

### Changed
- `coding-bash-reference`: new "Before you reach for Bash (and before you ship)" section - prefer a
  Python script over shell for real logic (the global working rule, woven in), and gate every Bash
  script you do ship with `shellcheck -x` + `bash -n` (required checks) before committing. Surfaced by
  the deep dream as a fleet-wide host-ops practice; it is good practice everywhere, so it lives in the
  skill rather than in any one project rung.

## [4.15.0] - 2026-06-29

### Changed
- **`meta-dream-global-deep` org-chart audit now detects MISSING rungs (departments and HQ)**,
  evidence-gated. A missing department = the nearest common-ancestor folder of >= 2 RELATED projects has
  no `CLAUDE.md`; a missing HQ = the top of the tree has no head-office rung. Trigger is evidence (a rule
  duplicated across related siblings that wants to consolidate into a rung that does not exist), not bare
  structure - placed at the lowest common ancestor whose children share a domain, never a generic bucket;
  structural-only look-alikes are surfaced as a question. The deep dream MAY propose a brand-new
  workspace-root HQ above the current highest `CLAUDE.md` (the one exception to gap-fill's conservative
  rule); the machine-global layer auto-creates on first promotion. Propose-only, user-gated; creating a
  rung is light (a new `CLAUDE.md`, no slug migration) but adds a tier to children's ancestor chain.
- `meta-self-improve`: noted that descriptor gap-fill stays conservative (never above the highest
  existing `CLAUDE.md`); proposing a new top-level HQ is the deep dream's job, user-gated.

### Docs
- `docs/self-learning-memory.md`: the departments section now covers the deep dream spotting a missing
  department / head office (a related cluster whose folder has no shared shelf) and offering to create it.

## [4.14.0] - 2026-06-29

### Changed
- **CLAUDE.md tiers are treated as altitudes; dreams now RECONCILE them to save context** instead of just
  flagging duplicates. The ancestor `CLAUDE.md` chain + memory + global form one altitude lattice under
  the existing reference+delta model, decided by "reduce total always-loaded context". When a rule is
  found duplicated: covered by a broader tier -> propose DELETING the lower copy (now valid at
  intermediate altitudes too, not just project-root/global); belongs higher -> lift up + leave the delta;
  only-here -> keep; contradiction -> fix memory, not the rule. Runs in both `meta-dream-project` (own
  chain) and `meta-dream-global` / `meta-dream-global-deep` (consolidate sibling duplicates UP across
  trees). All `CLAUDE.md` edits stay propose-first, never without confirmation.
- **`meta-dream-global-deep` gains an org-chart audit** (deep dream only, propose-only): assess whether
  the directory structure still fits and propose moving a drifted project to another department, creating
  a department folder for a flat cluster, or splitting an incoherent one - with the slug-migration +
  ancestor-chain + repo-path consequences spelled out. The dream never relocates a directory itself.

### Docs
- `docs/self-learning-memory.md`: new section "Group your projects like departments in a company"
  (HQ = global, grouping folder = department, project = desk; group related projects so shared rules live
  once at the department altitude). Section 1 now covers that a dream may take several cycles to converge
  (recurring-dream analogy), escalates a non-converging loop to you (intervention), and asks you for
  genuinely-yours decisions (therapist).

## [4.13.0] - 2026-06-29

### Added
- New skill **`meta-dream-global-deep`** - the exhaustive cross-project dream that ALWAYS runs the full
  semantic fan-out scan (every store + every CLAUDE.md), no convergence shortcut, no asking. The normal
  `meta-dream-global` now convergence-checks cheaply first and ASKS before launching the expensive scan;
  `-deep` is for when you want the thorough read regardless.

### Changed
- **Dreams now dedup promotions against CLAUDE.md, not only memory stores.** During the conversion phase
  many cross-project rules still live in `CLAUDE.md`; promoting one already there would duplicate it.
  `meta-dream-global` (step 4 gate) and `meta-dream-project` (promotion step) now grep each candidate
  against the project + ancestor + workspace `CLAUDE.md` before promoting: already-there -> do NOT
  duplicate, FLAG for the user; never edit `CLAUDE.md` without confirmation.
- `meta-dream-global` step 3: cheap convergence/integrity pre-check, then ask before the deep fan-out
  (was: unconditional fan-out).
- Skill content from the cross-project scan: `compuse-ssh` (long remote reload outlives the SSH timeout
  -> verify real state, never infer failure from a dropped connection); `coding-python-clean-architecture`
  (no concrete paths/URLs/hostnames in the domain - config flows from the composition root; a no-env-read
  test proves layer purity); `coding-python-use-modern-libraries` (httpx2 is the legit Pydantic-org
  successor, scanner typosquat flags are false positives - re-verify, do not auto-swap).

## [4.12.0] - 2026-06-29

### Changed
- **Recall hook now also searches other projects' `CLAUDE.md`**, not only their Auto-memory. A lot of
  cross-project knowledge still lives in `CLAUDE.md` (conversion phase), so the per-prompt "check the
  notebook" pass would otherwise miss it. New `gather_scan.discover_claude_md(cwd)` walks up to the
  workspace root (highest ancestor holding a CLAUDE.md), finds every CLAUDE.md under it, EXCLUDES the
  current project's ancestor chain (already loaded in-session) and vendored dirs, and caches the file
  list per root with a 1h TTL so the per-prompt cost stays grep-only. The recall hook injects a snippet
  CENTERED on the first matched keyword (large CLAUDE.md files would miss the match under head-trunc)
  and labels each as `<parent-dir>/CLAUDE.md`. (+4 tests.)

## [4.11.0] - 2026-06-29

### Added
- New skill **`process-test-design`** - the WHAT-to-write companion to `process-test-driven-development`
  (which owns red-green). Consolidates the scattered test-quality rules: prefer real/integration/e2e
  over mocks; dependency injection over monkeypatching (patch only a true external edge); the
  adversarial boundary-input battery (unusual UTF, emoji, CJK, binary, wrong types, oversized, edge
  numbers - the test side of `coding-input-sanitization`); determinism + order-independence (no
  execution-order dependence, no real `sleep`, injected clock/seed, offline unit suite); and pruning
  low-value tests (assert-nothing, impl-mirroring, mock-testing, duplicate). Added to the catalog;
  cross-referenced from `process-test-driven-development` and `coding-input-sanitization`.

## [4.10.0] - 2026-06-29

### Added
- New skill **`coding-input-sanitization`** - the single canonical home for untrusted-input handling,
  scoped to the TRUST BOUNDARY (application / facing-API edge), explicitly NOT the libraries between
  boundaries. Two directions: validate-and-bound on the way IN (typed model, length/size limits,
  charset), escape-per-sink on the way OUT - parametrized SQL (SQL injection), HTML autoescape (XSS),
  argv-not-shell (command injection), path-traversal, deserialization, SSRF, header/log injection.
  Five skills now cross-reference it instead of restating the rules: `coding-python-clean-architecture`,
  `coding-python-enforce-data-architecture-strict`, `process-review-enhance-code-quality`,
  `coding-rust`, `coding-bash-reference`. (The always-on baseline lives in the machine-local global
  rules layer, not shipped here.)

## [4.9.2] - 2026-06-29

### Fixed
- `reconcile_memory_index` reference resolver now also matches a note's frontmatter `name:`, not only
  its filename stem. So a `[[ref]]` resolves whether it used the filename
  (`feedback_generalize_learnings`) or the note's declared name (`generalize-learnings`) - the
  name-vs-filename mismatch class no longer becomes a false orphan. A new `_entry_slugs()` indexes each
  note by stem AND name (both `_canon`-folded); `check_references` and the demotion-safety
  `has_inbound_refs` (which now expands the queried note to all the slugs it answers to) route through
  it. (+2 tests.)

## [4.9.1] - 2026-06-29

### Fixed
- `reconcile_memory_index` reference resolver is now SEPARATOR-INSENSITIVE: a `[[ref]]` matches its
  target note regardless of hyphen/underscore drift (`[[feedback-no-em-dashes]]` resolves to
  `feedback_no_em_dashes.md` and vice versa). A `-` vs `_` mismatch was the single biggest source of
  false orphan refs across the stores. A new `_canon()` folds case and `-`/`_`; `_ref_slug`, the target
  index, the self-ref skip, and `has_inbound_refs` all route through it. (+2 tests.)

## [4.9.0] - 2026-06-29

### Added
- **Pathfinder discipline** woven into the marketplace skills: leave every file better than you found it,
  accept no technical debt (point mistakes out clearly, never "works anyway"), route an out-of-scope fix
  to its own worktree, and clean up temporary scaffolding when done. Canonical statement is a new
  "Pathfinder discipline" section in `meta-self-improve`; an always-on reminder is in the
  SessionStart-loaded `meta-using-bitranox-skills`; and one-line cross-references are in
  `process-review-enhance-code-quality`, `process-review-receiving-code-review`, and
  `process-agents-subagent-driven-development` (with the out-of-scope-fix rule cross-linking
  `git-worktrees`).

## [4.8.2] - 2026-06-29

### Changed
- Dream skills: make dedup/normalize an explicit **final sweep after promotion**, not only a pre-pass.
  Promotion is what *creates* duplication (a rule lifted up now overlaps the note it came from and any
  sibling holding the same lesson), so a dedup that runs only before promoting leaves the just-promoted
  general duplicated below it. `meta-dream-project` step 8 now re-dedups the promotion-touched notes
  before reconcile (and step 4 notes that dedup runs twice); `meta-dream-global` step 6 is now an
  explicit "re-dedup after promotion (required final sweep)". Net per-note bytes can be a wash; the win
  is one source of truth instead of restating the general in every note.

## [4.8.1] - 2026-06-29

### Changed
- Folded two universal learnings from the global-dream scan into their right skills:
  - **`compuse-bash`**: exit 0 is necessary but NOT sufficient - ALSO verify the real artifact/output
    (some tools exit 0 while writing nothing or silently ignoring options, e.g. `vips out.tif[opts]`).
  - **`coding-python-uv`**: gotcha - a stray `VIRTUAL_ENV` (IDE / other project) hijacks `uv` /
    `pip-audit` / `tox` / Makefile targets; unset it (`env -u VIRTUAL_ENV`) or pin the project venv.
- The remaining cross-cutting working rules from the scan (no secrets in tracked files, read-before-Edit,
  docs-describe-current-state, inline-comments-explain-WHY) were promoted to the machine-local global
  rules layer (`~/.claude/rules/bitranox/`), which is not shipped in this repo.

## [4.8.0] - 2026-06-29

### Added
- New skill **`coding-rust`** - Rust idioms / review checks distilled from real review learnings
  (surfaced by a global-dream scan across all project memory stores): no `std::io::Error` for non-IO
  conditions (add a `thiserror` variant), preserve the error chain, constant-time secret comparison,
  `--password-file` over inline `--password`, minimal purpose-specific crates + feature-gating heavy
  optional deps, and making invalid states unrepresentable. Added to the skills catalog.

### Notes
- This release is the productive output of testing `meta-dream-global`: the cross-project scan
  (12 sonnet readers over 32 stores, privacy scrub excluding all domain-private content) found that
  almost all universal knowledge is already encoded in skills/hooks, so it proposed no new global-rule
  bloat - except the user-stated "no Claude/AI commit attribution" rule, promoted to the machine-local
  global layer (`~/.claude/rules/bitranox/`, not shipped in this repo), and the Rust idioms above, which
  belong in a skill rather than the always-loaded global layer.

## [4.7.0] - 2026-06-28

### Changed
- Split the dream skill by scope into two explicit commands (the word "dream" alone was ambiguous):
  - **`meta-dream-project`** - the frequent, cheap consolidation of the CURRENT project (the old
    `meta-dream`, renamed). Keeps `dream_state.py`, the SessionStart "consolidation due" nudge, and the
    behavioral passes (demotion, obsolete-prune, override, CLAUDE.md reconcile, per-project
    filler-classification, model-review). Triggers: "dream", "dream project", "/dream-project",
    "consolidate memory".
  - **`meta-dream-global`** (NEW) - the occasional, expensive cross-project pass: the global-dream scan
    across all project stores (sonnet fan-out -> opus promotion gate), inbound gather, outbound
    cross-pollination. Triggers: "dream global", "/dream-global", "consolidate across projects".
  Renaming `meta-dream` -> `meta-dream-project` removes the old `/meta-dream` skill name (the "dream"
  natural-language trigger is preserved). Updated every cross-reference: `meta-self-improve`,
  `meta-collect-knowledge` (its inbound-pass pointer now targets `meta-dream-global`), the skills
  catalog in `meta-using-bitranox-skills`, the SessionStart / PostCompact nudge text, `README.md`, and
  `docs/self-learning-memory.md` (added the "short nap vs deep sleep" analogy for the two dreams).

## [4.6.0] - 2026-06-28

### Changed
- Recall filler/topical lists are now **per-project** (were machine-global). The shipped
  `filler_words.json` baseline stays **global** (universal generic-English filler, PR-only); the
  **learned filler blacklist**, the **topical whitelist**, and the **pending classification queue** are
  now keyed per project (`~/.claude/self-improve-audit/<proj_key>.{filler,topical,recall-unknown}`).
  This fixes a cross-project contamination bug: a word a dream classified as filler in one project no
  longer suppresses recall of that word in another project where it is a real topic (e.g. `compression`
  is noise in a docs project but a topic in a codec project). The effective blacklist for a prompt is
  `global baseline UNION the current project's learned filler`. `extract_keywords`, `load_filler_words`,
  `add_filler_words`, `load_topical_words`, `add_topical_words`, `note_unknown_keywords`,
  `load_pending_keywords`, `clear_pending_keywords` now take the project; the recall hook and gather CLI
  pass the current `cwd`. The meta-dream filler-classification pass writes per-project.
- Legacy machine-global learned lists (`~/.claude/.bitranox-filler-words.json` etc., a 4.5.x artifact)
  are NOT auto-migrated - the next per-project dream re-learns them. (On the maintainer machine they
  were migrated into the originating project by hand.)

## [4.5.3] - 2026-06-28

### Added
- End-to-end integration test for the memory system (`hooks/tests/test_e2e_memory_system.py`). Unlike
  the per-script unit tests, it drives every component through its REAL entry point - subprocess
  stdin/stdout for the hooks (`recall-memory`, `session-start`, `self-improve-gate`) and CLI argv for
  the helpers (`settings`, `dream_state`, `gather_scan`, `reconcile_memory_index`) - against an
  isolated sandbox HOME, proving they are wired together (settings round-trip, model-review marker,
  new-project nudge self-silencing, recall surfacing + session-dedup + filler/corpus-common
  suppression + self-exclusion, filler-classification queue, cross-tree gather, dream cadence, index
  backfill + dangling-reference `--check`, learning-signal detection). Runs in CI with the unit suite.

## [4.5.2] - 2026-06-28

### Fixed
- Memory-recall precision, round 2 - corpus-stopwording. A keyword can carry no signal yet not be
  generic-English filler: a word common in YOUR store (e.g. "memory" in a memory-centric knowledge
  base - 83% of notes) is a de-facto stopword the static filler list cannot catch. Recall now drops
  such corpus-common keywords (present in > 25% of the store AND not absolutely rare, `df > 6`) from
  both the qualify gate and the inverse-frequency score, so a note matching ONLY corpus-common words
  is no longer surfaced. The absolute-rarity floor keeps a tiny store (where any word is a big
  fraction) from misfiring. Ranking remains an additive IDF sum (one independent weight per useful
  keyword - no combinatorial scoring).

## [4.5.1] - 2026-06-28

### Fixed
- Memory-recall precision. A conversational prompt (e.g. "i got again hits on my previous answer - is
  that normal?") surfaced several unrelated notes. Two causes: (1) keyword matching was SUBSTRING-based,
  so "again" matched "against" and "test" matched "latest" - switched to WORD-BOUNDARY matching;
  (2) generic/conversational words became search keywords - added a filler-word blacklist.

### Added
- Filler-word blacklist for recall keyword extraction: a shipped baseline (`hooks/filler_words.json`)
  unioned with a machine-local list. The per-prompt recall hook stays deterministic / model-free - it
  drops known filler and QUEUES any not-yet-classified keyword; the new `meta-dream` filler-classification
  pass (a `sonnet` subagent) drains the queue, appending confirmed filler to the machine-local list and
  topical words to a known-good cache (conservative: unsure -> topical). Classification is off the
  per-prompt hot path (sleep-time only).
- `self_improve_signals` helpers: `load_filler_words` / `add_filler_words`, `load_topical_words` /
  `add_topical_words`, `note_unknown_keywords` / `load_pending_keywords` / `clear_pending_keywords`,
  plus `model_review_due` / `mark_model_reviewed` (the 4.5.0 model-hierarchy-review marker).

### Changed
- `docs/self-learning-memory.md`: expanded the notebook-recall reflex with the token-economy rationale
  (re-deriving costs more than reading a note; the glance gets cheaper and saves tokens over time) and
  the dream-offload of slow learning; corrected the forgetting section to the no-usage/age-based-decay
  reality (removal = dedup + obsolete-prune + manual only); added the "right tool for the right job"
  model-tier analogy.

## [4.5.0] - 2026-06-28

### Added
- Subagent model-tier doctrine. A canonical "Concrete tiers" mapping in
  `process-agents-subagent-driven-development`: `opus` for deep reasoning / synthesis / adversarial
  correctness-verify / architecture; `sonnet` as the default fan-out workhorse (bounded extraction,
  relevance, per-dimension/per-file/per-store reviewers); `haiku` for mechanical work. Dispatches use the
  stable tier ALIASES so a new model version is picked up with no edit. Cross-referenced from
  `process-agents-dispatching-parallel` and baked into `meta-skill-writer` scaffolding (a skill that
  dispatches subagents must pin a tier).
- Pinned model tiers in the existing dispatchers (`process-review-requesting-code-review`,
  `coding-python-enforce-data-architecture-strict`, `process-agents-dispatching-parallel`,
  `meta-skill-writer`).
- Added subagent fan-out (with tiers) to skills that did heavy/parallel/judgment work inline:
  `process-review-enhance-code-quality` (parallel `sonnet` per rubric dimension -> `opus` synthesis),
  `meta-dream` global scan (`sonnet` per-store -> `opus` judgment), `meta-collect-knowledge` inspect
  (`sonnet`), `process-review-verification-before-completion` (`opus` adversarial verifier),
  `coding-python-performance-review` (`sonnet`), `process-debug-systematic` Phase 2 (`sonnet` finders),
  `meta-adopting-external-skills` (`sonnet` repo analysis, `haiku` license map).
- Periodic model-hierarchy review in `meta-dream` (time-gated via `model_review_due` /
  `mark_model_reviewed`): asks the `claude-code-guide` agent for the current lineup and proposes a
  re-tier via the self-PR loop when the capability/cost ordering shifts. Model releases are infrequent,
  so it runs monthly-ish, not every dream.

### Changed
- `docs-convert-markitdown` default model is now `anthropic/claude-sonnet-4.5` (cheaper/faster);
  opus remains recommended for hard vision / presentations / OCR.

## [4.4.2] - 2026-06-28

### Changed
- Forgetting is gone as an automatic mechanism, because usage cannot be measured (a note sits in
  context and the model reasons over it silently, so absence of a signal does not mean unused) and age
  and detail/size are not valid forget metrics. Removed the dead idle helpers
  (`bump_idle`/`reset_idle`/`should_archive` + the idle file) and the `forgetting` / `forget_idle_dreams`
  config knobs. Memory removal is now ONLY: dedup/merge, obsolete/superseded pruning (model-judged on
  content - a deleted file/flag, a resolved issue, a superseded entry - propose-first), or a manual
  request. `archive_entry` and `has_inbound_refs` are kept (mechanical move + demotion safety).
- Recall hook precision: candidates are ranked by keyword RARITY (inverse document frequency) instead
  of a flat >= 2-keyword filter. A note matching one rare/specific term outranks one matching only a
  common token like "test"; common-only matches are dropped; a lone specific keyword still surfaces.

## [4.4.1] - 2026-06-28

### Fixed
- Reference-integrity `--check` no longer hangs or false-positives. `altitude_chain` previously walked
  to `/` and the check `rglob`'d every ancestor (scanning the whole filesystem for `*.md`). Now: the
  chain is the contiguous set from the project up to the HIGHEST existing `CLAUDE.md` (gap levels
  included, never above it); only the project memory (flat) and the global layer (recursive) are scanned
  for slugged entries; ancestor `CLAUDE.md` altitudes and non-entry files (`CLAUDE.md`, `CHANGELOG.md`,
  `README.md`, ...) are excluded - so code like `Callable[[...]]` or a CHANGELOG mention of `[[general]]`
  is no longer mis-read as a dangling reference.
- Recall precision: the per-prompt recall hook now requires >= 2 keyword hits (or the single keyword
  when only one is significant), so a common token like "test" no longer surfaces dozens of weak matches.

### Changed
- Forgetting is OFF by default and must be USAGE-based, never age/dream-count, never detail-level/size.
  The accidental age-based archive pass is removed from the dream; detail still goes to pulled bodies
  (representation, not deletion). A real usage meter (recall hits + an in-project memory-read signal +
  inbound references) is required before any usage-based, propose-first forgetting is enabled.
- The dream's descriptor step fills `CLAUDE.md` scope-descriptor GAPS up to the highest existing
  `CLAUDE.md` (create the missing levels, propose-first) so the classifier has a descriptor at every
  altitude, rather than skipping gaps.

## [4.4.0] - 2026-06-28

### Added
- Per-prompt memory recall: a `UserPromptSubmit` hook (`recall-memory.py`) that, on each prompt, does a
  fast keyword grep across your OTHER projects' memory and the global rules layer (reusing the existing
  `gather_scan.py` engine; the current project is excluded, so what it draws in is de-duplicated against
  your own memory) and injects the strongest matching notes' bodies as advisory context - once per
  session. The "look in my notebook before reinventing" reflex on top of the always-present index.
  Read-only (it surfaces; it does not copy/promote - that stays meta-collect-knowledge). Fail-open.

## [4.3.1] - 2026-06-28

### Fixed
- Renamed the two duplicate-basename `test_strip_typographic_tells.py` files (write-humanize-en/-de) to
  `_en`/`_de` suffixes so a plain `pytest` over the tree collects without an import-file-mismatch. The
  CI gate was unaffected (it already runs `--import-mode=importlib`); this fixes the naive developer run.

## [4.3.0] - 2026-06-28

### Added
- Layered memory, Phase 2 (cross-tree): knowledge can now flow between sibling project trees, not just
  down one ancestor chain.
- New skill `meta-collect-knowledge` (`/collect-knowledge`): the inbound cross-tree gather via a
  grep -> inspect -> gather funnel. Ships `gather_scan.py` (deterministic stage-1: derive keywords,
  grep other projects' memory + the global rules layer, excluding the current project) so the model
  step runs only on a hit. Brings knowledge in by lifting to a common ancestor or a self-contained
  copy - never a cross-tree reference - with a secret/PII scrub on cross-boundary writes. Also runs as
  meta-dream's inbound pass, and powers the new-project bootstrap nudge (now active).
- New skill `meta-memory-settings` (`/memory-settings`): view/set/reset the informed-consent knobs
  (dream mode, privacy, promotion eagerness, forgetting, nudges) in `~/.claude/.bitranox-memory.json`,
  via a small `settings.py` CLI. A recorded choice is applied automatically, never re-asked.
- `meta-dream` gains the cross-tree passes: inbound gather (delegated), outbound cross-pollination
  (promote to the lowest common ancestor; native cascade delivers it; rare self-contained copy), and a
  global-dream cross-project scan with a cross-project corroboration path. All honor the `privacy` knob.

## [4.2.1] - 2026-06-28

### Added
- Layered memory, Phase 1.5 (counter-gated behavioral passes; counters live outside the dreamed store
  so consolidation stays a no-op on an unchanged store):
  - Forgetting / decay: out-of-store per-entry idle counter (`bump_idle`/`reset_idle`),
    `should_archive` honoring a `forgetting` knob (off / conservative / aggressive), and
    `reconcile_memory_index.archive_entry` that moves an idle non-must-always body to a cold `.archive/`
    and drops its index line (bias toward keeping; must-always is never archived).
  - Demotion safety: `reconcile_memory_index.has_inbound_refs` so an entry that lower entries still
    reference upward is never demoted; demotion reuses the promotion dwell/hysteresis.
- `meta-dream` gains the behavioral passes: demotion, forgetting/decay, contradiction/override
  (CLAUDE.md authoritative; memory override = more-specific wins), and CLAUDE.md reconciliation
  (back up before edit; integrate overlap into a same-scope always-present home and propose deletion;
  intermediate-altitude overlaps are flag-only).

## [4.2.0] - 2026-06-28

### Added
- Layered memory, Phase 1 (core). Knowledge is now placed by SCOPE across always-present homes:
  per-project Auto memory, a global cross-project layer at `~/.claude/rules/bitranox/` (native
  whole-loaded user rules, recursion confirmed; never touches the user's hand-written CLAUDE.md), and
  CLAUDE.md only for must-hold intermediate-subtree rules. Concrete-but-universal facts are promoted
  KEPT CONCRETE, not abstracted away.
- Normalization instead of duplication: a specialized entry `references [[general]]` and adds only its
  delta; references point UPWARD only (deletion-safe). `reconcile_memory_index.py --check` verifies
  reference integrity (orphans, downward refs) across the altitude chain and warns on an over-cap
  `MEMORY.md`.
- Quality/dwell gate before global promotion (the global layer loads into every session): user-stated
  concrete rules promote eagerly; model-inferred generalizations need corroboration across >= 2 dreams.
  Counters live outside the dreamed store, so consolidation stays convergent.
- One machine-local config `~/.claude/.bitranox-memory.json` (`load_config`/`save_config`) for the
  informed-consent knobs (dream mode, promotion eagerness, forgetting, nudges), migrating the legacy
  `.bitranox-dream-*` sentinels one-way. A `nudges` flag can switch session nudges off.
- Per-level scope descriptor support (a bounded, diff-free `<!-- bitranox:self-learning -->` block) and
  new helpers in `self_improve_signals.py`: `global_rules_dir`, `altitude_chain`, project seeding, and a
  "store changed under me" signature.
- A dormant new-project bootstrap nudge (activates only once the Phase-2 `meta-collect-knowledge` skill
  is installed and there is knowledge to seed from).

### Changed
- `meta-self-improve` and `meta-dream` rewritten to the scope-based multi-altitude model (concrete
  homes, normalization, upward-only references, descriptor-guided classification, config as the single
  source of truth for modes/knobs); `self-improve-gate.py` nudge text updated to match.

## [4.1.0] - 2026-06-27

### Added
- `meta-dream` skill: periodic memory consolidation ("sleep" to self-improve's per-turn capture). It
  backs up the memory store, then dedups/merges/generalizes/re-wires/prunes it and the session,
  routes generalized must-hold rules to the right-altitude CLAUDE.md (creating it if missing) with
  dual representation (combine general+specific, or split across altitudes, cross-linked), and batches
  skill-worthy generalizations into one self-PR via self-improve's upstream loop. A tri-state mode
  (opt-out sentinels in ~/.claude) controls it: `off` (no nudges; memory-only), `auto` (apply without
  asking), `propose` (default). Ships `dream_state.py` (due/done/mode cadence marker).
- Trigger wiring: a self-silencing SessionStart nudge when a consolidation is due
  (`dream_due` in `self_improve_signals.py`); the SessionEnd audit hook now also runs at **PreCompact**
  to salvage candidate learnings from the still-full transcript before compaction; a new
  **PostCompact** hook (`post-compact-nudge.py`) injects a capture/consolidate reminder afterward.

## [4.0.1] - 2026-06-27

### Changed
- Stripped pre-existing typographic AI-writing tells (em/en dashes, curly quotes, ellipsis,
  non-breaking/zero-width spaces) to ASCII across 135 shipped reference docs and a few code
  comments/strings, using the `write-humanize-en` strip tool. The two humanize SKILLs (which teach
  about tells) and the `coding-python-textual` screenshot SVG are intentionally left as-is.

## [4.0.0] - 2026-06-27

### Changed (BREAKING) - every skill renamed to the category-prefix scheme

All skills now carry a category prefix (`<category>-[<sub>-]<name>`). Invocation names changed,
so update any saved references to the new names below. The full current catalog is the
`bitranox:meta-using-bitranox-skills` domains list; categories live in `skill-taxonomy.json`.

New invocation names:

- `bitranox:process-plan-brainstorming` (brainstorming)
- `bitranox:process-plan-writing-plans` (writing-plans)
- `bitranox:process-plan-executor` (plan-executor)
- `bitranox:process-agents-dispatching-parallel` (dispatching-parallel-agents)
- `bitranox:process-agents-subagent-driven-development` (subagent-driven-development)
- `bitranox:process-debug-systematic` (systematic-debugging)
- `bitranox:process-test-driven-development` (test-driven-development)
- `bitranox:process-review-requesting-code-review` (requesting-code-review)
- `bitranox:process-review-receiving-code-review` (receiving-code-review)
- `bitranox:process-review-verification-before-completion` (verification-before-completion)
- `bitranox:process-review-enhance-code-quality` (enhance-code-quality)
- `bitranox:process-ship-finishing-development-branch` (finishing-development-branch)
- `bitranox:coding-python-clean-architecture` (python-clean-architecture)
- `bitranox:coding-python-enforce-data-architecture-strict` (python-enforce-data-architecture-strict)
- `bitranox:coding-python-performance-review` (python-performance-review)
- `bitranox:coding-python-use-modern-libraries` (python-use-modern-libraries)
- `bitranox:coding-python-gitignore` (python-gitignore)
- `bitranox:coding-python-rpyc` (rpyc), `bitranox:coding-python-textual` (textual),
  `bitranox:coding-python-uv` (uv)
- `bitranox:coding-bash-clean-architecture` (bash-clean-architecture),
  `bitranox:coding-bash-reference` (bash-reference)
- `bitranox:files-edit-json` (edit-json), `bitranox:files-edit-xml` (edit-xml),
  `bitranox:files-edit-yml` (edit-yml)
- `bitranox:docs-md-table-formatting` (md-table-formatting),
  `bitranox:docs-convert-markitdown` (markitdown)
- `bitranox:compuse-bash` (computer-use-bash), `bitranox:compuse-git` (computer-use-git),
  `bitranox:compuse-ssh` (computer-use-ssh), `bitranox:compuse-vnc` (computer-use-vnc)
- `bitranox:git-worktrees` (unchanged)
- `bitranox:infra-proxmox` (proxmox), `bitranox:infra-proxmox-bindsnap` (proxmox-bindsnap)
- `bitranox:net-rotating-proxies` (rotating-proxies)
- `bitranox:write-humanize-en` (humanize-en), `bitranox:write-humanize-de` (humanize-de)
- `bitranox:marketing-rory` (rory)
- `bitranox:meta-self-improve` (self-improve), `bitranox:meta-skill-writer` (skill-writer),
  `bitranox:meta-adopting-external-skills` (adopting-external-skills),
  `bitranox:meta-using-bitranox-skills` (using-bitranox-skills)

The `skill-taxonomy.json` registry's `legacy`/`retrofit` migration data is removed now that the
rename is applied; the registry is just the forward category vocabulary.

## [3.14.0] - 2026-06-27

### Added
- Category-prefix naming scheme for skills: `<category>-[<sub>-]<name>` (e.g.
  `coding-python-clean-architecture`, `compuse-ssh`, `marketing-rory`). A new
  `plugins/bitranox/skill-taxonomy.json` registry defines 26 top-level categories (with seed
  sub-prefixes), grounded in real-world skill directories. `repo-gate.py` `check_skill_naming`
  forces every NEW skill's top-level prefix to be a registry category (sub-prefixes free-form);
  `adopt_skill.py` validates the same on adoption. Opening a new category is a deliberate registry
  edit. The 41 existing flat names are grandfathered (`legacy`) until a future retrofit MAJOR, whose
  full rename map is prepared in the registry (`retrofit`). CONTRIBUTING documents the scheme and
  tie-break rules; skill-writer points authors at a marketplace's naming registry.

## [3.13.0] - 2026-06-27

### Added
- SessionStart auto-update reminder: when marketplace auto-update is OFF for `bitranox-skills`,
  `session-start.py` emits a one-line `systemMessage` explaining how to enable it (`/plugin` UI or
  `extraKnownMarketplaces.<name>.autoUpdate` in settings.json). It is **self-silencing** - it stops
  once auto-update is enabled in user/project settings - and can be dismissed without enabling by
  creating `~/.claude/.bitranox-no-autoupdate-nudge`. A plugin cannot set auto-update itself; this
  only reminds. README gained an "Enable auto-update (recommended)" section.

## [3.12.0] - 2026-06-27

### Changed
- `self-improve` is now **native-first** about memory. Durable learnings are written to `MEMORY.md`
  (one-line index entry) + a topic-file body - the index line is what makes a learning present.
  A memory MCP server (`basic-memory`/`server-memory`) is no longer treated as a write path or home:
  routing learnings through it skips the `MEMORY.md` index (not present) and a pull store is not
  searched (lost). An MCP now earns its place only at genuine scale AND with a real recall mechanism,
  indexing the native dirs as a search augmentation - never the sole store.

### Added
- `self-improve/reconcile_memory_index.py`: a maintenance utility that backfills a `MEMORY.md` index
  line for every topic file that lacks one (additive, idempotent, never deletes; reports orphans).
  Repairs an index that drifted from its topic files after out-of-band/MCP writes.

## [3.11.0] - 2026-06-27

### Added
- `self-improve` end-of-session miss audit (self-tuning loop): a new **SessionEnd** hook
  (`self-improve-audit.py`) scans the whole transcript and records **candidate misses** - turns a
  broad recall pattern flags but the precision-tuned gate did not catch - to a per-project audit
  file. The **SessionStart** hook (`session-start.py`) surfaces that audit once next session so the
  model reviews the misses, captures their learnings, and extends the gate. SessionEnd cannot nudge
  the model, so the analysis is deterministic and the review is deferred to the next start.
- `self_improve_signals.py`: shared single source of truth for the strict gate patterns (now
  imported by the gate) plus the broader recall patterns and the audit-file location, so the gate
  and the audit can never drift.

## [3.10.3] - 2026-06-27

### Changed
- `self-improve` gate: idea endorsement is now detected from **either side**. The high-signal case
  is the assistant judging the user's suggestion good ("good idea", "good call" -> the user found the
  better path, adopt it); it still also fires when the user endorses the assistant's proposal (a
  confirmed approach). Factored into a shared `_ENDORSE_PATTERN` checked against both messages; a
  bare "ok/thanks/nice" still does not fire. (Corrects 3.10.2, which only checked the user side.)

## [3.10.2] - 2026-06-27

### Changed
- `self-improve` gate: user endorsement of a proposed idea is now a learning signal ("good idea",
  "good call", "nice catch", "let's do that") - it marks a confirmed approach worth recording. A
  bare "ok/thanks/looks good" still does not fire. The skill and gate now frame signals as families
  (user correction / remember / endorsement; assistant self-admission / realization) and say to
  extend the whole family rather than one phrase at a time.

## [3.10.1] - 2026-06-27

### Changed
- `self-improve` gate: broadened the realization signal to the "clear" family - "now it's clear",
  "I have a clearer picture", "the full picture", "makes sense now" - while still not firing on a
  plain "the requirements are clear" / "is that clear?".

## [3.10.0] - 2026-06-27

### Added
- `adopting-external-skills` skill: a playbook plus a `adopt_skill.py` helper for bringing a useful
  third-party Claude Code skill (a repo URL, an installed plugin path, or a pasted `SKILL.md`) up to
  bitranox standards and into this marketplace. It runs a blocking license gate (accept the permissive
  family MIT/BSD/ISC/Apache-2.0, reject copyleft, never assume MIT when a license is absent), normalizes
  naming and cross-references, scaffolds tests, and records attribution. It is upstream-first - push the
  improvement to the original author first - and never removes or disables the user's other plugins.
- `plugins/bitranox/THIRD_PARTY_NOTICES.md`: per-skill attribution and license texts for adapted skills,
  shipped with the plugin so the notice travels with every install. Seeded with the existing adaptations.
- `repo-gate.py` `check_attribution`: keeps every `> Adapted from ...` credit line in sync with a
  `THIRD_PARTY_NOTICES.md` entry (no orphan credit lines or notices).

### Changed
- `self-improve`: realizations now count as a learning signal. The gated Stop hook fires on
  discovery phrasings ("now I understand the real ...", "I figured out ...", "it turns out ..."),
  and the skill routes a discovered infrastructure/architecture/topology/data-flow fact at the
  right altitude (own infra spanning projects -> top-level CLAUDE.md; one project -> its
  CLAUDE.md/memory; unsure -> ask). The memory backend is framed as a push/pull choice: must-hold
  standing rules stay in `MEMORY.md`/CLAUDE.md, the episodic tail can live in an installed memory
  MCP server (`basic-memory` or `server-memory`).
- `skill-writer`: new rule "Persisting durable state: choose a memory backend" - a skill that stores
  durable facts must treat the backend as a push/pull choice (standing rules in `MEMORY.md`/CLAUDE.md,
  episodic tail in a memory MCP server) rather than hard-coding `MEMORY.md`.

## [3.9.0] - 2026-06-26

### Added
- `python-gitignore` skill: git-exact `.gitignore` parsing and path filtering (include/whitelist mode,
  memory-bounded for millions of paths) via the `igittigitt` library/CLI - install, config, library
  API, CLI, and bash piping. Added the matching row to `python-use-modern-libraries` (prefer
  `igittigitt` over hand-rolled fnmatch/glob/re, `gitignore_parser`, or `pathspec`).
- `self-improve`: a "Scaling memory as it grows" section - keep entries lean (one-line index, edit over
  append); when the index gets too big, add the `basic-memory` MCP for semantic search over the existing
  markdown memory files (with the caveat to disable its frontmatter-rewriting flags first and back up +
  diff). Keeps must-hold rules in MEMORY.md/CLAUDE.md (push, always loaded) and uses basic-memory for the episodic tail (pull, on-demand search); `@modelcontextprotocol/server-memory` noted as a knowledge-graph alternative.

## [3.8.0] - 2026-06-26

### Added
- `proxmox-bindsnap`: install, verify, configure and operate pve-bindsnap on a Proxmox VE node -
  snapshot and clone LXC containers that have bind/device mounts (the `BINDSNAP-FORCE-RUNNING`,
  `BINDSNAP-UNSUPPORTED`, `BINDSNAP-EXCLUDE` markers, the checksum guard / untested-build workflow,
  cloning, and uninstall).

## [3.7.0] - 2026-06-26

### Changed
- `python-use-modern-libraries`: sharpened the structured-data guidance - `pydantic` to parse
  untrusted input at every boundary, `dataclasses` for pure internal layers, and `attrs` /
  hand-woven classes / raw `dict`s added to what to avoid. Cross-links the
  `python-enforce-data-architecture-strict` skill for the full end-to-end discipline.

## [3.6.0] - 2026-06-25

### Added
- `computer-use-git`: a "review for leaked data before push / PR / publish" section - scan the WHOLE
  push range (every unpushed commit, plus `--all`/`--tags`/side branches), not just the last diff, for
  secrets, private infrastructure, and personal data; use documentation-safe placeholders; history is
  hard to scrub once pushed. Brief cross-referencing gates added to `finishing-development-branch`
  (before a push/PR option) and `requesting-code-review` (before merging).

## [3.5.0] - 2026-06-25

### Added
- `reformat-md-tables` hook (`PostToolUse(Write|Edit|MultiEdit)`): after a markdown file is written
  or edited, it auto-realigns the file's tables in place (reusing the md-table-formatting skill's
  `reformat_file`), so a table can never ship misaligned. Silent, safe-by-design (bails on malformed
  tables), exits 0 on every failure path.

## [3.4.0] - 2026-06-25

### Added
- `computer-use-vnc` skill: drive a target's screen over plain VNC/RFB with the `vnc-remote-control`
  CLI (type, key, click, screenshot, OCR, click-text) when the target has no network/SSH/agent/API -
  Proxmox/hypervisor VM consoles (incl. first boot before networking), legacy GUI software, and old
  TUI apps. Pure client: nothing on the target except its VNC server (Proxmox ships noVNC). The skill
  installs the tool via uv and drives it; click coordinates are absolute native pixels (no scaling).

## [3.3.0] - 2026-06-25

### Added
- `computer-use-ssh`: an Authentication and host keys section - never ask for / type / accept an SSH
  password (it leaks into transcript, history, logs); log in with a key by PATH (`ssh -i <keypath>`,
  never reading the key or a passphrase), proposing the user set up passwordless key auth if a host
  still wants a password; on the user's OWN/trusted subnet accept new AND changed
  host keys (reimaged hosts), scoped via `~/.ssh/config` to the subnet ranges (`StrictHostKeyChecking=no`
  + `UserKnownHostsFile=/dev/null`), while untrusted hosts use `accept-new`. Includes per-OS walkthroughs
  for setting up key auth (client, incl. Windows OpenSSH via winget/Add-WindowsCapability) and an SSH
  server (Linux/macOS/Windows).

## [3.2.1] - 2026-06-25

### Fixed
- `computer-use-git`: the `repo-gate` hook description now lists all of its checks - the
  using-bitranox-skills index sync and the secrets/private-data scan, alongside tests/pytest/JSON/LF.

## [3.2.0] - 2026-06-25

### Added
- `python-performance-review`, `python-clean-architecture`, `enhance-code-quality`: a third
  robustness rule - never trust structured input. Structured data passed in (dict, JSON, API/IPC
  payload, deserialized object) must have its structure parsed/validated into a typed model before
  use, never assumed correct - unless the user deliberately opts out of the check.

## [3.1.0] - 2026-06-25

### Added
- `python-performance-review`, `python-clean-architecture`, `enhance-code-quality`: two robustness
  rules - (1) keep memory bounded on large/unbounded data (big files, huge DB result sets, huge log
  files must stream/chunk/paginate, not load whole, unless provably bounded), and (2) sanitize and
  bound all external input (lengths/overflow, types, encoding; non-ASCII/emoji/CJK/binary handled
  safely and tested). `enhance-code-quality` gains a Resource Safety rubric dimension.
- `python-performance-review`: `find_unbounded_memory.py` AST detector (with tests) that flags
  whole-file/DB/log reads (`read()`/`readlines()`/`read_text()`, `fetchall()`, un-chunked pandas
  readers), wired into the analysis pipeline as Step 4f.

## [3.0.0] - 2026-06-25

### Changed (BREAKING)
- Renamed skill `python-performance-reviewer` -> `python-performance-review` (the invocation name
  changes; update any references).

### Added
- `python-enforce-data-architecture-strict` skill: an iterative, subagent-driven workflow that
  refactors Python to a strict data architecture - Pydantic models at every external boundary,
  typed models (never raw dicts) internally, Enums/IntEnum for fixed string values, compatibility
  shims removed, and conversions minimized to one parse in / one dump out.

## [2.0.0] - 2026-06-25

### Changed (BREAKING)
- Renamed two skills (the invocation names change, so any references must update):
  `force-using-skills` -> `using-bitranox-skills`, and `plan-writer` -> `writing-plans`
  (matching the upstream superpowers name). All in-repo cross-links, the SessionStart hook,
  and the README were updated.

### Added
- Adopted the remaining four superpowers skills so bitranox fully covers them and the
  superpowers marketplace can be dropped: `dispatching-parallel-agents` (fan out 2+ independent
  tasks), `requesting-code-review` and `receiving-code-review` (the two halves of a review
  cycle, with a `code-reviewer.md` subagent template), and `subagent-driven-development`
  (drive a plan through implementer/reviewer subagents in one session, with `task-brief` /
  `review-package` / `sdd-workspace` helper scripts).
- `session-start.py` hook (SessionStart, matcher `startup|clear|compact`): injects the
  `using-bitranox-skills` skill as session context on startup, `/clear`, and after compaction -
  bitranox's replacement for the superpowers SessionStart bootstrap, so the skills-first
  discipline is active from the first turn without dropping when superpowers is removed.

### Changed
- `using-bitranox-skills` (renamed from `force-using-skills`) enhanced with concepts carried over
  from superpowers `using-superpowers`: a SUBAGENT-STOP guard, an Instruction Priority section
  (user instructions / CLAUDE.md outrank skills outrank the default prompt), a "never read a
  skill's SKILL.md by hand - invoke it" rule, and a brainstorm-before-plan-mode branch.
- `writing-plans` (renamed from `plan-writer`) reconciled with superpowers `writing-plans`, adding
  the Scope Check, File Structure, Task Right-Sizing, Global Constraints, Interfaces block,
  checkbox steps, No Placeholders, and Self-Review sections it was missing.
- Cross-links in the adopted skills now point at their bitranox equivalents
  (superpowers `writing-plans` -> `bitranox:process-plan-writing-plans`, `executing-plans` -> `plan-executor`,
  `using-git-worktrees` -> `git-worktrees`,
  `finishing-a-development-branch` -> `finishing-development-branch`). The SDD workspace dir
  moved from `.superpowers/sdd` to `.bitranox/sdd`. `plan-executor` gained a reciprocal link to
  `subagent-driven-development` as the in-session execution alternative.

## [1.8.0] - 2026-06-25

### Added
- `computer-use-bash`, `computer-use-git`, `computer-use-ssh` skills: consolidate the global
  shell/git/ssh mechanics that were scattered across project notes. Bash: never dismiss a
  non-zero exit as a quirk, isolate a mutation from a trailing check (exit-code masking),
  pipeline `PIPESTATUS`, pgrep/pkill self-match, don't over-wait. Git: `rev-parse --short`
  takes one rev, the `core.fileMode=false` exec-bit trap (`git update-index --chmod=+x`),
  CRLF/LF, no interactive flags. SSH: remote pgrep/pkill self-match, inline-quoting layers,
  backgrounding drops the session, remote PowerShell needs `-File` not inline.
- `git-footgun-guard` hook: a `PreToolUse(Bash)` guard that blocks the always-broken
  `git rev-parse --short <2+ revs>` (it fails `fatal: needed a single commit`) before it
  produces the confusing error, naming the fix.

## [1.7.0] - 2026-06-24

### Added
- `tell-sweep` hook: a `PostToolUse(Write|Edit|MultiEdit)` guard that flags AI-writing
  typographic and invisible tells (em/en-dashes, curly quotes, ellipsis, guillemets, NBSP,
  ZWSP, BOM, bidi controls) just written to a prose file (`*.md`, `*.markdown`, `*.txt`,
  `CLAUDE.md`). Tells inside inline-code spans and fenced code blocks are ignored, so a file
  that documents the tells does not false-positive on its own examples. Code files are
  skipped; allowed symbols (arrow, multiplication, comparison, check, bullet) never trip it.

## [1.6.0] - 2026-06-24

### Added
- `validate-structured-files` hook: a `PostToolUse(Write|Edit|MultiEdit)` guard that re-parses
  the resulting JSON/YAML/XML and blocks the write (with the parse error fed back) when it no
  longer parses. Skips templates, JSONC, multi-doc YAML, empty stubs, and missing libraries;
  parses XML XXE/billion-laughs-safe.
- `repo-gate` hook: a pre-commit / CI gate. As `PreToolUse(Bash)` it blocks a local
  `git commit` / `gh pr create` on a violation (and no-ops outside this repo); as `--ci` it runs
  the same checks for GitHub Actions. Enforces tests-exist, pytest passes, JSON valid, and LF
  endings; version-bump is enforced in the local pre-commit only, never on a contributor PR.
- GitHub Actions workflow (`.github/workflows/ci.yml`): reporting check that runs the gate.
- Tests for every shipped hook (previously only skill scripts had them), enforced by a new
  CLAUDE.md guardrail.

### Changed
- `rotating-proxies`: dropped the `import httpx2 as httpx` alias; the script uses `httpx2`
  throughout.

## [1.5.0] - 2026-06-24

### Added
- `edit-json`, `edit-yml`, `edit-xml` skills: edit structured files through a library
  (round-trip + re-validate) instead of by hand or with `sed`/regex.
- Listed `lxml` in `python-use-modern-libraries`.

## [1.4.0] - 2026-06-24

### Added
- `block-pgrep-self-match` hook: blocks the `pgrep`/`pkill` bracket-trick self-match.

### Changed
- `self-improve`: require a version bump when propagating shared artifacts.
- Documented the semver versioning rule in `CONTRIBUTING.md`.

## [1.3.0] - 2026-06-24

### Added
- Skills audit pass: new skills, performance-reviewer merge, added tests and fixes.
- `rory`: wove the distilled corpus into its references.

## [1.2.2] - 2026-06-23

### Fixed
- `self-improve`: close the git-config gap when shipping a guard script.

## [1.2.1] - 2026-06-23

### Changed
- `skill-writer`: document cross-platform rules for bundled scripts and hooks.

## [1.2.0] - 2026-06-23

### Fixed
- `self-improve` hook: cut Windows false positives and hardened the gate launcher
  (LF endings, UTF-8, Git-Bash-only guard, 64 KiB transcript-tail read).

## [1.1.0] - 2026-06-23

### Added
- Cross-platform hook support, the count-then-enforce escalation ladder, Python helper
  ports, and documentation.

## [1.0.0] - 2026-06-23

### Added
- Initial marketplace release: the bitranox skill collection (invoked as `/bitranox:<skill>`)
  plus the `self-improve` Stop hook, `CONTRIBUTING.md`, and the upstream-propagation workflow.
