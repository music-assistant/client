"""Several generic/basic helpers and utilities complementing the Music Assistant Client."""

from __future__ import annotations

import asyncio
import base64
from _collections_abc import dict_keys, dict_values
from types import MethodType
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

import orjson
from music_assistant_models.auth import AuthProviderType

from .exceptions import InvalidServerVersion

if TYPE_CHECKING:
    from music_assistant_models.api import ServerInfoMessage
    from music_assistant_models.media_items import SearchResults

JSON_ENCODE_EXCEPTIONS = (TypeError, ValueError)
JSON_DECODE_EXCEPTIONS = (orjson.JSONDecodeError,)

DO_NOT_SERIALIZE_TYPES = (MethodType, asyncio.Task)


class LinkedUser(TypedDict):
    """
    Reference to a user by auth provider, as user argument of an API command.

    A plain user_id/username string is shorthand for provider "builtin" with required True.
    With required False, an unknown user softly resolves to no impersonation at all
    (the command runs as the authenticated account) instead of erroring.
    """

    provider: str
    user_id: str
    required: NotRequired[bool]


def impersonation_arg(
    server_info: ServerInfoMessage | None,
    user: str | LinkedUser | None,
) -> dict[str, Any]:
    """
    Return the impersonation argument for an API command.

    :param server_info: The connected server's info (to determine the schema version).
    :param user: The user to impersonate (or None): a user_id or username string, or a
        LinkedUser dict referencing the user by auth provider (server schema >= 44).
    """
    schema_version = server_info.schema_version if server_info is not None else 0
    plain_user: str | None
    if isinstance(user, dict):
        if schema_version >= 44:
            return {"user": user}
        if not user.get("required", True):
            # older server: gracefully degrade soft impersonation to no impersonation
            return {}
        if user.get("provider") != AuthProviderType.BUILTIN:
            raise InvalidServerVersion(
                "Impersonating a user by auth provider requires api schema 44."
            )
        plain_user = user["user_id"]
    else:
        plain_user = user
    if schema_version >= 35:
        return {"user": plain_user}
    # older servers only accept the username argument on selected commands
    return {"username": plain_user}


def compact_media_item_dict(item: dict[str, Any]) -> dict[str, Any]:
    """Return compacted MediaItem dict."""
    for key in (
        "metadata",
        "provider_mappings",
        "favorite",
        "timestamp_added",
        "timestamp_modified",
        "mbid",
    ):
        item.pop(key, None)
    for key, value in item.items():
        if isinstance(value, dict):
            item[key] = compact_media_item_dict(value)
        elif isinstance(value, list):
            for subitem in value:
                if not isinstance(subitem, dict):
                    continue
                compact_media_item_dict(subitem)
    return item


def searchresults_as_compact_dict(search_results: SearchResults) -> dict[str, Any]:
    """Return compacted search result dict."""
    dict_result: dict[str, list[dict[str, Any]]] = search_results.to_dict()
    for media_type_key in dict_result:  # noqa: PLC0206
        for item in dict_result[media_type_key]:
            if not isinstance(item, dict):
                # guards against invalid data
                continue  # type: ignore[unreachable]
            # return limited result to prevent it being too verbose
            compact_media_item_dict(item)
    return dict_result


def get_serializable_value(obj: Any, raise_unhandled: bool = False) -> Any:
    """Parse the value to its serializable equivalent."""
    if getattr(obj, "do_not_serialize", None):
        return None
    if (
        isinstance(obj, list | set | filter | tuple | dict_values | dict_keys | dict_values)
        or obj.__class__ == "dict_valueiterator"
    ):
        return [get_serializable_value(x) for x in obj]
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode("ascii")
    if isinstance(obj, DO_NOT_SERIALIZE_TYPES):
        return None
    if raise_unhandled:
        raise TypeError
    return obj


def serialize_to_json(obj: Any) -> Any:
    """Serialize a value (or a list of values) to json."""
    if obj is None:
        return obj
    if hasattr(obj, "to_json"):
        return obj.to_json()
    return json_dumps(get_serializable_value(obj))


def json_dumps(data: Any, indent: bool = False) -> str:
    """Dump json string."""
    # we use the passthrough dataclass option because we use mashumaro for that
    option = orjson.OPT_OMIT_MICROSECONDS | orjson.OPT_PASSTHROUGH_DATACLASS
    if indent:
        option |= orjson.OPT_INDENT_2
    return orjson.dumps(
        data,
        default=get_serializable_value,
        option=option,
    ).decode("utf-8")


json_loads = orjson.loads
