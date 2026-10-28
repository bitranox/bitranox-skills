# skill-writer checklist - devops-bmk (2026-10-28, pytest 9.2.0 drops xdist groups, bmk 3.31.0)

Twin sync of bmk's own devops-bmk copy for bmk 3.31.0: one sentence group appended to the xdist
paragraph. Lines come byte-identical from bmk's patch (the twin must match).

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference; the test is retrieval - why a grouped suite runs serially, and what
      restores the parallel run.
- [x] RED by text check against the pre-change file: no line names pytest 9.2.0 or the
      `[coverage] tests run in one process` line.
- [x] Claims checked here, each by its own instrument:
      - every group dropped, `pytestmark` included: measured in this repo's session (8 tests,
        `-n 4 --dist loadgroup`, xdist 3.8.0): pytest 9.2.0 spread all arms over gw0..gw3 with no
        `@g`, pytest 8.4.2 / 9.0.3 / 9.1.1 grouped the `pytestmark` control.
      - the mechanism: installed xdist 3.8.0 `xdist/remote.py:254` assigns `item._nodeid`, and
        pytest 9.2.0's `Node.nodeid` property returns `str(self._id)`.
      - bmk's guard and its line: `bmk/adapters/stagerunner/helpers/_coverage.py:488` prints
        "[coverage] tests run in one process: this pytest drops pytest-xdist's xdist_group marks",
        committed in bmk c005219.
      - pytest-xdist issue #1386: cited by bmk, not opened here.
- [x] GREEN: run by bmk on opus and haiku plus a quote-back (bmk repo,
      skills/devops-bmk/.skillwriter/checklist-20261028-pytest92-groups.md).
- [x] Description unchanged - no routing keyword moved.
- [x] Added lines: no address, hostname or machine path; ASCII only; no version-history phrasing.
