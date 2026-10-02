"""Handle Music/library related endpoints for Music Assistant."""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING, Any, Literal, cast, overload

from music_assistant_models.background_task import BackgroundTask
from music_assistant_models.enums import (
    AlbumType,
    ArtistType,
    ImageType,
    MediaType,
    PlaylistMatchPolicy,
)
from music_assistant_models.helpers import create_sort_name
from music_assistant_models.media_items import (
    Album,
    Artist,
    Audiobook,
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
    Radio,
    RecommendationFolder,
    SearchResults,
    SoundEffect,
    Track,
    media_from_dict,
)

from .helpers import LinkedUser, impersonation_arg

if TYPE_CHECKING:
    from music_assistant_models.enums import ExternalID, ProviderSharing
    from music_assistant_models.media_items import ProviderMapping
    from music_assistant_models.queue_item import QueueItem

    from .client import MusicAssistantClient


class Music:
    """Music(library) related endpoints/data for Music Assistant."""

    def __init__(self, client: MusicAssistantClient) -> None:
        """Handle Initialization."""
        self.client = client

    #  Tracks related endpoints/commands

    async def get_library_tracks(  # noqa: PLR0913, PLR0917
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        provider: str | list[str] | None = None,
        user: str | None = None,
        genre: int | list[int] | None = None,
        played_only: bool | None = None,
        explicit: bool | None = None,
        summary: bool | None = None,
        reachable_via: list[str] | None = None,
    ) -> list[Track]:
        """Get Track listing from the server.

        :param favorite: Filter by favorite status.
        :param search: Filter by search query.
        :param limit: Maximum number of items to return.
        :param offset: Number of items to skip.
        :param order_by: Order by field (e.g. 'sort_name', 'timestamp_added').
        :param provider: Filter by provider instance ID or domain (single string or list).
        :param user: Optionally execute the request on behalf of this user (user_id or
            username). Requires the authenticated client to have sufficient permissions.
        :param genre: Filter by genre id(s).
        :param played_only: Only include items that have been played.
        :param explicit: Filter by explicit content (True=only explicit, False=no explicit).
        :param summary: Return slim summary items (server default), False for full items.
        :param reachable_via: Only include items reachable through these provider instances.
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
                provider=provider,
                user=user,
                genre=genre,
                played_only=played_only,
                explicit=explicit,
                summary=summary,
                reachable_via=reachable_via,
                require_schema=35 if user else None,
            )
        ]

    async def get_track(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        album_uri: str | None = None,
        allow_update_metadata: bool | None = None,
        recursive: bool | None = None,
    ) -> Track:
        """Get single Track from the server."""
        return Track.from_dict(
            await self.client.send_command(
                "music/tracks/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                album_uri=album_uri,
                allow_update_metadata=allow_update_metadata,
                recursive=recursive,
            ),
        )

    async def get_track_versions(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> list[Track]:
        """Get all other versions for given Track from the server."""
        return [
            Track.from_dict(item)
            for item in await self.client.send_command(
                "music/tracks/track_versions",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
            )
        ]

    async def get_track_albums(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        in_library_only: bool = False,
    ) -> list[Album]:
        """Get all (known) albums this track is featured on."""
        return [
            Album.from_dict(item)
            for item in await self.client.send_command(
                "music/tracks/track_albums",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                in_library_only=in_library_only,
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

    async def get_library_albums(  # noqa: PLR0913, PLR0917
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        album_types: list[AlbumType] | None = None,
        provider: str | list[str] | None = None,
        user: str | None = None,
        genre: int | list[int] | None = None,
        played_only: bool | None = None,
        summary: bool | None = None,
        reachable_via: list[str] | None = None,
    ) -> list[Album]:
        """Get Albums listing from the server.

        :param favorite: Filter by favorite status.
        :param search: Filter by search query.
        :param limit: Maximum number of items to return.
        :param offset: Number of items to skip.
        :param order_by: Order by field (e.g. 'sort_name', 'timestamp_added').
        :param album_types: Filter by album types.
        :param provider: Filter by provider instance ID or domain (single string or list).
        :param user: Optionally execute the request on behalf of this user (user_id or
            username). Requires the authenticated client to have sufficient permissions.
        :param genre: Filter by genre id(s).
        :param played_only: Only include items that have been played.
        :param summary: Return slim summary items (server default), False for full items.
        :param reachable_via: Only include items reachable through these provider instances.
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
                album_types=album_types,
                provider=provider,
                user=user,
                genre=genre,
                played_only=played_only,
                summary=summary,
                reachable_via=reachable_via,
                require_schema=35 if user else None,
            )
        ]

    async def get_album(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        allow_update_metadata: bool | None = None,
        recursive: bool | None = None,
    ) -> Album:
        """Get single Album from the server."""
        return Album.from_dict(
            await self.client.send_command(
                "music/albums/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                allow_update_metadata=allow_update_metadata,
                recursive=recursive,
            ),
        )

    async def get_album_tracks(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        in_library_only: bool = False,
    ) -> list[Track]:
        """Get tracks for given album."""
        return [
            Track.from_dict(item)
            for item in await self.client.send_command(
                "music/albums/album_tracks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                in_library_only=in_library_only,
            )
        ]

    async def get_album_versions(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> list[Album]:
        """Get all other versions for given Album from the server."""
        return [
            Album.from_dict(item)
            for item in await self.client.send_command(
                "music/albums/album_versions",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
            )
        ]

    #  Artist related endpoints/commands

    async def get_library_artists(  # noqa: PLR0913, PLR0917
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        album_artists_only: bool = False,
        provider: str | list[str] | None = None,
        user: str | None = None,
        genre: int | list[int] | None = None,
        played_only: bool | None = None,
        artist_type: ArtistType | None = None,
        summary: bool | None = None,
        reachable_via: list[str] | None = None,
    ) -> list[Artist]:
        """Get Artists listing from the server.

        :param favorite: Filter by favorite status.
        :param search: Filter by search query.
        :param limit: Maximum number of items to return.
        :param offset: Number of items to skip.
        :param order_by: Order by field (e.g. 'sort_name', 'timestamp_added').
        :param album_artists_only: Only return artists that have albums.
        :param provider: Filter by provider instance ID or domain (single string or list).
        :param user: Optionally execute the request on behalf of this user (user_id or
            username). Requires the authenticated client to have sufficient permissions.
        :param genre: Filter by genre id(s).
        :param played_only: Only include items that have been played.
        :param summary: Return slim summary items (server default), False for full items.
        :param reachable_via: Only include items reachable through these provider instances.
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
                album_artists_only=album_artists_only,
                provider=provider,
                user=user,
                genre=genre,
                played_only=played_only,
                artist_type=artist_type,
                summary=summary,
                reachable_via=reachable_via,
                require_schema=35 if user else None,
            )
        ]

    async def get_artist(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        allow_update_metadata: bool | None = None,
    ) -> Artist:
        """Get single Artist from the server."""
        return Artist.from_dict(
            await self.client.send_command(
                "music/artists/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                allow_update_metadata=allow_update_metadata,
            ),
        )

    async def get_artist_tracks(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        provider_filter: str | None = None,
    ) -> list[Track]:
        """
        Get tracks for given artist.

        :param provider_filter: Optional provider instance ID to limit the (library) result to.
        """
        return [
            Track.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/artist_tracks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                provider_filter=provider_filter,
            )
        ]

    async def get_artist_albums(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        provider_filter: str | None = None,
    ) -> list[Album]:
        """
        Get albums for given artist.

        :param provider_filter: Optional provider instance ID to limit the (library) result to.
        """
        return [
            Album.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/artist_albums",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                provider_filter=provider_filter,
            )
        ]

    async def get_artist_top_tracks(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        provider_filter: str | None = None,
    ) -> list[Track]:
        """Return the top/featured tracks for an artist."""
        return [
            Track.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/top_tracks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                provider_filter=provider_filter,
                require_schema=84,
            )
        ]

    async def get_artist_top_albums(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        provider_filter: str | None = None,
    ) -> list[Album]:
        """Return the top/featured albums for an artist."""
        return [
            Album.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/top_albums",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                provider_filter=provider_filter,
                require_schema=84,
            )
        ]

    async def get_artist_appears_on(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        provider_filter: str | None = None,
    ) -> list[Album]:
        """Return the albums an artist appears on without being an album artist."""
        return [
            Album.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/artist_appears_on",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                provider_filter=provider_filter,
                require_schema=84,
            )
        ]

    @overload
    async def get_artist_audiobooks(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        artist_type: ArtistType = ...,
        in_library_only: bool = ...,
        *,
        collapse_collections: Literal[False] = False,
    ) -> list[Audiobook]: ...

    @overload
    async def get_artist_audiobooks(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        artist_type: ArtistType = ...,
        in_library_only: bool = ...,
        *,
        collapse_collections: bool,
    ) -> list[Audiobook] | list[Audiobook | MediaCollection[Audiobook]]: ...

    async def get_artist_audiobooks(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        artist_type: ArtistType = ArtistType.AUTHOR,
        in_library_only: bool = False,
        *,
        collapse_collections: bool = False,
    ) -> list[Audiobook] | list[Audiobook | MediaCollection[Audiobook]]:
        """
        Return audiobooks for an artist (artist_type can be omitted for library artists).

        :param collapse_collections: Return collections instead of their individual items.
            Only applies to in-library items.
        """
        items: list[Audiobook | MediaCollection[Audiobook]] = [
            MediaCollection.from_dict(item)
            if item["media_type"] == MediaType.COLLECTION
            else Audiobook.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/artist_audiobooks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                artist_type=artist_type,
                in_library_only=in_library_only,
                collapse_collections=collapse_collections,
                require_schema=84,
            )
        ]
        return items

    async def get_artist_discography(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> list[Album]:
        """Return the discography of a library artist as MusicBrainz knows it, newest first."""
        return [
            Album.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/discography",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                require_schema=84,
            )
        ]

    async def similar_artists(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        provider_filter: str | None = None,
        limit: int = 25,
    ) -> list[Artist]:
        """Return similar artists for an artist."""
        return [
            Artist.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/similar_artists",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                provider_filter=provider_filter,
                limit=limit,
                require_schema=84,
            )
        ]

    async def get_library_artist_types(self) -> list[ArtistType]:
        """Get all supported in-library artist types."""
        return [
            ArtistType(item)
            for item in await self.client.send_command(
                "music/artists/library_artist_types",
                require_schema=84,
            )
        ]

    #  Playlist related endpoints/commands

    async def get_library_playlists(  # noqa: PLR0913, PLR0917
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        provider: str | list[str] | None = None,
        user: str | None = None,
        genre: int | list[int] | None = None,
        played_only: bool | None = None,
        summary: bool | None = None,
        reachable_via: list[str] | None = None,
    ) -> list[Playlist]:
        """Get Playlists listing from the server.

        :param favorite: Filter by favorite status.
        :param search: Filter by search query.
        :param limit: Maximum number of items to return.
        :param offset: Number of items to skip.
        :param order_by: Order by field (e.g. 'sort_name', 'timestamp_added').
        :param provider: Filter by provider instance ID or domain (single string or list).
        :param user: Optionally execute the request on behalf of this user (user_id or
            username). Requires the authenticated client to have sufficient permissions.
        :param genre: Filter by genre id(s).
        :param played_only: Only include items that have been played.
        :param summary: Return slim summary items (server default), False for full items.
        :param reachable_via: Only include items reachable through these provider instances.
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
                provider=provider,
                user=user,
                genre=genre,
                played_only=played_only,
                summary=summary,
                reachable_via=reachable_via,
                require_schema=35 if user else None,
            )
        ]

    async def get_playlist(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        allow_update_metadata: bool | None = None,
    ) -> Playlist:
        """Get single Playlist from the server."""
        return Playlist.from_dict(
            await self.client.send_command(
                "music/playlists/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                allow_update_metadata=allow_update_metadata,
            ),
        )

    async def get_playlist_tracks(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        force_refresh: bool = False,
        allow_dynamic_tracks: bool | None = None,
        strict_provider_instance: bool | None = None,
    ) -> list[Track | Radio | PodcastEpisode | Audiobook | SoundEffect]:
        """
        Get all items for given playlist.

        :param force_refresh: Force a refresh of the (cached) playlist tracks.
        :param allow_dynamic_tracks: Request a fresh sample from dynamic playlists.
        :param strict_provider_instance: Do not fall back to another provider instance.
        """
        return [
            cast("Track | Radio | PodcastEpisode | Audiobook | SoundEffect", media_from_dict(obj))
            for obj in await self.client.send_command(
                "music/playlists/playlist_tracks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                force_refresh=force_refresh,
                allow_dynamic_tracks=allow_dynamic_tracks,
                strict_provider_instance=strict_provider_instance,
            )
        ]

    async def add_playlist_tracks(
        self, db_playlist_id: str | int, uris: list[str]
    ) -> BackgroundTask | None:
        """Add multiple tracks to playlist. Creates background tasks to process the action."""
        result = await self.client.send_command(
            "music/playlists/add_playlist_tracks",
            db_playlist_id=db_playlist_id,
            uris=uris,
        )
        return BackgroundTask.from_dict(result) if result else None

    async def remove_playlist_tracks(
        self, db_playlist_id: str | int, positions_to_remove: tuple[int, ...]
    ) -> BackgroundTask | None:
        """Remove multiple tracks from playlist."""
        result = await self.client.send_command(
            "music/playlists/remove_playlist_tracks",
            db_playlist_id=db_playlist_id,
            positions_to_remove=positions_to_remove,
        )
        return BackgroundTask.from_dict(result) if result else None

    async def create_playlist(
        self,
        name: str,
        provider_instance_or_domain: str | None = None,
        media_types: list[MediaType] | None = None,
        strict_provider_instance: bool | None = None,
    ) -> Playlist:
        """
        Create new playlist.

        :param media_types: Media types the playlist must support.
        :param strict_provider_instance: Do not fall back to another provider instance.
        """
        return Playlist.from_dict(
            await self.client.send_command(
                "music/playlists/create_playlist",
                name=name,
                provider_instance_or_domain=provider_instance_or_domain,
                media_types=media_types,
                strict_provider_instance=strict_provider_instance,
            )
        )

    async def export_playlist(self, db_playlist_id: str | int) -> str:
        """Export a playlist to M3U8 format."""
        return cast(
            "str",
            await self.client.send_command(
                "music/playlists/export_playlist",
                db_playlist_id=db_playlist_id,
                require_schema=84,
            ),
        )

    async def import_playlist(
        self,
        m3u_data: str,
        match_providers: list[str] | None = None,
        match_policy: PlaylistMatchPolicy | None = None,
    ) -> Playlist:
        """
        Import a playlist from M3U8 format.

        :param match_providers: Provider instances or domains to search when matching runs.
        :param match_policy: Minimum substitute confidence. Leave unset to skip matching.
        """
        return Playlist.from_dict(
            await self.client.send_command(
                "music/playlists/import_playlist",
                m3u_data=m3u_data,
                match_providers=match_providers,
                match_policy=match_policy,
                require_schema=84,
            )
        )

    async def migrate_playlist(
        self,
        db_playlist_id: str | int,
        destination_provider: str = "builtin",
        name: str | None = None,
        match_policy: PlaylistMatchPolicy = PlaylistMatchPolicy.SAME_RECORDING,
    ) -> BackgroundTask:
        """Queue copying a playlist to another provider or Music Assistant."""
        return BackgroundTask.from_dict(
            await self.client.send_command(
                "music/playlists/migrate_playlist",
                db_playlist_id=db_playlist_id,
                destination_provider=destination_provider,
                name=name,
                match_policy=match_policy,
                require_schema=84,
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

        :param owner: User id of the member owning the playlist, None for the whole home.
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
                require_schema=84,
            )
        )

    # Audiobooks related endpoints/commands

    @overload
    async def get_library_audiobooks(
        self,
        favorite: bool | None = ...,
        search: str | None = ...,
        limit: int | None = ...,
        offset: int | None = ...,
        order_by: str | None = ...,
        provider: str | list[str] | None = ...,
        user: str | None = ...,
        genre: int | list[int] | None = ...,
        played_only: bool | None = ...,
        summary: bool | None = ...,
        reachable_via: list[str] | None = ...,
        *,
        collapse_collections: Literal[False] = False,
    ) -> list[Audiobook]: ...

    @overload
    async def get_library_audiobooks(
        self,
        favorite: bool | None = ...,
        search: str | None = ...,
        limit: int | None = ...,
        offset: int | None = ...,
        order_by: str | None = ...,
        provider: str | list[str] | None = ...,
        user: str | None = ...,
        genre: int | list[int] | None = ...,
        played_only: bool | None = ...,
        summary: bool | None = ...,
        reachable_via: list[str] | None = ...,
        *,
        collapse_collections: bool,
    ) -> list[Audiobook] | list[Audiobook | MediaCollection[Audiobook]]: ...

    async def get_library_audiobooks(  # noqa: PLR0913, PLR0917
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        provider: str | list[str] | None = None,
        user: str | None = None,
        genre: int | list[int] | None = None,
        played_only: bool | None = None,
        summary: bool | None = None,
        reachable_via: list[str] | None = None,
        *,
        collapse_collections: bool = False,
    ) -> list[Audiobook] | list[Audiobook | MediaCollection[Audiobook]]:
        """Get Audiobooks listing from the server.

        :param favorite: Filter by favorite status.
        :param search: Filter by search query.
        :param limit: Maximum number of items to return.
        :param offset: Number of items to skip.
        :param order_by: Order by field (e.g. 'sort_name', 'timestamp_added').
        :param provider: Filter by provider instance ID or domain (single string or list).
        :param user: Optionally execute the request on behalf of this user (user_id or
            username). Requires the authenticated client to have sufficient permissions.
        :param genre: Filter by genre id(s).
        :param played_only: Only include items that have been played.
        :param summary: Return slim summary items (server default), False for full items.
        :param reachable_via: Only include items reachable through these provider instances.
        :param collapse_collections: Return collections instead of their individual items.
        """
        items: list[Audiobook | MediaCollection[Audiobook]] = [
            MediaCollection.from_dict(obj)
            if obj["media_type"] == MediaType.COLLECTION
            else Audiobook.from_dict(obj)
            for obj in await self.client.send_command(
                "music/audiobooks/library_items",
                favorite=favorite,
                search=search,
                limit=limit,
                offset=offset,
                order_by=order_by,
                provider=provider,
                user=user,
                genre=genre,
                played_only=played_only,
                summary=summary,
                reachable_via=reachable_via,
                collapse_collections=collapse_collections,
                require_schema=40 if collapse_collections else (35 if user else None),
            )
        ]
        return items

    async def get_audiobook(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        allow_update_metadata: bool | None = None,
    ) -> Audiobook:
        """Get single Audiobook from the server."""
        return Audiobook.from_dict(
            await self.client.send_command(
                "music/audiobooks/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                allow_update_metadata=allow_update_metadata,
            ),
        )

    # Podcasts related endpoints/commands

    async def get_library_podcasts(  # noqa: PLR0913, PLR0917
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        provider: str | list[str] | None = None,
        user: str | None = None,
        genre: int | list[int] | None = None,
        played_only: bool | None = None,
        summary: bool | None = None,
        reachable_via: list[str] | None = None,
    ) -> list[Podcast]:
        """Get Podcasts listing from the server.

        :param favorite: Filter by favorite status.
        :param search: Filter by search query.
        :param limit: Maximum number of items to return.
        :param offset: Number of items to skip.
        :param order_by: Order by field (e.g. 'sort_name', 'timestamp_added').
        :param provider: Filter by provider instance ID or domain (single string or list).
        :param user: Optionally execute the request on behalf of this user (user_id or
            username). Requires the authenticated client to have sufficient permissions.
        :param genre: Filter by genre id(s).
        :param played_only: Only include items that have been played.
        :param summary: Return slim summary items (server default), False for full items.
        :param reachable_via: Only include items reachable through these provider instances.
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
                provider=provider,
                user=user,
                genre=genre,
                played_only=played_only,
                summary=summary,
                reachable_via=reachable_via,
                require_schema=35 if user else None,
            )
        ]

    async def get_podcast(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        allow_update_metadata: bool | None = None,
    ) -> Podcast:
        """Get single Podcast from the server."""
        return Podcast.from_dict(
            await self.client.send_command(
                "music/podcasts/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                allow_update_metadata=allow_update_metadata,
            ),
        )

    async def get_podcast_episodes(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> list[PodcastEpisode]:
        """Get episodes for given podcast."""
        return [
            PodcastEpisode.from_dict(obj)
            for obj in await self.client.send_command(
                "music/podcasts/podcast_episodes",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
            )
        ]

    async def podcast_episode_transcript(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> tuple[str | None, list[MediaItemTranscriptCue] | None]:
        """Return a podcast episode's transcript as (readable text, timed cues)."""
        text, cues = await self.client.send_command(
            "music/podcasts/podcast_episode_transcript",
            item_id=item_id,
            provider_instance_id_or_domain=provider_instance_id_or_domain,
            require_schema=84,
        )
        if cues is None:
            return text, None
        return text, [MediaItemTranscriptCue.from_dict(cue) for cue in cues]

    #  Radio related endpoints/commands

    async def get_library_radios(  # noqa: PLR0913, PLR0917
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        provider: str | list[str] | None = None,
        user: str | None = None,
        genre: int | list[int] | None = None,
        played_only: bool | None = None,
        summary: bool | None = None,
        reachable_via: list[str] | None = None,
    ) -> list[Radio]:
        """Get Radio listing from the server.

        :param favorite: Filter by favorite status.
        :param search: Filter by search query.
        :param limit: Maximum number of items to return.
        :param offset: Number of items to skip.
        :param order_by: Order by field (e.g. 'sort_name', 'timestamp_added').
        :param provider: Filter by provider instance ID or domain (single string or list).
        :param user: Optionally execute the request on behalf of this user (user_id or
            username). Requires the authenticated client to have sufficient permissions.
        :param genre: Filter by genre id(s).
        :param played_only: Only include items that have been played.
        :param summary: Return slim summary items (server default), False for full items.
        :param reachable_via: Only include items reachable through these provider instances.
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
                provider=provider,
                user=user,
                genre=genre,
                played_only=played_only,
                summary=summary,
                reachable_via=reachable_via,
                require_schema=35 if user else None,
            )
        ]

    async def get_radio(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        allow_update_metadata: bool | None = None,
    ) -> Radio:
        """Get single Radio from the server."""
        return Radio.from_dict(
            await self.client.send_command(
                "music/radios/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                allow_update_metadata=allow_update_metadata,
            ),
        )

    async def get_radio_versions(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> list[Radio]:
        """Get all other versions for given Radio from the server."""
        return [
            Radio.from_dict(item)
            for item in await self.client.send_command(
                "music/radios/radio_versions",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
            )
        ]

    async def get_radio_tracks(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> list[Track]:
        """Return a fresh batch of tracks for a dynamic radio station."""
        return [
            Track.from_dict(item)
            for item in await self.client.send_command(
                "music/radios/radio_tracks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                require_schema=84,
            )
        ]

    async def export_radios(self) -> str:
        """Export all library radio stations to M3U8 format."""
        return cast(
            "str",
            await self.client.send_command("music/radios/export_radios", require_schema=84),
        )

    async def import_radios(self, m3u_data: str) -> BackgroundTask:
        """Queue importing radio stations from M3U8 format."""
        return BackgroundTask.from_dict(
            await self.client.send_command(
                "music/radios/import_radios",
                m3u_data=m3u_data,
                require_schema=84,
            )
        )

    # Other/generic endpoints/commands

    async def start_sync(
        self,
        media_types: list[MediaType] | None = None,
        providers: list[str] | None = None,
    ) -> list[BackgroundTask]:
        """Start running the sync of (all or selected) musicproviders.

        media_types: only sync these media types. None for all.
        providers: only sync these provider instances. None for all.
        """
        result = await self.client.send_command(
            "music/sync", media_types=media_types, providers=providers
        )
        return [BackgroundTask.from_dict(task) for task in result or []]

    async def search(
        self,
        search_query: str,
        media_types: list[MediaType] = MediaType.ALL,
        limit: int = 50,
        library_only: bool = False,
        user: str | LinkedUser | None = None,
        providers: list[str] | None = None,
    ) -> SearchResults:
        """Perform global search for media items on all providers.

        :param search_query: Search query.
        :param media_types: A list of media_types to include.
        :param limit: number of items to return in the search (per type).
        :param library_only: Deprecated - use providers=["library"] instead.
        :param user: Optionally execute the search on behalf of this user: a user_id or
            username string, or a LinkedUser reference by auth provider.
            Requires the authenticated client to have sufficient permissions.
        :param providers: Optionally restrict the search to the given providers (by instance
            id or domain), where the special value "library" selects the library.
        """
        return SearchResults.from_dict(
            await self.client.send_command(
                "music/search",
                search_query=search_query,
                media_types=media_types,
                limit=limit,
                library_only=library_only,
                providers=providers,
                **impersonation_arg(self.client.server_info, user),
            ),
        )

    async def browse(
        self,
        path: str | None = None,
        player_id: str | None = None,
    ) -> list[MediaItemType | ItemMapping]:
        """
        Browse Music providers.

        :param player_id: Scope audio-source listings to the sources bound to this player.
        """
        return [
            media_from_dict(obj)
            for obj in await self.client.send_command(
                "music/browse", path=path, player_id=player_id
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
        :param providers: Only include items reachable through these provider instances.
        :param always_include_media_types: Media types to include regardless of
            user_initiated_only (e.g. podcasts/audiobooks).
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
            )
        ]

    async def recently_added_tracks(self, limit: int = 10) -> list[Track]:
        """Return a list of the last added tracks."""
        return [
            Track.from_dict(item)
            for item in await self.client.send_command(
                "music/recently_added_tracks",
                limit=limit,
                require_schema=84,
            )
        ]

    async def in_progress_items(
        self, limit: int = 10, all_users: bool = False, providers: list[str] | None = None
    ) -> list[ItemMapping]:
        """
        Return a list of the Audiobooks and PodcastEpisodes that are in progress.

        :param providers: Only include items reachable through these provider instances.
        """
        return [
            ItemMapping.from_dict(item)
            for item in await self.client.send_command(
                "music/in_progress_items",
                limit=limit,
                all_users=all_users,
                providers=providers,
            )
        ]

    async def recommendations(self) -> list[RecommendationFolder]:
        """Get all recommendations."""
        return [
            RecommendationFolder.from_dict(item)
            for item in await self.client.send_command("music/recommendations")
        ]

    async def recommendation_items(
        self, provider: str, item_id: str, providers: list[str] | None = None
    ) -> list[MediaItemType | ItemMapping]:
        """
        Get the items for a single recommendation row.

        :param provider: The provider instance id owning the row.
        :param item_id: The item_id of the row, as returned by the recommendations listing.
        :param providers: Only include items reachable through these provider instances.
        """
        return [
            media_from_dict(item)
            for item in await self.client.send_command(
                "music/recommendations/items",
                provider=provider,
                item_id=item_id,
                providers=providers,
                require_schema=84,
            )
        ]

    async def sound_effects(self) -> list[SoundEffect]:
        """Return all sound effect items from providers supporting them."""
        return [
            SoundEffect.from_dict(item)
            for item in await self.client.send_command("music/sound_effects", require_schema=84)
        ]

    async def get_item_by_uri(
        self,
        uri: str,
        allow_update_metadata: bool | None = None,
    ) -> MediaItemType | ItemMapping:
        """Get single music item providing a mediaitem uri."""
        return media_from_dict(
            await self.client.send_command(
                "music/item_by_uri", uri=uri, allow_update_metadata=allow_update_metadata
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
        allow_update_metadata: bool | None = None,
    ) -> MediaItemType | ItemMapping:
        """Get single music item by id and media type."""
        return media_from_dict(
            await self.client.send_command(
                "music/item",
                media_type=media_type,
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                allow_update_metadata=allow_update_metadata,
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
        item: str | MediaItemType | ItemMapping,
    ) -> None:
        """Add an item to the favorites."""
        await self.client.send_command("music/favorites/add_item", item=item)

    async def set_item_favorite(
        self,
        item: str | MediaItemType | ItemMapping,
        favorite: bool | None,
    ) -> None:
        """
        Set the calling user's like, dislike or unset on a media item.

        :param favorite: True to like, False to dislike, None to clear the state.
        """
        await self.client.send_command(
            "music/favorites/set_item",
            item=item,
            favorite=favorite,
            require_schema=84,
        )

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
        self, item: str | MediaItemType | ItemMapping, overwrite_existing: bool = False
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
        media_item: str | MediaItemType,
    ) -> MediaItemType | ItemMapping | None:
        """Try to refresh a mediaitem by requesting it's full object or search for substitutes."""
        if result := await self.client.send_command("music/refresh_item", media_item=media_item):
            return media_from_dict(result)
        return None

    async def mark_item_played(
        self,
        media_item: MediaItemType | ItemMapping,
        fully_played: bool = True,
        userid: str | None = None,
        seconds_played: int | None = None,
        is_playing: bool | None = None,
        queue_id: str | None = None,
        user_initiated: bool | None = None,
        skip_artist_ids: list[str] | None = None,
        playback_speed: float | None = None,
        provider_instance_id: str | None = None,
    ) -> None:
        """
        Mark item as played in playlog.

        :param media_item: The media item to mark as played.
        :param fully_played: If True, mark the item as fully played.
        :param userid: Optionally attribute this play to a specific user (instead of the user
            the client is authenticated as). Requires the authenticated client to have
            sufficient permissions.
        :param seconds_played: The number of seconds played.
        :param is_playing: If True, the item is currently playing.
        :param queue_id: The queue ID where the item was played.
        :param user_initiated: If True (server default), the playback was initiated by the
            user. Pass False when reporting playback not initiated by the caller itself.
        :param skip_artist_ids: Library artist ids to skip when crediting an album's artists.
        :param playback_speed: The current playback speed to persist (audiobooks/podcasts).
        :param provider_instance_id: The provider instance reporting the play.
        """
        await self.client.send_command(
            "music/mark_played",
            media_item=media_item,
            fully_played=fully_played,
            userid=userid,
            seconds_played=seconds_played,
            is_playing=is_playing,
            queue_id=queue_id,
            user_initiated=user_initiated,
            skip_artist_ids=skip_artist_ids,
            playback_speed=playback_speed,
            provider_instance_id=provider_instance_id,
        )

    async def mark_item_unplayed(
        self,
        media_item: MediaItemType | ItemMapping,
        userid: str | None = None,
        provider_instance_id: str | None = None,
    ) -> None:
        """
        Mark item as unplayed in playlog.

        :param media_item: The media item to mark as unplayed.
        :param userid: Optionally apply this to a specific user (instead of the user the
            client is authenticated as). Requires the authenticated client to have sufficient
            permissions.
        :param provider_instance_id: The provider instance reporting the change.
        """
        await self.client.send_command(
            "music/mark_unplayed",
            media_item=media_item,
            userid=userid,
            provider_instance_id=provider_instance_id,
        )

    async def add_provider_mapping(
        self, media_type: MediaType, db_id: str, mapping: ProviderMapping
    ) -> None:
        """Add provider mapping to the given library item."""
        await self.client.send_command(
            "music/add_provider_mapping",
            media_type=media_type,
            db_id=db_id,
            mapping=mapping,
            require_schema=84,
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
            require_schema=84,
        )

    async def match_providers(self, media_type: MediaType, db_id: str) -> None:
        """Search for mappings on all providers for the given library item."""
        await self.client.send_command(
            "music/match_providers",
            media_type=media_type,
            db_id=db_id,
            require_schema=84,
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
            result = await self.client.send_command(
                "music/track_by_name",
                track_name=track_name,
                artist_name=artist_name,
                album_name=album_name,
                track_version=track_version,
            )
            return Track.from_dict(result) if result else None

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
        artist_type: ArtistType | None = None,
    ) -> int:
        """Return the total number of items in the library."""
        return cast(
            "int",
            await self.client.send_command(
                "music/artists/count",
                favorite_only=favorite_only,
                album_artists_only=album_artists_only,
                artist_type=artist_type,
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
    ) -> list[Audiobook]:
        """Return all versions of an audiobook we can find on all providers."""
        return [
            Audiobook.from_dict(obj)
            for obj in await self.client.send_command(
                "music/audiobooks/audiobook_versions",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
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
    ) -> PodcastEpisode:
        """Return single podcast episode by the given provider podcast id."""
        return PodcastEpisode.from_dict(
            await self.client.send_command(
                "music/podcasts/podcast_episode",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
            )
        )

    async def podcast_versions(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
    ) -> list[Podcast]:
        """Return all versions of an podcast we can find on all providers."""
        return [
            Podcast.from_dict(obj)
            for obj in await self.client.send_command(
                "music/podcasts/podcast_versions",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
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
        preferred_provider_instances: list[str] | None = None,
    ) -> list[Track]:
        """
        Get a list of similar tracks for the given track.

        :param preferred_provider_instances: Provider instance IDs to try first.
        """
        return [
            Track.from_dict(obj)
            for obj in await self.client.send_command(
                "music/tracks/similar_tracks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                limit=limit,
                allow_lookup=allow_lookup,
                preferred_provider_instances=preferred_provider_instances,
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

    # Genre related endpoints/commands

    async def get_library_genres(  # noqa: PLR0913, PLR0917
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        provider: str | list[str] | None = None,
        played_only: bool | None = None,
        hide_empty: bool | None = None,
        media_type: MediaType | None = None,
        content_type: str | None = None,
        summary: bool | None = None,
    ) -> list[Genre]:
        """
        Get genres in the library.

        :param hide_empty: Only applies when media_type is not set. True: only genres with
            at least one media mapping, False: all genres, None: only default genres.
        :param media_type: Return all genres with at least one mapping for this media type.
        :param content_type: Restrict to one taxonomy: "music", "podcast" or "audiobook".
        :param summary: Return slim summary items (server default), False for full items.
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
                require_schema=84,
            )
        ]

    async def get_genre(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        allow_update_metadata: bool | None = None,
    ) -> Genre:
        """Get single Genre from the server."""
        return Genre.from_dict(
            await self.client.send_command(
                "music/genres/get",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                allow_update_metadata=allow_update_metadata,
                require_schema=84,
            ),
        )

    async def genre_count(self, favorite_only: bool | None = None) -> int:
        """Return the total number of genres in the library."""
        return cast(
            "int",
            await self.client.send_command(
                "music/genres/count",
                favorite_only=favorite_only,
                require_schema=84,
            ),
        )

    async def add_genre(self, item: Genre, overwrite_existing: bool = False) -> Genre:
        """Add genre to library and return the new (or updated) database item."""
        return Genre.from_dict(
            await self.client.send_command(
                "music/genres/add",
                item=item,
                overwrite_existing=overwrite_existing,
                require_schema=84,
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
                require_schema=84,
            )
        )

    async def remove_genre(self, item_id: str | int, exclude_globally: bool = True) -> None:
        """
        Delete genre record from the database.

        :param exclude_globally: Soft-delete the genre so the scanner will not recreate it.
        """
        await self.client.send_command(
            "music/genres/remove",
            item_id=item_id,
            exclude_globally=exclude_globally,
            require_schema=84,
        )

    async def get_genre_albums(
        self,
        item_id: str | int,
        limit: int = 500,
        offset: int = 0,
        order_by: str | None = None,
    ) -> list[Album]:
        """Return the albums mapped to a genre."""
        return [
            Album.from_dict(obj)
            for obj in await self.client.send_command(
                "music/genres/albums",
                item_id=item_id,
                limit=limit,
                offset=offset,
                order_by=order_by,
                require_schema=84,
            )
        ]

    async def get_genre_tracks(
        self,
        item_id: str | int,
        limit: int = 500,
        offset: int = 0,
        order_by: str | None = None,
    ) -> list[Track]:
        """Return the tracks mapped to a genre."""
        return [
            Track.from_dict(obj)
            for obj in await self.client.send_command(
                "music/genres/tracks",
                item_id=item_id,
                limit=limit,
                offset=offset,
                order_by=order_by,
                require_schema=84,
            )
        ]

    async def genre_overview(
        self,
        item_id: str,
        provider_instance_id_or_domain: str | None = None,
        limit: int = 25,
    ) -> list[RecommendationFolder]:
        """Return overview rows for a genre (all media types)."""
        return [
            RecommendationFolder.from_dict(obj)
            for obj in await self.client.send_command(
                "music/genres/overview",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                limit=limit,
                require_schema=84,
            )
        ]

    async def genre_media_counts(self, genre_ids: list[str]) -> dict[str, dict[str, int]]:
        """Return media item counts per media type for each requested genre."""
        return cast(
            "dict[str, dict[str, int]]",
            await self.client.send_command(
                "music/genres/media_counts",
                genre_ids=genre_ids,
                require_schema=84,
            ),
        )

    async def genres_for_media_item(
        self, media_type: MediaType, media_id: str | int
    ) -> list[Genre]:
        """Return all genres mapped to a given media item."""
        return [
            Genre.from_dict(obj)
            for obj in await self.client.send_command(
                "music/genres/genres_for_media_item",
                media_type=media_type,
                media_id=media_id,
                require_schema=84,
            )
        ]

    async def genre_exclusions_for_media_item(
        self, media_type: MediaType, media_id: str | int
    ) -> list[Genre]:
        """Return all genres excluded from a given media item."""
        return [
            Genre.from_dict(obj)
            for obj in await self.client.send_command(
                "music/genres/genre_exclusions_for_media_item",
                media_type=media_type,
                media_id=media_id,
                require_schema=84,
            )
        ]

    async def add_genre_alias(self, genre_id: str | int, alias: str) -> Genre:
        """Add an alias string to a genre."""
        return Genre.from_dict(
            await self.client.send_command(
                "music/genres/add_alias",
                genre_id=genre_id,
                alias=alias,
                require_schema=84,
            )
        )

    async def remove_genre_alias(self, genre_id: str | int, alias: str) -> Genre:
        """Remove an alias string from a genre."""
        return Genre.from_dict(
            await self.client.send_command(
                "music/genres/remove_alias",
                genre_id=genre_id,
                alias=alias,
                require_schema=84,
            )
        )

    async def promote_genre_alias(self, genre_id: str | int, alias: str) -> Genre:
        """Promote an alias to become a standalone genre."""
        return Genre.from_dict(
            await self.client.send_command(
                "music/genres/promote_alias",
                genre_id=genre_id,
                alias=alias,
                require_schema=84,
            )
        )

    async def add_genre_media_mapping(
        self,
        genre_id: str | int,
        media_type: MediaType,
        media_id: str | int,
        alias: str | None = None,
    ) -> None:
        """Map a media item to a genre."""
        await self.client.send_command(
            "music/genres/add_media_mapping",
            genre_id=genre_id,
            media_type=media_type,
            media_id=media_id,
            alias=alias,
            require_schema=84,
        )

    async def remove_genre_media_mapping(
        self, genre_id: str | int, media_type: MediaType, media_id: str | int
    ) -> None:
        """Remove a media item mapping from a genre."""
        await self.client.send_command(
            "music/genres/remove_media_mapping",
            genre_id=genre_id,
            media_type=media_type,
            media_id=media_id,
            require_schema=84,
        )

    async def exclude_genre_from_media_item(
        self, genre_id: str | int, media_type: MediaType, media_id: str | int
    ) -> None:
        """Permanently exclude a genre from being mapped to a media item."""
        await self.client.send_command(
            "music/genres/exclude_genre_from_media_item",
            genre_id=genre_id,
            media_type=media_type,
            media_id=media_id,
            require_schema=84,
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
            require_schema=84,
        )

    async def get_genre_global_exclusions(self) -> list[dict[str, Any]]:
        """Return all globally excluded genres."""
        return cast(
            "list[dict[str, Any]]",
            await self.client.send_command("music/genres/global_exclusions", require_schema=84),
        )

    async def remove_genre_global_exclusion(self, genre_id: int) -> Genre:
        """Lift a global genre exclusion, making the genre visible and scannable again."""
        return Genre.from_dict(
            await self.client.send_command(
                "music/genres/remove_global_exclusion",
                genre_id=genre_id,
                require_schema=84,
            )
        )

    async def merge_genres(self, genre_ids: list[str | int], target_genre_id: str | int) -> Genre:
        """Merge one or more genres into a target genre."""
        return Genre.from_dict(
            await self.client.send_command(
                "music/genres/merge",
                genre_ids=genre_ids,
                target_genre_id=target_genre_id,
                require_schema=84,
            )
        )

    async def restore_default_genres(
        self, full_restore: bool = False, content_type: str | None = None
    ) -> list[Genre]:
        """
        Restore default genres for one or every taxonomy (music, podcast, audiobook).

        :param full_restore: Delete all existing genres and recreate them from defaults.
        :param content_type: Restrict a non-destructive restore to a single taxonomy.
        """
        return [
            Genre.from_dict(obj)
            for obj in await self.client.send_command(
                "music/genres/restore_defaults",
                full_restore=full_restore,
                content_type=content_type,
                require_schema=84,
            )
        ]

    async def scan_genre_mappings(self) -> dict[str, Any]:
        """Manually trigger a genre mapping scan (admin only)."""
        return cast(
            "dict[str, Any]",
            await self.client.send_command("music/genres/scan_mappings", require_schema=84),
        )

    async def genre_scanner_status(self) -> dict[str, Any]:
        """Get status of the genre mapping background scanner."""
        return cast(
            "dict[str, Any]",
            await self.client.send_command("music/genres/scanner_status", require_schema=84),
        )

    # Lookup by external id and audiobook collections

    async def get_track_by_external_id(
        self, external_id: str, external_id_type: ExternalID | None = None
    ) -> Track | None:
        """Get track by external ID, querying library then active providers."""
        result = await self.client.send_command(
            "music/tracks/get_by_external_id",
            external_id=external_id,
            external_id_type=external_id_type,
            require_schema=84,
        )
        return Track.from_dict(result) if result else None

    async def get_album_by_external_id(
        self, external_id: str, external_id_type: ExternalID | None = None
    ) -> Album | None:
        """Get album by external ID, querying library then active providers."""
        result = await self.client.send_command(
            "music/albums/get_by_external_id",
            external_id=external_id,
            external_id_type=external_id_type,
            require_schema=84,
        )
        return Album.from_dict(result) if result else None

    async def get_artist_by_external_id(
        self, external_id: str, external_id_type: ExternalID | None = None
    ) -> Artist | None:
        """Get artist by external ID, querying library then active providers."""
        result = await self.client.send_command(
            "music/artists/get_by_external_id",
            external_id=external_id,
            external_id_type=external_id_type,
            require_schema=84,
        )
        return Artist.from_dict(result) if result else None

    async def get_playlist_by_external_id(
        self, external_id: str, external_id_type: ExternalID | None = None
    ) -> Playlist | None:
        """Get playlist by external ID, querying library then active providers."""
        result = await self.client.send_command(
            "music/playlists/get_by_external_id",
            external_id=external_id,
            external_id_type=external_id_type,
            require_schema=84,
        )
        return Playlist.from_dict(result) if result else None

    async def get_radio_by_external_id(
        self, external_id: str, external_id_type: ExternalID | None = None
    ) -> Radio | None:
        """Get radio by external ID, querying library then active providers."""
        result = await self.client.send_command(
            "music/radios/get_by_external_id",
            external_id=external_id,
            external_id_type=external_id_type,
            require_schema=84,
        )
        return Radio.from_dict(result) if result else None

    async def get_audiobook_by_external_id(
        self, external_id: str, external_id_type: ExternalID | None = None
    ) -> Audiobook | None:
        """Get audiobook by external ID, querying library then active providers."""
        result = await self.client.send_command(
            "music/audiobooks/get_by_external_id",
            external_id=external_id,
            external_id_type=external_id_type,
            require_schema=84,
        )
        return Audiobook.from_dict(result) if result else None

    async def get_audiobook_collection(self, item_id: str) -> MediaCollection[Audiobook]:
        """Get a single audiobook collection."""
        return MediaCollection.from_dict(
            await self.client.send_command(
                "music/audiobooks/get_collection",
                item_id=item_id,
                require_schema=84,
            )
        )

    async def get_podcast_by_external_id(
        self, external_id: str, external_id_type: ExternalID | None = None
    ) -> Podcast | None:
        """Get podcast by external ID, querying library then active providers."""
        result = await self.client.send_command(
            "music/podcasts/get_by_external_id",
            external_id=external_id,
            external_id_type=external_id_type,
            require_schema=84,
        )
        return Podcast.from_dict(result) if result else None

    async def get_genre_by_external_id(
        self, external_id: str, external_id_type: ExternalID | None = None
    ) -> Genre | None:
        """Get genre by external ID, querying library then active providers."""
        result = await self.client.send_command(
            "music/genres/get_by_external_id",
            external_id=external_id,
            external_id_type=external_id_type,
            require_schema=84,
        )
        return Genre.from_dict(result) if result else None
