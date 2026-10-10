"""Pure state transitions for successful breach checks."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from .hibp import Breach, normalize_email


def _meaningful(breach: dict) -> tuple:
    """Title spelling and data-class ordering do not warrant another alert."""
    return (
        breach.get("domain"),
        breach.get("breach_date"),
        breach.get("added_date"),
        sorted(set(breach.get("data_classes", []))),
    )


def apply_success(
    state: dict, email: str, breaches: list[Breach], checked_at: str
) -> tuple[dict, list[Breach]]:
    """Record a successful lookup and return new or materially changed matches.

    Existing matches remain in history even if later API results omit them.
    The first successful check surfaces existing matches as well as recent ones.
    Only successful requests should call this function; an error is not an
    empty result. Changing the watched account starts a separate history.
    """
    account = normalize_email(email)
    items = deepcopy(state.get("items", {})) if state.get("account") == account else {}
    notifications = []
    seen = set()
    for breach in breaches:
        if breach.name in seen:
            continue
        seen.add(breach.name)
        data = asdict(breach)
        previous = items.get(breach.name)
        changed = previous is None or _meaningful(previous["breach"]) != _meaningful(data)
        items[breach.name] = {
            "breach": data,
            "acknowledged": False if changed else previous["acknowledged"],
            "first_seen": checked_at if previous is None else previous["first_seen"],
        }
        if changed:
            notifications.append(breach)
    return {"account": account, "last_success": checked_at, "items": items}, notifications
