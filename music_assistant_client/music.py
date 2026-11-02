"""Handle Music/library related endpoints for Music Assistant."""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING, Any, NamedTuple, cast

from music_assistant_models.api import SortOptionInfo
from music_assistant_models.background_task import BackgroundTask
from music_assistant_models.enums import (
    AlbumType,
    ArtistType,
    ExternalID,
    ImageType,
    ListingType,
    MediaType,
    PlaylistMatchPolicy,
    ProviderSharing,
    SortDirection,
    SortField,
)
from music_assistant_models.helpers import create_sort_name
from music_assistant_models.media_items import (
    Album,
    Artist,
    Audiobook,
    BrowseFolder,
    Genre,
    ItemMapping,
    MediaCollection,
    MediaItemImage,
    MediaItemMetadata,
    MediaItemTranscriptCue,
    MediaItemType,
    Playlist,
    Podcast,
    PodcastEpisode,
    ProviderMapping,
    Radio,
    RecommendationFolder,
    SearchResults,
    SoundEffect,
    Track,
    media_from_dict,
)

from .constants import (
    ALBUM_TRACKS_LISTING_SCHEMA_VERSION,
    ARTIST_LISTING_SCHEMA_VERSION,
    ARTIST_PROVIDER_FILTER_SCHEMA_VERSION,
    IMPERSONATION_SCHEMA_VERSION,
    LIBRARY_USER_SCHEMA_VERSION,
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


# Schema 86 only had sort options for library listings, 89 added the rest.
_LIBRARY_LISTINGS = frozenset(
    {
        ListingType.LIBRARY_ARTISTS,
        ListingType.LIBRARY_ALBUMS,
        ListingType.LIBRARY_TRACKS,
        ListingType.LIBRARY_PLAYLISTS,
        ListingType.LIBRARY_RADIOS,
        ListingType.LIBRARY_AUDIOBOOKS,
        ListingType.LIBRARY_PODCASTS,
        ListingType.LIBRARY_GENRES,
    }
)


class PodcastEpisodeTranscript(NamedTuple):
    """Transcript of a podcast episode."""

    text: str | None
    cues: list[MediaItemTranscriptCue] | None


def _listing_require_schema(*requirements: tuple[int, *tuple[object, ...]]) -> int | None:
    """Return the highest schema version among the option groups in use."""
    return max(
        (version for version, *values in requirements if any(v is not None for v in values)),
        default=None,
    )


class Music:
    """Music(library) related endpoints/data for Music Assistant."""

    def __init__(self, client: MusicAssistantClient) -> None:
        """Handle Initialization."""
        self.client = client

    async def get_sort_options(self, listing: ListingType) -> list[SortOptionInfo]:
        """Get the sort options offered by a listing, with the default first."""
        return [
            SortOptionInfo.from_dict(item)
            for item in await self.client.send_command(
                "music/sort_options",
                listing=listing,
                require_schema=(
                    TYPED_LISTING_SCHEMA_VERSION
                    if listing in _LIBRARY_LISTINGS
                    else ALBUM_TRACKS_LISTING_SCHEMA_VERSION
                ),
            )
        ]

    #  Tracks related endpoints/commands

    async def get_library_tracks(  # noqa: PLR0913
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
        genre: int | list[int] | None = None,
        played_only: bool | None = None,
        explicit: bool | None = None,
        reachable_via: list[str] | None = None,
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
        :param genre: Filter by genre id(s).
        :param played_only: Only include played tracks.
        :param explicit: Filter by explicit content.
        :param reachable_via: Only include tracks reachable through one of these provider
            instance ids.
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
                genre=genre,
                played_only=played_only,
                explicit=explicit,
                reachable_via=reachable_via,
                require_schema=_listing_require_schema(
                    (TYPED_LISTING_SCHEMA_VERSION, sort_field, sort_direction),
                    (LIBRARY_USER_SCHEMA_VERSION, user),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
                    (101, genre, played_only, explicit, reachable_via),
                ),
            )
        ]

    async def get_track(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        album_uri: str | None = None,
        *,
        allow_update_metadata: bool | None = None,
        recursive: bool | None = None,
        user: str | LinkedUser | None = None,
    ) -> Track:
        """
        Get single Track from the server.

        :param allow_update_metadata: Schedule a metadata refresh on access.
        :param recursive: Resolve the full album details.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return Track.from_dict(
            await self.client.send_command(
                "music/tracks/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                album_uri=album_uri,
                allow_update_metadata=allow_update_metadata,
                recursive=recursive,
                require_schema=_listing_require_schema(
                    (101, allow_update_metadata, recursive),
                    (IMPERSONATION_SCHEMA_VERSION, user),
                ),
                **impersonation_arg(self.client.server_info, user),
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
                    (
                        VERSIONS_BROWSE_LISTING_SCHEMA_VERSION,
                        sort_field,
                        sort_direction,
                        search,
                        limit,
                        offset,
                    ),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
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
                    (
                        ARTIST_LISTING_SCHEMA_VERSION,
                        sort_field,
                        sort_direction,
                        search,
                        limit,
                        offset,
                    ),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
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
        genre: int | list[int] | None = None,
        played_only: bool | None = None,
        reachable_via: list[str] | None = None,
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
        :param genre: Filter by genre id(s).
        :param played_only: Only include played albums.
        :param reachable_via: Only include albums reachable through one of these provider
            instance ids.
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
                genre=genre,
                played_only=played_only,
                reachable_via=reachable_via,
                require_schema=_listing_require_schema(
                    (TYPED_LISTING_SCHEMA_VERSION, sort_field, sort_direction),
                    (LIBRARY_USER_SCHEMA_VERSION, user),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
                    (101, genre, played_only, reachable_via),
                ),
            )
        ]

    async def get_album(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        allow_update_metadata: bool | None = None,
        recursive: bool | None = None,
        user: str | LinkedUser | None = None,
    ) -> Album:
        """
        Get single Album from the server.

        :param allow_update_metadata: Schedule a metadata refresh on access.
        :param recursive: Resolve the full artist details.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return Album.from_dict(
            await self.client.send_command(
                "music/albums/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                allow_update_metadata=allow_update_metadata,
                recursive=recursive,
                require_schema=_listing_require_schema(
                    (101, allow_update_metadata, recursive),
                    (IMPERSONATION_SCHEMA_VERSION, user),
                ),
                **impersonation_arg(self.client.server_info, user),
            ),
        )

    async def get_album_tracks(  # noqa: PLR0913
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
        user: str | LinkedUser | None = None,
    ) -> list[Track]:
        """
        Get a searched, sorted and paged listing of tracks for an album.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
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
                    (
                        ALBUM_TRACKS_LISTING_SCHEMA_VERSION,
                        sort_field,
                        sort_direction,
                        search,
                        limit,
                        offset,
                    ),
                    (LISTING_FILTER_SCHEMA_VERSION, favorite),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
                    (IMPERSONATION_SCHEMA_VERSION, user),
                ),
                **impersonation_arg(self.client.server_info, user),
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
                    (
                        VERSIONS_BROWSE_LISTING_SCHEMA_VERSION,
                        sort_field,
                        sort_direction,
                        search,
                        limit,
                        offset,
                    ),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
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
        genre: int | list[int] | None = None,
        played_only: bool | None = None,
        artist_type: ArtistType | None = None,
        reachable_via: list[str] | None = None,
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
        :param genre: Filter by genre id(s).
        :param played_only: Only include played artists.
        :param artist_type: Only include artists of this type.
        :param reachable_via: Only include artists reachable through one of these provider
            instance ids.
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
                genre=genre,
                played_only=played_only,
                artist_type=artist_type,
                reachable_via=reachable_via,
                require_schema=_listing_require_schema(
                    (TYPED_LISTING_SCHEMA_VERSION, sort_field, sort_direction),
                    (LIBRARY_USER_SCHEMA_VERSION, user),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
                    (101, genre, played_only, artist_type, reachable_via),
                ),
            )
        ]

    async def get_artist(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        allow_update_metadata: bool | None = None,
        user: str | LinkedUser | None = None,
    ) -> Artist:
        """
        Get single Artist from the server.

        :param allow_update_metadata: Schedule a metadata refresh on access.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return Artist.from_dict(
            await self.client.send_command(
                "music/artists/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                allow_update_metadata=allow_update_metadata,
                require_schema=_listing_require_schema(
                    (101, allow_update_metadata),
                    (IMPERSONATION_SCHEMA_VERSION, user),
                ),
                **impersonation_arg(self.client.server_info, user),
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
        user: str | LinkedUser | None = None,
    ) -> list[Track]:
        """
        Get a searched, sorted and paged artist track listing.

        :param in_library_only: Deprecated and ignored; use provider_filter instead.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        del in_library_only
        return [
            Track.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/artist_tracks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                provider_filter=provider_filter,
                search=search,
                limit=limit,
                offset=offset,
                sort_field=sort_field,
                sort_direction=sort_direction,
                favorite=favorite,
                random_seed=random_seed,
                require_schema=_listing_require_schema(
                    (
                        ARTIST_LISTING_SCHEMA_VERSION,
                        sort_field,
                        sort_direction,
                        search,
                        limit,
                        offset,
                    ),
                    (LISTING_FILTER_SCHEMA_VERSION, favorite),
                    (ARTIST_PROVIDER_FILTER_SCHEMA_VERSION, provider_filter),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
                    (IMPERSONATION_SCHEMA_VERSION, user),
                ),
                **impersonation_arg(self.client.server_info, user),
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
        user: str | LinkedUser | None = None,
    ) -> list[Album]:
        """
        Get a searched, sorted and paged artist album listing.

        :param in_library_only: Deprecated and ignored; use provider_filter instead.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        del in_library_only
        return [
            Album.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/artist_albums",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
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
                    (
                        ARTIST_LISTING_SCHEMA_VERSION,
                        sort_field,
                        sort_direction,
                        search,
                        limit,
                        offset,
                    ),
                    (LISTING_FILTER_SCHEMA_VERSION, album_types, favorite),
                    (ARTIST_PROVIDER_FILTER_SCHEMA_VERSION, provider_filter),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
                    (IMPERSONATION_SCHEMA_VERSION, user),
                ),
                **impersonation_arg(self.client.server_info, user),
            )
        ]

    #  Playlist related endpoints/commands

    async def get_library_playlists(  # noqa: PLR0913
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
        genre: int | list[int] | None = None,
        played_only: bool | None = None,
        reachable_via: list[str] | None = None,
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
        :param genre: Filter by genre id(s).
        :param played_only: Only include played playlists.
        :param reachable_via: Only include playlists reachable through one of these provider
            instance ids.
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
                genre=genre,
                played_only=played_only,
                reachable_via=reachable_via,
                require_schema=_listing_require_schema(
                    (TYPED_LISTING_SCHEMA_VERSION, sort_field, sort_direction),
                    (LIBRARY_USER_SCHEMA_VERSION, user),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
                    (101, genre, played_only, reachable_via),
                ),
            )
        ]

    async def get_playlist(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        allow_update_metadata: bool | None = None,
        user: str | LinkedUser | None = None,
    ) -> Playlist:
        """
        Get single Playlist from the server.

        :param allow_update_metadata: Schedule a metadata refresh on access.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return Playlist.from_dict(
            await self.client.send_command(
                "music/playlists/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                allow_update_metadata=allow_update_metadata,
                require_schema=_listing_require_schema(
                    (101, allow_update_metadata),
                    (IMPERSONATION_SCHEMA_VERSION, user),
                ),
                **impersonation_arg(self.client.server_info, user),
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
        user: str | LinkedUser | None = None,
    ) -> list[Track]:
        """
        Get a page of tracks for the given playlist.

        :param force_refresh: Force a refresh of the (cached) playlist tracks.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
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
                    (
                        PLAYLIST_PODCAST_LISTING_SCHEMA_VERSION,
                        sort_field,
                        sort_direction,
                        favorite,
                        search,
                        limit,
                        offset,
                    ),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
                    (IMPERSONATION_SCHEMA_VERSION, user),
                ),
                **impersonation_arg(self.client.server_info, user),
            )
        ]

    async def add_playlist_tracks(
        self,
        db_playlist_id: str | int,
        uris: list[str],
        *,
        user: str | LinkedUser | None = None,
    ) -> BackgroundTask | None:
        """
        Add multiple tracks to playlist. Creates background tasks to process the action.

        Returns the background task on servers that report it.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        if result := await self.client.send_command(
            "music/playlists/add_playlist_tracks",
            db_playlist_id=db_playlist_id,
            uris=uris,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        ):
            return BackgroundTask.from_dict(result)
        return None

    async def remove_playlist_tracks(
        self,
        db_playlist_id: str | int,
        positions_to_remove: tuple[int, ...],
        *,
        user: str | LinkedUser | None = None,
    ) -> BackgroundTask | None:
        """
        Remove multiple tracks from playlist.

        Returns the background task on servers that report it.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        if result := await self.client.send_command(
            "music/playlists/remove_playlist_tracks",
            db_playlist_id=db_playlist_id,
            positions_to_remove=positions_to_remove,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        ):
            return BackgroundTask.from_dict(result)
        return None

    async def create_playlist(
        self,
        name: str,
        provider_instance_or_domain: str | None = None,
        *,
        media_types: list[MediaType] | None = None,
        strict_provider_instance: bool | None = None,
        user: str | LinkedUser | None = None,
    ) -> Playlist:
        """
        Create new playlist.

        :param media_types: Media types the playlist must support.
        :param strict_provider_instance: Do not fall back to another provider instance.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return Playlist.from_dict(
            await self.client.send_command(
                "music/playlists/create_playlist",
                name=name,
                provider_instance_or_domain=provider_instance_or_domain,
                media_types=media_types,
                strict_provider_instance=strict_provider_instance,
                require_schema=_listing_require_schema(
                    (101, media_types, strict_provider_instance),
                    (IMPERSONATION_SCHEMA_VERSION, user),
                ),
                **impersonation_arg(self.client.server_info, user),
            )
        )

    async def move_playlist_track(
        self, db_playlist_id: str | int, from_position: int, to_position: int
    ) -> None:
        """
        Move one item of a playlist to another position.

        :param db_playlist_id: Library playlist id.
        :param from_position: The current position of the item, 1-based.
        :param to_position: The position the item ends up at after the move, 1-based.
        """
        await self.client.send_command(
            "music/playlists/move_playlist_track",
            db_playlist_id=db_playlist_id,
            from_position=from_position,
            to_position=to_position,
            require_schema=101,
        )

    async def move_playlist_tracks(
        self, db_playlist_id: str | int, positions: list[int], to_position: int | None = None
    ) -> None:
        """
        Move items of a playlist as one block to another position.

        :param db_playlist_id: Library playlist id.
        :param positions: The current positions of the items, 1-based.
        :param to_position: The position the block's first item ends up at, 1-based.
            Omit it to move the items to the end of the playlist.
        """
        await self.client.send_command(
            "music/playlists/move_playlist_tracks",
            db_playlist_id=db_playlist_id,
            positions=positions,
            to_position=to_position,
            require_schema=101,
        )

    async def export_playlist(self, db_playlist_id: str | int) -> str:
        """Export a playlist to M3U8 format."""
        return cast(
            "str",
            await self.client.send_command(
                "music/playlists/export_playlist",
                db_playlist_id=db_playlist_id,
                require_schema=101,
            ),
        )

    async def import_playlist(
        self,
        m3u_data: str,
        library_matching: bool = False,
        match_providers: list[str] | None = None,
        match_policy: PlaylistMatchPolicy | None = None,
    ) -> Playlist:
        """
        Import a playlist from M3U8 format.

        :param m3u_data: The M3U8 playlist data as a string.
        :param library_matching: Deprecated; use match_policy instead.
        :param match_providers: Provider instances or domains to search when matching runs.
        :param match_policy: Minimum substitute confidence. Leave unset to skip matching.
        """
        return Playlist.from_dict(
            await self.client.send_command(
                "music/playlists/import_playlist",
                m3u_data=m3u_data,
                library_matching=library_matching,
                match_providers=match_providers,
                match_policy=match_policy,
                require_schema=101,
            )
        )

    async def migrate_playlist(
        self,
        db_playlist_id: str | int,
        destination_provider: str = "builtin",
        name: str | None = None,
        match_policy: PlaylistMatchPolicy = PlaylistMatchPolicy.SAME_RECORDING,
    ) -> BackgroundTask:
        """
        Queue copying a playlist to another provider or Music Assistant.

        :param db_playlist_id: Library database ID of the source playlist.
        :param destination_provider: Destination provider instance ID or domain.
        :param name: Optional destination playlist name.
        :param match_policy: Lowest track-match confidence that may be accepted.
        """
        return BackgroundTask.from_dict(
            await self.client.send_command(
                "music/playlists/migrate_playlist",
                db_playlist_id=db_playlist_id,
                destination_provider=destination_provider,
                name=name,
                match_policy=match_policy,
                require_schema=101,
            )
        )

    async def set_playlist_access(
        self,
        item_id: str | int,
        sharing: ProviderSharing,
        owner: str | None = None,
        shared_users: list[str] | None = None,
        collaborative: bool = False,
    ) -> Playlist:
        """
        Set who owns a Music Assistant playlist, who may see it and who may edit it.

        :param item_id: Library id of the playlist.
        :param sharing: Who, besides its owner, may see and play the playlist.
        :param owner: User id of the member owning the playlist, None for a playlist of the
            whole home.
        :param shared_users: The user ids the playlist is shared with, SELECTED sharing only.
        :param collaborative: Whether everyone the playlist is shared with may also edit it.
        """
        return Playlist.from_dict(
            await self.client.send_command(
                "music/playlists/set_access",
                item_id=item_id,
                sharing=sharing,
                owner=owner,
                shared_users=shared_users,
                collaborative=collaborative,
                require_schema=101,
            )
        )

    # Audiobooks related endpoints/commands

    async def get_library_audiobooks(  # noqa: PLR0913
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
        genre: int | list[int] | None = None,
        played_only: bool | None = None,
        reachable_via: list[str] | None = None,
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
        :param genre: Filter by genre id(s).
        :param played_only: Only include played audiobooks.
        :param reachable_via: Only include audiobooks reachable through one of these provider
            instance ids.
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
                genre=genre,
                played_only=played_only,
                reachable_via=reachable_via,
                require_schema=_listing_require_schema(
                    (TYPED_LISTING_SCHEMA_VERSION, sort_field, sort_direction),
                    (LIBRARY_USER_SCHEMA_VERSION, user),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
                    (101, genre, played_only, reachable_via),
                ),
            )
        ]

    async def get_audiobook(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        allow_update_metadata: bool | None = None,
        user: str | LinkedUser | None = None,
    ) -> Audiobook:
        """
        Get single Audiobook from the server.

        :param allow_update_metadata: Schedule a metadata refresh on access.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return Audiobook.from_dict(
            await self.client.send_command(
                "music/audiobooks/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                allow_update_metadata=allow_update_metadata,
                require_schema=_listing_require_schema(
                    (101, allow_update_metadata),
                    (IMPERSONATION_SCHEMA_VERSION, user),
                ),
                **impersonation_arg(self.client.server_info, user),
            ),
        )

    # Podcasts related endpoints/commands

    async def get_library_podcasts(  # noqa: PLR0913
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
        genre: int | list[int] | None = None,
        played_only: bool | None = None,
        reachable_via: list[str] | None = None,
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
        :param genre: Filter by genre id(s).
        :param played_only: Only include played podcasts.
        :param reachable_via: Only include podcasts reachable through one of these provider
            instance ids.
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
                genre=genre,
                played_only=played_only,
                reachable_via=reachable_via,
                require_schema=_listing_require_schema(
                    (TYPED_LISTING_SCHEMA_VERSION, sort_field, sort_direction),
                    (LIBRARY_USER_SCHEMA_VERSION, user),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
                    (101, genre, played_only, reachable_via),
                ),
            )
        ]

    async def get_podcast(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        allow_update_metadata: bool | None = None,
        user: str | LinkedUser | None = None,
    ) -> Podcast:
        """
        Get single Podcast from the server.

        :param allow_update_metadata: Schedule a metadata refresh on access.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return Podcast.from_dict(
            await self.client.send_command(
                "music/podcasts/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                allow_update_metadata=allow_update_metadata,
                require_schema=_listing_require_schema(
                    (101, allow_update_metadata),
                    (IMPERSONATION_SCHEMA_VERSION, user),
                ),
                **impersonation_arg(self.client.server_info, user),
            ),
        )

    async def get_podcast_episodes(  # noqa: PLR0913
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
        user: str | LinkedUser | None = None,
    ) -> list[PodcastEpisode]:
        """
        Get a page of episodes for the given podcast.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
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
                    (
                        PLAYLIST_PODCAST_LISTING_SCHEMA_VERSION,
                        sort_field,
                        sort_direction,
                        fully_played,
                        search,
                        limit,
                        offset,
                    ),
                    (LISTING_FILTER_SCHEMA_VERSION, exclude_item_id),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
                    (IMPERSONATION_SCHEMA_VERSION, user),
                ),
                **impersonation_arg(self.client.server_info, user),
            )
        ]

    #  Radio related endpoints/commands

    async def get_library_radios(  # noqa: PLR0913
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
        genre: int | list[int] | None = None,
        played_only: bool | None = None,
        reachable_via: list[str] | None = None,
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
        :param genre: Filter by genre id(s).
        :param played_only: Only include played radios.
        :param reachable_via: Only include radios reachable through one of these provider
            instance ids.
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
                genre=genre,
                played_only=played_only,
                reachable_via=reachable_via,
                require_schema=_listing_require_schema(
                    (TYPED_LISTING_SCHEMA_VERSION, sort_field, sort_direction),
                    (LIBRARY_USER_SCHEMA_VERSION, user),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
                    (101, genre, played_only, reachable_via),
                ),
            )
        ]

    async def get_library_genres(  # noqa: PLR0913
        self,
        favorite: bool | None = None,
        *,
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
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        random_seed: int | None = None,
        user: str | LinkedUser | None = None,
    ) -> list[Genre]:
        """Get a searched, sorted and paged genre listing.

        :param favorite: Filter by favorite status.
        :param search: Filter by search query.
        :param limit: Maximum number of items to return.
        :param offset: Number of items to skip.
        :param order_by: Deprecated sort key; use sort_field and sort_direction instead.
        :param provider: Ignored by the server; genres are library-only.
        :param played_only: Only return genres that have been played.
        :param hide_empty: True returns only genres with media mappings, False returns all
            genres, None returns only the default genres. Ignored when media_type is set.
        :param media_type: Return all genres with at least one mapping for this media type.
        :param content_type: Restrict to one genre taxonomy: "music", "podcast" or "audiobook".
        :param summary: Return slim list-view items; set to False for fully hydrated items.
        :param sort_field: Typed sort field.
        :param sort_direction: Direction for the selected sort field.
        :param random_seed: Keep random ordering stable across pages.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
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
                    (TYPED_LISTING_SCHEMA_VERSION, sort_field, sort_direction),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
                    (IMPERSONATION_SCHEMA_VERSION, user),
                ),
                **impersonation_arg(self.client.server_info, user),
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
                    (TYPED_LISTING_SCHEMA_VERSION, sort_field, sort_direction),
                    (VERSIONS_BROWSE_LISTING_SCHEMA_VERSION, search),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
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
                    (TYPED_LISTING_SCHEMA_VERSION, sort_field, sort_direction),
                    (VERSIONS_BROWSE_LISTING_SCHEMA_VERSION, search),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
                ),
            )
        ]

    async def get_genre(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        allow_update_metadata: bool | None = None,
        user: str | LinkedUser | None = None,
    ) -> Genre:
        """
        Get single Genre from the server.

        :param allow_update_metadata: Schedule a metadata refresh on access.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return Genre.from_dict(
            await self.client.send_command(
                "music/genres/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                allow_update_metadata=allow_update_metadata,
                require_schema=101,
                **impersonation_arg(self.client.server_info, user),
            ),
        )

    async def get_genre_by_external_id(
        self, external_id: str, external_id_type: ExternalID | None = None
    ) -> Genre | None:
        """Get a genre by external ID, querying the library then the active providers."""
        if result := await self.client.send_command(
            "music/genres/get_by_external_id",
            external_id=external_id,
            external_id_type=external_id_type,
            require_schema=101,
        ):
            return Genre.from_dict(result)
        return None

    async def get_genre_collection(
        self,
        item_id: str,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        favorite: bool | None = None,
        *,
        user: str | LinkedUser | None = None,
    ) -> MediaCollection[Genre]:
        """
        Get a genre collection and optionally search or page its items.

        :param item_id: The collection ID.
        :param search: Only include items whose name contains this text.
        :param limit: Maximum number of items to return; omitted or 0 returns them all.
        :param offset: Number of items to skip.
        :param favorite: Only include the items the current user likes (True) or dislikes.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return MediaCollection[Genre].from_dict(
            await self.client.send_command(
                "music/genres/get_collection",
                item_id=item_id,
                search=search,
                limit=limit,
                offset=offset,
                favorite=favorite,
                require_schema=101,
                **impersonation_arg(self.client.server_info, user),
            )
        )

    async def genre_count(self, favorite_only: bool | None = None) -> int:
        """Return the total number of genres in the library."""
        return cast(
            "int",
            await self.client.send_command(
                "music/genres/count",
                favorite_only=favorite_only,
                require_schema=101,
            ),
        )

    async def add_genre(self, item: Genre, overwrite_existing: bool = False) -> Genre:
        """Add a genre to the library and return the new (or updated) library item."""
        return Genre.from_dict(
            await self.client.send_command(
                "music/genres/add",
                item=item,
                overwrite_existing=overwrite_existing,
                require_schema=101,
            )
        )

    async def update_genre(
        self,
        item_id: str | int,
        update: Genre,
        overwrite: bool | None = None,
    ) -> Genre:
        """Update existing library record in the library database."""
        return Genre.from_dict(
            await self.client.send_command(
                "music/genres/update",
                item_id=item_id,
                update=update,
                overwrite=overwrite,
                require_schema=101,
            )
        )

    async def remove_genre(
        self,
        item_id: str | int,
        recursive: bool | None = None,
        exclude_globally: bool | None = None,
    ) -> None:
        """
        Delete genre record from the database.

        :param exclude_globally: Keep the scanner from recreating the genre (server default).
        """
        await self.client.send_command(
            "music/genres/remove",
            item_id=item_id,
            recursive=recursive,
            exclude_globally=exclude_globally,
            require_schema=101,
        )

    async def genre_overview(
        self,
        item_id: str,
        provider_instance_id_or_domain: str | None = None,
        limit: int = 25,
    ) -> list[RecommendationFolder]:
        """Return overview rows for a genre (all media types)."""
        return [
            RecommendationFolder.from_dict(item)
            for item in await self.client.send_command(
                "music/genres/overview",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                limit=limit,
                require_schema=101,
            )
        ]

    async def add_genre_alias(self, genre_id: str | int, alias: str) -> Genre:
        """Add an alias string to a genre."""
        return Genre.from_dict(
            await self.client.send_command(
                "music/genres/add_alias",
                genre_id=genre_id,
                alias=alias,
                require_schema=101,
            )
        )

    async def remove_genre_alias(self, genre_id: str | int, alias: str) -> Genre:
        """Remove an alias string from a genre."""
        return Genre.from_dict(
            await self.client.send_command(
                "music/genres/remove_alias",
                genre_id=genre_id,
                alias=alias,
                require_schema=101,
            )
        )

    async def promote_genre_alias(self, genre_id: str | int, alias: str) -> Genre:
        """Promote an alias to a standalone genre and return the new genre."""
        return Genre.from_dict(
            await self.client.send_command(
                "music/genres/promote_alias",
                genre_id=genre_id,
                alias=alias,
                require_schema=101,
            )
        )

    async def add_genre_media_mapping(
        self,
        genre_id: str | int,
        media_type: MediaType,
        media_id: str | int,
        alias: str | None = None,
    ) -> None:
        """
        Map a (library) media item to a genre.

        :param alias: The alias string that caused this mapping; the genre's name if omitted.
        """
        await self.client.send_command(
            "music/genres/add_media_mapping",
            genre_id=genre_id,
            media_type=media_type,
            media_id=media_id,
            alias=alias,
            require_schema=101,
        )

    async def remove_genre_media_mapping(
        self, genre_id: str | int, media_type: MediaType, media_id: str | int
    ) -> None:
        """Remove a (library) media item mapping from a genre."""
        await self.client.send_command(
            "music/genres/remove_media_mapping",
            genre_id=genre_id,
            media_type=media_type,
            media_id=media_id,
            require_schema=101,
        )

    async def genres_for_media_item(
        self, media_type: MediaType, media_id: str | int
    ) -> list[Genre]:
        """Return all genres mapped to a given (library) media item."""
        return [
            Genre.from_dict(item)
            for item in await self.client.send_command(
                "music/genres/genres_for_media_item",
                media_type=media_type,
                media_id=media_id,
                require_schema=101,
            )
        ]

    async def genre_exclusions_for_media_item(
        self, media_type: MediaType, media_id: str | int
    ) -> list[Genre]:
        """Return all genres excluded from a given (library) media item."""
        return [
            Genre.from_dict(item)
            for item in await self.client.send_command(
                "music/genres/genre_exclusions_for_media_item",
                media_type=media_type,
                media_id=media_id,
                require_schema=101,
            )
        ]

    async def exclude_genre_from_media_item(
        self, genre_id: str | int, media_type: MediaType, media_id: str | int
    ) -> None:
        """Permanently exclude a genre from being mapped to a (library) media item."""
        await self.client.send_command(
            "music/genres/exclude_genre_from_media_item",
            genre_id=genre_id,
            media_type=media_type,
            media_id=media_id,
            require_schema=101,
        )

    async def remove_genre_exclusion(
        self, genre_id: str | int, media_type: MediaType, media_id: str | int
    ) -> None:
        """Remove a genre exclusion, allowing the scanner to re-map it on the next run."""
        await self.client.send_command(
            "music/genres/remove_genre_exclusion",
            genre_id=genre_id,
            media_type=media_type,
            media_id=media_id,
            require_schema=101,
        )

    async def merge_genres(self, genre_ids: list[str | int], target_genre_id: str | int) -> Genre:
        """Merge one or more genres into a target genre."""
        return Genre.from_dict(
            await self.client.send_command(
                "music/genres/merge",
                genre_ids=genre_ids,
                target_genre_id=target_genre_id,
                require_schema=101,
            )
        )

    async def genre_media_counts(self, genre_ids: list[str]) -> dict[str, dict[str, int]]:
        """Return media item counts per media type for each requested genre (by genre id)."""
        return cast(
            "dict[str, dict[str, int]]",
            await self.client.send_command(
                "music/genres/media_counts",
                genre_ids=genre_ids,
                require_schema=101,
            ),
        )

    async def genre_global_exclusions(self) -> list[dict[str, Any]]:
        """Return all globally excluded genres."""
        return cast(
            "list[dict[str, Any]]",
            await self.client.send_command("music/genres/global_exclusions", require_schema=101),
        )

    async def remove_genre_global_exclusion(self, genre_id: int) -> Genre:
        """Lift a global genre exclusion and return the restored genre."""
        return Genre.from_dict(
            await self.client.send_command(
                "music/genres/remove_global_exclusion",
                genre_id=genre_id,
                require_schema=101,
            )
        )

    async def restore_default_genres(
        self, full_restore: bool = False, content_type: str | None = None
    ) -> list[Genre]:
        """
        Restore the default genres for one or every taxonomy.

        :param full_restore: Delete all existing genres and recreate them from the defaults.
        :param content_type: Restrict a non-destructive restore to "music", "podcast" or
            "audiobook".
        """
        return [
            Genre.from_dict(item)
            for item in await self.client.send_command(
                "music/genres/restore_defaults",
                full_restore=full_restore,
                content_type=content_type,
                require_schema=101,
            )
        ]

    async def scan_genre_mappings(self) -> dict[str, Any]:
        """Manually trigger a genre mapping scan and return its status."""
        return cast(
            "dict[str, Any]",
            await self.client.send_command("music/genres/scan_mappings", require_schema=101),
        )

    async def genre_scanner_status(self) -> dict[str, Any]:
        """Get status of the genre mapping background scanner."""
        return cast(
            "dict[str, Any]",
            await self.client.send_command("music/genres/scanner_status", require_schema=101),
        )

    async def get_radio(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        allow_update_metadata: bool | None = None,
        user: str | LinkedUser | None = None,
    ) -> Radio:
        """
        Get single Radio from the server.

        :param allow_update_metadata: Schedule a metadata refresh on access.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return Radio.from_dict(
            await self.client.send_command(
                "music/radios/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                allow_update_metadata=allow_update_metadata,
                require_schema=_listing_require_schema(
                    (101, allow_update_metadata),
                    (IMPERSONATION_SCHEMA_VERSION, user),
                ),
                **impersonation_arg(self.client.server_info, user),
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
                    (
                        VERSIONS_BROWSE_LISTING_SCHEMA_VERSION,
                        sort_field,
                        sort_direction,
                        search,
                        limit,
                        offset,
                    ),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
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
        *,
        providers: list[str] | None = None,
    ) -> SearchResults:
        """Perform global search for media items on all providers.

        :param search_query: Search query.
        :param media_types: A list of media_types to include.
        :param limit: number of items to return in the search (per type).
        :param user: Optionally execute the search on behalf of this user: a user_id or
            username string, or a LinkedUser reference by auth provider.
            Requires the authenticated client to have sufficient permissions.
        :param providers: Only search these provider instance ids or domains, where "library"
            selects the library.
        """
        return SearchResults.from_dict(
            await self.client.send_command(
                "music/search",
                search_query=search_query,
                media_types=media_types,
                limit=limit,
                library_only=library_only,
                providers=providers,
                require_schema=101 if providers is not None else None,
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
                    (
                        VERSIONS_BROWSE_LISTING_SCHEMA_VERSION,
                        sort_field,
                        sort_direction,
                        search,
                        limit,
                        offset,
                    ),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
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
        *,
        providers: list[str] | None = None,
        always_include_media_types: list[MediaType] | None = None,
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
        :param providers: Only include items reachable through one of these provider
            instance ids; an empty list returns no items.
        :param always_include_media_types: Media types to include regardless of
            user_initiated_only.
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
                providers=providers,
                always_include_media_types=always_include_media_types,
                require_schema=_listing_require_schema(
                    (101, providers, always_include_media_types)
                ),
            )
        ]

    async def recently_added_tracks(self, limit: int = 10) -> list[Track]:
        """Return a list of the last added tracks."""
        return [
            Track.from_dict(item)
            for item in await self.client.send_command(
                "music/recently_added_tracks",
                limit=limit,
                require_schema=101,
            )
        ]

    async def sound_effects(self) -> list[SoundEffect]:
        """Return all sound effect items from providers supporting them."""
        return [
            SoundEffect.from_dict(item)
            for item in await self.client.send_command("music/sound_effects", require_schema=101)
        ]

    async def in_progress_items(
        self,
        limit: int = 10,
        all_users: bool = False,
        *,
        providers: list[str] | None = None,
    ) -> list[ItemMapping]:
        """
        Return a list of the Audiobooks and PodcastEpisodes that are in progress.

        :param providers: Only include items reachable through one of these provider
            instance ids; an empty list returns no items.
        """
        return [
            ItemMapping.from_dict(item)
            for item in await self.client.send_command(
                "music/in_progress_items",
                limit=limit,
                all_users=all_users,
                providers=providers,
                require_schema=101 if providers is not None else None,
            )
        ]

    async def recommendations(
        self, *, user: str | LinkedUser | None = None
    ) -> list[RecommendationFolder]:
        """
        Get all recommendations.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return [
            RecommendationFolder.from_dict(item)
            for item in await self.client.send_command(
                "music/recommendations",
                require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
                **impersonation_arg(self.client.server_info, user),
            )
        ]

    async def recommendation_items(
        self,
        provider: str,
        item_id: str,
        providers: list[str] | None = None,
        *,
        user: str | LinkedUser | None = None,
    ) -> list[MediaItemType | ItemMapping | BrowseFolder]:
        """
        Get the items for a single recommendation row.

        :param provider: The provider instance id owning the row.
        :param item_id: The item_id of the row, as returned by the recommendations listing.
        :param providers: Only include items reachable through one of these provider
            instance ids, on rows that support a provider filter.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return [
            BrowseFolder.from_dict(item)
            if item.get("media_type") == MediaType.FOLDER
            else media_from_dict(item)
            for item in await self.client.send_command(
                "music/recommendations/items",
                provider=provider,
                item_id=item_id,
                providers=providers,
                require_schema=101,
                **impersonation_arg(self.client.server_info, user),
            )
        ]

    async def get_item_by_uri(
        self,
        uri: str,
        *,
        allow_update_metadata: bool | None = None,
        user: str | LinkedUser | None = None,
    ) -> MediaItemType | ItemMapping:
        """
        Get single music item providing a mediaitem uri.

        :param allow_update_metadata: Schedule a metadata refresh on access.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return media_from_dict(
            await self.client.send_command(
                "music/item_by_uri",
                uri=uri,
                allow_update_metadata=allow_update_metadata,
                require_schema=_listing_require_schema(
                    (101, allow_update_metadata),
                    (IMPERSONATION_SCHEMA_VERSION, user),
                ),
                **impersonation_arg(self.client.server_info, user),
            )
        )

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
        *,
        allow_update_metadata: bool | None = None,
        user: str | LinkedUser | None = None,
    ) -> MediaItemType | ItemMapping:
        """
        Get single music item by id and media type.

        :param allow_update_metadata: Schedule a metadata refresh on access.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return media_from_dict(
            await self.client.send_command(
                "music/item",
                media_type=media_type,
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                allow_update_metadata=allow_update_metadata,
                require_schema=_listing_require_schema(
                    (101, allow_update_metadata),
                    (IMPERSONATION_SCHEMA_VERSION, user),
                ),
                **impersonation_arg(self.client.server_info, user),
            )
        )

    async def get_library_item_by_prov_id(
        self,
        media_type: MediaType,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        user: str | LinkedUser | None = None,
    ) -> MediaItemType | None:
        """
        Get single library music item by id and media type.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        if result := await self.client.send_command(
            "music/get_library_item",
            media_type=media_type,
            item_id=item_id,
            provider_instance_id_or_domain=provider_instance_id_or_domain,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
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

    async def set_item_favorite(
        self,
        item: str | MediaItemType | ItemMapping,
        favorite: bool | None,
    ) -> None:
        """
        Set the calling user's like, dislike or unset on a media item.

        :param item: The item (uri or media item) to set the state on.
        :param favorite: True to like, False to dislike, None to clear the state.
        """
        await self.client.send_command(
            "music/favorites/set_item",
            item=item,
            favorite=favorite,
            require_schema=101,
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

    async def add_provider_mapping(
        self, media_type: MediaType, db_id: str, mapping: ProviderMapping
    ) -> None:
        """Add provider mapping to the given library item."""
        await self.client.send_command(
            "music/add_provider_mapping",
            media_type=media_type,
            db_id=db_id,
            mapping=mapping,
            require_schema=101,
        )

    async def remove_provider_mapping(
        self, media_type: MediaType, db_id: str, mapping: ProviderMapping
    ) -> None:
        """Remove provider mapping from the given library item."""
        await self.client.send_command(
            "music/remove_provider_mapping",
            media_type=media_type,
            db_id=db_id,
            mapping=mapping,
            require_schema=101,
        )

    async def match_providers(self, media_type: MediaType, db_id: str) -> None:
        """Search for mappings on all providers for the given library item."""
        await self.client.send_command(
            "music/match_providers",
            media_type=media_type,
            db_id=db_id,
            require_schema=101,
        )

    async def mark_item_played(
        self,
        media_item: MediaItemType,
        fully_played: bool = True,
        userid: str | None = None,
        *,
        seconds_played: int | None = None,
        playback_speed: float | None = None,
    ) -> None:
        """
        Mark item as played in playlog.

        :param media_item: The media item to mark as played.
        :param fully_played: If True, mark the item as fully played.
        :param userid: Optionally attribute this play to a specific user (instead of the user
            the client is authenticated as). Requires the authenticated client to have
            sufficient permissions.
        :param seconds_played: The number of seconds played (the resume position).
        :param playback_speed: The playback speed to store (audiobooks/podcasts).
        """
        await self.client.send_command(
            "music/mark_played",
            media_item=media_item,
            fully_played=fully_played,
            userid=userid,
            seconds_played=seconds_played,
            playback_speed=playback_speed,
            require_schema=_listing_require_schema((101, seconds_played, playback_speed)),
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

    async def get_album_by_external_id(
        self, external_id: str, external_id_type: ExternalID | None = None
    ) -> Album | None:
        """Get an album by external ID, querying the library then the active providers."""
        if result := await self.client.send_command(
            "music/albums/get_by_external_id",
            external_id=external_id,
            external_id_type=external_id_type,
            require_schema=101,
        ):
            return Album.from_dict(result)
        return None

    async def get_album_collection(
        self,
        item_id: str,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        favorite: bool | None = None,
        *,
        user: str | LinkedUser | None = None,
    ) -> MediaCollection[Album]:
        """
        Get an album collection and optionally search or page its items.

        :param item_id: The collection ID.
        :param search: Only include items whose name contains this text.
        :param limit: Maximum number of items to return; omitted or 0 returns them all.
        :param offset: Number of items to skip.
        :param favorite: Only include the items the current user likes (True) or dislikes.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return MediaCollection[Album].from_dict(
            await self.client.send_command(
                "music/albums/get_collection",
                item_id=item_id,
                search=search,
                limit=limit,
                offset=offset,
                favorite=favorite,
                require_schema=101,
                **impersonation_arg(self.client.server_info, user),
            )
        )

    async def artist_count(
        self,
        favorite_only: bool | None = None,
        album_artists_only: bool | None = None,
        artist_type: ArtistType | None = None,
    ) -> int:
        """
        Return the total number of items in the library.

        :param artist_type: Only count artists of this type.
        """
        return cast(
            "int",
            await self.client.send_command(
                "music/artists/count",
                favorite_only=favorite_only,
                album_artists_only=album_artists_only,
                artist_type=artist_type,
                require_schema=101 if artist_type is not None else None,
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

    async def get_artist_by_external_id(
        self, external_id: str, external_id_type: ExternalID | None = None
    ) -> Artist | None:
        """Get an artist by external ID, querying the library then the active providers."""
        if result := await self.client.send_command(
            "music/artists/get_by_external_id",
            external_id=external_id,
            external_id_type=external_id_type,
            require_schema=101,
        ):
            return Artist.from_dict(result)
        return None

    async def get_artist_collection(
        self,
        item_id: str,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        favorite: bool | None = None,
        *,
        user: str | LinkedUser | None = None,
    ) -> MediaCollection[Artist]:
        """
        Get an artist collection and optionally search or page its items.

        :param item_id: The collection ID.
        :param search: Only include items whose name contains this text.
        :param limit: Maximum number of items to return; omitted or 0 returns them all.
        :param offset: Number of items to skip.
        :param favorite: Only include the items the current user likes (True) or dislikes.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return MediaCollection[Artist].from_dict(
            await self.client.send_command(
                "music/artists/get_collection",
                item_id=item_id,
                search=search,
                limit=limit,
                offset=offset,
                favorite=favorite,
                require_schema=101,
                **impersonation_arg(self.client.server_info, user),
            )
        )

    async def artist_tracks_count(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        provider_filter: str | None = None,
        search: str | None = None,
        favorite: bool | None = None,
    ) -> int:
        """Return the number of tracks in an artist listing."""
        return cast(
            "int",
            await self.client.send_command(
                "music/artists/artist_tracks_count",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                provider_filter=provider_filter,
                search=search,
                favorite=favorite,
                require_schema=101,
            ),
        )

    async def artist_albums_count(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        provider_filter: str | None = None,
        search: str | None = None,
        album_types: list[AlbumType] | None = None,
        favorite: bool | None = None,
    ) -> int:
        """Return the number of albums in an artist listing."""
        return cast(
            "int",
            await self.client.send_command(
                "music/artists/artist_albums_count",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                provider_filter=provider_filter,
                search=search,
                album_types=album_types,
                favorite=favorite,
                require_schema=101,
            ),
        )

    async def artist_appears_on(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        provider_filter: str | None = None,
        search: str | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        limit: int | None = None,
        offset: int | None = None,
        random_seed: int | None = None,
    ) -> list[Album]:
        """Return the albums an artist appears on without being an album artist."""
        return [
            Album.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/artist_appears_on",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                provider_filter=provider_filter,
                search=search,
                sort_field=sort_field,
                sort_direction=sort_direction,
                limit=limit,
                offset=offset,
                random_seed=random_seed,
                require_schema=101,
            )
        ]

    async def artist_appears_on_count(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        provider_filter: str | None = None,
        search: str | None = None,
    ) -> int:
        """Return the number of albums an artist appears on without being an album artist."""
        return cast(
            "int",
            await self.client.send_command(
                "music/artists/artist_appears_on_count",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                provider_filter=provider_filter,
                search=search,
                require_schema=101,
            ),
        )

    async def artist_audiobooks(  # noqa: PLR0913
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        artist_type: ArtistType | None = None,
        in_library_only: bool = False,
        *,
        search: str | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        limit: int | None = None,
        offset: int | None = None,
        provider_filter: str | None = None,
        collapse_collections: bool = False,
        random_seed: int | None = None,
    ) -> list[Audiobook | MediaCollection[Audiobook]]:
        """
        Return the audiobooks of an artist, searched, sorted and paged.

        :param artist_type: Whether the artist is listed as the author (default) or the
            narrator; can be omitted for library artists.
        :param in_library_only: Only list the audiobooks that are in the library.
        :param provider_filter: Only list audiobooks from this provider instance.
        :param collapse_collections: Return a collection instead of its in-library audiobooks.
        """
        return [
            MediaCollection[Audiobook].from_dict(item)
            if item.get("media_type") == MediaType.COLLECTION
            else Audiobook.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/artist_audiobooks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                artist_type=artist_type,
                in_library_only=in_library_only,
                search=search,
                sort_field=sort_field,
                sort_direction=sort_direction,
                limit=limit,
                offset=offset,
                provider_filter=provider_filter,
                collapse_collections=collapse_collections,
                random_seed=random_seed,
                require_schema=101,
            )
        ]

    async def discography(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        search: str | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        limit: int | None = None,
        offset: int | None = None,
        album_types: list[AlbumType] | None = None,
        random_seed: int | None = None,
    ) -> list[Album]:
        """
        Return a library artist's discography as MusicBrainz knows it, searched, sorted and paged.

        :param provider_instance_id_or_domain: The provider of the artist, must be "library".
        :param album_types: Only list the releases MusicBrainz gives one of these types.
        """
        return [
            Album.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/discography",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                search=search,
                sort_field=sort_field,
                sort_direction=sort_direction,
                limit=limit,
                offset=offset,
                album_types=album_types,
                random_seed=random_seed,
                require_schema=101,
            )
        ]

    async def discography_count(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        search: str | None = None,
        album_types: list[AlbumType] | None = None,
    ) -> int:
        """Return the number of releases in a library artist's discography."""
        return cast(
            "int",
            await self.client.send_command(
                "music/artists/discography_count",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                search=search,
                album_types=album_types,
                require_schema=101,
            ),
        )

    async def top_tracks(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        provider_filter: str | None = None,
        search: str | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        limit: int | None = None,
        offset: int | None = None,
        random_seed: int | None = None,
    ) -> list[Track]:
        """Return the top/featured tracks of an artist, searched, sorted and paged."""
        return [
            Track.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/top_tracks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                provider_filter=provider_filter,
                search=search,
                sort_field=sort_field,
                sort_direction=sort_direction,
                limit=limit,
                offset=offset,
                random_seed=random_seed,
                require_schema=101,
            )
        ]

    async def top_albums(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        provider_filter: str | None = None,
        search: str | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        limit: int | None = None,
        offset: int | None = None,
        random_seed: int | None = None,
    ) -> list[Album]:
        """Return the top/featured albums of an artist, searched, sorted and paged."""
        return [
            Album.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/top_albums",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                provider_filter=provider_filter,
                search=search,
                sort_field=sort_field,
                sort_direction=sort_direction,
                limit=limit,
                offset=offset,
                random_seed=random_seed,
                require_schema=101,
            )
        ]

    async def similar_artists(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        *,
        provider_filter: str | None = None,
        limit: int | None = None,
        search: str | None = None,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        offset: int | None = None,
        random_seed: int | None = None,
    ) -> list[Artist]:
        """Return the artists similar to an artist, searched, sorted and paged."""
        return [
            Artist.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/similar_artists",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                provider_filter=provider_filter,
                limit=limit,
                search=search,
                sort_field=sort_field,
                sort_direction=sort_direction,
                offset=offset,
                random_seed=random_seed,
                require_schema=101,
            )
        ]

    async def library_artist_types(self) -> list[ArtistType]:
        """Get all supported in-library artist types."""
        return [
            ArtistType(item)
            for item in await self.client.send_command(
                "music/artists/library_artist_types",
                require_schema=101,
            )
        ]

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
                    (
                        VERSIONS_BROWSE_LISTING_SCHEMA_VERSION,
                        sort_field,
                        sort_direction,
                        search,
                        limit,
                        offset,
                    ),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
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

    async def get_audiobook_by_external_id(
        self, external_id: str, external_id_type: ExternalID | None = None
    ) -> Audiobook | None:
        """Get an audiobook by external ID, querying the library then the active providers."""
        if result := await self.client.send_command(
            "music/audiobooks/get_by_external_id",
            external_id=external_id,
            external_id_type=external_id_type,
            require_schema=101,
        ):
            return Audiobook.from_dict(result)
        return None

    async def get_audiobook_collection(
        self,
        item_id: str,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        favorite: bool | None = None,
        *,
        user: str | LinkedUser | None = None,
    ) -> MediaCollection[Audiobook]:
        """
        Get an audiobook collection and optionally search or page its items.

        :param item_id: The collection ID.
        :param search: Only include items whose name contains this text.
        :param limit: Maximum number of items to return; omitted or 0 returns them all.
        :param offset: Number of items to skip.
        :param favorite: Only include the items the current user likes (True) or dislikes.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return MediaCollection[Audiobook].from_dict(
            await self.client.send_command(
                "music/audiobooks/get_collection",
                item_id=item_id,
                search=search,
                limit=limit,
                offset=offset,
                favorite=favorite,
                require_schema=101,
                **impersonation_arg(self.client.server_info, user),
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
        *,
        user: str | LinkedUser | None = None,
    ) -> Playlist:
        """
        Update existing library record in the library database.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return Playlist.from_dict(
            await self.client.send_command(
                "music/playlists/update",
                item_id=item_id,
                update=update,
                overwrite=overwrite,
                require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
                **impersonation_arg(self.client.server_info, user),
            )
        )

    async def get_playlist_by_external_id(
        self, external_id: str, external_id_type: ExternalID | None = None
    ) -> Playlist | None:
        """Get a playlist by external ID, querying the library then the active providers."""
        if result := await self.client.send_command(
            "music/playlists/get_by_external_id",
            external_id=external_id,
            external_id_type=external_id_type,
            require_schema=101,
        ):
            return Playlist.from_dict(result)
        return None

    async def get_playlist_collection(
        self,
        item_id: str,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        favorite: bool | None = None,
        *,
        user: str | LinkedUser | None = None,
    ) -> MediaCollection[Playlist]:
        """
        Get a playlist collection and optionally search or page its items.

        :param item_id: The collection ID.
        :param search: Only include items whose name contains this text.
        :param limit: Maximum number of items to return; omitted or 0 returns them all.
        :param offset: Number of items to skip.
        :param favorite: Only include the items the current user likes (True) or dislikes.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return MediaCollection[Playlist].from_dict(
            await self.client.send_command(
                "music/playlists/get_collection",
                item_id=item_id,
                search=search,
                limit=limit,
                offset=offset,
                favorite=favorite,
                require_schema=101,
                **impersonation_arg(self.client.server_info, user),
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
        *,
        user: str | LinkedUser | None = None,
    ) -> PodcastEpisode:
        """
        Return single podcast episode by the given provider podcast id.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return PodcastEpisode.from_dict(
            await self.client.send_command(
                "music/podcasts/podcast_episode",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
                **impersonation_arg(self.client.server_info, user),
            )
        )

    async def podcast_episode_transcript(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> PodcastEpisodeTranscript:
        """
        Return a podcast episode's transcript as readable text and timed cues.

        Both are None when no transcript is available for the episode.

        :param item_id: The provider episode id.
        :param provider_instance_id_or_domain: Provider the episode belongs to.
        """
        text, cues = await self.client.send_command(
            "music/podcasts/podcast_episode_transcript",
            item_id=item_id,
            provider_instance_id_or_domain=provider_instance_id_or_domain,
            require_schema=101,
        )
        return PodcastEpisodeTranscript(
            text=text,
            cues=[MediaItemTranscriptCue.from_dict(cue) for cue in cues]
            if cues is not None
            else None,
        )

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
                    (
                        VERSIONS_BROWSE_LISTING_SCHEMA_VERSION,
                        sort_field,
                        sort_direction,
                        search,
                        limit,
                        offset,
                    ),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
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

    async def get_podcast_by_external_id(
        self, external_id: str, external_id_type: ExternalID | None = None
    ) -> Podcast | None:
        """Get a podcast by external ID, querying the library then the active providers."""
        if result := await self.client.send_command(
            "music/podcasts/get_by_external_id",
            external_id=external_id,
            external_id_type=external_id_type,
            require_schema=101,
        ):
            return Podcast.from_dict(result)
        return None

    async def get_podcast_collection(
        self,
        item_id: str,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        favorite: bool | None = None,
        *,
        user: str | LinkedUser | None = None,
    ) -> MediaCollection[Podcast]:
        """
        Get a podcast collection and optionally search or page its items.

        :param item_id: The collection ID.
        :param search: Only include items whose name contains this text.
        :param limit: Maximum number of items to return; omitted or 0 returns them all.
        :param offset: Number of items to skip.
        :param favorite: Only include the items the current user likes (True) or dislikes.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return MediaCollection[Podcast].from_dict(
            await self.client.send_command(
                "music/podcasts/get_collection",
                item_id=item_id,
                search=search,
                limit=limit,
                offset=offset,
                favorite=favorite,
                require_schema=101,
                **impersonation_arg(self.client.server_info, user),
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

    async def get_radio_by_external_id(
        self, external_id: str, external_id_type: ExternalID | None = None
    ) -> Radio | None:
        """Get a radio by external ID, querying the library then the active providers."""
        if result := await self.client.send_command(
            "music/radios/get_by_external_id",
            external_id=external_id,
            external_id_type=external_id_type,
            require_schema=101,
        ):
            return Radio.from_dict(result)
        return None

    async def get_radio_collection(
        self,
        item_id: str,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        favorite: bool | None = None,
        *,
        user: str | LinkedUser | None = None,
    ) -> MediaCollection[Radio]:
        """
        Get a radio collection and optionally search or page its items.

        :param item_id: The collection ID.
        :param search: Only include items whose name contains this text.
        :param limit: Maximum number of items to return; omitted or 0 returns them all.
        :param offset: Number of items to skip.
        :param favorite: Only include the items the current user likes (True) or dislikes.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return MediaCollection[Radio].from_dict(
            await self.client.send_command(
                "music/radios/get_collection",
                item_id=item_id,
                search=search,
                limit=limit,
                offset=offset,
                favorite=favorite,
                require_schema=101,
                **impersonation_arg(self.client.server_info, user),
            )
        )

    async def radio_tracks(self, item_id: str, provider_instance_id_or_domain: str) -> list[Track]:
        """Return the preview/listing for a tracklisted radio station, dynamic or finite."""
        return [
            Track.from_dict(item)
            for item in await self.client.send_command(
                "music/radios/radio_tracks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                require_schema=101,
            )
        ]

    async def export_radios(self) -> str:
        """Export all library radio stations to M3U8 format."""
        return cast(
            "str",
            await self.client.send_command("music/radios/export_radios", require_schema=101),
        )

    async def import_radios(self, m3u_data: str) -> BackgroundTask:
        """Queue importing radio stations from M3U8 format."""
        return BackgroundTask.from_dict(
            await self.client.send_command(
                "music/radios/import_radios",
                m3u_data=m3u_data,
                require_schema=101,
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
                    (ARTIST_LISTING_SCHEMA_VERSION, sort_field, sort_direction, search, offset),
                    (RANDOM_SEED_SCHEMA_VERSION, random_seed),
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

    async def get_track_by_external_id(
        self, external_id: str, external_id_type: ExternalID | None = None
    ) -> Track | None:
        """Get a track by external ID, querying the library then the active providers."""
        if result := await self.client.send_command(
            "music/tracks/get_by_external_id",
            external_id=external_id,
            external_id_type=external_id_type,
            require_schema=101,
        ):
            return Track.from_dict(result)
        return None

    async def get_track_collection(
        self,
        item_id: str,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        favorite: bool | None = None,
        *,
        user: str | LinkedUser | None = None,
    ) -> MediaCollection[Track]:
        """
        Get a track collection and optionally search or page its items.

        :param item_id: The collection ID.
        :param search: Only include items whose name contains this text.
        :param limit: Maximum number of items to return; omitted or 0 returns them all.
        :param offset: Number of items to skip.
        :param favorite: Only include the items the current user likes (True) or dislikes.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return MediaCollection[Track].from_dict(
            await self.client.send_command(
                "music/tracks/get_collection",
                item_id=item_id,
                search=search,
                limit=limit,
                offset=offset,
                favorite=favorite,
                require_schema=101,
                **impersonation_arg(self.client.server_info, user),
            )
        )
