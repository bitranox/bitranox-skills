"""The plugin's shipped text prescribes only the `haiku` and `opus` subagent tiers.

`sonnet` is not a tier this plugin dispatches on: across a whole job it costs more than `opus`,
because it takes more turns and more reasoning tokens for the same work. `haiku` stays for purely
mechanical work. A skill that still says "fan out on sonnet" teaches every reader the old tier, so
this test scans every shipped skill text, agent definition and script for the word.

Files where `sonnet` is DATA rather than a tier choice are listed in DATA_FILES with the reason:
a model-window table, the gate that warns on it, a vendored upstream document. A model id such as
`claude-sonnet-4.5` is never matched. The canonical tier reference may name it only on the lines
in EXPLANATIONS, which say why it is excluded.
"""

import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]

# Paths relative to PLUGIN where the word names a model as data, never a tier to dispatch on.
DATA_FILES = {
    # model-family context-window table: every family needs its row
    "hooks/context-watcher.py",
    # the gate that warns on a sonnet pin has to name it
    "hooks/subagent-model-gate.py",
    # Anthropic's own authoring guide, vendored verbatim
    "skills/meta-skill-writer/anthropic-best-practices.md",
}

# The canonical tier reference says once why sonnet is excluded; only those lines may name it.
EXPLANATIONS = {
    "skills/process-agents-subagent-driven-development/SKILL.md": (
        "**`sonnet` is not a tier here.**",
        "warns on a dispatch pinned to `sonnet`.",
    ),
}

SONNET = re.compile(r"(?<![\w/-])sonnet(?![\w-])", re.IGNORECASE)


def _shipped_texts():
    for path in sorted(PLUGIN.rglob("*")):
        rel = path.relative_to(PLUGIN).as_posix()
        if not path.is_file() or path.suffix not in {".md", ".py"}:
            continue
        parts = set(rel.split("/"))
        if parts & {"tests", ".skillwriter", "__pycache__"} or rel == "CHANGELOG.md":
            continue
        yield rel, path


def test_no_shipped_text_prescribes_a_sonnet_tier():
    scanned = 0
    hits = []
    for rel, path in _shipped_texts():
        scanned += 1
        if rel in DATA_FILES:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if SONNET.search(line) and not any(e in line for e in EXPLANATIONS.get(rel, ())):
                hits.append(f"{rel}:{lineno}: {line.strip()[:120]}")
    assert scanned > 100, f"scanned only {scanned} files - the walk is broken"
    assert hits == [], "sonnet is not a dispatch tier (use opus, or haiku for mechanical work):\n" + "\n".join(hits)


def test_every_data_file_exemption_still_names_the_model():
    """An exemption whose file no longer mentions the model is dead and would hide a new tier choice."""
    for rel in DATA_FILES:
        text = (PLUGIN / rel).read_text(encoding="utf-8")
        assert SONNET.search(text), f"{rel} no longer mentions sonnet; drop it from DATA_FILES"
    for rel, lines in EXPLANATIONS.items():
        text = (PLUGIN / rel).read_text(encoding="utf-8")
        for line in lines:
            assert line in text, f"{rel} lost its explanation line {line!r}; update EXPLANATIONS"


def test_the_pattern_matches_tier_spellings_and_skips_model_ids():
    for tier_choice in ("a `sonnet` subagent", 'model="sonnet"', "model: sonnet", "Sonnet tier"):
        assert SONNET.search(tier_choice), tier_choice
    for data in ("anthropic/claude-sonnet-4.5", "claude-sonnet-5", "sonnet-5 665,313"):
        assert not SONNET.search(data), data
