"""The credential vocabulary shared by every hook that must recognise a secret.

Three callers need the same answer to "is this a secret?" and used to carry three copies:
repo-gate blocks a commit that holds one, recall-memory withholds a note that holds one, and the
classifier REDACTS one before text leaves the machine. One definition keeps a pattern added for
one of them from being silently missing in the others.

The test is always a VALUE, never a word: "never commit a password" names the concept and
carries nothing, while `Password: <value>`, `DB_PASSWORD=<value>` and `scheme://user:pw@host`
are the secret itself.

Pure standard library.
"""

import re

__all__ = [
    "PRIVATE_KEY_RX",
    "REDACTED",
    "TOKEN_PATTERNS",
    "find_secret_labels",
    "holds_a_credential",
    "real_private_key_blocks",
    "redact",
]

REDACTED = "[REDACTED]"

# High-signal token formats (gitleaks/trufflehog family), low false-positive by construction.
TOKEN_PATTERNS = [
    (re.compile(r"ghp_[A-Za-z0-9]{36,}"), "GitHub token"),
    # Installation tokens (ghs_) are long JWT-format strings (~520 chars) carrying dots, dashes
    # and underscores, so the body allows ".-_" and is open-ended on length.
    (re.compile(r"ghs_[A-Za-z0-9._-]{36,}"), "GitHub App installation token"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{60,}"), "GitHub fine-grained PAT"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{24,}"), "Anthropic API key"),
    (re.compile(r"\bsk-[A-Za-z0-9]{40,}\b"), "OpenAI-style key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "Google API key"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20}\b"), "GitLab token"),
]

PRIVATE_KEY_RX = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----([\s\S]{20,8000}?)-----END [A-Z0-9 ]*PRIVATE KEY-----"
)

# A labelled value as a human writes it in a runbook: `Password: x`, `api key = x`. Group 1 is
# the label with its separator (kept), group 2 the value (redacted).
_LABELLED_RX = re.compile(
    r"(?im)(\b(?:pass(?:word|phrase)?|pwd|secret|api[ _-]?key|access[ _-]?key|token"
    r"|credentials?)\b\s*[:=]\s*)(\S+)"
)
# An environment assignment whose NAME says secret. `\btoken\b` above cannot see `GITHUB_TOKEN`
# because `_` is a word character, which is exactly the shape a `.env` file and tool output use.
_ENV_RX = re.compile(
    r"(?im)^(\s*(?:export\s+)?[A-Za-z_][A-Za-z0-9_]*"
    r"(?:PASS|PASSWD|PASSWORD|SECRET|TOKEN|APIKEY|API_KEY|ACCESS_KEY|PRIVATE_KEY|CREDENTIALS?|PWD)"
    r"[A-Za-z0-9_]*\s*=\s*)(\S+)"
)
_URL_USERINFO_RX = re.compile(r"(?i)(\b[a-z][a-z0-9+.-]*://[^/\s:@]+:)([^/\s@]+)(@)")
_BEARER_RX = re.compile(r"(?i)(\bbearer\s+)([A-Za-z0-9._~+/=-]{8,})")


def real_private_key_blocks(text):
    """Yield each private key block that carries real key material.

    A body with a "..." truncation marker or too little base64 is an illustrative example (a
    tutorial's elided key), which the commit gate must not block on.
    """
    for m in PRIVATE_KEY_RX.finditer(text):
        body = m.group(1)
        if "..." not in body and len(re.sub(r"[^A-Za-z0-9+/=]", "", body)) > 64:
            yield m


def find_secret_labels(text):
    """Return the label of every known token format present in `text` (a label per format)."""
    return [label for rx, label in TOKEN_PATTERNS if rx.search(text)]


def holds_a_credential(text):
    """True when `text` carries a secret VALUE rather than merely discussing one."""
    if find_secret_labels(text) or next(real_private_key_blocks(text), None):
        return True
    return any(rx.search(text) for rx in (_LABELLED_RX, _ENV_RX, _URL_USERINFO_RX))


def redact(text, extra_literals=()):
    """Replace every secret value in `text` with `[REDACTED]`; return (text, count).

    Everything around a secret is kept - the label, the variable name, the URL's host - because
    that is the context a classifier needs to judge the text. Private key blocks are replaced
    whole, markers included, since even an elided example has no value to a reader. Aggressive
    by design: a false positive costs one word of context, a false negative sends a live
    credential to a third party.
    """
    count = 0

    def _sub(rx, build, s):
        # `build(m)` returns the replacement, or None to leave that match alone; only a real
        # replacement counts, so one secret matched by two passes is counted once.
        def _repl(m):
            nonlocal count
            out = build(m)
            if out is None:
                return m.group(0)
            count += 1
            return out
        return rx.sub(_repl, s)

    for literal in extra_literals:
        if literal:
            count += text.count(literal)
            text = text.replace(literal, REDACTED)
    text = _sub(PRIVATE_KEY_RX, lambda m: REDACTED, text)
    for rx, _label in TOKEN_PATTERNS:
        text = _sub(rx, lambda m: REDACTED, text)
    text = _sub(_URL_USERINFO_RX, _redact_group_2, text)
    text = _sub(_BEARER_RX, _redact_group_2, text)
    for rx in (_ENV_RX, _LABELLED_RX):
        text = _sub(rx, _redact_group_2, text)
    return text, count


def _redact_group_2(m):
    """Keep group 1 (the label, name or scheme) and anything after group 2; drop group 2.

    Returns None when group 2 already starts with the marker, so a value an earlier pass
    redacted is neither marked nor counted twice.
    """
    if m.group(2).startswith(REDACTED):
        return None
    tail = m.group(3) if m.re.groups >= 3 else ""
    return m.group(1) + REDACTED + tail
