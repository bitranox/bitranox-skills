#!/usr/bin/env python3
"""SessionStart hook: keep `skillListingBudgetFraction` large enough for the installed catalogue.

Claude Code injects the available-skills listing under a character budget of
`context_tokens * chars_per_token * skillListingBudgetFraction` (the fraction defaults to 0.01).
When the listing exceeds it, every non-bundled entry drops to its bare name and the harness then
restores descriptions greedily in descending `usageCount * 0.5^(days_since_last_use / 7)` order.
A skill that has never been invoked scores 0, so it is first to lose the very text the router
matches on: the skill nobody found stays unfindable. Installing skills is exactly what pushes the
listing over, so the default silently degrades as a catalogue grows.

This hook sizes the fraction to the catalogue actually installed. The budget is a CEILING and not
a reservation - the listing only ever contains the entries that exist - so raising it costs nothing
when the catalogue is small, and the fraction is only ever raised, never lowered.

Only the USER-level fraction (`<config>/settings.json`) is managed. A project can set its own in
`<project>/.claude/settings.json` or `settings.local.json`; a listing produced in such a project
says nothing about the user-level value, so it is skipped rather than used as a correction.

Emits the Claude Code SessionStart contract on stdout. Pure standard library. Every failure path
emits nothing and exits 0, so a broken hook never blocks a session.
"""

import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

import skill_frontmatter

# The listing reader is the skill router's, and it pulls in the router's classifier and signal
# modules. An import error there may cost the correction it feeds, never the disk estimate.
try:
    import skill_roster
except Exception:  # noqa: BLE001 - any failure to import it means "no listing to read"
    skill_roster = None

# The harness truncates a single description at this many characters (skillListingMaxDescChars).
MAX_DESC_CHARS = 1536

# Bundled (Anthropic) skills ship inside the CLI binary, not on disk, so they cannot be measured
# here - but they occupy the same budget and are exempt from the rationing. Measured at 19 entries
# and ~8.3k characters; rounded well up because they grow between CLI releases and over-providing
# a ceiling is free.
BUNDLED_ALLOWANCE = 12_000

# budget = context_tokens * chars_per_token * fraction. chars_per_token is read from the harness
# rather than guessed: it returns 4 for a known set of models and 3 for every other, so 3 is the
# floor across all of them. The fraction is therefore sized against the smallest context worth
# serving (a 200k-token model) at that floor. A larger context gets a ceiling far above its
# listing, which costs nothing.
CHARS_PER_TOKEN_FLOOR = 3
DENOMINATOR_FLOOR = 200_000 * CHARS_PER_TOKEN_FLOOR

SAFETY = 1.25
FRACTION_CAP = 0.5  # refuse to run away if a catalogue is pathologically large
HARNESS_DEFAULT_FRACTION = 0.01

def config_dir():
    """Return the Claude configuration directory (CLAUDE_CONFIG_DIR wins, else ~/.claude)."""
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(override) if override else Path.home() / ".claude"


def read_description(skill_md):
    """Return a SKILL.md's frontmatter description as one line, or None if it has none.

    The shared reader, so a BOM or CRLF file is measured rather than counted as empty."""
    return skill_frontmatter.description(skill_md)


def _skills_in(directory, prefix):
    """Yield (qualified_name, description) for every SKILL.md directly under `directory`."""
    try:
        children = sorted(directory.iterdir())
    except OSError:
        return
    for child in children:
        skill_md = child / "SKILL.md"
        if not skill_md.is_file():
            continue
        yield f"{prefix}{child.name}", read_description(skill_md) or ""


def installed_skills(config):
    """Return (qualified_name, description) for every skill installed on disk.

    Covers the plugin cache (each plugin's `skills/`) and the personal `~/.claude/skills`.
    Bundled skills live in the CLI binary and are accounted for by BUNDLED_ALLOWANCE instead.
    """
    entries = {}
    manifest = config / "plugins" / "installed_plugins.json"
    try:
        plugins = json.loads(manifest.read_text(encoding="utf-8")).get("plugins", {})
    except (OSError, ValueError, AttributeError):
        plugins = {}
    if not isinstance(plugins, dict):
        plugins = {}  # a malformed manifest must not stop the personal skills below being measured
    for key, installs in plugins.items():
        name = str(key).split("@")[0]
        for install in installs if isinstance(installs, list) else []:
            path = (install or {}).get("installPath")
            if not path:
                continue
            for qualified, desc in _skills_in(Path(path) / "skills", f"{name}:"):
                entries[qualified] = desc
    for qualified, desc in _skills_in(config / "skills", ""):
        entries[qualified] = desc
    return sorted(entries.items())


def listing_demand(entries, bundled_allowance=BUNDLED_ALLOWANCE):
    """Return the character cost of a listing carrying every entry's full description.

    Mirrors the harness line format `- <name>: <description>` joined by newlines, with each
    description truncated at MAX_DESC_CHARS the way the harness truncates it.
    """
    if not entries:
        return bundled_allowance
    total = sum(len(name) + 2 + min(len(desc), MAX_DESC_CHARS) + (2 if desc else 0) for name, desc in entries)
    return total + (len(entries) - 1) + bundled_allowance


def required_fraction(demand, floor=DENOMINATOR_FLOOR, safety=SAFETY, cap=FRACTION_CAP):
    """Return the smallest 2-decimal fraction whose budget covers `demand`, bounded by `cap`."""
    if demand <= 0:
        return 0.0
    wanted = (demand * safety) / floor
    return min(cap, math.ceil(wanted * 100) / 100)


def _fraction(value):
    """`value` when it is a finite number, else the harness default.

    Python's json reads NaN and Infinity, and a bool is an int to isinstance; none of them is a
    fraction the harness could apply, and NaN would make every comparison below answer False.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return HARNESS_DEFAULT_FRACTION
    return value


def stored_fraction(settings_path):
    """Return the configured fraction, or the harness default when it is unset or unreadable."""
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return HARNESS_DEFAULT_FRACTION
    if not isinstance(settings, dict):
        return HARNESS_DEFAULT_FRACTION
    return _fraction(settings.get("skillListingBudgetFraction"))


def raise_fraction(settings_path, wanted):
    """Raise `skillListingBudgetFraction` to `wanted` if it is currently lower.

    Returns (old, new) when the file was rewritten, else None. The settings file is round-tripped
    through json so no unrelated key is disturbed, and it is left untouched if it does not parse.
    """
    try:
        raw = settings_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        settings = json.loads(raw)
    except ValueError:
        return None  # a settings file we cannot parse is one we must not rewrite
    if not isinstance(settings, dict):
        return None
    current = _fraction(settings.get("skillListingBudgetFraction"))
    if wanted <= current:
        return None
    settings["skillListingBudgetFraction"] = wanted
    try:
        settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError:
        return None
    return current, wanted


def _epoch(stamp):
    """Return a transcript record's ISO-8601 `timestamp` as epoch seconds, or None if unreadable."""
    if not isinstance(stamp, str):
        return None
    try:
        # fromisoformat accepts a trailing Z only from Python 3.11
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    except (ValueError, OverflowError, OSError):
        return None


def _bare_entries(content, names):
    """The listed skills that arrived as a bare `- <name>`, with no description.

    With the listing's `names` (the installed set, which every measured listing carries) the
    router's own names-aware parser decides, so a description that continues on a line starting
    "- " stays part of its entry. Without them, a `- ` line with no ": " is the best reading left.
    """
    if isinstance(names, list) and names:
        return [name for name, text in skill_roster.raw_listing(content, names).items() if not text]
    return [ln[2:].strip() for ln in content.splitlines() if ln.startswith("- ") and ": " not in ln]


def _last_full_listing(transcript):
    """Return the transcript's LAST full listing as a summary dict, or None when it has none.

    A later full listing (after /reload-plugins) supersedes an earlier one. A delta
    (`isInitial: false`) carries only the skills added since, so it is not the listing the budget
    packed and never stands in for one.
    """
    if skill_roster is None:
        return None
    found = None
    for record, attachment in skill_roster.listing_records(transcript):
        if attachment.get("isInitial") is False:
            continue
        content = attachment.get("content")
        if isinstance(content, list):
            content = "\n".join(str(part) for part in content)
        if not isinstance(content, str) or not content:
            continue
        found = {
            "total": len(content),
            "bare": _bare_entries(content, attachment.get("names")),
            "timestamp": _epoch(record.get("timestamp")),
            "cwd": record.get("cwd"),
        }
    return found


def newest_listing(config, max_files=5):
    """Return the most recent injected listing, or None if none is readable.

    The result is {"total", "bare", "timestamp", "cwd"}: its length, the entries that arrived as a
    bare `- name`, when it was produced (epoch seconds, None if unreadable) and in which directory.
    The listing is the OUTCOME the estimate is trying to predict, so reading it back closes the
    loop: any bare entry is a description the router never saw. Only the newest `max_files`
    transcripts are opened; the first of them holding a full listing answers, with its last one.
    """
    try:
        files = sorted(config.glob("projects/*/*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    except OSError:
        return None
    for path in files[:max_files]:
        found = _last_full_listing(path)
        if found is not None:
            return found
    return None


def listing_is_current(listing, settings_path):
    """Whether `listing` was produced after settings.json last changed.

    A listing produced before the file's last write - this hook's own raise, or a hand edit - was
    packed under a value the file no longer holds, whatever the model. A listing whose timestamp
    cannot be read cannot be placed, so it is not trusted either.
    """
    produced = listing.get("timestamp")
    if produced is None:
        return False
    try:
        changed = settings_path.stat().st_mtime
    except OSError:
        return True  # no settings file: nothing was written after the listing
    return produced >= changed


def project_overrides_fraction(cwd, config):
    """Whether the project at `cwd` sets its own `skillListingBudgetFraction`.

    Such a listing was packed under the project's value, not the user-level one this hook manages.
    A session run from the home directory is not a project: its `.claude` IS the config dir.
    """
    if not isinstance(cwd, str) or not cwd:
        return False
    project = Path(cwd) / ".claude"
    try:
        if project.resolve() == config.resolve():
            return False
    except OSError:
        return False
    for name in ("settings.json", "settings.local.json"):
        try:
            settings = json.loads((project / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(settings, dict) and "skillListingBudgetFraction" in settings:
            return True
    return False


def observed_requirement(listing, descriptions, current):
    """Return the fraction the LAST listing shows was needed, or None when it shows no shortfall.

    A listing that is over budget is packed to within one entry of it, so `total` stands in for the
    budget that produced it. Scaling the fraction by (what was needed / what was delivered) needs
    neither the context size nor chars_per_token - both cancel - so this correction holds on any
    model, including one whose constants the estimate got wrong.

    That cancellation only works while `current` is the fraction that PRODUCED this listing. A
    listing from before the last raise was produced under a smaller one, and scaling today's value
    by yesterday's shortfall compounds the two into a wild over-correction. Two checks keep such a
    listing out. `listing_is_current` rejects one produced before settings.json last changed; the
    caller applies it, and it is the check that holds on every model. This function keeps a floor
    check that needs no timestamp: whatever the model, a budget is at least DENOMINATOR_FLOOR *
    current, so a total below that cannot have come from the current setting. The converse does
    not hold - above 200k tokens x 3 chars an old listing clears the floor - which is why the
    floor alone let a re-read listing ratchet the fraction up at every SessionStart.
    """
    if not listing or not listing["bare"]:
        return None
    if listing["total"] < DENOMINATOR_FLOOR * current:
        return None  # produced under an older, smaller fraction: it says nothing about this one
    owed = sum(2 + min(len(descriptions[name]), MAX_DESC_CHARS) for name in listing["bare"] if descriptions.get(name))
    if owed <= 0 or listing["total"] <= 0:
        return None  # every bare entry is a bundled skill or has no description to restore
    return (current * (listing["total"] + owed) / listing["total"]) * SAFETY


def build_message(entries, demand, change, dropped=0):
    """Return the one-line user-facing message for a fraction that was raised."""
    old, new = change
    evidence = (
        f"the last listing dropped {dropped} description(s) to a bare name"
        if dropped
        else f"{len(entries)} installed skills need about {demand:,} chars of skill listing"
    )
    return (
        f"skillListingBudgetFraction raised {old} -> {new}: {evidence}, which the old value could "
        f"not cover, so those skills reached the router as a name with no triggers. "
        f"Takes effect next session."
    )


def _correction(config, entries, current, settings_path):
    """Return (fraction, dropped) the newest usable listing asks for, or None when it asks nothing.

    A listing is usable when it was produced under the user-level value as it stands now: after
    settings.json last changed, and not in a project that overrides the fraction.
    """
    listing = newest_listing(config)
    if listing is None or not listing_is_current(listing, settings_path):
        return None
    if project_overrides_fraction(listing.get("cwd"), config):
        return None
    observed = observed_requirement(listing, dict(entries), current)
    if observed is None:
        return None
    return min(FRACTION_CAP, math.ceil(observed * 100) / 100), len(listing["bare"])


def wanted_fraction(config, entries, current, settings_path=None):
    """Return the fraction to aim for, and how many descriptions the last listing dropped.

    Two independent readings, and the larger wins: an ESTIMATE from what is installed on disk,
    which works on a machine with no history, and a CORRECTION from the listing the harness
    actually produced, which is the outcome the estimate is guessing at and needs none of its
    constants to be right. A correction that cannot be computed costs only itself: the estimate
    still stands.
    """
    estimate = required_fraction(listing_demand(entries))
    settings_path = settings_path if settings_path is not None else config / "settings.json"
    try:
        correction = _correction(config, entries, current, settings_path)
    except (OSError, ValueError, TypeError, AttributeError, KeyError, OverflowError):
        correction = None
    if correction is None:
        return estimate, 0
    corrected, dropped = correction
    return max(estimate, corrected), dropped


def main():
    config = config_dir()
    entries = installed_skills(config)
    if not entries:
        return  # nothing measured means nothing to conclude; never guess a fraction
    settings_path = config / "settings.json"
    wanted, dropped = wanted_fraction(config, entries, stored_fraction(settings_path), settings_path)
    change = raise_fraction(settings_path, wanted)
    if change is None:
        return
    message = build_message(entries, listing_demand(entries), change, dropped)
    json.dump({"systemMessage": message}, sys.stdout)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - a hook must never wedge a session
        pass
    sys.exit(0)
