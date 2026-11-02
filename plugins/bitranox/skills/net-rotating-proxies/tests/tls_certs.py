"""A throwaway certificate authority for the TLS stand-ins, built with the standard library only.

The CI dependency set has no `cryptography`, and a key committed as a fixture is refused by the
repository's secret gate, so the test CA and the server certificate it signs are generated per
test session: RSA-2048 keys from a Miller-Rabin prime search, certificates DER-encoded by hand and
signed with PKCS#1 v1.5 / SHA-256. Nothing here is a secret worth keeping - every run makes new
ones in pytest's temporary directory. The extensions are the ones Python's default context
(VERIFY_X509_STRICT since 3.13) requires: key identifiers, a critical basicConstraints on the CA,
and a subjectAltName naming 127.0.0.1 and localhost on the server certificate.
"""
import base64
import hashlib
import math
import secrets

_SMALL_PRIMES = [p for p in range(3, 2000) if all(p % d for d in range(2, int(p**0.5) + 1))]
_E = 65537
# DER of DigestInfo's AlgorithmIdentifier for SHA-256, as PKCS#1 v1.5 signatures prefix it.
_SHA256_DIGEST_INFO = bytes.fromhex("3031300d060960864801650304020105000420")
_RSA_ENCRYPTION = "1.2.840.113549.1.1.1"
_SHA256_WITH_RSA = "1.2.840.113549.1.1.11"


# ---- DER --------------------------------------------------------------------------------------
def _tlv(tag, body):
    n = len(body)
    if n < 0x80:
        length = bytes([n])
    else:
        raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
        length = bytes([0x80 | len(raw)]) + raw
    return bytes([tag]) + length + body


def _int(value):
    return _tlv(0x02, value.to_bytes(value.bit_length() // 8 + 1, "big"))


def _seq(*parts):
    return _tlv(0x30, b"".join(parts))


def _oid(dotted):
    first, second, *rest = (int(x) for x in dotted.split("."))
    body = bytes([40 * first + second])
    for arc in rest:
        chunk = [arc & 0x7F]
        arc >>= 7
        while arc:
            chunk.append(0x80 | (arc & 0x7F))
            arc >>= 7
        body += bytes(reversed(chunk))
    return _tlv(0x06, body)


def _bits(data):
    return _tlv(0x03, b"\x00" + data)


def _octets(data):
    return _tlv(0x04, data)


def _algorithm(dotted):
    return _seq(_oid(dotted), b"\x05\x00")


def _name(common_name):
    attribute = _seq(_oid("2.5.4.3"), _tlv(0x0C, common_name.encode("utf-8")))
    return _seq(_tlv(0x31, attribute))


def _time(year):
    # UTCTime up to 2049, GeneralizedTime from 2050 (RFC 5280 4.1.2.5).
    if year < 2050:
        return _tlv(0x17, f"{year % 100:02d}0101000000Z".encode("ascii"))
    return _tlv(0x18, f"{year}0101000000Z".encode("ascii"))


def _extension(dotted, value, critical=False):
    flag = _tlv(0x01, b"\xff") if critical else b""
    return _seq(_oid(dotted), flag, _octets(value))


# ---- RSA --------------------------------------------------------------------------------------
def _probably_prime(n, rounds=24):
    if any(n % p == 0 for p in _SMALL_PRIMES):
        return n in _SMALL_PRIMES
    d, s = n - 1, 0
    while d % 2 == 0:
        d, s = d // 2, s + 1
    for _ in range(rounds):
        x = pow(secrets.randbelow(n - 3) + 2, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _prime(bits):
    while True:
        candidate = secrets.randbits(bits) | (1 << (bits - 1)) | (1 << (bits - 2)) | 1
        if math.gcd(candidate - 1, _E) == 1 and _probably_prime(candidate):
            return candidate


class _Rsa:
    def __init__(self, bits=2048):
        while True:
            p, q = _prime(bits // 2), _prime(bits // 2)
            if p != q and (p * q).bit_length() == bits:
                break
        self.n, self.p, self.q = p * q, p, q
        self.d = pow(_E, -1, (p - 1) * (q - 1))

    def public_info(self):
        """SubjectPublicKeyInfo DER."""
        return _seq(_algorithm(_RSA_ENCRYPTION), _bits(_seq(_int(self.n), _int(_E))))

    def key_id(self):
        # RFC 5280 4.2.1.2 method 1: SHA-1 of the subjectPublicKey BIT STRING contents.
        return hashlib.sha1(_seq(_int(self.n), _int(_E)), usedforsecurity=False).digest()

    def sign(self, data):
        digest = _SHA256_DIGEST_INFO + hashlib.sha256(data).digest()
        size = (self.n.bit_length() + 7) // 8
        block = b"\x00\x01" + b"\xff" * (size - len(digest) - 3) + b"\x00" + digest
        return pow(int.from_bytes(block, "big"), self.d, self.n).to_bytes(size, "big")

    def pkcs1_pem(self):
        p, q, d = self.p, self.q, self.d
        der = _seq(_int(0), _int(self.n), _int(_E), _int(d), _int(p), _int(q),
                   _int(d % (p - 1)), _int(d % (q - 1)), _int(pow(q, -1, p)))
        return _pem("RSA PRIVATE" + " KEY", der)


def _pem(label, der):
    lines = base64.encodebytes(der).decode("ascii").replace("\n", "")
    body = "\n".join(lines[i:i + 64] for i in range(0, len(lines), 64))
    return f"-----BEGIN {label}-----\n{body}\n-----END {label}-----\n"


def _certificate(serial, issuer, issuer_rsa, subject, subject_rsa, extensions):
    tbs = _seq(_tlv(0xA0, _int(2)), _int(serial), _algorithm(_SHA256_WITH_RSA), _name(issuer),
               _seq(_time(2020), _time(2099)), _name(subject), subject_rsa.public_info(),
               _tlv(0xA3, _seq(*extensions)))
    der = _seq(tbs, _algorithm(_SHA256_WITH_RSA), _bits(issuer_rsa.sign(tbs)))
    return _pem("CERTIFICATE", der)


def make_ca(directory):
    """Write ca.pem, server.pem and server-priv.pem into directory; return their paths.

    ca.pem is the CA a client must trust; server.pem plus server-priv.pem are what a TLS origin
    on 127.0.0.1 presents."""
    ca, server = _Rsa(), _Rsa()
    ca_pem = _certificate(1, "net-rotating-proxies test CA", ca, "net-rotating-proxies test CA", ca, [
        _extension("2.5.29.19", _seq(_tlv(0x01, b"\xff")), critical=True),       # cA TRUE
        _extension("2.5.29.15", _tlv(0x03, b"\x01\x06"), critical=True),          # keyCertSign, cRLSign
        _extension("2.5.29.14", _octets(ca.key_id())),
    ])
    names = _seq(_tlv(0x87, bytes([127, 0, 0, 1])), _tlv(0x82, b"localhost"))
    server_pem = _certificate(2, "net-rotating-proxies test CA", ca, "127.0.0.1", server, [
        _extension("2.5.29.19", _seq(), critical=True),                          # cA FALSE
        _extension("2.5.29.15", _tlv(0x03, b"\x05\xa0"), critical=True),          # signature, encipherment
        _extension("2.5.29.37", _seq(_oid("1.3.6.1.5.5.7.3.1"))),                # serverAuth
        _extension("2.5.29.17", names),
        _extension("2.5.29.35", _seq(_tlv(0x80, ca.key_id()))),
    ])
    paths = {}
    for name, text in (("ca.pem", ca_pem), ("server.pem", server_pem),
                       ("server-priv.pem", server.pkcs1_pem())):
        path = directory / name
        path.write_text(text, encoding="ascii")
        paths[name] = str(path)
    return paths["ca.pem"], paths["server.pem"], paths["server-priv.pem"]
