# Checklist: memory_add body optional on an update (OPEN-WORK [510] item 5)

- [x] RED: `git show origin/master:plugins/bitranox/skills/meta-self-improve/SKILL.md | grep -n "body. are required"`
      -> "`title`, `hook` and `body` are required", which the tool change below makes false.
- [x] Change is behaviour-led: hooks/mods/register.ts drops `body` from `required`, and
      mod_bridge.py passes an absent body to the engine; tests
      test_an_update_without_a_body_keeps_the_stored_body and
      test_a_create_without_a_body_is_an_empty_body_refusal in hooks/tests/test_mod_bridge.py
      (RED on the old bridge: exit 1 BadInput "body must be a non-empty string"; GREEN after).
- [x] GREEN: the paragraph now reads "`title` and `hook` are required, `body` ... may be omitted
      only on an update, which then keeps the stored body (a new fact without one is refused as
      `EmptyBody`)" - quoted back with grep -n "omitted only on an update".
- [x] Placed in the paragraph a reader calling the tool already reads (step 4, the mod route).
- [x] Frontmatter description untouched.
