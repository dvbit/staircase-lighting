"""Switch platform for the Staircase Lighting integration.

Provides:
- switch.<name>_lux_control: runtime toggle for lux-based gating.
- switch.<name>_lights: manual on/off for both staircase lights.
"""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, CONF_NAME
from .coordinator import StaircaseLightingCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities from a config entry."""
    coordinator: StaircaseLightingCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data[CONF_NAME]

    async_add_entities(
        [
            LuxControlSwitch(coordinator, entry, name),
            LightsSwitch(coordinator, entry, name),
        ]
    )


class StaircaseBaseSwitch(SwitchEntity):
    """Base class for staircase switches with shared device info and callbacks."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: StaircaseLightingCoordinator,
        entry: ConfigEntry,
        name: str,
    ) -> None:
        """Initialize base switch."""
        self._coordinator = coordinator
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=name,
            manufacturer="Staircase Lighting",
            model="Virtual",
            sw_version="1.0.0",
        )

    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        self._coordinator.async_add_update_callback(
            self._handle_coordinator_update
        )

    async def async_will_remove_from_hass(self) -> None:
        """Remove update callback."""
        self._coordinator.async_remove_update_callback(
            self._handle_coordinator_update
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle coordinator state update."""
        self.async_write_ha_state()


class LuxControlSwitch(StaircaseBaseSwitch):
    """Switch to enable/disable lux-based light gating.

    When off, lights always activate regardless of ambient lux.
    """

    _attr_translation_key = "lux_control"
    _attr_icon = "mdi:theme-light-dark"

    def __init__(self, coordinator, entry, name) -> None:
        """Initialize lux control switch."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_lux_control"

    @property
    def is_on(self) -> bool:
        """Return True if lux control is enabled."""
        return self._coordinator.lux_control_enabled

    async def async_turn_on(self, **kwargs) -> None:
        """Enable lux control."""
        self._coordinator.lux_control_enabled = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Disable lux control — lights always activate."""
        self._coordinator.lux_control_enabled = False
        self.async_write_ha_state()


class LightsSwitch(StaircaseBaseSwitch):
    """Manual on/off switch for both staircase lights.

    Turn ON: activates both lights at current mode brightness (normal/dim).
    Does not start zone timers.
    Turn OFF: turns off both lights, cancels any active zone timers,
    resets state to idle.
    If a sensor triggers while manually on, timers start normally.
    When timers expire, lights turn off and manual flag clears.
    """

    _attr_translation_key = "lights"
    _attr_icon = "mdi:lightbulb-group"

    def __init__(self, coordinator, entry, name) -> None:
        """Initialize lights switch."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_lights"

    @property
    def is_on(self) -> bool:
        """Return True if lights are currently on (auto or manual)."""
        return self._coordinator.lights_on

    async def async_turn_on(self, **kwargs) -> None:
        """Manually turn on both lights at current mode brightness."""
        await self._coordinator.async_manual_turn_on()

    async def async_turn_off(self, **kwargs) -> None:
        """Manually turn off both lights and cancel active timers."""
        await self._coordinator.async_manual_turn_off()
