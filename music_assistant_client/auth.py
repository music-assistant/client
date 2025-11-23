"""Authentication helpers for Music Assistant Client."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import aiohttp
from music_assistant_models.auth import AuthToken, User
from music_assistant_models.errors import AuthenticationFailed, LoginFailed

from .exceptions import CannotConnect

if TYPE_CHECKING:
    from ssl import SSLContext

    from aiohttp import ClientSession

LOGGER = logging.getLogger(__name__)


async def login(
    server_url: str,
    username: str,
    password: str,
    aiohttp_session: ClientSession | None = None,
    ssl_context: SSLContext | None = None,
) -> tuple[User, str]:
    """
    Log in to a Music Assistant server with username and password.

    Args:
        server_url: The base URL of the Music Assistant server
        username: The username to authenticate with
        password: The password to authenticate with
        aiohttp_session: Optional aiohttp session to use
        ssl_context: Optional SSL context for HTTPS connections

    Returns:
        A tuple of (User, access_token)

    Raises:
        LoginFailed: If authentication fails
        CannotConnect: If unable to connect to server
    """
    # Ensure we have a session
    session_provided = aiohttp_session is not None
    if aiohttp_session:
        session = aiohttp_session
    else:
        # Create session with SSL context if provided
        connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else None
        session = aiohttp.ClientSession(connector=connector)

    # Normalize server URL
    if not server_url.endswith("/"):
        server_url = f"{server_url}/"

    try:
        # Send login request
        async with session.post(
            f"{server_url}auth/login",
            json={"username": username, "password": password},
        ) as response:
            if response.status == 401:
                msg = "Invalid username or password"
                raise LoginFailed(msg)

            if response.status != 200:
                msg = f"Login failed with status {response.status}"
                raise CannotConnect(Exception(msg))

            data = await response.json()
            user = User.from_dict(data["user"])
            access_token = data["access_token"]

            LOGGER.info("Successfully logged in as %s", username)
            return user, access_token

    except aiohttp.ClientError as err:
        raise CannotConnect(err) from err
    finally:
        if not session_provided:
            await session.close()


async def create_long_lived_token(
    server_url: str,
    access_token: str,
    token_name: str,
    aiohttp_session: ClientSession | None = None,
    ssl_context: SSLContext | None = None,
) -> str:
    """
    Create a long-lived token using an existing access token.

    Args:
        server_url: The base URL of the Music Assistant server
        access_token: The access token from a previous login
        token_name: A friendly name for the token
        aiohttp_session: Optional aiohttp session to use
        ssl_context: Optional SSL context for HTTPS connections

    Returns:
        The long-lived token string

    Raises:
        AuthenticationFailed: If token creation fails
        CannotConnect: If unable to connect to server
    """
    # Ensure we have a session
    session_provided = aiohttp_session is not None
    if aiohttp_session:
        session = aiohttp_session
    else:
        # Create session with SSL context if provided
        connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else None
        session = aiohttp.ClientSession(connector=connector)

    # Normalize server URL
    if not server_url.endswith("/"):
        server_url = f"{server_url}/"

    try:
        # Send token creation request
        async with session.post(
            f"{server_url}auth/tokens",
            json={"name": token_name, "is_long_lived": True},
            headers={"Authorization": f"Bearer {access_token}"},
        ) as response:
            if response.status == 401:
                msg = "Invalid or expired access token"
                raise AuthenticationFailed(msg)

            if response.status != 200:
                msg = f"Token creation failed with status {response.status}"
                raise CannotConnect(Exception(msg))

            data = await response.json()
            token: str = data["token"]

            LOGGER.info("Successfully created long-lived token: %s", token_name)
            return token

    except aiohttp.ClientError as err:
        raise CannotConnect(err) from err
    finally:
        if not session_provided:
            await session.close()


async def get_current_user(
    server_url: str,
    access_token: str,
    aiohttp_session: ClientSession | None = None,
    ssl_context: SSLContext | None = None,
) -> User:
    """
    Get the current user info using an access token.

    Args:
        server_url: The base URL of the Music Assistant server
        access_token: The access token to use
        aiohttp_session: Optional aiohttp session to use
        ssl_context: Optional SSL context for HTTPS connections

    Returns:
        The User object

    Raises:
        AuthenticationFailed: If the token is invalid
        CannotConnect: If unable to connect to server
    """
    # Ensure we have a session
    session_provided = aiohttp_session is not None
    if aiohttp_session:
        session = aiohttp_session
    else:
        # Create session with SSL context if provided
        connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else None
        session = aiohttp.ClientSession(connector=connector)

    # Normalize server URL
    if not server_url.endswith("/"):
        server_url = f"{server_url}/"

    try:
        # Send request to get current user
        async with session.get(
            f"{server_url}auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        ) as response:
            if response.status == 401:
                msg = "Invalid or expired access token"
                raise AuthenticationFailed(msg)

            if response.status != 200:
                msg = f"Failed to get user info with status {response.status}"
                raise CannotConnect(Exception(msg))

            data = await response.json()
            return User.from_dict(data)

    except aiohttp.ClientError as err:
        raise CannotConnect(err) from err
    finally:
        if not session_provided:
            await session.close()


async def list_tokens(
    server_url: str,
    access_token: str,
    aiohttp_session: ClientSession | None = None,
    ssl_context: SSLContext | None = None,
) -> list[AuthToken]:
    """
    List all tokens for the current user.

    Args:
        server_url: The base URL of the Music Assistant server
        access_token: The access token to use
        aiohttp_session: Optional aiohttp session to use
        ssl_context: Optional SSL context for HTTPS connections

    Returns:
        List of AuthToken objects

    Raises:
        AuthenticationFailed: If the token is invalid
        CannotConnect: If unable to connect to server
    """
    # Ensure we have a session
    session_provided = aiohttp_session is not None
    if aiohttp_session:
        session = aiohttp_session
    else:
        # Create session with SSL context if provided
        connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else None
        session = aiohttp.ClientSession(connector=connector)

    # Normalize server URL
    if not server_url.endswith("/"):
        server_url = f"{server_url}/"

    try:
        # Send request to list tokens
        async with session.get(
            f"{server_url}auth/tokens",
            headers={"Authorization": f"Bearer {access_token}"},
        ) as response:
            if response.status == 401:
                msg = "Invalid or expired access token"
                raise AuthenticationFailed(msg)

            if response.status != 200:
                msg = f"Failed to list tokens with status {response.status}"
                raise CannotConnect(Exception(msg))

            data = await response.json()
            return [AuthToken.from_dict(token) for token in data]

    except aiohttp.ClientError as err:
        raise CannotConnect(err) from err
    finally:
        if not session_provided:
            await session.close()


async def revoke_token(
    server_url: str,
    access_token: str,
    token_id: str,
    aiohttp_session: ClientSession | None = None,
    ssl_context: SSLContext | None = None,
) -> None:
    """
    Revoke a token.

    Args:
        server_url: The base URL of the Music Assistant server
        access_token: The access token to use
        token_id: The ID of the token to revoke
        aiohttp_session: Optional aiohttp session to use
        ssl_context: Optional SSL context for HTTPS connections

    Raises:
        AuthenticationFailed: If the token is invalid
        CannotConnect: If unable to connect to server
    """
    # Ensure we have a session
    session_provided = aiohttp_session is not None
    if aiohttp_session:
        session = aiohttp_session
    else:
        # Create session with SSL context if provided
        connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else None
        session = aiohttp.ClientSession(connector=connector)

    # Normalize server URL
    if not server_url.endswith("/"):
        server_url = f"{server_url}/"

    try:
        # Send request to revoke token
        async with session.delete(
            f"{server_url}auth/tokens/{token_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        ) as response:
            if response.status == 401:
                msg = "Invalid or expired access token"
                raise AuthenticationFailed(msg)

            if response.status != 200:
                msg = f"Failed to revoke token with status {response.status}"
                raise CannotConnect(Exception(msg))

            LOGGER.info("Successfully revoked token: %s", token_id)

    except aiohttp.ClientError as err:
        raise CannotConnect(err) from err
    finally:
        if not session_provided:
            await session.close()


async def login_with_token(
    server_url: str,
    username: str,
    password: str,
    token_name: str = "Music Assistant Client",  # noqa: S107
    aiohttp_session: ClientSession | None = None,
    ssl_context: SSLContext | None = None,
) -> tuple[User, str]:
    """
    Login and immediately create a long-lived token.

    This is a convenience method that combines login() and create_long_lived_token().

    Args:
        server_url: The base URL of the Music Assistant server
        username: The username to authenticate with
        password: The password to authenticate with
        token_name: A friendly name for the token (default: "Music Assistant Client")
        aiohttp_session: Optional aiohttp session to use
        ssl_context: Optional SSL context for HTTPS connections

    Returns:
        A tuple of (User, long_lived_token)

    Raises:
        LoginFailed: If authentication fails
        CannotConnect: If unable to connect to server
    """
    # First, login to get access token
    user, access_token = await login(server_url, username, password, aiohttp_session, ssl_context)

    # Then create a long-lived token
    long_lived_token = await create_long_lived_token(
        server_url, access_token, token_name, aiohttp_session, ssl_context
    )

    return user, long_lived_token
