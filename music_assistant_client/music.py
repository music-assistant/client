"""Handle Music/library related endpoints for Music Assistant."""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING, cast

from music_assistant_models.enums import AlbumType, ImageType, MediaType
from music_assistant_models.helpers import create_sort_name
from music_assistant_models.media_items import (
    Album,
    Artist,
    Audiobook,
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
from music_assistant_models.provider import SyncTask

if TYPE_CHECKING:
    from music_assistant_models.queue_item import QueueItem

    from .client import MusicAssistantClient


class Music:
    """Music(library) related endpoints/data for Music Assistant."""

    def __init__(self, client: MusicAssistantClient) -> None:
        """Handle Initialization."""
        self.client = client

    #  Tracks related endpoints/commands

    async def get_library_tracks(
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
    ) -> list[Track]:
        """Get Track listing from the server."""
        return [
            Track.from_dict(obj)
            for obj in await self.client.send_command(
                "music/tracks/library_items",
                favorite=favorite,
                search=search,
                limit=limit,
                offset=offset,
                order_by=order_by,
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
                "music/tracks/get_track",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                album_uri=album_uri,
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

    async def get_library_albums(
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        album_types: list[AlbumType] | None = None,
    ) -> list[Album]:
        """Get Albums listing from the server."""
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
                "music/albums/get_album",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
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

    async def get_library_artists(
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        album_artists_only: bool = False,
    ) -> list[Artist]:
        """Get Artists listing from the server."""
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
                "music/artists/get_artist",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
            ),
        )

    async def get_artist_tracks(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        in_library_only: bool = False,
    ) -> list[Track]:
        """Get (top)tracks for given artist."""
        return [
            Track.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/artist_tracks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                in_library_only=in_library_only,
            )
        ]

    async def get_artist_albums(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        in_library_only: bool = False,
    ) -> list[Album]:
        """Get (top)albums for given artist."""
        return [
            Album.from_dict(item)
            for item in await self.client.send_command(
                "music/artists/artist_albums",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                in_library_only=in_library_only,
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
    ) -> list[Playlist]:
        """Get Playlists listing from the server."""
        return [
            Playlist.from_dict(obj)
            for obj in await self.client.send_command(
                "music/playlists/library_items",
                favorite=favorite,
                search=search,
                limit=limit,
                offset=offset,
                order_by=order_by,
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
                "music/playlists/get_playlist",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
            ),
        )

    async def get_playlist_tracks(
        self,
        item_id: str,
        provider_instance_id_or_domain: str,
        page: int = 0,
    ) -> list[Track]:
        """Get tracks for given playlist."""
        return [
            Track.from_dict(obj)
            for obj in await self.client.send_command(
                "music/playlists/playlist_tracks",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
                page=page,
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
    ) -> list[Audiobook]:
        """Get Audiobooks listing from the server."""
        return [
            Audiobook.from_dict(obj)
            for obj in await self.client.send_command(
                "music/audiobooks/library_items",
                favorite=favorite,
                search=search,
                limit=limit,
                offset=offset,
                order_by=order_by,
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
                "music/audiobooks/get_audiobook",
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
    ) -> list[Podcast]:
        """Get Podcasts listing from the server."""
        return [
            Podcast.from_dict(obj)
            for obj in await self.client.send_command(
                "music/podcasts/library_items",
                favorite=favorite,
                search=search,
                limit=limit,
                offset=offset,
                order_by=order_by,
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
                "music/podcasts/get_podcast",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
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

    #  Radio related endpoints/commands

    async def get_library_radios(
        self,
        favorite: bool | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
    ) -> list[Radio]:
        """Get Radio listing from the server."""
        return [
            Radio.from_dict(obj)
            for obj in await self.client.send_command(
                "music/radios/library_items",
                favorite=favorite,
                search=search,
                limit=limit,
                offset=offset,
                order_by=order_by,
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
                "music/radios/get_radio",
                item_id=item_id,
                provider_instance_id_or_domain=provider_instance_id_or_domain,
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

    async def get_running_sync_tasks(self) -> list[SyncTask]:
        """Return list with providers that are currently (scheduled for) syncing."""
        return [SyncTask(**item) for item in await self.client.send_command("music/synctasks")]

    async def search(
        self,
        search_query: str,
        media_types: list[MediaType] = MediaType.ALL,
        limit: int = 50,
        library_only: bool = False,
    ) -> SearchResults:
        """Perform global search for media items on all providers.

        :param search_query: Search query.
        :param media_types: A list of media_types to include.
        :param limit: number of items to return in the search (per type).
        """
        return SearchResults.from_dict(
            await self.client.send_command(
                "music/search",
                search_query=search_query,
                media_types=media_types,
                limit=limit,
                library_only=library_only,
            ),
        )

    async def browse(
        self,
        path: str | None = None,
    ) -> list[MediaItemType | ItemMapping]:
        """Browse Music providers."""
        return [
            media_from_dict(obj)
            for obj in await self.client.send_command("music/browse", path=path)
        ]

    async def recently_played(
        self, limit: int = 10, media_types: list[MediaType] | None = None
    ) -> list[ItemMapping]:
        """Return a list of the last played items."""
        return [
            ItemMapping.from_dict(item)
            for item in await self.client.send_command(
                "music/recently_played_items", limit=limit, media_types=media_types
            )
        ]

    async def in_progress_items(self, limit: int = 10) -> list[ItemMapping]:
        """Return a list of the Audiobooks and PodcastEpisodes that are in progress."""
        return [
            ItemMapping.from_dict(item)
            for item in await self.client.send_command("music/in_progress_items", limit=limit)
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
        item_id: str | int,
    ) -> None:
        """Remove (library) item from the favorites."""
        await self.client.send_command(
            "music/favorites/remove_item",
            media_type=media_type,
            item_id=item_id,
        )

    async def remove_item_from_library(
        self, media_type: MediaType, library_item_id: str | int
    ) -> None:
        """
        Remove item from the library.

        Destructive! Will remove the item and all dependants.
        """
        await self.client.send_command(
            "music/library/remove_item",
            media_type=media_type,
            library_item_id=library_item_id,
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
    ) -> None:
        """Mark item as played in playlog."""
        await self.client.send_command(
            "music/mark_played",
            media_item=media_item,
            fully_played=fully_played,
        )

    async def mark_item_unplayed(
        self,
        media_item: MediaItemType,
    ) -> None:
        """Mark item as unplayed in playlog."""
        await self.client.send_command("music/mark_unplayed", media_item=media_item)

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
                    track_name=track_name.split(splitter)[0].strip(),
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
    ) -> MediaItemType | ItemMapping | None:
        """Try to find a media item (such as a playlist) by name."""
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
