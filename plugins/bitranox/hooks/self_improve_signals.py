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


# ---- meta-dream-project consolidation: cadence markers + mode (shared by session-start + dream_state) --

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
    dir, then each ancestor directory THAT ACTUALLY HOLDS A `CLAUDE.md` (a real cascade altitude),
    then the global rules layer (always LAST). Only CLAUDE.md-bearing ancestors are altitudes - we
    never return every dir up to `/`, so a consumer never has to scan unrelated trees. Reference-
    integrity uses this: a `[[ref]]` must resolve to a target at the SAME or a LATER (higher)
    position - upward only; the last position (global) is the recursive layer."""
    chain = [memory_dir(proj)]
    try:
        here = Path(proj)
        ladder = [here, *here.parents]            # project dir up toward /
        highest = None                            # index of the HIGHEST ancestor that HAS a CLAUDE.md
        for i, d in enumerate(ladder):
            try:
                if (d / "CLAUDE.md").is_file():
                    highest = i
            except OSError:
                continue
        if highest is not None:
            # contiguous tree from the project up to the highest existing CLAUDE.md, INCLUDING gap
            # levels in between (a missing CLAUDE.md is a gap to fill, not a stop - see the dream's
            # descriptor step). We never go above the highest existing CLAUDE.md (no walk to / beyond).
            chain.extend(ladder[:highest + 1])
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


# NOTE: there is deliberately NO usage/age/size "forgetting" mechanism. Usage cannot be measured (the
# note sits in context; the model reasons over it silently), and age/size are not valid forget metrics
# (see the `forgetting-is-usage-based-only` memory). Removal happens only via dedup, obsolete/superseded
# pruning (model-judged, propose-first), or a manual request - the dream does that; no helper here.


def _model_review_file():
    return Path.home() / ".claude" / "self-improve-audit" / "model-review.txt"


def model_review_due(interval_days=30, now=None):
    """True if the periodic model-hierarchy review (run by meta-dream-project) is due: no prior review, or the
    last one is older than `interval_days`. GLOBAL (not per-project) and OUT of any memory store, so it
    never bumps a store's mtime (convergence holds). Model releases are infrequent -> a monthly default."""
    import time as _time
    now = _time.time() if now is None else now
    try:
        last = float(_model_review_file().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return True
    return (now - last) >= interval_days * 86400


def mark_model_reviewed(now=None):
    """Record that the model-hierarchy review just ran, so it does not re-fire until due again."""
    import time as _time
    now = _time.time() if now is None else now
    f = _model_review_file()
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(str(now), encoding="utf-8")
    except OSError:
        pass
    return now


# --- Recall filler words (memory-recall keyword precision) ---------------------------------------
# Generic/conversational words must not become recall search keywords (they match half the store).
# THREE lists, split by who is universal vs a project-specific judgment (so one project's learned
# classification never suppresses another project's recall - see the `recall-filler-per-project` memory):
#   - GLOBAL baseline blacklist: filler_words.json next to this module (generic English; grows via PRs).
#   - PER-PROJECT learned blacklist: filler the dream classified for THAT project.
#   - PER-PROJECT learned whitelist: topical/known-good words (so they are not re-queued).
# The per-prompt hook only USES these (deterministic, no model), keyed to the CURRENT project (the
# prompt's origin); GROWING them is a slow dream pass. See meta-dream-project's "Filler-word classification".

def _filler_baseline_path():
    return Path(__file__).resolve().parent / "filler_words.json"


def _filler_local_path(proj):
    """PER-PROJECT learned filler blacklist (out-of-store, machine-local)."""
    return Path.home() / ".claude" / "self-improve-audit" / (proj_key(proj) + ".filler.json")


def _topical_words_path(proj):
    """PER-PROJECT learned topical whitelist - confirmed genuine topics, not re-queued for classification."""
    return Path.home() / ".claude" / "self-improve-audit" / (proj_key(proj) + ".topical.json")


def _recall_pending_path(proj):
    """PER-PROJECT queue of as-yet-unclassified recall keywords, drained by the dream classifier."""
    return Path.home() / ".claude" / "self-improve-audit" / (proj_key(proj) + ".recall-unknown.txt")


def _read_word_json(path):
    """Read a word-list JSON that may be a bare list or {"filler"/"words"/"topical": [...]}. Fail-open []."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if isinstance(data, list):
        words = data
    elif isinstance(data, dict):
        words = data.get("filler") or data.get("words") or data.get("topical") or []
    else:
        words = []
    return [str(w).strip().lower() for w in words if isinstance(w, str) and str(w).strip()]


def _write_word_json(path, words, key="words"):
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps({key: sorted(set(words))}, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def load_filler_words(proj=None):
    """The effective filler blacklist for `proj`: GLOBAL baseline UNION the project's LEARNED filler.
    Baseline is universal generic-English filler; learned filler is per-project so one project's
    classification never suppresses another's recall. With proj=None, baseline only. Lowercased frozenset."""
    words = list(_read_word_json(_filler_baseline_path()))
    if proj is not None:
        words += _read_word_json(_filler_local_path(proj))
    return frozenset(words)


def add_filler_words(words, proj):
    """Append classifier-confirmed filler to the PROJECT's learned blacklist (never the shipped baseline)."""
    new = {str(w).strip().lower() for w in words if str(w).strip()}
    if not new:
        return
    p = _filler_local_path(proj)
    _write_word_json(p, set(_read_word_json(p)) | new, key="filler")


def load_topical_words(proj):
    """The project's learned topical whitelist (genuine topics, not re-queued). Lowercased frozenset."""
    return frozenset(_read_word_json(_topical_words_path(proj)))


def add_topical_words(words, proj):
    """Record classifier-confirmed topical words for THIS project so they are not re-queued."""
    new = {str(w).strip().lower() for w in words if str(w).strip()}
    if not new:
        return
    p = _topical_words_path(proj)
    _write_word_json(p, set(_read_word_json(p)) | new, key="topical")


def note_unknown_keywords(words, proj):
    """Per-prompt: queue this project's recall keywords that are NEITHER known filler NOR known-topical,
    for the dream classifier to judge. Deterministic, append-only, deduped; never calls a model."""
    known = load_filler_words(proj) | load_topical_words(proj)
    cur = load_pending_keywords(proj)
    add = {str(w).strip().lower() for w in words if str(w).strip()} - known - cur
    if not add:
        return
    f = _recall_pending_path(proj)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        with f.open("a", encoding="utf-8") as fh:
            for w in sorted(add):
                fh.write(w + "\n")
    except OSError:
        pass


def load_pending_keywords(proj):
    """The project's queued-but-unclassified recall keywords (for the dream classifier)."""
    try:
        return frozenset(w.strip().lower() for w in _recall_pending_path(proj).read_text(
            encoding="utf-8").splitlines() if w.strip())
    except OSError:
        return frozenset()


def clear_pending_keywords(proj):
    """Drain THIS project's queue after the dream classifier has processed it."""
    try:
        _recall_pending_path(proj).unlink()
    except OSError:
        pass


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
    r"|you (forgot|missed|should have|shouldn.?t)|not what i|instead of|rather than"
    r"|that.?s not right|isn.?t right"
    r"|remember|note that|keep in mind|for next time|for the future|from now on"
    r"|make a (memory|rule|note)"
    r"|falsch|nein,|stattdessen|anstatt|anstelle|merke? dir|in zukunft|denk dran",
    re.IGNORECASE,
)

# ASSISTANT self-admitted miss (incl. a guard/hook blocking the assistant's own action).
ASST_PATTERN = re.compile(
    r"you.?re right|you are right|my mistake|i was wrong|apolog"
    r"|\bi should(?: have|'?ve)\b|\bi (missed|overlooked|forgot|misread|misunderstood)\b"
    r"|\bi did(?:n'?t| not) (realize|notice|account|consider|catch)\b|\bin hindsight\b"
    r"|\b(from now on|going forward|next time)\b[^.\n]{0,20}\bi('?ll| will| should)\b"
    r"|\bi('?ll| will) (make sure|remember) (to|not)\b"
    r"|\b(hook|guard|gate)\b[^.\n]{0,30}\b(caught|blocked|stopped|flagged|rejected)\b"
    r"|\b(caught|blocked|stopped|flagged|rejected)\b[^.\n]{0,30}\b(hook|guard|gate)\b"
    r"|self.?match(ed|ing|es)?",
    re.IGNORECASE,
)

# ASSISTANT realization/discovery (how something really fits together).
REALIZATION_PATTERN = re.compile(
    r"now i (understand|see|realize|get it)\b"
    r"|i (now|finally) (understand|see|realize)\b"
    r"|i(.?ve| have)? figured (it |this )?out|i figured out\b"
    r"|(?<!not )(?<!n't )\bfound it\b"
    r"|\bfound (the|a|its) (bug|cause|culprit|problem|issue|leak|regression|reason|root cause)\b"
    r"|\bfound out (that|why|how|where)\b|\bthe culprit (is|was)\b"
    r"|the (real|actual) (topolog|architect|structure|setup|layout|wiring|flow|picture|story|design)"
    r"|it turns out\b|turns out (that|the)\b"
    r"|(that|this) explains (the|why|how|what)\b"
    r"|the (key|real|actual) (insight|issue|problem|cause|reason)\b|root cause is\b"
    r"|(actually|really) (runs|lives|sits|resides|is hosted|happens|is served) on\b"
    r"|clear(er)? picture|the (full|whole|complete|bigger) picture"
    r"|\b(now|it all|everything|it)('?s| is| are)? (clear|much clearer)\b"
    r"|\bmakes sense now\b|\bnow [^.\n]{0,20}makes sense\b"
    r"|jetzt (verstehe ich|wird klar|ergibt)|jetzt ist (alles |es )?klar|klares bild"
    r"|stellt sich heraus|herausgefunden"
    r"|\b(fehler|ursache|problem|grund|bug) gefunden\b|\bda (ist|war) (es|der fehler|das problem)\b",
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
    r"|\bfound (it|the|out)\b|\bthe culprit\b|\bgefunden\b"
    r"|\blet me (stop|inspect|double.?check|re.?check|look (again|closer)|take a closer look)\b"
    r"|\bper the .{1,80}? rule\b|\bthe \".{1,80}?\" rule\b|\bfollowing the .{1,60}? (rule|convention)\b"
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
