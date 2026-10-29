"""Handle Statistics related endpoints for Music Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast

from music_assistant_models.media_items import ItemMapping
from music_assistant_models.statistics import (
    DistributionItem,
    HeatmapPoint,
    ListeningTimeItem,
    TimeSeriesPoint,
    TopItemResult,
)

if TYPE_CHECKING:
    from music_assistant_models.enums import MediaType

    from .client import MusicAssistantClient

# TODO: set to the server schema that makes statistics/* a public api contract
STATISTICS_SCHEMA_VERSION = 101

StatisticsPeriod = Literal["today", "week", "month", "year", "all_time"]
StatisticsGranularity = Literal["hour", "day", "week", "month"]
ListeningTimeGroup = Literal["artist", "genre"]


class Statistics:
    """
    Statistics related endpoints for Music Assistant.

    All statistics are scoped to the user the client is authenticated as. A ``timezone``
    is an IANA name (e.g. "Europe/Berlin") that sets the calendar boundaries and buckets.
    """

    def __init__(self, client: MusicAssistantClient) -> None:
        """Initialize Statistics controller."""
        self.client = client

    async def get_play_history(
        self,
        limit: int = 50,
        media_types: list[MediaType] | None = None,
        played_after_timestamp: int | None = None,
        offset: int = 0,
    ) -> list[ItemMapping]:
        """
        Get the play history, most recent first.

        :param limit: Maximum number of items to return.
        :param media_types: Only return plays of these media types.
        :param played_after_timestamp: Only return plays after this unix timestamp.
        :param offset: Number of matching items to skip.
        """
        result = await self._send(
            "statistics/play_history",
            limit=limit,
            media_types=media_types,
            played_after_timestamp=played_after_timestamp,
            offset=offset,
        )
        return [ItemMapping.from_dict(item) for item in result]

    async def get_top_items(
        self,
        media_type: MediaType,
        period: StatisticsPeriod = "week",
        limit: int = 50,
        timezone: str = "UTC",
    ) -> list[TopItemResult]:
        """
        Get the most played items of a media type in a period.

        :param media_type: The media type to rank.
        :param period: The period to count plays in.
        :param limit: Maximum number of items to return.
        :param timezone: IANA timezone for the period boundaries.
        """
        result = await self._send(
            "statistics/top_items",
            media_type=media_type,
            period=period,
            limit=limit,
            timezone=timezone,
        )
        return [TopItemResult.from_dict(item) for item in result]

    async def get_genre_distribution(
        self,
        period: StatisticsPeriod = "week",
        limit: int = 10,
        timezone: str = "UTC",
    ) -> list[DistributionItem]:
        """
        Get play counts per genre in a period.

        :param period: The period to count plays in.
        :param limit: Maximum number of genres to return.
        :param timezone: IANA timezone for the period boundaries.
        """
        result = await self._send(
            "statistics/genre_distribution",
            period=period,
            limit=limit,
            timezone=timezone,
        )
        return [DistributionItem.from_dict(item) for item in result]

    async def get_decade_distribution(
        self,
        period: StatisticsPeriod = "all_time",
        limit: int = 10,
        timezone: str = "UTC",
    ) -> list[DistributionItem]:
        """
        Get play counts per release decade in a period.

        :param period: The period to count plays in.
        :param limit: Maximum number of decades to return.
        :param timezone: IANA timezone for the period boundaries.
        """
        result = await self._send(
            "statistics/decade_distribution",
            period=period,
            limit=limit,
            timezone=timezone,
        )
        return [DistributionItem.from_dict(item) for item in result]

    async def get_play_count(self, item_id: str, provider: str, media_type: MediaType) -> int:
        """
        Get how often an item was played.

        Albums count the plays of their tracks and artists the plays of tracks they are
        credited on.

        :param item_id: The item id.
        :param provider: The provider instance id or domain of the item.
        :param media_type: The media type of the item.
        """
        return cast(
            "int",
            await self._send(
                "statistics/play_count",
                item_id=item_id,
                provider=provider,
                media_type=media_type,
            ),
        )

    async def get_plays_over_time(
        self,
        period: StatisticsPeriod = "week",
        granularity: StatisticsGranularity = "day",
        timezone: str = "UTC",
    ) -> list[TimeSeriesPoint]:
        """
        Get play counts per time bucket, oldest first.

        :param period: The period to cover.
        :param granularity: The size of each bucket.
        :param timezone: IANA timezone for the buckets and period boundaries.
        """
        result = await self._send(
            "statistics/plays_over_time",
            period=period,
            granularity=granularity,
            timezone=timezone,
        )
        return [TimeSeriesPoint.from_dict(item) for item in result]

    async def get_listening_activity(
        self,
        period: StatisticsPeriod = "week",
        timezone: str = "UTC",
    ) -> list[HeatmapPoint]:
        """
        Get play counts per weekday and hour of day.

        :param period: The period to count plays in.
        :param timezone: IANA timezone for the hours and period boundaries.
        """
        result = await self._send(
            "statistics/listening_activity",
            period=period,
            timezone=timezone,
        )
        return [HeatmapPoint.from_dict(item) for item in result]

    async def get_listening_time(
        self,
        period: StatisticsPeriod = "week",
        group_by: ListeningTimeGroup = "artist",
        limit: int = 10,
        timezone: str = "UTC",
    ) -> list[ListeningTimeItem]:
        """
        Get the listening time per artist or genre in a period.

        :param period: The period to sum listening time in.
        :param group_by: Group the results by artist or by genre.
        :param limit: Maximum number of results to return.
        :param timezone: IANA timezone for the period boundaries.
        """
        result = await self._send(
            "statistics/listening_time",
            period=period,
            group_by=group_by,
            limit=limit,
            timezone=timezone,
        )
        return [ListeningTimeItem.from_dict(item) for item in result]

    async def _send(self, command: str, **kwargs: Any) -> Any:
        """Send a statistics command, requiring a server that offers it."""
        return await self.client.send_command(
            command, require_schema=STATISTICS_SCHEMA_VERSION, **kwargs
        )
