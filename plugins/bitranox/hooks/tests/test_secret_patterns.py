"""Tests for secret_patterns: the one credential vocabulary shared by redaction and detection.

Redaction guards what leaves the machine (the classifier's egress), so each test plants a
realistic secret and requires that its VALUE is gone from the output, not merely that a marker
appeared somewhere.
"""

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
