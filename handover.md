# Handover - written 2026-09-01, nothing in flight

## In flight

Nothing. Five commits, each gated and CI-green before the next started.

## Committed, or not

`HEAD == origin/master == ce5f856`, working tree clean, plugin `5.299.1`. Nothing uncommitted.

The session's commits, oldest first: `d165a3a` `212b9a7` `d190494` (the tell hooks) and `448f207`
`ce5f856` (the guard slice), plus `93a71a3` recording progress against the backlog.

## What was done, in one paragraph, because the repo cannot tell you WHY

Two pieces of the same audit. First, the `commit-tell-sweep` finding from report 20 of the
2026-08-28 script wave: both tell hooks decoded with `errors="replace"`, which mints U+FFFD per
undecodable byte, and U+FFFD is itself a tell - so the reader manufactured what the detector hunts
for. Fixing that opened a silent miss (a Windows-editor em-dash is byte `0x97`, dropped and
reported clean), so the encoding is now its own finding. Second, the seven gate and guard reports
of that same wave were adjudicated against the live tree: 38 claims, 24 drivable, five under-blocks
shipped.

## Decided, and why - do not reopen

- **`errors="ignore"` plus an explicit encoding finding, not one or the other.** Dropping the bytes
  silently trades a loud wrong answer for a quiet one; both tell hooks now name the first bad byte.
- **A `-F` file's hits report codepoints (`1: U+2014`), never the line.** PreToolUse runs before the
  call is approved, so the path is only a string the caller named. An inline `-m` message is still
  quoted in full: the caller typed it. Uniform, deliberately - keying it on where the path lives
  would put a security property behind a path comparison inside a fail-open hook.
- **One shared `tell_chars.decode_utf8`.** The detector and its rewriter twin had drifted on how a
  file is read; one function is what stops that recurring.
- **`{{` is a template marker only when not followed by `"` or `{`.** Measured before keeping it:
  across 24,112 structured files on this machine, zero would be newly validated. That is evidence
  from one machine, not a proof about every repo.
- **No length cap on the probe gate's label prefix.** An arbitrary number deciding a
  security-shaped verdict fails in the silent direction; the newly-accepted false positive is
  pinned by its own test instead.
- **The exception phrase list stays short** (`other than`, `except`, `besides`, `apart from`). It
  fails toward DENY, and `but`/`only` in that list would silently disarm the gate.

## Decided against, and why

- **Keying the template skip on path or directory layout.** Considered and rejected: it encodes
  layout assumptions into a hook shipped to other people's repos, and fails loudly for a template
  that lives outside the convention.
- **Fixing the four confirmed findings outside the chosen scope.** They are backlog item 85 now,
  with their mechanisms written down, rather than half-done here.

## Still open, untouched

Fifteen items in `OPEN-WORK.md`, ranked. Read that file; summarising it here is the re-encoding
that file exists to prevent.

## The exact next action

**`OPEN-WORK.md` item 10** - still the top-ranked open item and the oldest, the user's 2026-08-27
audit directive. The seven gate/guard reports are done. Next are the six reports never mentioned
anywhere in `TRIAGE.md`:

    self-improve-audit  warn-inline-powershell  session-start
    subagent-backstop-nudge  subagent-brief  session-banner

in `/media/srv-main-softdev/projects/public/KI/scriptwave-2026-08-28/reports/`, about 55 KB.

Two things that pass are worth carrying:

- Extract claims with `^\s*[*_#>\-\s]*FINDING:\s*([A-Z][A-Z-]*)\s*\|` - seven reviewers wrote
  `**FINDING: BUG | ...**`, which a `^FINDING` anchor misses entirely, and that undercount was
  filed as "clean" three times in the original session.
- Adjudicate by DRIVING the hook with a JSON event against the live tree, and give every probe a
  control that must answer the opposite. Several 2026-08-28 claims are already fixed, and two of my
  own instruments were wrong before they were right.

A report of 2-4 KB is CLOBBERED, not clean - the Stop hook overwrote it with a capture summary.
Its real content is the sibling `.recovered` file.

If you do something else instead, say so in the next handover and why - recency is not a reason.

## Files that matter

- `OPEN-WORK.md` - the backlog; its header states the line format and ranking rules.
- `/media/srv-main-softdev/projects/public/KI/scriptwave-2026-08-28/TRIAGE.md` - the audit record.
  Its `GUARD SLICE ADJUDICATED 2026-09-01` section lists what was refuted, so it is not re-filed.
  This directory is beside the repo, not inside it: it is 19 MB and the repo is public.
- `plugins/bitranox/hooks/tell_chars.py` - `decode_utf8`, `find_tell_codepoints`, `_scannable`.
- `plugins/bitranox/hooks/subagent-probe-capability-gate.py` - `_BULLET_OR_LABEL`, `_EXCEPTION`,
  `_APOSTROPHES`, `_declares_text_only`.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
```

`repo-gate: all checks passed`; 4211 passed / 13 skipped / 1 xfailed at `ce5f856`.

## Two traps this session paid for

- **A version bump needs BOTH `plugins/bitranox/.claude-plugin/plugin.json` AND `pyproject.toml`.**
  The gate catches the drift, but only after you have written the changelog entry.
- **Do not put `git fetch` in the same Bash call as the commit or push.** The PreToolUse gate reads
  its answer before any statement runs, so that shape can never satisfy it, and a block discards
  the prep with it.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
