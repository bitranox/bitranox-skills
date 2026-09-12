"""A hook's registration, stated in prose, must never be narrower than what hooks.json registers.

A hook's first docstring line names its event and matcher, `PreToolUse(Bash|PowerShell)`, and skills
cite hooks the same way, `(PreToolUse on Bash)`. Measured on 2026-09-01: warn-inline-powershell said
Bash while hooks.json registered Bash|PowerShell and the hook fired under both. Prose NARROWER than
the registration is the direction that invites a maintainer to "fix" the registration back to match
it, so that is the direction these tests forbid; a docstring naming more tools than are registered
is left alone. Each scan also has a check that it read every claim of its kind, because a spelling
the pattern cannot read drops out of the comparison without failing it.
"""

import ast
import json
import re
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = HOOKS_DIR.parent / "skills"
TOOLS = ("Bash", "PowerShell", "Edit", "Write", "MultiEdit", "NotebookEdit", "Task", "Agent", "Skill", "Read")
FORM = re.compile(r"^(\w+)\s*\(([^)]*)\)")
SKILL_CITATION = re.compile(r"`([a-z0-9-]+)`(?:\s+hook)?\s*\(PreToolUse on ([^)]*)\)", re.S)


def _registered():
    """{(script stem, event): set of tools} from hooks.json, merging a hook's matcher groups."""
    hooks = json.loads((HOOKS_DIR / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    found = {}
    for event, groups in hooks.items():
        for group in groups:
            tools = set(filter(None, (group.get("matcher") or "").split("|")))
            for handler in group["hooks"]:
                script = handler["command"].rsplit("/", 1)[-1].rstrip('"')
                found.setdefault((Path(script).stem, event), set()).update(tools)
    return found


def _first_docstring_line(stem):
    """The module docstring's first line, wherever it sits (with or without a shebang above it)."""
    doc = ast.get_docstring(ast.parse((HOOKS_DIR / (stem + ".py")).read_text(encoding="utf-8"))) or ""
    return doc.splitlines()[0] if doc else ""


def _docstring_claims():
    """[(stem, event, registered tools, docstring tools)] for every hook whose first line uses the form."""
    claims = []
    for (stem, event), tools in sorted(_registered().items()):
        match = FORM.match(_first_docstring_line(stem))
        if match and match.group(1) == event:
            claims.append((stem, event, tools, {t.strip() for t in match.group(2).split("|")}))
    return claims


def _skill_markdown():
    return [md for md in sorted(SKILLS_DIR.glob("**/*.md")) if ".skillwriter" not in md.parts]


def _skill_citations():
    """[(skill file, hook, cited tools)] for every `hook` (PreToolUse on X) citation in skill markdown."""
    cites = []
    for md in _skill_markdown():
        for hook, named in SKILL_CITATION.findall(md.read_text(encoding="utf-8")):
            cited = {t for t in TOOLS if re.search(r"\b%s\b" % t, named)}
            cites.append((str(md.relative_to(SKILLS_DIR)), hook, cited))
    return cites


def test_the_docstring_scan_reads_every_hook_that_states_its_event():
    unread = [(stem, line[:60]) for (stem, event) in _registered()
              for line in [_first_docstring_line(stem)]
              if line.startswith(event) and "(" in line.split(":")[0] and not FORM.match(line)]
    assert not unread, unread
    stems = {stem for stem, *_ in _docstring_claims()}
    assert {"warn-inline-powershell", "block-pgrep-self-match", "skill-edit-guard"} <= stems


@pytest.mark.parametrize("stem,event,registered,documented", _docstring_claims(),
                         ids=lambda v: v if isinstance(v, str) else "")
def test_a_hook_docstring_names_every_tool_it_is_registered_for(stem, event, registered, documented):
    missing = sorted(registered - documented)
    assert not missing, "%s.py says %s(%s) but hooks.json also registers it for %s" % (
        stem, event, "|".join(sorted(documented)), missing)


def test_the_skill_citation_scan_reads_every_citation():
    total = sum(len(re.findall(r"\(PreToolUse\s+on\b", md.read_text(encoding="utf-8"))) for md in _skill_markdown())
    cites = _skill_citations()
    assert total == len(cites), "%d '(PreToolUse on' citations, %d read" % (total, len(cites))
    assert ("compuse-ssh/SKILL.md", "warn-inline-powershell") in {(s, h) for s, h, _ in cites}


@pytest.mark.parametrize("skill,hook,cited", _skill_citations(), ids=lambda v: v if isinstance(v, str) else "")
def test_a_skill_citation_names_every_tool_the_hook_is_registered_for(skill, hook, cited):
    registered = _registered().get((hook, "PreToolUse"))
    if registered is None:
        pytest.skip("%s is not a PreToolUse hook of this plugin" % hook)
    missing = sorted(registered - cited)
    assert not missing, "skills/%s cites %s as PreToolUse on %s; hooks.json also registers %s" % (
        skill, hook, "|".join(sorted(cited)), missing)
