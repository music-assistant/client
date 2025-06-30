"""Handle player related endpoints for Music Assistant."""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

from music_assistant_models.enums import EventType, MediaType
from music_assistant_models.errors import (
    MusicAssistantError,
    PlayerCommandFailed,
    PlayerUnavailableError,
)
from music_assistant_models.player import Player

if TYPE_CHECKING:
    from collections.abc import Iterator

    from music_assistant_models.event import MassEvent

    from .client import MusicAssistantClient


class Players:
    """Player related endpoints/data for Music Assistant."""

    def __init__(self, client: MusicAssistantClient) -> None:
        """Handle Initialization."""
        self.client = client
        # subscribe to player events
        client.subscribe(
            self._handle_event,
            (
                EventType.PLAYER_ADDED,
                EventType.PLAYER_REMOVED,
                EventType.PLAYER_UPDATED,
            ),
        )
        # the initial items are retrieved after connect
        self._players: dict[str, Player] = {}

    @property
    def players(self) -> list[Player]:
        """Return all players."""
        return list(self._players.values())

    def __iter__(self) -> Iterator[Player]:
        """Iterate over (available) players."""
        return iter(self._players.values())

    def get(self, player_id: str) -> Player | None:
        """Return Player by ID (or None if not found)."""
        return self._players.get(player_id)

    def __getitem__(self, player_id: str) -> Player:
        """Return Player by ID."""
        return self._players[player_id]

    #  Player related endpoints/commands

    async def player_command_stop(self, player_id: str) -> None:
        """Send STOP command to given player (directly)."""
        await self.client.send_command("players/cmd/stop", player_id=player_id)

    async def player_command_play(self, player_id: str) -> None:
        """Send PLAY command to given player (directly)."""
        await self.client.send_command("players/cmd/play", player_id=player_id)

    async def player_command_pause(self, player_id: str) -> None:
        """Send PAUSE command to given player (directly)."""
        await self.client.send_command("players/cmd/pause", player_id=player_id)

    async def player_command_play_pause(self, player_id: str) -> None:
        """Send PLAY_PAUSE (toggle) command to given player (directly)."""
        await self.client.send_command("players/cmd/pause", player_id=player_id)

    async def player_command_power(self, player_id: str, powered: bool) -> None:
        """Send POWER command to given player."""
        await self.client.send_command("players/cmd/power", player_id=player_id, powered=powered)

    async def player_command_volume_set(self, player_id: str, volume_level: int) -> None:
        """Send VOLUME SET command to given player."""
        await self.client.send_command(
            "players/cmd/volume_set", player_id=player_id, volume_level=volume_level
        )

    async def player_command_volume_up(self, player_id: str) -> None:
        """Send VOLUME UP command to given player."""
        await self.client.send_command("players/cmd/volume_up", player_id=player_id)

    async def player_command_volume_down(self, player_id: str) -> None:
        """Send VOLUME DOWN command to given player."""
        await self.client.send_command("players/cmd/volume_down", player_id=player_id)

    async def player_command_volume_mute(self, player_id: str, muted: bool) -> None:
        """Send VOLUME MUTE command to given player."""
        await self.client.send_command("players/cmd/volume_mute", player_id=player_id, muted=muted)

    async def player_command_seek(self, player_id: str, position: int) -> None:
        """Handle SEEK command for given player (directly).

        - player_id: player_id of the player to handle the command.
        - position: position in seconds to seek to in the current playing item.
        """
        await self.client.send_command("players/cmd/seek", player_id=player_id, position=position)

    async def player_command_next_track(self, player_id: str) -> None:
        """Handle NEXT TRACK command for given player."""
        await self.client.send_command("players/cmd/next", player_id=player_id)

    async def player_command_previous_track(self, player_id: str) -> None:
        """Handle PREVIOUS TRACK command for given player."""
        await self.client.send_command("players/cmd/previous", player_id=player_id)

    async def player_command_select_source(self, player_id: str, source: str) -> None:
        """
        Handle SELECT SOURCE command on given player.

        - player_id: player_id of the player to handle the command.
        - source: The ID of the source that needs to be activated/selected.
        """
        await self.client.send_command(
            "players/cmd/select_source", player_id=player_id, source=source
        )

    async def player_command_group(self, player_id: str, target_player: str) -> None:
        """Handle GROUP command for given player.

        Join/add the given player(id) to the given (leader) player/sync group.
        If the target player itself is already synced to another player, this may fail.
        If the player can not be synced with the given target player, this may fail.

            - player_id: player_id of the player to handle the command.
            - target_player: player_id of the syncgroup leader or group player.
        """
        await self.client.send_command(
            "players/cmd/group", player_id=player_id, target_player=target_player
        )

    async def player_command_ungroup(self, player_id: str) -> None:
        """Handle UNGROUP command for given player.

        Remove the given player from any (sync)groups it currently is synced to.
        If the player is not currently grouped to any other player,
        this will silently be ignored.

            - player_id: player_id of the player to handle the command.
        """
        await self.client.send_command("players/cmd/ungroup", player_id=player_id)

    async def player_command_group_many(
        self, target_player: str, child_player_ids: list[str]
    ) -> None:
        """Join given player(s) to target player."""
        await self.client.send_command(
            "players/cmd/group_many", target_player=target_player, child_player_ids=child_player_ids
        )

    async def player_command_ungroup_many(self, player_ids: list[str]) -> None:
        """Handle UNGROUP command for all the given players."""
        await self.client.send_command("players/cmd/ungroup_many", player_ids=player_ids)

    async def play_announcement(
        self,
        player_id: str,
        url: str,
        use_pre_announce: bool | None = None,
        volume_level: int | None = None,
    ) -> None:
        """Handle playback of an announcement (url) on given player."""
        await self.client.send_command(
            "players/cmd/play_announcement",
            player_id=player_id,
            url=url,
            use_pre_announce=use_pre_announce,
            volume_level=volume_level,
        )

    #  PlayerGroup related endpoints/commands

    async def set_player_group_volume(self, player_id: str, volume_level: int) -> None:
        """
        Send VOLUME_SET command to given playergroup.

        Will send the new (average) volume level to group child's.
        - player_id: player_id of the playergroup to handle the command.
        - volume_level: volume level (0..100) to set on the player.
        """
        await self.client.send_command(
            "players/cmd/group_volume", player_id=player_id, volume_level=volume_level
        )

    async def player_command_group_volume_up(self, player_id: str) -> None:
        """Send VOLUME_UP command to given playergroup."""
        await self.client.send_command("players/cmd/group_volume_up", player_id=player_id)

    async def player_command_group_volume_down(self, player_id: str) -> None:
        """Send VOLUME_DOWN command to given playergroup."""
        await self.client.send_command("players/cmd/group_volume_down", player_id=player_id)

    async def add_currently_playing_to_favorites(self, player_id: str) -> None:
        """
        Add the currently playing item/track on given player to the favorites.

        This tries to resolve the currently playing media to an actual media item
        and add that to the favorites in the library.

        Will raise an error if the player is not currently playing anything
        or if the currently playing media can not be resolved to a media item.
        """
        assert self.client.server_info  # for type checking
        if self.client.server_info.schema_version >= 27:
            # if the server supports the new favorites endpoint, use that
            await self.client.send_command(
                "players/add_currently_playing_to_favorites", player_id=player_id
            )
            return
        # Fallback implementation for older server versions.
        # TODO: remove this after a while, once all/most servers are updated

        # guard for unknown player - which should not happen, but just in case
        if not (player := self._players.get(player_id)):
            raise PlayerUnavailableError(f"Player {player_id} not found")
        # handle mass player queue active
        if mass_queue := await self.client.player_queues.get_active_queue(player_id):
            if not (current_item := mass_queue.current_item) or not current_item.media_item:
                raise PlayerCommandFailed("No current item to add to favorites")
            # if we're playing a radio station, try to resolve the currently playing track
            if current_item.media_item.media_type == MediaType.RADIO:
                if not (
                    (streamdetails := mass_queue.current_item.streamdetails)
                    and (stream_title := streamdetails.stream_title)
                    and " - " in stream_title
                ):
                    # no stream title available, so we can't resolve the track
                    # this can happen if the radio station does not provide metadata
                    # or there's a commercial break
                    # Possible future improvement could be to actually detect the song with a
                    # shazam-like approach.
                    raise PlayerCommandFailed("No current item to add to favorites")
                # send the streamtitle into a global search query
                search_artist, search_title_title = stream_title.split(" - ", 1)
                if track := await self.client.music.get_track_by_name(
                    search_title_title, search_artist
                ):
                    # we found a track, so add it to the favorites
                    await self.client.music.add_item_to_favorites(track)
                    return
            # any other media item, just add it to the favorites directly
            await self.client.music.add_item_to_favorites(current_item.media_item)
            return
        # guard for player with no active source
        if not player.active_source:
            raise PlayerCommandFailed("Player has no active source")
        # handle other source active using the current_media with uri
        if current_media := player.current_media:
            # prefer the uri of the current media item
            if current_media.uri:
                with suppress(MusicAssistantError):
                    await self.client.music.add_item_to_favorites(current_media.uri)
                    return
            # fallback to search based on artist and title (and album if available)
            if current_media.artist and current_media.title:  # noqa: SIM102
                if track := await self.client.music.get_track_by_name(
                    current_media.title,
                    current_media.artist,
                    current_media.album,
                ):
                    # we found a track, so add it to the favorites
                    await self.client.music.add_item_to_favorites(track)
                    return
        # if we reach here, we could not resolve the currently playing item
        raise PlayerCommandFailed("No current item to add to favorites")

    # Other endpoints/commands

    async def _get_players(self) -> list[Player]:
        """Fetch all Players from the server."""
        return [Player.from_dict(item) for item in await self.client.send_command("players/all")]

    async def fetch_state(self) -> None:
        """Fetch initial state once the server is connected."""
        for player in await self._get_players():
            self._players[player.player_id] = player

    def _handle_event(self, event: MassEvent) -> None:
        """Handle incoming player event."""
        if event.event in (EventType.PLAYER_ADDED, EventType.PLAYER_UPDATED):
            # Player events always have an object id
            assert event.object_id
            self._players[event.object_id] = Player.from_dict(event.data)
            return
        if event.event == EventType.PLAYER_REMOVED:
            # Player events always have an object id
            assert event.object_id
            self._players.pop(event.object_id, None)
