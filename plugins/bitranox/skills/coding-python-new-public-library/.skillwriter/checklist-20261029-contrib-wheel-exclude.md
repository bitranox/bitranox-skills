# Review: what the wheel ships (contrib entry)

- [x] RED: no wheel `exclude` or "what ships" text in the pre-edit skill.
- [x] Executed on the template (git archive HEAD into a scratch dir): a new
      `src/<pkg>/logo.svg`, NOT listed in the wheel `include`, shipped in the wheel and the sdist
      (`uv build`, listed with zipfile/tarfile). After adding
      `exclude = ["/src/<pkg>/logo.svg"]` to `[tool.hatch.build.targets.wheel]`: gone from the
      wheel, `py.typed` still there, still in the sdist.
- [x] The verify command in the text (`uv build --wheel --out-dir dist && python -m zipfile -l
      dist/*.whl`) was run and lists the package files.
- [x] GREEN: `grep -n "What the wheel ships" SKILL.md` quotes the new section.
- [x] Twin regenerated; `diff -r -x .skillwriter -x __pycache__` shows only the `name:` line.
- [x] ASCII only; no history wording; description untouched.
- [x] Declined, not run: subagent quote-back probes (this pass dispatched no subagents).
