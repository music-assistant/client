"""Tests for the PlayerQueues cache."""

from collections.abc import Callable
from types import SimpleNamespace

from music_assistant_models.enums import EventType, PlaybackState
from music_assistant_models.event import MassEvent
from music_assistant_models.player_queue import PlayerQueue

from music_assistant_client.player_queues import PlayerQueues


def test_player_removed_drops_queue() -> None:
    """A removed player's queue leaves the cache after its final idle update."""
    listeners: list[tuple[Callable[[MassEvent], None], tuple[EventType, ...]]] = []

    def dispatch(event: MassEvent) -> None:
        for cb_func, event_filter in listeners:
            if event.event in event_filter:
                cb_func(event)

    queues = PlayerQueues(
        SimpleNamespace(subscribe=lambda cb, events: listeners.append((cb, events)))  # type: ignore[arg-type]
    )
    queue = PlayerQueue(
        queue_id="player_1",
        active=False,
        display_name="Player 1",
        available=True,
        items=0,
        state=PlaybackState.IDLE,
    )

    dispatch(MassEvent(event=EventType.QUEUE_UPDATED, object_id="player_1", data=queue.to_dict()))
    assert queues.get("player_1") is not None
    dispatch(MassEvent(event=EventType.PLAYER_REMOVED, object_id="player_1"))

    assert queues.get("player_1") is None
