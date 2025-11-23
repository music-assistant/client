"""Connect to a remote Music Assistant Server using the Websocket API."""

from __future__ import annotations

import logging
import pprint
import ssl
from typing import TYPE_CHECKING, Any, cast

from aiohttp import ClientSession, ClientWebSocketResponse, WSMsgType, client_exceptions

from .exceptions import (
    CannotConnect,
    ConnectionClosed,
    ConnectionFailed,
    InvalidMessage,
    InvalidState,
    NotConnected,
)
from .helpers import json_dumps, json_loads

if TYPE_CHECKING:
    from ssl import SSLContext

LOGGER = logging.getLogger(f"{__package__}.connection")


def get_websocket_url(url: str) -> str:
    """Extract Websocket URL from (base) Music Assistant URL."""
    if not url or "://" not in url:
        msg = f"{url} is not a valid url"
        raise RuntimeError(msg)
    ws_url = url.replace("http", "ws")
    if not ws_url.endswith("/ws"):
        ws_url += "/ws"
    return ws_url.replace("//ws", "/ws")


class WebsocketsConnection:
    """Websockets connection to a Music Assistant Server."""

    def __init__(
        self,
        server_url: str,
        aiohttp_session: ClientSession | None,
        auth_token: str | None = None,
        ssl_context: SSLContext | None = None,
    ) -> None:
        """
        Initialize the WebSocket connection.

        Args:
            server_url: The base URL of the Music Assistant server
            aiohttp_session: Optional aiohttp ClientSession to use
            auth_token: Optional authentication token
            ssl_context: Optional SSL context for HTTPS connections
        """
        self.ws_server_url = get_websocket_url(server_url)
        self.auth_token = auth_token
        self.ssl_context = ssl_context
        self._aiohttp_session_provided = aiohttp_session is not None
        self._aiohttp_session: ClientSession | None = aiohttp_session or ClientSession()
        self._ws_client: ClientWebSocketResponse | None = None

    @property
    def connected(self) -> bool:
        """Return if we're currently connected."""
        return self._ws_client is not None and not self._ws_client.closed

    async def connect(self) -> dict[str, Any]:
        """Connect to the websocket server and return the first message (server info)."""
        if self._aiohttp_session is None:
            self._aiohttp_session = ClientSession()
        if self._ws_client is not None:
            msg = "Already connected"
            raise InvalidState(msg)

        LOGGER.debug("Trying to connect to %s", self.ws_server_url)
        try:
            # Determine SSL context based on URL scheme
            ssl_param: SSLContext | bool
            if self.ws_server_url.startswith("wss://") and self.ssl_context is None:
                # For secure connections without a custom SSL context, use default
                # This allows connections to work with system certificates
                ssl_param = True  # Use default SSL context from aiohttp
            elif self.ssl_context is not None:
                ssl_param = self.ssl_context
            else:
                ssl_param = False  # No SSL

            self._ws_client = await self._aiohttp_session.ws_connect(
                self.ws_server_url,
                heartbeat=55,
                compress=15,
                max_msg_size=0,
                ssl=ssl_param,
            )
            LOGGER.debug("Successfully connected to %s", self.ws_server_url)
            # receive first server info message
            return await self.receive_message()
        except ssl.SSLError as err:
            # Provide detailed SSL error information
            LOGGER.error(
                "SSL certificate verification failed when connecting to %s: %s",
                self.ws_server_url,
                err,
            )
            LOGGER.error(
                "If using a self-signed certificate or custom CA, "
                "please provide a custom ssl_context parameter"
            )
            raise CannotConnect(err) from err
        except client_exceptions.ClientConnectorCertificateError as err:
            # Specific certificate error handling
            LOGGER.error(
                "SSL certificate error when connecting to %s: %s",
                self.ws_server_url,
                err,
            )
            LOGGER.error(
                "Certificate verification failed. You may need to:"
                "\n  1. Use a valid SSL certificate signed by a trusted CA"
                "\n  2. Add your custom CA certificate to the system trust store"
                "\n  3. Provide a custom ssl_context with verify_mode=ssl.CERT_NONE "
                "(not recommended for production)"
            )
            raise CannotConnect(err) from err
        except (
            client_exceptions.WSServerHandshakeError,
            client_exceptions.ClientError,
        ) as err:
            LOGGER.error(
                "Failed to connect to %s: %s",
                self.ws_server_url,
                err,
            )
            raise CannotConnect(err) from err

    async def disconnect(self) -> None:
        """Disconnect the client."""
        LOGGER.debug("Closing client connection")
        if self._ws_client is not None and not self._ws_client.closed:
            await self._ws_client.close()
        self._ws_client = None
        if self._aiohttp_session and not self._aiohttp_session_provided:
            await self._aiohttp_session.close()
            self._aiohttp_session = None

    async def receive_message(self) -> dict[str, Any]:
        """Receive the next message from the server (or raise on error)."""
        assert self._ws_client
        ws_msg = await self._ws_client.receive()

        if ws_msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING):
            raise ConnectionClosed("Connection was closed.")

        if ws_msg.type == WSMsgType.ERROR:
            raise ConnectionFailed

        if ws_msg.type != WSMsgType.TEXT:
            raise InvalidMessage(f"Received non-Text message: {ws_msg.type}")

        try:
            msg = cast("dict[str, Any]", json_loads(ws_msg.data))
        except TypeError as err:
            raise InvalidMessage(f"Received unsupported JSON: {err}") from err
        except ValueError as err:
            raise InvalidMessage("Received invalid JSON.") from err

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug("Received message:\n%s\n", pprint.pformat(ws_msg))

        return msg

    async def send_message(self, message: dict[str, Any]) -> None:
        """
        Send a message to the server.

        Raises NotConnected if client not connected.
        """
        if not self.connected:
            raise NotConnected

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug("Publishing message:\n%s\n", pprint.pformat(message))

        assert self._ws_client
        assert isinstance(message, dict)

        await self._ws_client.send_json(message, dumps=json_dumps)

    def __repr__(self) -> str:
        """Return the representation."""
        prefix = "" if self.connected else "not "
        return f"{type(self).__name__}(ws_server_url={self.ws_server_url!r}, {prefix}connected)"
