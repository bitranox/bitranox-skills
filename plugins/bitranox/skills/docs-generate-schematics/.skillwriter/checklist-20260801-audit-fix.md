# skill-writer checklist - docs-generate-schematics (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit`. Ships with plugin 5.127.0.

- [x] WRONG, and it breaks the script on a clean machine: the skill said `httpx2` is handled by
      "PEP-723/uv", but neither shipped script carried an inline metadata block, and every
      documented invocation was plain `python3`. uv reads inline metadata only from the file it is
      handed, so nothing resolved the dependency. Added the PEP 723 block to the AI script and
      switched all three documented invocations to `uv run`, which is what reads it.
- [x] The remaining two findings (a wrapper described as single-shot, a model-slug URL in a
      comment) are recorded as open: both need the OpenRouter API to settle, which this audit does
      not call.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every QUOTE checked against the real file; every executable claim re-run rather than trusted.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
