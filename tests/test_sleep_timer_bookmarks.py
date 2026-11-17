"""Tests for the sleep timer and bookmark commands."""

from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from music_assistant_models.enums import MediaType, SleepTimerMode

from music_assistant_client.helpers import LinkedUser
from music_assistant_client.music import Music
from music_assistant_client.players import Players

SOFT_USER = LinkedUser(provider="homeassistant", user_id="ha_user_1", required=False)

type Call = Callable[[SimpleNamespace], Awaitable[object]]

CALLS = [
    pytest.param(
        lambda c: c.players.set_sleep_timer("player_1", 60, user=SOFT_USER),
        "players/sleep_timer/set",
        {"player_id": "player_1", "seconds": 60},
        None,
        id="set_sleep_timer",
    ),
    pytest.param(
        lambda c: c.players.set_sleep_timer(
            "player_1", mode=SleepTimerMode.END_OF_ITEM, user=SOFT_USER
        ),
        "players/sleep_timer/set",
        {"player_id": "player_1", "seconds": None, "mode": SleepTimerMode.END_OF_ITEM},
        105,
        id="set_sleep_timer_end_of_item",
    ),
    pytest.param(
        lambda c: c.players.get_sleep_timer("player_1", user=SOFT_USER),
        "players/sleep_timer/get",
        {"player_id": "player_1"},
        None,
        id="get_sleep_timer",
    ),
    pytest.param(
        lambda c: c.players.clear_sleep_timer("player_1", user=SOFT_USER),
        "players/sleep_timer/clear",
        {"player_id": "player_1"},
        None,
        id="clear_sleep_timer",
    ),
    pytest.param(
        lambda c: c.music.get_bookmarks(MediaType.AUDIOBOOK, "book_1", "library", user=SOFT_USER),
        "music/bookmarks",
        {
            "media_type": MediaType.AUDIOBOOK,
            "item_id": "book_1",
            "provider_instance_id_or_domain": "library",
        },
        102,
        id="get_bookmarks",
    ),
    pytest.param(
        lambda c: c.music.set_bookmark(
            MediaType.AUDIOBOOK, "abs_1", "book_1", 90.0, "Chapter 2", user=SOFT_USER
        ),
        "music/set_bookmark",
        {
            "media_type": MediaType.AUDIOBOOK,
            "provider_instance_id": "abs_1",
            "provider_item_id": "book_1",
            "start": 90.0,
            "name": "Chapter 2",
        },
        102,
        id="set_bookmark",
    ),
    pytest.param(
        lambda c: c.music.remove_bookmark(
            MediaType.AUDIOBOOK, "abs_1", "book_1", 90.0, user=SOFT_USER
        ),
        "music/remove_bookmark",
        {
            "media_type": MediaType.AUDIOBOOK,
            "provider_instance_id": "abs_1",
            "provider_item_id": "book_1",
            "start": 90.0,
        },
        102,
        id="remove_bookmark",
    ),
]


def _client(schema_version: int) -> SimpleNamespace:
    client = SimpleNamespace(
        send_command=AsyncMock(
            side_effect=lambda command, **_: [] if command == "music/bookmarks" else None
        ),
        subscribe=lambda *_args: None,
        server_info=SimpleNamespace(schema_version=schema_version),
    )
    client.players = Players(client)  # type: ignore[arg-type]
    client.music = Music(client)  # type: ignore[arg-type]
    return client


@pytest.mark.parametrize(("call", "command", "payload", "gate"), CALLS)
async def test_a_soft_user_is_dropped_before_schema_117(
    call: Call, command: str, payload: dict[str, Any], gate: int | None
) -> None:
    """A server older than 117 runs the command as the connected account."""
    client = _client(105)
    await call(client)
    client.send_command.assert_awaited_once_with(command, **payload, require_schema=gate)


@pytest.mark.parametrize(("call", "command", "payload", "gate"), CALLS)
async def test_the_user_is_sent_from_schema_117(
    call: Call, command: str, payload: dict[str, Any], gate: int | None
) -> None:
    """From schema 117 the command runs as the given user."""
    del gate
    client = _client(117)
    await call(client)
    client.send_command.assert_awaited_once_with(
        command, **payload, require_schema=117, user=SOFT_USER
    )
