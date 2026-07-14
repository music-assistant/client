"""Tests for player queue endpoints."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from music_assistant_models.api import ServerInfoMessage
from music_assistant_models.audio_processing import AudioProcessingChain
from music_assistant_models.enums import EventType
from music_assistant_models.event import MassEvent

from music_assistant_client.client import MusicAssistantClient
from music_assistant_client.exceptions import InvalidServerVersion
from music_assistant_client.player_queues import PlayerQueues

AUDIO_PROCESSING_DATA: dict[str, Any] = {
    "queue_id": "queue-1",
    "queue_item_id": "item-1",
    "revision": 4,
    "state": "ready",
    "outputs": [{"player_ids": ["player-1"]}],
}


def create_player_queues(
    command_result: dict[str, Any] | None,
) -> tuple[PlayerQueues, AsyncMock, Mock]:
    """Create a player queue controller with a mocked client."""
    client = Mock(spec=MusicAssistantClient)
    send_command = AsyncMock(return_value=command_result)
    client.send_command = send_command
    controller = PlayerQueues(cast("MusicAssistantClient", client))
    return controller, send_command, client.subscribe


class PlayerQueuesTest(IsolatedAsyncioTestCase):
    """Test player queue endpoints."""

    async def test_get_audio_processing_chain(self) -> None:
        """Test command arguments and result parsing."""
        controller, send_command, _ = create_player_queues(AUDIO_PROCESSING_DATA)

        result = await controller.get_audio_processing_chain("queue-1")

        send_command.assert_awaited_once_with(
            "player_queues/audio_processing_chain",
            queue_id="queue-1",
            require_schema=38,
        )
        assert isinstance(result, AudioProcessingChain)
        assert result.queue_id == "queue-1"
        assert result.revision == 4
        assert result.outputs[0].player_ids == ["player-1"]

    async def test_get_audio_processing_chain_returns_none(self) -> None:
        """Test a missing audio processing snapshot."""
        controller, _, _ = create_player_queues(None)

        assert await controller.get_audio_processing_chain("queue-1") is None

    async def test_subscribe_audio_processing(self) -> None:
        """Test typed full snapshot and clear events."""
        controller, _, subscribe = create_player_queues(None)
        unsubscribe = Mock()
        subscribe.return_value = unsubscribe
        updates: list[tuple[str, AudioProcessingChain | None]] = []

        async def handle_update(queue_id: str, chain: AudioProcessingChain | None) -> None:
            updates.append((queue_id, chain))

        remove_listener = controller.subscribe_audio_processing(handle_update, "queue-1")
        event_handler: Callable[[MassEvent], Any] = subscribe.call_args.args[0]

        await event_handler(
            MassEvent(
                event=EventType.AUDIO_PROCESSING_UPDATED,
                object_id="queue-1",
                data=AUDIO_PROCESSING_DATA,
            )
        )
        await event_handler(
            MassEvent(
                event=EventType.AUDIO_PROCESSING_UPDATED,
                object_id="queue-1",
                data=None,
            )
        )

        assert remove_listener is unsubscribe
        assert subscribe.call_args.args[1:] == (
            EventType.AUDIO_PROCESSING_UPDATED,
            "queue-1",
        )
        assert updates[0][0] == "queue-1"
        assert isinstance(updates[0][1], AudioProcessingChain)
        assert updates[0][1].revision == 4
        assert updates[1] == ("queue-1", None)

    async def test_audio_processing_chain_requires_schema_38(self) -> None:
        """Test rejection by servers without audio processing support."""
        client = MusicAssistantClient("http://example.test", Mock())
        client.connection = Mock()
        client.connection.connected = True
        client._server_info = ServerInfoMessage(  # noqa: SLF001
            server_id="server",
            server_version="0.0.0",
            schema_version=37,
            min_supported_schema_version=33,
        )

        with self.assertRaisesRegex(InvalidServerVersion, "api schema 38"):  # noqa: PT027
            await client.player_queues.get_audio_processing_chain("queue-1")

        client.connection.send_message.assert_not_called()
