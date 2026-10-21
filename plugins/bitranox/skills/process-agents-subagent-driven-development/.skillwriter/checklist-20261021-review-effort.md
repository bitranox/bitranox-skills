# skill-writer checklist - process-agents-subagent-driven-development (2026-10-21, review effort)

- [x] Change: a new "Review dispatches" subsection under Model Selection makes every dispatch that
      judges work or a verdict already produced run on `model: "opus"` with `effort: "medium"`
      (per-task reviewer and re-reviews, final whole-branch review, code review, skeptic and
      adversarial lenses, verify passes, adjudicators, quote-back checks, audit reviewers, judge
      panels), with the Workflow and headless spellings, and states that the paragraph is the
      explicit ask the Agent tool's `effort` field requires. It excludes implementers, fixers,
      scenario writers and probe subjects, and separates a reviewer fan-out (a review) from a
      scanner judging raw material (not a review). The effort table gains a review row; adversarial
      verify and judge panels leave the `xhigh`/`max` row, which keeps final synthesis; the haiku
      `low` row is unchanged. The "extremes only" warning names reviews as the one
      exception; the reviewer mentions in Concrete tiers and Turn count carry the effort.
      `task-reviewer-prompt.md` pins `model: opus` and `effort: medium`. The effort paragraph gets
      its own heading so it no longer reads as part of the review subsection.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`), skill loaded by the editing agent
- [x] Skill type: reference/discipline rule for dispatch parameters; test approach: quote-back
      application probe on the text, both tiers
- [x] Corpus check: `redcheck.py --corpus-cascade` reported INHERITED COVERAGE (STRONG) by term
      overlap. The named documents teach effort only as "set extremes: low for mechanical fan-out,
      xhigh/max for adversarial verify" (a grep for an effort `medium` rule in them finds none), so
      the inherited lesson is the OLD rule and works against GREEN, not for RED. Route kept: a
      behavioural quote-back arm on the pasted text, with the excerpt declared the text under test.
- [x] RED (pre-edit excerpt, `bitranox:baseline-probe`, text only, Skill gaps requested), haiku and
      opus: both answered opus with effort OMITTED for (a) per-task reviewer, (b) skeptic lens on a
      duplicate verdict, (c) adversarial verifier. Deciding quotes: "on an Agent-tool dispatch, only
      once the user, CLAUDE.md or a skill step has asked for a level." and "for an Agent-tool
      dispatch the table below is not itself an ask". RED gaps: the `xhigh`/`max` adversarial row
      could never apply on the Agent tool (no ask); "skeptic lens" not named anywhere; the reviewer
      template had no effort line and said an omitted model inherits "the most expensive one"
      while SKILL.md says "a premium tier or a weaker one".
- [x] GREEN (post-edit excerpt, both tiers, plus control arms (d) a fixer implementing review
      findings and (e) final synthesis): (a) (b) (c) opus/medium on haiku and opus, each quoting
      "Every dispatch whose job is to JUDGE work already done runs on `model: "opus"` with
      `effort: "medium"`" or the template's "effort: medium" line; (c) also quoted "adversarial
      CORRECTNESS verification and the final whole-branch review, both at effort `medium`".
      Controls did not over-trigger: (d) effort omit, quoting "It does NOT cover implementers and
      fixers"; (e) effort omit on the Agent tool. Every quote checked against the pasted excerpt.
- [x] GREEN vs RED diffed both ways: RED's three model answers (opus) are unchanged; nothing RED
      produced is missing from GREEN. The RED template contradiction is gone (template line
      replaced by `model: opus`).
- [x] Gaps closed: per-store/per-file reviewers "at effort `medium`" vs the table's "`opus` fan-out
      ... inherit" (now: a reviewer fan-out is a review, a scanner over raw material is not);
      "work already done" an awkward fit for a duplicate verdict (now: "work or a verdict already
      produced").
- [x] Gaps declined: final synthesis `xhigh`/`max` cannot ride the Agent tool without an ask (out
      of scope: synthesis is not review and keeps its row unchanged by this task); a fixer's model
      when review findings are prose vs complete code (implementer tiering, out of scope);
      `xhigh` vs `max` choice (pre-existing, synthesis); which dispatches `subagent-model-gate`
      treats as review-shaped (owned by the hook and its own docs); `fable` for an adversarial
      verifier (the review paragraph pins `opus`, which both arms read correctly).
- [x] Re-probe 1 (questions the fixes touched: (b), a per-file reviewer fan-out (f), a scanner
      judging raw log lines (g), plus (a) (c)), haiku and opus: (a) (b) (c) (f) opus/medium, (f)
      quoting "A fan-out of such reviewers (one per file, dimension or store) is a review too";
      (g) opus with effort omitted, quoting "a scanner that judges raw material nobody has
      produced a result from yet (log lines, search hits, records) is not". New gaps: the table
      row "`opus` fan-out / bounded judgment / deep reasoning" read as covering (f); the tier
      bullet named reviewers' effort but not scanners'. Closed: the row is now "Non-review `opus`
      fan-out / judgment / reasoning", the review paragraph points at "the non-review `opus` row",
      and the bullet says scanners run "at inherited effort".
- [x] Re-probe 2 (final wording of the review section, table and tier bullet; same five
      questions), haiku and opus: all five correct on both tiers, (g) quoting "takes the
      non-review `opus` row below" and the row "Non-review `opus` fan-out / judgment / reasoning |
      inherit - do not set". One new gap (opus): a review sent as a `fork` would silently drop
      both fields. Closed with "Never send a review as a `fork`: a fork ignores both fields and
      runs on the parent's model and effort."
- [x] Re-probe 3 (the fork question only), haiku and opus: both answered no fork, dispatch a
      non-fork agent with `model: "opus"` and `effort: "medium"`, quoting that line. No new
      undecided gap.
- [x] Gaps declined in the re-probes: how a non-fork reviewer gets its context (owned by
      "Constructing Reviewer Prompts" and "Reviewer inputs" in this SKILL.md, outside the probe
      excerpt); whether `subagent-model-gate` flags a fork or a judging scanner (owned by the hook
      and its docs); classifying a dispatch as a review counts as the dispatcher's judgment (the
      paragraph enumerates the roles and gives the produced-vs-raw test, so the level is not the
      dispatcher's choice); the haiku `low` row on the Agent tool needs an ask (pre-existing, row
      unchanged by this task); what to do if the tool rejected the field (it does not; the field
      accepts `medium` when a skill asks).
- [x] Tiers and cells: RED 2 tiers x 3 questions; GREEN 2 tiers x 5 questions; re-probe 1 and 2
      each 2 tiers x 5 questions; re-probe 3 2 tiers x 1 question. All probes ran as
      `bitranox:baseline-probe` (text only) with the excerpt declared the text under test; every
      quote was checked against the pasted excerpt and none quoted text absent from it.
- [x] Description: unchanged (no frontmatter edit)
- [x] Tables: `reformat_tables.py` reports the file unchanged (canonical); new rows fit the existing
      widths
- [x] ASCII only in the added lines; no addresses, hostnames or private paths added
- [x] Tests: `test_model_tiers.py` and the skill's own `tests/` pass with CI's dependency set
- [x] Security scan: prose edits only, no secrets, hostnames, paths or PII

## Fix round (final whole-branch review)

- [x] Review dispatches paragraph, effort warning and table row state the rule as the skill's own:
      no dates, no attribution, no maintainer setting. The omitted-field sentence now reads "an
      omitted field inherits the session or settings default, which is often higher", and the
      token figure is narrowed to what was measured ("on one measured prompt ... about twice the
      output tokens it spent at `medium`"). The table row reads "`medium` on `opus`", re-padded to
      the existing column width.
- [x] "It does NOT cover" now names the final synthesis (keeps `xhigh` or `max`) and `haiku`
      mechanical scans (keep `low`). `subagent-model-gate` keeps warning on a `haiku`
      review-shaped dispatch on purpose (a review mis-tiered to haiku is what it catches), and its
      message tells a mechanical scan that makes no judgment to ignore it.
- [x] `task-reviewer-prompt.md`: the stale `[MODEL]` placeholder line is gone (the template
      hard-codes `model: opus`).
- [x] Quote-back on the final text, `bitranox:baseline-probe`, haiku and opus, one cell per
      question per tier (2 x 3). Question: per-task reviewer, final synthesis, fixer - which model
      and effort, quote the line. Both tiers: (a) opus / medium, quoting "Every dispatch whose job
      is to JUDGE work ... runs on `model: "opus"` with `effort: "medium"`"; (b) opus / `xhigh` or
      `max`, quoting "the final synthesis (it keeps `xhigh` or `max`, see the table below)" and the
      Final synthesis row; (c) opus with no effort field, quoting "It does NOT cover implementers
      and fixers" and "Non-review `opus` fan-out / judgment / reasoning | inherit - do not set".
      Every quote checked against the pasted excerpt.
- [x] Gaps from the quote-back, declined: no rule for choosing `xhigh` over `max` (the table row
      predates this change and leaves the level to the dispatcher by design); where the final
      synthesis ends and the final whole-branch review or an adjudicator begins (both role names
      are listed explicitly; a sharper boundary is outside this fix round's scope); fixers are not
      named in Concrete tiers (they map to "implementers working from prose"; out of scope here);
      the fork warning is stated for reviews only (a synthesis sent as a fork is a separate
      question, out of scope); the elided channel paragraph (deliberately cut from the excerpt).
- [x] ASCII only; no addresses, hostnames, private paths or provenance added.
