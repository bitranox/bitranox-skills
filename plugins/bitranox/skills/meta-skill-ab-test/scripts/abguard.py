"""The memory-store guard (a manifest before and after each arm) and the out-of-band login check.

The guard drives skills/meta-dream-tree/store_manifest.py as a subprocess: its exit code is the
answer (0 identical, 1 differs, 2 could not run). The login check asks the API directly because
the CLI reports a 429 (rate limited: an exhausted quota, or a refusal of this request shape -
measured 2026-11-04: a 429 came back while the account was serving) with the same "not logged
in" text as a bad token (401), and a run must PAUSE on the first and VOID nothing (design S4).
"""
from __future__ import annotations

import http.client
import json
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from _ablib import run

__all__ = [
    "API_URL",
    "MANIFEST",
    "MANIFEST_TIMEOUT",
    "NO_STORE_MARK",
    "GuardError",
    "check_login",
    "snapshot",
    "verify",
]

MANIFEST = Path(__file__).resolve().parents[2] / "meta-dream-tree" / "store_manifest.py"
# store_manifest.py's no-store refusal starts "no .claude-memory/ store at the memory anchor of".
# A chain without a store is a legal workpiece, so only that refusal is a skip, never an error.
NO_STORE_MARK = "no .claude-memory"
MANIFEST_TIMEOUT = 600.0
API_URL = "https://api.anthropic.com/v1/messages"
LOGIN_MODEL = "claude-haiku-5-5"
STATUS_WORDS = {200: "ok", 401: "login", 429: "quota"}
PostFn = Callable[[str, dict[str, str], bytes], tuple[int, str]]


class GuardError(RuntimeError):
    """The guard could not run; the arm must not start (or its result cannot be trusted)."""


def _manifest(argv: list[str], manifest: Path, *, timeout: float = MANIFEST_TIMEOUT) -> tuple[int, dict[str, Any]]:
    """Run the manifest script with --json; (exit code, parsed envelope or {})."""
    try:
        proc = run([sys.executable, str(manifest), *argv, "--json"], timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise GuardError(f"store_manifest {argv[0]} timed out after {timeout:g} s") from exc
    except OSError as exc:
        raise GuardError(f"store_manifest {argv[0]} could not start: {exc}") from exc
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        data = {}
    return proc.returncode, data if isinstance(data, dict) else {}


def _data(envelope: dict[str, Any]) -> dict[str, Any]:
    d = envelope.get("data")
    return d if isinstance(d, dict) else {}


def snapshot(chain_from: Path, out: Path, *, manifest: Path = MANIFEST) -> dict[str, Any]:
    """Back up the chain's pointer files and store under out; skipped (not taken) without a store."""
    rc, data = _manifest(["backup", "--from", str(chain_from), "--scope", "chain", "--out", str(out)], manifest)
    if rc == 0:
        return {"taken": True, "entries": int(_data(data).get("entries") or 0), "skipped": None}
    error = str(_data(data).get("error") or "")
    if rc == 2 and NO_STORE_MARK in error:
        return {"taken": False, "entries": 0, "skipped": error}
    raise GuardError(f"store_manifest backup rc={rc}: {error or data or 'no JSON output'}")


def verify(out: Path, *, manifest: Path = MANIFEST) -> list[str]:
    """One line per change since the snapshot; empty when identical or when no snapshot was taken.

    A missing manifest.json under out reads as no change, so a store an arm damaged after a
    skipped or failed snapshot passes silently: call this only after snapshot() returned
    taken=True for the same out.
    """
    if not (out / "manifest.json").is_file():
        return []
    rc, data = _manifest(["verify", "--out", str(out)], manifest)
    if rc not in (0, 1):
        raise GuardError(f"store_manifest verify could not run (rc={rc}): {_data(data).get('error') or data}")
    d = _data(data)
    lines: list[str] = []
    for kind in ("added", "removed", "changed", "moved"):
        lines.extend(f"{kind}: {item}" for item in d.get(kind) or [])
    if rc == 1 and not lines:
        lines.append("differs (no detail in the verify output)")
    return lines


def _post(url: str, headers: dict[str, str], body: bytes) -> tuple[int, str]:
    """POST body; (HTTP status, first 500 chars of the response). Status 0: no answer at all."""
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310 - API_URL is a fixed https URL
            return resp.status, resp.read().decode("utf-8", "replace")[:500]
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")[:500]
    except (urllib.error.URLError, OSError) as exc:
        # No network, DNS down: reported as unknown:0, which pauses the run like a quota would.
        # repr of these carries the reason only, never the request headers.
        return 0, repr(exc)
    except (ValueError, http.client.HTTPException) as exc:
        # A refused header value (ValueError) quotes that value, the token, in its message, and
        # a malformed answer (BadStatusLine and kin) is no status either: name the type only.
        return 0, type(exc).__name__


def _read_token(credentials: Path) -> str | None:
    try:
        doc = json.loads(credentials.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    oauth = doc.get("claudeAiOauth") if isinstance(doc, dict) else None
    token = oauth.get("accessToken") if isinstance(oauth, dict) else None
    if not isinstance(token, str) or not token:
        return None
    # A control or non-ASCII character cannot travel in a header, and http.client's refusal would
    # quote the token in its message; such a credential is unusable, so it reads as no login.
    return token if token.isascii() and token.isprintable() else None


def check_login(credentials: Path, *, post: PostFn = _post) -> str:
    """ok / login / quota / unknown:<status>, from one minimal request with the arm's credential.

    200 is ok, 401 login, 429 quota (rate limited: an exhausted quota, or a refusal of this
    request shape - measured 2026-11-04: a 429 came back while the account was serving), anything
    else unknown:<status>, 0 when no answer came. A missing, unreadable or malformed token (empty,
    or holding a control or non-ASCII character) is login and is never sent. The token is read
    from the credentials copy and sent once; it is never logged or returned.
    """
    token = _read_token(credentials)
    if token is None:
        return "login"
    headers = {"authorization": f"Bearer {token}", "anthropic-version": "2023-06-01",
               "anthropic-beta": "oauth-2025-04-20", "content-type": "application/json"}
    body = json.dumps({"model": LOGIN_MODEL, "max_tokens": 1,
                       "messages": [{"role": "user", "content": "hi"}]}).encode("utf-8")
    status, _ = post(API_URL, headers, body)
    return STATUS_WORDS.get(status, f"unknown:{status}")
