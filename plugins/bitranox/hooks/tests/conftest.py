"""Pytest config: load the hyphenated hook modules so tests can import them.

The hook files use hyphenated names (validate-structured-files.py), which are not
importable with a plain `import`. Load each from its path and register it in
sys.modules under an underscore alias so test files can `import <alias>`.
"""

import importlib.util
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent

# Put the hooks dir on sys.path so the hyphenated hooks can import sibling underscore
# modules (e.g. self_improve_signals) at load time, and test files can import them directly.
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

# filename stem -> import alias used by the test modules
_HOOK_MODULES = {
    "ci-watch-nudge": "ci_watch_nudge",
    "ci-watch-gate": "ci_watch_gate",
    "validate-structured-files": "validate_structured_files",
    "git-path-not-here-nudge": "git_path_not_here_nudge",
    "block-pgrep-self-match": "block_pgrep_self_match",
    "block-partial-typecheck": "block_partial_typecheck",
    "block-masked-gate-exit": "block_masked_gate_exit",
    "self-improve-gate": "self_improve_gate",
    "self-improve-audit": "self_improve_audit",
    "decision-review-nudge": "decision_review_nudge",
    "post-compact-nudge": "post_compact_nudge",
    "repo-gate": "repo_gate",
    "tell-sweep": "tell_sweep",
    "commit-tell-sweep": "commit_tell_sweep",
    "git-footgun-guard": "git_footgun_guard",
    "git-wrong-repo-nudge": "git_wrong_repo_nudge",
    "git-revparse-nudge": "git_revparse_nudge",
    "tooling-detour-nudge": "tooling_detour_nudge",
    "block-git-semicolon-chain": "block_git_semicolon_chain",
    "gated-prep-nudge": "gated_prep_nudge",
    "sed-line1-range-nudge": "sed_line1_range_nudge",
    "shell-prefix-selfref-guard": "shell_prefix_selfref_guard",
    "git-commit-branch-guard": "git_commit_branch_guard",
    "block-sed-structured-files": "block_sed_structured_files",
    "session-start": "session_start",
    "session-banner": "session_banner",
    "reformat-md-tables": "reformat_md_tables",
    "recall-memory": "recall_memory",
    "subagent-model-gate": "subagent_model_gate",
    "subagent-probe-capability-gate": "subagent_probe_capability_gate",
    "subagent-backstop-nudge": "subagent_backstop_nudge",
    "touched-paths": "touched_paths",
    "subagent-capture": "subagent_capture",
    "subagent-brief": "subagent_brief",
    "config-edit-guard": "config_edit_guard",
    "context-watcher": "context_watcher",
    "retry-with-a-flag-nudge": "retry_with_a_flag_nudge",
    "recovery-retry-gate": "recovery_retry_gate",
    "jig-repetition-nudge": "jig_repetition_nudge",
    "toolbox-nudge": "toolbox_nudge",
    "skill-edit-guard": "skill_edit_guard",
    "skill-listing-budget": "skill_listing_budget",
    "skill-router": "skill_router",
    "store-edit-guard": "store_edit_guard",
    "venv-guard": "venv_guard",
    "warn-inline-powershell": "warn_inline_powershell",
}

for _stem, _alias in _HOOK_MODULES.items():
    _spec = importlib.util.spec_from_file_location(_alias, HOOKS_DIR / (_stem + ".py"))
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    sys.modules[_alias] = _module


import types as _types

import pytest as _pytest


@_pytest.fixture
def two_trees(tmp_path, monkeypatch):
    """Two INDEPENDENT knowledge trees under tmp_path/work (OUTSIDE the isolated HOME at
    tmp_path/home): work/marketing and work/bakery, each with its own top CLAUDE.md +
    .claude-memory store + a nested project dir carrying its own CLAUDE.md."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True, exist_ok=True)   # tolerate a module-level home fixture
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    work = tmp_path / "work"
    tops = {}
    for name in ("marketing", "bakery"):
        top = work / name
        proj = top / "campaigns" / "proj1" if name == "marketing" else top / "recipes" / "proj1"
        proj.mkdir(parents=True)
        (top / "CLAUDE.md").write_text("%s tree top\n" % name, encoding="utf-8")
        (top / ".claude-memory").mkdir()
        (proj / "CLAUDE.md").write_text("%s proj\n" % name, encoding="utf-8")
        tops[name] = (top, proj)
    return _types.SimpleNamespace(
        home=home, root=work,
        top_a=tops["marketing"][0], proj_a=tops["marketing"][1],
        top_b=tops["bakery"][0], proj_b=tops["bakery"][1],
    )


# ---- a local stand-in for the TypeSafe API (test_classifier*, via the fake_jev fixture) ----
# Lives here because pytest runs with --import-mode=importlib, where one test module cannot
# import another.

import json as _json  # noqa: E402
import threading as _threading  # noqa: E402
import time  # noqa: E402
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402

import pytest  # noqa: E402


class FakeJev:
    """A local stand-in for api.typesafe.ai: records each request, answers per a script."""

    def __init__(self, status=200, body=None, delay=0.0, trickle=False, echo_state=False):
        self.status, self.body, self.delay, self.trickle = status, body, delay, trickle
        self.echo_state = echo_state
        self.requests = []
        # How many requests were being served AT ONCE. A client that serialises can never push
        # this above 1, so it is the concurrency property itself rather than a wall-clock proxy.
        self.in_flight = 0
        self.max_in_flight = 0
        self._counter_lock = _threading.Lock()
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):  # keep pytest output clean
                pass

            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                request = _json.loads(raw)
                fake.requests.append({"path": self.path, "headers": dict(self.headers),
                                      "json": request})
                with fake._counter_lock:
                    fake.in_flight += 1
                    fake.max_in_flight = max(fake.max_in_flight, fake.in_flight)
                try:
                    time.sleep(fake.delay)
                finally:
                    with fake._counter_lock:
                        fake.in_flight -= 1
                payload = fake.body
                if payload is None:
                    payload = fake.default_answers(request, echo_state=fake.echo_state)
                data = payload if isinstance(payload, bytes) else _json.dumps(payload).encode()
                self.send_response(fake.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                if fake.trickle:  # each byte arrives inside the socket timeout; the whole does not
                    for b in data:
                        self.wfile.write(bytes([b]))
                        self.wfile.flush()
                        time.sleep(0.05)
                else:
                    self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]
        _threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @staticmethod
    def default_answers(req, echo_state=False):
        """The scripted answer. With `echo_state`, `model` carries the request's own state value
        back, which is how a caller can tell WHICH request a result belongs to - otherwise every
        answer is identical and an ordering claim cannot be checked at all."""
        answers = {}
        for qid, q in req["questions"].items():
            if q["type"] == "noul":
                answers[qid] = {"type": "noul", "noul": 0.9}
            else:
                key = next(iter(q["criteria"]))
                answers[qid] = {"type": "choice", "choice": key,
                                "probabilities": {key: 0.8}, "confidence": 0.7}
        model = "jev-1.13.0"
        if echo_state:
            values = list((req.get("state") or {}).values())
            model = str(values[0]) if values else model
        return {"model": model, "answers": answers,
                "usage": {"input_tokens": 123, "output_tokens": 5}}

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def fake_jev():
    """Factory: `fake_jev(status=, body=, delay=, trickle=)` starts a server; all close at teardown."""
    started = []

    def make(**kw):
        f = FakeJev(**kw)
        started.append(f)
        return f

    yield make
    for f in started:
        f.close()
