"""The Jev shadow sites: their question files, and the item builders for the store-based ones.

A site is one skill step where the agent makes the same bounded judgment over many items. Each has
a file `jev_sites/<site>.json` holding `{"site", "version", "questions", "state_fields"}`: the
jev-judge question objects, and the exact named fields every item's state carries. A question
refers to a field only as a backticked name, and every backticked name is a state field.

Five sites build their items here from a source the skill step already has: the curated memory
store under an anchor, or a `guard_replay.py --firings` file. The other five are agent-built: the
step's agent writes the items itself, and `jev_shadow.py run` checks their fields against the site
file. Standard library only; the store readers come from hooks/ and meta-self-improve/.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

_HERE = Path(__file__).resolve().parent
_HOOKS = _HERE.parent.parent / "hooks"
for _d in (str(_HOOKS), str(_HERE)):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import memory_engine as ME

import reconcile_memory_index as R

__all__ = [
    "AGENT_BUILT",
    "BUILDERS",
    "SITES_DIR",
    "BuildRequest",
    "ShadowItem",
    "Site",
    "SiteError",
    "build_items",
    "load_site",
    "site_names",
]

SITES_DIR = _HERE / "jev_sites"

# Sites whose items the step's agent writes itself: there is nothing on disk to build them from.
AGENT_BUILT = frozenset(
    {
        "quality-polarity",
        "quality-param-hit",
        "data-arch-dict",
        "consolidate-cause",
        "collect-relevance",
    }
)


class SiteError(ValueError):
    """A usage problem with a site: unknown, malformed, or asked for a source it does not take."""


@dataclass(frozen=True)
class Site:
    """One site file, loaded.

    Attributes:
        name: The site id, equal to the file's stem.
        version: The site file's own version; bump it when a question changes.
        questions: The jev-judge question objects, sent as they stand.
        state_fields: The named fields every item's state carries, in order.
        questions_sha: A short hash of the questions, so a log row names the exact wording.
    """

    name: str
    version: int
    questions: list[dict[str, Any]]
    state_fields: tuple[str, ...]
    questions_sha: str

    def types(self) -> dict[str, str]:
        """Question id -> type (noul, choice or score)."""
        return {str(q["id"]): str(q["type"]) for q in self.questions}

    def question(self, qid: str) -> dict[str, Any]:
        """The question object with id `qid`."""
        return next(q for q in self.questions if q["id"] == qid)


class ShadowItem(NamedTuple):
    """One item to judge: an id unique in its batch and the named fields Jev reads."""

    id: str
    state: dict[str, str]


@dataclass(frozen=True)
class BuildRequest:
    """What `items` was given: a memory anchor, or a firings file plus the guard's hazard."""

    anchor: Path | None = None
    firings: Path | None = None
    hazard: str | None = None


def site_names() -> list[str]:
    """Every site with a file in SITES_DIR, sorted."""
    return sorted(p.stem for p in SITES_DIR.glob("*.json"))


def load_site(name: str) -> Site:
    """Load `jev_sites/<name>.json`.

    Args:
        name: The site id.

    Returns:
        The loaded site.

    Raises:
        SiteError: No such site, or its file is not the documented shape.
    """
    path = SITES_DIR / (f"{name}.json")
    if name not in site_names():
        raise SiteError(
            "unknown site {!r} (known: {})".format(name, ", ".join(site_names()))
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        questions, fields = list(raw["questions"]), tuple(raw["state_fields"])
        version = int(raw["version"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SiteError(
            f"site file {path.name} is unreadable or malformed: {exc}"
        ) from exc
    canonical = json.dumps(questions, sort_keys=True, separators=(",", ":"))
    sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return Site(
        name=name,
        version=version,
        questions=questions,
        state_fields=fields,
        questions_sha=sha,
    )


# ---- the store-based builders -------------------------------------------------------------


class _Fact(NamedTuple):
    level: str
    slug: str
    hook: str
    body: str


def _body_text(body: str) -> str:
    """A stored body without its frontmatter frame: Jev reads the note, not its metadata."""
    _meta, text = R.parse_frontmatter(body or "")
    return text.strip()


def _facts(anchor: Path) -> tuple[list[_Fact], dict[str, str]]:
    """Every fact under `anchor`, plus each level's scope descriptor by level path."""
    facts: list[_Fact] = []
    scopes: dict[str, str] = {}
    for level in ME.curated_levels_under(str(anchor)):
        scope, entries, bodies = ME.read_store(level)
        scopes[level] = scope or ""
        facts.extend(
            _Fact(level, e.slug, e.hook, _body_text(bodies.get(e.slug) or ""))
            for e in entries
        )
    return facts, scopes


def _require_anchor(req: BuildRequest) -> Path:
    if req.anchor is None:
        raise SiteError(
            "this site builds its items from a memory store: pass --anchor DIR"
        )
    if not req.anchor.is_dir():
        raise SiteError(f"--anchor {req.anchor} is not a directory")
    return req.anchor.resolve()


def _hook_body(req: BuildRequest) -> list[ShadowItem]:
    """dream-prune and dream-firing: one item per fact, `{hook, body}`, id = slug."""
    facts, _scopes = _facts(_require_anchor(req))
    return [ShadowItem(f.slug, {"hook": f.hook, "body": f.body}) for f in facts]


def _level_label(anchor: Path, level: str) -> str:
    rel = Path(level).resolve().relative_to(anchor).as_posix()
    return rel or "."


def _candidate_levels(level: str, levels: Iterable[str]) -> list[str]:
    """The fact's own level, its curated ancestors, and its curated descendants (up AND down)."""
    here = Path(level).resolve()
    out = []
    for other in levels:
        o = Path(other).resolve()
        if o == here or o in here.parents or here in o.parents:
            out.append(other)
    return out


def _placement(req: BuildRequest) -> list[ShadowItem]:
    """dream-placement: one item per (fact, candidate level), id `slug|<level relative to anchor>`."""
    anchor = _require_anchor(req)
    facts, scopes = _facts(anchor)
    items = []
    for f in facts:
        for lvl in _candidate_levels(f.level, scopes):
            state = {"hook": f.hook, "body": f.body, "level_scope": scopes[lvl]}
            items.append(ShadowItem(f"{f.slug}|{_level_label(anchor, lvl)}", state))
    return items


def _misplaced(req: BuildRequest) -> list[ShadowItem]:
    """crosstree-misplaced: one item per `find_misplaced` candidate, id = slug."""
    anchor = _require_anchor(req)
    facts, scopes = _facts(anchor)
    by_key = {(str(Path(f.level).resolve()), f.slug): f for f in facts}
    items = []
    for cand in R.find_misplaced(str(anchor)):
        level = str(Path(cand["level"]).resolve())
        f = by_key.get((level, cand["slug"]))
        if f is None:
            continue
        state = {
            "hook": f.hook,
            "body": f.body,
            "level_scope": scopes.get(f.level, ""),
            "cited_paths": "\n".join(cand["paths"]),
        }
        items.append(ShadowItem(cand["slug"], state))
    return items


def _read_firings(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]
    except (OSError, ValueError) as exc:
        raise SiteError(f"cannot read --firings {path}: {exc}") from exc


def _guard_firings(req: BuildRequest) -> list[ShadowItem]:
    """guard-firing: one item per firing, id = its tool_use id, the hazard text on every item."""
    if req.firings is None or not req.hazard:
        raise SiteError(
            "guard-firing builds from guard_replay output: pass --firings F and "
            "--hazard TEXT (what the guard warns about)"
        )
    items = []
    for rec in _read_firings(req.firings):
        state = {
            "hazard": req.hazard,
            "command": str(rec.get("command") or ""),
            "error": str(rec.get("error") or ""),
        }
        items.append(ShadowItem(str(rec.get("id")), state))
    return items


BUILDERS: dict[str, Callable[[BuildRequest], list[ShadowItem]]] = {
    "guard-firing": _guard_firings,
    "dream-prune": _hook_body,
    "dream-firing": _hook_body,
    "dream-placement": _placement,
    "crosstree-misplaced": _misplaced,
}


def build_items(site: Site, req: BuildRequest) -> list[ShadowItem]:
    """Build the items for a store-based site.

    Args:
        site: The loaded site.
        req: The sources the caller passed.

    Returns:
        The items, in source order.

    Raises:
        SiteError: The site is agent-built, or a source it needs was not passed or is unreadable.
    """
    builder = BUILDERS.get(site.name)
    if builder is None:
        raise SiteError(
            "{} is agent-built: write items.jsonl yourself, one "
            '{{"id": ..., "state": {{...}}}} per line, with exactly the state fields {}'.format(
                site.name, ", ".join(site.state_fields)
            )
        )
    try:
        return builder(req)
    except ME.TreeWalkError as exc:
        raise SiteError(f"cannot read the memory store: {exc}") from exc
