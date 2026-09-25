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


# --- review findings: leaks and over-matches ---------------------------------------------------

V = "hunter2Xq9"
UUID = "3f1c9a7e-2b44-4d1e-9a51-0c6b8e2f7d11"
B64_RUN = "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7"


@pytest.mark.parametrize("line, value", [
    # Any *_PWD name holds a password; only the WHOLE names PWD and OLDPWD are the shell's paths.
    ("DB_PWD=" + V, V),
    ("MYSQL_PWD=" + V, V),
    ("export MYSQL_PWD='" + V + "'", V),
    ("ROOT_PWD=" + V, V),
    ("docker run -e MYSQL_PWD=" + V + " img", V),
    # A dollar sign followed by a capital is a variable only when the WHOLE value is the reference.
    ("DB_PASSWORD=$P@ssw0rd99", "$P@ssw0rd99"),
    ("password: $X!" + V, "$X!" + V),
    ("PASSWORD=$ABC#123def", "$ABC#123def"),
    # Vault's AppRole secret_id is the credential, not an identifier of one.
    ("VAULT_SECRET_ID=" + UUID, UUID),
    ("vault write auth/approle/login role_id=abc secret_id=" + UUID, UUID),
    # A long run of digits is a token, not a count.
    ("GITHUB_TOKEN=" + "1234567890" * 2 + "123456", "1234567890" * 2 + "123456"),
    ("API_TOKEN=982734982374982374", "982734982374982374"),
    # An upper-case environment name is a variable however many words it has.
    ("GOOGLE_OAUTH_CLIENT_SECRET_PROD_EU=" + V, V),
    ("COMPANY_PROD_DB_ADMIN_PASSWORD_OVERRIDE=" + V, V),
    # JSON escaped inside a string (curl -d, a log line), and a quote escaped inside a value.
    ('curl -d "{\\"password\\": \\"' + V + '\\"}"', V),
    ('"{\\"password\\":\\"' + V + '\\"}"', V),
    ('{"password": "ab\\"cd-' + V + '"}', "cd-" + V),
    ('"{\\"password\\":\\"ab\\\\\\"cd-' + V + '\\"}"', "cd-" + V),
    # Keys named by what they do.
    ("ENCRYPTION_KEY=" + V + "abcdef", V),
    ("SIGNING_KEY=" + V, V),
    ("MASTER_KEY=" + V, V),
    ("SSH_KEY=" + V, V),
    ("DEPLOY_KEY=" + V, V),
    ("JWT_KEY=" + V, V),
    ("HMAC_KEY=" + V, V),
    ("jwt_signing_key: " + V, V),
    ("AZURE_STORAGE_ACCOUNT_KEY=" + V, V),
    # A password passed as a separate command-line argument.
    ("mysqldump --password " + V + " db", V),
    ("app --api-key " + V + " run", V),
    ("sshpass -p " + V + " ssh admin@host", V),
    ("sshpass -p" + V + " ssh admin@host", V),
    ("mysql -u root -p" + V + " appdb", V),
    # GitHub's `token` Authorization scheme, and a session cookie.
    ("Authorization: token " + V + "abcdef", V),
    ('curl -H "Authorization: token ' + V + 'abcdef" https://api.github.com', V),
    ("Cookie: session=" + V, V),
    ("Cookie: theme=dark; session=" + V, V),
    ("Set-Cookie: sid=" + V + "; Path=/; HttpOnly", V),
    # A dotted value is an attribute reference only behind a code receiver.
    ("DB_PASSWORD=super.secret", "super.secret"),
    ("export SECRET_KEY=django.secret", "django.secret"),
    ("POSTGRES_PASSWORD: my.secret", "my.secret"),
    ("password: s3cr3t.token", "s3cr3t.token"),
    ("api_key=prod.apikey", "prod.apikey"),
    # The kebab-case slug exemption covers only a qualified `key`, never a real secret word.
    ('"db-admin-password-prod": "' + V + '"', V),
    # A reference followed by anything but a path is not a reference.
    ("DB_PASSWORD=$ABC!" + V, "$ABC!" + V),
])
def test_review_findings_secret_values_are_redacted(line, value):
    text, n = sp.redact(line)
    assert value not in text and n >= 1, text
    assert sp.holds_a_credential(line), line


def test_a_flattened_truncated_key_on_one_line_is_redacted():
    line = "PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY----- " + B64_RUN + " " + B64_RUN
    text, n = sp.redact(line)
    assert B64_RUN[:20] not in text and n >= 1, text
    bare = "-----BEGIN RSA PRIVATE KEY----- " + B64_RUN + " " + B64_RUN[:30]
    text, n = sp.redact("see " + bare + " end")
    assert B64_RUN[:20] not in text and n == 1, text
    assert len(list(sp.real_private_key_blocks(bare))) == 1


def test_an_openai_none_key_is_found_and_redacted():
    key = "sk-" + "None-" + "Ab1_" * 12
    assert sp.find_secret_labels("x " + key) == ["OpenAI-style key"]
    text, n = sp.redact("x " + key + " y")
    assert key not in text and n == 1


@pytest.mark.parametrize("line", [
    "passwd:         files systemd",
    "shadow: files",
    "PASS_MAX_DAYS=99999",
    "PASS_WARN_AGE=7",
    "password_changed_at: 2024-01-02",
    "token_expires_at: 2024-01-02T00:00",
    "TOKEN_LIFETIME=3600s",
    "token_refresh_interval: 5m",
    "token_endpoint: https://login.example.com/oauth2/token",
    "TOKEN_AUDIENCE=api://default",
    "credential_process = /usr/bin/aws-vault",
    "use_token_auth: true",
    "SECRET_KEY_ROTATION: enabled",
    "secret_scanning: enabled",
    "TokenCredential: DefaultAzureCredential",
    "GIT_ASKPASS=/usr/bin/true git fetch",
    "PASSWORD_HASHERS=django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "GITHUB_TOKEN_PATH=/home/u/.tok",
    "MAX_TOKEN_COUNT=4096",
    "PASS_THROUGH=1",
    "max_tokens: 100000",
    "SECRET_KEY_ID=abc123",
    "TOKEN_ID=abc123",
    # A secret-named flag that takes no value, or a value that is not the secret.
    "echo x | docker login --username u --password-stdin registry.example.com",
    "tool --token-file /run/tok",
    "ansible-playbook --ask-pass site.yml",
    "pg_dump --no-password db1",
    # -p is a port, a parent flag or a publish flag everywhere but sshpass and mysql.
    "ssh -p 2222 admin@host",
    "mkdir -p " + V,
    "docker run -p 8080:80 img",
    "psql -h db -p 5432 -U app",
    "mysql -u root -p appdb",
    # The word token in prose is not the Authorization scheme.
    "the token abcdefghijklmnop was rotated",
    # Found by replaying real transcripts: a wait flag takes a duration, a cookie header in a
    # prose code span holds a placeholder and ends at its backtick.
    "launch detached with `--wait-for-token 43200`.",
    "carries the wait behind `--wait-for-token SECONDS`, defaulting to 0",
    "`Cookie: session=<x>` and `Cookie: session=...` are missed; only `--password=x` works",
    "a count of `access_token_expires_in: 3600`.",
    "run --log-dir $R/logs --credentials $R/fixtures/creds.json",
    '"proxmox-install-ssh-key-pmxcfs": "When installing an SSH key on a node, write it whole"',
    "API-Token auf der Maschine, nur den SSH-Key: den legt das Skript an",
    "SSH_ASKPASS=/tmp/ap.sh SSH_ASKPASS_REQUIRE=force ssh host",
    # A reference is still a reference, braces and trailing punctuation included.
    "export DB_PASSWORD=$VAULT_DB_PASSWORD;",
    "TOKEN=${A}${B}",
])
def test_review_findings_non_secrets_are_left_alone(line):
    assert sp.redact(line) == (line, 0), line
    assert not sp.holds_a_credential(line), line


# Each case is (prefix, repeated unit, suffix): the unit is the part whose repeat count drives
# the input size, so the same shape can be built at two sizes and compared for GROWTH rather than
# timed once against a fixed ceiling - a shared CI runner is not a fixed clock, and a flat 0.5s
# wall-clock budget failed on ubuntu-latest/windows-latest at 0.51s for a run that took 0.11s
# locally, with nothing quadratic in the code.
_ADVERSARIAL_CASE_SHAPES = {
    "escaped_json_backslash_run": ('\\"password\\": \\"', "\\\\", ""),
    "long_password_flag_run": ("", "--password ", ""),
    "long_sshpass_run": ("", "sshpass ", ""),
    "long_mysql_dash_p_run": ("", "mysql -p", ""),
    "flattened_pem_run": ("-----BEGIN RSA PRIVATE KEY----- ", B64_RUN + " ", ""),
    # The consistently slowest shape in profiling (cProfile: linear, ~660k calls for 60k pairs):
    # each pair runs its own exemption checks (a placeholder, a cookie attribute, "cannot be a
    # secret"), which is the real cost of getting every pair right, not a regex backtracking on
    # this text - no cheaper equivalent pattern redacts the same spans.
    "many_cookie_pairs": ("Cookie: ", "a=b; ", ""),
    "long_authorization_token_run": ("", "Authorization: token ", ""),
    "long_password_dollar_run": ("password=$", "A", ""),
    "long_password_quote_backslash_run": ('password: "', "\\", ""),
    # A long hyphenated run: the pre-7.23.2 scheme regex started at every \b, so it rescanned the
    # rest of the run from each hyphen - quadratic in the run's length (see CHANGELOG 7.23.2).
    "long_hyphenated_scheme_run": ("", "a-", "://x"),
    "long_api_key_dashes_run": ("", "--api-key-", " x"),
}


def _sized_case(prefix, unit, suffix, target_len):
    """Build `prefix + unit * n + suffix` with `n` chosen so the text is about `target_len` long."""
    count = max(1, target_len // len(unit))
    return prefix + unit * count + suffix


def _scan(text):
    sp.redact(text)
    sp.holds_a_credential(text)


def _fastest_of(text, scan=_scan, repeats=3):
    """The minimum of a few timed passes, which filters a transient scheduling stall without
    hiding real quadratic growth - a slow pass recurs on every repeat, a stall does not."""
    best = None
    for _ in range(repeats):
        start = time.monotonic()
        scan(text)
        elapsed = time.monotonic() - start
        best = elapsed if best is None else min(best, elapsed)
    return best


# The small arm must run long enough that scheduler noise is a small share of it. At a fixed
# 50k chars the fastest shape took ~10 ms on a macOS runner, where a few ms of jitter alone moved
# a linear scan's ratio to 8.03 and failed the bound. Doubling the size until the small arm takes
# this long keeps the ratio a measurement of growth rather than of noise.
_SMALL_ARM_FLOOR_S = 0.05
_START_LEN = 50_000
_MAX_SMALL_LEN = 1_600_000


def _growth_ratio(prefix, unit, suffix, scan=_scan):
    """Time `scan` on the shape at a calibrated size n and at 4n; return (t_n, t_4n)."""
    length = _START_LEN
    t_n = _fastest_of(_sized_case(prefix, unit, suffix, length), scan)
    while t_n < _SMALL_ARM_FLOOR_S and length < _MAX_SMALL_LEN:
        length *= 2
        t_n = _fastest_of(_sized_case(prefix, unit, suffix, length), scan)
    t_4n = _fastest_of(_sized_case(prefix, unit, suffix, 4 * length), scan)
    return t_n, t_4n


# A 4x input costs a linear scan ~4x (measured 3.9-4.1x locally); a quadratic scan costs ~16x.
# 8 sits well clear of both, so it survives a noisy shared runner without going blind to the
# defect it exists to catch.
_MAX_LINEAR_RATIO = 8


@pytest.mark.parametrize("shape", sorted(_ADVERSARIAL_CASE_SHAPES))
def test_adversarial_inputs_stay_linear(shape):
    prefix, unit, suffix = _ADVERSARIAL_CASE_SHAPES[shape]
    t_n, t_4n = _growth_ratio(prefix, unit, suffix)
    # A generous absolute backstop: on ANY runner this must never crawl, quadratic or not.
    assert t_4n < 10.0, (shape, t_4n)
    ratio = t_4n / t_n
    assert ratio < _MAX_LINEAR_RATIO, (shape, t_n, t_4n, ratio)


_PLANTED_BASE_S = 0.1


def _sleep_for(seconds):
    time.sleep(max(seconds, 0.0))


def test_growth_ratio_flags_a_planted_quadratic_and_passes_a_planted_linear():
    """The instrument must be able to fail: a scan whose cost grows with the square of the input
    has to land above the bound, and a linear one below it, through the same calibration.

    The planted cost starts at 100 ms, well above timer slack: a macOS runner's sleep overshoots
    by tens of ms, and with a 4 ms base that noise flattened the quadratic arm to a ratio of 4."""

    def quadratic(text):
        _sleep_for(_PLANTED_BASE_S * (len(text) / _START_LEN) ** 2)

    def linear(text):
        _sleep_for(_PLANTED_BASE_S * (len(text) / _START_LEN))

    q_n, q_4n = _growth_ratio("", "a", "", scan=quadratic)
    l_n, l_4n = _growth_ratio("", "a", "", scan=linear)
    assert q_4n / q_n > _MAX_LINEAR_RATIO, (q_n, q_4n)
    assert l_4n / l_n < _MAX_LINEAR_RATIO, (l_n, l_4n)
