"""The skill router's option list: the skills this session actually has installed.

Globbing this plugin's own `skills/*/SKILL.md` offers only bitranox skills, so a skill from another
plugin, a project skill or a Claude Code built-in can never be proposed however well it fits.
Measured on the two blind-adjudicated replays: 4 of the 6 skills no arm ever proposed were of that
kind (typesafe-ai, soundtouch-decloud, provmm-build, update-config).

The session's real listing is in its transcript as a `skill_listing` attachment: a full record
(`isInitial: true`) after startup and after every plugin reload, and a delta (`isInitial: false`)
carrying only the skills added since. On the FIRST prompt it is usually not on disk yet - in 50
of 51 sessions it was written after the first typed prompt - so a listing read from the
transcript is cached per project and answers the next session's first prompt. With neither, the
shipped glob answers, which is what the router offered before.

When the listing would exceed its budget the harness drops descriptions and leaves a bare
`- <name>` line; a third of real listings carry such lines. A trimmed skill is still installed, so
it is still offered: with the text its own SKILL.md or command file gives it (the front matter's
`description:`, else the body's first paragraph, as the harness reads it) when that file can be
found in this plugin's skills dir, the installed plugin's directory, or the project's or the
user's `.claude/`; else under its name alone - a Claude Code built-in has no file to read.

Names from this plugin are keyed bare (`files-edit-xml`), as the keyword router, the shadow log
and every adjudication name them; any other skill keeps its full name, because bare names collide
across plugins (`code-review` is both a built-in and `code-review:code-review`). When a skill of
the same bare name is also listed, this plugin's keeps its prefix so neither hides the other.

Pure standard library; every failure degrades to the next source, never raises.
"""
import contextlib
import json
import os
import tempfile
from pathlib import Path

import classifier
import self_improve_signals as sig
import skill_frontmatter

OWN_PREFIX = "bitranox:"
SOURCE_TRANSCRIPT = "transcript"
SOURCE_CACHE = "cache"
SOURCE_SHIPPED = "shipped"
_MARKER = b'"skill_listing"'
_PLUGIN_ROOT = Path(__file__).resolve().parent.parent


# ---- one listing's text --------------------------------------------------------------------------

def _opener(line, names):
    """(name, first description text) when `line` opens a listed skill's entry, else None.

    An entry opens with `- <name>: <description>`, or with a bare `- <name>` when the harness
    trimmed the description. Only a LISTED name opens one, so a description line that happens to
    start with "- " stays part of the description it belongs to. Names never contain ": ", so the
    split cannot cut `- code-review:code-review: ...` at the plugin separator.
    """
    if not line.startswith("- "):
        return None
    head, sep, text = line[2:].partition(": ")
    if sep and head in names:
        return head, text
    bare = line[2:].rstrip()
    bare = bare[:-1] if bare.endswith(":") else bare
    return (bare, "") if bare in names else None


def _raw_listing(content, names):
    """{full listed name: description, "" where the listing carries none}, in listing order.

    Every listed name gets an entry, including one with no line at all: `names` is the installed
    set, and the text is only how it is described.
    """
    names = [n for n in names if isinstance(n, str) and n]
    nameset = set(names)
    out, current, parts = {}, None, []

    def close():
        if current is None:
            return
        text = " ".join(p.strip() for p in parts if p.strip())
        if text or current not in out:
            out[current] = text

    for line in (content or "").splitlines():
        opened = _opener(line, nameset)
        if opened is None:
            parts.append(line)
            continue
        close()
        current, parts = opened[0], [opened[1]]
    close()
    for name in names:
        out.setdefault(name, "")
    return out


# ---- a trimmed skill's own file ------------------------------------------------------------------

def _first_paragraph(body):
    """The first paragraph of markdown prose, headings skipped, joined into one line."""
    para = []
    for line in [*body, ""]:
        if line.strip():
            if not line.lstrip().startswith("#"):
                para.append(line.strip())
        elif para:
            return " ".join(para)
    return ""


def _file_description(path):
    """How the harness describes a SKILL.md or command file: its front matter's `description:`
    (read by `skill_frontmatter`, the reader the gate and the builders share, with its quotes or
    block header decoded), else the first paragraph of its body. "" for a missing file."""
    text = skill_frontmatter.read_text(path)
    if text is None:
        return ""
    block, body = skill_frontmatter.split_frontmatter(text)
    desc = skill_frontmatter.scalar_text(skill_frontmatter.field(block, "description"))
    return desc or _first_paragraph(body.splitlines())


def _installed_plugin_roots():
    """{plugin name: [install dirs]} from Claude Code's installed_plugins.json, {} when
    it cannot be read."""
    path = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    try:
        plugins = json.loads(path.read_text(encoding="utf-8")).get("plugins")
    except (OSError, ValueError, AttributeError):
        return {}
    roots = {}
    for key, entries in (plugins.items() if isinstance(plugins, dict) else ()):
        name = str(key).split("@", 1)[0]
        for entry in entries if isinstance(entries, list) else ():
            install = entry.get("installPath") if isinstance(entry, dict) else None
            if isinstance(install, str) and install:
                roots.setdefault(name, []).append(Path(install))
    return roots


def _claude_dirs(cwd):
    """The `.claude/` dirs whose skills a session sees: the cwd's and its ancestors',
    then HOME's."""
    dirs = []
    if cwd:
        start = Path(cwd).absolute()
        dirs += [d / ".claude" for d in (start, *start.parents)]
    home = Path.home() / ".claude"
    return dirs + ([home] if home not in dirs else [])


def _candidates(roots, skill):
    """The files that can define `skill` under each root: a skill dir, or a (namespaced) command."""
    parts = skill.split(":")
    for root in roots:
        yield root / "skills" / skill / "SKILL.md"
        yield root.joinpath("commands", *parts[:-1], parts[-1] + ".md")


class _Describer:
    """A trimmed skill's text: its own file's description, else its name. Built once per roster, so
    installed_plugins.json is read at most once however many lines were trimmed."""

    def __init__(self, cwd=None):
        self.cwd = cwd
        self._plugins = None

    def _roots(self, plugin):
        if plugin + ":" == OWN_PREFIX:
            return [_PLUGIN_ROOT]
        if self._plugins is None:
            self._plugins = _installed_plugin_roots()
        return self._plugins.get(plugin, [])

    def __call__(self, name):
        plugin, sep, skill = name.partition(":")
        roots = self._roots(plugin) if sep else _claude_dirs(self.cwd)
        for candidate in _candidates(roots, skill if sep else name):
            desc = _file_description(candidate)
            if desc:
                return desc
        return name


# ---- the roster ----------------------------------------------------------------------------------

def _keyed(raw, describe):
    """{option name: description}: this plugin's skills bare unless that bare name is listed too,
    and every empty description filled in by `describe`."""
    listed = set(raw)
    out = {}
    for name, desc in raw.items():
        key = option_name(name)
        if key != name and key in listed:
            key = name
        out[key] = desc or describe(name)
    return out


def option_name(name):
    """The key a skill is offered under: this plugin's skills bare, every other one in full."""
    return name[len(OWN_PREFIX):] if name.startswith(OWN_PREFIX) else name


def parse_listing(content, names, cwd=None):
    """{option name: description} from a listing's `content`, one entry per listed name.

    Each entry opens with a line `- <name>: <description>` and may run over further lines, or is a
    bare `- <name>` the harness trimmed. A trimmed name, or a listed name with no line at all,
    takes its own file's description (a project skill is looked up from `cwd`), else its name.
    """
    return _keyed(_raw_listing(content, names), _Describer(cwd))


def _listings(transcript_path):
    """Every `skill_listing` attachment in the transcript, in order. A substring test skips the
    JSON decode of every other line, which keeps a 12 MB transcript at about 10 ms."""
    try:
        fh = Path(transcript_path).open("rb")
    except (OSError, TypeError, ValueError):
        return
    with fh:
        for line in fh:
            if _MARKER not in line:
                continue
            try:
                att = json.loads(line).get("attachment")
            except (ValueError, AttributeError):
                continue
            if isinstance(att, dict) and att.get("type") == "skill_listing":
                yield att


def listing_from_transcript(transcript_path, cwd=None):
    """The session's installed skills: the latest full listing plus the deltas after it.

    None when there is no full listing, including when there are only deltas - one added skill
    is not the installed set, and offering it alone would hide every other skill. Names are keyed
    and trimmed descriptions resolved over the MERGED set, so a delta's bare name still sees this
    plugin's skill of the same name from the full listing.
    """
    raw = None
    for att in _listings(transcript_path) if transcript_path else ():
        parsed = _raw_listing(att.get("content"), att.get("names") or [])
        if att.get("isInitial") is False:
            if raw is not None:
                raw.update({k: v for k, v in parsed.items() if v or k not in raw})
        else:
            raw = parsed
    return _keyed(raw, _Describer(cwd)) if raw else None


def _cache_file(cwd):
    return sig._audit_dir() / ("%s.skill-listing.json" % sig.proj_key(cwd))  # noqa: SLF001


def _write_cache(cwd, skills):
    """Replace the project's cache atomically, never raising. The temp file is named per write:
    every session of a project writes this one cache, and a shared fixed temp name let one
    session rename another's half-written file into place."""
    tmp = None
    try:
        path = _cache_file(cwd)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(skills, ensure_ascii=False))
        os.replace(tmp, path)
        tmp = None
    except OSError:
        pass
    finally:
        if tmp is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp)


def _read_cache(cwd):
    try:
        data = json.loads(_cache_file(cwd).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(data, dict) and data and all(isinstance(v, str) for v in data.values()):
        return data
    return None


def installed_skills(transcript_path, cwd):
    """(roster, source): the transcript's listing, else this project's cached one, else the
    shipped skills. `source` is recorded beside every shadow verdict so rows judged against
    different rosters never pool in one report."""
    skills = listing_from_transcript(transcript_path, cwd)
    if skills:
        if skills != _read_cache(cwd):
            _write_cache(cwd, skills)
        return skills, SOURCE_TRANSCRIPT
    skills = _read_cache(cwd)
    if skills:
        return skills, SOURCE_CACHE
    return classifier.load_skill_descriptions(), SOURCE_SHIPPED
