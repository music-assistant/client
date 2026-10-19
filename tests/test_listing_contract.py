"""Tests for typed listing API payloads."""

# Ruff's pytest-style rules do not apply to stdlib unittest cases.
# ruff: noqa: D101, D102, INP001, PT009, PT027

from functools import partial
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from music_assistant_models.enums import AlbumType, ListingType, SortDirection, SortField

from music_assistant_client.client import MusicAssistantClient
from music_assistant_client.exceptions import InvalidServerVersion
from music_assistant_client.music import Music
from music_assistant_client.player_queues import PlayerQueues


class TestSortOptions(IsolatedAsyncioTestCase):
    async def test_sort_discovery_gates_each_listing_type(self) -> None:
        send_command = AsyncMock(return_value=[])
        music = Music(SimpleNamespace(send_command=send_command))  # type: ignore[arg-type]
        requirements = {
            ListingType.LIBRARY_ARTISTS: 86,
            ListingType.LIBRARY_ALBUMS: 86,
            ListingType.LIBRARY_TRACKS: 86,
            ListingType.LIBRARY_PLAYLISTS: 86,
            ListingType.LIBRARY_RADIOS: 86,
            ListingType.LIBRARY_AUDIOBOOKS: 86,
            ListingType.LIBRARY_PODCASTS: 86,
            ListingType.LIBRARY_GENRES: 86,
            ListingType.ALBUM_TRACKS: 89,
            ListingType.ARTIST_ALBUMS: 89,
            ListingType.ARTIST_TRACKS: 89,
            ListingType.ARTIST_APPEARS_ON: 89,
            ListingType.ARTIST_DISCOGRAPHY: 89,
            ListingType.ARTIST_TOP_TRACKS: 89,
            ListingType.ARTIST_TOP_ALBUMS: 89,
            ListingType.ARTIST_AUDIOBOOKS: 89,
            ListingType.SIMILAR_ARTISTS: 89,
            ListingType.SIMILAR_TRACKS: 89,
            ListingType.TRACK_ALBUMS: 89,
            ListingType.VERSIONS: 89,
            ListingType.PLAYLIST_TRACKS: 89,
            ListingType.PODCAST_EPISODES: 89,
            ListingType.GENRE_TRACKS: 89,
            ListingType.GENRE_ALBUMS: 89,
            ListingType.BROWSE: 89,
        }
        self.assertEqual(set(requirements), set(ListingType))

        for listing, schema_version in requirements.items():
            with self.subTest(listing=listing):
                await music.get_sort_options(listing)
                self.assertEqual(send_command.await_args.kwargs["require_schema"], schema_version)

    async def test_nonlibrary_discovery_rejects_older_servers_before_sending(self) -> None:
        connection = SimpleNamespace(connected=True, send_message=AsyncMock())
        client = SimpleNamespace(
            connection=connection,
            server_info=SimpleNamespace(schema_version=86),
        )
        client.send_command = partial(MusicAssistantClient.send_command, client)  # type: ignore[arg-type]
        music = Music(client)  # type: ignore[arg-type]

        with self.assertRaises(InvalidServerVersion):
            await music.get_sort_options(ListingType.ALBUM_TRACKS)

        connection.send_message.assert_not_awaited()

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
            require_schema=86,
        )
        self.assertEqual(options[0].field, SortField.SORT_NAME)
        self.assertEqual(options[0].default_direction, SortDirection.ASC)
        self.assertEqual(options[1].field, SortField.RANDOM)
        self.assertFalse(options[1].supports_direction)


class TestListingPayloads(IsolatedAsyncioTestCase):
    async def test_library_sorting_preserves_legacy_schema_requirements(self) -> None:
        send_command = AsyncMock(return_value=[])
        music = Music(SimpleNamespace(send_command=send_command))  # type: ignore[arg-type]

        for get_listing in (
            music.get_library_tracks,
            music.get_library_albums,
            music.get_library_artists,
            music.get_library_playlists,
            music.get_library_audiobooks,
            music.get_library_podcasts,
            music.get_library_radios,
        ):
            with self.subTest(method=get_listing.__name__):
                await get_listing(order_by="name", limit=10)
                self.assertIsNone(send_command.await_args.kwargs["require_schema"])

                await get_listing(user="user-id")
                self.assertEqual(send_command.await_args.kwargs["require_schema"], 35)

                await get_listing(sort_field=SortField.NAME, user="user-id")
                self.assertEqual(send_command.await_args.kwargs["require_schema"], 86)

                await get_listing(sort_field=SortField.RANDOM, random_seed=0)
                self.assertEqual(send_command.await_args.kwargs["require_schema"], 98)

    async def test_container_listings_require_their_introduction_schema(self) -> None:
        send_command = AsyncMock(return_value=[])
        music = Music(SimpleNamespace(send_command=send_command))  # type: ignore[arg-type]

        for get_listing, schema_version in (
            (music.get_album_tracks, 89),
            (music.get_track_albums, 92),
            (music.get_artist_tracks, 92),
            (music.get_artist_albums, 92),
            (music.get_playlist_tracks, 93),
            (music.get_podcast_episodes, 93),
            (music.get_track_versions, 94),
            (music.get_album_versions, 94),
            (music.get_radio_versions, 94),
            (music.audiobook_versions, 94),
            (music.podcast_versions, 94),
        ):
            with self.subTest(method=get_listing.__name__):
                await get_listing("item-id", "provider-id")
                self.assertIsNone(send_command.await_args.kwargs["require_schema"])

                await get_listing("item-id", "provider-id", sort_field=SortField.NAME)
                self.assertEqual(send_command.await_args.kwargs["require_schema"], schema_version)

                await get_listing("item-id", "provider-id", limit=10, offset=0)
                self.assertEqual(send_command.await_args.kwargs["require_schema"], schema_version)

                await get_listing("item-id", "provider-id", search="live")
                self.assertEqual(send_command.await_args.kwargs["require_schema"], schema_version)

                await get_listing("item-id", "provider-id", random_seed=0)
                self.assertEqual(send_command.await_args.kwargs["require_schema"], 98)

    async def test_new_filters_keep_schema_96_requirement(self) -> None:
        send_command = AsyncMock(return_value=[])
        music = Music(SimpleNamespace(send_command=send_command))  # type: ignore[arg-type]

        for get_listing in (
            music.get_album_tracks,
            music.get_artist_tracks,
            music.get_artist_albums,
        ):
            with self.subTest(method=get_listing.__name__):
                await get_listing("item-id", "provider-id", favorite=False)
                self.assertEqual(send_command.await_args.kwargs["require_schema"], 96)

                await get_listing("item-id", "provider-id", favorite=False, random_seed=0)
                self.assertEqual(send_command.await_args.kwargs["require_schema"], 98)

        await music.get_artist_albums("item-id", "provider-id", album_types=[AlbumType.SINGLE])
        self.assertEqual(send_command.await_args.kwargs["require_schema"], 96)

        await music.get_podcast_episodes("item-id", "provider-id", exclude_item_id="episode-id")
        self.assertEqual(send_command.await_args.kwargs["require_schema"], 96)

    async def test_original_listing_filters_do_not_require_schema_96(self) -> None:
        send_command = AsyncMock(return_value=[])
        music = Music(SimpleNamespace(send_command=send_command))  # type: ignore[arg-type]

        for get_listing in (music.get_artist_tracks, music.get_artist_albums):
            with self.subTest(method=get_listing.__name__):
                await get_listing("item-id", "provider-id", provider_filter="provider-id")
                self.assertEqual(send_command.await_args.kwargs["require_schema"], 92)

        await music.get_playlist_tracks("item-id", "provider-id", favorite=False)
        self.assertEqual(send_command.await_args.kwargs["require_schema"], 93)

        await music.get_podcast_episodes("item-id", "provider-id", fully_played=False)
        self.assertEqual(send_command.await_args.kwargs["require_schema"], 93)

    async def test_genre_options_have_independent_schema_requirements(self) -> None:
        send_command = AsyncMock(return_value=[])
        music = Music(SimpleNamespace(send_command=send_command))  # type: ignore[arg-type]

        for get_listing in (music.get_genre_tracks, music.get_genre_albums):
            with self.subTest(method=get_listing.__name__):
                await get_listing("item-id", order_by="name", limit=10, offset=0)
                self.assertIsNone(send_command.await_args.kwargs["require_schema"])

                await get_listing("item-id", sort_field=SortField.NAME, limit=10, offset=0)
                self.assertEqual(send_command.await_args.kwargs["require_schema"], 86)

                await get_listing("item-id", sort_direction=SortDirection.DESC)
                self.assertEqual(send_command.await_args.kwargs["require_schema"], 86)

                await get_listing("item-id", search="live", sort_field=SortField.NAME)
                self.assertEqual(send_command.await_args.kwargs["require_schema"], 94)

                await get_listing("item-id", search="")
                self.assertEqual(send_command.await_args.kwargs["require_schema"], 94)

                await get_listing("item-id", sort_field=SortField.RANDOM, random_seed=0)
                self.assertEqual(send_command.await_args.kwargs["require_schema"], 98)

        await music.get_library_genres(sort_field=SortField.NAME)
        self.assertEqual(send_command.await_args.kwargs["require_schema"], 86)

        await music.get_library_genres(random_seed=0)
        self.assertEqual(send_command.await_args.kwargs["require_schema"], 98)

    async def test_browse_requires_schema_94(self) -> None:
        send_command = AsyncMock(return_value=[])
        music = Music(SimpleNamespace(send_command=send_command))  # type: ignore[arg-type]

        await music.browse("provider://", sort_field=SortField.NAME, limit=10, offset=0)
        self.assertEqual(send_command.await_args.kwargs["require_schema"], 94)

        await music.browse("provider://", sort_field=SortField.RANDOM, random_seed=0)
        self.assertEqual(send_command.await_args.kwargs["require_schema"], 98)

    async def test_playlist_dynamic_refresh_is_opt_in(self) -> None:
        send_command = AsyncMock(return_value=[])
        music = Music(SimpleNamespace(send_command=send_command))  # type: ignore[arg-type]

        await music.get_playlist_tracks("playlist-id", "provider-id", limit=25, offset=25)

        self.assertFalse(send_command.await_args.kwargs["force_refresh"])
        self.assertFalse(send_command.await_args.kwargs["allow_dynamic_tracks"])

        await music.get_playlist_tracks("playlist-id", "provider-id", allow_dynamic_tracks=True)

        self.assertTrue(send_command.await_args.kwargs["allow_dynamic_tracks"])

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
            allow_dynamic_tracks=False,
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
            require_schema=94,
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
            require_schema=94,
        )

        send_command.reset_mock()
        await music.similar_tracks("track-id", "provider-id", limit=25)
        send_command.assert_awaited_once_with(
            "music/tracks/similar_tracks",
            item_id="track-id",
            provider_instance_id_or_domain="provider-id",
            limit=25,
            allow_lookup=None,
            preferred_provider_instances=None,
            search=None,
            sort_field=None,
            sort_direction=None,
            offset=None,
            random_seed=None,
            require_schema=None,
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
            require_schema=95,
            user=None,
        )
