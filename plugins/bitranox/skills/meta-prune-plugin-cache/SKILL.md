---
name: meta-prune-plugin-cache
description: Use when ~/.claude has grown large or the disk is filling, when the Claude Code plugin cache holds a directory per published version, when temp_subdir_*.clone or temp_git_* leftovers pile up after marketplace add/update operations, or before deleting anything under ~/.claude/plugins/cache while a session is running.
---

# Pruning the Claude Code plugin cache

## Overview

`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` keeps a FULL copy per version and
drops none, so the marketplace you publish to grows by a whole plugin on every release. Beside
those sit `temp_subdir_*.clone` and `temp_git_*` directories at the CACHE ROOT: temporary clones
from marketplace add/update operations that a killed operation abandons, ~50MB each.

One question decides the whole job: **which versions is a live session still using?** Delete the
directory a running session loaded from and its skills and hooks stop loading until it restarts.

## The cache answers that question itself

Every version directory carries `.in_use/<pid>` locks, one per Claude Code process that loaded
it, each holding `{"pid":N,"procStart":"<start time>"}`.

A lock is evidence only while its process lives. `procStart` is there so a REUSED pid cannot pass
for the original holder: a lock whose pid is gone, or whose start time disagrees with the running
process, is stale and keeps nothing. An `.in_use` directory that is empty or absent means no
session has claimed that version.

**Do not reach for `lsof`, `pgrep`, or transcript mtimes.** Hooks are launched per invocation and
hold no file open between calls, so an open-file search finds nothing and reads as "free" for a
version that is very much in use. The lock file is the direct instrument; the rest are proxies
that answer a different question.

## Use the tool

`scripts/pluginprune.py` classifies every version directory AND every `temp_*` leftover in ONE
pass, stating a reason per line. Paths here are relative to this skill's own directory, which
is announced when the skill loads. Dry run by default; `--apply` removes exactly what the plan
listed and never re-scans for new candidates. That set can only shrink: a session starting
between the plan and the apply claims its version, and that directory is refused instead.

```bash
uv run scripts/pluginprune.py             # the plan, with sizes and a reason per kept directory
uv run scripts/pluginprune.py --apply     # remove exactly that
uv run scripts/pluginprune.py --json      # {ok, command, data, skipped}; 0 fine, 1 refused, 2 usage
```

Run `--help` for the rest (`--marketplace`, `--keep`, `--min-age`, `--settings`).

It keeps a version with a live lock, the `installPath` from `installed_plugins.json` (what a
fresh session resolves to), anything a settings file pins, anything `--keep` names, and the
sole version of a plugin a settings file's `enabledPlugins` lists. It reads each `temp_*`
leftover's own mtime and keeps any younger than `--min-age` (60m), so no separate age check is
needed. It refuses symlinks and paths outside the cache.

A plugin nothing references at all is planned even as the only version: that is what an
uninstalled plugin leaves behind, and nothing else reclaims it. `enabledPlugins` is the guard
that makes that safe, and it applies only to a sole version - it names a PLUGIN, never a
version, so honouring it per version would preserve the entire history of everything enabled.

When locks exist but none is live it says so on stderr rather than guessing: a session whose
version cannot be identified is worth confirming by hand, so pass that version with `--keep`.

When NOT ONE version directory has an `.in_use` directory at all, it refuses them and exits
non-zero. An idle machine leaves that directory behind EMPTY, so its total absence means the
mechanism was renamed or dropped, and every version would otherwise read as unused - the
running session's included. `--allow-missing-locks` overrides it once you know why.

## Where the space actually is

Count version directories PER PLUGIN, never sort by size. A plugin with one version that
something still references is footprint, not waste. Apply that test per plugin, not per
marketplace - a marketplace can be mixed - though in practice only the one you publish to
accumulates, and the one you merely consume is routinely the biggest directory while yielding
nothing but its uninstalled leftovers.

A long-running session pins every version it has loaded, not just its current one, so with
several old sessions open most of the cache is legitimately in use. The yield rises once they
end; that is not a reason to override a live lock.

## Common mistakes

| Mistake                                             | What happens                                                                 |
|-----------------------------------------------------|------------------------------------------------------------------------------|
| Keeping only the newest version                     | The running session may sit on an older one it loaded before the last update |
| `lsof` / `pgrep` to find the session's version      | Finds nothing, so a live version reads as free                               |
| Deleting the biggest marketplace directory          | Referenced single-version plugins are footprint, not waste                   |
| Looking for `temp_*` inside a marketplace directory | They sit at the cache ROOT, one level up                                     |
| `rm -rf` straight from a glob                       | No plan, no reasons, no refusals, and no way to check before it runs         |

After pruning, confirm a kept version is intact (its `skills/` and `hooks/` are populated). A
fresh session re-fetches whatever it needs, so a wrong deletion costs a re-fetch, not data.

One side effect: a memory fact captured with the working directory inside a cache version
directory leaves its POINTER there and its BODY at the tree anchor, so pruning strands the body
where no integrity check looks. See `bitranox:meta-self-improve`.
