"""Music Assistant Client: Manage a Music Assistant server remotely."""

from .auth_helpers import create_long_lived_token, get_server_info, login, login_with_token
from .client import MusicAssistantClient

__all__ = [
    "MusicAssistantClient",
    "create_long_lived_token",
    "get_server_info",
    "login",
    "login_with_token",
]
