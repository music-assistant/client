"""Music Assistant Client: Manage a Music Assistant server remotely."""

from .auth import (
    create_long_lived_token,
    get_current_user,
    list_tokens,
    login,
    login_with_token,
    revoke_token,
)
from .client import MusicAssistantClient

__all__ = [
    "MusicAssistantClient",
    "create_long_lived_token",
    "get_current_user",
    "list_tokens",
    "login",
    "login_with_token",
    "revoke_token",
]
