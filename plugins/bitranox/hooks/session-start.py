#!/usr/bin/env python3
"""SessionStart hook: inject the SMALL session essentials - the memory-retrieval standing rule,
a pending miss-audit, and the self-silencing nudges.

The big skills-first banner is emitted by its OWN hook command (session-banner.py). The split is
load-bearing: the harness persists an oversized additionalContext to a file and injects only a
~2KB preview, so anything appended AFTER a ~10KB banner (this hook's essentials, before the split)
never reached context. Emitted separately and kept SMALL (see the size test), the essentials always
land inline.

Emits the Claude Code SessionStart contract on stdout:
  {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}
plus an optional top-level "systemMessage" - a one-line, self-silencing reminder to enable
marketplace auto-update when it is off (it cannot set it; only the user/admin can).
json.dumps does the escaping (newlines/quotes), so no hand-rolled JSON escaping.

Pure standard library. Every failure path emits nothing and exits 0, so a broken
or slow hook never blocks or delays a session.
"""
import datetime
import json
import os
import re
import sys
import time
from pathlib import Path

from self_improve_signals import (
    audit_file,
    dream_due,
    knowledge_store_empty,
    load_config,
    mark_seeded,
    project_unseeded,
    read_contributions,
)


_RETRIEVAL_TMPL = (
    "<BITRANOX-MEMORY-RETRIEVAL>\n"
    "Your loaded context includes a memory index: lines of the form\n"
    "  - [Title](mem:<slug>) - hook\n"
    "in the CLAUDE.local.md cascade. Those are always-loaded POINTERS - the Title + hook are present, "
    "but the full fact BODY is NOT preloaded. When a hook is relevant to your CURRENT task and you need "
    "the detail behind it, retrieve that body ON DEMAND by Reading:\n"
    "  %(anchor)s/.claude-memory/facts/<slug>.md\n"
    "(example: mem:no-em-dashes -> %(anchor)s/.claude-memory/facts/no-em-dashes.md)\n"
    "Do this mid-task whenever a relevant hook needs its body; the per-prompt recall hook only surfaces "
    "keyword matches at prompt time, so pull anything else yourself. Read a body ONLY when its hook is "
    "genuinely relevant - never bulk-read the index.\n"
    "</BITRANOX-MEMORY-RETRIEVAL>"
)


def retrieval_context(proj):
    """A standing rule teaching the model to fetch a fact body ON DEMAND from the central UUID store,
    with the concrete anchor path baked in. Returns None when there is no anchor or no store yet (so a
    fresh project with no facts is not told to retrieve from an empty store). Fail-open."""
    try:
        import uuid_store as us
        anchor = us.resolve_anchor(proj)
        if anchor is None or not us.central_facts_dir(anchor).is_dir():
            return None
        return _RETRIEVAL_TMPL % {"anchor": str(anchor)}
    except Exception:  # noqa: BLE001 - a hook must never wedge a session
        return None


def _read_event():
    try:
        return json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: fall back, never wedge
        return {}


def _proj(event):
    return event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def audit_context(proj):
    """Surface (and consume) a pending SessionEnd miss-audit for this project, if any.

    The SessionEnd hook (self-improve-audit.py) writes candidate gate-misses to a per-project
    file; here we inject it once so the model reviews them, then delete it so it is not
    resurfaced.
    """
    try:
        path = audit_file(proj)
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8").strip()
        path.unlink()  # consume once
    except Exception:  # noqa: BLE001 - unreadable/undeletable: skip, never wedge
        return None
    return text or None


def contrib_context(proj):
    """Surface PENDING upstream contributions - and, unlike the audit, do NOT consume them.

    A learning that warrants a skill/hook change used to reach the marketplace only if the model
    authored the self-PR before the session ended: nothing recorded the INTENT, so it died with the
    context while the private fact survived. The queue is that missing state, so it must SURVIVE
    being read - it stands until it actually ships and is drained.
    """
    try:
        recs = read_contributions(proj)
        if not recs:
            return None
        lines = ["- %s%s%s" % (r.get("what") or "",
                               " -> %s" % r["target"] if r.get("target") else "",
                               " (%s)" % r["why"] if r.get("why") else "")
                 for r in recs]
        return ("%d PENDING UPSTREAM CONTRIBUTION(S) - learnings already judged skill/hook-worthy "
                "that have NOT shipped yet. They persist until shipped, so pick them up when the "
                "work suits (route via bitranox:meta-self-improve -> references/upstream-propagation.md; "
                "a dream drains the queue once they land):\n%s" % (len(recs), "\n".join(lines)))
    except Exception:  # noqa: BLE001 - never wedge a session start
        return None


#: One open backlog line: "- [ ] (YYYY-MM-DD) [rank] ORIGIN: text | field: value | ..."
#: The date field is taken loosely and parsed after, because every honest form for "nobody
#: recorded this" must survive - a trailing "?" and the bare word "unknown" both. A parser that
#: drops them makes the admitted guess invisible and leaves only the invented date showing.
_OPEN_WORK_RX = re.compile(r"-\s*\[ \]\s*\(([^)]*)\)\s*\[(\d+)\]\s*(\S.*)")
_ISO_DATE_RX = re.compile(r"(\d{4})-(\d{2})-(\d{2})\??$")
#: The whole essentials block must stay small or the harness persists it to a file and injects
#: only a ~2KB preview, which is how the retrieval rule once stopped reaching context at all.
#: The open-work block therefore gets what the OTHER blocks left, never a fixed share: a fixed
#: item COUNT recreated the sink it exists to remove, and a fixed BYTE share passed its unit test
#: on a fixture that had no other blocks in it, then overran on the real repo by 429 bytes.
_OPEN_WORK_HEADER = (
    "%d OPEN-WORK ITEM(S) - the standing backlog at OPEN-WORK.md, ordered by RANK and "
    "NOT by what was touched last. It persists until an item is closed there, so reading it "
    "does not clear it. Whatever you do next should be the top-ranked item, or you should say "
    "plainly why a lower-ranked one goes first:\n"
)
_ESSENTIALS_CEILING_BYTES = 3300
#: When the other blocks have spent the ceiling, the backlog degrades to this one line rather
#: than to nothing (hiding it is the failure the file exists to stop) or to a breach (going
#: over makes the harness persist the WHOLE essentials block and preview ~2KB, which hides it
#: anyway - a floor that protects the backlog by a mechanism that hides it is self-defeating).
_OPEN_WORK_COMPACT = "%d OPEN-WORK ITEM(S) standing - read OPEN-WORK.md; no room to list them here."
_OPEN_WORK_HEAD_CHARS = 96


def _parse_open_work(text, today=None):
    """Open items from OPEN-WORK.md as (rank, raised_date, text), ordered by RANK then age.

    Ordering by rank rather than by file order is the whole point: the failure this file exists
    to stop is a fresh micro-task outranking a standing one purely by being recent.
    """
    today = today or datetime.date.today()
    items = []
    for raw in text.splitlines():
        m = _OPEN_WORK_RX.match(raw.strip())
        if not m:
            continue                                  # closed "[x]" items and prose both land here
        raised = _parse_raised(m.group(1))
        items.append((int(m.group(2)), raised, m.group(3).strip()))
    # An undated item sorts last within its rank: it makes no age claim, so it cannot displace one
    # that does. datetime.date.max is the sentinel because None will not compare against a date.
    items.sort(key=lambda it: (it[0], it[1] or datetime.date.max))
    return items


def _parse_raised(token):
    """The date a line claims, or None when it admits it does not have one."""
    m = _ISO_DATE_RX.match(token.strip())
    if not m:
        return None                                   # "unknown", empty, anything unparseable
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:                                # a typo'd date must not drop the item
        return None


def _age(raised, today):
    if raised is None:
        return "date unknown"
    days = (today - raised).days
    if days <= 0:
        return "raised today"
    return "raised %d day%s ago" % (days, "" if days == 1 else "s")


def open_work_context(proj, today=None, budget=None):
    """Surface the STANDING backlog, ranked, and - like the contribution queue - do NOT consume it.

    `handover.md` describes one moment and is overwritten wholesale, so anything outliving the
    session survives only by being retyped from memory, and shrinks on every rewrite: measured,
    five tracked items lost their sizes and then their heading across three rewrites in one day.
    This block is the durable half, and it prints rank-first so age cannot be mistaken for
    priority. Fail-open: any problem reading or parsing it emits nothing.
    """
    try:
        today = today or datetime.date.today()
        raw = (Path(proj) / "OPEN-WORK.md").read_text(encoding="utf-8", errors="replace")
        items = _parse_open_work(raw, today)
        if not items:
            return None
        head = _OPEN_WORK_HEADER % len(items)
        allowed = _ESSENTIALS_CEILING_BYTES if budget is None else budget
        if allowed < len(head.encode("utf-8")) + _OPEN_WORK_HEAD_CHARS:
            return _OPEN_WORK_COMPACT % len(items)
        lines, used = [], len(head.encode("utf-8"))
        for rank, raised, what in items:
            line = "- [%d] (%s) %s" % (rank, _age(raised, today), what[:_OPEN_WORK_HEAD_CHARS])
            cost = len(line.encode("utf-8")) + 1
            # Always emit the first, however long: one oversized item must not reduce the whole
            # block to a bare count, which would hide the very item ranked most urgent.
            if lines and used + cost > allowed:
                break
            lines.append(line)
            used += cost
        hidden = len(items) - len(lines)
        if hidden:
            lines.append("- ... and %d more in OPEN-WORK.md" % hidden)
        return head + "\n".join(lines)
    except Exception:  # noqa: BLE001 - never wedge a session start
        return None


_NUDGE = (
    "bitranox-skills: marketplace auto-update is OFF, so you will not get fixes and new skills "
    "automatically. Enable it: /plugin > Marketplaces > bitranox-skills > Enable auto-update, or "
    'add "autoUpdate": true to the "bitranox-skills" entry under extraKnownMarketplaces in '
    "~/.claude/settings.json. (Auto-update runs at startup; a running session still needs "
    "/reload-plugins or a restart to load an update.) To silence this without enabling, create "
    "~/.claude/.bitranox-no-autoupdate-nudge"
)


def _autoupdate_enabled(proj):
    """True if extraKnownMarketplaces['bitranox-skills'].autoUpdate is set in user/project settings."""
    candidates = [
        Path.home() / ".claude" / "settings.json",
        Path(proj) / ".claude" / "settings.json",
        Path(proj) / ".claude" / "settings.local.json",
    ]
    for c in candidates:
        try:
            data = json.loads(c.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - missing/invalid: skip this source
            continue
        entry = (data.get("extraKnownMarketplaces") or {}).get("bitranox-skills") or {}
        if entry.get("autoUpdate") is True:
            return True
    return False


def autoupdate_nudge(proj):
    """A one-line, self-silencing reminder to enable marketplace auto-update; None when off."""
    try:
        optout = Path.home() / ".claude" / ".bitranox-no-autoupdate-nudge"
        if optout.exists() or _autoupdate_enabled(proj):
            return None
    except Exception:  # noqa: BLE001 - never let detection wedge the session
        return None
    return _NUDGE


_DREAM_NUDGE = (
    "<BITRANOX-DREAM-DUE>\n"
    "A memory consolidation is due. Run bitranox:meta-dream-tree to dedup / merge / generalize / prune "
    "the memory store (it backs up first), or say 'skip'. Adjust via bitranox:meta-memory-settings: "
    "dream_mode 'off' silences this, 'auto' stops the per-change asking.\n"
    "</BITRANOX-DREAM-DUE>"
)


def dream_nudge(proj):
    """Self-silencing nudge to run meta-dream-tree when a consolidation is due (off when mode=off)."""
    try:
        if not dream_due(proj):
            return None
    except Exception:  # noqa: BLE001 - detection must never wedge the session
        return None
    return _DREAM_NUDGE


_NEWPROJECT_NUDGE = (
    "<BITRANOX-NEW-PROJECT>\n"
    "This project has no memory yet. Run bitranox:meta-collect-knowledge (/collect-knowledge) to seed "
    "it from your existing knowledge tree, so it starts informed. Say 'skip' to ignore.\n"
    "</BITRANOX-NEW-PROJECT>"
)


def _collect_skill_available():
    """True if the meta-collect-knowledge skill is installed (Phase 2). The new-project nudge stays
    dormant until it is, so it never points at a missing skill."""
    try:
        root = os.environ.get("CLAUDE_PLUGIN_ROOT")
        base = Path(root) if root else Path(__file__).resolve().parent.parent
        return (base / "skills" / "meta-collect-knowledge" / "SKILL.md").is_file()
    except Exception:  # noqa: BLE001
        return False


def newproject_nudge(proj):
    """Fire ONCE for a fresh, unseeded project - only when the collect skill is installed AND there
    is knowledge elsewhere to seed from. Marks the project seeded so it self-silences."""
    try:
        if not _collect_skill_available():
            return None
        if not project_unseeded(proj) or knowledge_store_empty(proj):
            return None
        mark_seeded(proj)  # fire once
    except Exception:  # noqa: BLE001 - never wedge the session
        return None
    return _NEWPROJECT_NUDGE


def _nudges_on():
    """Honor the user's config: nudges can be switched off (decision recorded, not re-asked)."""
    try:
        return bool(load_config().get("nudges", True))
    except Exception:  # noqa: BLE001
        return True


def _self_heal(proj):
    """Best-effort repair of the project's memory chain every session (missing/malformed stores,
    markers, index files). Fail-open: any error is swallowed so a broken store never wedges a start."""
    try:
        import memory_engine
        memory_engine.heal(proj)
    except Exception:  # noqa: BLE001 - a hook must never block a session
        pass


_DECOY_CHECK_INTERVAL_S = 86400
"""How often the decoy-anchor scan actually runs. It is a full `os.walk` of the tree (measured 1.34s
over a 97-level tree), far too slow to pay on every start, and a decoy appears only when a migration
leaves a drained sub-store behind - twice in two months on the tree that motivated this. Daily closes
the gap at a fiftieth of the cost."""


def decoy_context(proj):
    """Warn when the tree holds a `.claude-memory` BELOW its top - a decoy anchor that silently
    breaks body retrieval for a whole subtree.

    `find_decoy_anchors` has existed for a while, but only `reconcile --check-tree` ran it, and that
    runs only during a dream - so a decoy could shadow real bodies for however long sits between two
    dreams. The walk-up retrieval text resolves a slug to the NEAREST store first, so a drained
    sub-store answers with a stale or empty-stub body while the real one at the top is never read,
    and nothing reports an error.

    Throttled to :data:`_DECOY_CHECK_INTERVAL_S` via a stamp file, and fail-open like every other
    part of this hook: a broken check must never wedge a session start.
    """
    try:
        import self_improve_signals as sig
        import uuid_store as us

        # find_decoy_anchors is only meaningful below a RESOLVED anchor - a CLAUDE.md-bearing
        # ancestor. memory_engine._anchor falls back to `proj` itself when there is none, which
        # breaks the precondition in both directions: every live per-tree store underneath then
        # reads as a decoy and the message tells the reader to remove it, and the walk root
        # becomes the cwd, so a session started in a home directory walks the whole of it.
        anchor = us.resolve_anchor(proj)
        if anchor is None:
            return ""
        # Keyed per PROJECT, like audit_file beside it. One machine-wide stamp let whichever
        # project started a session first each day consume every other tree's daily check, so a
        # tree that really did carry a decoy was warned about only if it won that race.
        stamp = sig._audit_dir() / (sig.proj_key(proj) + ".decoy-check.stamp")
        if stamp.exists() and (time.time() - stamp.stat().st_mtime) < _DECOY_CHECK_INTERVAL_S:
            return ""
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "meta-self-improve"))
        import reconcile_memory_index as rmi

        found = rmi.find_decoy_anchors(anchor)
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.write_text(time.strftime("%Y-%m-%dT%H:%M:%S"), encoding="utf-8")
        # The pre-5.299.2 machine-wide stamp is dead once the key is per-project, but it is a file
        # in the user's audit dir with no owner left to remove it and nothing in it saying why it
        # is there. Swept on the first run that writes a per-project one; missing is the normal case.
        try:
            (sig._audit_dir() / "decoy-check.stamp").unlink()
        except OSError:
            pass
        if not found:
            return ""
        listed = "\n".join(f"  {d}" for d in found[:5])
        return (
            f"MEMORY STORE: {len(found)} decoy anchor(s) under {anchor} - a `.claude-memory` BELOW "
            f"the tree top:\n{listed}\nWalk-up retrieval resolves a slug to the NEAREST store, so "
            "these shadow the real bodies at the top and return stale or empty ones with no error. "
            "A migration that centralized bodies should have deleted them. Verify each is drained, "
            "then remove it; `reconcile_memory_index.py --check-tree` reports them in full."
        )
    except Exception:  # noqa: BLE001 - a hook must never block a session
        return ""


def main():
    event = _read_event()
    proj = _proj(event)
    _self_heal(proj)
    # Everything else is assembled FIRST so the backlog can be given what is actually left. Sized
    # against a fixture instead, it overran the ceiling on the real repo while its test stayed green.
    retrieval, audit = retrieval_context(proj), audit_context(proj)
    contrib, decoy = contrib_context(proj), decoy_context(proj)
    tail = [dream_nudge(proj), newproject_nudge(proj)] if _nudges_on() else []
    spent = sum(len(p.encode("utf-8")) + 2 for p in [retrieval, audit, contrib, decoy] + tail if p)
    open_work = open_work_context(proj, budget=_ESSENTIALS_CEILING_BYTES - spent)
    ctx = [p for p in [retrieval, audit, open_work, contrib, decoy] + tail if p]
    nudge = autoupdate_nudge(proj)
    if not ctx and not nudge:
        return 0
    out = {}
    if ctx:
        out["hookSpecificOutput"] = {
            "hookEventName": "SessionStart",
            "additionalContext": "\n\n".join(ctx),
        }
    if nudge:
        out["systemMessage"] = nudge
    sys.stdout.write(json.dumps(out))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never block a session
        sys.exit(0)
