# skill-writer checklist - ai-llm-jev-judge (2026-10-27, mirror of jev-judge 0.3.4)

Source: the `jev-judge` skill of `bitranox/btx-skill-jev-judge` at tag `v0.3.4`
(`skills/jev-judge/SKILL.md`), regenerated here with only the `name:` line changed. This release
corrects the skill's text against what the 0.3.3 CLI does; frontmatter is byte-identical.

- [x] Skill type: technique. RED: a read-only reviewer that read the 0.3.3 skill and ran the CLI
      reported two false statements and nine places it had to guess:
  - false: `run` without a key exits 2, not 1 (only `check-key` exits 1);
  - false: under a refused `LOG_*` variable, `config --section judge` exits 78 itself, so the
    named remedy fails;
  - guessed: ids come back as strings; what a `score` value and its `probabilities` mean;
    the `score` level and `noul` key limits; that `check-key` does not test the key; how to
    retry failed rows; what happens to long strings; how to estimate cost; how to keep the pilot
    and full run on one model.
- [x] Each fact was verified against the source or a CLI run: no-key exit 2, `config` exit 78 under
      `LOG_CONSOLE_LEVEL=bogus`, `{"id": 1}` returned as `"1"`, duplicate id exit 2, 11 score levels
      and a `noul` key `yes` refused, a 401 stub failing every row, `run` writing `--out` with "w",
      a 200,000-character body reaching the stub at 60,000, `run --cap` and `run --model` in
      `--help`, rows carrying `model`.
- [x] GREEN: a probe on `opus` and one on `haiku`, each given only the edited text, answered all ten
      gap questions by direct quote (no NONE). Three probe gaps (pilot model pinning, cost
      variance, the `--cap` flag) were closed and re-probed on both tiers, 3 of 3 by quote.
      Remaining probe gaps are declined with reasons in the tool repo's `docs/skill-review.md`.
- [x] The five `uvx --from 'btx-skill-jev-judge>=0.3.4'` floors name a version PyPI serves.
- [x] `meta-self-improve/jev_shadow.py` `JEV_JUDGE_FLOOR` follows the floor (pinned by
      `test_jev_shadow.py`).
- [x] Frontmatter untouched (description 425 chars): routing keywords unchanged.
- [x] No version-history wording; ASCII only; no address, MAC, hostname or private path added.
- [x] No session narrative or private provenance added.
