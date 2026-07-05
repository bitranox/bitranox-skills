# Installation

This chapter answers: how to install the plugin, how to keep it updated, what Windows needs, and
how to check that everything is running.

## Install

```text
/plugin marketplace add bitranox/bitranox-skills
/plugin install bitranox@bitranox-skills
```

**Install at user scope** (the default for `/plugin install`). This matters for the memory: the
self-learning routes each lesson to the layer where it belongs - a project rule into that project,
a cross-project rule higher up. That only works if the skills and their hooks run in every
project. A project-scoped install would confine the capture gate and the layered memory to a
single repo, and cross-project learning would be lost.

## Enable auto-update (recommended)

By default the marketplace updates only when you run `/plugin marketplace update bitranox-skills`.
To get fixes and new skills automatically, turn on auto-update - a one-time opt-in (a plugin
cannot set this for you; it is a user/admin choice):

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
asks you to run `/reload-plugins`. Until you enable it, the session start shows a one-line
reminder; that reminder silences itself once auto-update is on. To dismiss it without enabling,
create an empty `~/.claude/.bitranox-no-autoupdate-nudge` file.

## How an update reaches your sessions

The marketplace clone and the plugin cache are machine-global, so one
`/plugin marketplace update bitranox-skills` updates them for the whole machine:

- **New sessions** pick up the new version automatically.
- **A session that is already running** keeps the version it started with until you run
  `/reload-plugins` in it (or restart it). Updating alone does not change a live session.

## Windows: install Git for Windows

On macOS and Linux everything works out of the box. On **Windows**, install
[Git for Windows](https://gitforwindows.org/) so Claude Code has **Git Bash**. The skills and
their Python helpers run fine either way, but every hook is launched through a small bash shim
(the same pattern Claude Code's own official plugins use). Without Git for Windows, Claude Code
falls back to PowerShell and the hooks are simply skipped - they never error a turn, but the
capture gate will not nudge you and the guards will not fire. With Git for Windows installed,
everything runs normally; you can also run any skill manually at any time.

The shim is designed for **Git Bash** specifically. WSL and Cygwin bash are neither required nor
supported: they mount Windows drives differently and resolve a Linux `python`, which breaks the
native-path design. Claude Code invokes its own Git Bash, so this is normally a non-issue; if a
hook silently does nothing on Windows, check that `uname -s` under the hook shell reports
`MINGW`/`MSYS` (Git Bash) and not `*Microsoft*` (WSL), and that `CLAUDE_CODE_GIT_BASH_PATH` (if
set) points at Git Bash. The shim refuses to run under an unexpected shell rather than misbehave.

## Verify the install

- `/plugin` -> **Plugins** lists `bitranox` from `bitranox-skills`.
- Ask Claude to "view my memory settings": the knob table it prints (see
  [reference.md](reference.md)) proves the skills and their Python helpers run on your machine.
- Skills answer as `/bitranox:<skill>` - try `/bitranox:meta-memory-settings`.

Next: [setup.md](setup.md) for the first-session decisions.
