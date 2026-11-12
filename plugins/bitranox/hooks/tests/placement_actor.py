"""One engine call in a process of its own, for the placement-lock race tests.

The race tests need two processes to interleave at a chosen point, every time. This actor runs
`render_topics` or `set_fact_topics` with a `write` port (the documented port every level file is
written through) that writes as the default port does and then, after a chosen write, creates
`<barrier>/at` and waits for `<barrier>/go`. The barrier files live outside the tree, so the
engine never sees them; nothing in the engine is patched. The test then starts the other process
while this one is held exactly there.

Usage (argv): render <proj> <scope> <barrier> <pause-after>
              set-topics <proj> <rows-json> <barrier> <pause-after>
`pause-after` is a level file's path (pause after the first write to it) or a count (pause after
that many writes). Prints the call's result as JSON; exit 0 on success, 2 on any exception.
Not a test module: pytest collects only test_*.py.
"""

import json
import os
import sys
import time
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))

import memory_engine as E  # noqa: E402  (the hooks dir is put on sys.path just above)
import uuid_store as us  # noqa: E402

# Long enough for any CI cell to start the other process; a test that never says go fails here
# rather than hanging the suite.
GO_WAIT_S = 60.0


def _is_pause_point(pause_after, path, count):
    if pause_after.isdigit():
        return count == int(pause_after)
    return os.path.abspath(str(path)) == os.path.abspath(pause_after)


def barrier_writer(barrier, pause_after):
    """A `write` port that writes through `uuid_store.write_if_changed` and holds once, after the
    write `pause_after` names, until the test creates `<barrier>/go`."""
    state = {"count": 0, "held": False}

    def write(path, text):
        changed = us.write_if_changed(path, text)
        state["count"] += 1
        if not state["held"] and _is_pause_point(pause_after, path, state["count"]):
            state["held"] = True
            (barrier / "at").write_text("held\n", encoding="utf-8")
            deadline = time.monotonic() + GO_WAIT_S
            while not (barrier / "go").exists():
                if time.monotonic() > deadline:
                    raise RuntimeError("placement_actor: no go within %d s" % GO_WAIT_S)
                time.sleep(0.02)                 # polling a barrier file, not waiting on a guess
        return changed

    return write


def main(argv):
    verb, proj, arg, barrier, pause_after = argv
    write = barrier_writer(Path(barrier), pause_after)
    try:
        if verb == "render":
            rep = E.render_topics(proj, scope=arg, write=write)
        else:
            rows = {slug: (None if topics is None else tuple(topics))
                    for slug, topics in json.loads(arg).items()}
            rep = E.set_fact_topics(proj, rows, write=write)
    except Exception as exc:                     # noqa: BLE001 - reported to the test as data
        print("%s: %s" % (type(exc).__name__, exc))
        return 2
    print(json.dumps(rep, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
