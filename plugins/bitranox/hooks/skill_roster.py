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

Names from this plugin are keyed bare (`files-edit-xml`), as the keyword router, the shadow log
and every adjudication name them; any other skill keeps its full name, because bare names collide
across plugins (`code-review` is both a built-in and `code-review:code-review`).

Pure standard library; every failure degrades to the next source, never raises.
"""
import json
from pathlib import Path

import classifier
import self_improve_signals as sig

OWN_PREFIX = "bitranox:"
SOURCE_TRANSCRIPT = "transcript"
SOURCE_CACHE = "cache"
SOURCE_SHIPPED = "shipped"
_MARKER = b'"skill_listing"'


def option_name(name):
    """The key a skill is offered under: this plugin's skills bare, every other one in full."""
    return name[len(OWN_PREFIX):] if name.startswith(OWN_PREFIX) else name


def parse_listing(content, names):
    """{option name: description} from a listing's `content`, one entry per listed name.

    Each entry opens with a line `- <name>: <description>` and may run over further lines. Only a
    line naming a LISTED skill opens an entry, so a description line that happens to start with
    "- " stays part of the description it belongs to.
    """
    openers = {"- %s: " % n: n for n in names}
    out, current, parts = {}, None, []

    def close():
        text = " ".join(p.strip() for p in parts if p.strip())
        if current is not None and text:
            out[option_name(current)] = text

    for line in (content or "").splitlines():
        opener = next((o for o in openers if line.startswith(o)), None)
        if opener is None:
            parts.append(line)
            continue
        close()
        current, parts = openers[opener], [line[len(opener):]]
    close()
    return out


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


def listing_from_transcript(transcript_path):
    """The session's installed skills: the latest full listing plus the deltas after it.

    None when there is no full listing, including when there are only deltas - one added skill
    is not the installed set, and offering it alone would hide every other skill.
    """
    roster = None
    for att in _listings(transcript_path) if transcript_path else ():
        parsed = parse_listing(att.get("content"), att.get("names") or [])
        if att.get("isInitial") is False:
            if roster is not None:
                roster.update(parsed)
        else:
            roster = parsed
    return roster or None


def _cache_file(cwd):
    return sig._audit_dir() / ("%s.skill-listing.json" % sig.proj_key(cwd))  # noqa: SLF001


def _write_cache(cwd, skills):
    try:
        path = _cache_file(cwd)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(skills, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


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
    skills = listing_from_transcript(transcript_path)
    if skills:
        if skills != _read_cache(cwd):
            _write_cache(cwd, skills)
        return skills, SOURCE_TRANSCRIPT
    skills = _read_cache(cwd)
    if skills:
        return skills, SOURCE_CACHE
    return classifier.load_skill_descriptions(), SOURCE_SHIPPED
