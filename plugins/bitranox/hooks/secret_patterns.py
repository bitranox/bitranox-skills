"""The credential vocabulary shared by every hook that must recognise a secret.

Three callers need the same answer to "is this a secret?" and used to carry three copies:
repo-gate blocks a commit that holds one, recall-memory withholds a note that holds one, and the
classifier REDACTS one before text leaves the machine. One definition keeps a pattern added for
one of them from being silently missing in the others.

The test is always a VALUE, never a word: "never commit a password" names the concept and
carries nothing, while `Password: <value>`, `DB_PASSWORD=<value>`, `{"password": "<value>"}`,
`Authorization: Basic <base64 of user:password>` and `scheme://user:pw@host` are the secret itself.
A value that cannot be a secret whatever the name before it - a function word in prose, a mask a
tool already applied, a type annotation, an attribute reference - is not one.

Pure standard library.
"""

import base64
import binascii
import re

__all__ = [
    "FLATTENED_PRIVATE_KEY_RX",
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
    # admin / owner-less ("None") keys whose bodies carry "-" and "_". Only the NAMED prefixes
    # admit those characters,
    # so a long kebab-case identifier that happens to start "sk-" is not a key, and sk-ant- keys
    # (matched above) never match here: "ant" is not one of the prefixes.
    (re.compile(r"\bsk-[A-Za-z0-9]{40,}\b"), "OpenAI-style key"),
    (re.compile(r"\bsk-(?:proj|svcacct|admin|None)-[A-Za-z0-9_-]{40,}"), "OpenAI-style key"),
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
# The same block flattened onto ONE line (a pasted key whose line breaks became spaces, a log
# field) and cut off before its END: group 1 is the run of space-separated base64 words. A word
# must be long enough that prose after a bare BEGIN line ("... KEY----- and nothing else") is
# never taken for key material.
FLATTENED_PRIVATE_KEY_RX = re.compile(_KEY_BEGIN + r"((?:[ \t]+[A-Za-z0-9+/=]{16,})+)")
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
#
# The quotes may themselves be backslash-escaped: JSON inside a string (`curl -d "{\"password\":
# \"x\"}"`, a log field) closes its value at `\"`, not at the bare quote. Inside a plainly quoted
# value an escaped quote (`\"`) is part of the value; inside an escaped one, an escaped backslash
# (`\\`) and a doubly escaped quote (`\\\"`) are. Otherwise the value's tail would leak past the
# first escape.
_QUOTED_VALUE = (
    r"(?(q)(?(bq)(?:\\\\\\(?P=q)|\\\\|(?!\\(?P=q))[^\r\n])+"
    r"|(?:\\[^\r\n]|(?!(?P=q))[^\r\n])+)"
)
# A quote left open (a truncated line) takes the value to the end of the line.
_VALUE_CLOSE = r"(?P<post>(?(q)(?:(?(bq)\\)(?P=q)|(?=[\r\n]|\Z))|))"
_OPEN_QUOTE = r"(?:(?P<bq>\\)?(?P<q>[\"']))?"
_NAMED_VALUE_RX = re.compile(
    r"(?P<pre>(?<![A-Za-z0-9_.-])"
    r"(?P<name>(?:[A-Za-z0-9_.-]+ )?"
    # A lookahead, which never backtracks, so a long run of name characters costs one pass.
    r"(?=[A-Za-z0-9_.-]*?(?:pass|pwd|secret|token|key|credential))[A-Za-z0-9_.-]+)"
    # `==` and `::` are a comparison and a path (`Token::new`), not an assignment.
    r"(?:\\?[\"'])?[ \t]*[:=](?![:=])[ \t]*" + _OPEN_QUOTE + r")"
    r"(?P<val>" + _QUOTED_VALUE + r"|(?![\"'])\S+))" + _VALUE_CLOSE,
    re.IGNORECASE,
)
# A secret passed as the NEXT argument of a long option (`--password x`, `--api-key x`). A value
# starting with a dash is the next option, and `_redact_flag_value` drops the switches that take
# no value (`--ask-pass`, `--password-stdin`). No real option name is longer than 80 characters,
# and the cap keeps a pathological run from being split into words.
_FLAG_VALUE_RX = re.compile(
    r"(?P<pre>(?<![A-Za-z0-9_.-])"
    r"(?P<name>--(?=[A-Za-z0-9-]{0,80}?(?:pass|pwd|secret|token|key|credential))"
    r"[A-Za-z0-9][A-Za-z0-9-]{0,80})"
    r"[ \t]+" + _OPEN_QUOTE + r")"
    r"(?P<val>" + _QUOTED_VALUE + r"|(?![\"'-])\S+))" + _VALUE_CLOSE,
    re.IGNORECASE,
)
# `-p` is a password only for two tools: sshpass takes it as the next argument or attached, the
# mysql family only attached (`-pSECRET`; `-p db` prompts and names a database). Everywhere else
# it is a port (ssh, psql), a parent flag (mkdir) or a publish flag (docker), so it is not a
# general rule. The option list before `-p` is bounded, which keeps the scan linear.
_CLI_PASSWORD_VALUE = r"(?P<val>'[^'\r\n]*'|\"[^\"\r\n]*\"|[^\s'\"]\S*)"
_SSHPASS_RX = re.compile(r"(?P<pre>\bsshpass(?:[ \t]+-[a-oq-zA-Z]\S*){0,4}[ \t]+-p[ \t]*)"
                         + _CLI_PASSWORD_VALUE)
_MYSQL_RX = re.compile(
    r"(?P<pre>\b(?:mysql|mysqldump|mysqladmin|mysqlimport|mysqlshow|mysqlcheck|mysqlpump|mysqlsh"
    r"|mariadb(?:-dump|-admin|-import|-check)?)(?:[ \t]+[^\s|;&]+){0,20}?[ \t]+-p)"
    + _CLI_PASSWORD_VALUE)
# The scheme starts only where a run of scheme characters starts: a `\b` start would rescan the
# rest of a long `a-b-c-...` run from every hyphen, which is quadratic in the run's length.
_URL_USERINFO_RX = re.compile(
    r"(?i)((?<![a-z0-9+.-])[a-z][a-z0-9+.-]*://[^/\s:@]+:)([^/\s@]+)(@)")
_BEARER_RX = re.compile(r"(?i)(\bbearer\s+)([A-Za-z0-9._~+/=-]{8,})")
# GitHub's own scheme, `Authorization: token <x>`. `token` is an ordinary word, so only after the
# header name.
_AUTH_TOKEN_RX = re.compile(
    r"(?i)(\bauthorization\\?[\"']?[ \t]*[:=][ \t]*\\?[\"']?token[ \t]+)([A-Za-z0-9._~+/=-]{8,})")
# A Cookie header carries session credentials in its `name=value` pairs; `_redact_cookies` drops
# every value but a Set-Cookie attribute's. The header ends at a quote or a backtick, so a header
# named in a prose code span does not reach into the sentence after it.
_COOKIE_RX = re.compile(r"(?i)(\b(?:set-)?cookie\\?[\"']?[ \t]*:[ \t]*)([^\r\n\"'\\`]+)")
# A pair name starts after a separator only, so a long run with no `=` is scanned once.
_COOKIE_PAIR_RX = re.compile(r"((?<![^;\s])[^=;\s]+=)([^;\s]+)")
_COOKIE_ATTRIBUTES = frozenset({
    "path", "domain", "expires", "max-age", "samesite", "secure", "httponly", "priority",
    "partitioned", "version", "comment",
})
# `Basic` is an ordinary word, so the candidate is only a credential when it DECODES to the
# `user:password` pair the scheme carries (see `_redact_basic`).
_BASIC_RX = re.compile(r"(?i)(\bbasic\s+)([A-Za-z0-9+/]{4,}={0,2})(?![A-Za-z0-9+/=])")

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
# ASKPASS (GIT_ASKPASS, SSH_ASKPASS) names the program that asks, not the password.
_UPPER_NOT_SECRET = frozenset({"PASS", "PWD", "BYPASS", "OLDPWD", "ASKPASS"})
# `key` is a secret word only after one of these (`api_key`, `access-key`, `Private key`,
# `ENCRYPTION_KEY`, `SSH_KEY`, `AZURE_STORAGE_ACCOUNT_KEY`): a key named by what it opens or signs.
_KEY_QUALIFIERS = frozenset({
    "api", "access", "private", "secret", "encryption", "decryption", "signing", "master", "ssh",
    "deploy", "jwt", "hmac", "account",
})
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
    # A time or a schedule, an OAuth setting, a program, and the class that hashes passwords.
    "at", "days", "age", "lifetime", "interval", "rotation", "endpoint", "audience", "issuer",
    "scope", "scopes", "process", "command", "cmd", "stdin", "hasher", "hashers",
})
# Vault's AppRole `secret_id` IS the credential: an "id" tail directly after "secret" is not an
# identifier of a secret, as `API_KEY_ID` and `TOKEN_ID` are.
_ID_TAILS = frozenset({"id", "ids"})
# A name of this many words is a slug or a sentence (a memory index line, a heading), not a
# variable: only its last word can make it secret, as in any other prose. An all-capitals
# environment name (GOOGLE_OAUTH_CLIENT_SECRET_PROD_EU) is a variable however long it is.
_SLUG_WORDS = 6
_ENV_NAME_RX = re.compile(r"[A-Z0-9_]*[A-Z][A-Z0-9_]*")
# A lower-case kebab-case name of four or more parts is a slug (a memory fact, a file stem, a
# JSON key such as `proxmox-install-ssh-key-pmxcfs`), however short.
_KEBAB_SLUG_RX = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+){3,}")
# Whole names that carry a secret word and are not one: the shell's working-directory variables
# hold a path, and NOPASSWD is a sudoers tag. Whole names only: DB_PWD and MYSQL_PWD are passwords.
_NOT_SECRET_NAMES = frozenset({"PWD", "OLDPWD", "NOPASSWD"})
_CAMEL_RX = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")
# A value that only POINTS at a secret: a variable (`$DB_PASSWORD`, `${TOKEN}`), a command
# substitution (`$(sudo cat keyfile)`) or a placeholder (`<token>`, also inside prose punctuation
# such as a closing backtick). Lowercase after a bare `$` is left alone, since a password may well
# start with one. A bare `$NAME` is a reference only when it is the WHOLE value (trailing prose
# punctuation aside), or the start of a path (`$HOME/.tok`): `$P@ssw0rd99` and `$ABC#123def` are
# passwords that start with a dollar.
_REFERENCE_VALUE_RX = re.compile(
    r"\$[{(]"
    r"|(?:\$[A-Z_][A-Z0-9_]*(?![A-Za-z0-9_])|\$\{[^{}\s]*\})+(?:/\S*|[`'\",;:.)\]}]*$)"
    r"|<[^<>\s]+>[`'\",;:.)\]}]*$")
# A long run of digits is a token (a Telegram, Discord or numeric API token); a short one after a
# token-only name is a count (`max_tokens: 800`).
_MAX_COUNT_DIGITS = 9
# A long option whose first word makes it a switch taking no value (`--ask-pass`, `--no-password`,
# `--with-token`) or one whose value is not the secret (`--wait-for-token 30`, a duration), and
# the words that follow a flag named in prose ("the --token flag").
_SWITCH_FLAG_WORDS = frozenset({
    "ask", "no", "prompt", "use", "show", "hide", "require", "read", "allow", "disable", "enable",
    "skip", "with", "without", "generate", "print", "stdin", "wait",
})
_FLAG_PROSE_WORDS = frozenset({
    "flag", "flags", "option", "options", "argument", "arguments", "arg", "args", "parameter",
    "parameters", "switch", "value", "values",
})
# The sources nsswitch.conf lists after its `passwd:` database.
_NSSWITCH_SOURCES = frozenset({
    "files", "systemd", "sss", "ldap", "nis", "nisplus", "compat", "db", "winbind", "altfiles",
    "cache", "extrausers", "usrfiles", "mymachines", "hesiod",
})

# Values that cannot be a secret whatever name precedes them. Each is a closed class, so no real
# credential falls into one: a label in prose followed by a function word ("one pass: the loop"),
# a mask a tool already applied, a type annotation (`password: str`), a switch setting, a
# credential class, and an attribute reference on a code receiver whose last name is itself the
# secret's name (`smtp_password=self.smtp_password`).
_PROSE_TRAILING = "`'\",;:.)]}"
_FUNCTION_WORDS = frozenset({
    "a", "an", "the", "it", "its", "is", "are", "was", "be", "this", "that", "these", "those",
    "one", "each", "every", "all", "any", "some", "no", "not", "and", "or", "but", "if", "then",
    "so", "to", "of", "in", "on", "at", "by", "for", "with", "as", "from", "into", "which", "who",
    "what", "when", "where", "how", "there", "here", "we", "you", "they", "he", "she",
    # German, which this workspace's prose is often written in ("nur den SSH-Key: den ...").
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "ist", "und", "oder",
    "nicht", "mit", "auf", "im", "wird", "sind",
})
_MASKED_VALUE_RX = re.compile(
    r"(?i)^(?:[*x\u2022#.]{3,}|\*{3,}[a-z_ ]*\*{3,}"
    r"|\[(?:redacted|scrubbed|masked|hidden|omitted|removed|filtered|sensitive)\])$")
_TYPE_NAME_RX = re.compile(
    r"(?i)^(?:str|string|int|integer|bytes|bool|boolean|float|number|any|none|null|object"
    r"|secret(?:str|bytes)|(?:optional|list|dict|tuple|set|sequence|mapping)\[.*\])$")
_DOTTED_REFERENCE_RX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
# A dotted value is an attribute reference only behind a code receiver (`self.smtp_password`,
# `settings.OPENAI_API_KEY`, `os.environ.TOKEN`); behind anything else (`super.secret`,
# `django.secret`, `s3cr3t.token`) it is a password that happens to hold a dot.
_CODE_RECEIVERS = frozenset({
    "self", "cls", "this", "args", "kwargs", "opts", "options", "settings", "config", "cfg",
    "conf", "os", "env", "environ", "ctx", "context", "request", "req", "params", "props", "app",
    "obj", "secrets", "vars", "inputs", "process", "creds", "cred", "credentials", "auth", "form",
    "data", "payload", "body", "conn", "client",
})
# A switch setting (`use_token_auth: true`, `secret_scanning: enabled`), and a credential CLASS
# (`TokenCredential: DefaultAzureCredential`) rather than a credential.
_SWITCH_VALUES = frozenset({
    "true", "false", "yes", "no", "on", "off", "enabled", "disabled", "enable", "disable",
})
_CREDENTIAL_CLASS_RX = re.compile(r"^[A-Z][A-Za-z0-9]*[a-z0-9]Credentials?$")


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

    Complete blocks come first; a BEGIN line with no END (a truncated key, on its own lines or
    flattened onto one) is then looked for in what is left, so a complete block is never counted
    twice. A BEGIN line is followed either by a line break or by a space, never both, so the two
    truncation shapes never count one block twice either.
    """
    for m in PRIVATE_KEY_RX.finditer(text):
        if _is_real_body(m.group(1)):
            yield m
    if "-----BEGIN " not in text:
        return
    rest = _mask_complete_blocks(text)
    for m in UNTERMINATED_PRIVATE_KEY_RX.finditer(rest):
        if _key_material(m.group(1)) > _MIN_KEY_MATERIAL:
            yield m
    for m in FLATTENED_PRIVATE_KEY_RX.finditer(rest):
        if len(re.sub(r"\s", "", m.group(1))) > _MIN_KEY_MATERIAL:
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
    slug-length name whose last word is not itself secret. `name` may carry one word before the
    variable (`export PWD`); the variable is the last space-separated part.
    """
    variable = name.rsplit(" ", 1)[-1]
    parts = [p for p in re.split(r"[ _.-]+", name) if p]
    if not parts or variable in _NOT_SECRET_NAMES:
        return []
    words = _name_words(name)
    if not words or _is_about_a_secret(words):
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
    if _reads_as_a_slug(variable, words, found) and words[-1] not in found and not (
            words[-1] == "key" and "key" in found):
        return []
    return found


def _is_about_a_secret(words):
    """True when the name's last word names something ABOUT a secret (`API_KEY_ID`), except the
    Vault `secret_id`, which is the credential itself."""
    if words[-1] not in _NON_SECRET_TAILS:
        return False
    return not (words[-1] in _ID_TAILS and len(words) > 1 and words[-2] == "secret")


def _reads_as_a_slug(variable, words, found):
    """True for a name long enough to be a slug or a sentence rather than a variable; an
    all-capitals environment name is a variable however many words it has.

    A shorter kebab-case slug counts only when its one secret word is a qualified `key`
    (`...-ssh-key-...`): a real secret word (`db-admin-password-prod`) keeps its name secret.
    """
    if _KEBAB_SLUG_RX.fullmatch(variable) and set(found) == {"key"}:
        return True
    return len(words) >= _SLUG_WORDS and not _ENV_NAME_RX.fullmatch(variable)


def _is_attribute_reference(core):
    """True for `receiver.attr` where the receiver is code and the attribute names a secret."""
    if not _DOTTED_REFERENCE_RX.match(core):
        return False
    receiver, attribute = core.split(".", 1)[0], core.rsplit(".", 1)[-1]
    return receiver.lower() in _CODE_RECEIVERS and bool(_secret_words(attribute))


def _cannot_be_a_secret(value):
    """True for a value in one of the closed classes above, which no credential belongs to.

    An unquoted value runs to the next whitespace, so it may carry the prose punctuation after
    it (`str`,); a bracket may also be the value's own (`[scrubbed]`), so both forms are tried.
    """
    for core in dict.fromkeys((value, value.rstrip(_PROSE_TRAILING))):
        if len(core) <= 1 or core.lower() in _FUNCTION_WORDS or core.lower() in _SWITCH_VALUES:
            return True
        if _MASKED_VALUE_RX.match(core) or _TYPE_NAME_RX.match(core):
            return True
        if _CREDENTIAL_CLASS_RX.match(core) or _is_attribute_reference(core):
            return True
    return False


def _opens_inside_the_names_literal(m):
    """True when the value's opening quote is really the CLOSING quote of a string literal the
    name itself sits in (`"PASS: " if ok else "FAIL: "`): the "value" is then the code between
    two literals, not a secret."""
    quote = m.group("q")
    start, end = m.start("name"), m.end("name")
    text = m.string
    # A backslash after the name is its own escaped closing quote (`\"password\": \"x\"`).
    return (bool(quote) and start > 0 and text[start - 1] == quote
            and text[end:end + 1] not in "\"'\\")


def _is_a_count(value, found):
    """A short number after a name whose only secret word is "token" is a count."""
    value = value.rstrip(_PROSE_TRAILING)
    return (value.isdigit() and len(value) <= _MAX_COUNT_DIGITS
            and all(w.endswith("token") for w in found))


def _is_an_nsswitch_source(m):
    """`passwd: files systemd` in nsswitch.conf lists where the passwd database lives."""
    return (m.group("name") == "passwd" and not m.group("q")
            and m.group("val") in _NSSWITCH_SOURCES)


def _redact_named_value(m):
    """Replace the value of a secret-named assignment; None to leave the match alone.

    A short number after a name whose only secret word is "token" is a count (`max_token: 800`,
    `access_token_expires_in: 3600`), which an LLM tool's output is full of; a reference to a
    secret carries none, and neither does a value that cannot be a secret at all.
    """
    value = m.group("val")
    if value.startswith(REDACTED) or _REFERENCE_VALUE_RX.match(value):
        return None
    if _cannot_be_a_secret(value) or _opens_inside_the_names_literal(m):
        return None
    found = _secret_words(m.group("name"))
    if not found or _is_a_count(value, found) or _is_an_nsswitch_source(m):
        return None
    return m.group("pre") + REDACTED + m.group("post")


def _redact_flag_value(m):
    """Replace the argument of a secret-named long option; None for a switch taking no value.

    The option must END in its secret word (`--password`, `--api-key`, not `--password-stdin`)
    and not start with a switch word (`--ask-pass`, `--no-password`); a flag named in prose
    ("the --token flag") is followed by a word about flags, not by a value.
    """
    if m.group("val").rstrip(_PROSE_TRAILING).lower() in _FLAG_PROSE_WORDS:
        return None
    words = _name_words(m.group("name"))
    found = _secret_words(m.group("name"))
    if not found or words[0] in _SWITCH_FLAG_WORDS:
        return None
    if words[-1] not in found and not (words[-1] == "key" and "key" in found):
        return None
    return _redact_named_value(m)


def _redact_cli_password(m):
    """Replace the `-p` password of sshpass or a mysql-family client; None for a reference."""
    value = m.group("val")
    core = value[1:-1] if value[:1] in "'\"" and len(value) > 1 else value
    if value.startswith(REDACTED) or _REFERENCE_VALUE_RX.match(core) or _cannot_be_a_secret(core):
        return None
    return m.group("pre") + REDACTED


def _redact_cookies(m):
    """Replace every cookie value in a Cookie / Set-Cookie header but an attribute's, a
    placeholder's (`session=<x>`) or one that cannot be a secret (`session=...`)."""
    changed = False

    def _pair(p):
        nonlocal changed
        name, value = p.group(1), p.group(2)
        if name[:-1].lower() in _COOKIE_ATTRIBUTES or value.startswith(REDACTED):
            return p.group(0)
        if _REFERENCE_VALUE_RX.match(value) or _cannot_be_a_secret(value):
            return p.group(0)
        changed = True
        return name + REDACTED

    header = _COOKIE_PAIR_RX.sub(_pair, m.group(2))
    return m.group(1) + header if changed else None


def _redact_group_2(m):
    """Keep group 1 (the label, name or scheme) and anything after group 2; drop group 2.

    Returns None when group 2 already starts with the marker, so a value an earlier pass
    redacted is neither marked nor counted twice.
    """
    if m.group(2).startswith(REDACTED):
        return None
    tail = m.group(3) if m.re.groups >= 3 else ""
    return m.group(1) + REDACTED + tail


def _redact_basic(m):
    """Replace a `Basic` credential; None unless the value decodes to `user:password`."""
    token = m.group(2)
    if token.startswith(REDACTED):
        return None
    try:
        decoded = base64.b64decode(token + "=" * (-len(token) % 4), validate=True).decode("utf-8")
    except (binascii.Error, ValueError):
        return None
    if ":" not in decoded or not decoded.isprintable():
        return None
    return m.group(1) + REDACTED


# The value rules, in redaction order: each is a regex and a builder that returns the
# replacement, or None to leave that match alone. redact() applies them and holds_a_credential()
# asks the same builders, so a rule can never be in one and missing from the other.
_VALUE_RULES = (
    (_URL_USERINFO_RX, _redact_group_2),
    (_BEARER_RX, _redact_group_2),
    (_AUTH_TOKEN_RX, _redact_group_2),
    (_BASIC_RX, _redact_basic),
    (_COOKIE_RX, _redact_cookies),
    (_SSHPASS_RX, _redact_cli_password),
    (_MYSQL_RX, _redact_cli_password),
    (_NAMED_VALUE_RX, _redact_named_value),
    (_FLAG_VALUE_RX, _redact_flag_value),
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
    text = _sub(FLATTENED_PRIVATE_KEY_RX, lambda m: REDACTED, text)
    for rx, _label in TOKEN_PATTERNS:
        text = _sub(rx, lambda m: REDACTED, text)
    for rx, build in _VALUE_RULES:
        text = _sub(rx, build, text)
    return text, count
