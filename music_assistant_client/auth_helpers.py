"""Authentication helpers for Music Assistant Client."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import aiohttp
from music_assistant_models.api import ServerInfoMessage
from music_assistant_models.auth import User
from music_assistant_models.errors import LoginFailed

from .client import MusicAssistantClient
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

    This uses the HTTP REST endpoint /auth/login which is the only auth endpoint
    available without an existing token.

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

    This is a convenience method that:
    1. Logs in with username/password to get a session token
    2. Connects a MusicAssistantClient with that token
    3. Creates a long-lived token via the API
    4. Returns the user and long-lived token

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

    # Create a client with the session token and create a long-lived token
    async with MusicAssistantClient(
        server_url, aiohttp_session, access_token, ssl_context
    ) as client:
        long_lived_token = await client.auth.create_token(token_name)
        LOGGER.info("Successfully created long-lived token: %s", token_name)
        return user, long_lived_token


async def create_long_lived_token(
    server_url: str,
    access_token: str,
    token_name: str = "Music Assistant Client",  # noqa: S107
    aiohttp_session: ClientSession | None = None,
    ssl_context: SSLContext | None = None,
) -> str:
    """
    Create a long-lived token using an existing session token.

    Args:
        server_url: The base URL of the Music Assistant server
        access_token: An existing session token (from login)
        token_name: A friendly name for the token (default: "Music Assistant Client")
        aiohttp_session: Optional aiohttp session to use
        ssl_context: Optional SSL context for HTTPS connections

    Returns:
        The long-lived token string

    Raises:
        CannotConnect: If unable to connect to server
    """
    async with MusicAssistantClient(
        server_url, aiohttp_session, access_token, ssl_context
    ) as client:
        long_lived_token = await client.auth.create_token(token_name)
        LOGGER.info("Successfully created long-lived token: %s", token_name)
        return long_lived_token


async def get_server_info(
    server_url: str,
    aiohttp_session: ClientSession | None = None,
    ssl_context: SSLContext | None = None,
) -> ServerInfoMessage:
    """
    Get server information from the /info endpoint.

    This endpoint does not require authentication and can be used to check
    server availability and get basic server information like version and schema.

    Args:
        server_url: The base URL of the Music Assistant server
        aiohttp_session: Optional aiohttp session to use
        ssl_context: Optional SSL context for HTTPS connections

    Returns:
        ServerInfoMessage with server details

    Raises:
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
        async with session.get(f"{server_url}info") as response:
            if response.status != 200:
                msg = f"Failed to get server info with status {response.status}"
                raise CannotConnect(Exception(msg))

            data = await response.json()
            return ServerInfoMessage.from_dict(data)

    except aiohttp.ClientError as err:
        raise CannotConnect(err) from err
    finally:
        if not session_provided:
            await session.close()
