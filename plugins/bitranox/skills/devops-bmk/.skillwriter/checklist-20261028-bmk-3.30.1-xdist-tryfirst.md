# skill-writer checklist - devops-bmk (2026-10-28, xdist_group tryfirst rule, bmk 3.30.1)

Twin sync of bmk's own devops-bmk copy for bmk 3.30.1. One passage changed, the xdist paragraph:
a conftest `pytest_collection_modifyitems` that adds `xdist_group` needs
`@pytest.hookimpl(tryfirst=True)`; a module-level `pytestmark` needs no hook; check a group by the
`@<name>` node-id suffix on one worker in a `pytest -n 4 --dist loadgroup -v` run, never by a
green run. Lines come byte-identical from bmk's patch (the twin must match).

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference; the test is retrieval - how to make and check an xdist group.
- [x] RED by text check against the pre-change file: no line names `tryfirst`, `@<name>` or
      `--dist loadgroup`.
- [x] Claim re-measured here, not taken from the sender: scratch project, 8 tests, `-n 4 --dist
      loadgroup -v`, pytest-xdist 3.8.0, Python 3.15. On pytest 8.4.2: a `pytestmark` control ran
      on gw0 only with `@g`; the conftest hook without `tryfirst` spread over gw0..gw3 with no
      suffix; with `tryfirst` gw0 only with `@g` - the paragraph's claim holds. pytest 9.0.3 and
      9.1.1 group the control too.
- [x] Finding beyond the text, reported to bmk, not written into the twin alone: on pytest 9.2.0
      (released 2026-10-27) with xdist 3.8.0, the latest, NO arm groups - not even the
      `pytestmark` control - and every run stays green. The paragraph's own check (the `@<name>`
      suffix, never a green run) is what exposes it.
- [x] GREEN: run by bmk on opus and haiku plus a quote-back (bmk repo,
      skills/devops-bmk/.skillwriter/checklist-20261028-xdist-group-tryfirst.md).
- [x] Description unchanged - no routing keyword moved.
- [x] Added lines: no address, hostname or machine path; ASCII only; no version-history phrasing.
