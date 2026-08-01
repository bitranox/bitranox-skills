#!/usr/bin/env python3
"""Audit shipped skills in a clean room, one reviewer per skill, in parallel.

Two mechanics this encodes, both of which are easy to get wrong and silent when you do:

- The isolation that matters is from the MEMORY STORE, not from the plugin. A reviewer running
  anywhere on a machine that has a curated store is handed matching entries by the recall hook, so
  it cannot tell whether the SKILL taught it something or the store did. Wall recall for the run
  (`cross_tree_search: false` with the room outside the tree) and restore it afterwards.
- The INSTALL UNIT is the plugin, not the skill directory. A skill legitimately points at sibling
  skills and at the plugin's own hooks; judging reachability against one skill directory reports
  every such reference as dangling.

Run with `--jobs` reviewers at a time; each writes `<room>/reports/<skill>.audit.txt`.

Pure standard library.
"""

import argparse
import concurrent.futures as cf
import shutil
import subprocess
import sys
from pathlib import Path

PROMPT = """You are auditing ONE Claude Code skill for defects: `skills/{name}/`.

Read `skills/{name}/SKILL.md` fully, and every supporting file it references.

WHAT SHIPS: this whole directory is the installed plugin. The reader who installs it gets every
skill under `skills/`, the hooks under `hooks/`, and nothing outside this directory. So a reference
to a sibling skill (`{prefix}:<name>`) or to a plugin hook IS reachable - verify it resolves to a
real path here rather than assuming either way. What is NOT reachable is anything outside this
directory: a source repo, a package's `docs/`, a path on the author's machine.

Judge only from what is here. Do not search the wider filesystem and do not rely on knowledge of
any repository this plugin came from.

Report defects in these classes, most severe first:

1. WRONG - a claim, command, flag, API signature or code sample that is incorrect, or that
   contradicts another part of the same skill. Verify it if you can: run the command, check the
   help, execute the snippet.
2. DANGLING - a reference that does not resolve: a sibling skill or hook path that is NOT in this
   directory, a bare script filename with no stated home, a `docs/x.md` or README that ships
   nowhere and is not a URL.
3. UNEXECUTABLE - an instruction a competent reader cannot carry out as written because a required
   value, path, order or precondition is missing.
4. STALE - a claim that reads as version-bound or time-bound and carries no version, date, or way
   to check it.

For EVERY finding, output exactly this shape, one per finding:

FINDING: <class> | <file> | <one-line claim>
QUOTE: <the exact offending line, copied verbatim from the file>
WHY: <what a reader does wrong because of it>

Copy the quote character for character. If you cannot produce a verbatim quote, you do not have a
finding - drop it. Before reporting a DANGLING finding, actually check the path exists or does not:
`ls skills/<name>/SKILL.md`, `ls hooks/<file>`. Do not report style, tone, formatting, or
"could be clearer" opinions, and do not report the absence of things a skill of this kind need not
have.

If the skill has no defects in these classes, output the single line: NO FINDINGS

Then end with a section headed "Skill gaps": what you could not turn into a concrete action, what
you had to guess, and anywhere the text was silent or said two different things.
"""


def build_prompt(name, prefix="bitranox"):
    """The reviewer contract for one skill. `prefix` is the plugin's skill namespace."""
    return PROMPT.format(name=name, prefix=prefix)


def skill_names(plugin_dir, only=()):
    """Every skill in `plugin_dir/skills` that ships a SKILL.md, sorted. `only` filters by name."""
    skills = Path(plugin_dir) / "skills"
    wanted = {s for s in only if s}
    if not skills.is_dir():
        return []
    return sorted(d.name for d in skills.iterdir()
                  if d.is_dir() and (d / "SKILL.md").is_file() and (not wanted or d.name in wanted))


def prepare_room(plugin_src, room_root, reuse=False):
    """Copy the plugin into `<room_root>/plugin` and make `<room_root>/reports`. Returns the copy.

    The room belongs OUTSIDE the knowledge tree: a reviewer whose cwd sits inside it also picks up
    the tree's CLAUDE.md cascade, which is a second contamination route on top of recall."""
    room_root = Path(room_root)
    room = room_root / "plugin"
    (room_root / "reports").mkdir(parents=True, exist_ok=True)
    if room.exists() and not reuse:
        shutil.rmtree(room)
    if not room.exists():
        shutil.copytree(Path(plugin_src), room,
                        ignore=shutil.ignore_patterns(".skillwriter", "__pycache__", "*.pyc"))
    return room


def count_findings(text):
    """How many findings a report claims. `NO FINDINGS` and an empty report both count 0."""
    return (text or "").count("FINDING:")


def _subprocess_runner(prompt, cwd, model, timeout):
    """Default reviewer: a headless `claude -p` whose cwd is the clean room."""
    try:
        proc = subprocess.run(["claude", "-p", "--model", model], cwd=str(cwd), input=prompt,
                              capture_output=True, text=True, timeout=timeout)
        return proc.stdout.strip() or ("(no stdout) " + proc.stderr.strip()[:400])
    except subprocess.TimeoutExpired:
        return "(TIMEOUT after %ss)" % timeout


def audit_one(name, room, reports_dir, model="sonnet", timeout=900, prefix="bitranox",
              runner=_subprocess_runner):
    """Review one skill and write its report. `runner` is the injectable reviewer seam."""
    out = runner(build_prompt(name, prefix), room, model, timeout)
    path = Path(reports_dir) / ("%s.audit.txt" % name)
    path.write_text(out, encoding="utf-8")
    return name, count_findings(out)


def audit_all(plugin_src, room_root, model="sonnet", jobs=6, timeout=900, only=(),
              prefix="bitranox", reuse=False, runner=_subprocess_runner, log=print):
    """Audit every selected skill. Returns {skill: finding_count}."""
    room = prepare_room(plugin_src, room_root, reuse=reuse)
    reports = Path(room_root) / "reports"
    names = skill_names(room, only)
    log("auditing %d skill(s) in %s with %d job(s)" % (len(names), room, jobs))
    results = {}
    with cf.ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        futs = {ex.submit(audit_one, n, room, reports, model, timeout, prefix, runner): n
                for n in names}
        for fut in cf.as_completed(futs):
            name, n = fut.result()
            results[name] = n
            log("%-42s %s" % (name, "clean" if not n else "%d finding(s)" % n))
    log("DONE: %d finding(s) across %d skill(s)" % (sum(results.values()), len(names)))
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description="Audit shipped skills in a clean room.")
    ap.add_argument("--plugin", required=True, help="the plugin dir to audit (holds skills/, hooks/)")
    ap.add_argument("--room", required=True, help="clean-room root, OUTSIDE the knowledge tree")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--only", default="", help="comma-separated skill names, else all")
    ap.add_argument("--prefix", default="bitranox", help="the plugin's skill namespace")
    ap.add_argument("--reuse-room", action="store_true", help="keep an existing plugin copy")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    audit_all(args.plugin, args.room, args.model, args.jobs, args.timeout,
              tuple(s.strip() for s in args.only.split(",")), args.prefix, args.reuse_room)
    return 0


if __name__ == "__main__":
    sys.exit(main())
