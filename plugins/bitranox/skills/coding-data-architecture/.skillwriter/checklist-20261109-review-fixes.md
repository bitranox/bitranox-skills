# skill-writer checklist - coding-data-architecture (2026-11-09, review fixes)

Fixes from an independent review: Core Principle 7 names its one boundary case (a versioned
wire record for a format the system must still read, converted once, old aliases and defaults on
that record only, a format nobody reads deleted); Principles 4 and 5 say an open type for a
foreign value and a wire record plus its one conversion are not violations; STEP A's
NOT-violations brief lists both plus the versioned record and the language skill's own list;
STEP D judges hits against those NOT-violations; the STEP B alias instruction separates a code
alias from a wire-format one; the boundary-parsing pointer is language-neutral and the Python
layered-architecture pointer sits in the Python row.

Decisions: d-20261109-4ff324a7

- [x] Receipt fresh and `bitranox:meta-skill-writer` loaded in this agent before the first edit.
      Ledger read first (`show coding-data-architecture --kind rejected,removed --full`: none).
      After the edit `skill_decisions.py check coding-data-architecture` reports 0 findings, so
      the anchors of d-20261109-06f0b30f still occur once.
- [x] Not mirrored: the skill ships only from this marketplace.
- [x] Finding 11 verified: the old blockquote pointed every language at
      `bitranox:coding-python-clean-architecture`.

## Probes (opus, `general-purpose`, told to read only this skill and the Rust skill)

- [x] RED arms read the pre-edit text (`git show HEAD:`) of both skills, GREEN and final arms the
      edited copies; neither skill is in the installed plugin. Tier: opus only, one cell per
      changed rule, as the task scoped; no haiku arm was run.
- [x] Item 2 (compatibility shims). Scenario: persisted v1 (`mail`) and v2 (`email`) job files
      that must keep loading, alias and default on the domain type, two reviewers disagreeing.
      RED: "The two texts give opposite answers, and neither says which one wins", four
      contradictions quoted, retirement answered NONE. GREEN quoted "One case is a boundary, not
      a shim: a wire format the system MUST still read ..." and "every old-format alias or
      default lives on that record only, never on the domain type", found no contradiction, and
      answered retirement with "A format nothing reads any more is deleted, record and all".
- [x] Item 3 (NOT-violations). RED: correct verdicts from the Rust text, but "the generic
      skill's Core Principles 4 and 5, read alone, would support the analyser". GREEN quoted the
      new Principle 4 and 5 sentences as deciding. The final re-run quoted the reworded
      Principle 4 ("stored, forwarded or written back unchanged") for an opcode kept to forward.
- [x] Item 1 (workflow inputs) is a Rust-skill change; its probes read this skill too, and the
      gaps they reported about this text are under "Gaps declined".
- [x] Every dispatch asked for a "Skill gaps" section; each reply's list was read.

## Gaps closed

- [x] STEP D's "A hit that fits no named exclusion is real" ignored the NOT-violations list:
      STEP D now judges against it, the language skill's included.
- [x] Principle 4 said the open value travels on only to be written back while the Rust skill
      also allows storing and forwarding: Principle 4 now names all three.
- [x] "no alias outlives the run" could be read as forbidding a serde alias: now "no code alias",
      with the wire-format alias named as Principle 7's boundary case.

## Gaps declined

- [x] A coordinator verdict field for an analyser false positive in the state file, and the
      analysis template carrying the generic NOT-violations verbatim: workflow restructuring
      beyond this review's findings; the STEP A prose already makes the list required.
- [x] Migrate-versus-keep-a-reader for old data, untagged old files, proving the old format is
      gone: format-design questions no finding raised.
- [x] The `exit code|raises|refused` doc grep is Python-flavoured: the Rust skill adds its
      `# Errors` note; other languages keep the generic grep.

## Checks

- [x] Width and fence check over the added lines printed nothing after every fix round; the
      paragraph after each insertion read for re-bound references.
- [x] Route table re-padded by the reformat hook; ASCII only; history finder hits are
      pre-existing behaviour sentences.
- [x] Description unchanged; trigger map and docs regenerated with no diff.
- [x] Security: no secrets, hosts or private paths added.
