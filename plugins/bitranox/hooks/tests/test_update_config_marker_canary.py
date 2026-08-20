"""Canary: the marker `config-edit-guard` keys on must still be the update-config skill's heading.

`config-edit-guard` allows an edit of Claude Code settings when the host `update-config` skill is
driving, and it recognises that skill by the H1 of its body. That heading is Anthropic's string, not
ours. If it is ever reworded, the detection stops matching, the guard silently resumes blocking the
skill it tells you to use, and nothing says so - a maintainer would only find out from a user
hitting a refusal they cannot explain. That is the exact failure class the hooks audit that
produced this guard was about, so the coupling gets a test rather than a comment.

WHY THIS IS NOT A FLAKY TEST, which is the usual fate of a canary and the reason most get deleted.
Three things have to be true before it is allowed to fail:

  1. a `claude` binary is found - otherwise SKIP (CI runners have none);
  2. that binary demonstrably contains skill bodies at all, proven by a CONTROL string from a
     different part of the same skill - otherwise SKIP, because an instrument that cannot see the
     thing it is looking for must report "I cannot tell", never "it is gone";
  3. only then is the absence of the marker a real finding.

So a packaging change, a wrapper script, or a stripped binary makes this skip. Only a genuine
rewording of the heading makes it fail.
"""

import os
import shutil
from pathlib import Path

import pytest

import config_edit_guard as G

# A string from elsewhere in the update-config skill body. Its job is to answer "can this binary
# show me skill bodies at all?" before the marker's absence is allowed to mean anything.
CONTROL = b"CRITICAL: Read Before Write"

MAX_BYTES = 400 * 1024 * 1024      # refuse to scan something implausibly large


def _claude_binary():
    """The resolved claude executable, or None. Env override for a non-standard install."""
    override = os.environ.get("BITRANOX_CLAUDE_BINARY")
    candidates = [override] if override else []
    found = shutil.which("claude")
    if found:
        candidates.append(found)
    for candidate in candidates:
        try:
            path = Path(candidate).resolve()
        except (OSError, ValueError):
            continue
        if path.is_file():
            return path
    return None


def test_the_update_config_heading_still_matches_the_marker():
    binary = _claude_binary()
    if binary is None:
        pytest.skip("no claude binary on PATH (expected on CI)")
    try:
        if binary.stat().st_size > MAX_BYTES:
            pytest.skip(f"{binary} is implausibly large to scan")
        blob = binary.read_bytes()
    except OSError as exc:
        pytest.skip(f"cannot read {binary}: {exc}")

    if CONTROL not in blob:
        pytest.skip(
            f"{binary} does not contain update-config's body (control string absent), so this "
            f"instrument cannot tell whether the marker is still the heading"
        )

    assert G._UPDATE_CONFIG_MARK.encode("utf-8") in blob, (
        f"config-edit-guard keys on {G._UPDATE_CONFIG_MARK!r} to recognise an active update-config "
        f"skill, and that string is no longer in {binary} even though the skill body is. The "
        f"heading was probably reworded upstream. Until the marker is updated, the guard blocks "
        f"update-config - the exact behaviour 5.216.1 existed to fix."
    )
