"""The credential vocabulary shared by every hook that must recognise a secret.

Three callers need the same answer to "is this a secret?" and used to carry three copies:
repo-gate blocks a commit that holds one, recall-memory withholds a note that holds one, and the
classifier REDACTS one before text leaves the machine. One definition keeps a pattern added for
one of them from being silently missing in the others.

The test is always a VALUE, never a word: "never commit a password" names the concept and
carries nothing, while `Password: <value>`, `DB_PASSWORD=<value>`, `{"password": "<value>"}` and
`scheme://user:pw@host` are the secret itself.

Pure standard library.
"""

import re

__all__ = [
    "PRIVATE_KEY_RX",
    "REDACTED",
    "TOKEN_PATTERNS",
    "UNTERMINATED_PRIVATE_KEY_RX",
    "find_secret_labels",
    "holds_a_credential",
    "real_private_key_blocks",
    "redact",
]

REDACTED = "[REDACTED]"

# High-signal token formats (gitleaks/trufflehog family), low false-positive by construction.
TOKEN_PATTERNS = [
    # Personal (ghp_), OAuth (gho_), user-to-server (ghu_) and refresh (ghr_) tokens share a
    # shape: the prefix and 36+ alphanumerics.
    (re.compile(r"gh[pour]_[A-Za-z0-9]{36,}"), "GitHub token"),
    # Installation tokens (ghs_) are long JWT-format strings (~520 chars) carrying dots, dashes
    # and underscores, so the body allows ".-_" and is open-ended on length.
    (re.compile(r"ghs_[A-Za-z0-9._-]{36,}"), "GitHub App installation token"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{60,}"), "GitHub fine-grained PAT"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{24,}"), "Anthropic API key"),
    # Two OpenAI shapes: the legacy all-alphanumeric key, and the project / service-account /
    # admin keys whose bodies carry "-" and "_". Only the NAMED prefixes admit those characters,
    # so a long kebab-case identifier that happens to start "sk-" is not a key, and sk-ant- keys
    # (matched above) never match here: "ant" is not one of the prefixes.
    (re.compile(r"\bsk-[A-Za-z0-9]{40,}\b"), "OpenAI-style key"),
    (re.compile(r"\bsk-(?:proj|svcacct|admin)-[A-Za-z0-9_-]{40,}"), "OpenAI-style key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "Google API key"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    # Not a fixed 20 characters: the body is open-ended, like the other formats here.
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}"), "GitLab token"),
]

# PEM ("RSA PRIVATE KEY", "OPENSSH PRIVATE KEY", ...) and PGP armour ("PGP PRIVATE KEY BLOCK").
_KEY_BEGIN = r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----"
_KEY_END = r"-----END [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----"

# A complete block. The body may not cross another BEGIN line, so an elided example sitting
# before a real key is its own (short) block instead of swallowing the real one up to its END.
# That same rule bounds the scan, so the body needs no length cap.
PRIVATE_KEY_RX = re.compile(_KEY_BEGIN + r"((?:(?!-----BEGIN )[\s\S])*?)" + _KEY_END)

# A BEGIN line with no END: `head -5 id_rsa`, a capped tool output, a truncated paste. Group 1
# is the run of lines that follows - base64 lines, `Name: value` armour headers (Proc-Type,
# DEK-Info, Version) and blank lines - up to the first line that is none of those. A line break
# may also be the two characters backslash-n, the shape a key takes inside a JSON string.
_KEY_LINE_BREAK = r"(?:\r?\n|\\r?\\n)"
_KEY_LINE = (
    r"(?:[ \t]*[A-Za-z0-9+/=]+[ \t]*"
    r"|[A-Za-z][A-Za-z0-9-]*:[^\r\n\\\"]*"
    r"|[ \t]*)"
    r"(?=[\r\n\\\"]|\Z)"
)
UNTERMINATED_PRIVATE_KEY_RX = re.compile(
    _KEY_BEGIN + r"((?:" + _KEY_LINE_BREAK + _KEY_LINE + r")*)"
)
_BASE64_LINE_RX = re.compile(r"[ \t]*([A-Za-z0-9+/=]+)[ \t]*")
_KEY_LINE_SPLIT_RX = re.compile(_KEY_LINE_BREAK)

# The base64 characters a block must carry before detection calls it real key material.
_MIN_KEY_MATERIAL = 64

# A labelled value, in every shape a human, a config file or a tool writes one: `Password: x`,
# `api key = x`, `DB_PASSWORD=x`, `export DB_PASSWORD='x'`, `docker run -e DB_PASSWORD=x`,
# `{"password": "x"}`, `  POSTGRES_PASSWORD: x`, `"SecretAccessKey": "x"`. The regex only finds
# CANDIDATES (a name holding a secret-ish keyword, a `:` or `=`, a value); `_secret_words` then
# decides from the name's words whether it really names a secret, which keeps `max_tokens: 800`,
# `bypass=1` and the shell's `PWD=/home/x` out. A quoted value is taken whole, up to its closing
# quote; an unquoted one runs to the next whitespace.
_NAMED_VALUE_RX = re.compile(
    r"(?P<pre>(?<![A-Za-z0-9_.-])"
    r"(?P<name>(?:[A-Za-z0-9_.-]+ )?"
    # A lookahead, which never backtracks, so a long run of name characters costs one pass.
    r"(?=[A-Za-z0-9_.-]*?(?:pass|pwd|secret|token|key|credential))[A-Za-z0-9_.-]+)"
    # `==` and `::` are a comparison and a path (`Token::new`), not an assignment.
    r"[\"']?[ \t]*[:=](?![:=])[ \t]*(?P<q>[\"'])?)"
    r"(?P<val>(?(q)(?:(?!(?P=q))[^\r\n])+|(?![\"'])\S+))"
    # A quote left open (a truncated line) takes the value to the end of the line.
    r"(?P<post>(?(q)(?:(?P=q)|(?=[\r\n]|\Z))|))",
    re.IGNORECASE,
)
_URL_USERINFO_RX = re.compile(r"(?i)(\b[a-z][a-z0-9+.-]*://[^/\s:@]+:)([^/\s@]+)(@)")
_BEARER_RX = re.compile(r"(?i)(\bbearer\s+)([A-Za-z0-9._~+/=-]{8,})")

# A name is secret when ANY of its words is a secret word (`SECRET_KEY_BASE`, `DB_PASSWORD_PROD`,
# `client_secret`), unless its LAST word names something ABOUT the secret rather than the secret
# itself (`API_KEY_ID`, `PASSWORD_FILE`, `password_policy`, `token_count`, `credential.helper`).
_SECRET_WORDS = frozenset({
    "pass", "passwd", "password", "passphrase", "pwd", "secret", "token", "credential",
    "credentials", "apikey", "accesskey", "privatekey", "secretkey",
})
# The same, run together into one word (PGPASSWORD, clientsecret, NPMTOKEN). A bare "pass" or
# "pwd" suffix counts only in an all-capitals environment name (DBPASS, DBPWD), where BYPASS and
# OLDPWD are the exceptions; in ordinary words it would take bypass and compass along.
_SECRET_SUFFIXES = ("password", "passwd", "passphrase", "secret", "apikey", "accesskey",
                    "privatekey", "secretkey", "token", "credential", "credentials")
_UPPER_SUFFIXES = ("PASS", "PWD")
_UPPER_NOT_SECRET = frozenset({"PASS", "PWD", "BYPASS", "OLDPWD"})
# `key` is a secret word only after one of these (`api_key`, `access-key`, `Private key`).
_KEY_QUALIFIERS = frozenset({"api", "access", "private", "secret"})
# "pass" before one of these is a mode, not a password (`PASS_THROUGH`).
_PASS_MODES = frozenset({"through", "thru"})
# Last words that make the name about a secret rather than the secret: an identifier or a
# location, a setting, a measure. `key` is not here: `SECRET_KEY` is the secret.
_NON_SECRET_TAILS = frozenset({
    "id", "ids", "file", "files", "path", "dir", "url", "uri", "host", "port", "user",
    "username", "name", "names", "policy", "count", "helper", "helpers", "type", "types", "env",
    "len", "length", "expiry", "expires", "ttl", "timeout", "size", "mode", "cap", "limit",
    "budget", "usage", "kind", "format", "prefix", "suffix", "pattern", "patterns", "regex",
    "rx", "re", "hint", "label", "field", "fields", "header", "store", "source", "provider",
    "manager", "check", "checks", "rule", "rules", "shape", "min", "max", "floor", "ceiling",
    "rate", "version", "enabled", "required", "set", "exists", "index", "list", "map",
})
# A name of this many words is a slug or a sentence (a memory index line, a heading), not a
# variable: only its last word can make it secret, as in any other prose.
_SLUG_WORDS = 6
# Names that carry a secret word and are not one: the shell's working-directory variables hold a
# path, and NOPASSWD is a sudoers tag.
_NOT_SECRET_NAMES = frozenset({"PWD", "OLDPWD", "NOPASSWD"})
_CAMEL_RX = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")
# A value that only POINTS at a secret: a variable (`$DB_PASSWORD`, `${TOKEN}`), a command
# substitution (`$(sudo cat keyfile)`) or a placeholder (`<token>`, also inside prose punctuation
# such as a closing backtick). Lowercase after a bare `$` is left alone, since a password may well
# start with one.
_REFERENCE_VALUE_RX = re.compile(r"\$(?:\{|\(|[A-Z_][A-Z0-9_]*\b)|<[^<>\s]+>[`'\",;:.)\]}]*$")


def _key_material(body):
    """Count the base64 characters in the whole base64 lines of an unterminated block's body."""
    total = 0
    for line in _KEY_LINE_SPLIT_RX.split(body):
        m = _BASE64_LINE_RX.fullmatch(line)
        if m:
            total += len(m.group(1))
    return total


def _is_real_body(body):
    """A complete block's body is real key material unless it is elided ("...") or too short.

    A body with a "..." truncation marker or too little base64 is an illustrative example (a
    tutorial's elided key), which the commit gate must not block on.
    """
    return "..." not in body and len(re.sub(r"[^A-Za-z0-9+/=]", "", body)) > _MIN_KEY_MATERIAL


def _mask_complete_blocks(text):
    """Overwrite every complete block with filler of the same length, keeping offsets valid."""
    return PRIVATE_KEY_RX.sub(lambda m: "#" * len(m.group(0)), text)


def real_private_key_blocks(text):
    """Yield each private key block that carries real key material.

    Complete blocks come first; a BEGIN line with no END (a truncated key) is then looked for in
    what is left, so a complete block is never counted twice.
    """
    for m in PRIVATE_KEY_RX.finditer(text):
        if _is_real_body(m.group(1)):
            yield m
    if "-----BEGIN " not in text:
        return
    for m in UNTERMINATED_PRIVATE_KEY_RX.finditer(_mask_complete_blocks(text)):
        if _key_material(m.group(1)) > _MIN_KEY_MATERIAL:
            yield m


def find_secret_labels(text):
    """Return the label of every known token format present in `text` (a label per format)."""
    return list(dict.fromkeys(label for rx, label in TOKEN_PATTERNS if rx.search(text)))


def _name_words(name):
    """Split a variable or label name into lowercase words at separators and camelCase humps."""
    words = []
    for part in re.split(r"[ _.-]+", name):
        if part.isupper() or not any(c.isalpha() for c in part):
            words.append(part.lower())
        else:
            words.extend(w.lower() for w in _CAMEL_RX.findall(part))
    return [w for w in words if w]


def _secret_words(name):
    """The secret words `name` carries, in order; empty when it names no secret.

    Empty too when its last word names something about a secret (`_NON_SECRET_TAILS`), and for a
    slug-length name whose last word is not itself secret.
    """
    parts = [p for p in re.split(r"[ _.-]+", name) if p]
    if not parts or parts[-1] in _NOT_SECRET_NAMES:
        return []
    words = _name_words(name)
    if not words or words[-1] in _NON_SECRET_TAILS:
        return []
    found = []
    for i, word in enumerate(words):
        following = words[i + 1] if i + 1 < len(words) else ""
        if word == "pass" and following in _PASS_MODES:
            continue
        if word in _SECRET_WORDS or word.endswith(_SECRET_SUFFIXES):
            found.append(word)
        elif word == "key" and i and words[i - 1] in _KEY_QUALIFIERS:
            found.append("key")
    found.extend(p.lower() for p in parts
                 if p.isupper() and p.endswith(_UPPER_SUFFIXES) and p not in _UPPER_NOT_SECRET)
    if len(words) >= _SLUG_WORDS and words[-1] not in found and not (
            words[-1] == "key" and "key" in found):
        return []
    return found


def _redact_named_value(m):
    """Replace the value of a secret-named assignment; None to leave the match alone.

    A number after a name whose only secret word is "token" is a count (`max_token: 800`,
    `access_token_expires_in: 3600`), which an LLM tool's output is full of; a reference to a
    secret carries none.
    """
    value = m.group("val")
    if value.startswith(REDACTED) or _REFERENCE_VALUE_RX.match(value):
        return None
    found = _secret_words(m.group("name"))
    if not found or (value.isdigit() and all(w.endswith("token") for w in found)):
        return None
    return m.group("pre") + REDACTED + m.group("post")


def _redact_group_2(m):
    """Keep group 1 (the label, name or scheme) and anything after group 2; drop group 2.

    Returns None when group 2 already starts with the marker, so a value an earlier pass
    redacted is neither marked nor counted twice.
    """
    if m.group(2).startswith(REDACTED):
        return None
    tail = m.group(3) if m.re.groups >= 3 else ""
    return m.group(1) + REDACTED + tail


# The value rules, in redaction order: each is a regex and a builder that returns the
# replacement, or None to leave that match alone. redact() applies them and holds_a_credential()
# asks the same builders, so a rule can never be in one and missing from the other.
_VALUE_RULES = (
    (_URL_USERINFO_RX, _redact_group_2),
    (_BEARER_RX, _redact_group_2),
    (_NAMED_VALUE_RX, _redact_named_value),
)


def holds_a_credential(text):
    """True when `text` carries a secret VALUE rather than merely discussing one."""
    if find_secret_labels(text) or next(real_private_key_blocks(text), None):
        return True
    return any(build(m) is not None for rx, build in _VALUE_RULES for m in rx.finditer(text))


def redact(text, extra_literals=()):
    """Replace every secret value in `text` with `[REDACTED]`; return (text, count).

    Everything around a secret is kept - the label, the variable name, the URL's host, a quoted
    value's quotes - because that is the context a classifier needs to judge the text. Private key
    blocks are replaced whole, markers included, since even an elided example has no value to a
    reader; a BEGIN line with no END is replaced together with the key lines that follow it.
    Aggressive by design: a false positive costs one word of context, a false negative sends a
    live credential to a third party.
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
    text = _sub(UNTERMINATED_PRIVATE_KEY_RX,
                lambda m: REDACTED if _key_material(m.group(1)) else None, text)
    for rx, _label in TOKEN_PATTERNS:
        text = _sub(rx, lambda m: REDACTED, text)
    for rx, build in _VALUE_RULES:
        text = _sub(rx, build, text)
    return text, count
