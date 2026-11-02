"""Handle Config related endpoints for Music Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from music_assistant_models.auth import UserSummary
from music_assistant_models.config_entries import (
    ConfigActionResult,
    ConfigEntry,
    ConfigValueType,
    CoreConfig,
    PlayerConfig,
    PlayerQueueConfig,
    ProviderConfig,
)
from music_assistant_models.dsp import DSPConfig, DSPConfigPreset
from music_assistant_models.setup_flow import SetupFlowStep

if TYPE_CHECKING:
    from music_assistant_models.enums import ProviderSharing, ProviderType

    from .client import MusicAssistantClient


class Config:
    """Config related endpoints/data for Music Assistant."""

    def __init__(self, client: MusicAssistantClient) -> None:
        """Handle Initialization."""
        self.client = client

    # Provider Config related commands/functions

    async def get_provider_configs(
        self,
        provider_type: ProviderType | None = None,
        provider_domain: str | None = None,
        include_values: bool = False,
    ) -> list[ProviderConfig]:
        """Return all known provider configurations, optionally filtered by ProviderType."""
        return [
            ProviderConfig.from_dict(item)
            for item in await self.client.send_command(
                "config/providers",
                provider_type=provider_type,
                provider_domain=provider_domain,
                include_values=include_values,
            )
        ]

    async def get_provider_config(self, instance_id: str) -> ProviderConfig:
        """Return (full) configuration for a single provider."""
        return ProviderConfig.from_dict(
            await self.client.send_command("config/providers/get", instance_id=instance_id)
        )

    async def get_provider_config_value(
        self,
        instance_id: str,
        key: str,
        default: ConfigValueType = None,
    ) -> ConfigValueType:
        """Return single configentry value for a provider."""
        return cast(
            "ConfigValueType",
            await self.client.send_command(
                "config/providers/get_value",
                instance_id=instance_id,
                key=key,
                default=default,
            ),
        )

    async def get_provider_config_entries(self, instance_id: str) -> list[ConfigEntry]:
        """Return the config (options) entries for an existing provider instance."""
        return [
            ConfigEntry.from_dict(x)
            for x in await self.client.send_command(
                "config/providers/get_entries",
                instance_id=instance_id,
            )
        ]

    async def invoke_provider_config_action(
        self, instance_id: str, action: str
    ) -> list[ConfigEntry] | ConfigActionResult:
        """
        Run a one-shot action button from a provider's options.

        An empty list means the action ran with nothing to report; a non-empty list holds
        the entries the options page should re-render with.

        :param instance_id: The provider instance id.
        :param action: The action id of the pressed button.
        """
        return _parse_config_action_result(
            await self.client.send_command(
                "config/providers/invoke_action",
                instance_id=instance_id,
                action=action,
                require_schema=101,
            )
        )

    async def setup_provider(self, provider_domain: str) -> SetupFlowStep:
        """Start the setup flow to add a new instance of the given provider."""
        return SetupFlowStep.from_dict(
            await self.client.send_command(
                "config/providers/setup",
                provider_domain=provider_domain,
                require_schema=101,
            )
        )

    async def reconfigure_provider(self, instance_id: str) -> SetupFlowStep:
        """Start the reconfigure flow on an existing provider instance (covers reauth)."""
        return SetupFlowStep.from_dict(
            await self.client.send_command(
                "config/providers/reconfigure",
                instance_id=instance_id,
                require_schema=101,
            )
        )

    async def set_provider_access(
        self,
        instance_id: str,
        sharing: ProviderSharing,
        owner: str | None = None,
        shared_users: list[str] | None = None,
    ) -> ProviderConfig:
        """
        Set who owns a music source and who else may use it.

        :param instance_id: The music source (provider instance) to set the access of.
        :param sharing: Who, besides its owner, may use the source.
        :param owner: User id of the member owning the source, None for a source of the whole home.
        :param shared_users: The user ids the source is shared with, SELECTED sharing only.
        """
        return ProviderConfig.from_dict(
            await self.client.send_command(
                "config/providers/set_access",
                instance_id=instance_id,
                sharing=sharing,
                owner=owner,
                shared_users=shared_users,
                require_schema=101,
            )
        )

    async def get_share_candidates(self) -> list[UserSummary]:
        """Return the users a music source or playlist can be shared with."""
        return [
            UserSummary.from_dict(item)
            for item in await self.client.send_command(
                "config/providers/share_candidates",
                require_schema=101,
            )
        ]

    async def save_provider_config(
        self,
        provider_domain: str,
        values: dict[str, ConfigValueType],
        instance_id: str | None = None,
    ) -> ProviderConfig:
        """
        Save Provider(instance) Config.

        provider_domain: (mandatory) domain of the provider.
        values: the raw values for config entries that need to be stored/updated.
        instance_id: id of an existing provider instance (None for new instance setup).
        """
        return ProviderConfig.from_dict(
            await self.client.send_command(
                "config/providers/save",
                provider_domain=provider_domain,
                values=values,
                instance_id=instance_id,
            )
        )

    async def remove_provider_config(self, instance_id: str) -> None:
        """Remove ProviderConfig."""
        await self.client.send_command(
            "config/providers/remove",
            instance_id=instance_id,
        )

    async def reload_provider(self, instance_id: str) -> None:
        """Reload provider."""
        await self.client.send_command(
            "config/providers/reload",
            instance_id=instance_id,
        )

    # Player Config related commands/functions

    async def get_player_configs(
        self,
        provider: str | None = None,
        include_values: bool = False,
        include_unavailable: bool = True,
        include_disabled: bool = True,
    ) -> list[PlayerConfig]:
        """Return all known player configurations, optionally filtered by provider id."""
        return [
            PlayerConfig.from_dict(item)
            for item in await self.client.send_command(
                "config/players",
                provider=provider,
                include_values=include_values,
                include_unavailable=include_unavailable,
                include_disabled=include_disabled,
            )
        ]

    async def get_player_config(self, player_id: str) -> PlayerConfig:
        """Return (full) configuration for a single player."""
        return PlayerConfig.from_dict(
            await self.client.send_command("config/players/get", player_id=player_id)
        )

    async def get_player_config_value(
        self,
        player_id: str,
        key: str,
        default: ConfigValueType = None,
        unpack_splitted_values: bool = False,
    ) -> ConfigValueType:
        """Return single configentry value for a player."""
        return cast(
            "ConfigValueType",
            await self.client.send_command(
                "config/players/get_value",
                player_id=player_id,
                key=key,
                default=default,
                unpack_splitted_values=unpack_splitted_values,
            ),
        )

    async def save_player_config(
        self, player_id: str, values: dict[str, ConfigValueType]
    ) -> PlayerConfig:
        """Save/update PlayerConfig."""
        return PlayerConfig.from_dict(
            await self.client.send_command(
                "config/players/save", player_id=player_id, values=values
            )
        )

    async def remove_player_config(self, player_id: str) -> None:
        """Remove PlayerConfig."""
        await self.client.send_command("config/players/remove", player_id=player_id)

    async def invoke_player_config_action(
        self, player_id: str, action: str
    ) -> list[ConfigEntry] | ConfigActionResult:
        """
        Run a one-shot action button from a player's config.

        An empty list means the action ran with nothing to report; a non-empty list holds
        the player's entries the config form should re-render with.

        :param player_id: The player whose config surface holds the action.
        :param action: The action id of the pressed button (may be protocol-prefixed).
        """
        return _parse_config_action_result(
            await self.client.send_command(
                "config/players/invoke_action",
                player_id=player_id,
                action=action,
                require_schema=101,
            )
        )

    async def setup_player(self, player_id: str) -> SetupFlowStep:
        """Start the setup flow for a player (e.g. pairing)."""
        return SetupFlowStep.from_dict(
            await self.client.send_command(
                "config/players/setup",
                player_id=player_id,
                require_schema=101,
            )
        )

    # Player Queue Config related commands/functions

    async def get_player_queue_configs(self) -> list[PlayerQueueConfig]:
        """Return all (stored) queue configurations."""
        return [
            PlayerQueueConfig.from_dict(item)
            for item in await self.client.send_command(
                "config/player_queues",
                require_schema=101,
            )
        ]

    async def get_player_queue_config(self, queue_id: str) -> PlayerQueueConfig:
        """Return (full) configuration for a single queue, with dynamic options populated."""
        return PlayerQueueConfig.from_dict(
            await self.client.send_command(
                "config/player_queues/get",
                queue_id=queue_id,
                require_schema=101,
            )
        )

    async def get_player_queue_config_entries(self, queue_id: str) -> list[ConfigEntry]:
        """Return all Config Entries to configure a queue."""
        return [
            ConfigEntry.from_dict(x)
            for x in await self.client.send_command(
                "config/player_queues/get_entries",
                queue_id=queue_id,
                require_schema=101,
            )
        ]

    async def get_player_queue_config_value(self, queue_id: str, key: str) -> ConfigValueType:
        """Return single config(entry) value for a queue."""
        return cast(
            "ConfigValueType",
            await self.client.send_command(
                "config/player_queues/get_value",
                queue_id=queue_id,
                key=key,
                require_schema=101,
            ),
        )

    async def save_player_queue_config(
        self, queue_id: str, values: dict[str, ConfigValueType]
    ) -> PlayerQueueConfig:
        """Save/update PlayerQueueConfig."""
        return PlayerQueueConfig.from_dict(
            await self.client.send_command(
                "config/player_queues/save",
                queue_id=queue_id,
                values=values,
                require_schema=101,
            )
        )

    # Core Controller config commands

    async def get_core_configs(self, include_values: bool = False) -> list[CoreConfig]:
        """Return all core controllers config options."""
        return [
            CoreConfig.from_dict(item)
            for item in await self.client.send_command(
                "config/core",
                include_values=include_values,
            )
        ]

    async def get_core_config(self, domain: str) -> CoreConfig:
        """Return configuration for a single core controller."""
        return CoreConfig.from_dict(
            await self.client.send_command(
                "config/core/get",
                domain=domain,
            )
        )

    async def get_core_config_value(
        self,
        domain: str,
        key: str,
        default: ConfigValueType = None,
    ) -> ConfigValueType:
        """Return single configentry value for a core controller."""
        return cast(
            "ConfigValueType",
            await self.client.send_command(
                "config/core/get_value",
                domain=domain,
                key=key,
                default=default,
            ),
        )

    async def get_core_config_entries(self, domain: str) -> list[ConfigEntry]:
        """Return Config entries to configure a core controller."""
        return [
            ConfigEntry.from_dict(x)
            for x in await self.client.send_command(
                "config/core/get_entries",
                domain=domain,
            )
        ]

    async def invoke_core_config_action(
        self, domain: str, action: str
    ) -> list[ConfigEntry] | ConfigActionResult:
        """
        Run a one-shot action button from a core module's config.

        An empty list means the action ran with nothing to report; a non-empty list holds
        the entries the config form should re-render with.

        :param domain: The core controller domain.
        :param action: The action id of the pressed button.
        """
        return _parse_config_action_result(
            await self.client.send_command(
                "config/core/invoke_action",
                domain=domain,
                action=action,
                require_schema=101,
            )
        )

    async def save_core_config(
        self,
        domain: str,
        values: dict[str, ConfigValueType],
    ) -> CoreConfig:
        """Save CoreController Config values."""
        return CoreConfig.from_dict(
            await self.client.send_command(
                "config/core/save",
                domain=domain,
                values=values,
            )
        )

    async def get_dsp_preset(self) -> list[DSPConfigPreset]:
        """Return all user-defined DSP presets."""
        return [
            DSPConfigPreset.from_dict(obj)
            for obj in await self.client.send_command(
                "config/dsp_presets/get",
            )
        ]

    async def remove_dsp_preset(self, preset_id: str) -> None:
        """Remove a user-defined DSP preset."""
        await self.client.send_command(
            "config/dsp_presets/remove",
            preset_id=preset_id,
        )

    async def save_dsp_preset(self, preset: DSPConfigPreset) -> DSPConfigPreset:
        """Save/update a user-defined DSP preset."""
        return DSPConfigPreset.from_dict(
            await self.client.send_command(
                "config/dsp_presets/save",
                preset=preset,
            )
        )

    async def get_player_dsp_config(self, player_id: str) -> DSPConfig:
        """Return the DSP Configuration for a player."""
        return DSPConfig.from_dict(
            await self.client.send_command(
                "config/players/dsp/get",
                player_id=player_id,
            )
        )

    async def save_player_dsp_config(self, player_id: str, config: DSPConfig) -> DSPConfig:
        """Save/update DSPConfig for a player."""
        return DSPConfig.from_dict(
            await self.client.send_command(
                "config/players/dsp/save",
                player_id=player_id,
                config=config,
            )
        )

    async def apply_dsp_preset(self, player_id: str, preset_id: str) -> DSPConfig:
        """Apply a persisted DSP preset to a player."""
        return DSPConfig.from_dict(
            await self.client.send_command(
                "config/players/dsp/apply_preset",
                player_id=player_id,
                preset_id=preset_id,
                require_schema=101,
            )
        )

    async def get_dsp_irs(self) -> list[dict[str, Any]]:
        """Return the metadata for all stored convolution impulse responses."""
        result: list[dict[str, Any]] = await self.client.send_command(
            "config/dsp_irs/list",
            require_schema=101,
        )
        return result

    async def upload_dsp_ir(self, name: str, data: str) -> dict[str, Any]:
        """
        Store a convolution impulse response and return its metadata record.

        :param name: Display name for the impulse response.
        :param data: Base64 encoded contents of the audio file to store.
        """
        result: dict[str, Any] = await self.client.send_command(
            "config/dsp_irs/upload",
            name=name,
            data=data,
            require_schema=101,
        )
        return result

    async def remove_dsp_ir(self, ir_id: str) -> None:
        """Remove a stored convolution impulse response by its identifier."""
        await self.client.send_command(
            "config/dsp_irs/remove",
            ir_id=ir_id,
            require_schema=101,
        )

    async def get_player_config_entries(self, player_id: str) -> list[ConfigEntry]:
        """Return Config entries to configure a player."""
        return [
            ConfigEntry.from_dict(x)
            for x in await self.client.send_command(
                "config/players/get_entries",
                player_id=player_id,
            )
        ]

    # Setup flow commands

    async def submit_setup_flow(
        self, flow_id: str, values: dict[str, ConfigValueType]
    ) -> SetupFlowStep:
        """
        Submit the user's values for the flow's pending FORM step.

        Returns the flow's next step, or the same FORM step (with per-field errors
        set) when validation failed.

        :param flow_id: The id of the running flow.
        :param values: The raw values for the form's config entries.
        """
        return SetupFlowStep.from_dict(
            await self.client.send_command(
                "config/flows/submit",
                flow_id=flow_id,
                values=values,
                require_schema=101,
            )
        )

    async def get_setup_flow(self, flow_id: str) -> SetupFlowStep:
        """Return the current step of a running flow (idempotent re-render, never advances)."""
        return SetupFlowStep.from_dict(
            await self.client.send_command(
                "config/flows/get",
                flow_id=flow_id,
                require_schema=101,
            )
        )

    async def abort_setup_flow(self, flow_id: str) -> None:
        """Abort a running flow (user cancelled)."""
        await self.client.send_command(
            "config/flows/abort",
            flow_id=flow_id,
            require_schema=101,
        )


def _parse_config_action_result(result: Any) -> list[ConfigEntry] | ConfigActionResult:
    """Parse the result of a config invoke_action command."""
    if isinstance(result, list):
        return [ConfigEntry.from_dict(x) for x in result]
    return ConfigActionResult.from_dict(result)
