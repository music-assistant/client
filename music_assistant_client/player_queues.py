"""Handle PlayerQueues related endpoints for Music Assistant."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from music_assistant_models.background_task import BackgroundTask
from music_assistant_models.enums import (
    EventType,
    QueueOption,
    RepeatMode,
    SortDirection,
    SortField,
)
from music_assistant_models.player_queue import PlayerQueue
from music_assistant_models.queue_item import QueueItem

from .constants import IMPERSONATION_SCHEMA_VERSION, PLAY_MEDIA_SORT_SCHEMA_VERSION
from .helpers import LinkedUser, impersonation_arg

if TYPE_CHECKING:
    from collections.abc import Iterator

    from music_assistant_models.event import MassEvent
    from music_assistant_models.media_items import ItemMapping, MediaItemType

    from .client import MusicAssistantClient


def radio_playlist_uri(seed: MediaItemType | ItemMapping | str) -> str:
    """
    Return the radio_playlist:// uri that enqueues a dynamic 'radio' for a seed item.

    Pass the result to PlayerQueues.play_media to start a dynamic radio playlist based on the
    seed item. This replaces the deprecated radio_mode=True flag.

    - seed: The seed media item (artist/album/track/genre/playlist) or its uri.
    """
    seed_uri = seed if isinstance(seed, str) else str(seed.uri)
    if seed_uri.startswith("radio_playlist://"):
        return seed_uri
    return f"radio_playlist://playlist/{seed_uri}"


class PlayerQueues:
    """PlayerQueue related endpoints/data for Music Assistant."""

    def __init__(self, client: MusicAssistantClient) -> None:
        """Handle Initialization."""
        self.client = client
        # subscribe to player events
        client.subscribe(
            self._handle_event,
            (
                EventType.QUEUE_ADDED,
                EventType.QUEUE_UPDATED,
                EventType.QUEUE_TIME_UPDATED,
                EventType.PLAYER_REMOVED,
            ),
        )
        # the initial items are retrieved after connect
        self._queues: dict[str, PlayerQueue] = {}

    @property
    def player_queues(self) -> list[PlayerQueue]:
        """Return all player queues."""
        return list(self._queues.values())

    def get(self, queue_id: str) -> PlayerQueue | None:
        """Return PlayerQueue by ID (or None if not found)."""
        return self._queues.get(queue_id)

    async def get_queue_items(
        self,
        queue_id: str,
        limit: int = 500,
        offset: int = 0,
        *,
        user: str | LinkedUser | None = None,
    ) -> list[QueueItem]:
        """
        Get all QueueItems for given PlayerQueue.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return [
            QueueItem.from_dict(obj)
            for obj in await self.client.send_command(
                "player_queues/items",
                queue_id=queue_id,
                limit=limit,
                offset=offset,
                require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
                **impersonation_arg(self.client.server_info, user),
            )
        ]

    async def get_active_queue(
        self, player_id: str, *, user: str | LinkedUser | None = None
    ) -> PlayerQueue | None:
        """
        Return the current active/synced queue for a player.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        assert self.client.server_info  # for type checking
        # from schema version 27+, the server can handle this natively; another user's queue
        # only ever comes from the server, never from this connection's cache
        if self.client.server_info.schema_version >= 27 or user is not None:
            result = await self.client.send_command(
                "player_queues/get_active_queue",
                player_id=player_id,
                require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
                **impersonation_arg(self.client.server_info, user),
            )
            if result or user is not None:
                return PlayerQueue.from_dict(result) if result else None
        if player := self.client.players.get(player_id):
            return self.get(player.active_source or player.player_id)
        return None

    async def play(self, queue_id: str, *, user: str | LinkedUser | None = None) -> None:
        """
        Send PLAY command to given queue.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/play",
            queue_id=queue_id,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        )

    async def pause(self, queue_id: str, *, user: str | LinkedUser | None = None) -> None:
        """
        Send PAUSE command to given queue.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/pause",
            queue_id=queue_id,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        )

    async def stop(self, queue_id: str, *, user: str | LinkedUser | None = None) -> None:
        """
        Send STOP command to given queue.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/stop",
            queue_id=queue_id,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        )

    async def resume(
        self,
        queue_id: str,
        fade_in: bool | None = None,
        *,
        user: str | LinkedUser | None = None,
    ) -> None:
        """Handle RESUME command for given queue.

        :param queue_id: queue_id of the queue to handle the command.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/resume",
            queue_id=queue_id,
            fade_in=fade_in,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        )

    async def next(self, queue_id: str, *, user: str | LinkedUser | None = None) -> None:
        """
        Send NEXT TRACK command to given queue.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/next",
            queue_id=queue_id,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        )

    async def previous(self, queue_id: str, *, user: str | LinkedUser | None = None) -> None:
        """
        Send PREVIOUS TRACK command to given queue.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/previous",
            queue_id=queue_id,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        )

    async def clear(self, queue_id: str, *, user: str | LinkedUser | None = None) -> None:
        """
        Send CLEAR QUEUE command to given queue.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/clear",
            queue_id=queue_id,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        )

    async def move_item(
        self,
        queue_id: str,
        queue_item_id: str,
        pos_shift: int = 1,
        *,
        user: str | LinkedUser | None = None,
    ) -> None:
        """
        Move queue item x up/down the queue.

        Parameters:
        - queue_id: id of the queue to process this request.
        - queue_item_id: the item_id of the queueitem that needs to be moved.
        - pos_shift: move item x positions down if positive value
        - pos_shift: move item x positions up if negative value
        - pos_shift:  move item to top of queue as next item if 0
        - user: Run the command on behalf of this user: a user_id or username, or a
          LinkedUser reference by auth provider. Requires the users.impersonate scope when
          it is another user.

        NOTE: Fails if the given QueueItem is already playing or loaded in the buffer.
        """
        await self.client.send_command(
            "player_queues/move_item",
            queue_id=queue_id,
            queue_item_id=queue_item_id,
            pos_shift=pos_shift,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        )

    async def move_up(self, queue_id: str, queue_item_id: str) -> None:
        """Move given queue item one place up in the queue."""
        await self.move_item(queue_id=queue_id, queue_item_id=queue_item_id, pos_shift=-1)

    async def move_down(self, queue_id: str, queue_item_id: str) -> None:
        """Move given queue item one place down in the queue."""
        await self.move_item(queue_id=queue_id, queue_item_id=queue_item_id, pos_shift=1)

    async def move_next(self, queue_id: str, queue_item_id: str) -> None:
        """Move given queue item as next up in the queue."""
        await self.move_item(queue_id=queue_id, queue_item_id=queue_item_id, pos_shift=0)

    async def move_item_end(
        self, queue_id: str, queue_item_id: str, *, user: str | LinkedUser | None = None
    ) -> None:
        """
        Move queue item to the end of the queue.

        :param queue_id: id of the queue to process this request.
        :param queue_item_id: the item_id of the queueitem that needs to be moved.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/move_item_end",
            queue_id=queue_id,
            queue_item_id=queue_item_id,
            require_schema=101,
            **impersonation_arg(self.client.server_info, user),
        )

    async def delete_item(
        self,
        queue_id: str,
        item_id_or_index: int | str,
        *,
        user: str | LinkedUser | None = None,
    ) -> None:
        """
        Delete item (by id or index) from the queue.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/delete_item",
            queue_id=queue_id,
            item_id_or_index=item_id_or_index,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        )

    async def seek(
        self, queue_id: str, position: int, *, user: str | LinkedUser | None = None
    ) -> None:
        """
        Handle SEEK command for given queue.

        Parameters:
        - position: position in seconds to seek to in the current playing item.
        - user: Run the command on behalf of this user: a user_id or username, or a
          LinkedUser reference by auth provider. Requires the users.impersonate scope when
          it is another user.
        """
        await self.client.send_command(
            "player_queues/seek",
            queue_id=queue_id,
            position=position,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        )

    async def skip(
        self, queue_id: str, seconds: int, *, user: str | LinkedUser | None = None
    ) -> None:
        """
        Handle SKIP command for given queue.

        Parameters:
        - seconds: number of seconds to skip in track. Use negative value to skip back.
        - user: Run the command on behalf of this user: a user_id or username, or a
          LinkedUser reference by auth provider. Requires the users.impersonate scope when
          it is another user.
        """
        await self.client.send_command(
            "player_queues/skip",
            queue_id=queue_id,
            seconds=seconds,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        )

    async def shuffle(
        self, queue_id: str, shuffle_enabled: bool, *, user: str | LinkedUser | None = None
    ) -> None:
        """
        Configure shuffle mode on the the queue.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/shuffle",
            queue_id=queue_id,
            shuffle_enabled=shuffle_enabled,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        )

    async def repeat(
        self, queue_id: str, repeat_mode: RepeatMode, *, user: str | LinkedUser | None = None
    ) -> None:
        """
        Configure repeat mode on the the queue.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/repeat",
            queue_id=queue_id,
            repeat_mode=repeat_mode,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        )

    async def crossfade(
        self, queue_id: str, crossfade_enabled: bool, *, user: str | LinkedUser | None = None
    ) -> None:
        """
        Enable or disable crossfade on the queue.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/crossfade",
            queue_id=queue_id,
            crossfade_enabled=crossfade_enabled,
            require_schema=101,
            **impersonation_arg(self.client.server_info, user),
        )

    async def overlay(
        self,
        queue_id: str,
        enabled: bool | None = None,
        source: str | None = None,
        volume: int | None = None,
        *,
        user: str | LinkedUser | None = None,
    ) -> None:
        """
        Configure the audio overlay (a looping sound effect mixed into the queue's audio).

        :param queue_id: queue_id of the queue to configure.
        :param enabled: Enable or disable the audio overlay. Omit to leave unchanged.
        :param source: URI of the sound effect item to mix in. Omit to leave unchanged.
        :param volume: Overlay loudness relative to the music in percent
            (0-200, 100 = equally loud). Omit to leave unchanged.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/overlay",
            queue_id=queue_id,
            enabled=enabled,
            source=source,
            volume=volume,
            require_schema=101,
            **impersonation_arg(self.client.server_info, user),
        )

    async def set_playback_speed(
        self,
        queue_id: str,
        speed: float,
        queue_item_id: str | None = None,
        *,
        user: str | LinkedUser | None = None,
    ) -> None:
        """
        Set the playback speed for the given queue item (audiobooks and podcast episodes only).

        :param queue_id: queue_id of the queue to configure.
        :param speed: playback speed multiplier (0.5 to 3.0). 1.0 = normal speed.
        :param queue_item_id: The queue item to set the speed for, the current item if omitted.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/set_playback_speed",
            queue_id=queue_id,
            speed=speed,
            queue_item_id=queue_item_id,
            require_schema=101,
            **impersonation_arg(self.client.server_info, user),
        )

    async def play_index(
        self,
        queue_id: str,
        index: int | str,
        seek_position: int = 0,
        fade_in: bool = False,
        *,
        user: str | LinkedUser | None = None,
    ) -> None:
        """
        Play item at index (or item_id) X in queue.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/play_index",
            queue_id=queue_id,
            index=index,
            seek_position=seek_position,
            fade_in=fade_in,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        )

    async def play_media(  # noqa: PLR0913
        self,
        queue_id: str,
        media: MediaItemType | list[MediaItemType] | str | list[str],
        option: QueueOption | None = None,
        radio_mode: bool = False,
        start_item: str | None = None,
        user: str | LinkedUser | None = None,
        username: str | None = None,
        sort_by: str | None = None,
        *,
        sort_field: SortField | None = None,
        sort_direction: SortDirection | None = None,
        shuffle: bool | None = None,
        start_from_beginning: bool = False,
    ) -> None:
        """
        Play media item(s) on the given queue.

        - media: Media that should be played (MediaItem(s) or uri's).
        - queue_opt: Which enqueue mode to use.
        - radio_mode: Deprecated. When True against a server that supports radio playlists, the
          seed item(s) are translated client-side to a radio_playlist:// dynamic playlist (see
          radio_playlist_uri); older servers still receive the flag. Prefer passing such a uri.
        - start_item: Optional item to start the playlist or album from.
        - user: Optionally attribute the playback to this user: a user_id or username string,
          or a LinkedUser reference by auth provider (server schema >= 44), e.g. for playback
          history when triggered from automation. Requires the authenticated client to have
          sufficient permissions.
        - username: Deprecated alias for user.
        - sort_by: Deprecated sort key; use sort_field and sort_direction instead.
          Ignored when sort_field is set; cannot be combined with sort_direction alone.
        - sort_field: Sort field to order album or playlist tracks before applying start_item.
        - sort_direction: Direction for the selected sort field.
        - shuffle: Play the media shuffled (or explicitly in order), only for the options that
          start playing right away. Omit to follow the queue's own shuffle setting.
        - start_from_beginning: Start a podcast episode at position 0, ignoring any saved
          resume position.
        """
        if sort_by is not None and sort_field is None and sort_direction is not None:
            raise ValueError(
                "Use sort_field with sort_direction instead of combining sort_by "
                "with sort_direction alone"
            )
        if (
            radio_mode
            and self.client.server_info is not None
            and self.client.server_info.schema_version >= 34
        ):
            # schema 34+ supports radio playlists: translate the deprecated radio_mode flag into
            # a radio_playlist:// dynamic playlist client-side. Older servers still receive the
            # radio_mode flag (below) so radio keeps working there.
            seeds = media if isinstance(media, list) else [media]
            media = [radio_playlist_uri(seed) for seed in seeds]
            radio_mode = False
        await self.client.send_command(
            "player_queues/play_media",
            queue_id=queue_id,
            media=media,
            option=option,
            radio_mode=radio_mode,
            start_item=start_item,
            sort_by=(sort_by if sort_field is None else None),
            sort_field=sort_field,
            sort_direction=sort_direction,
            shuffle=shuffle,
            start_from_beginning=start_from_beginning,
            require_schema=max(
                (
                    PLAY_MEDIA_SORT_SCHEMA_VERSION
                    if sort_field is not None or sort_direction is not None
                    else 0
                ),
                51 if shuffle is not None else 0,
                40 if start_from_beginning else 0,
            )
            or None,
            **impersonation_arg(self.client.server_info, user or username),
        )

    async def transfer(
        self,
        source_queue_id: str,
        target_queue_id: str,
        auto_play: bool | None = None,
        *,
        user: str | LinkedUser | None = None,
    ) -> None:
        """
        Transfer queue to another queue.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/transfer",
            source_queue_id=source_queue_id,
            target_queue_id=target_queue_id,
            auto_play=auto_play,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else 25,
            **impersonation_arg(self.client.server_info, user),
        )

    async def autoplay(
        self, queue_id: str, autoplay_enabled: bool, *, user: str | LinkedUser | None = None
    ) -> None:
        """
        Configure the Autoplay setting on the queue.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/autoplay",
            queue_id=queue_id,
            autoplay_enabled=autoplay_enabled,
            require_schema=101,
            **impersonation_arg(self.client.server_info, user),
        )

    async def dont_stop_the_music(self, queue_id: str, dont_stop_the_music_enabled: bool) -> None:
        """Configure Don't stop the music setting on the queue."""
        await self.client.send_command(
            "player_queues/dont_stop_the_music",
            queue_id=queue_id,
            dont_stop_the_music_enabled=dont_stop_the_music_enabled,
        )

    async def play_pause(self, queue_id: str, *, user: str | LinkedUser | None = None) -> None:
        """
        Toggle play/pause on given playerqueue.

        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        await self.client.send_command(
            "player_queues/play_pause",
            queue_id=queue_id,
            require_schema=IMPERSONATION_SCHEMA_VERSION if user is not None else None,
            **impersonation_arg(self.client.server_info, user),
        )

    async def save_as_playlist(
        self, queue_id: str, name: str, *, user: str | LinkedUser | None = None
    ) -> BackgroundTask:
        """
        Save the current queue items as a new playlist.

        :param queue_id: The queue_id of the queue to save.
        :param name: The name for the new playlist.
        :param user: Run the command on behalf of this user: a user_id or username, or a
            LinkedUser reference by auth provider. Requires the users.impersonate scope when
            it is another user.
        """
        return BackgroundTask.from_dict(
            await self.client.send_command(
                "player_queues/save_as_playlist",
                queue_id=queue_id,
                name=name,
                require_schema=101,
                **impersonation_arg(self.client.server_info, user),
            )
        )

    async def _get_player_queues(self) -> list[PlayerQueue]:
        """Fetch all PlayerQueues from the server."""
        return [
            PlayerQueue.from_dict(item)
            for item in await self.client.send_command("player_queues/all")
        ]

    async def fetch_state(self) -> None:
        """Fetch initial state once the server is connected."""
        for queue in await self._get_player_queues():
            self._queues[queue.queue_id] = queue

    def _handle_event(self, event: MassEvent) -> None:
        """Handle incoming player(queue) event."""
        if event.event in (EventType.QUEUE_ADDED, EventType.QUEUE_UPDATED):
            # Queue events always have an object_id
            assert event.object_id
            self._queues[event.object_id] = PlayerQueue.from_dict(event.data)
        elif event.event == EventType.QUEUE_TIME_UPDATED:
            # keep the cached elapsed time in sync so consumers don't read a stale value
            assert event.object_id
            if queue := self._queues.get(event.object_id):
                queue.elapsed_time = float(event.data)
                queue.elapsed_time_last_updated = time.time()
        elif event.event == EventType.PLAYER_REMOVED:
            # the server has no queue removal event, a queue goes away with its player
            assert event.object_id
            self._queues.pop(event.object_id, None)

    def __iter__(self) -> Iterator[PlayerQueue]:
        """Iterate over (available) PlayerQueues."""
        return iter(self._queues.values())

    # Backward compatibility aliases (deprecated)
    queue_command_play = play
    queue_command_pause = pause
    queue_command_stop = stop
    queue_command_resume = resume
    queue_command_next = next  # noqa: A003
    queue_command_previous = previous
    queue_command_clear = clear
    queue_command_move_item = move_item
    queue_command_move_up = move_up
    queue_command_move_down = move_down
    queue_command_move_next = move_next
    queue_command_delete = delete_item
    queue_command_seek = seek
    queue_command_skip = skip
    queue_command_shuffle = shuffle
    queue_command_repeat = repeat
    transfer_queue = transfer
    get_player_get_queue_items = get_queue_items
