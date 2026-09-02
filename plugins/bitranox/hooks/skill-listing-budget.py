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

Emits the Claude Code SessionStart contract on stdout. Pure standard library. Every failure path
emits nothing and exits 0, so a broken hook never blocks a session.
"""

import json
import math
import os
import re
import sys
from pathlib import Path

# The harness truncates a single description at this many characters (skillListingMaxDescChars).
MAX_DESC_CHARS = 1536

# Bundled (Anthropic) skills ship inside the CLI binary, not on disk, so they cannot be measured
# here - but they occupy the same budget and are exempt from the rationing. Measured at 19 entries
# and ~8.3k characters; rounded well up because they grow between CLI releases and over-providing
# a ceiling is free.
BUNDLED_ALLOWANCE = 12_000

# budget = context_tokens * chars_per_token * fraction. Both factors vary per model, so the
# fraction is sized against the SMALLEST context worth serving (a 200k-token model at 3 chars per
# token). A larger context then gets a ceiling far above its listing, which costs nothing.
DENOMINATOR_FLOOR = 600_000

SAFETY = 1.25
FRACTION_CAP = 0.5  # refuse to run away if a catalogue is pathologically large

_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
_DESCRIPTION = re.compile(r"^description:\s*(.*(?:\n(?![A-Za-z_-]+:).*)*)", re.M)


def config_dir():
    """Return the Claude configuration directory (CLAUDE_CONFIG_DIR wins, else ~/.claude)."""
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(override) if override else Path.home() / ".claude"


def read_description(skill_md):
    """Return a SKILL.md's frontmatter description as one line, or None if it has none."""
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    matter = _FRONTMATTER.match(text)
    if not matter:
        return None
    found = _DESCRIPTION.search(matter.group(1))
    return " ".join(found.group(1).split()) if found else None


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
    current = settings.get("skillListingBudgetFraction")
    current = current if isinstance(current, (int, float)) else 0.01  # harness default
    if wanted <= current:
        return None
    settings["skillListingBudgetFraction"] = wanted
    try:
        settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError:
        return None
    return current, wanted


def build_message(entries, demand, change):
    """Return the one-line user-facing message for a fraction that was raised."""
    old, new = change
    return (
        f"skillListingBudgetFraction raised {old} -> {new}: {len(entries)} installed skills need "
        f"about {demand:,} chars of skill listing, which the old value could not cover, so "
        f"descriptions were being dropped to bare names. Takes effect next session."
    )


def main():
    config = config_dir()
    entries = installed_skills(config)
    if not entries:
        return  # nothing measured means nothing to conclude; never guess a fraction
    demand = listing_demand(entries)
    change = raise_fraction(config / "settings.json", required_fraction(demand))
    if change is None:
        return
    json.dump({"systemMessage": build_message(entries, demand, change)}, sys.stdout)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - a hook must never wedge a session
        pass
    sys.exit(0)
