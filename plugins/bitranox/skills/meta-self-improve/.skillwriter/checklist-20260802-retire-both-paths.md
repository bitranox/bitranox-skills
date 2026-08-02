# skill-writer checklist - meta-self-improve (2026-08-02, retirement has two paths)

Change: the retirement rule shipped earlier today assumed you can land the contribution yourself.
It now states both paths and names the check that backstops the slower one.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, issued this session).
- [x] Corrects a rule shipped hours earlier in this same skill, rather than layering onto it: the
      first version said to delete the local copy "once the shipped copy is committed", which only
      describes a contributor with commit rights. Through a PR the twin appears in a later session,
      so that instruction is unfollowable for most readers and would read as license to delete the
      local copy before anything replaced it.
- [x] Both paths stated concretely: with commit rights the local copy goes in the SAME change as
      the push, because there is no window to forget in; via a PR it goes when the twin lands.
- [x] Does not rely on the reader remembering the second case - names
      `bitranox:meta-audit-local-skills-and-hooks` and its `duplicate-of-shipped` check, and that
      the deep dream runs that audit. A rule whose compliance depends on recalling it months later
      is a rule with no mechanism.
- [x] Cross-skill reference by skill NAME (no path, no `@` link), per this skill-writer's rule for
      referencing another skill.
- [x] Scope held: the surrounding CONTRIBUTE bullet, the drift measurement and the caller-check
      instruction are unchanged - this edit only splits the WHEN.
- [x] No session narrative or private provenance added; no machine paths added.
