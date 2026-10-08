"""One JSON request in on stdin, one JSON envelope out on stdout: the Claude Code mod's way in.

hooks/mods/register.ts registers the model-callable tools and hands each call here, so every rule
those tools obey lives in tested Python and the TypeScript only relays. Exit 0 on success, 1 when
the request was refused (the envelope names the kind), 2 when the bridge could not run it at all.
Output is ASCII-escaped JSON, so no console code page can mangle it.
"""
import json
import os
import sys
import traceback
from pathlib import Path

import memory_engine as ME
import open_work as ow
import self_improve_signals as sig

MEMORY_TYPES = (None, "user", "feedback", "project", "reference")


class BadInput(ValueError):
    """A tool input the bridge refuses before calling anything."""


class BadRequest(ValueError):
    """A request the bridge cannot run: not JSON, not an object, an unknown tool. `tool` is the
    tool name when it was parsed and is known, so the envelope can still name it."""

    def __init__(self, message, tool=None):
        super().__init__(message)
        self.tool = tool


REFUSALS = (ow.BacklogError, BadInput, ME.SlugCollision, ME.HookTooLong, ME.EmptyBody,
            ME.PinnedEntry, ME.InvalidSlug, ME.ExcludedLevel, OSError)


def _backlog_list(inp, cwd):
    path = ow.backlog_path(cwd)
    data = {"path": str(path), "items": ow.list_items(path, state=inp.get("state", "open"))}
    if not path.is_file():
        data["note"] = "no OPEN-WORK.md at %s yet; backlog_add creates it" % path.parent
    return data


def _backlog_add(inp, cwd):
    return ow.add_item(ow.backlog_path(cwd), inp.get("rank"), inp.get("origin"), inp.get("what"),
                       inp.get("size"), inp.get("open"), inp.get("next"), raised=inp.get("raised"))


def _backlog_close(inp, cwd):
    return ow.close_item(ow.backlog_path(cwd), inp.get("rank"), inp.get("reason"))


def _text(inp, name):
    value = inp.get(name)
    if not isinstance(value, str) or not value.strip():
        raise BadInput("%s must be a non-empty string" % name)
    return value


def _level(inp, cwd):
    value = inp.get("level")
    if value is None:
        return cwd
    if not isinstance(value, str) or not value.strip():
        raise BadInput("level must be a non-empty string (a directory), or absent for the session cwd")
    return Path(value)


def _memory_add(inp, cwd):
    level = _level(inp, cwd)
    if not level.is_dir():
        raise BadInput("level is not a directory: %s" % level)
    type_ = inp.get("type")
    if type_ not in MEMORY_TYPES:
        raise BadInput("type must be one of user, feedback, project, reference, got %r" % (type_,))
    slug, created, advice = ME.add_with_advice(
        str(level), title=_text(inp, "title"), hook=_text(inp, "hook"), body=_text(inp, "body"),
        type_=type_, slug=inp.get("slug"))
    return {"slug": slug, "level": str(level.resolve()),
            "action": "created" if created else "updated", "warnings": advice}


def _contrib_add(inp, cwd):
    what = ow.require_line(_text(inp, "what"), "what")
    target = ow.require_line(_text(inp, "target"), "target")
    proj = str(cwd)
    queued = sig.add_contribution(proj, {"what": what, "target": target,
                                         "why": ow.require_line(_text(inp, "why"), "why"), "source": "mod:contrib_add"},
                                  strict=True)
    if queued:
        return {"queued": True}
    return {"queued": False, "reason": sig.why_not_queued(proj, what, target)}


TOOLS = {"backlog_list": _backlog_list, "backlog_add": _backlog_add,
         "backlog_close": _backlog_close, "memory_add": _memory_add, "contrib_add": _contrib_add}


def _request(raw):
    try:
        req = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise BadRequest("stdin is not JSON: %s" % exc) from None
    tool = req.get("tool") if isinstance(req, dict) else None
    known = tool if isinstance(tool, str) and tool in TOOLS else None
    if not isinstance(req, dict) or not isinstance(req.get("input", {}), dict):
        raise BadRequest("the request must be {\"tool\": <name>, \"input\": {...}}", known)
    if known is None:
        raise BadRequest("unknown tool %r; known: %s" % (tool, ", ".join(sorted(TOOLS))))
    return known, req.get("input", {})


def _emit(envelope, rc):
    sys.stdout.write(json.dumps(envelope, ensure_ascii=True) + "\n")
    sys.stdout.flush()
    return rc


def _internal(tool, exc):
    traceback.print_exc()
    return _emit({"ok": False, "tool": tool,
                  "error": {"kind": "Internal",
                            "message": "%s: %s" % (type(exc).__name__, exc)}}, 2)


def main():
    try:
        tool, inp = _request(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
    except BadRequest as exc:
        return _emit({"ok": False, "tool": exc.tool,
                      "error": {"kind": "BadRequest", "message": str(exc)}}, 2)
    except Exception as exc:  # noqa: BLE001 - the relay must always get an envelope
        return _internal(None, exc)
    try:
        data = TOOLS[tool](inp, Path(os.getcwd()))
    except REFUSALS as exc:
        return _emit({"ok": False, "tool": tool,
                      "error": {"kind": type(exc).__name__, "message": str(exc)}}, 1)
    except Exception as exc:  # noqa: BLE001 - the relay must always get an envelope, never a bare traceback
        return _internal(tool, exc)
    return _emit({"ok": True, "tool": tool, "data": data}, 0)


if __name__ == "__main__":
    sys.exit(main())
