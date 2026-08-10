"""Handle Dashboard related endpoints for Music Assistant."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast

from music_assistant_models.dashboard import DashboardDevice, DashboardSession
from music_assistant_models.enums import EventType

if TYPE_CHECKING:
    from music_assistant_models.enums import DashboardType
    from music_assistant_models.event import MassEvent

    from .client import MusicAssistantClient

# the dashboard/* commands landed in the server api at schema 39
DASHBOARD_SCHEMA_VERSION = 39

OnShowCallback = Callable[[DashboardSession], Awaitable[None] | None]
OnHideCallback = Callable[[], Awaitable[None] | None]


class Dashboard:
    """Dashboard related endpoints/data for Music Assistant."""

    def __init__(self, client: MusicAssistantClient) -> None:
        """Handle Initialization."""
        self.client = client
        # subscribe to dashboard events
        client.subscribe(
            self._handle_updated_event,
            (EventType.DASHBOARDS_UPDATED, EventType.DASHBOARD_SESSIONS_UPDATED),
        )
        client.subscribe(
            self._handle_intent_event,
            (EventType.DASHBOARD_SHOW, EventType.DASHBOARD_HIDE),
        )
        # the initial items are retrieved after connect
        self._dashboards: dict[str, DashboardDevice] = {}
        self._sessions: dict[str, DashboardSession] = {}
        self._on_show_callbacks: dict[str, OnShowCallback | None] = {}
        self._on_hide_callbacks: dict[str, OnHideCallback | None] = {}

    @property
    def dashboards(self) -> list[DashboardDevice]:
        """Return all registered dashboard endpoints."""
        return list(self._dashboards.values())

    @property
    def sessions(self) -> list[DashboardSession]:
        """Return all active dashboard cast sessions."""
        return list(self._sessions.values())

    def get(self, dashboard_id: str) -> DashboardDevice | None:
        """Return a registered dashboard endpoint by id (or None if not found)."""
        return self._dashboards.get(dashboard_id)

    def get_session(self, dashboard_id: str) -> DashboardSession | None:
        """Return the active session on a dashboard endpoint by id (or None if not found)."""
        return self._sessions.get(dashboard_id)

    async def register(
        self,
        dashboard_id: str,
        name: str,
        supported_types: set[DashboardType] | None = None,
        provider_domain_hint: str | None = None,
        on_show: OnShowCallback | None = None,
        on_hide: OnHideCallback | None = None,
    ) -> None:
        """
        Register this client as a dashboard endpoint.

        The registration belongs to the current connection, so it must be repeated
        after a reconnect.

        :param dashboard_id: Unique id chosen by the registering client.
        :param name: Display name for the dashboard endpoint.
        :param supported_types: Dashboard types this endpoint can show, defaults to all
            types; an explicitly empty set is rejected.
        :param provider_domain_hint: Optional provider domain used to resolve the endpoint's icon.
        :param on_show: Called with the DashboardSession when a show intent is received.
        :param on_hide: Called with no arguments when a hide intent is received.
        """
        await self.client.send_command(
            "dashboard/register",
            dashboard_id=dashboard_id,
            name=name,
            supported_types=supported_types,
            provider_domain_hint=provider_domain_hint,
            require_schema=DASHBOARD_SCHEMA_VERSION,
        )
        self._on_show_callbacks[dashboard_id] = on_show
        self._on_hide_callbacks[dashboard_id] = on_hide

    async def unregister(self, dashboard_id: str) -> None:
        """Unregister a dashboard endpoint, dropping any active session for it."""
        await self.client.send_command(
            "dashboard/unregister",
            dashboard_id=dashboard_id,
            require_schema=DASHBOARD_SCHEMA_VERSION,
        )
        self._on_show_callbacks.pop(dashboard_id, None)
        self._on_hide_callbacks.pop(dashboard_id, None)

    async def show(
        self, dashboard_id: str, dashboard: DashboardType, player_id: str | None = None
    ) -> None:
        """
        Show a Music Assistant dashboard on a registered dashboard endpoint.

        Requires a token with the `users.invite` scope.

        :param dashboard_id: Id of a registered dashboard endpoint.
        :param dashboard: Dashboard to show.
        :param player_id: Player to show, required when dashboard is NOW_PLAYING.
        """
        await self.client.send_command(
            "dashboard/show",
            dashboard_id=dashboard_id,
            dashboard=dashboard,
            player_id=player_id,
            require_schema=DASHBOARD_SCHEMA_VERSION,
        )

    async def hide(self, dashboard_id: str) -> None:
        """
        Hide a Music Assistant dashboard from a registered dashboard endpoint.

        Requires a token with the `users.invite` scope.
        """
        await self.client.send_command(
            "dashboard/hide",
            dashboard_id=dashboard_id,
            require_schema=DASHBOARD_SCHEMA_VERSION,
        )

    async def get_url(
        self,
        dashboard: DashboardType,
        player_id: str | None = None,
        prefer_local: bool = False,
    ) -> str:
        """
        Return a fully-qualified dashboard URL for this client to load itself.

        Requires a token with the `users.invite` scope, or an active session of
        this endpoint's own that matches the requested dashboard.

        :param dashboard: Dashboard to load.
        :param player_id: Player to show, required when dashboard is NOW_PLAYING.
        :param prefer_local: Return the plain local base url, for native LAN viewers.
        """
        return cast(
            "str",
            await self.client.send_command(
                "dashboard/get_url",
                dashboard=dashboard,
                player_id=player_id,
                prefer_local=prefer_local,
                require_schema=DASHBOARD_SCHEMA_VERSION,
            ),
        )

    async def fetch_state(self) -> None:
        """Fetch initial state once the server is connected."""
        server_info = self.client.server_info
        # a server without the dashboard commands leaves both caches empty
        if server_info is None or server_info.schema_version < DASHBOARD_SCHEMA_VERSION:
            return
        self._dashboards = {item.dashboard_id: item for item in await self._get_dashboards()}
        self._sessions = {item.dashboard_id: item for item in await self._get_sessions()}

    def _handle_updated_event(self, event: MassEvent) -> None:
        """Handle incoming dashboards/sessions updated event."""
        if event.event == EventType.DASHBOARDS_UPDATED:
            devices = [DashboardDevice.from_dict(item) for item in event.data]
            self._dashboards = {device.dashboard_id: device for device in devices}
            return
        if event.event == EventType.DASHBOARD_SESSIONS_UPDATED:
            sessions = [DashboardSession.from_dict(item) for item in event.data]
            self._sessions = {session.dashboard_id: session for session in sessions}

    async def _handle_intent_event(self, event: MassEvent) -> None:
        """Handle incoming dashboard show/hide intent event."""
        # dashboard show/hide events always have an object id
        assert event.object_id
        dashboard_id = event.object_id
        if event.event == EventType.DASHBOARD_SHOW:
            if on_show := self._on_show_callbacks.get(dashboard_id):
                show_result = on_show(DashboardSession.from_dict(event.data))
                if inspect.isawaitable(show_result):
                    await show_result
            return
        if event.event == EventType.DASHBOARD_HIDE and (
            on_hide := self._on_hide_callbacks.get(dashboard_id)
        ):
            hide_result = on_hide()
            if inspect.isawaitable(hide_result):
                await hide_result

    async def _get_dashboards(self) -> list[DashboardDevice]:
        """Fetch all registered dashboard endpoints from the server."""
        return [
            DashboardDevice.from_dict(item)
            for item in await self.client.send_command(
                "dashboard/dashboards", require_schema=DASHBOARD_SCHEMA_VERSION
            )
        ]

    async def _get_sessions(self) -> list[DashboardSession]:
        """Fetch all active dashboard cast sessions from the server."""
        return [
            DashboardSession.from_dict(item)
            for item in await self.client.send_command(
                "dashboard/sessions", require_schema=DASHBOARD_SCHEMA_VERSION
            )
        ]
