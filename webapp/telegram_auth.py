"""Telegram Mini App initData validation (stdlib only).

Implements the HMAC validation from
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app:

- ``data-check-string``: every received field EXCEPT ``hash`` (and
  ``signature`` — the Ed25519 third-party-validation field, which
  Telegram excludes from the check string as well), sorted by key,
  joined as ``key=<value>`` with ``"\\n"`` separators. Values are the
  URL-decoded values.
- ``secret_key = HMAC_SHA256(key=b"WebAppData", msg=bot_token)``.
- ``expected = HMAC_SHA256(key=secret_key, msg=data-check-string)``
  (hex), compared with the received ``hash`` via ``hmac.compare_digest``.
- ``auth_date`` must be within ``max_age_seconds`` (default 24h) of now.

The bot token is read from the ``TELEGRAM_BOT_TOKEN`` environment
variable — the same convention the bot's ``telegram_client`` documents.
The token is NEVER logged, returned or stored by this module. The raw
token is not available from the Muse secure connection: authd only
hands out ``hsurr:`` surrogates, which cannot be an HMAC key. Until
the token is provisioned (Secure Vault → ``/etc/default/webapp-giao-viec``,
mode 600), the login endpoint answers 503.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qsl

#: Default freshness window for ``auth_date`` (Telegram's own examples
#: and most libraries use 24h; initData is minted when the Mini App
#: opens, so a real login is seconds old).
DEFAULT_MAX_AGE_SECONDS = 24 * 3600
#: Clock-skew allowance for an ``auth_date`` slightly in the future.
_FUTURE_SKEW_SECONDS = 300

#: Fields that are signatures themselves and never enter the check string.
_EXCLUDED_FIELDS = ("hash", "signature")


class InitDataError(ValueError):
    """initData failed validation (message is safe to show to clients)."""


def get_bot_token() -> str | None:
    """Bot token for initData validation, or None when not configured."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    return token or None


def _parse_fields(init_data: str) -> dict:
    if not init_data or not isinstance(init_data, str):
        raise InitDataError("Thiếu dữ liệu xác thực Telegram.")
    fields = {}
    for key, value in parse_qsl(init_data, keep_blank_values=True):
        fields.setdefault(key, value)
    return fields


def validate_init_data(init_data: str, token: str,
                       max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
                       now: float | None = None) -> dict:
    """Validate Telegram Mini App initData; return the ``user`` object.

    Raises InitDataError on any failure. Never includes the token or
    the received/computed hashes in the message.
    """
    if not token:
        raise InitDataError("Mini App chưa được cấu hình.")
    fields = _parse_fields(init_data)
    received_hash = fields.get("hash", "")
    if not received_hash:
        raise InitDataError("Thiếu chữ ký xác thực Telegram.")
    auth_date_raw = fields.get("auth_date", "")
    try:
        auth_date = int(auth_date_raw)
    except (TypeError, ValueError):
        raise InitDataError("Ngày xác thực Telegram không hợp lệ.")
    moment = time.time() if now is None else now
    if auth_date > moment + _FUTURE_SKEW_SECONDS:
        raise InitDataError("Ngày xác thực Telegram ở tương lai.")
    if moment - auth_date > max_age_seconds:
        raise InitDataError("Phiên Telegram đã hết hạn, hãy mở lại Mini App.")
    check_lines = [f"{key}={fields[key]}" for key in sorted(fields)
                   if key not in _EXCLUDED_FIELDS]
    data_check_string = "\n".join(check_lines)
    secret_key = hmac.new(b"WebAppData", token.encode("utf-8"),
                          hashlib.sha256).digest()
    expected = hmac.new(secret_key, data_check_string.encode("utf-8"),
                        hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash.lower()):
        raise InitDataError("Chữ ký xác thực Telegram không hợp lệ.")
    try:
        user = json.loads(fields.get("user") or "")
    except (ValueError, TypeError):
        raise InitDataError("Thông tin người dùng Telegram không hợp lệ.")
    if not isinstance(user, dict) or not isinstance(user.get("id"), int):
        raise InitDataError("Thông tin người dùng Telegram không hợp lệ.")
    return user


def sign_init_data(fields: dict, token: str) -> str:
    """Build a signed initData string (tests and probes only).

    ``fields`` maps key -> raw (unencoded) value; ``user`` must be a
    JSON string already. The hash is computed exactly as Telegram
    computes it, so a round trip through validate_init_data proves
    the algorithm. Never used in production code paths.
    """
    check_lines = [f"{key}={fields[key]}" for key in sorted(fields)
                   if key not in _EXCLUDED_FIELDS]
    data_check_string = "\n".join(check_lines)
    secret_key = hmac.new(b"WebAppData", token.encode("utf-8"),
                          hashlib.sha256).digest()
    digest = hmac.new(secret_key, data_check_string.encode("utf-8"),
                      hashlib.sha256).hexdigest()
    from urllib.parse import urlencode

    signed = dict(fields)
    signed["hash"] = digest
    return urlencode(signed)
