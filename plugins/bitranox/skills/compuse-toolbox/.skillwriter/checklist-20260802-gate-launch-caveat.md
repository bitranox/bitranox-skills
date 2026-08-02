# skill-writer checklist - compuse-toolbox (2026-08-02, launch gate with python3, not uv run)

Change: one caveat on the `gate` bullet. The jig must be launched with plain `python3`; `uv run`
interposes its own ephemeral interpreter on the environment the child gates inherit.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, issued this session).
- [x] Found by the jig failing for real, not by review: run as `uv run scripts/gate.py`, the
      repo-gate child died with
      `/home/srvadmin/.cache/uv/builds-v0/.tmpJgPxTm/bin/python3: No module named pytest`
      and the run reported GATE RED.
- [x] Diagnosed rather than retried: the same gate passed standalone, so the difference was the
      launcher, not the gate. gate.py declares no dependencies, so uv buys nothing here and only
      adds an interpreter the children then inherit.
- [x] Verified both arms: identical gate list under `uv run` -> false RED; under `python3` ->
      1674 passed and repo-gate clean.
- [x] Scoped honestly - the caveat says only this jig is affected, because only this one runs other
      commands; the rest are fine under `uv run` and the skill's general instruction stands.
- [x] No session narrative or private provenance in the SKILL.md; the measured path appears here in
      the artifact, where it is the evidence, not in the skill body.
