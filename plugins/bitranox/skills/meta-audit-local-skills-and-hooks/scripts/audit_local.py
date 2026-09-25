#!/usr/bin/env python3
"""Audit the skills and hooks that no plugin ships.

`targets` answers the only question worth asking before spending reviewers: which dirs is this
allowed to touch? The same shipped skill is reachable at the source checkout, the marketplace
clone and the version cache at once, and ten tool repos in the tree ship mirrored twins. Reviewing
those is wasted work; EDITING one outside the mirror ritual manufactures the drift the marketplace
CLAUDE.md exists to prevent. So run `targets` and read it before running anything else.

    audit_local.py targets [--root DIR ...] [--no-personal] [--home DIR] [--json]
    audit_local.py check   [--root DIR ...] [--no-personal] [--home DIR]
                           [--shipped SKILLS_DIR] [--json]

Exit codes are format-independent, and the two verbs answer OPPOSITE questions with the same
numbers - do not wire CI off one of them expecting the other:

    targets   0 = targets found      1 = none found        2 = error
    check     0 = no findings        1 = findings found    2 = error

So `check` exiting 0 is the CLEAN result, and it exits 0 over an empty tree too (0 findings
across 0 targets) - run `targets` first if you need to know anything was in scope at all.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hooks"))

import harness_checks as hc  # noqa: E402


def gather(roots, home=None, personal=True, unlistable=None):
    """(selected, skipped) for `roots`, where each skipped entry carries the reason it was cut.

    A directory the walk could not list is a skipped entry too, and is also appended to
    `unlistable` as (path, reason) when a list is passed: an unreadable subtree otherwise reads
    exactly like one holding nothing."""
    errors = []
    candidates = hc.discover_candidates(roots, home=home, personal=personal, errors=errors)
    selected = hc.select_targets(candidates, home=home)
    chosen = set(selected)
    skipped = []
    for candidate in candidates:
        if candidate in chosen:
            continue
        reason = hc.skip_reason(candidate, home=home) or "duplicate checkout of a selected target"
        skipped.append({"path": str(candidate), "reason": reason})
    # Plugin-owned dirs are not `.claude/skills`-shaped, so they are never candidates and would
    # leave the skipped list empty - making a correctly-scoped run indistinguishable from a walk
    # that found nothing. Name them explicitly.
    for owned in hc.discover_shipped(roots, home=home, errors=errors):
        skipped.append({"path": str(owned),
                        "reason": hc.skip_reason(owned, home=home) or "shipped by a plugin"})
    seen = set()
    for path, why in errors:                  # both walks meet the same dir; report it once
        if path in seen:
            continue
        seen.add(path)
        skipped.append({"path": path, "reason": "cannot list, not audited: %s" % why})
        if unlistable is not None:
            unlistable.append((path, why))
    skipped.sort(key=lambda entry: entry["path"])
    return selected, skipped


def _home(args):
    """The home dir to treat as the machine's own, defaulting to the real one.

    Overridable so a run can be aimed at a fixture: without it, auditing a sandbox silently mixes
    in findings about the operator's actual `~/.claude`, and the report reads as if they came from
    the tree under test."""
    return Path(args.home) if getattr(args, "home", "") else None


def _envelope(selected, skipped):
    return {
        "ok": True,
        "command": "targets",
        "data": {"targets": [str(p) for p in selected], "count": len(selected)},
        "skipped": skipped,
    }


def render_text(selected, skipped, out):
    """Human rendering. The skipped block is not noise - it is the proof the filter ran."""
    if selected:
        print("targets (%d):" % len(selected), file=out)
        for path in selected:
            print("  %s" % path, file=out)
    else:
        print("targets: none", file=out)
    if skipped:
        print("\nskipped (%d):" % len(skipped), file=out)
        for entry in skipped:
            print("  %s\n      %s" % (entry["path"], entry["reason"]), file=out)


def cmd_targets(args, out=None, err=None):
    """Print the selection and return its exit code."""
    out = out or sys.stdout
    err = err or sys.stderr
    roots = [Path(r) for r in args.root]
    for root in roots:
        if not root.is_dir():
            print("warning: root does not exist, skipping: %s" % root, file=err)
    unlistable = []
    selected, skipped = gather(roots, home=_home(args), personal=not args.no_personal,
                               unlistable=unlistable)
    for path, why in unlistable:
        print("warning: cannot list, not audited: %s: %s" % (path, why), file=err)
    if args.json:
        print(json.dumps(_envelope(selected, skipped), indent=2), file=out)
    else:
        render_text(selected, skipped, out)
    return 0 if selected else 1


def check_skills(target, shipped=None):
    """Deterministic findings for one skills dir, as (check name, message) pairs."""
    target = Path(target)
    found = [("frontmatter", m) for m in hc.frontmatter_problems(target)]
    skills = [d for d in sorted(target.iterdir()) if d.is_dir()]
    found += [("tests-missing", "%s ships a .py but carries no test" % p.name)
              for p in hc.packages_missing_tests(skills)]
    for skill in skills:
        for path, error, unmeasured in hc.uncollectable_tests(skill / "tests"):
            check = "tests-unmeasured" if unmeasured else "tests-uncollectable"
            found.append((check, "%s: %s" % (path, error)))
    for name, twin, ratio in hc.unmanaged_twins(target, shipped or {}):
        found.append(("unmanaged-twin",
                      "%s duplicates the shipped skill %s (description match %.0f%%) and no "
                      "mirror gate covers the pair" % (name, twin, ratio * 100)))
    found += [("graveyard", "%s: %s" % (p, why)) for p, why in hc.graveyard_entries(target)]
    return found


def _kind(value):
    return {dict: "an object", list: "a list", str: "a string", type(None): "null"}.get(
        type(value), type(value).__name__)


def _group_shape_problem(event, groups):
    """Why one event's matcher groups are not the shape Claude Code reads, or None."""
    if not isinstance(groups, list):
        return '"hooks.%s" is %s, not a list of matcher groups' % (event, _kind(groups))
    for group in groups:
        if not isinstance(group, dict):
            return '"hooks.%s" holds %s, not a matcher group object' % (event, _kind(group))
        inner = group.get("hooks")
        if inner is not None and not isinstance(inner, list):
            return '"hooks.%s[].hooks" is %s, not a list' % (event, _kind(inner))
        for hook in inner or []:
            if not isinstance(hook, dict):
                return '"hooks.%s[].hooks" holds %s, not a hook object' % (event, _kind(hook))
    return None


def _hooks_shape_problem(data):
    """Why parsed settings are not the shape Claude Code reads hooks from, or None."""
    if not isinstance(data, dict):
        return "the top level is %s, not a JSON object" % _kind(data)
    hooks = data.get("hooks")
    if hooks is None:
        return None
    if not isinstance(hooks, dict):
        return '"hooks" is %s, not an object keyed by event' % _kind(hooks)
    for event, groups in hooks.items():
        problem = _group_shape_problem(event, groups)
        if problem:
            return problem
    return None


def settings_problem(path):
    """Why a settings file cannot be read for its hooks, or None when it can.

    A file Claude Code cannot load disables every hook it registers, and the registration check
    reads such a file as registering nothing - so it has to be named here, or the harness it kills
    is reported clean."""
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        return "unreadable: %s" % exc
    if raw.startswith(b"\xef\xbb\xbf"):
        return "it starts with a UTF-8 byte-order mark, which JSON readers commonly refuse"
    try:
        data = json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        return "not UTF-8: %s" % exc
    except ValueError as exc:
        return "not valid JSON: %s" % exc
    return _hooks_shape_problem(data)


def _settings_findings(settings, home):
    """(findings, registered paths) for the settings files: an unloadable file is one finding and
    contributes no registrations; a loadable one is checked for registrations naming missing files."""
    found, loadable = [], []
    for path in settings:
        problem = settings_problem(path)
        if problem:
            found.append(("settings-unparseable", "%s: %s - every hook it registers is dead, and none of "
                                                   "them could be checked" % (path, problem)))
        else:
            loadable.append(path)
    for path in loadable:
        for event, _command, missing in hc.registration_problems(path, home=home):
            found.append(("registration", "%s (%s): command names %s, which does not exist - the "
                                          "hook silently never fires" % (path.name, event, missing)))
    return found, hc.registered_paths(loadable, home=home)


def check_personal(home=None, shipped_root=None):
    """Deterministic findings for the personal harness: registrations, hooks, tombstones, and any
    local hook or skill script the marketplace now ships too.

    The dedup half exists because contributing upstream is ASYNCHRONOUS for anyone without commit
    rights: the PR lands in a later session, so no session is standing at the contribution to retire
    the local copy when the twin finally appears. Every other check keeps passing - the file exists,
    it is registered, its tombstone is well formed - because none of them asks whether the plugin
    now ships the same thing."""
    home = Path(home) if home is not None else Path.home()
    claude, found = home / ".claude", []
    if shipped_root:
        for local, twin, status in hc.duplicate_shipped_files(
                [claude / "hooks", claude / "skills"], shipped_root):
            if status == "identical":
                found.append(("duplicate-of-shipped",
                              "%s is byte-identical to the shipped %s. Retire the local copy "
                              "(delete it, or leave a tombstone naming the replacement) so there is "
                              "one source of truth, and repoint whatever still invokes the local "
                              "path." % (local, twin)))
            else:
                found.append(("duplicate-of-shipped",
                              "%s DIFFERS from the shipped %s. Do NOT delete it to dedup: read the "
                              "diff first and say which side holds what. If the local copy is ahead "
                              "(a fix, a wider scope), CONTRIBUTE that upstream and retire it only "
                              "once the improvement has landed - deduping here would throw the "
                              "improvement away. If the shipped copy is ahead, retire the local one."
                              % (local, twin)))
    settings = [p for p in sorted(claude.glob("settings*.json")) if p.is_file()]
    settings_found, registered = _settings_findings(settings, home)
    found += settings_found
    hooks_dir = claude / "hooks"
    found += [("orphan-hook", "%s is registered nowhere and is neither a library nor a tombstone"
               % p.name) for p in hc.orphan_scripts(hooks_dir, registered)]
    if hooks_dir.is_dir():
        for path in sorted(hooks_dir.iterdir()):
            if path.is_file() and path.suffix in (".py", ".sh") and hc.is_retired_shim(path):
                found += [("shim", "%s: %s" % (path.name, why))
                          for why in hc.shim_problems(path, registered, home=home)]
        # The hooks dir keeps its tests beside the scripts rather than per-skill, so the
        # collectability check has to be aimed at it explicitly or the loudest defect goes unseen.
        for path, error, unmeasured in hc.uncollectable_tests(hooks_dir / "tests"):
            check = "tests-unmeasured" if unmeasured else "tests-uncollectable"
            found.append((check, "%s: %s" % (path, error)))
        found += [("graveyard", "%s: %s" % (p, why)) for p, why in hc.graveyard_entries(hooks_dir)]
    # Deliberately shallow: ~/.claude holds gigabytes of transcripts and caches that are not
    # harness content, so only the parked-skills case is worth a top-level look.
    for path in sorted(claude.glob("*.bak")):
        if path.is_dir():
            count = sum(1 for _ in path.glob("*/SKILL.md"))
            found.append(("graveyard", "%s: parked dir holding %d skill(s)" % (path, count)))
    return found


def _missing_path_args(args):
    """One line per path argument naming a directory that does not exist.

    `check` must refuse these rather than skip them: a typo in --root audits nothing, one in
    --home audits an empty harness, and one in --shipped turns the duplicate checks off - and all
    three would otherwise print "clean" and exit 0."""
    named = [("--root", r) for r in args.root]
    named += [(flag, value) for flag, value in (("--home", args.home), ("--shipped", args.shipped))
              if value]
    return ["%s is not a directory: %s" % (flag, value) for flag, value in named
            if not Path(value).is_dir()]


def cmd_check(args, out=None, err=None):
    """Run every deterministic check over the selected targets and return an exit code."""
    out = out or sys.stdout
    err = err or sys.stderr
    missing = _missing_path_args(args)
    if missing:
        for line in missing:
            print("error: %s" % line, file=err)
        return 2
    home = _home(args) or Path.home()
    unlistable = []
    selected, skipped = gather([Path(r) for r in args.root], home=_home(args),
                                personal=not args.no_personal, unlistable=unlistable)
    # resolve() first: "." has no parent of its own, and --shipped names a skills/ dir whose
    # PARENT is the plugin root that also holds hooks/.
    shipped_dir = Path(args.shipped).resolve() if args.shipped else None
    shipped = hc.shipped_descriptions(shipped_dir) if shipped_dir else {}
    results, total = [], 0
    for path, why in unlistable:
        total += 1
        results.append({"target": path, "findings": [
            {"check": "unlistable", "message": "cannot list, not audited: %s" % why}]})
    for target in selected:
        findings = check_skills(target, shipped)
        total += len(findings)
        results.append({"target": str(target),
                        "findings": [{"check": c, "message": m} for c, m in findings]})
    # The personal harness is a target in its own right, never a rider on ~/.claude/skills.
    # Hanging it off that target meant a home with broken hooks but no personal skill produced
    # no target at all, so the run printed "0 finding(s) across 0 target(s)" and exited 0 over
    # exactly the rot this check exists to find.
    if not args.no_personal:
        findings = check_personal(home, shipped_root=shipped_dir.parent if shipped_dir else None)
        total += len(findings)
        results.append({"target": str(home / ".claude"),
                        "findings": [{"check": c, "message": m} for c, m in findings]})
    if args.json:
        print(json.dumps({"ok": True, "command": "check",
                          "data": {"results": results, "finding_count": total},
                          "skipped": skipped}, indent=2), file=out)
    else:
        for entry in results:
            print("\n%s" % entry["target"], file=out)
            if not entry["findings"]:
                print("  clean", file=out)
            for finding in entry["findings"]:
                print("  [%s] %s" % (finding["check"], finding["message"]), file=out)
        print("\n%d finding(s) across %d target(s)" % (total, len(results)), file=out)
    del err
    return 0 if total == 0 else 1


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    subs = parser.add_subparsers(dest="command", required=True)
    targets = subs.add_parser("targets", help="list the skill dirs no plugin ships, then exit")
    targets.add_argument("--root", action="append", default=[],
                         help="a tree to walk for project skills; repeatable")
    targets.add_argument("--no-personal", action="store_true",
                         help="leave ~/.claude/skills out (the per-tree pass does not own it)")
    targets.add_argument("--home", default="", help="treat this dir as the machine home "
                         "instead of the real one (aim a run at a fixture)")
    targets.add_argument("--json", action="store_true", help="machine-readable envelope")

    check = subs.add_parser("check", help="run every deterministic check over the targets")
    check.add_argument("--root", action="append", default=[],
                       help="a tree to walk for project skills; repeatable")
    check.add_argument("--no-personal", action="store_true",
                       help="leave ~/.claude out (the per-tree pass does not own it)")
    check.add_argument("--shipped", default="",
                       help="a shipped skills/ dir to compare descriptions against, so a local "
                            "copy of a marketplace skill is reported as an unmanaged twin")
    check.add_argument("--home", default="", help="treat this dir as the machine home "
                       "instead of the real one (aim a run at a fixture)")
    check.add_argument("--json", action="store_true", help="machine-readable envelope")
    return parser


def _tolerant_stdio():
    """Replace what the console encoding cannot carry instead of crashing on it: a Windows pipe
    is cp1252, and one CJK path would otherwise end the report with a traceback."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def main(argv=None):
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    _tolerant_stdio()
    try:
        return {"targets": cmd_targets, "check": cmd_check}[args.command](args)
    except Exception as exc:  # noqa: BLE001 - 1 means "findings"; a crash must never read as that
        print("error: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
