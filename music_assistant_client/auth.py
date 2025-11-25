"""Handle Auth related endpoints for Music Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from music_assistant_models.auth import AuthToken, User, UserAuthProvider

if TYPE_CHECKING:
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
        """Get user by ID (admin only)."""
        result = await self.client.send_command("auth/user", user_id=user_id)
        return User.from_dict(result) if result else None

    async def list_users(self) -> list[User]:
        """Get all users (admin only)."""
        return [User.from_dict(user) for user in await self.client.send_command("auth/users")]

    async def create_user(
        self,
        username: str,
        password: str,
        role: str = "user",
        display_name: str | None = None,
        avatar_url: str | None = None,
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

    async def unlink_provider(self, link_id: str) -> None:
        """Unlink authentication provider from user (admin only)."""
        await self.client.send_command("auth/user/unlink_provider", link_id=link_id)

    async def update_user(
        self,
        user_id: str | None = None,
        username: str | None = None,
        display_name: str | None = None,
        avatar_url: str | None = None,
        password: str | None = None,
        old_password: str | None = None,
        role: str | None = None,
        preferences: dict[str, Any] | None = None,
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
            old_password: Current password (required when user updates own password)
            role: New role - "admin" or "user" (optional, admin only)
            preferences: User preferences dict (completely replaces existing, optional)

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
                old_password=old_password,
                role=role,
                preferences=preferences,
            )
        )

    async def logout(self) -> None:
        """Logout current user by revoking the current token."""
        await self.client.send_command("auth/logout")
