"""Handle Music/library related endpoints for Music Assistant."""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING, cast

from music_assistant_models.api import SortOptionInfo
from music_assistant_models.enums import (
    AlbumType,
    ImageType,
    ListingType,
    MediaType,
    SortDirection,
    SortField,
)
from music_assistant_models.helpers import create_sort_name
from music_assistant_models.media_items import (
    Album,
    Artist,
    Audiobook,
    Genre,
    ItemMapping,
    MediaItemImage,
    MediaItemMetadata,
    MediaItemType,
    Playlist,
    Podcast,
    PodcastEpisode,
    Radio,
    RecommendationFolder,
    SearchResults,
    Track,
    media_from_dict,
)

from .constants import (
    ALBUM_TRACKS_LISTING_SCHEMA_VERSION,
    ARTIST_LISTING_SCHEMA_VERSION,
    ARTIST_PROVIDER_FILTER_SCHEMA_VERSION,
    LISTING_FILTER_SCHEMA_VERSION,
    PLAYLIST_PODCAST_LISTING_SCHEMA_VERSION,
    RANDOM_SEED_SCHEMA_VERSION,
    TYPED_LISTING_SCHEMA_VERSION,
    VERSIONS_BROWSE_LISTING_SCHEMA_VERSION,
)
from .helpers import LinkedUser, impersonation_arg

if TYPE_CHECKING:
    from music_assistant_models.queue_item import QueueItem

    from .client import MusicAssistantClient


def _listing_require_schema(
    sort_field: SortField | None,
    sort_direction: SortDirection | None,
    random_seed: int | None,
    *,
    schema_version: int = TYPED_LISTING_SCHEMA_VERSION,
    has_paging: bool = False,
    has_filters: bool = False,
    has_provider_filter: bool = False,
    user: bool = False,
) -> int | None:
    """Return the minimum API schema needed by the requested listing options."""
    if random_seed is not None:
        return RANDOM_SEED_SCHEMA_VERSION
    if has_filters:
        return LISTING_FILTER_SCHEMA_VERSION
    if sort_field is not None or sort_direction is not None or has_paging:
        return schema_version
    if user:
        return 35
    if has_provider_filter:
        return ARTIST_PROVIDER_FILTER_SCHEMA_VERSION
    return None


class Music:
    """Music(library) related endpoints/data for Music Assistant."""

    def __init__(self, client: MusicAssistantClient) -> None:
        """Handle Initialization."""
        self.client = client

    async def get_sort_options(self, listing: ListingType) -> list[SortOptionInfo]:
        """Get the sort options offered by a listing, with the default first."""
        # The complete nonlibrary registry shipped before its individual listing endpoints.
        library_listings = (
            ListingType.LIBRARY_ARTISTS,
            ListingType.LIBRARY_ALBUMS,
            ListingType.LIBRARY_TRACKS,
            ListingType.LIBRARY_PLAYLISTS,
            ListingType.LIBRARY_RADIOS,
            ListingType.LIBRARY_AUDIOBOOKS,
            ListingType.LIBRARY_PODCASTS,
            ListingType.LIBRARY_GENRES,
        )
        return [
            SortOptionInfo.from_dict(item)
            for item in await self.client.send_command(
                "music/sort_options",
                listing=listing,
                require_schema=(
                    TYPED_LISTING_SCHEMA_VERSION
                    if listing in library_listings
                    else ALBUM_TRACKS_LISTING_SCHEMA_VERSION
                ),
            )
        ]

    #  Tracks related endpoints/commands

    async def get_library_tracks(
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        provider: str | list[str] | None = None,
        user: str | None = None,
        *,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        random_seed: int | None = None,
    ) -> list[Track]:
        """Get Track listing from the server.

        :param favorite: Filter by favorite status.
        :param search: Filter by search query.
        :param limit: Maximum number of items to return.
        :param offset: Number of items to skip.
        :param order_by: Deprecated sort key; use sort_field and sort_direction instead.
        :param sort_field: Typed sort field.
        :param sort_direction: Direction for the selected sort field.
        :param random_seed: Keep random ordering stable across pages.
        :param provider: Filter by provider instance ID or domain (single string or list).
        :param user: Optionally execute the request on behalf of this user (user_id or
            username). Requires the authenticated client to have sufficient permissions.
        """
        return [
            Track.from_dict(obj)
            for obj in await self.client.send_command(
                "music/tracks/library_items",
                favorite=favorite,
                search=search,
                limit=limit,
                offset=offset,
                order_by=order_by,
                sort_field=sort_field,
                sort_direction=sort_direction,
                random_seed=random_seed,
                provider=provider,
                user=user,
                require_schema=_listing_require_schema(
                    sort_field, sort_direction, random_seed, user=user is not None
                ),
            )
        ]

    async def get_track(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        album_uri: str | None = None,
    ) -> Track:
        """Get single Track from the server."""
        return Track.from_dict(
            await self.client.send_command(
                "music/tracks/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                album_uri=album_uri,
            ),
        )

    async def get_track_versions(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        search: str | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        limit: int | None = None,
        offset: int | None = None,
        random_seed: int | None = None,
    ) -> list[Track]:
        """Get a page of other track versions from the server."""
        return [
            Track.from_dict(item)
            for item in await self.client.send_command(
                "music/tracks/track_versions",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                search=search,
                sort_field=sort_field,
                sort_direction=sort_direction,
                limit=limit,
                offset=offset,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    sort_field,
                    sort_direction,
                    random_seed,
                    schema_version=VERSIONS_BROWSE_LISTING_SCHEMA_VERSION,
                    has_paging=any(value is not None for value in (search, limit, offset)),
                ),
            )
        ]

    async def get_track_albums(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        in_library_only: bool = False,
        *,
        search: str | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        limit: int | None = None,
        offset: int | None = None,
        random_seed: int | None = None,
    ) -> list[Album]:
        """Get a page of (known) albums this track is featured on."""
        return [
            Album.from_dict(item)
            for item in await self.client.send_command(
                "music/tracks/track_albums",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                in_library_only=in_library_only,
                search=search,
                sort_field=sort_field,
                sort_direction=sort_direction,
                limit=limit,
                offset=offset,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    sort_field,
                    sort_direction,
                    random_seed,
                    schema_version=ARTIST_LISTING_SCHEMA_VERSION,
                    has_paging=any(value is not None for value in (search, limit, offset)),
                ),
            )
        ]

    def get_track_preview_url(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> str:
        """Get URL to preview clip of given track."""
        assert self.client.server_info
        encoded_url = urllib.parse.quote(urllib.parse.quote(item_id))
        return f"{self.client.server_info.base_url}/preview?path={encoded_url}&provider={provider_instance_id_or_domain}"  # noqa: E501

    #  Albums related endpoints/commands

    async def get_library_albums(  # noqa: PLR0913
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        album_types: list[AlbumType] | None = None,
        provider: str | list[str] | None = None,
        user: str | None = None,
        *,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        random_seed: int | None = None,
    ) -> list[Album]:
        """Get Albums listing from the server.

        :param favorite: Filter by favorite status.
        :param search: Filter by search query.
        :param limit: Maximum number of items to return.
        :param offset: Number of items to skip.
        :param order_by: Deprecated sort key; use sort_field and sort_direction instead.
        :param album_types: Filter by album types.
        :param provider: Filter by provider instance ID or domain (single string or list).
        :param user: Optionally execute the request on behalf of this user (user_id or
            username). Requires the authenticated client to have sufficient permissions.
        """
        return [
            Album.from_dict(obj)
            for obj in await self.client.send_command(
                "music/albums/library_items",
                favorite=favorite,
                search=search,
                limit=limit,
                offset=offset,
                order_by=order_by,
                sort_field=sort_field,
                sort_direction=sort_direction,
                random_seed=random_seed,
                album_types=album_types,
                provider=provider,
                user=user,
                require_schema=_listing_require_schema(
                    sort_field, sort_direction, random_seed, user=user is not None
                ),
            )
        ]

    async def get_album(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> Album:
        """Get single Album from the server."""
        return Album.from_dict(
            await self.client.send_command(
                "music/albums/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
            ),
        )

    async def get_album_tracks(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        in_library_only: bool = False,
        *,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        favorite: bool | None = None,
        random_seed: int | None = None,
    ) -> list[Track]:
        """Get a searched, sorted and paged listing of tracks for an album."""
        return [
            Track.from_dict(item)
            for item in await self.client.send_command(
                "music/albums/album_tracks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                in_library_only=in_library_only,
                search=search,
                limit=limit,
                offset=offset,
                sort_field=sort_field,
                sort_direction=sort_direction,
                favorite=favorite,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    sort_field,
                    sort_direction,
                    random_seed,
                    schema_version=ALBUM_TRACKS_LISTING_SCHEMA_VERSION,
                    has_paging=any(value is not None for value in (search, limit, offset)),
                    has_filters=favorite is not None,
                ),
            )
        ]

    async def get_album_versions(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        search: str | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        limit: int | None = None,
        offset: int | None = None,
        random_seed: int | None = None,
    ) -> list[Album]:
        """Get a page of other album versions from the server."""
        return [
            Album.from_dict(item)
            for item in await self.client.send_command(
                "music/albums/album_versions",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                search=search,
                sort_field=sort_field,
                sort_direction=sort_direction,
                limit=limit,
                offset=offset,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    sort_field,
                    sort_direction,
                    random_seed,
                    schema_version=VERSIONS_BROWSE_LISTING_SCHEMA_VERSION,
                    has_paging=any(value is not None for value in (search, limit, offset)),
                ),
            )
        ]

    #  Artist related endpoints/commands

    async def get_library_artists(  # noqa: PLR0913
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        album_artists_only: bool = False,
        provider: str | list[str] | None = None,
        user: str | None = None,
        *,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        random_seed: int | None = None,
    ) -> list[Artist]:
        """Get Artists listing from the server.

        :param favorite: Filter by favorite status.
        :param search: Filter by search query.
        :param limit: Maximum number of items to return.
        :param offset: Number of items to skip.
        :param order_by: Deprecated sort key; use sort_field and sort_direction instead.
        :param album_artists_only: Only return artists that have albums.
        :param provider: Filter by provider instance ID or domain (single string or list).
        :param user: Optionally execute the request on behalf of this user (user_id or
            username). Requires the authenticated client to have sufficient permissions.
        """
        return [
            Artist.from_dict(obj)
            for obj in await self.client.send_command(
                "music/artists/library_items",
                favorite=favorite,
                search=search,
                limit=limit,
                offset=offset,
                order_by=order_by,
                sort_field=sort_field,
                sort_direction=sort_direction,
                random_seed=random_seed,
                album_artists_only=album_artists_only,
                provider=provider,
                user=user,
                require_schema=_listing_require_schema(
                    sort_field, sort_direction, random_seed, user=user is not None
                ),
            )
        ]

    async def get_artist(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> Artist:
        """Get single Artist from the server."""
        return Artist.from_dict(
            await self.client.send_command(
                "music/artists/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
            ),
        )

    async def get_artist_tracks(  # noqa: PLR0913
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        in_library_only: bool = False,
        *,
        provider_filter: str | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        favorite: bool | None = None,
        random_seed: int | None = None,
    ) -> list[Track]:
        """Get a searched, sorted and paged artist track listing."""
        return [
            Track.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/artist_tracks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                in_library_only=in_library_only,
                provider_filter=provider_filter,
                search=search,
                limit=limit,
                offset=offset,
                sort_field=sort_field,
                sort_direction=sort_direction,
                favorite=favorite,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    sort_field,
                    sort_direction,
                    random_seed,
                    schema_version=ARTIST_LISTING_SCHEMA_VERSION,
                    has_paging=any(value is not None for value in (search, limit, offset)),
                    has_filters=favorite is not None,
                    has_provider_filter=provider_filter is not None,
                ),
            )
        ]

    async def get_artist_albums(  # noqa: PLR0913
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        in_library_only: bool = False,
        *,
        provider_filter: str | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        album_types: list[AlbumType] | None = None,
        favorite: bool | None = None,
        random_seed: int | None = None,
    ) -> list[Album]:
        """Get a searched, sorted and paged artist album listing."""
        return [
            Album.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/artist_albums",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                in_library_only=in_library_only,
                provider_filter=provider_filter,
                search=search,
                limit=limit,
                offset=offset,
                sort_field=sort_field,
                sort_direction=sort_direction,
                album_types=album_types,
                favorite=favorite,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    sort_field,
                    sort_direction,
                    random_seed,
                    schema_version=ARTIST_LISTING_SCHEMA_VERSION,
                    has_paging=any(value is not None for value in (search, limit, offset)),
                    has_filters=album_types is not None or favorite is not None,
                    has_provider_filter=provider_filter is not None,
                ),
            )
        ]

    #  Playlist related endpoints/commands

    async def get_library_playlists(
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        provider: str | list[str] | None = None,
        user: str | None = None,
        *,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        random_seed: int | None = None,
    ) -> list[Playlist]:
        """Get Playlists listing from the server.

        :param favorite: Filter by favorite status.
        :param search: Filter by search query.
        :param limit: Maximum number of items to return.
        :param offset: Number of items to skip.
        :param order_by: Deprecated sort key; use sort_field and sort_direction instead.
        :param provider: Filter by provider instance ID or domain (single string or list).
        :param user: Optionally execute the request on behalf of this user (user_id or
            username). Requires the authenticated client to have sufficient permissions.
        """
        return [
            Playlist.from_dict(obj)
            for obj in await self.client.send_command(
                "music/playlists/library_items",
                favorite=favorite,
                search=search,
                limit=limit,
                offset=offset,
                order_by=order_by,
                sort_field=sort_field,
                sort_direction=sort_direction,
                random_seed=random_seed,
                provider=provider,
                user=user,
                require_schema=_listing_require_schema(
                    sort_field, sort_direction, random_seed, user=user is not None
                ),
            )
        ]

    async def get_playlist(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> Playlist:
        """Get single Playlist from the server."""
        return Playlist.from_dict(
            await self.client.send_command(
                "music/playlists/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
            ),
        )

    async def get_playlist_tracks(  # noqa: PLR0913
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        force_refresh: bool = False,
        *,
        allow_dynamic_tracks: bool = False,
        strict_provider_instance: bool = False,
        favorite: bool | None = None,
        search: str | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        limit: int | None = None,
        offset: int | None = None,
        random_seed: int | None = None,
    ) -> list[Track]:
        """
        Get a page of tracks for the given playlist.

        :param force_refresh: Force a refresh of the (cached) playlist tracks.
        """
        return [
            Track.from_dict(obj)
            for obj in await self.client.send_command(
                "music/playlists/playlist_tracks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                force_refresh=force_refresh,
                allow_dynamic_tracks=allow_dynamic_tracks,
                strict_provider_instance=strict_provider_instance,
                favorite=favorite,
                search=search,
                sort_field=sort_field,
                sort_direction=sort_direction,
                limit=limit,
                offset=offset,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    sort_field,
                    sort_direction,
                    random_seed,
                    schema_version=PLAYLIST_PODCAST_LISTING_SCHEMA_VERSION,
                    has_paging=any(
                        value is not None for value in (favorite, search, limit, offset)
                    ),
                ),
            )
        ]

    async def add_playlist_tracks(self, db_playlist_id: str | int, uris: list[str]) -> None:
        """Add multiple tracks to playlist. Creates background tasks to process the action."""
        await self.client.send_command(
            "music/playlists/add_playlist_tracks",
            db_playlist_id=db_playlist_id,
            uris=uris,
        )

    async def remove_playlist_tracks(
        self, db_playlist_id: str | int, positions_to_remove: tuple[int, ...]
    ) -> None:
        """Remove multiple tracks from playlist."""
        await self.client.send_command(
            "music/playlists/remove_playlist_tracks",
            db_playlist_id=db_playlist_id,
            positions_to_remove=positions_to_remove,
        )

    async def create_playlist(
        self, name: str, provider_instance_or_domain: str | None = None
    ) -> Playlist:
        """Create new playlist."""
        return Playlist.from_dict(
            await self.client.send_command(
                "music/playlists/create_playlist",
                name=name,
                provider_instance_or_domain=provider_instance_or_domain,
            )
        )

    # Audiobooks related endpoints/commands

    async def get_library_audiobooks(
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        provider: str | list[str] | None = None,
        user: str | None = None,
        *,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        random_seed: int | None = None,
    ) -> list[Audiobook]:
        """Get Audiobooks listing from the server.

        :param favorite: Filter by favorite status.
        :param search: Filter by search query.
        :param limit: Maximum number of items to return.
        :param offset: Number of items to skip.
        :param order_by: Deprecated sort key; use sort_field and sort_direction instead.
        :param provider: Filter by provider instance ID or domain (single string or list).
        :param user: Optionally execute the request on behalf of this user (user_id or
            username). Requires the authenticated client to have sufficient permissions.
        """
        return [
            Audiobook.from_dict(obj)
            for obj in await self.client.send_command(
                "music/audiobooks/library_items",
                favorite=favorite,
                search=search,
                limit=limit,
                offset=offset,
                order_by=order_by,
                sort_field=sort_field,
                sort_direction=sort_direction,
                random_seed=random_seed,
                provider=provider,
                user=user,
                require_schema=_listing_require_schema(
                    sort_field, sort_direction, random_seed, user=user is not None
                ),
            )
        ]

    async def get_audiobook(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> Audiobook:
        """Get single Audiobook from the server."""
        return Audiobook.from_dict(
            await self.client.send_command(
                "music/audiobooks/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
            ),
        )

    # Podcasts related endpoints/commands

    async def get_library_podcasts(
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        provider: str | list[str] | None = None,
        user: str | None = None,
        *,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        random_seed: int | None = None,
    ) -> list[Podcast]:
        """Get Podcasts listing from the server.

        :param favorite: Filter by favorite status.
        :param search: Filter by search query.
        :param limit: Maximum number of items to return.
        :param offset: Number of items to skip.
        :param order_by: Deprecated sort key; use sort_field and sort_direction instead.
        :param provider: Filter by provider instance ID or domain (single string or list).
        :param user: Optionally execute the request on behalf of this user (user_id or
            username). Requires the authenticated client to have sufficient permissions.
        """
        return [
            Podcast.from_dict(obj)
            for obj in await self.client.send_command(
                "music/podcasts/library_items",
                favorite=favorite,
                search=search,
                limit=limit,
                offset=offset,
                order_by=order_by,
                sort_field=sort_field,
                sort_direction=sort_direction,
                random_seed=random_seed,
                provider=provider,
                user=user,
                require_schema=_listing_require_schema(
                    sort_field, sort_direction, random_seed, user=user is not None
                ),
            )
        ]

    async def get_podcast(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> Podcast:
        """Get single Podcast from the server."""
        return Podcast.from_dict(
            await self.client.send_command(
                "music/podcasts/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
            ),
        )

    async def get_podcast_episodes(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        fully_played: bool | None = None,
        search: str | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        limit: int | None = None,
        offset: int | None = None,
        exclude_item_id: str | None = None,
        random_seed: int | None = None,
    ) -> list[PodcastEpisode]:
        """Get a page of episodes for the given podcast."""
        return [
            PodcastEpisode.from_dict(obj)
            for obj in await self.client.send_command(
                "music/podcasts/podcast_episodes",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                fully_played=fully_played,
                search=search,
                sort_field=sort_field,
                sort_direction=sort_direction,
                limit=limit,
                offset=offset,
                exclude_item_id=exclude_item_id,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    sort_field,
                    sort_direction,
                    random_seed,
                    schema_version=PLAYLIST_PODCAST_LISTING_SCHEMA_VERSION,
                    has_paging=any(
                        value is not None for value in (fully_played, search, limit, offset)
                    ),
                    has_filters=exclude_item_id is not None,
                ),
            )
        ]

    #  Radio related endpoints/commands

    async def get_library_radios(
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        provider: str | list[str] | None = None,
        user: str | None = None,
        *,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        random_seed: int | None = None,
    ) -> list[Radio]:
        """Get Radio listing from the server.

        :param favorite: Filter by favorite status.
        :param search: Filter by search query.
        :param limit: Maximum number of items to return.
        :param offset: Number of items to skip.
        :param order_by: Deprecated sort key; use sort_field and sort_direction instead.
        :param provider: Filter by provider instance ID or domain (single string or list).
        :param user: Optionally execute the request on behalf of this user (user_id or
            username). Requires the authenticated client to have sufficient permissions.
        """
        return [
            Radio.from_dict(obj)
            for obj in await self.client.send_command(
                "music/radios/library_items",
                favorite=favorite,
                search=search,
                limit=limit,
                offset=offset,
                order_by=order_by,
                sort_field=sort_field,
                sort_direction=sort_direction,
                random_seed=random_seed,
                provider=provider,
                user=user,
                require_schema=_listing_require_schema(
                    sort_field, sort_direction, random_seed, user=user is not None
                ),
            )
        ]

    async def get_library_genres(  # noqa: PLR0913, PLR0917
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        provider: str | list[str] | None = None,
        played_only: bool = False,
        hide_empty: bool | None = None,
        media_type: MediaType | None = None,
        content_type: str | None = None,
        summary: bool = True,
        *,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        random_seed: int | None = None,
    ) -> list[Genre]:
        """Get a searched, sorted and paged genre listing."""
        return [
            Genre.from_dict(obj)
            for obj in await self.client.send_command(
                "music/genres/library_items",
                favorite=favorite,
                search=search,
                limit=limit,
                offset=offset,
                order_by=order_by,
                provider=provider,
                played_only=played_only,
                hide_empty=hide_empty,
                media_type=media_type,
                content_type=content_type,
                summary=summary,
                sort_field=sort_field,
                sort_direction=sort_direction,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    sort_field,
                    sort_direction,
                    random_seed,
                ),
            )
        ]

    async def get_genre_tracks(
        self,
        item_id: str | int,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        *,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        search: str | None = None,
        random_seed: int | None = None,
    ) -> list[Track]:
        """Get a searched, sorted and paged listing of tracks mapped to a genre."""
        return [
            Track.from_dict(obj)
            for obj in await self.client.send_command(
                "music/genres/tracks",
                item_id=item_id,
                limit=limit,
                offset=offset,
                order_by=order_by,
                sort_field=sort_field,
                sort_direction=sort_direction,
                search=search,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    sort_field,
                    sort_direction,
                    random_seed,
                    schema_version=(
                        VERSIONS_BROWSE_LISTING_SCHEMA_VERSION
                        if search is not None
                        else TYPED_LISTING_SCHEMA_VERSION
                    ),
                    has_paging=search is not None,
                ),
            )
        ]

    async def get_genre_albums(
        self,
        item_id: str | int,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        *,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        search: str | None = None,
        random_seed: int | None = None,
    ) -> list[Album]:
        """Get a searched, sorted and paged listing of albums mapped to a genre."""
        return [
            Album.from_dict(obj)
            for obj in await self.client.send_command(
                "music/genres/albums",
                item_id=item_id,
                limit=limit,
                offset=offset,
                order_by=order_by,
                sort_field=sort_field,
                sort_direction=sort_direction,
                search=search,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    sort_field,
                    sort_direction,
                    random_seed,
                    schema_version=(
                        VERSIONS_BROWSE_LISTING_SCHEMA_VERSION
                        if search is not None
                        else TYPED_LISTING_SCHEMA_VERSION
                    ),
                    has_paging=search is not None,
                ),
            )
        ]

    async def get_radio(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> Radio:
        """Get single Radio from the server."""
        return Radio.from_dict(
            await self.client.send_command(
                "music/radios/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
            ),
        )

    async def get_radio_versions(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        search: str | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        limit: int | None = None,
        offset: int | None = None,
        random_seed: int | None = None,
    ) -> list[Radio]:
        """Get a page of other radio versions from the server."""
        return [
            Radio.from_dict(item)
            for item in await self.client.send_command(
                "music/radios/radio_versions",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                search=search,
                sort_field=sort_field,
                sort_direction=sort_direction,
                limit=limit,
                offset=offset,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    sort_field,
                    sort_direction,
                    random_seed,
                    schema_version=VERSIONS_BROWSE_LISTING_SCHEMA_VERSION,
                    has_paging=any(value is not None for value in (search, limit, offset)),
                ),
            )
        ]

    # Other/generic endpoints/commands

    async def start_sync(
        self,
        media_types: list[MediaType] | None = None,
        providers: list[str] | None = None,
    ) -> None:
        """Start running the sync of (all or selected) musicproviders.

        media_types: only sync these media types. None for all.
        providers: only sync these provider instances. None for all.
        """
        await self.client.send_command("music/sync", media_types=media_types, providers=providers)

    async def search(
        self,
        search_query: str,
        media_types: list[MediaType] = MediaType.ALL,
        limit: int = 50,
        library_only: bool = False,
        user: str | LinkedUser | None = None,
    ) -> SearchResults:
        """Perform global search for media items on all providers.

        :param search_query: Search query.
        :param media_types: A list of media_types to include.
        :param limit: number of items to return in the search (per type).
        :param user: Optionally execute the search on behalf of this user: a user_id or
            username string, or a LinkedUser reference by auth provider.
            Requires the authenticated client to have sufficient permissions.
        """
        return SearchResults.from_dict(
            await self.client.send_command(
                "music/search",
                search_query=search_query,
                media_types=media_types,
                limit=limit,
                library_only=library_only,
                **impersonation_arg(self.client.server_info, user),
            ),
        )

    async def browse(
        self,
        path: str | None = None,
        *,
        player_id: str | None = None,
        search: str | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        limit: int | None = None,
        offset: int | None = None,
        random_seed: int | None = None,
    ) -> list[MediaItemType | ItemMapping]:
        """Browse music providers with optional search, sorting and paging."""
        return [
            media_from_dict(obj)
            for obj in await self.client.send_command(
                "music/browse",
                path=path,
                player_id=player_id,
                search=search,
                sort_field=sort_field,
                sort_direction=sort_direction,
                limit=limit,
                offset=offset,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    sort_field,
                    sort_direction,
                    random_seed,
                    schema_version=VERSIONS_BROWSE_LISTING_SCHEMA_VERSION,
                    has_paging=any(value is not None for value in (search, limit, offset)),
                ),
            )
        ]

    async def recently_played(
        self,
        limit: int = 10,
        media_types: list[MediaType] | None = None,
        userid: str | None = None,
        queue_id: str | None = None,
        fully_played_only: bool = True,
        user_initiated_only: bool = False,
        played_after_timestamp: int | None = None,
    ) -> list[ItemMapping]:
        """
        Return a list of the last played items.

        :param limit: Maximum number of items to return.
        :param media_types: Filter by media types.
        :param userid: Optionally return the history of this user (instead of the user the
            client is authenticated as). Requires the authenticated client to have sufficient
            permissions.
        :param queue_id: Filter by specific queue ID.
        :param fully_played_only: If True, only return fully played items.
        :param user_initiated_only: If True, only return items initiated by the user.
        :param played_after_timestamp: If set, only return items played at or after this
            epoch-seconds timestamp.
        """
        return [
            ItemMapping.from_dict(item)
            for item in await self.client.send_command(
                "music/recently_played_items",
                limit=limit,
                media_types=media_types,
                userid=userid,
                queue_id=queue_id,
                fully_played_only=fully_played_only,
                user_initiated_only=user_initiated_only,
                played_after_timestamp=played_after_timestamp,
            )
        ]

    async def in_progress_items(
        self, limit: int = 10, all_users: bool = False
    ) -> list[ItemMapping]:
        """Return a list of the Audiobooks and PodcastEpisodes that are in progress."""
        return [
            ItemMapping.from_dict(item)
            for item in await self.client.send_command(
                "music/in_progress_items",
                limit=limit,
                all_users=all_users,
            )
        ]

    async def recommendations(self) -> list[RecommendationFolder]:
        """Get all recommendations."""
        return [
            RecommendationFolder.from_dict(item)
            for item in await self.client.send_command("music/recommendations")
        ]

    async def get_item_by_uri(
        self,
        uri: str,
    ) -> MediaItemType | ItemMapping:
        """Get single music item providing a mediaitem uri."""
        return media_from_dict(await self.client.send_command("music/item_by_uri", uri=uri))

    async def verify_item_uri(
        self,
        uri: str,
        user: str | LinkedUser | None = None,
        username: str | None = None,
    ) -> bool:
        """
        Verify whether a uri points to a valid, accessible item.

        :param user: Optionally verify access on behalf of this user: a user_id or username
            string, or a LinkedUser reference by auth provider.
            Requires the authenticated client to have sufficient permissions.
        :param username: Deprecated alias for user.
        """
        return cast(
            "bool",
            await self.client.send_command(
                "music/verify_item_uri",
                uri=uri,
                require_schema=33,
                **impersonation_arg(self.client.server_info, user or username),
            ),
        )

    async def get_item(
        self,
        media_type: MediaType,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> MediaItemType | ItemMapping:
        """Get single music item by id and media type."""
        return media_from_dict(
            await self.client.send_command(
                "music/item",
                media_type=media_type,
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
            )
        )

    async def get_library_item_by_prov_id(
        self,
        media_type: MediaType,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> MediaItemType | None:
        """Get single library music item by id and media type."""
        if result := await self.client.send_command(
            "music/get_library_item",
            media_type=media_type,
            item_id=item_id,
            provider_instance_id_or_domain=provider_instance_id_or_domain,
        ):
            return cast("MediaItemType", media_from_dict(result))
        return None

    async def add_item_to_favorites(
        self,
        item: str | MediaItemType,
    ) -> None:
        """Add an item to the favorites."""
        await self.client.send_command("music/favorites/add_item", item=item)

    async def remove_item_from_favorites(
        self,
        media_type: MediaType,
        library_item_id: str | int,
    ) -> None:
        """Remove (library) item from the favorites."""
        await self.client.send_command(
            "music/favorites/remove_item",
            media_type=media_type,
            library_item_id=library_item_id,
        )

    async def remove_item_from_library(
        self, media_type: MediaType, library_item_id: str | int, recursive: bool = True
    ) -> None:
        """
        Remove item from the library.

        Destructive! Will remove the item and all dependants.
        """
        await self.client.send_command(
            "music/library/remove_item",
            media_type=media_type,
            library_item_id=library_item_id,
            recursive=recursive,
        )

    async def add_item_to_library(
        self, item: str | MediaItemType, overwrite_existing: bool = False
    ) -> MediaItemType:
        """Add item (uri or mediaitem) to the library."""
        return cast(
            "MediaItemType",
            await self.client.send_command(
                "music/library/add_item", item=item, overwrite_existing=overwrite_existing
            ),
        )

    async def refresh_item(
        self,
        media_item: MediaItemType,
    ) -> MediaItemType | ItemMapping | None:
        """Try to refresh a mediaitem by requesting it's full object or search for substitutes."""
        if result := await self.client.send_command("music/refresh_item", media_item=media_item):
            return media_from_dict(result)
        return None

    async def mark_item_played(
        self,
        media_item: MediaItemType,
        fully_played: bool = True,
        userid: str | None = None,
    ) -> None:
        """
        Mark item as played in playlog.

        :param media_item: The media item to mark as played.
        :param fully_played: If True, mark the item as fully played.
        :param userid: Optionally attribute this play to a specific user (instead of the user
            the client is authenticated as). Requires the authenticated client to have
            sufficient permissions.
        """
        await self.client.send_command(
            "music/mark_played",
            media_item=media_item,
            fully_played=fully_played,
            userid=userid,
        )

    async def mark_item_unplayed(
        self,
        media_item: MediaItemType,
        userid: str | None = None,
    ) -> None:
        """
        Mark item as unplayed in playlog.

        :param media_item: The media item to mark as unplayed.
        :param userid: Optionally apply this to a specific user (instead of the user the
            client is authenticated as). Requires the authenticated client to have sufficient
            permissions.
        """
        await self.client.send_command(
            "music/mark_unplayed",
            media_item=media_item,
            userid=userid,
        )

    async def get_track_by_name(
        self,
        track_name: str,
        artist_name: str | None = None,
        album_name: str | None = None,
        track_version: str | None = None,
    ) -> Track | None:
        """Get a track by its name, optionally with artist and album."""
        assert self.client.server_info  # for type checking
        if self.client.server_info.schema_version >= 27:
            # from schema version 27+, the server can handle this natively
            await self.client.send_command(
                "music/track_by_name",
                track_name=track_name,
                artist_name=artist_name,
                album_name=album_name,
                track_version=track_version,
            )
            return None

        # Fallback implementation for older server versions.
        # TODO: remove this after a while, once all/most servers are updated

        def compare_strings(str1: str, str2: str) -> bool:
            str1_compare = create_sort_name(str1)
            str2_compare = create_sort_name(str2)
            return str1_compare == str2_compare

        search_query = f"{artist_name} - {track_name}" if artist_name else track_name
        search_result = await self.client.music.search(
            search_query=search_query,
            media_types=[MediaType.TRACK],
        )
        for allow_item_mapping in (False, True):
            for search_track in search_result.tracks:
                if not allow_item_mapping and not isinstance(search_track, Track):
                    continue
                if not compare_strings(track_name, search_track.name):
                    continue
                # check optional artist(s)
                if artist_name and isinstance(search_track, Track):
                    for artist in search_track.artists:
                        if compare_strings(artist_name, artist.name):
                            break
                    else:
                        # no artist match found: abort
                        continue
                # check optional album
                if (
                    album_name
                    and isinstance(search_track, Track)
                    and search_track.album
                    and not compare_strings(album_name, search_track.album.name)
                ):
                    # no album match found: abort
                    continue
                # if we reach this, we found a match
                if not isinstance(search_track, Track):
                    # ensure we return an actual Track object
                    return await self.client.music.get_track(
                        item_id=search_track.item_id,
                        provider_instance_id_or_domain=search_track.provider,
                    )
                return search_track

        # try to handle case where something is appended to the title
        for splitter in ("•", "-", "|", "(", "["):
            if splitter in track_name:
                return await self.get_track_by_name(
                    track_name=track_name.split(splitter, maxsplit=1)[0].strip(),
                    artist_name=artist_name,
                    album_name=None,
                    track_version=track_version,
                )
        # try to handle case where multiple artists are listed as single string
        if artist_name:
            for splitter in ("•", ",", "&", "/", "|", "/"):
                if splitter in artist_name:
                    return await self.get_track_by_name(
                        track_name=track_name,
                        artist_name=artist_name.split(splitter)[0].strip(),
                        album_name=None,
                        track_version=track_version,
                    )
        # allow non-exact album match as fallback
        if album_name:
            return await self.get_track_by_name(
                track_name=track_name,
                artist_name=artist_name,
                album_name=None,
                track_version=track_version,
            )
        # no match found
        return None

    # helpers

    def get_media_item_image(
        self,
        item: MediaItemType | ItemMapping | QueueItem,
        type: ImageType = ImageType.THUMB,  # noqa: A002
    ) -> MediaItemImage | None:
        """Get MediaItemImage for MediaItem, ItemMapping."""
        if not item:
            # guard for unexpected bad things
            return None
        # handle image in itemmapping
        if item.image and item.image.type == type:
            return item.image
        # always prefer album image for tracks
        album: Album | ItemMapping | None
        if (album := getattr(item, "album", None)) and (
            album_image := self.get_media_item_image(album, type)
        ):
            return album_image
        # handle regular image within mediaitem
        metadata: MediaItemMetadata | None
        if metadata := getattr(item, "metadata", None):
            for img in metadata.images or []:
                if img.type == type:
                    return cast("MediaItemImage", img)
        # retry with album/track artist(s)
        artists: list[Artist | ItemMapping] | None
        if artists := getattr(item, "artists", None):
            for artist in artists:
                if artist_image := self.get_media_item_image(artist, type):
                    return artist_image
        # allow landscape fallback
        if type == ImageType.THUMB:
            return self.get_media_item_image(item, ImageType.LANDSCAPE)
        return None

    async def get_item_by_name(
        self,
        name: str,
        artist: str | None = None,
        album: str | None = None,
        media_type: MediaType | None = None,
        user: str | LinkedUser | None = None,
        username: str | None = None,
    ) -> MediaItemType | ItemMapping | None:
        """
        Try to find a media item (such as a playlist) by name.

        :param user: Optionally perform the lookup on behalf of this user: a user_id or
            username string, or a LinkedUser reference by auth provider.
            Requires the authenticated client to have sufficient permissions.
            Only honored by the native server lookup (schema >= 33); the legacy fallback
            always runs as the authenticated user.
        :param username: Deprecated alias for user.
        """
        assert self.client.server_info  # for type checking
        if self.client.server_info.schema_version >= 33:
            # from schema version 33+, the server can handle this natively
            if result := await self.client.send_command(
                "music/item_by_name",
                name=name,
                artist=artist,
                album=album,
                media_type=media_type,
                **impersonation_arg(self.client.server_info, user or username),
            ):
                return media_from_dict(result)
            return None

        # Fallback implementation for older server versions.
        # TODO: remove this after a while, once all/most servers are updated
        # pylint: disable=too-many-nested-blocks
        searchname = name.lower()
        library_functions = [
            x
            for x in (
                self.get_library_playlists,
                self.get_library_radios,
                self.get_library_tracks,
                self.get_library_albums,
                self.get_library_artists,
                self.get_library_audiobooks,
                self.get_library_podcasts,
            )
            if not media_type or media_type.value.lower() in x.__name__
        ]
        # prefer (exact) lookup in the library by name
        for func in library_functions:
            result = await func(search=searchname)
            for item in result:
                # handle optional artist filter
                if (
                    artist
                    and (artists := getattr(item, "artists", None))
                    and not any(x for x in artists if x.name.lower() == artist.lower())
                ):
                    continue
                # handle optional album filter
                if (
                    album
                    and (item_album := getattr(item, "album", None))
                    and item_album.name.lower() != album.lower()
                ):
                    continue
                if searchname == item.name.lower():
                    return item
        # nothing found in the library, fallback to global search
        search_name = name
        if album and artist:
            search_name = f"{artist} - {album} - {name}"
        elif album:
            search_name = f"{album} - {name}"
        elif artist:
            search_name = f"{artist} - {name}"
        search_results = await self.search(
            search_query=search_name,
            media_types=[media_type]
            if media_type and media_type != MediaType.UNKNOWN
            else MediaType.ALL,
            limit=8,
        )
        for results in (
            search_results.tracks,
            search_results.albums,
            search_results.playlists,
            search_results.artists,
            search_results.radio,
            search_results.audiobooks,
            search_results.podcasts,
        ):
            for _item in results:
                # simply return the first item because search is already sorted by best match
                return _item
        return None

    async def album_count(
        self,
        favorite_only: bool | None = None,
        album_types: list[AlbumType] | None = None,
    ) -> int:
        """Return the total number of items in the library."""
        return cast(
            "int",
            await self.client.send_command(
                "music/albums/count",
                favorite_only=favorite_only,
                album_types=album_types,
            ),
        )

    async def remove_album(self, item_id: str | int, recursive: bool | None = None) -> None:
        """Delete item from the library(database)."""
        await self.client.send_command(
            "music/albums/remove",
            item_id=item_id,
            recursive=recursive,
        )

    async def update_album(
        self,
        item_id: str | int,
        update: Album,
        overwrite: bool | None = None,
    ) -> Album:
        """Update existing library record in the library database."""
        return Album.from_dict(
            await self.client.send_command(
                "music/albums/update",
                item_id=item_id,
                update=update,
                overwrite=overwrite,
            )
        )

    async def artist_count(
        self,
        favorite_only: bool | None = None,
        album_artists_only: bool | None = None,
    ) -> int:
        """Return the total number of items in the library."""
        return cast(
            "int",
            await self.client.send_command(
                "music/artists/count",
                favorite_only=favorite_only,
                album_artists_only=album_artists_only,
            ),
        )

    async def remove_artist(self, item_id: str | int, recursive: bool | None = None) -> None:
        """Delete record from the database."""
        await self.client.send_command(
            "music/artists/remove",
            item_id=item_id,
            recursive=recursive,
        )

    async def update_artist(
        self,
        item_id: str | int,
        update: Artist,
        overwrite: bool | None = None,
    ) -> Artist:
        """Update existing library record in the library database."""
        return Artist.from_dict(
            await self.client.send_command(
                "music/artists/update",
                item_id=item_id,
                update=update,
                overwrite=overwrite,
            )
        )

    async def audiobook_versions(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        search: str | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        limit: int | None = None,
        offset: int | None = None,
        random_seed: int | None = None,
    ) -> list[Audiobook]:
        """Return a searched, sorted and paged listing of audiobook versions."""
        return [
            Audiobook.from_dict(obj)
            for obj in await self.client.send_command(
                "music/audiobooks/audiobook_versions",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                search=search,
                sort_field=sort_field,
                sort_direction=sort_direction,
                limit=limit,
                offset=offset,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    sort_field,
                    sort_direction,
                    random_seed,
                    schema_version=VERSIONS_BROWSE_LISTING_SCHEMA_VERSION,
                    has_paging=any(value is not None for value in (search, limit, offset)),
                ),
            )
        ]

    async def audiobook_count(self, favorite_only: bool | None = None) -> int:
        """Return the total number of items in the library."""
        return cast(
            "int",
            await self.client.send_command(
                "music/audiobooks/count",
                favorite_only=favorite_only,
            ),
        )

    async def remove_audiobook(self, item_id: str | int, recursive: bool | None = None) -> None:
        """Delete library record from the database."""
        await self.client.send_command(
            "music/audiobooks/remove",
            item_id=item_id,
            recursive=recursive,
        )

    async def update_audiobook(
        self,
        item_id: str | int,
        update: Audiobook,
        overwrite: bool | None = None,
    ) -> Audiobook:
        """Update existing library record in the library database."""
        return Audiobook.from_dict(
            await self.client.send_command(
                "music/audiobooks/update",
                item_id=item_id,
                update=update,
                overwrite=overwrite,
            )
        )

    async def playlist_count(self, favorite_only: bool | None = None) -> int:
        """Return the total number of items in the library."""
        return cast(
            "int",
            await self.client.send_command(
                "music/playlists/count",
                favorite_only=favorite_only,
            ),
        )

    async def remove_playlist(self, item_id: str | int, recursive: bool | None = None) -> None:
        """Delete library record from the database."""
        await self.client.send_command(
            "music/playlists/remove",
            item_id=item_id,
            recursive=recursive,
        )

    async def update_playlist(
        self,
        item_id: str | int,
        update: Playlist,
        overwrite: bool | None = None,
    ) -> Playlist:
        """Update existing library record in the library database."""
        return Playlist.from_dict(
            await self.client.send_command(
                "music/playlists/update",
                item_id=item_id,
                update=update,
                overwrite=overwrite,
            )
        )

    async def podcast_count(self, favorite_only: bool | None = None) -> int:
        """Return the total number of items in the library."""
        return cast(
            "int",
            await self.client.send_command(
                "music/podcasts/count",
                favorite_only=favorite_only,
            ),
        )

    async def podcast_episode(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> list[PodcastEpisode]:
        """Return single podcast episode by the given provider podcast id."""
        return [
            PodcastEpisode.from_dict(obj)
            for obj in await self.client.send_command(
                "music/podcasts/podcast_episode",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
            )
        ]

    async def podcast_versions(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        search: str | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        limit: int | None = None,
        offset: int | None = None,
        random_seed: int | None = None,
    ) -> list[Podcast]:
        """Return a searched, sorted and paged listing of podcast versions."""
        return [
            Podcast.from_dict(obj)
            for obj in await self.client.send_command(
                "music/podcasts/podcast_versions",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                search=search,
                sort_field=sort_field,
                sort_direction=sort_direction,
                limit=limit,
                offset=offset,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    sort_field,
                    sort_direction,
                    random_seed,
                    schema_version=VERSIONS_BROWSE_LISTING_SCHEMA_VERSION,
                    has_paging=any(value is not None for value in (search, limit, offset)),
                ),
            )
        ]

    async def remove_podcast(self, item_id: str | int, recursive: bool | None = None) -> None:
        """Delete library record from the database."""
        await self.client.send_command(
            "music/podcasts/remove",
            item_id=item_id,
            recursive=recursive,
        )

    async def update_podcast(
        self,
        item_id: str | int,
        update: Podcast,
        overwrite: bool | None = None,
    ) -> Podcast:
        """Update existing library record in the library database."""
        return Podcast.from_dict(
            await self.client.send_command(
                "music/podcasts/update",
                item_id=item_id,
                update=update,
                overwrite=overwrite,
            )
        )

    async def radio_count(self, favorite_only: bool | None = None) -> int:
        """Return the total number of items in the library."""
        return cast(
            "int",
            await self.client.send_command(
                "music/radios/count",
                favorite_only=favorite_only,
            ),
        )

    async def remove_radio(self, item_id: str | int, recursive: bool | None = None) -> None:
        """Delete library record from the database."""
        await self.client.send_command(
            "music/radios/remove",
            item_id=item_id,
            recursive=recursive,
        )

    async def update_radio(
        self,
        item_id: str | int,
        update: Radio,
        overwrite: bool | None = None,
    ) -> Radio:
        """Update existing library record in the library database."""
        return Radio.from_dict(
            await self.client.send_command(
                "music/radios/update",
                item_id=item_id,
                update=update,
                overwrite=overwrite,
            )
        )

    async def track_count(self, favorite_only: bool | None = None) -> int:
        """Return the total number of items in the library."""
        return cast(
            "int",
            await self.client.send_command(
                "music/tracks/count",
                favorite_only=favorite_only,
            ),
        )

    async def track_preview(self, provider_instance_id_or_domain: str, item_id: str) -> str:
        """Return url to short preview sample."""
        return cast(
            "str",
            await self.client.send_command(
                "music/tracks/preview",
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                item_id=item_id,
            ),
        )

    async def remove_track(self, item_id: str | int, recursive: bool | None = None) -> None:
        """Delete record from the database."""
        await self.client.send_command(
            "music/tracks/remove",
            item_id=item_id,
            recursive=recursive,
        )

    async def similar_tracks(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        limit: int | None = None,
        allow_lookup: bool | None = None,
        *,
        preferred_provider_instances: list[str] | None = None,
        search: str | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        offset: int | None = None,
        random_seed: int | None = None,
    ) -> list[Track]:
        """Get a searched, sorted and paged listing of similar tracks."""
        return [
            Track.from_dict(obj)
            for obj in await self.client.send_command(
                "music/tracks/similar_tracks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                limit=limit,
                allow_lookup=allow_lookup,
                preferred_provider_instances=preferred_provider_instances,
                search=search,
                sort_field=sort_field,
                sort_direction=sort_direction,
                offset=offset,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    sort_field,
                    sort_direction,
                    random_seed,
                    schema_version=VERSIONS_BROWSE_LISTING_SCHEMA_VERSION,
                    has_paging=any(value is not None for value in (search, offset)),
                ),
            )
        ]

    async def update_track(
        self,
        item_id: str | int,
        update: Track,
        overwrite: bool | None = None,
    ) -> Track:
        """Update existing library record in the library database."""
        return Track.from_dict(
            await self.client.send_command(
                "music/tracks/update",
                item_id=item_id,
                update=update,
                overwrite=overwrite,
            )
        )
