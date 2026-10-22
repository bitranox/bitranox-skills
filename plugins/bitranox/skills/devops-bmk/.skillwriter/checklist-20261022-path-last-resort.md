# skill-writer checklist - devops-bmk (2026-10-22, path-last-resort)

- [x] Change: one sentence in the hand-resync paragraph. It said bmk never passes the
      interpreter's path, on any version. It now says bmk passes the path only when that
      interpreter cannot report its version (uv could not build from it either), and that a user
      never types the path by hand, on any version, because on CPython 3.10 and older it leaves an
      empty venv when uv recreates it.
- [x] Claim checked against bmk source: `venv._sync_python_request` returns the declared minor,
      else `_python_request(_probe_interpreter(venv)) or str(venv_python(venv))`, so the path is
      used exactly when the probe gives no answer. The CHANGELOG's I1 bullet already says "Only an
      interpreter that cannot answer is still passed by path".
- [x] Receipt held (skill_receipt.py start meta-skill-writer); this agent loaded the skill.
- [x] RED route: a text check of the artifact (the new sentence present, "bmk never passes the
      interpreter's path" absent). FAIL on the pre-change SKILL.md, PASS on the final text.
- [x] Quote-back, haiku, two questions (does bmk ever pass the path and when; may a user pass the
      path by hand on CPython 3.12). Answers, each with a direct quote of the new sentence: bmk
      passes it "only as a fallback, when the venv's interpreter cannot report its version", and
      by hand "No. Pass the bare minor instead" (`--python 3.12`).
- [x] Gaps declined: "With none" and the literal `--python` flag lie outside the probed excerpt
      (the paragraph opens with the full `uv sync --python <X.Y>` command and the classifier rule);
      the reason for "on any version" naming only 3.10 and older is deliberate - the rule is the
      simple one for a reader, the reason is the case where breaking it costs a venv.
- [x] Mirrors the bmk repo's copy byte for byte.
