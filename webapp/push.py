"""Web Push (VAPID + RFC 8291) for the Web App — Giai đoạn 3.

Crypto choices (host constraints, see NHAT-KY GĐ3):

- This VM has **no ``cryptography`` package**, and the project is
  stdlib-only, so all elliptic-curve work (P-256 key generation, ECDH,
  ECDSA-SHA256 sign/verify for the VAPID JWT) is delegated to the
  **openssl CLI** via ``subprocess``. openssl is a system binary, not
  a Python dependency.
- ``openssl enc`` cannot do AEAD ciphers, so **AES-128-GCM is
  implemented in pure Python** below (AES block cipher + GHASH per
  NIST SP 800-38D). It is validated by the NIST test vectors and a
  full RFC 8291 encrypt→decrypt round-trip in the test suite.
- HKDF/HMAC/SHA-256 are stdlib (``hmac``/``hashlib``).

The VAPID application-server keys are generated once and stored as
JSON next to the bot database (``data/vapid.json``, mode 0600, never
in the repo). Everything network-facing is best-effort: a failed push
never breaks the request that triggered it, and subscriptions the
push service reports as gone (404/410) are deleted.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import struct
import subprocess
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

#: VAPID "sub" claim — the app owner's contact, as in the bot config.
VAPID_SUBJECT = "mailto:ntdung.lak@gmail.com"

#: RFC 8291 record size we emit (single-record messages only).
RECORD_SIZE = 4096

#: DER prefix of a P-256 SubjectPublicKeyInfo up to the BIT STRING
#: payload: SEQUENCE { SEQUENCE { OID ecPublicKey, OID prime256v1 },
#: BIT STRING 0x00 || uncompressed-point }.
_SPKI_PREFIX = bytes.fromhex(
    "3059301306072a8648ce3d020106082a8648ce3d030107034200")


# ------------------------------------------------------------ base64url
def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    if isinstance(text, str):
        text = text.encode("ascii")
    return base64.urlsafe_b64decode(text + b"=" * (-len(text) % 4))


# ------------------------------------------------------------ AES-128
_SBOX = (
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b,
    0xfe, 0xd7, 0xab, 0x76, 0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0,
    0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0, 0xb7, 0xfd, 0x93, 0x26,
    0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2,
    0xeb, 0x27, 0xb2, 0x75, 0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0,
    0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84, 0x53, 0xd1, 0x00, 0xed,
    0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f,
    0x50, 0x3c, 0x9f, 0xa8, 0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5,
    0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2, 0xcd, 0x0c, 0x13, 0xec,
    0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14,
    0xde, 0x5e, 0x0b, 0xdb, 0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c,
    0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79, 0xe7, 0xc8, 0x37, 0x6d,
    0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f,
    0x4b, 0xbd, 0x8b, 0x8a, 0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e,
    0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e, 0xe1, 0xf8, 0x98, 0x11,
    0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f,
    0xb0, 0x54, 0xbb, 0x16,
)
_RCON = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36)


def _xtime(a: int) -> int:
    a <<= 1
    return (a ^ 0x11b) & 0xff if a & 0x100 else a & 0xff


def _aes128_expand_key(key: bytes):
    if len(key) != 16:
        raise ValueError("AES-128 key must be 16 bytes")
    words = [list(key[i:i + 4]) for i in range(0, 16, 4)]
    for i in range(4, 44):
        temp = list(words[i - 1])
        if i % 4 == 0:
            temp = [_SBOX[temp[1]] ^ _RCON[i // 4 - 1],
                    _SBOX[temp[2]], _SBOX[temp[3]], _SBOX[temp[0]]]
        words.append([words[i - 4][j] ^ temp[j] for j in range(4)])
    return [[words[4 * r + c][row] for c in range(4) for row in range(4)]
            for r in range(11)]


def _aes_encrypt_block(round_keys, block: bytes) -> bytes:
    if len(block) != 16:
        raise ValueError("AES block must be 16 bytes")
    state = [block[i] ^ round_keys[0][i] for i in range(16)]
    for rnd in range(1, 11):
        state = [_SBOX[b] for b in state]
        # ShiftRows: state is column-major (index = row + 4*col).
        state = [state[(i % 4) + 4 * ((i // 4 + i % 4) % 4)]
                 for i in range(16)]
        if rnd < 10:  # MixColumns (skipped in the final round)
            mixed = [0] * 16
            for col in range(4):
                s = state[4 * col:4 * col + 4]
                mixed[4 * col + 0] = _xtime(s[0]) ^ (_xtime(s[1]) ^ s[1]) \
                    ^ s[2] ^ s[3]
                mixed[4 * col + 1] = s[0] ^ _xtime(s[1]) \
                    ^ (_xtime(s[2]) ^ s[2]) ^ s[3]
                mixed[4 * col + 2] = s[0] ^ s[1] ^ _xtime(s[2]) \
                    ^ (_xtime(s[3]) ^ s[3])
                mixed[4 * col + 3] = (_xtime(s[0]) ^ s[0]) ^ s[1] ^ s[2] \
                    ^ _xtime(s[3])
            state = mixed
        state = [state[i] ^ round_keys[rnd][i] for i in range(16)]
    return bytes(state)


def _gf_mul(x: int, y: int) -> int:
    """Multiply two GF(2^128) elements (SP 800-38D, Algorithm 1)."""
    r = 0xE1000000000000000000000000000000
    z, v = 0, y
    for i in range(128):
        if (x >> (127 - i)) & 1:
            z ^= v
        v = (v >> 1) ^ r if v & 1 else v >> 1
    return z


def _ghash(h_int: int, data: bytes) -> int:
    y = 0
    for off in range(0, len(data), 16):
        y = _gf_mul(y ^ int.from_bytes(data[off:off + 16], "big"), h_int)
    return y


def _pad16(data: bytes) -> bytes:
    return data + b"\x00" * (-len(data) % 16)


def _inc32(block: bytes) -> bytes:
    head, tail = block[:12], int.from_bytes(block[12:], "big")
    return head + ((tail + 1) & 0xFFFFFFFF).to_bytes(4, "big")


def _gcm_crypt(round_keys, j0: bytes, data: bytes) -> bytes:
    out = bytearray()
    counter = j0
    for off in range(0, len(data), 16):
        counter = _inc32(counter)
        keystream = _aes_encrypt_block(round_keys, counter)
        chunk = data[off:off + 16]
        out.extend(b ^ k for b, k in zip(chunk, keystream))
    return bytes(out)


def _gcm_tag(round_keys, h_int: int, j0: bytes, aad: bytes,
             ciphertext: bytes) -> bytes:
    s = _ghash(h_int, _pad16(aad) + _pad16(ciphertext)
               + struct.pack(">QQ", len(aad) * 8, len(ciphertext) * 8))
    return bytes(a ^ b for a, b in
                 zip(s.to_bytes(16, "big"),
                     _aes_encrypt_block(round_keys, j0)))


def aes128gcm_encrypt(key: bytes, nonce: bytes, plaintext: bytes,
                      aad: bytes = b"") -> bytes:
    """AES-128-GCM encrypt; returns ciphertext || 16-byte tag."""
    if len(nonce) != 12:
        raise ValueError("GCM nonce must be 12 bytes")
    round_keys = _aes128_expand_key(key)
    h_int = int.from_bytes(_aes_encrypt_block(round_keys, b"\x00" * 16),
                           "big")
    j0 = nonce + b"\x00\x00\x00\x01"
    ciphertext = _gcm_crypt(round_keys, j0, plaintext)
    return ciphertext + _gcm_tag(round_keys, h_int, j0, aad, ciphertext)


def aes128gcm_decrypt(key: bytes, nonce: bytes, data: bytes,
                      aad: bytes = b"") -> bytes:
    """Verify the tag and decrypt ``ciphertext || tag``."""
    if len(nonce) != 12 or len(data) < 16:
        raise ValueError("bad GCM input")
    ciphertext, tag = data[:-16], data[-16:]
    round_keys = _aes128_expand_key(key)
    h_int = int.from_bytes(_aes_encrypt_block(round_keys, b"\x00" * 16),
                           "big")
    j0 = nonce + b"\x00\x00\x00\x01"
    expected = _gcm_tag(round_keys, h_int, j0, aad, ciphertext)
    if not hmac.compare_digest(expected, tag):
        raise ValueError("GCM tag mismatch")
    return _gcm_crypt(round_keys, j0, ciphertext)


# ---------------------------------------------------------------- HKDF
def _hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    return hmac.new(salt, ikm, hashlib.sha256).digest()


def _hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    out, previous, counter = b"", b"", 1
    while len(out) < length:
        previous = hmac.new(prk, previous + info + bytes([counter]),
                            hashlib.sha256).digest()
        out += previous
        counter += 1
    return out[:length]


# ------------------------------------------------------- openssl helpers
def _run_openssl(args, input_bytes: bytes | None = None) -> bytes:
    proc = subprocess.run(["openssl", *args], input=input_bytes,
                          capture_output=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError(
            f"openssl {' '.join(args[:2])} failed: "
            f"{proc.stderr.decode('utf-8', 'replace')[:200]}")
    return proc.stdout


def generate_ec_keypair():
    """New P-256 keypair: (private_key_pem str, public_point 65 bytes)."""
    pem = _run_openssl(
        ["ecparam", "-name", "prime256v1", "-genkey", "-noout"]).decode()
    return pem, ec_public_point(pem)


def ec_public_point(private_pem: str) -> bytes:
    """Uncompressed public point (0x04 || X || Y) for a P-256 PEM key."""
    der = _run_openssl(["ec", "-pubout", "-outform", "DER"],
                       input_bytes=private_pem.encode())
    point = der[-65:]
    if len(point) != 65 or point[0] != 0x04:
        raise RuntimeError("unexpected EC public key format from openssl")
    return point


def public_pem_from_point(point: bytes) -> str:
    if len(point) != 65 or point[0] != 0x04:
        raise ValueError("not an uncompressed P-256 point")
    der = _SPKI_PREFIX + point
    b64 = base64.b64encode(der).decode()
    lines = "\n".join(b64[i:i + 64] for i in range(0, len(b64), 64))
    return f"-----BEGIN PUBLIC KEY-----\n{lines}\n-----END PUBLIC KEY-----\n"


def _der_encode_integer(value: int) -> bytes:
    raw = value.to_bytes(max(1, (value.bit_length() + 7) // 8), "big")
    if raw[0] & 0x80:
        raw = b"\x00" + raw
    return b"\x02" + bytes([len(raw)]) + raw


def _raw_sig_to_der(raw: bytes) -> bytes:
    body = _der_encode_integer(int.from_bytes(raw[:32], "big")) \
        + _der_encode_integer(int.from_bytes(raw[32:], "big"))
    return b"\x30" + bytes([len(body)]) + body


def _der_sig_to_raw(der: bytes) -> bytes:
    if not der or der[0] != 0x30:
        raise ValueError("not a DER signature")
    idx = 2
    if der[1] & 0x80:
        idx = 2 + (der[1] & 0x7F)
    values = []
    for _ in range(2):
        if der[idx] != 0x02:
            raise ValueError("not a DER signature")
        length = der[idx + 1]
        values.append(int.from_bytes(der[idx + 2:idx + 2 + length], "big"))
        idx += 2 + length
    return values[0].to_bytes(32, "big") + values[1].to_bytes(32, "big")


def ec_sign_sha256(private_pem: str, data: bytes) -> bytes:
    """ECDSA-SHA256 signature in JWS raw form (r || s, 64 bytes)."""
    with tempfile.TemporaryDirectory() as tmp:
        key_file = Path(tmp) / "key.pem"
        key_file.write_text(private_pem)
        der = _run_openssl(
            ["dgst", "-sha256", "-sign", str(key_file)], input_bytes=data)
    return _der_sig_to_raw(der)


def ec_verify_sha256(public_point: bytes, data: bytes,
                     raw_signature: bytes) -> bool:
    """Verify a JWS raw ECDSA-SHA256 signature (used by the tests)."""
    with tempfile.TemporaryDirectory() as tmp:
        pub_file = Path(tmp) / "pub.pem"
        sig_file = Path(tmp) / "sig.der"
        pub_file.write_text(public_pem_from_point(public_point))
        sig_file.write_bytes(_raw_sig_to_der(raw_signature))
        proc = subprocess.run(
            ["openssl", "dgst", "-sha256", "-verify", str(pub_file),
             "-signature", str(sig_file)],
            input=data, capture_output=True, timeout=30)
    return proc.returncode == 0


def ecdh_derive(private_pem: str, peer_point: bytes) -> bytes:
    """ECDH shared secret (32 bytes) with a peer's public point."""
    with tempfile.TemporaryDirectory() as tmp:
        key_file = Path(tmp) / "key.pem"
        peer_file = Path(tmp) / "peer.pem"
        key_file.write_text(private_pem)
        peer_file.write_text(public_pem_from_point(peer_point))
        return _run_openssl(
            ["pkeyutl", "-derive", "-inkey", str(key_file),
             "-peerkey", str(peer_file)])


# ------------------------------------------------------------- VAPID keys
def default_vapid_path(db_path) -> Path:
    """Key file location: env override, else next to the database
    (in production that is the bot's ``data/`` directory)."""
    override = os.environ.get("WEBAPP_VAPID_PATH")
    if override:
        return Path(override)
    return Path(db_path).parent / "vapid.json"


def load_or_create_keys(path) -> dict:
    """Load the VAPID keys, generating and storing them once.

    The file is JSON: the private key PEM + the base64url public key.
    It is written with mode 0600 and must never enter the repo."""
    path = Path(path)
    if path.exists():
        data = json.loads(path.read_text())
        point = ec_public_point(data["private_key_pem"])
        if b64url_decode(data["public_key"]) != point:
            raise RuntimeError("VAPID key file is inconsistent")
        return {"private_pem": data["private_key_pem"], "public_point": point,
                "public_key": data["public_key"]}
    pem, point = generate_ec_keypair()
    payload = {
        "private_key_pem": pem,
        "public_key": b64url_encode(point),
        "subject": VAPID_SUBJECT,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(payload, fh, indent=1)
    os.chmod(path, 0o600)
    return {"private_pem": pem, "public_point": point,
            "public_key": payload["public_key"]}


def build_vapid_jwt(keys: dict, audience_origin: str,
                    subject: str = VAPID_SUBJECT,
                    ttl_hours: int = 12, now: datetime | None = None) -> str:
    """Signed VAPID JWT (ES256) for one push-service origin."""
    now = now or datetime.now(timezone.utc)
    header = {"typ": "JWT", "alg": "ES256"}
    claims = {
        "aud": audience_origin,
        "exp": int((now + timedelta(hours=ttl_hours)).timestamp()),
        "sub": subject,
    }
    signing_input = (
        b64url_encode(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + b64url_encode(json.dumps(claims, separators=(",", ":")).encode())
    )
    signature = ec_sign_sha256(keys["private_pem"],
                               signing_input.encode("ascii"))
    return f"{signing_input}.{b64url_encode(signature)}"


# ---------------------------------------------------- RFC 8291 encryption
def _derive_content_keys(receiver_point: bytes, sender_point: bytes,
                         ecdh_secret: bytes, auth_secret: bytes,
                         salt: bytes):
    """RFC 8291 §3.3–3.4 key schedule → (content key, nonce)."""
    prk_key = _hkdf_extract(auth_secret, ecdh_secret)
    key_info = b"WebPush: info\x00" + receiver_point + sender_point
    ikm = _hkdf_expand(prk_key, key_info, 32)
    prk = _hkdf_extract(salt, ikm)
    cek = _hkdf_expand(prk, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf_expand(prk, b"Content-Encoding: nonce\x00", 12)
    return cek, nonce


def encrypt_payload(receiver_public_b64: str, auth_b64: str,
                    payload: bytes, sender_keypair=None) -> bytes:
    """Encrypt one push payload (RFC 8291, aes128gcm content coding).

    ``sender_keypair`` may inject (private_pem, public_point) of the
    ephemeral key (the tests use it; production generates per message).
    """
    receiver_point = b64url_decode(receiver_public_b64)
    if len(receiver_point) != 65 or receiver_point[0] != 0x04:
        raise ValueError("bad p256dh key in subscription")
    auth_secret = b64url_decode(auth_b64)
    if len(auth_secret) < 16:
        raise ValueError("bad auth secret in subscription")
    if len(payload) + 1 > RECORD_SIZE - 16:
        raise ValueError("push payload too large for one record")
    sender_pem, sender_point = sender_keypair or generate_ec_keypair()
    secret = ecdh_derive(sender_pem, receiver_point)
    salt = os.urandom(16)
    cek, nonce = _derive_content_keys(receiver_point, sender_point,
                                      secret, auth_secret, salt)
    record = aes128gcm_encrypt(cek, nonce, payload + b"\x02")
    return (salt + struct.pack(">I", RECORD_SIZE)
            + bytes([len(sender_point)]) + sender_point + record)


def decrypt_payload(body: bytes, receiver_private_pem: str,
                    receiver_point: bytes, auth_secret: bytes) -> bytes:
    """Inverse of :func:`encrypt_payload` (receiver side; the tests
    use it to prove the round-trip end to end)."""
    salt, rest = body[:16], body[16:]
    _rs, rest = struct.unpack(">I", rest[:4])[0], rest[4:]
    idlen, rest = rest[0], rest[1:]
    sender_point, record = rest[:idlen], rest[idlen:]
    secret = ecdh_derive(receiver_private_pem, sender_point)
    cek, nonce = _derive_content_keys(receiver_point, sender_point,
                                      secret, auth_secret, salt)
    plain = aes128gcm_decrypt(cek, nonce, record)
    plain = plain.rstrip(b"\x00")
    if not plain.endswith(b"\x02"):
        raise ValueError("bad record delimiter")
    return plain[:-1]


# -------------------------------------------------------------- transport
def _opener_for(url: str):
    """urllib opener for a push endpoint. Production endpoints go
    through the cell's egress proxy (env); loopback endpoints — only
    used by tests/dev — bypass it."""
    host = (urlparse(url).hostname or "").lower()
    if host in ("127.0.0.1", "localhost", "::1"):
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener()


class PushService:
    """Sends Web Push notifications for users of the web app.

    Holds the VAPID keys and the WebDB (for subscriptions). Every
    public method is best-effort: transport problems are reported in
    the result dicts, never raised into request handlers.
    """

    def __init__(self, webdb, keys_path, subject: str = VAPID_SUBJECT,
                 timeout: int = 20):
        self.webdb = webdb
        self.keys = load_or_create_keys(keys_path)
        self.subject = subject
        self.timeout = timeout

    @property
    def public_key(self) -> str:
        return self.keys["public_key"]

    # ------------------------------------------------------------ send
    def send_to_subscription(self, subscription, payload: bytes) -> dict:
        """POST one encrypted payload to one subscription endpoint.

        Returns {endpoint, ok, status, gone, error}. A 404/410 answer
        deletes the subscription (``gone``) as RFC 8030 requires."""
        endpoint = subscription["endpoint"]
        result = {"endpoint": endpoint, "ok": False, "status": None,
                  "gone": False, "error": None}
        try:
            parsed = urlparse(endpoint)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            jwt = build_vapid_jwt(self.keys, origin, subject=self.subject)
            body = encrypt_payload(subscription["p256dh"],
                                   subscription["auth"], payload)
            request = urllib.request.Request(endpoint, data=body,
                                             method="POST")
            request.add_header("Authorization",
                               f"vapid t={jwt}, k={self.public_key}")
            request.add_header("Content-Encoding", "aes128gcm")
            request.add_header("Content-Type", "application/octet-stream")
            request.add_header("TTL", "86400")
            with _opener_for(endpoint).open(request,
                                            timeout=self.timeout) as resp:
                resp.read()
                result["status"] = resp.status
                result["ok"] = 200 <= resp.status < 300
        except urllib.error.HTTPError as err:
            result["status"] = err.code
            if err.code in (404, 410):
                result["gone"] = True
                self.webdb.delete_push_subscription(endpoint)
        except Exception as err:  # transport/openssl problems: report only
            result["error"] = f"{type(err).__name__}: {err}"
        return result

    def notify_user_detailed(self, user_id: int, title: str, body: str,
                             url: str = "/") -> list:
        payload = json.dumps({"title": title, "body": body, "url": url},
                             ensure_ascii=False).encode("utf-8")
        results = []
        for sub in self.webdb.push_subscriptions_for_user(user_id):
            results.append(self.send_to_subscription(sub, payload))
        return results

    def notify_users(self, user_ids, title: str, body: str,
                     url: str = "/") -> dict:
        """Push one message to every subscription of ``user_ids``.

        Returns a small summary; failures of individual endpoints are
        swallowed into it so callers can fire-and-forget."""
        summary = {"sent": 0, "failed": 0, "gone": 0, "results": []}
        try:
            payload = json.dumps({"title": title, "body": body, "url": url},
                                 ensure_ascii=False).encode("utf-8")
            for sub in self.webdb.push_subscriptions_for_users(user_ids):
                result = self.send_to_subscription(sub, payload)
                summary["results"].append(result)
                if result["ok"]:
                    summary["sent"] += 1
                elif result["gone"]:
                    summary["gone"] += 1
                else:
                    summary["failed"] += 1
        except Exception as err:  # never break the triggering request
            summary["error"] = f"{type(err).__name__}: {err}"
        return summary
