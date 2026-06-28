"""Shared learning-signal patterns for the self-improve hooks.

Single source of truth, imported by:
  * self-improve-gate.py  - the per-turn Stop hook (uses the STRICT patterns: high
    precision, fires a capture nudge on the last turn).
  * self-improve-audit.py - the SessionEnd hook (uses STRICT + the BROADER recall
    patterns to find CANDIDATE MISSES across the whole session: a turn the broad set
    flags but the strict set did not, i.e. a likely gate gap to review next session).

Signals cluster in FAMILIES; cover the family, do not wait to be fed one phrase at a time:
  (1) USER correction, (2) USER explicit "remember", (3) ENDORSEMENT of a good idea from
  EITHER side, (4) ASSISTANT self-admitted miss, (5) ASSISTANT realization/discovery.

Role split: correction/"remember" count only from the USER; self-admitted misses and
realizations only from the ASSISTANT; endorsement counts from either side. English + German.
"""

import hashlib
import json
import re
import time
from pathlib import Path

# ---- Audit-file location (shared by self-improve-audit.py writer + session-start reader) --

def proj_key(proj):
    """Stable per-project key (matches the gate's state-file scheme)."""
    return hashlib.sha1(proj.encode("utf-8", "replace")).hexdigest()[:16]


def audit_file(proj):
    """Where the SessionEnd audit writes candidate misses for the next SessionStart to read."""
    return Path.home() / ".claude" / "self-improve-audit" / (proj_key(proj) + ".md")


# ---- meta-dream consolidation: cadence markers + mode (shared by session-start + dream_state) --

_DREAM_THRESHOLD_S = 24 * 3600  # do not nudge a fresh consolidation more often than this


def memory_dir(proj):
    """The native Auto-memory dir for a project cwd (Claude Code sanitizes '/' to '-')."""
    return Path.home() / ".claude" / "projects" / proj.replace("/", "-") / "memory"


def last_dream_file(proj):
    """Marker holding the unix timestamp of the last completed dream for this project."""
    return Path.home() / ".claude" / "self-improve-audit" / (proj_key(proj) + ".dream")


def dream_mode(proj=None):
    """Dream mode (single source of truth = the machine-local config; see load_config):
      off     -> no dream nudges; a manual dream consolidates memory only, no CLAUDE.md/skill proposals
      auto    -> dream applies CLAUDE.md edits and ships skill changes WITHOUT per-change prompts
      propose -> (default) dream asks before CLAUDE.md edits and routes skill changes to a self-PR
    Reads `~/.claude/.bitranox-memory.json`; until that exists, the legacy
    `.bitranox-dream-off` / `.bitranox-dream-auto` sentinels still apply (one-way migration).
    """
    return load_config().get("dream_mode", "propose")


def _newest_mtime(d):
    newest = 0.0
    try:
        for p in d.glob("*.md"):
            try:
                newest = max(newest, p.stat().st_mtime)
            except OSError:
                continue
    except OSError:
        return 0.0
    return newest


def dream_due(proj, threshold_s=_DREAM_THRESHOLD_S, now=None):
    """True if a memory consolidation is due: mode not off, memory changed since the last dream,
    and the last dream is older than the threshold. No memory or mode off -> not due."""
    if dream_mode(proj) == "off":
        return False
    mem = memory_dir(proj)
    newest = _newest_mtime(mem)
    if newest == 0.0:
        return False  # no memory to consolidate
    now = time.time() if now is None else now
    try:
        last = float(last_dream_file(proj).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return True  # never dreamed but memory exists -> due
    return newest > last and (now - last) > threshold_s


def mark_dream_done(proj, now=None):
    """Record that a dream just completed (silences the nudge until memory changes again)."""
    f = last_dream_file(proj)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(str(time.time() if now is None else now), encoding="utf-8")
        return True
    except OSError:
        return False


# ---- machine-local config: one JSON for all informed-consent knobs (recommended defaults) ----
# Every habit-dependent decision is recorded here and applied automatically (asked once, never
# re-nagged). The `meta-memory-settings` skill views / sets / resets it.

def _config_path():
    return Path.home() / ".claude" / ".bitranox-memory.json"


DEFAULT_CONFIG = {
    "dream_mode": "propose",       # off | auto | propose
    "privacy": "open",             # open (secret/PII scrub only) | walled (by privacy domain)
    "promotion": "corroborated",   # corroborated (inferred needs dwell) | eager
    "forgetting": "conservative",  # conservative | aggressive | off
    "forget_idle_dreams": 3,       # idle dreams before a non-must-always body is archived
    "skill_placement": "lowest",   # lowest scope that fits; ask before the public marketplace
    "nudges": True,                # session-start nudges on/off
}


def _legacy_dream_mode():
    """Pre-config opt-out sentinels in ~/.claude (honored until a config file is written)."""
    home = Path.home() / ".claude"
    try:
        if (home / ".bitranox-dream-off").exists():
            return "off"
        if (home / ".bitranox-dream-auto").exists():
            return "auto"
    except OSError:
        pass
    return "propose"


def load_config():
    """Config merged over DEFAULT_CONFIG. The JSON file is authoritative once it exists; until
    then the legacy `.bitranox-dream-*` sentinels supply dream_mode (one-way migration). Robust:
    a missing or corrupt file yields the recommended defaults."""
    cfg = dict(DEFAULT_CONFIG)
    try:
        raw = json.loads(_config_path().read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            cfg.update({k: raw[k] for k in raw if k in DEFAULT_CONFIG})
            return cfg
    except (OSError, ValueError):
        pass
    cfg["dream_mode"] = _legacy_dream_mode()
    return cfg


def save_config(updates):
    """Merge known keys from `updates` into the config file (created if missing); return the
    saved dict. Unknown keys are ignored so the file stays a clean, known schema."""
    cfg = load_config()
    cfg.update({k: updates[k] for k in updates if k in DEFAULT_CONFIG})
    try:
        p = _config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        pass
    return cfg


# ---- altitude homes (always-present tiers, narrowest -> broadest) --------------------

def global_rules_dir():
    """The always-present global rule layer: whole-loaded user rules, namespaced to bitranox."""
    return Path.home() / ".claude" / "rules" / "bitranox"


def altitude_chain(proj):
    """Ordered always-present homes for `proj`, narrowest -> broadest: the project's Auto-memory
    dir, then each ancestor directory (project root up toward `/`, each a CLAUDE.md altitude
    reachable by native cascade), then the global rules layer. Reference-integrity uses this: a
    `[[ref]]` must resolve to a target at the SAME or a LATER (higher) position - upward only."""
    chain = [memory_dir(proj)]
    try:
        here = Path(proj)
        chain.append(here)
        chain.extend(here.parents)
    except (TypeError, ValueError):
        pass
    chain.append(global_rules_dir())
    return chain


# ---- new-project seeding (one-time /collect-knowledge bootstrap nudge) ---------------

def seeded_file(proj):
    """Marker that this project has been seed-nudged (so the bootstrap nudge fires once)."""
    return Path.home() / ".claude" / "self-improve-audit" / (proj_key(proj) + ".seeded")


def mark_seeded(proj, now=None):
    f = seeded_file(proj)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(str(time.time() if now is None else now), encoding="utf-8")
        return True
    except OSError:
        return False


def project_unseeded(proj):
    """True if this project has no memory yet AND has not been seed-nudged - a fresh project that
    could be bootstrapped from the existing knowledge tree via /collect-knowledge."""
    if seeded_file(proj).exists():
        return False
    return _newest_mtime(memory_dir(proj)) == 0.0


# ---- quality / dwell gate for global promotion (high blast radius) -------------------
# The global layer loads into EVERY session, so a wrong entry there is high-blast. A user-stated
# concrete rule promotes eagerly; a model-INFERRED generalization must be corroborated (seen across
# >= threshold dreams) first. The dwell counter lives OUT of the dreamed store (here), so counting
# never bumps the store mtime - the convergence no-op holds.

def _promote_file(proj):
    return Path.home() / ".claude" / "self-improve-audit" / (proj_key(proj) + ".promote.json")


def _read_counts(path):
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def note_promotion_candidate(proj, key):
    """Record that this dream saw promotion-candidate `key`; return its dwell count (number of
    dreams it has appeared in). Out-of-store, so it does not affect convergence."""
    f = _promote_file(proj)
    counts = _read_counts(f)
    counts[key] = int(counts.get(key, 0)) + 1
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(counts, sort_keys=True), encoding="utf-8")
    except OSError:
        pass
    return counts[key]


def clear_promotion_candidate(proj, key):
    """Forget a candidate's dwell count (call after it is promoted, so it is not re-counted)."""
    f = _promote_file(proj)
    counts = _read_counts(f)
    if key in counts:
        del counts[key]
        try:
            f.write_text(json.dumps(counts, sort_keys=True), encoding="utf-8")
        except OSError:
            pass


def should_promote(source, dwell_count, mode=None, threshold=2):
    """Whether a generalization may be promoted to the always-everywhere global layer.
    source is "user" (user-stated concrete rule -> eager) or "inferred" (model generalization ->
    needs corroboration). mode comes from the config (`promotion`: corroborated | eager)."""
    mode = load_config().get("promotion", "corroborated") if mode is None else mode
    if mode == "eager" or source == "user":
        return True
    return int(dwell_count) >= threshold


# ---- per-level scope descriptor: a bounded, marked block in a CLAUDE.md --------------
# Each altitude declares "what this level is about" so the classifier can route knowledge. The
# descriptor is a clearly-delimited block so it never touches the user's hand-written content, and
# the upsert is DIFF-FREE (a no-change refresh returns the text unchanged -> convergence holds).

SCOPE_MARK_BEGIN = "<!-- bitranox:self-learning -->"
SCOPE_MARK_END = "<!-- /bitranox:self-learning -->"


def read_scope_block(text):
    """Return the descriptor inside the bitranox:self-learning markers in `text`, or None."""
    b = (text or "").find(SCOPE_MARK_BEGIN)
    if b < 0:
        return None
    e = text.find(SCOPE_MARK_END, b)
    if e < 0:
        return None
    return text[b + len(SCOPE_MARK_BEGIN):e].strip()


def upsert_scope_block(text, descriptor):
    """Return CLAUDE.md `text` with the marked scope block set to `descriptor` (replaced in place if
    present, appended if absent). DIFF-FREE: if the block already holds `descriptor`, return `text`
    unchanged so a no-change refresh writes nothing."""
    text = text or ""
    descriptor = (descriptor or "").strip()
    block = "%s\n%s\n%s" % (SCOPE_MARK_BEGIN, descriptor, SCOPE_MARK_END)
    b = text.find(SCOPE_MARK_BEGIN)
    if b >= 0:
        e = text.find(SCOPE_MARK_END, b)
        if e >= 0:
            if text[b + len(SCOPE_MARK_BEGIN):e].strip() == descriptor:
                return text  # already current -> no write
            return text[:b] + block + text[e + len(SCOPE_MARK_END):]
    sep = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    return text + sep + block + "\n"


def store_changed(memory_dir_path, since_mtime):
    """True if a memory dir changed since `since_mtime` (a 'store changed under me' guard for the
    dream's read-modify-write; pair with the pre-flight backup)."""
    return _newest_mtime(Path(memory_dir_path)) > float(since_mtime)


def _idle_file(proj):
    return Path.home() / ".claude" / "self-improve-audit" / (proj_key(proj) + ".idle.json")


def bump_idle(proj, key):
    """Increment and return an entry's idle-dream count (how many consecutive dreams saw it unused).
    Out-of-store, so decay bookkeeping never bumps the dreamed store's mtime (convergence holds)."""
    f = _idle_file(proj)
    counts = _read_counts(f)
    counts[key] = int(counts.get(key, 0)) + 1
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(counts, sort_keys=True), encoding="utf-8")
    except OSError:
        pass
    return counts[key]


def reset_idle(proj, key):
    """Clear an entry's idle count - call when an observable proxy shows it was used (a skill
    invocation, an explicit reference) so a used entry is never archived."""
    f = _idle_file(proj)
    counts = _read_counts(f)
    if key in counts:
        del counts[key]
        try:
            f.write_text(json.dumps(counts, sort_keys=True), encoding="utf-8")
        except OSError:
            pass


def should_archive(idle_count, mode=None, n=None):
    """Whether a NON-must-always entry idle this many dreams should be archived out of the
    always-present window. Honors the `forgetting` knob: off -> never; conservative -> idle >= N
    (config `forget_idle_dreams`, default 3); aggressive -> idle >= 1. Bias toward keeping."""
    cfg = load_config()
    mode = cfg.get("forgetting", "conservative") if mode is None else mode
    if mode == "off":
        return False
    n = cfg.get("forget_idle_dreams", 3) if n is None else n
    if mode == "aggressive":
        return int(idle_count) >= 1
    return int(idle_count) >= int(n)


def knowledge_store_empty():
    """True if there is nothing anywhere to seed a new project FROM: the global rules layer is empty
    AND no project's memory holds a topic file. Used to suppress the new-project bootstrap nudge on a
    fresh machine (nothing to gather yet)."""
    try:
        if any(global_rules_dir().rglob("*.md")):
            return False
    except OSError:
        pass
    try:
        for memdir in (Path.home() / ".claude" / "projects").glob("*/memory"):
            for p in memdir.glob("*.md"):
                if p.name != "MEMORY.md":
                    return False
    except OSError:
        pass
    return True


# ---- STRICT patterns (the gate fires on these; tuned for precision) -----------------

# USER correction / explicit remember.
USER_PATTERN = re.compile(
    r"no,|nope|that.?s wrong|that is wrong|incorrect|don.?t do|do not do|stop doing"
    r"|you (forgot|missed|should have|shouldn.?t)|not what i|instead of"
    r"|that.?s not right|isn.?t right"
    r"|remember|note that|keep in mind|for next time|for the future|from now on"
    r"|make a (memory|rule|note)"
    r"|falsch|nein,|stattdessen|merke? dir|in zukunft|denk dran",
    re.IGNORECASE,
)

# ASSISTANT self-admitted miss (incl. a guard/hook blocking the assistant's own action).
ASST_PATTERN = re.compile(
    r"you.?re right|you are right|my mistake|i was wrong|apolog"
    r"|(hook|guard|gate)\b[^.\n]{0,30}\b(caught|blocked|stopped|flagged|rejected)\b[^.\n]{0,10}\b(me|my)\b"
    r"|\b(caught|blocked|stopped|flagged|rejected)\b[^.\n]{0,20}\bby (a |the )?(hook|guard|gate)"
    r"|self.?match(ed|ing|es)?",
    re.IGNORECASE,
)

# ASSISTANT realization/discovery (how something really fits together).
REALIZATION_PATTERN = re.compile(
    r"now i (understand|see|realize|get it)\b"
    r"|i (now|finally) (understand|see|realize)\b"
    r"|i(.?ve| have)? figured (it |this )?out|i figured out\b"
    r"|the (real|actual) (topolog|architect|structure|setup|layout|wiring|flow|picture|story|design)"
    r"|it turns out\b|turns out (that|the)\b"
    r"|(that|this) explains (the|why|how|what)\b"
    r"|the (key|real|actual) (insight|issue|problem|cause|reason)\b|root cause is\b"
    r"|(actually|really) (runs|lives|sits|resides|is hosted|happens|is served) on\b"
    r"|clear(er)? picture|the (full|whole|complete|bigger) picture"
    r"|\b(now|it all|everything|it)('?s| is| are)? (clear|much clearer)\b"
    r"|\bmakes sense now\b|\bnow [^.\n]{0,20}makes sense\b"
    r"|jetzt (verstehe ich|wird klar|ergibt)|jetzt ist (alles |es )?klar|klares bild"
    r"|stellt sich heraus|herausgefunden",
    re.IGNORECASE,
)

# ENDORSEMENT of a good idea, from EITHER side (assistant judging the user's suggestion
# good -> adopt it; or the user endorsing the assistant's proposal -> confirmed approach).
ENDORSE_PATTERN = re.compile(
    r"(good|great|nice|smart|clever|brilliant|excellent) (idea|call|point|catch|thinking|suggestion)"
    r"|i like (that|this|your) (idea|approach|plan|suggestion)|let.?s do (that|it)"
    r"|gute idee|guter (punkt|einfall)|gut(er)? gedacht",
    re.IGNORECASE,
)

# ---- BROAD recall patterns (audit-only: catch likely MISSES the strict set skips) ----
# Deliberately wider and learning-flavoured. A turn that matches BROAD but not STRICT is a
# CANDIDATE MISS for review, never a live block. Tuned to stay off bare acknowledgements.

BROAD_USER_PATTERN = re.compile(
    r"\b(wrong|incorrect|broken|fails?|failing|not working|doesn.?t work|didn.?t work)\b"
    r"|\bwhy (did|are|is|do|does) (you|it|that|this)\b"
    r"|\byou (always|keep|still|again|never)\b"
    r"|\bi (told|asked) you\b|\bas i (said|mentioned|asked)\b"
    r"|\bnot (quite|what i|right|correct)\b|\b(revert|undo|rollback)\b"
    r"|\b(perfect|exactly right|spot on|love it|that.?s it|works now)\b",
    re.IGNORECASE,
)

BROAD_ASST_PATTERN = re.compile(
    r"\bi (missed|overlooked|forgot|misread|misunderstood|didn.?t (realize|notice|account))\b"
    r"|\bi should (have|.?ve) \w+|\bon reflection\b|\blet me reconsider\b"
    r"|\bgood (point|catch)\b"
    r"|\bthe (issue|problem|bug|root cause|reason) (is|was|turned out|ended up)\b"
    r"|\b(in hindsight|as it turns out)\b"
    r"|\bi see (why|how|what|now|the)\b"
    r"|\b(ah|oh|oops|whoops)[, ]|\bwait[, ]",
    re.IGNORECASE,
)


def strict_user_hit(text):
    """A strict learning signal in a USER message (correction/remember/endorsement)."""
    return bool(USER_PATTERN.search(text) or ENDORSE_PATTERN.search(text))


def strict_asst_hit(text):
    """A strict learning signal in an ASSISTANT message (admission/realization/endorsement)."""
    return bool(ASST_PATTERN.search(text) or REALIZATION_PATTERN.search(text)
                or ENDORSE_PATTERN.search(text))


def broad_matches(role, text):
    """Lower-cased, de-duplicated broad-recall matches for a message; [] if none.

    role is "user" or "assistant"; selects the matching broad pattern.
    """
    rx = BROAD_USER_PATTERN if role == "user" else BROAD_ASST_PATTERN
    return sorted({m.group(0).strip().lower() for m in rx.finditer(text or "")})
