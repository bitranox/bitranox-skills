# checklist-20261005-error-contract-escapes

Change under test: the aspect checklist's `Error contract` row now asks for EVERY exception a
public call can let escape, a stdlib or dependency one included, and a paragraph under the table
says how to walk it: from each entry point inward, driving the dependency calls that receive
caller data with hostile values and asserting the exception TYPE that comes out.

The failure behind it: a reviewer read "nothing leaking a foreign exception" as "classify the
package's own raise statements", scored the row clean, and a stdlib `ValueError` raised from an
email header built out of caller data escaped the public `send()`.

## PLAN

- [x] Skill type: technique (how to walk one checklist row).
- [x] Scope: `SKILL.md` only - one table cell and one paragraph after the table.

## RED

- [x] Inherited-coverage check: `redcheck.py --corpus-cascade` on the repo answered INHERITED
      COVERAGE - a memory fact on this machine records this exact lesson. A behavioural RED cannot
      fail honestly here, so the route taken is a TEXT CHECK of the artifact.
- [x] Text-check RED: the pre-change file has no rule about exceptions raised by dependencies -
      `grep -n -i "escape\|stdlib\|dependency"` hits only unrelated lines (dependency decisions,
      dependency direction, output escaping), and the row read "One hierarchy, consistent types,
      nothing leaking a foreign exception".

## GREEN

- [x] Text-check GREEN: the row names "a stdlib or dependency one included" and the paragraph
      "The Error contract row is about what ESCAPES" is present once.
- [x] Behavioural arm on haiku with the new row and paragraph pasted (used for gaps, not as proof,
      given the inherited coverage): a library whose own exceptions all derive from one base and
      whose `upload(path)` hands the path to a third-party client was NOT passed on the census; the
      arm said to drive `upload()` with hostile paths and assert the type, quoting the paragraph.
- [x] The arm was asked for a `Skill gaps` section; its list is worked below.

## REFACTOR - every gap closed or declined

- [x] GAP: whether wrapping every foreign exception is mandatory or a documented passthrough is
      acceptable. DECLINED - the row's "one hierarchy" plus "a foreign type reaching the caller is
      a finding" decides the review verdict; whether to wrap or document is the fix's design,
      which the review does not prescribe.
- [x] GAP: how much hostile input is enough. DECLINED - the paragraph names the classes (CR/LF,
      NUL, oversized, wrongly typed); exhaustiveness is the reviewer's judgement per call.
- [x] Quote-back: the arm answered with a direct quote of the new paragraph, not NONE.
- [x] GREEN against the pre-change reading: the only change is where the row's walk starts (entry
      points, not raise sites); the other rows and the sweep reporting are unaffected.

## Quality

- [x] Description unchanged, so the trigger map needs no rebuild.
- [x] Table cell kept within the existing column width, so the table needs no reflow.
- [x] No narrative, no scratch paths, no addresses added.

## Deployment

- [x] No version bump or CHANGELOG entry in this branch: the integration owner bumps and writes
      the release notes for the whole batch.
