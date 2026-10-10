"""Small, bounded HIBP client. It never includes request data in diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from http.client import HTTPException
import json
import re
import ssl
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from . import __version__


MAX_RESPONSE_BYTES = 2 * 1024 * 1024
REQUEST_TIMEOUT = 15
USER_AGENT = "MimamoriBreach/" + __version__
_BASE_URL = "https://haveibeenpwned.com/api/v3/breachedAccount/"
_ERROR_MESSAGES = {
    "auth": "The breach service did not accept the API credentials.",
    "rate_limit": "The breach service requested a pause before the next check.",
    "network": "The breach service could not be reached.",
    "service": "The breach service could not complete the check.",
    "invalid_data": "The breach service returned an unsupported response.",
}


@dataclass(frozen=True)
class Breach:
    name: str
    title: str
    domain: str
    breach_date: str
    added_date: str
    data_classes: list[str]


class ClientError(Exception):
    """A deliberately generic error safe to display without request details."""

    def __init__(self, kind: str, retry_after: int = 300) -> None:
        if kind not in _ERROR_MESSAGES:
            kind = "service"
        self.kind = kind
        self.retry_after = max(1, min(86400, retry_after))
        super().__init__(_ERROR_MESSAGES[kind])


def normalize_email(value: str) -> str:
    """Validate common mailbox syntax; HIBP treats addresses case-insensitively.

    Quoted local parts and internationalized local parts are not supported.
    Internationalized domains are converted to their ASCII IDNA representation.
    """
    error = "Enter a valid email address."
    if not isinstance(value, str):
        raise ValueError(error)
    value = value.strip()
    if len(value) > 254 or value.count("@") != 1:
        raise ValueError(error)
    local, domain = value.rsplit("@", 1)
    atom = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
    if len(local) > 64 or not re.fullmatch(atom + r"(?:\." + atom + r")*", local):
        raise ValueError(error)
    try:
        domain = domain.encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise ValueError(error) from None
    labels = domain.split(".")
    if len(labels) < 2 or len(domain) > 253:
        raise ValueError(error)
    for label in labels:
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label):
            raise ValueError(error)
    result = local.lower() + "@" + domain
    if len(result) > 254:
        raise ValueError(error)
    return result


class _NoRedirect(HTTPRedirectHandler):
    # A redirected request must never carry an API key to another endpoint.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _retry_after(value: str | None) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,10}", value.strip()):
        return 300
    return max(1, min(86400, int(value.strip())))


def _text(value: object, limit: int, *, empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > limit or (not empty and not value):
        raise ValueError("Invalid field")
    if any(unicodedata.category(char).startswith("C") for char in value):
        raise ValueError("Invalid field")
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate field")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("Invalid JSON constant")


def _parse_breaches(body: bytes) -> list[Breach]:
    try:
        payload = json.loads(
            body.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        if not isinstance(payload, list) or len(payload) > 10000:
            raise ValueError("Invalid collection")
        result = []
        names = set()
        for record in payload:
            if not isinstance(record, dict):
                raise ValueError("Invalid record")
            name = _text(record.get("Name"), 200)
            title = _text(record.get("Title"), 300)
            domain = _text(record.get("Domain"), 253, empty=True)
            breach_date = _text(record.get("BreachDate"), 10)
            added_date = _text(record.get("AddedDate"), 64)
            if date.fromisoformat(breach_date).isoformat() != breach_date:
                raise ValueError("Invalid date")
            if datetime.fromisoformat(added_date.replace("Z", "+00:00")).tzinfo is None:
                raise ValueError("Invalid timestamp")
            data_classes = record.get("DataClasses")
            if not isinstance(data_classes, list) or len(data_classes) > 100:
                raise ValueError("Invalid classes")
            classes = sorted(set(_text(value, 120) for value in data_classes))
            if name in names:
                raise ValueError("Duplicate record")
            names.add(name)
            result.append(Breach(name, title, domain, breach_date, added_date, classes))
        return result
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise ClientError("invalid_data") from None


class HibpClient:
    """Email-address lookup using a caller-supplied paid HIBP subscription key.

    The complete email address is sent to HIBP over HTTPS. No raw response,
    address, key, or URL is added to errors. This class performs no automatic
    retries; callers must respect ClientError.retry_after for rate limits.
    """

    def __init__(self, api_key: str) -> None:
        if not isinstance(api_key, str) or not re.fullmatch(r"[0-9a-fA-F]{32}", api_key):
            raise ValueError("Enter a valid 32-character HIBP API key.")
        self._api_key = api_key
        self._opener = build_opener(
            _NoRedirect(), HTTPSHandler(context=ssl.create_default_context())
        )

    def breaches(self, email: str) -> list[Breach]:
        account = normalize_email(email)
        request = Request(
            _BASE_URL + quote(account, safe="") + "?truncateResponse=false&includeUnverified=false",
            headers={
                "hibp-api-key": self._api_key,
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with self._opener.open(request, timeout=REQUEST_TIMEOUT) as response:
                if response.status != 200:
                    raise ClientError("service")
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise ClientError("invalid_data")
        except HTTPError as error:
            code = error.code
            retry_after = _retry_after(error.headers.get("Retry-After") if error.headers else None)
            error.close()
            if code == 404:
                return []
            if code in (401, 403):
                raise ClientError("auth") from None
            if code == 429:
                raise ClientError("rate_limit", retry_after) from None
            raise ClientError("service") from None
        except (URLError, OSError, HTTPException):
            raise ClientError("network") from None
        return _parse_breaches(body)
