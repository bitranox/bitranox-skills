# devops-bmk: what version bump and release accept, and what they produce

Scope: one new subsection under section 3, plus three corrected claims (the `bump-patch` and
`make release` rows in the target table, and the `gh release create` line in Troubleshooting), one
new Troubleshooting row, and one bullet added to the shipped-skill version rules. No other section
changes.

## The finding this adds

bmk accepts any canonical PEP 440 project version. The skill described the release tag as `vX.Y.Z`
and said nothing about pre-releases anywhere. That is the dangerous shape of staleness: not a
missing detail but an ABSENCE claim, which steers a reader away from behaviour that works rather
than merely failing to help.

It also left the bump rule undefined. `bmk` finalizes a non-final version rather than stepping past
it, so `1.2.3rc1` patch-bumps to `1.2.3`. That is bmk's own rule and is not derivable from PEP 440,
so a reader cannot reconstruct it from general knowledge.

## RED: a behavioural arm is available here, and it fails

- [x] The lesson under test is bmk-specific, not inherited. General PEP 440 knowledge settles what
      `1.3.0b2` MEANS; it cannot say what `bump-patch` PRODUCES from it. So the behavioural arm can
      fail honestly and no text-check substitute is needed.
- [x] Text check of the artifact first: the pre-change file contains no occurrence of `PEP 440`,
      `pre-release`, `canonical`, or an `rc` version, and its only two version-shape statements
      both assert `X.Y.Z`.
- [x] Behavioural RED, pre-change text, asked what `make bump-patch` yields from `version =
      "1.3.0b2"` and what `make release` would tag: it could not answer the first, returning
      `1.3.0`, `1.3.1` and `1.3.0b3` as equally plausible and declining to pick, and it answered
      the second `v1.3.0b2` while stating that "nothing in the material suggests `release`
      normalizes, strips, or refuses a pre-release-suffixed version". At that time `release`
      refused it, so the text did not merely omit the rule, it supported the opposite conclusion.

## GREEN, with quote-back

- [x] Same scenario plus a third question (a colleague's `version = "v2.0.0"` failing) against the
      new text, each answer required to quote the governing line or return NONE. All three correct
      and all three quoted, not paraphrased: the `1.3.0b2` table row, "`release` tags `v` + that
      string verbatim", and the refused-shapes row for `v1.0.0`.

## REFACTOR: the gaps GREEN reported, and what closed them

- [x] "Whether `1.3.0b2` itself is canonical is inferred, not stated" - the accepted-version list
      gave `rc`, `dev` and `post` examples but no bare `bN`, so the reader had to reason from the
      refused `1.0.0-beta` row. Closed by naming `1.2.3a1` and `1.3.0b2` in the accepted list.
- [x] "No confirmation `make release` would even reach the tag-creation step" for a non-final
      version - the text described what release tags but never said a pre-release is not itself a
      refusal reason. Closed by stating it outright and pinning the only version check to the two
      shapes in the table.

## Mirror

- [x] This copy and the bmk repo's `skills/devops-bmk/SKILL.md` are byte-identical (`cmp`), and
      `repo-gate.py --mirror-of` reports `in sync`. The pair carries no conventional divergences:
      the `name:` field, the H1 and the absence of a self-install blockquote already match, so the
      sync is a straight copy with nothing to re-apply.

## Claims verified against the code, not the release notes

- [x] `release` accepts and tags a canonical pre-release, and refuses a non-canonical spelling and
      a local version without creating a tag. Exercised against real repositories with a real
      remote, reading the tags that arrived rather than the exit code alone.
- [x] The bump table matches what the implementation returns for every row, including
      `1.2.3.post1 -> 1.2.4`, which differs from the pre-release rows because a post release is
      final.
- [x] The claim that a non-final package version is not written into `.claude-plugin/plugin.json`
      matches the guard in the sync helper, not merely its docstring.
