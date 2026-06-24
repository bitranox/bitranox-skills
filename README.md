# bitranox-skills

A Claude Code plugin marketplace that distributes the **bitranox** skill collection:
software-engineering workflow skills (planning, debugging, code review, clean
architecture, language and tool references, humanizing) plus a self-improvement loop.

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

- **25 skills** under the `bitranox` namespace (`/bitranox:brainstorming`,
  `/bitranox:systematic-debugging`, ...). Claude can also invoke them automatically when
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

| Skill                          | Description                                                                                           |
|--------------------------------|-------------------------------------------------------------------------------------------------------|
| bash-clean-architecture        | Clean ports-and-adapters architecture for Bash 4.3+ scripts and multi-file projects.                  |
| bash-reference                 | Exact GNU Bash 5.3 reference: builtins, expansions, redirections, tests, arrays, traps.               |
| brainstorming                  | Collaborative design exploration before any creative work; surfaces intent and requirements.          |
| enhance-code-quality           | Rate, audit, and improve a project's code quality with a 0-10 assessment and concrete fixes.          |
| force-using-skills             | Establishes that applicable skills must be invoked before any response.                               |
| humanize-de                    | Remove signs of AI-generated writing from German text.                                                |
| humanize-en                    | Remove signs of AI-generated writing from English text.                                               |
| markitdown                     | Convert files and office docs (PDF, DOCX, PPTX, XLSX, images, audio, HTML, ...) to Markdown.          |
| md-table-formatting            | Create, edit, and realign Markdown tables with proper column alignment.                               |
| performance                    | Review Python for performance issues: caching, uncompiled regex, hot-spot profiling.                  |
| plan-executor                  | Execute a written implementation plan in a separate session with review checkpoints.                  |
| plan-writer                    | Turn a spec or requirements into a step-by-step implementation plan before coding.                    |
| proxmox                        | Proxmox VE 9.1.2 reference: clusters, VMs, containers, storage, Ceph, SDN, firewall, HA, backups.     |
| python-clean-architecture      | Layered ports-and-adapters architecture for Python 3.10+ (domain, UoW, outbox, idempotency).          |
| python-libraries-to-use        | Standardized library choices for Python projects; enforces preferred tools.                           |
| python-performance-reviewer    | Performance-analysis sub-agent: profile with real test suites, validate claims with benchmarks.       |
| rory                           | Marketing, branding, pricing, and behavioural-science angle (what would Rory Sutherland do).          |
| rpyc                           | Build transparent RPC, distributed computing, and remote object proxying in Python with RPyC.         |
| self-improve                   | Capture a session's learnings into the right memory or CLAUDE.md layer so they are not re-learned.    |
| skill-writer                   | Create, structure, test, and deploy SKILL.md skill files (TDD-based).                                 |
| systematic-debugging           | Root-cause-first debugging: find the cause before proposing fixes.                                    |
| test-driven-development        | Write tests first, watch them fail, then write minimal code to pass.                                  |
| textual                        | Textual TUI framework documentation reference (API, guides, CSS, widgets).                            |
| uv                             | Reference for the uv package manager (v0.10.2): projects, lockfiles, tools, Docker, CI/CD, migration. |
| verification-before-completion | Require running verification commands and confirming output before claiming success.                  |

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

## License

MIT
