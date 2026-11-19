# skill-writer checklist - coding-python-uv (smoke-test a published wheel isolated)

- [x] Change: the VIRTUAL_ENV gotcha gains the published-wheel smoke case: --isolated or env -u
      VIRTUAL_ENV, and require site-packages in __file__.
- [x] Decisions: d-20261119-bfc8d2fb
- [x] Mechanism executed: uv 0.13.0 with VIRTUAL_ENV on a dev venv: plain and `python -I` imported
      src/<pkg>/__init__.py; --isolated and env -u VIRTUAL_ENV imported site-packages in uv's cache.
- [x] Step 0b: `skill_decisions.py show coding-python-uv --kind rejected,removed` read in this worktree at the
      origin default branch; no declined entry is re-proposed and no live rule's anchor touched.
- [x] RED as a text check: opus (effort medium) and haiku quote-backs against the pre-edit text
      answered NONE, or only a neighbouring line that does not answer, for Q15.
- [x] GREEN quote-back on opus (effort medium) and haiku against the edited text: every quote for
      Q15 was found verbatim in the edited text and none in the pre-edit text.
- [x] Width and fence check over the added lines printed nothing; tables canonical.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Present tense, no history lines, no private hosts, paths or personal data.
