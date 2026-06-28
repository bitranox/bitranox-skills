# bitranox-skills

A Claude Code plugin marketplace: the **bitranox** skill collection - a set of
software-engineering skills refined over real day-to-day work (planning, debugging, code
review, clean architecture, language and tool references, humanizing) - finally gathered into
one tidy, installable marketplace. On top of the skills it adds two things that make the
collection compound rather than just sit there: **automatic self-learning** (a layered memory
that turns each session's lessons into durable, reusable knowledge) and **user contribution**
(when a lesson proves broadly useful, the system can package it as a skill and propose it back
upstream, so the shared marketplace grows).

> **If you install just one thing, make it `self-improve`.** It turns each session's corrections,
> gotchas, and discoveries into durable, layered memory - so the same lesson is not re-learned - and
> it propagates skill fixes back upstream on its own. The rest of the collection is handy; this one
> compounds over time.

This repo is both the marketplace (`.claude-plugin/marketplace.json`) and the single
plugin it ships (`plugins/bitranox/`). Skills are invoked as `/bitranox:<skill>`.

## Install

```text
/plugin marketplace add bitranox/bitranox-skills
/plugin install bitranox@bitranox-skills
```

**Install at user scope** (the default for `/plugin install`). For `self-improve` this is not just
a convenience, it is the point. `self-improve` routes each learning to the layer where it belongs:
a project-specific rule goes into that project, while a cross-project or tool/shell/OS rule goes
into your global config. That only works if the skill (and its Stop-hook gate) run everywhere. A
project-scoped install would confine `self-improve`, its gate, and its PR logic to a single repo,
so global and cross-project learnings would never be captured and the layered memory that makes the
skill worthwhile would be lost. Install it at user scope.

Update later with `/plugin marketplace update bitranox-skills`. Because `plugin.json`
sets a `version`, bump it when you want installed copies to pick up changes (or remove
the `version` field to track every commit SHA).

### Enable auto-update (recommended)

By default the marketplace updates only when you run `/plugin marketplace update`. To get fixes
and new skills automatically, turn on **auto-update** for this marketplace - a one-time opt-in
(a plugin cannot set this for you; it is a user/admin choice):

- **UI:** `/plugin` -> **Marketplaces** -> `bitranox-skills` -> **Enable auto-update**, or
- **settings.json** (`~/.claude/settings.json` for you, or `.claude/settings.json` for a team):

  ```json
  {
    "extraKnownMarketplaces": {
      "bitranox-skills": {
        "source": { "source": "github", "repo": "bitranox/bitranox-skills" },
        "autoUpdate": true
      }
    }
  }
  ```

Auto-update runs **at startup**: it refreshes the marketplace and updates installed plugins, then
asks you to run `/reload-plugins` (a running session still needs `/reload-plugins` or a restart to
load a new version). Until you enable it, the SessionStart hook shows a one-line reminder; that
reminder self-silences once auto-update is on. To dismiss it without enabling, create an empty
`~/.claude/.bitranox-no-autoupdate-nudge` file.

### Windows: install Git for Windows

On macOS and Linux everything works out of the box. On **Windows**, install
[Git for Windows](https://gitforwindows.org/) so Claude Code has **Git Bash**. The skills and
their Python helpers run fine either way, but the `self-improve` **Stop-hook gate** is launched
through a small bash shim (the same pattern Claude Code's own official plugins use). Without Git
for Windows, Claude Code falls back to PowerShell and the gate is simply skipped - it never errors
a turn, but it also will not auto-nudge you to capture learnings. With Git for Windows installed,
the gate fires normally. You can still run `self-improve` manually at any time.

The gate is designed for **Git Bash** specifically. WSL and Cygwin bash are neither required nor
supported: they mount Windows drives differently and resolve a Linux `python`, which breaks the
native-path design. Claude Code invokes its own Git Bash, so this is normally a non-issue; if the
gate silently does nothing on Windows, check that `uname -s` under the hook shell reports
`MINGW`/`MSYS` (Git Bash) and not `*Microsoft*` (WSL), and that `CLAUDE_CODE_GIT_BASH_PATH` (if
set) points at Git Bash. The shim refuses to run under an unexpected shell rather than misbehave.

## What you get

- **40+ skills** under the `bitranox` namespace (`/bitranox:process-plan-brainstorming`,
  `/bitranox:process-debug-systematic`, ...). Claude can also invoke them automatically when
  a task matches a skill's description.
- **A `Stop` hook** (`hooks/self-improve-gate.py`, launched via `hooks/run-python.sh` and wired
  in `hooks/hooks.json`) that, at the end of a turn, runs a cheap check for a learning signal (a
  correction, an explicit "remember", a self-admitted miss) and nudges Claude to run the
  `self-improve` skill. The gate logic is pure Python, but `hooks.json` launches it through a
  small bash shim, like Claude Code's own official plugin hooks. So it fires on macOS and Linux,
  and on Windows when **Git for Windows** (Git Bash) is installed; without it Claude Code runs
  hooks under PowerShell and the gate is simply skipped (it never errors a turn). Installing the
  plugin registers this hook automatically, so you no longer need a manual entry in
  `~/.claude/settings.json` for it.
- **A `PreToolUse` Bash guard** (`hooks/block-pgrep-self-match.py`, launched the same way) that
  blocks the `pgrep`/`pkill` bracket-trick self-match: a command like
  `pgrep -f "[n]ginx"; echo "nginx up?"` where the bracketed pattern's literal (`nginx`) also
  appears verbatim in an echo/label, which re-introduces it into the shell's own argv and makes
  the check self-match (a false positive, or `pkill` killing its own shell). It blocks only that
  precise case, so it almost never false-fires, and fail-opens like the gate.

## Skills

Skills follow a category-prefix naming scheme, `<category>-[<sub>-]<name>` (e.g.
`coding-python-clean-architecture`, `compuse-ssh`, `marketing-rory`, `files-edit-json`). The
category vocabulary lives in [`plugins/bitranox/skill-taxonomy.json`](plugins/bitranox/skill-taxonomy.json)
and is enforced by the repo gate.

The full, always-current catalog - grouped by domain - is the **Skills Span Every Domain** list in
`bitranox:meta-using-bitranox-skills`
([`SKILL.md`](plugins/bitranox/skills/meta-using-bitranox-skills/SKILL.md)); the gate keeps it in
sync with the shipped skill directories, so it never drifts. Browse
[`plugins/bitranox/skills/`](plugins/bitranox/skills/) for the directories.

## How the self-learning memory works

A layered memory that is meant to get better the more you use it. Knowledge is filed by how far it
reaches: per-project notes in Claude Code's native Auto memory, cross-project rules in a global layer
at `~/.claude/rules/bitranox/` (loaded into every session, and kept separate from your hand-written
`CLAUDE.md`), and `CLAUDE.md` only for must-hold rules at an in-between level. Concrete-but-broadly-
useful facts are promoted as-is, not watered down.

Five skills run it (the first is nudged automatically; the rest you can invoke, and the memory hooks
call them when relevant):

- **`bitranox:meta-self-improve`** - per-turn capture. A `Stop` hook notices a learning signal (a
  correction, a "remember", a self-admitted miss) and nudges it to record the lesson at the right
  altitude.
- **`bitranox:meta-dream-project`** (`/dream-project`, "dream", "consolidate memory") - the frequent,
  cheap consolidation of the *current* project, like sleep. It backs up first, then dedups, generalizes,
  promotes by scope, re-wires, and prunes obsolete or duplicate notes - so memory stays small and sharp.
  (There is no forgetting by age or use - only content-based removal.) Has an off / auto / propose mode.
- **`bitranox:meta-dream-global`** (`/dream-global`, "consolidate across projects") - the occasional,
  expensive cross-project pass: scans every project store, factors recurring / broadly-useful knowledge
  up to the global layer, and pulls sibling-tree knowledge into projects. Run it now and then, not every
  time.
- **`bitranox:meta-collect-knowledge`** (`/collect-knowledge`) - pulls knowledge from your *other*
  projects that is relevant to the current one (native cascade alone cannot reach sibling trees), and
  seeds a fresh project from what you already know.
- **`bitranox:meta-memory-settings`** (`/memory-settings`) - view, change, or reset the behaviour knobs
  (dream mode, privacy, promotion eagerness, nudges). A choice is recorded once and applied
  automatically.

> **Back up before your first full dream - especially the global one.** Each dream backs itself up
> first, but until you have watched it a few times and trust how it reshapes things, take your own
> backup of your memory and `CLAUDE.md` files before running it. The global pass (`/dream-global`) can
> lift rules into the layer that loads in *every* project, so verify it behaves the way you want on your
> own data before letting it run unwatched. A simple copy works:
> `zip -r ~/memory-backup.zip ~/.claude/projects/*/memory ~/.claude/rules` (add your `CLAUDE.md` files).

For the ideas behind all of this, in plain language and concepts over mechanics, see
[docs/self-learning-memory.md](docs/self-learning-memory.md).

## AI transparency

This project is built by a human, with an AI assistant used as a tool under that direction. Two short
pages spell out how:

- [ai-transparency.md](ai-transparency.md) - exactly where AI was and was not used in *this* repo,
  what is tested, and how to check the work yourself.
- [ai-stance.md](ai-stance.md) - the general view on AI-assisted development behind that choice.

## Layout

```text
bitranox-skills/
  .claude-plugin/
    marketplace.json            # marketplace catalog, lists the bitranox plugin
  plugins/
    bitranox/
      .claude-plugin/
        plugin.json             # plugin manifest (name: bitranox)
      skills/
        <skill>/SKILL.md        # one directory per skill (plus any supporting files)
      hooks/
        hooks.json              # registers the Stop gate and the PreToolUse Bash guard
        self-improve-gate.py    # the self-improve learning-signal gate (cross-platform)
        block-pgrep-self-match.py  # PreToolUse guard against the pgrep/pkill self-match
        run-python.sh           # interpreter-resolver launcher for both
  README.md
  CONTRIBUTING.md
```

## Credits

Most skills here are custom-built or adapted. Some general workflow skills
(brainstorming, systematic-debugging, test-driven-development, verification-before-completion)
originate from public skill libraries (for example Obra Superpowers and the Vercel Agent
Skills Directory) and have been adapted here. `markitdown` and `rory` build on upstream
sources (the MarkItDown document converter and Rory Sutherland's public talks and
writing, respectively).

Skills adapted from a third-party source under a permissive license carry their original
copyright and license text in [`plugins/bitranox/THIRD_PARTY_NOTICES.md`](plugins/bitranox/THIRD_PARTY_NOTICES.md).

## License

MIT - see [`LICENSE`](LICENSE). Adapted third-party skills retain their own permissive licenses;
see [`plugins/bitranox/THIRD_PARTY_NOTICES.md`](plugins/bitranox/THIRD_PARTY_NOTICES.md).
