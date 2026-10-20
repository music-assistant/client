"""Tests for typed listing API payloads."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientSession
from music_assistant_models.api import ServerInfoMessage
from music_assistant_models.enums import AlbumType, ListingType, SortDirection, SortField

from music_assistant_client.client import MusicAssistantClient
from music_assistant_client.exceptions import InvalidServerVersion
from music_assistant_client.music import Music, _listing_require_schema
from music_assistant_client.player_queues import PlayerQueues


@pytest.fixture
def send_command() -> AsyncMock:
    """Capture API payloads without sending commands."""
    return AsyncMock(return_value=[])


@pytest.fixture
def music(send_command: AsyncMock) -> Music:
    """Provide music wrappers backed by the captured command transport."""
    return Music(SimpleNamespace(send_command=send_command))  # type: ignore[arg-type]


@pytest.fixture
def queues(send_command: AsyncMock) -> PlayerQueues:
    """Provide queue wrappers backed by the captured command transport."""
    client = SimpleNamespace(
        send_command=send_command,
        subscribe=lambda *_args: None,
        server_info=SimpleNamespace(schema_version=98),
    )
    return PlayerQueues(client)  # type: ignore[arg-type]


@pytest.fixture
def older_server_client(monkeypatch: pytest.MonkeyPatch) -> tuple[MusicAssistantClient, AsyncMock]:
    """Use the real version guard with an older server and a mocked connection."""
    client = MusicAssistantClient("http://localhost:8095", MagicMock(spec=ClientSession))
    monkeypatch.setattr(
        client, "_server_info", MagicMock(spec=ServerInfoMessage, schema_version=86)
    )
    monkeypatch.setattr(client.connection, "_ws_client", MagicMock(closed=False))
    send_message = AsyncMock()
    monkeypatch.setattr(client.connection, "send_message", send_message)
    return client, send_message


async def test_sort_discovery_gates_each_listing_type(
    send_command: AsyncMock, music: Music
) -> None:
    """Sort discovery gates each listing type."""
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
    assert set(requirements) == set(ListingType)
    for listing, schema_version in requirements.items():
        await music.get_sort_options(listing)
        assert send_command.await_args.kwargs["require_schema"] == schema_version


async def test_nonlibrary_discovery_rejects_older_servers_before_sending(
    older_server_client: tuple[MusicAssistantClient, AsyncMock],
) -> None:
    """Reject nonlibrary discovery before sending to an older server."""
    client, send_message = older_server_client
    with pytest.raises(InvalidServerVersion):
        await client.music.get_sort_options(ListingType.ALBUM_TRACKS)
    send_message.assert_not_awaited()


async def test_get_sort_options_parses_server_models(send_command: AsyncMock, music: Music) -> None:
    """Get sort options parses server models."""
    send_command.return_value = [
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
    options = await music.get_sort_options(ListingType.LIBRARY_TRACKS)
    send_command.assert_awaited_once_with(
        "music/sort_options", listing=ListingType.LIBRARY_TRACKS, require_schema=86
    )
    assert options[0].field == SortField.SORT_NAME
    assert options[0].default_direction == SortDirection.ASC
    assert options[1].field == SortField.RANDOM
    assert not options[1].supports_direction


def test_schema_requirements_are_combined_without_ordering_assumptions() -> None:
    """Schema requirements are combined without ordering assumptions."""
    assert _listing_require_schema() is None
    assert _listing_require_schema((110, None), (98, None, None)) is None
    assert _listing_require_schema((110, "x"), (98, 1), (96, True)) == 110
    assert _listing_require_schema((96, "x"), (110, None), (98, 0)) == 98
    assert _listing_require_schema((31, None, False), (35, "user")) == 35


async def test_artist_listings_do_not_forward_deprecated_library_filter(
    send_command: AsyncMock, music: Music
) -> None:
    """Artist listings do not forward deprecated library filter."""
    for get_listing in (music.get_artist_tracks, music.get_artist_albums):
        for in_library_only in (False, True):
            await get_listing("artist-id", "provider-id", in_library_only)
            assert "in_library_only" not in send_command.await_args.kwargs
            assert send_command.await_args.kwargs["require_schema"] is None


async def test_library_sorting_preserves_legacy_schema_requirements(
    send_command: AsyncMock, music: Music
) -> None:
    """Library sorting preserves legacy schema requirements."""
    for get_listing in (
        music.get_library_tracks,
        music.get_library_albums,
        music.get_library_artists,
        music.get_library_playlists,
        music.get_library_audiobooks,
        music.get_library_podcasts,
        music.get_library_radios,
    ):
        await get_listing(order_by="name", limit=10)
        assert send_command.await_args.kwargs["require_schema"] is None
        await get_listing(user="user-id")
        assert send_command.await_args.kwargs["require_schema"] == 35
        await get_listing(sort_field=SortField.NAME, user="user-id")
        assert send_command.await_args.kwargs["require_schema"] == 86
        await get_listing(sort_field=SortField.RANDOM, random_seed=0)
        assert send_command.await_args.kwargs["require_schema"] == 98


async def test_container_listings_require_their_introduction_schema(
    send_command: AsyncMock, music: Music
) -> None:
    """Container listings require their introduction schema."""
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
        await get_listing("item-id", "provider-id")
        assert send_command.await_args.kwargs["require_schema"] is None
        await get_listing("item-id", "provider-id", sort_field=SortField.NAME)
        assert send_command.await_args.kwargs["require_schema"] == schema_version
        await get_listing("item-id", "provider-id", limit=10, offset=0)
        assert send_command.await_args.kwargs["require_schema"] == schema_version
        await get_listing("item-id", "provider-id", search="live")
        assert send_command.await_args.kwargs["require_schema"] == schema_version
        await get_listing("item-id", "provider-id", random_seed=0)
        assert send_command.await_args.kwargs["require_schema"] == 98


async def test_new_filters_keep_schema_96_requirement(
    send_command: AsyncMock, music: Music
) -> None:
    """New filters keep schema 96 requirement."""
    for get_listing in (music.get_album_tracks, music.get_artist_tracks, music.get_artist_albums):
        await get_listing("item-id", "provider-id", favorite=False)
        assert send_command.await_args.kwargs["require_schema"] == 96
        await get_listing("item-id", "provider-id", favorite=False, random_seed=0)
        assert send_command.await_args.kwargs["require_schema"] == 98
    await music.get_artist_albums("item-id", "provider-id", album_types=[AlbumType.SINGLE])
    assert send_command.await_args.kwargs["require_schema"] == 96
    await music.get_podcast_episodes("item-id", "provider-id", exclude_item_id="episode-id")
    assert send_command.await_args.kwargs["require_schema"] == 96


async def test_original_listing_filters_do_not_require_schema_96(
    send_command: AsyncMock, music: Music
) -> None:
    """Original listing filters do not require schema 96."""
    for get_listing in (music.get_artist_tracks, music.get_artist_albums):
        await get_listing("item-id", "provider-id", provider_filter="provider-id")
        assert send_command.await_args.kwargs["require_schema"] == 32
        await get_listing("item-id", "provider-id", provider_filter="provider-id", limit=10)
        assert send_command.await_args.kwargs["require_schema"] == 92
        await get_listing("item-id", "provider-id", provider_filter="provider-id", favorite=False)
        assert send_command.await_args.kwargs["require_schema"] == 96
        await get_listing("item-id", "provider-id", provider_filter="provider-id", random_seed=0)
        assert send_command.await_args.kwargs["require_schema"] == 98
    await music.get_playlist_tracks("item-id", "provider-id", favorite=False)
    assert send_command.await_args.kwargs["require_schema"] == 93
    await music.get_podcast_episodes("item-id", "provider-id", fully_played=False)
    assert send_command.await_args.kwargs["require_schema"] == 93


async def test_genre_listing_does_not_send_unsupported_genre_filter(
    send_command: AsyncMock, music: Music
) -> None:
    """Genre listing does not send unsupported genre filter."""
    await music.get_library_genres(provider="provider-id", hide_empty=True)
    assert "genre" not in send_command.await_args.kwargs
    assert send_command.await_args.kwargs["provider"] == "provider-id"
    assert send_command.await_args.kwargs["hide_empty"]
    with pytest.raises(TypeError):
        await music.get_library_genres(genre=1)


async def test_genre_options_have_independent_schema_requirements(
    send_command: AsyncMock, music: Music
) -> None:
    """Genre options have independent schema requirements."""
    for get_listing in (music.get_genre_tracks, music.get_genre_albums):
        await get_listing("item-id", order_by="name", limit=10, offset=0)
        assert send_command.await_args.kwargs["require_schema"] is None
        await get_listing("item-id", sort_field=SortField.NAME, limit=10, offset=0)
        assert send_command.await_args.kwargs["require_schema"] == 86
        await get_listing("item-id", sort_direction=SortDirection.DESC)
        assert send_command.await_args.kwargs["require_schema"] == 86
        await get_listing("item-id", search="live", sort_field=SortField.NAME)
        assert send_command.await_args.kwargs["require_schema"] == 94
        await get_listing("item-id", search="")
        assert send_command.await_args.kwargs["require_schema"] == 94
        await get_listing("item-id", sort_field=SortField.RANDOM, random_seed=0)
        assert send_command.await_args.kwargs["require_schema"] == 98
    await music.get_library_genres(sort_field=SortField.NAME)
    assert send_command.await_args.kwargs["require_schema"] == 86
    await music.get_library_genres(random_seed=0)
    assert send_command.await_args.kwargs["require_schema"] == 98


async def test_browse_requires_schema_94(send_command: AsyncMock, music: Music) -> None:
    """Browse requires schema 94."""
    await music.browse("provider://", sort_field=SortField.NAME, limit=10, offset=0)
    assert send_command.await_args.kwargs["require_schema"] == 94
    await music.browse("provider://", sort_field=SortField.RANDOM, random_seed=0)
    assert send_command.await_args.kwargs["require_schema"] == 98


async def test_playlist_dynamic_refresh_is_opt_in(send_command: AsyncMock, music: Music) -> None:
    """Playlist dynamic refresh is opt in."""
    await music.get_playlist_tracks("playlist-id", "provider-id", limit=25, offset=25)
    assert not send_command.await_args.kwargs["force_refresh"]
    assert not send_command.await_args.kwargs["allow_dynamic_tracks"]
    await music.get_playlist_tracks("playlist-id", "provider-id", allow_dynamic_tracks=True)
    assert send_command.await_args.kwargs["allow_dynamic_tracks"]


async def test_playlist_tracks_sends_paging_and_random_seed(
    send_command: AsyncMock, music: Music
) -> None:
    """Playlist tracks sends paging and random seed."""
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


async def test_podcast_episodes_sends_filters_and_paging(
    send_command: AsyncMock, music: Music
) -> None:
    """Podcast episodes sends filters and paging."""
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


async def test_browse_and_similar_tracks_use_server_parameter_names(
    send_command: AsyncMock, music: Music
) -> None:
    """Browse and similar tracks use server parameter names."""
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
        require_schema=92,
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


async def test_similar_track_options_have_independent_schema_requirements(
    send_command: AsyncMock, music: Music
) -> None:
    """Similar track options have independent schema requirements."""
    await music.similar_tracks("track-id", "provider-id", search="live")
    assert send_command.await_args.kwargs["require_schema"] == 92
    await music.similar_tracks("track-id", "provider-id", offset=0)
    assert send_command.await_args.kwargs["require_schema"] == 92
    await music.similar_tracks("track-id", "provider-id", sort_direction=SortDirection.DESC)
    assert send_command.await_args.kwargs["require_schema"] == 92
    await music.similar_tracks("track-id", "provider-id", search="live", random_seed=0)
    assert send_command.await_args.kwargs["require_schema"] == 98


async def test_play_media_rejects_legacy_sort_with_direction_only(
    send_command: AsyncMock, queues: PlayerQueues
) -> None:
    """Play media rejects legacy sort with direction only."""
    for direction in (SortDirection.ASC, SortDirection.DESC):
        with pytest.raises(ValueError, match="sort_field"):
            await queues.play_media(
                "queue-id", "album://album-id", sort_by="name", sort_direction=direction
            )
    send_command.assert_not_awaited()


async def test_play_media_preserves_legacy_sort_without_new_requirement(
    send_command: AsyncMock, queues: PlayerQueues
) -> None:
    """Play media preserves legacy sort without new requirement."""
    await queues.play_media("queue-id", "album://album-id", sort_by="name")
    assert send_command.await_args.kwargs["sort_by"] == "name"
    assert send_command.await_args.kwargs["require_schema"] is None


async def test_play_media_allows_direction_only_without_legacy_sort(
    send_command: AsyncMock, queues: PlayerQueues
) -> None:
    """Play media allows direction only without legacy sort."""
    await queues.play_media("queue-id", "album://album-id", sort_direction=SortDirection.DESC)
    assert send_command.await_args.kwargs["sort_by"] is None
    assert send_command.await_args.kwargs["sort_field"] is None
    assert send_command.await_args.kwargs["sort_direction"] == SortDirection.DESC
    assert send_command.await_args.kwargs["require_schema"] == 95


async def test_play_media_sends_typed_sort_and_schema_requirement(
    send_command: AsyncMock, queues: PlayerQueues
) -> None:
    """Play media sends typed sort and schema requirement."""
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
