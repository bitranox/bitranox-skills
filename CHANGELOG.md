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
