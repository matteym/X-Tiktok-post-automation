"""OAuth 1.0a signing for the X API."""

from __future__ import annotations

import binascii
import hashlib
import hmac
import os
import time
from base64 import b64encode
from urllib.parse import parse_qsl, quote, urlparse


def percent_encode(value: str) -> str:
    return quote(str(value), safe="~")


def oauth1_authorization_header(
    *,
    method: str,
    url: str,
    consumer_key: str,
    consumer_secret: str,
    token: str,
    token_secret: str,
    extra_params: dict[str, str] | None = None,
) -> str:
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": binascii.hexlify(os.urandom(16)).decode("ascii"),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": token,
        "oauth_version": "1.0",
    }
    all_params: dict[str, str] = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if extra_params:
        all_params.update(extra_params)
    all_params.update(oauth_params)
    param_str = "&".join(
        f"{percent_encode(key)}={percent_encode(val)}"
        for key, val in sorted(all_params.items())
    )
    base = "&".join(
        [method.upper(), percent_encode(base_url), percent_encode(param_str)]
    )
    signing_key = f"{percent_encode(consumer_secret)}&{percent_encode(token_secret)}"
    digest = hmac.new(signing_key.encode("utf-8"), base.encode("utf-8"), hashlib.sha1).digest()
    oauth_params["oauth_signature"] = b64encode(digest).decode("ascii")
    header = ", ".join(
        f'{percent_encode(key)}="{percent_encode(val)}"'
        for key, val in sorted(oauth_params.items())
    )
    return "OAuth " + header
