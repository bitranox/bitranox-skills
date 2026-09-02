"""Tests for pushcheck.py - would this push publish something private?

The tool exists because the check was twice run AFTER the push instead of before, and came
back clean both times, which is luck rather than method. Publishing is the irreversible
direction: a value pushed to a public repo stays in public history even after the file is
fixed, because scrubbing it needs a force-push.

Two properties matter more than the pattern list and are what most of these tests pin:

- Visibility is resolved from the REMOTE, never from the directory name. Measured 2026-09-01:
  the folder `public/KI/RESEARCH` holds a PRIVATE repo. A name-based guess is wrong in both
  directions - it also calls a public repo private and waves the scan through.
- Every non-answer fails CLOSED. Unknown visibility, an unreadable range and an EMPTY range are
  all refusals, not passes. A gate that reports "nothing found" after examining nothing is the
  failure this whole file guards against.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import pushcheck as PC

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "pushcheck.py"


# ---- remote parsing: the visibility question starts here ----------------------------------

@pytest.mark.parametrize("url, expected", [
    ("git@github.com:bitranox/skills.git", ("github.com", "bitranox", "skills")),
    ("https://github.com/bitranox/skills.git", ("github.com", "bitranox", "skills")),
    ("https://github.com/bitranox/skills", ("github.com", "bitranox", "skills")),
    ("ssh://git@github.com/owner/repo.git", ("github.com", "owner", "repo")),
    ("git@gitea.example.test:team/thing.git", ("gitea.example.test", "team", "thing")),
])
def test_parse_remote_reads_owner_and_repo_from_the_url(url, expected):
    assert PC.parse_remote(url) == expected


def test_parse_remote_returns_none_for_something_that_names_no_repo():
    """A local path remote has no owner/repo, so visibility cannot be resolved from it - and
    that must surface as unknown rather than as a parse that quietly invents a name."""
    assert PC.parse_remote("/srv/git/bare.git") is None
    assert PC.parse_remote("") is None


# ---- the scan: what counts as private ------------------------------------------------------

def test_a_posix_home_path_is_found():
    hits = PC.scan_text("see /home/alice/notes.md for the rest", "f.py")
    assert [h.kind for h in hits] == ["abs_path"]
    assert hits[0].line == 1


def test_a_windows_user_path_is_found():
    hits = PC.scan_text(r"copy C:\Users\alice\thing.txt over", "f.py")
    assert [h.kind for h in hits] == ["abs_path"]


def test_an_rfc1918_address_is_found_and_a_documentation_address_is_not():
    """RFC5737 ranges exist to be written down. Flagging them trains the reader to skip the
    report, which is how a real finding gets waved through."""
    assert [h.kind for h in PC.scan_text("host 192.168.1.10", "f")] == ["private_ip"]
    assert PC.scan_text("host 192.0.2.10 and 198.51.100.4 and 203.0.113.9", "f") == []


def test_a_loopback_and_an_unspecified_address_are_not_findings():
    assert PC.scan_text("bind 127.0.0.1 and 0.0.0.0", "f") == []


def test_an_example_domain_is_not_a_finding_but_an_internal_host_is():
    assert PC.scan_text("ssh admin@box.example.com", "f") == []
    hits = PC.scan_text("ssh admin@vm-build-07.internal", "f")
    assert [h.kind for h in hits] == ["hostname"]


@pytest.mark.parametrize("code", [
    "root = Path.home() / '.config'",
    "value = self.local",
    "cfg = settings.home",
    "obj.corp = 1",
])
def test_attribute_access_is_not_mistaken_for_an_internal_hostname(code):
    """Found by running the tool on this very repo: `Path.home()` was reported as a hostname,
    because `home` is an internal TLD and attribute access is shaped exactly like a domain.

    A false positive here is not cosmetic. This gate's whole value is that its report gets read,
    and a report full of `Path.home` teaches the reader to skim - which is how the one real
    finding gets waved through. A host is required to LOOK like one: a digit or hyphen in its
    first label, or three or more labels.
    """
    assert PC.scan_text(code, "f.py") == []


def test_a_host_shaped_internal_name_is_still_found():
    """The control for the test above: the narrowing must not silence real hostnames."""
    assert [h.text_excerpt for h in PC.scan_text("ssh vm-build-07.internal", "f")] \
        == ["vm-build-07.internal"]
    assert [h.text_excerpt for h in PC.scan_text("ssh box.eu-west.corp", "f")] \
        == ["box.eu-west.corp"]


def test_a_configured_secret_term_is_found_case_insensitively():
    """The denylist carries the operator's own hostnames and usernames. It is supplied at call
    time and never shipped, so this tool can be public while the terms stay private."""
    hits = PC.scan_text("deploy to PX-Main tonight", "f", denylist=["px-main"])
    assert [h.kind for h in hits] == ["denylist"]


def test_the_scan_reports_the_line_number_so_a_finding_can_be_opened():
    hits = PC.scan_text("clean\nclean\n/home/bob/x\n", "f.py")
    assert hits[0].line == 3


def test_only_added_lines_are_scanned_not_removed_ones():
    """A diff line starting with '-' is content LEAVING the repo. Flagging it makes a cleanup
    commit unpushable, which is precisely backwards.

    The two lines carry DIFFERENT usernames on purpose. With the same name on both, the excerpts
    are identical and the assertion cannot tell which line matched - it would pass whether or not
    removed lines were scanned.
    """
    diff = ("+++ b/a.py\n"
            "@@ -1,2 +1,2 @@\n"
            "+/home/added-user/x\n"
            "-/home/removed-user/x\n")
    assert [h.text_excerpt for h in PC.scan_diff(diff)] == ["/home/added-user"]


# ---- the verdict: fail closed ---------------------------------------------------------------

def test_findings_on_a_public_repo_are_a_refusal():
    v = PC.decide(visibility="public", findings=[PC.Finding("abs_path", "f", 1, "/home/a")],
                  examined_lines=10)
    assert not v.ok and v.exit_code == 1


def test_findings_on_a_private_repo_are_reported_but_do_not_refuse():
    """A private repo is where this content legitimately lives. Refusing there would make the
    gate something to switch off, and a gate that is off protects the public repo not at all."""
    v = PC.decide(visibility="private", findings=[PC.Finding("abs_path", "f", 1, "/home/a")],
                  examined_lines=10)
    assert v.ok and v.exit_code == 0
    assert v.findings


def test_unknown_visibility_refuses_even_with_no_findings():
    """The whole point is that the directory name cannot answer this. If the remote could not
    answer either, the honest result is 'I do not know', and not knowing must not read as safe."""
    v = PC.decide(visibility=None, findings=[], examined_lines=10)
    assert not v.ok and v.exit_code == 2
    assert "visibility" in v.reason.lower()


def test_an_empty_range_refuses_instead_of_reporting_a_clean_scan():
    """Zero examined lines is a broken instrument, not a clean bill of health - a gate must say
    how much it examined and treat zero as a refusal."""
    v = PC.decide(visibility="public", findings=[], examined_lines=0)
    assert not v.ok and v.exit_code == 2
    assert "nothing" in v.reason.lower() or "empty" in v.reason.lower()


def test_a_clean_public_range_passes_and_says_how_much_it_read():
    v = PC.decide(visibility="public", findings=[], examined_lines=42)
    assert v.ok and v.exit_code == 0
    assert v.examined_lines == 42


# ---- CLI: measured by running it ------------------------------------------------------------

def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _repo(tmp_path: Path, remote: str = "git@github.com:owner/repo.git") -> Path:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.test")
    _git(repo, "config", "user.name", "t")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-qm", "seed")
    _git(repo, "remote", "add", "origin", remote)
    return repo


def run_cli(args, cwd):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True,
                          encoding="utf-8", check=False, cwd=str(cwd))


def test_cli_refuses_a_public_repo_whose_range_carries_a_home_path(tmp_path):
    repo = _repo(tmp_path)
    (repo / "doc.md").write_text("run it from /home/alice/project\n", encoding="utf-8")
    _git(repo, "add", "doc.md")
    _git(repo, "commit", "-qm", "add doc")
    r = run_cli(["--repo", str(repo), "--range", "HEAD~1..HEAD", "--visibility", "public",
                 "--json"], tmp_path)
    assert r.returncode == 1, r.stdout + r.stderr
    env = json.loads(r.stdout)
    assert env["ok"] is False
    assert env["data"]["findings"][0]["kind"] == "abs_path"
    assert env["data"]["examined_lines"] >= 1


def test_cli_passes_a_clean_public_range_and_reports_what_it_read(tmp_path):
    repo = _repo(tmp_path)
    (repo / "doc.md").write_text("nothing private here\n", encoding="utf-8")
    _git(repo, "add", "doc.md")
    _git(repo, "commit", "-qm", "add doc")
    r = run_cli(["--repo", str(repo), "--range", "HEAD~1..HEAD", "--visibility", "public",
                 "--json"], tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    env = json.loads(r.stdout)
    assert env["ok"] is True and env["data"]["examined_lines"] >= 1


def test_cli_exits_2_on_an_empty_range_rather_than_reporting_clean(tmp_path):
    repo = _repo(tmp_path)
    r = run_cli(["--repo", str(repo), "--range", "HEAD..HEAD", "--visibility", "public",
                 "--json"], tmp_path)
    assert r.returncode == 2
    assert json.loads(r.stdout)["ok"] is False


def test_cli_emits_json_on_the_error_path_too(tmp_path):
    """--json must survive the failure path, or a caller parsing stdout gets a traceback."""
    r = run_cli(["--repo", str(tmp_path / "nope"), "--json"], tmp_path)
    assert r.returncode == 2
    assert "Traceback" not in r.stderr
    assert json.loads(r.stdout)["ok"] is False


def test_paths_can_be_excluded_so_a_scanner_does_not_block_on_its_own_fixtures(tmp_path):
    """Found by running this tool on its own push: all 16 findings were the fixture strings in
    this very file, which the tool must detect by construction.

    Every project with security fixtures has that shape. Without an exclusion the tool refuses
    such a repo's every push, and a gate that has to be bypassed routinely is one that gets
    bypassed when it matters - the failure it exists to prevent, arriving by a different route.
    """
    repo = _repo(tmp_path)
    (repo / "fixtures.py").write_text("SAMPLE = '/home/alice/x'\n", encoding="utf-8")
    (repo / "real.md").write_text("nothing private\n", encoding="utf-8")
    _git(repo, "add", "fixtures.py", "real.md")
    _git(repo, "commit", "-qm", "add both")
    args = ["--repo", str(repo), "--range", "HEAD~1..HEAD", "--visibility", "public", "--json"]
    assert run_cli(args, tmp_path).returncode == 1                      # control: it fires
    r = run_cli([*args, "--exclude", "fixtures.py"], tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    # Control: the exclusion is scoped, not a global off switch.
    assert json.loads(r.stdout)["data"]["examined_lines"] >= 1


def test_an_exclusion_that_matches_nothing_is_reported_not_silently_ignored(tmp_path):
    """A typo'd exclusion that silently matches nothing leaves the caller believing a path is
    covered by it, which is the quiet direction."""
    repo = _repo(tmp_path)
    (repo / "doc.md").write_text("/home/alice/x\n", encoding="utf-8")
    _git(repo, "add", "doc.md")
    _git(repo, "commit", "-qm", "add doc")
    r = run_cli(["--repo", str(repo), "--range", "HEAD~1..HEAD", "--visibility", "public",
                 "--json", "--exclude", "no/such/path.py"], tmp_path)
    assert r.returncode == 1
    assert json.loads(r.stdout)["data"]["unused_exclusions"] == ["no/such/path.py"]
