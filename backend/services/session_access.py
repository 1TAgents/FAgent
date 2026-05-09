"""
Session access policy.

The backend supports both anonymous sessions and user-owned sessions. This
module centralizes the ownership rule so every cid-based API endpoint uses the
same isolation behavior.
"""
from __future__ import annotations

from typing import Mapping, Optional


def can_access_session(
    session: Optional[Mapping],
    current_user: Optional[Mapping],
) -> bool:
    """Return whether the current request can access a session."""
    if session is None:
        return False

    owner_id = session.get("user_id")
    if owner_id is None:
        return current_user is None

    return current_user is not None and owner_id == current_user.get("id")
