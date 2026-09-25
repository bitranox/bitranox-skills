"""Tests for secret_patterns: the one credential vocabulary shared by redaction and detection.

Redaction guards what leaves the machine (the classifier's egress), so each test plants a
realistic secret and requires that its VALUE is gone from the output, not merely that a marker
appeared somewhere.
"""

import time

import pytest

import secret_patterns as sp

# Assembled at runtime so this file never holds a literal that a secret scanner flags.
GHP = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
SK_ANT = "sk-ant-" + "api03-" + "x" * 30
AKIA = "AKIA" + "ABCDEFGHIJKLMNOP"
PEM_BODY = "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7" * 3
PEM = "-----BEGIN RSA PRIVATE KEY-----\n" + PEM_BODY + "\n-----END RSA PRIVATE KEY-----"


def test_a_token_is_replaced_and_its_value_is_gone():
    text, n = sp.redact("push failed, token was %s, retry" % GHP)
    assert GHP not in text
    assert "[REDACTED]" in text
    assert n == 1
    assert text.startswith("push failed, token was ")


def test_every_known_token_shape_is_redacted():
    for secret in (GHP, SK_ANT, AKIA, "xoxb-" + "1234567890-abcdef"):
        text, n = sp.redact("value: " + secret)
        assert secret not in text, secret
        assert n >= 1


def test_a_private_key_block_is_redacted_whole():
    text, n = sp.redact("cat id_rsa\n" + PEM + "\nok")
    assert PEM_BODY[:40] not in text
    assert "BEGIN RSA PRIVATE KEY" not in text
    assert text.startswith("cat id_rsa\n") and text.endswith("\nok")
    assert n == 1


def test_an_env_line_keeps_its_name_and_loses_its_value():
    text, _ = sp.redact("GITHUB_TOKEN=s3cr3tvalue123\nPATH=/usr/bin\nexport DB_PASSWORD='hunter2'")
    assert "s3cr3tvalue123" not in text and "hunter2" not in text
    assert "GITHUB_TOKEN=" in text and "DB_PASSWORD=" in text
    assert "PATH=/usr/bin" in text  # not a secret-bearing name


def test_a_labelled_value_loses_its_value():
    text, _ = sp.redact("Password: Tr0ub4dor&3 for the admin")
    assert "Tr0ub4dor&3" not in text
    assert text.startswith("Password: ")


def test_url_userinfo_password_is_redacted_but_the_host_stays():
    text, _ = sp.redact("clone https://bob:pa55word@git.example.com/repo.git")
    assert "pa55word" not in text
    assert "git.example.com/repo.git" in text


def test_a_bearer_header_value_is_redacted():
    text, _ = sp.redact('curl -H "Authorization: Bearer abcDEF123456789xyz" https://x')
    assert "abcDEF123456789xyz" not in text


def test_extra_literals_are_redacted_even_without_a_known_shape():
    # The classifier's own API key has no public format; it is passed as a literal.
    key = "q" * 108
    text, n = sp.redact("the key is %s ok" % key, extra_literals=[key])
    assert key not in text and n == 1


def test_prose_that_only_mentions_secrets_is_untouched():
    prose = "Never commit a password or a token; load the api key from a keyfile instead."
    assert sp.redact(prose) == (prose, 0)


def test_a_non_secret_env_line_is_untouched():
    assert sp.redact("HOME=/home/x\nLANG=C.UTF-8") == ("HOME=/home/x\nLANG=C.UTF-8", 0)


def test_holds_a_credential_agrees_with_redaction():
    assert sp.holds_a_credential("x " + GHP)
    assert sp.holds_a_credential("Password: hunter2")
    assert not sp.holds_a_credential("never commit a password")


def test_find_secrets_labels_each_known_shape():
    labels = {label for label in sp.find_secret_labels("a %s b %s" % (GHP, AKIA))}
    assert labels == {"GitHub token", "AWS access key id"}


# --- token formats ------------------------------------------------------------------------------

ALNUM = "Ab3dE5fG7h" * 20
PGP = ("-----BEGIN PGP PRIVATE KEY BLOCK-----\n\n" + PEM_BODY
       + "\n-----END PGP PRIVATE KEY BLOCK-----")
ELIDED_PEM = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
# A BEGIN line and two key lines, as `head -3 id_rsa` or a capped tool output shows it.
TRUNCATED = "-----BEGIN RSA PRIVATE KEY-----\n" + PEM_BODY[:64] + "\n" + PEM_BODY[64:128]


@pytest.mark.parametrize("secret", [
    "sk-" + "proj-" + ALNUM[:30] + "_-" + ALNUM[:60],   # current OpenAI project key
    "sk-" + "svcacct-" + ALNUM[:30] + "-" + ALNUM[:40],  # service-account key
    "gh" + "o_" + ALNUM[:36],                             # GitHub OAuth token
    "gh" + "u_" + ALNUM[:36],                             # GitHub user-to-server token
    "gh" + "r_" + ALNUM[:36],                             # GitHub refresh token
    "glpat-" + ALNUM[:26],                                # GitLab token longer than 20
    "sk-" + "proj-" + ALNUM[:80],                         # project key, alphanumeric body
])
def test_current_token_formats_are_found_and_redacted(secret):
    assert sp.find_secret_labels("x " + secret + " y"), secret
    text, n = sp.redact("x " + secret + " y")
    assert secret not in text and n == 1, text


def test_a_legacy_openai_key_is_labelled_once():
    assert sp.find_secret_labels("sk-" + ALNUM[:48]) == ["OpenAI-style key"]


def test_an_anthropic_key_is_labelled_once_not_also_as_openai():
    assert sp.find_secret_labels(SK_ANT + "x" * 20) == ["Anthropic API key"]


def test_a_long_kebab_identifier_starting_sk_is_not_a_key():
    ident = "sk-" + "-".join(["learn"] * 12)
    assert sp.find_secret_labels(ident) == []


# --- private key blocks --------------------------------------------------------------------------


def test_a_pgp_private_key_block_is_found_and_redacted():
    assert len(list(sp.real_private_key_blocks(PGP))) == 1
    assert sp.holds_a_credential(PGP)
    text, n = sp.redact("gpg --export-secret-keys\n" + PGP + "\ndone")
    assert PEM_BODY[:40] not in text and n == 1
    assert text.endswith("\ndone")


def test_an_elided_example_before_a_real_key_does_not_hide_the_real_key():
    both = ELIDED_PEM + "\nthe real one:\n" + PEM
    assert len(list(sp.real_private_key_blocks(both))) == 1
    assert sp.holds_a_credential(both)


def test_an_elided_example_alone_is_not_a_real_key():
    assert list(sp.real_private_key_blocks(ELIDED_PEM)) == []
    assert not sp.holds_a_credential(ELIDED_PEM)


def test_a_key_body_longer_than_8000_chars_is_still_a_key():
    big = "-----BEGIN RSA PRIVATE KEY-----\n" + "A" * 9000 + "\n-----END RSA PRIVATE KEY-----"
    assert len(list(sp.real_private_key_blocks(big))) == 1
    text, _ = sp.redact(big)
    assert "A" * 100 not in text


def test_a_truncated_key_with_no_end_line_is_redacted():
    text, n = sp.redact("head -3 id_rsa\n" + TRUNCATED + "\n")
    assert PEM_BODY[:40] not in text and PEM_BODY[64:100] not in text
    assert text.startswith("head -3 id_rsa\n") and n == 1
    assert sp.holds_a_credential(TRUNCATED)
    assert len(list(sp.real_private_key_blocks(TRUNCATED))) == 1


def test_a_truncated_encrypted_key_is_redacted_past_its_armour_headers():
    head = ("-----BEGIN RSA PRIVATE KEY-----\nProc-Type: 4,ENCRYPTED\n"
            "DEK-Info: AES-128-CBC,0123456789ABCDEF\n\n" + PEM_BODY[:64])
    text, n = sp.redact(head)
    assert PEM_BODY[:40] not in text and n == 1


def test_a_truncated_key_inside_a_json_string_is_redacted():
    line = '{"private_key": "-----BEGIN PRIVATE KEY-----\\n' + PEM_BODY[:64] + "\\n" + PEM_BODY[64:100]
    text, n = sp.redact(line)
    assert PEM_BODY[:40] not in text and PEM_BODY[64:100] not in text, text
    assert n >= 1


def test_a_bare_begin_line_in_prose_is_neither_redacted_nor_a_key():
    prose = "A key file starts with -----BEGIN RSA PRIVATE KEY----- and nothing else here."
    assert sp.redact(prose) == (prose, 0)
    assert list(sp.real_private_key_blocks(prose)) == []


def test_a_truncated_key_with_too_little_material_is_not_a_committed_key():
    # Redaction takes any key line; the commit gate wants real material, as for a complete block.
    short = "-----BEGIN RSA PRIVATE KEY-----\n" + PEM_BODY[:40]
    assert list(sp.real_private_key_blocks(short)) == []
    assert sp.redact(short) == ("[REDACTED]", 1)


def test_a_complete_block_is_not_reported_twice_by_the_truncation_rule():
    assert len(list(sp.real_private_key_blocks(PEM))) == 1
    assert sp.redact(PEM)[1] == 1


def test_a_truncated_key_before_a_complete_one_counts_both():
    assert len(list(sp.real_private_key_blocks(TRUNCATED + "\n" + PEM))) == 2


def test_an_elided_body_long_enough_to_pass_is_still_an_example():
    # The "..." marker alone decides it: the body carries well over the minimum of base64.
    elided = ("-----BEGIN RSA PRIVATE KEY-----\n" + PEM_BODY[:80] + "\n...\n" + PEM_BODY[:80]
              + "\n-----END RSA PRIVATE KEY-----")
    assert list(sp.real_private_key_blocks(elided)) == []


# --- labelled values ------------------------------------------------------------------------------


@pytest.mark.parametrize("line, value", [
    ('{"password": "hunter2xyz"}', "hunter2xyz"),
    ("{'password': 'hunter2xyz'}", "hunter2xyz"),
    ('"SecretAccessKey": "wJalrXUtnFEMIK7MDENG"', "wJalrXUtnFEMIK7MDENG"),
    ("  POSTGRES_PASSWORD: hunter2xyz", "hunter2xyz"),
    ("docker run -e DB_PASSWORD=hunter2xyz img", "hunter2xyz"),
    ("PASSWD=hunter2xyz", "hunter2xyz"),
    ("PRIVATE_KEY=abcdef123456", "abcdef123456"),
    ("PGPASSWORD=hunter2xyz psql", "hunter2xyz"),
    ("SMTPPASS=hunter2xyz", "hunter2xyz"),
    # The secret word need not be the last one.
    ("SECRET_KEY_BASE=abc123def", "abc123def"),
    ("DB_PASSWORD_PROD=hunter2xyz", "hunter2xyz"),
    ("GITHUB_TOKEN_2=hunter2xyz", "hunter2xyz"),
    ("client_secret_value: hunter2xyz", "hunter2xyz"),
    ("NPMTOKEN=hunter2xyz", "hunter2xyz"),
    ("DBPWD=hunter2xyz", "hunter2xyz"),
    ("GOOGLECREDENTIALS=hunter2xyz", "hunter2xyz"),
    ("spring.datasource.password=hunter2xyz", "hunter2xyz"),
    ("X-Api-Key: hunter2xyz", "hunter2xyz"),
    ("api key = hunter2xyz", "hunter2xyz"),
    ("GET /v1/items?token=hunter2xyz HTTP/1.1", "hunter2xyz"),
    ('password: "two words"', "two words"),
    ('"password": "cut off here', "cut off here"),
])
def test_structured_and_mid_line_secret_values_are_redacted(line, value):
    text, n = sp.redact(line)
    assert value not in text and n >= 1, text
    assert sp.holds_a_credential(line), line


def test_a_quoted_value_keeps_its_quotes_and_the_name():
    assert sp.redact('{"password": "hunter2xyz", "user": "bob"}') == (
        '{"password": "[REDACTED]", "user": "bob"}', 1)


@pytest.mark.parametrize("line", [
    '"input_tokens": 1234',
    "max_tokens: 800",
    "MAX_TOKENS=800",
    "token_count: 800",
    "max_token: 800",
    "password_policy: strict",
    "git -c credential.helper='!gh auth git-credential' push",
    "user ALL=(ALL) NOPASSWD: ALL",
    # A memory slug followed by its hook line: a sentence, not a variable.
    "feedback-masking-a-secret-with-var-fallback-leaks-its-value: When masking",
    "semdex-mcp-server-surface-and-where-its-token-usage-lives: When running",
    "chunker-semantic-no-max-token-enforcement: When using",
    # A secret word followed by a tail naming something ABOUT the secret.
    "API_KEY_ID=AKIDEXAMPLE123",
    "PASSWORD_FILE=/run/secrets/x",
    "TREE_DENSITY_TOKENS=3",
    "_BYPASS_ENV=1",
    "credential.helper=store",
    "token_type: bearer",
    "IOCTL_ATA_PASS_THROUGH_DIRECT = 0x4D02C",
    "TREE_DENSITY_TOKENS = (1, 2)",
    "_BYPASS_ENV = 'X'",
    "CHOICE_BYPASS = 3",
    "compass: north",
    "PWD=/home/x",
    "OLDPWD=/tmp",
    "export PWD=/home/x",
    "the password policy is strict",
    "bypass=1",
    '"passed": 12',
    "tokenizer: cl100k",
    "sort_key: name",
    '"password": ""',
    "if password == other:",
    "let t = Token::new(1);",
])
def test_counts_working_dirs_and_prose_are_not_secrets(line):
    assert sp.redact(line) == (line, 0), line
    assert not sp.holds_a_credential(line), line


def test_a_token_name_with_a_non_numeric_value_is_still_a_secret():
    # The count exemption is for numbers only; the same name with a token-like value is redacted.
    assert sp.redact("max_token: abc123def")[1] == 1


@pytest.mark.parametrize("line", [
    'PGPASSWORD="$(sudo cat /etc/pg/root.pw)" psql',
    "export DB_PASSWORD=$VAULT_DB_PASSWORD",
    "token=${GH_TOKEN:-unset}",
    "GH_TOKEN=<invalid>",
    "while `DB_PASSWORD=<value>` is the secret itself",
])
def test_a_value_that_only_points_at_a_secret_is_not_one(line):
    assert sp.redact(line) == (line, 0), line
    assert not sp.holds_a_credential(line), line


def test_a_literal_password_that_starts_with_a_dollar_is_still_redacted():
    text, n = sp.redact("password=$ecret1x")
    assert "$ecret1x" not in text and n == 1


@pytest.mark.parametrize("line", [
    # A function word after a prose label: "pass" the noun, not a password. Measured: 5 of the 20
    # memory facts recall withheld were exactly this shape.
    "they share one pass: the loop is HaliHaltSystem",
    "give that bucket its OWN pass: a list built by iterating",
    "indistinguishable from a clean pass: it is the",
    "run on the next pass: one that reads the new state",
    # A value a tool already masked, or a one-character placeholder.
    '"authToken": "[scrubbed]"',
    "password: ***",
    "DB_PASSWORD=********",
    '{"password": "***REDACTED***"}',
    '{"auth": {"token": "T"}}',
    # A type annotation names the field's type, not its value.
    "a pydantic `password: str` field",
    "token: Optional[str] = None",
    "smtp_password: SecretStr",
    # A dotted reference whose attribute names the secret it passes along.
    "ConfMail(smtp_password=self.smtp_password)",
    "client(token=args.token)",
    "api_key=settings.OPENAI_API_KEY",
    # A label inside one string literal whose "value quote" is that literal's own closing quote.
    'print("PASS: " if ok else "FAIL: ")',
    "x = 'token: ' + name",
])
def test_values_that_cannot_be_a_secret_are_left_alone(line):
    assert sp.redact(line) == (line, 0), line
    assert not sp.holds_a_credential(line), line


@pytest.mark.parametrize("line, value", [
    # Controls for each exemption above: the nearest REAL secret keeps being caught.
    ("user bob pass: hunter2", "hunter2"),
    ("Pass: the2nd", "the2nd"),
    ('{"token": "Tx9"}', "Tx9"),
    ("DB_PASSWORD=x1*x2*x3", "x1*x2*x3"),
    ("password: string4u", "string4u"),
    ("password=hunter.two", "hunter.two"),
    ("password=self.hunter2", "self.hunter2"),
    ('x = "token: abc123def"', "abc123def"),
    ('{"password": "hunter2xyz"}', "hunter2xyz"),
    ("print('DB_PASSWORD=\"hunter2xyz\"')", "hunter2xyz"),
])
def test_the_nearest_real_secret_to_each_exemption_is_still_redacted(line, value):
    text, n = sp.redact(line)
    assert value not in text and n >= 1, text
    assert sp.holds_a_credential(line), line


@pytest.mark.parametrize("line, value", [
    ("Authorization: Basic dXNlcjpwYXNzd29yZA==", "dXNlcjpwYXNzd29yZA=="),
    ("curl -H 'Authorization: Basic YWRtaW46aHVudGVyMg==' https://x", "YWRtaW46aHVudGVyMg=="),
    ('{"Authorization": "Basic dXNlcjpwYXNz"}', "dXNlcjpwYXNz"),
    ("authorization: basic dXNlcjpwYXNz", "dXNlcjpwYXNz"),
])
def test_a_basic_auth_credential_is_redacted_and_detected(line, value):
    # base64 of "user:password" is the password itself, one decode away.
    text, n = sp.redact(line)
    assert value not in text and n == 1, text
    assert "Basic" in text or "basic" in text          # the scheme stays as context
    assert sp.holds_a_credential(line), line


@pytest.mark.parametrize("line", [
    "basic functionality works",
    "Basic setup of the proxy",
    "we use basic auth here",
    "Basic dGVzdHRlc3Q=",             # base64 of "testtest": no user:password colon
    "the basic ABCDEFGHIJKL keys",    # base64-ish, decodes to binary
])
def test_the_word_basic_before_anything_else_is_not_a_credential(line):
    assert sp.redact(line) == (line, 0), line
    assert not sp.holds_a_credential(line), line


# --- detection and redaction agree ----------------------------------------------------------------


def test_a_bearer_value_is_a_credential_for_detection_too():
    line = 'curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9abc" https://x'
    assert sp.redact(line)[1] == 1
    assert sp.holds_a_credential(line)


def test_every_redaction_pattern_is_also_a_detection_pattern():
    # One shared list, so a pattern added to redaction cannot be missing from detection.
    for line in ('"password": "x1y2z3"', "DB_TOKEN=abc123", "https://u:pw@h/x",
                 "Authorization: Bearer abcdefgh12345", "PWD=/home/x", "max_tokens: 800"):
        assert (sp.redact(line)[1] > 0) == sp.holds_a_credential(line), line


def test_a_value_redacted_by_an_earlier_pass_is_counted_once():
    assert sp.redact("API_TOKEN=" + GHP) == ("API_TOKEN=[REDACTED]", 1)


def test_a_long_run_of_name_characters_is_scanned_in_linear_time():
    start = time.monotonic()
    for text in ("key" * 50000, "x_token" * 20000 + ":", "PASSWORD" * 20000):
        sp.redact(text)
        sp.holds_a_credential(text)
    assert time.monotonic() - start < 5
