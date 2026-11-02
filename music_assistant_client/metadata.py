"""Handle Metadata related endpoints for Music Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from music_assistant_models.media_items import MediaItemPalette, media_from_dict

from .helpers import LinkedUser, impersonation_arg

if TYPE_CHECKING:
    from music_assistant_models.media_items import MediaItemType, Track

    from .client import MusicAssistantClient


class Metadata:
    """Metadata related endpoints/data for Music Assistant."""

    def __init__(self, client: MusicAssistantClient) -> None:
        """Initialize Metadata controller."""
        self.client = client

    async def set_default_preferred_language(self, lang: str) -> None:
        """
        Set the (default) preferred language.

        Reasoning behind this is that the backend can not make a wise choice for the default,
        so relies on some external source that knows better to set this info, like the frontend
        or a streaming provider.

        Can only be set once (by this call or the user).
        """
        await self.client.send_command(
            "metadata/set_default_preferred_language",
            lang=lang,
        )

    async def update_metadata(
        self,
        item: str | MediaItemType,
        force_refresh: bool | None = None,
    ) -> MediaItemType:
        """Get/update extra/enhanced metadata for/on given MediaItem."""
        return cast(
            "MediaItemType",
            media_from_dict(
                await self.client.send_command(
                    "metadata/update_metadata",
                    item=item,
                    force_refresh=force_refresh,
                )
            ),
        )

    async def get_image_palette(self, image_id: str) -> MediaItemPalette | None:
        """
        Get the color palette extracted from a (proxied) image.

        :param image_id: The imageproxy image id (the `proxy_id` field on a MediaItemImage).
        """
        result = await self.client.send_command(
            "metadata/get_image_palette",
            image_id=image_id,
            require_schema=34,
        )
        return MediaItemPalette.from_dict(result) if result else None

    async def get_track_lyrics(
        self,
        track: Track,
        *,
        user: str | LinkedUser | None = None,
    ) -> tuple[str | None, str | None]:
        """
        Get lyrics for given track from metadata providers.

        Returns a tuple of (lyrics, lrc_lyrics) if found.

        :param track: The track to get the lyrics for.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when it
            is another user.
        """
        lyrics, lrc_lyrics = await self.client.send_command(
            "metadata/get_track_lyrics",
            track=track,
            require_schema=101,
            **impersonation_arg(self.client.server_info, user),
        )
        return lyrics, lrc_lyrics

    async def set_preferred_language(self, lang: str) -> None:
        """
        Set the preferred language.

        Note that this will not modify any existing metadata, but will be used for future lookups.
        """
        await self.client.send_command(
            "metadata/set_preferred_language",
            lang=lang,
            require_schema=101,
        )
