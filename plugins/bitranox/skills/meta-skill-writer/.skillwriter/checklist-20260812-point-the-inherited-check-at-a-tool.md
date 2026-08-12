# skill-writer checklist - meta-skill-writer (2026-08-12, the inherited-context check gets a tool)

Change: the passage shipped in 5.196.0 told the reader to check whether the lesson under test is
already in the CLAUDE.md cascade or memory store, and left the enumeration to them. It now points
at `redcheck --corpus-cascade` in `bitranox:process-test-driven-development`, which assembles that
context itself. Three places: the RED-phase rule in SKILL.md, the RED-phase checklist item, and
both the "before trusting a RED" paragraph and route 2 in testing-skills-with-subagents.md. Each
also states how to read the result - a hit is strong and names the file, a clean result only means
not caught, exit 3 means nothing was checked.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique. Application scenario.
- [x] Not a new section. 5.196.0 established the rule; what it lacked was an instrument, so every
      reader following it re-derived the same enumeration by hand. That is the gap this closes.
- [x] NO BEHAVIOURAL RED WAS STAGED, and this skill's own rule is the reason: the lesson is in this
      machine's always-loaded index AND already in this skill's text as of 5.196.0, so an arm
      testing it would be contaminated twice over and could not fail honestly. Applying the rule to
      the change that ships the rule's tool.
- [x] DECLARED ROUTE: route 1, the coverage check against the FILE, now run with the tool this
      change points at rather than by hand. `redcheck --corpus-cascade` over the directory this
      repo sits in assembled 608 documents and returned exit 1 on a scenario about a lesson that
      index carries, naming the memory fact body and the pointer block that teach it; exit 0 on an
      unrelated scenario over the same corpus; exit 3 on an empty one. The instrument was seen
      giving all three answers before being cited as evidence for anything.
- [x] The instrument was verified against a KNOWN NEGATIVE before being trusted, not only against
      the case it was built for: the unrelated-scenario arm is the control, and it stayed clean
      over the same 608 documents.
- [x] Text states the ASYMMETRY rather than implying a guarantee, in all three places: a hit is
      strong evidence and names the file, a clean result means not caught rather than absent
      because term overlap cannot see a paraphrase, and exit 3 means the corpus was empty and
      nothing was checked at all. A reader must not be able to take a clean run for a sealed
      fixture, since that is the same class of defect the passage is about.
- [x] Route 2 was updated too, not just the first mention. It previously said to choose an untaught
      domain "with the same check" - the hand-rolled one - and now names the tool and notes the
      same run flags a scenario that hands over its own answer.
- [x] The RED-phase checklist item now names the command, so the box cannot be ticked by having
      thought about it.
- [x] Written for readers who do not run this plugin: the tool is named with its owning skill, the
      invocation is shown once, and the cascade and memory store are described by what they are
      rather than by this machine's layout.
- [x] Token budget: one code block and a short paragraph in the reference file that owns baseline
      mechanics; SKILL.md gains a clause on the existing rule and four words on the checklist line.
      No new section anywhere.
- [x] Frontmatter description unchanged, so the generated skill docs need no new description text.
- [x] No session narrative or private provenance in the skill text - no memory-fact slug, no
      machine paths, no document counts. The measured numbers live in this artifact only.
- [x] No addresses, MACs, hostnames or machine paths added.
