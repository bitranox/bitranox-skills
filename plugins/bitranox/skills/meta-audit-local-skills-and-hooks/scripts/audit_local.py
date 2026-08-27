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


def gather(roots, home=None, personal=True):
    """(selected, skipped) for `roots`, where each skipped entry carries the reason it was cut."""
    candidates = hc.discover_candidates(roots, home=home, personal=personal)
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
    for owned in hc.discover_shipped(roots, home=home):
        skipped.append({"path": str(owned),
                        "reason": hc.skip_reason(owned, home=home) or "shipped by a plugin"})
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
    selected, skipped = gather(roots, home=_home(args), personal=not args.no_personal)
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
    registered = hc.registered_paths(settings, home=home)
    for path in settings:
        for event, command, missing in hc.registration_problems(path, home=home):
            found.append(("registration", "%s (%s): command names %s, which does not exist - the "
                                          "hook silently never fires" % (path.name, event, missing)))
            del command
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


def cmd_check(args, out=None, err=None):
    """Run every deterministic check over the selected targets and return an exit code."""
    out = out or sys.stdout
    err = err or sys.stderr
    home = _home(args) or Path.home()
    selected, skipped = gather([Path(r) for r in args.root], home=_home(args),
                                personal=not args.no_personal)
    shipped = hc.shipped_descriptions(Path(args.shipped)) if args.shipped else {}
    results, total = [], 0
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
        # --shipped names a skills/ dir; its PARENT is the plugin root, which also holds hooks/.
        findings = check_personal(home, shipped_root=Path(args.shipped).parent if args.shipped else None)
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


def main(argv=None):
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return {"targets": cmd_targets, "check": cmd_check}[args.command](args)
    except OSError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
