"""Handle Auth related endpoints for Music Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from music_assistant_models.auth import AuthToken, Role, User, UserAuthProvider

if TYPE_CHECKING:
    from music_assistant_models.auth import Scope

    from .client import MusicAssistantClient


class Auth:
    """Auth related endpoints/data for Music Assistant."""

    def __init__(self, client: MusicAssistantClient) -> None:
        """Handle Initialization."""
        self.client = client

    async def get_current_user(self) -> User:
        """Get current authenticated user information."""
        return User.from_dict(await self.client.send_command("auth/me"))

    async def create_token(self, name: str, user_id: str | None = None) -> str:
        """
        Create a new long-lived access token.

        Args:
            name: A friendly name for the token
            user_id: Optional user ID to create token for (admin only)

        Returns:
            The token string
        """
        result: str = await self.client.send_command(
            "auth/token/create", name=name, user_id=user_id
        )
        return result

    async def revoke_token(self, token_id: str) -> None:
        """Revoke an auth token."""
        await self.client.send_command("auth/token/revoke", token_id=token_id)

    async def get_tokens(self, user_id: str | None = None) -> list[AuthToken]:
        """
        Get auth tokens for current user or another user (admin only).

        Args:
            user_id: Optional user ID to get tokens for (admin only)

        Returns:
            List of AuthToken objects
        """
        return [
            AuthToken.from_dict(token)
            for token in await self.client.send_command("auth/tokens", user_id=user_id)
        ]

    async def get_user(self, user_id: str) -> User | None:
        """Get user by ID (requires the users.read scope)."""
        result = await self.client.send_command("auth/user", user_id=user_id)
        return User.from_dict(result) if result else None

    async def list_users(self) -> list[User]:
        """Get all users (requires the users.read scope)."""
        return [User.from_dict(user) for user in await self.client.send_command("auth/users")]

    async def create_user(
        self,
        username: str,
        password: str,
        role: str = "user",
        display_name: str | None = None,
        avatar_url: str | None = None,
        player_filter: list[str] | None = None,
    ) -> User:
        """Create a new user with built-in authentication (admin only)."""
        return User.from_dict(
            await self.client.send_command(
                "auth/user/create",
                username=username,
                password=password,
                role=role,
                display_name=display_name,
                avatar_url=avatar_url,
                player_filter=player_filter,
            )
        )

    async def delete_user(self, user_id: str) -> None:
        """Delete user account (admin only)."""
        await self.client.send_command("auth/user/delete", user_id=user_id)

    async def enable_user(self, user_id: str) -> None:
        """Enable user account (admin only)."""
        await self.client.send_command("auth/user/enable", user_id=user_id)

    async def disable_user(self, user_id: str) -> None:
        """Disable user account (admin only)."""
        await self.client.send_command("auth/user/disable", user_id=user_id)

    async def get_user_providers(self) -> list[UserAuthProvider]:
        """Get current user's linked authentication providers."""
        return [
            UserAuthProvider.from_dict(provider)
            for provider in await self.client.send_command("auth/user/providers")
        ]

    async def unlink_provider(self, user_id: str, provider_type: str) -> bool:
        """Unlink authentication provider from user (admin only)."""
        result: bool = await self.client.send_command(
            "auth/user/unlink_provider",
            user_id=user_id,
            provider_type=provider_type,
        )
        return result

    async def update_user(
        self,
        user_id: str | None = None,
        username: str | None = None,
        display_name: str | None = None,
        avatar_url: str | None = None,
        password: str | None = None,
        role: str | None = None,
        preferences: dict[str, Any] | None = None,
        player_filter: list[str] | None = None,
    ) -> User:
        """
        Update user profile information.

        Users can update their own profile. Admins can update any user including role and password.

        Args:
            user_id: User ID to update (optional, defaults to current user)
            username: New username (optional)
            display_name: New display name (optional)
            avatar_url: New avatar URL (optional)
            password: New password (optional, minimum 8 characters)
            role: New role id - a builtin role (admin, user, guest, service)
                or the id of a custom role (optional, admin only)
            preferences: User preferences dict (completely replaces existing, optional)
            player_filter: List of player IDs the user has access to (admin only, optional)

        Returns:
            Updated user object
        """
        return User.from_dict(
            await self.client.send_command(
                "auth/user/update",
                user_id=user_id,
                username=username,
                display_name=display_name,
                avatar_url=avatar_url,
                password=password,
                role=role,
                preferences=preferences,
                player_filter=player_filter,
            )
        )

    async def logout(self) -> None:
        """Logout current user by revoking the current token."""
        await self.client.send_command("auth/logout")

    async def login(
        self,
        username: str | None = None,
        password: str | None = None,
        provider_id: str = "builtin",
        device_name: str | None = None,
    ) -> dict[str, Any]:
        """Authenticate user with credentials via WebSocket."""
        result: dict[str, Any] = await self.client.send_command(
            "auth/login",
            username=username,
            password=password,
            provider_id=provider_id,
            device_name=device_name,
            require_schema=84,
        )
        return result

    async def get_providers(self) -> list[dict[str, Any]]:
        """Get list of available authentication providers."""
        result: list[dict[str, Any]] = await self.client.send_command(
            "auth/providers", require_schema=84
        )
        return result

    async def get_authorization_url(
        self, provider_id: str, return_url: str | None = None
    ) -> dict[str, str | None]:
        """Get OAuth authorization URL for authentication."""
        result: dict[str, str | None] = await self.client.send_command(
            "auth/authorization_url",
            provider_id=provider_id,
            return_url=return_url,
            require_schema=84,
        )
        return result

    async def list_join_codes(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """List join codes, optionally filtered by user (admin only)."""
        result: list[dict[str, Any]] = await self.client.send_command(
            "auth/join_codes", user_id=user_id, require_schema=84
        )
        return result

    async def exchange_join_code(self, code: str) -> dict[str, Any]:
        """Exchange a join code for an access token (public API)."""
        result: dict[str, Any] = await self.client.send_command(
            "auth/join_code/exchange", code=code, require_schema=84
        )
        return result

    async def revoke_join_code(self, code_id: str) -> None:
        """Revoke a specific join code (admin only)."""
        await self.client.send_command("auth/join_code/revoke", code_id=code_id, require_schema=84)

    async def get_roles(self) -> list[Role]:
        """Get all user roles: the builtin roles first, then the custom roles by name."""
        return [
            Role.from_dict(role)
            for role in await self.client.send_command("auth/roles", require_schema=84)
        ]

    async def get_role_scopes(self) -> dict[str, list[str]]:
        """Get the scopes granted by each of the builtin and custom user roles, by role id."""
        result: dict[str, list[str]] = await self.client.send_command(
            "auth/scopes", require_schema=84
        )
        return result

    async def create_role(self, name: str, scopes: list[Scope]) -> Role:
        """Create a custom user role (requires the users.manage scope)."""
        return Role.from_dict(
            await self.client.send_command(
                "auth/role/create", name=name, scopes=scopes, require_schema=84
            )
        )

    async def update_role(
        self, role_id: str, name: str | None = None, scopes: list[Scope] | None = None
    ) -> Role:
        """Update a custom user role (requires the users.manage scope)."""
        return Role.from_dict(
            await self.client.send_command(
                "auth/role/update",
                role_id=role_id,
                name=name,
                scopes=scopes,
                require_schema=84,
            )
        )

    async def delete_role(self, role_id: str) -> None:
        """Delete a custom user role (requires the users.manage scope)."""
        await self.client.send_command("auth/role/delete", role_id=role_id, require_schema=84)
