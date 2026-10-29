"""Tests for the Statistics endpoints."""

from typing import Any

import pytest
from music_assistant_models.enums import MediaType
from music_assistant_models.media_items import ItemMapping
from music_assistant_models.statistics import ListeningTimeItem, TimeSeriesPoint, TopItemResult

from music_assistant_client.constants import STATISTICS_SCHEMA_VERSION
from music_assistant_client.statistics import Statistics

ARTIST = {
    "item_id": "1",
    "provider": "library",
    "name": "Artist",
    "media_type": "artist",
}


class FakeClient:
    """Records sent commands and answers with a canned result."""

    def __init__(self, result: Any) -> None:
        """Initialize with the result every command returns."""
        self.result = result
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def send_command(self, command: str, **kwargs: Any) -> Any:
        """Record the command and return the canned result."""
        self.calls.append((command, kwargs))
        return self.result


async def test_top_items_sends_command_and_parses_results() -> None:
    """Top items go out as statistics/top_items and come back as models."""
    client = FakeClient([{"item": ARTIST, "play_count": 3}])
    statistics = Statistics(client)  # type: ignore[arg-type]

    result = await statistics.get_top_items(MediaType.ARTIST, period="month", limit=5)

    assert client.calls == [
        (
            "statistics/top_items",
            {
                "require_schema": STATISTICS_SCHEMA_VERSION,
                "media_type": MediaType.ARTIST,
                "period": "month",
                "limit": 5,
                "timezone": "UTC",
            },
        )
    ]
    assert result == [TopItemResult(item=ItemMapping.from_dict(ARTIST), play_count=3)]


async def test_listening_time_keeps_the_artist() -> None:
    """Artist rows carry the artist, genre rows have none."""
    client = FakeClient(
        [{"name": "Artist", "minutes": 12.5, "item": ARTIST}, {"name": "Rock", "minutes": 4.0}]
    )
    statistics = Statistics(client)  # type: ignore[arg-type]

    result = await statistics.get_listening_time()

    assert client.calls[0][0] == "statistics/listening_time"
    assert result[0].item == ItemMapping.from_dict(ARTIST)
    assert result[1] == ListeningTimeItem(name="Rock", minutes=4.0)


@pytest.mark.parametrize(
    ("method", "command"),
    [
        ("get_play_history", "statistics/play_history"),
        ("get_genre_distribution", "statistics/genre_distribution"),
        ("get_decade_distribution", "statistics/decade_distribution"),
        ("get_plays_over_time", "statistics/plays_over_time"),
        ("get_listening_activity", "statistics/listening_activity"),
    ],
)
async def test_commands_require_the_statistics_schema(method: str, command: str) -> None:
    """Every statistics call names its command and requires the statistics schema."""
    client = FakeClient([])
    statistics = Statistics(client)  # type: ignore[arg-type]

    assert await getattr(statistics, method)() == []
    assert client.calls[0][0] == command
    assert client.calls[0][1]["require_schema"] == STATISTICS_SCHEMA_VERSION


async def test_plays_over_time_parses_points() -> None:
    """Time series points come back as models."""
    client = FakeClient([{"timestamp": "2026-10-29", "value": 0}])
    statistics = Statistics(client)  # type: ignore[arg-type]

    result = await statistics.get_plays_over_time(granularity="day")

    assert result == [TimeSeriesPoint(timestamp="2026-10-29", value=0)]


async def test_play_count_returns_the_number() -> None:
    """The play count is returned as is."""
    client = FakeClient(7)
    statistics = Statistics(client)  # type: ignore[arg-type]

    assert await statistics.get_play_count("1", "library", MediaType.ALBUM) == 7
