"""Tests for typed listing API payloads."""

# Ruff's pytest-style rules do not apply to stdlib unittest cases.
# ruff: noqa: D101, D102, INP001, PT009

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from music_assistant_models.enums import ListingType, SortDirection, SortField

from music_assistant_client.music import Music
from music_assistant_client.player_queues import PlayerQueues


class TestSortOptions(IsolatedAsyncioTestCase):
    async def test_get_sort_options_parses_server_models(self) -> None:
        send_command = AsyncMock(
            return_value=[
                {
                    "field": "sort_name",
                    "supports_direction": True,
                    "default_direction": "asc",
                    "label_key": "sort_name",
                },
                {
                    "field": "random",
                    "supports_direction": False,
                    "default_direction": None,
                    "label_key": "random",
                },
            ]
        )
        music = Music(SimpleNamespace(send_command=send_command))  # type: ignore[arg-type]

        options = await music.get_sort_options(ListingType.LIBRARY_TRACKS)

        send_command.assert_awaited_once_with(
            "music/sort_options",
            listing=ListingType.LIBRARY_TRACKS,
            require_schema=96,
        )
        self.assertEqual(options[0].field, SortField.SORT_NAME)
        self.assertEqual(options[0].default_direction, SortDirection.ASC)
        self.assertEqual(options[1].field, SortField.RANDOM)
        self.assertFalse(options[1].supports_direction)


class TestListingPayloads(IsolatedAsyncioTestCase):
    async def test_playlist_tracks_sends_paging_and_random_seed(self) -> None:
        send_command = AsyncMock(return_value=[])
        music = Music(SimpleNamespace(send_command=send_command))  # type: ignore[arg-type]

        await music.get_playlist_tracks(
            "playlist-id",
            "provider-id",
            force_refresh=True,
            search="live",
            sort_field=SortField.NAME,
            limit=25,
            offset=50,
            random_seed=42,
        )

        send_command.assert_awaited_once_with(
            "music/playlists/playlist_tracks",
            item_id="playlist-id",
            provider_instance_id_or_domain="provider-id",
            force_refresh=True,
            allow_dynamic_tracks=True,
            strict_provider_instance=False,
            favorite=None,
            search="live",
            sort_field=SortField.NAME,
            sort_direction=None,
            limit=25,
            offset=50,
            random_seed=42,
            require_schema=98,
        )

    async def test_podcast_episodes_sends_filters_and_paging(self) -> None:
        send_command = AsyncMock(return_value=[])
        music = Music(SimpleNamespace(send_command=send_command))  # type: ignore[arg-type]

        await music.get_podcast_episodes(
            "podcast-id",
            "provider-id",
            fully_played=False,
            search="interview",
            sort_field=SortField.NAME,
            sort_direction=SortDirection.DESC,
            limit=10,
            offset=20,
            exclude_item_id="episode-id",
        )

        send_command.assert_awaited_once_with(
            "music/podcasts/podcast_episodes",
            item_id="podcast-id",
            provider_instance_id_or_domain="provider-id",
            fully_played=False,
            search="interview",
            sort_field=SortField.NAME,
            sort_direction=SortDirection.DESC,
            limit=10,
            offset=20,
            exclude_item_id="episode-id",
            random_seed=None,
            require_schema=96,
        )

    async def test_browse_and_similar_tracks_use_server_parameter_names(self) -> None:
        send_command = AsyncMock(return_value=[])
        music = Music(SimpleNamespace(send_command=send_command))  # type: ignore[arg-type]

        await music.browse("provider://", player_id="player-id", search="jazz", limit=10)
        send_command.assert_awaited_once_with(
            "music/browse",
            path="provider://",
            player_id="player-id",
            search="jazz",
            sort_field=None,
            sort_direction=None,
            limit=10,
            offset=None,
            random_seed=None,
            require_schema=96,
        )

        send_command.reset_mock()
        await music.similar_tracks(
            "track-id",
            "provider-id",
            preferred_provider_instances=["preferred-provider"],
            sort_field=SortField.NAME,
        )
        send_command.assert_awaited_once_with(
            "music/tracks/similar_tracks",
            item_id="track-id",
            provider_instance_id_or_domain="provider-id",
            limit=None,
            allow_lookup=None,
            preferred_provider_instances=["preferred-provider"],
            search=None,
            sort_field=SortField.NAME,
            sort_direction=None,
            offset=None,
            random_seed=None,
            require_schema=96,
        )

    async def test_play_media_sends_typed_sort_and_schema_requirement(self) -> None:
        send_command = AsyncMock()
        client = SimpleNamespace(
            send_command=send_command,
            subscribe=lambda *_args: None,
            server_info=SimpleNamespace(schema_version=98),
        )
        queues = PlayerQueues(client)  # type: ignore[arg-type]

        await queues.play_media(
            "queue-id",
            "album://album-id",
            sort_by="name",
            sort_field=SortField.NAME,
            sort_direction=SortDirection.DESC,
        )

        send_command.assert_awaited_once_with(
            "player_queues/play_media",
            queue_id="queue-id",
            media="album://album-id",
            option=None,
            radio_mode=False,
            start_item=None,
            sort_by=None,
            sort_field=SortField.NAME,
            sort_direction=SortDirection.DESC,
            require_schema=96,
            user=None,
        )
